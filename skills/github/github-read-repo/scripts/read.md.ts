/**
 * read.md.ts — Read and edit large Markdown documents section-by-section.
 *
 * The companion to `deepwiki.com.ts`: where that script pulls a repo's full
 * DeepWiki document into `data/<owner>/<repo>/contents.md`, this script reads
 * it (or any other Markdown file) one section at a time instead of dumping the
 * whole thing into context. It parses the document with `md2ast` and slices out
 * exactly the section you ask for.
 *
 * Usage (run from the skill root):
 *   tsx scripts/read.md.ts outline --file <path> | --repo <owner/repo>
 *   tsx scripts/read.md.ts read    --file <path> | --repo <owner/repo> [--section "<title>"] [--range "start-end"]
 *   tsx scripts/read.md.ts edit    --file <path> | --repo <owner/repo> --section "<title>" --replace <text> [--write] [--no-backup]
 *
 * `--repo <owner/repo>` is shorthand for the cached path
 * `data/<owner>/<repo>/contents.md`. `--file` takes any direct path.
 *
 * Exit codes:
 *   0  success
 *   1  input error (bad args, missing file, section not found)
 *   2  runtime / I/O failure
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  parseMarkdown,
  buildHeadingOutline,
  findBestSectionWithContent,
  findSectionCandidates,
  locateSection,
  splitLines,
  type OutlineEntry,
} from './lib/ast.js';

/** Resolve the skill root directory (parent of `scripts/`). */
function skillRoot(): string {
  return path.resolve(import.meta.dirname, '..');
}

/**
 * A thin parsed-argument holder produced by {@link parseArgs}.
 */
interface Args {
  command: 'outline' | 'read' | 'edit' | 'files';
  file?: string;
  repo?: string;
  source?: string;
  section?: string;
  range?: string;
  replace?: string;
  limit?: number;
  path?: string;
  filter?: string;
  write: boolean;
  noBackup: boolean;
}

/**
 * Parse the process argument vector into a typed {@link Args}.
 *
 * `--section` consumes one value; `--replace` consumes one value (the next arg).
 * Unrecognized flags and missing required values are rejected.
 *
 * @param argv The raw args (excluding `node`/script).
 * @returns The parsed arguments.
 * @throws Error on malformed input.
 */
function parseArgs(argv: string[]): Args {
  const command = argv[0] as Args['command'];
  if (command !== 'outline' && command !== 'read' && command !== 'edit' && command !== 'files') {
    throw new Error(`Unknown command "${command ?? ''}". Expected outline, read, edit, or files.`);
  }

  const args: Args = { command, write: false, noBackup: false };
  for (let i = 1; i < argv.length; i++) {
    const flag = argv[i];
    switch (flag) {
      case '--file':
        args.file = argv[++i];
        if (!args.file) throw new Error('--file requires a path argument.');
        break;
      case '--repo':
        args.repo = argv[++i];
        if (!args.repo) throw new Error('--repo requires an <owner>/<repo> argument.');
        break;
      case '--source':
        args.source = argv[++i];
        if (!args.source) throw new Error('--source requires a source name (deepwiki|gitdiagram|gitingest).');
        break;
      case '--section':
        args.section = argv[++i];
        if (!args.section) throw new Error('--section requires a title argument.');
        break;
      case '--range':
        args.range = argv[++i];
        if (!args.range) throw new Error('--range requires a "start-end" argument.');
        break;
      case '--replace':
        args.replace = argv[++i];
        if (args.replace === undefined) throw new Error('--replace requires a text argument.');
        break;
      case '--limit':
        args.limit = Number(argv[++i]);
        if (!Number.isInteger(args.limit) || args.limit < 1) throw new Error('--limit requires a positive integer.');
        break;
      case '--path':
        args.path = argv[++i];
        if (!args.path) throw new Error('--path requires a file name argument (gitingest digest file).');
        break;
      case '--filter':
        args.filter = argv[++i];
        if (!args.filter) throw new Error('--filter requires a substring argument.');
        break;
      case '--write':
        args.write = true;
        break;
      case '--no-backup':
        args.noBackup = true;
        break;
      default:
        throw new Error(`Unknown flag "${flag}".`);
    }
  }

  if (args.file && args.repo) {
    throw new Error('Use either --file OR --repo, not both.');
  }
  if (!args.file && !args.repo) {
    throw new Error('One of --file or --repo is required.');
  }

  if (args.command === 'read') {
    const locators = [args.section, args.range, args.path].filter(Boolean).length;
    if (locators === 0) throw new Error('read requires one of --section, --range, or --path.');
    if (locators > 1) throw new Error('--section, --range and --path are mutually exclusive.');
  }
  if (args.command === 'files' && (args.section || args.range || args.replace)) {
    throw new Error('files only supports --file/--repo/--source and --filter.');
  }

  return args;
}

/**
 * Check whether a path is an existing directory.
 *
 * @param p The path to test.
 * @returns `true` if `p` is a directory.
 */
function isDirectory(p: string): boolean {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

/**
 * Scan `data/` for every on-disk cache directory of a repo, so the "no cache"
 * error can point at where the content actually lives (non-standard layout,
 * or another source pulled it) instead of leaving the user to guess.
 *
 * @param owner Repo owner segment.
 * @param repo Repo name segment.
 * @returns Absolute paths of any `data/<layer>/<owner>/<repo>/` directory found.
 */
function findCacheHints(owner: string, repo: string): string[] {
  const dataRoot = path.join(skillRoot(), 'data');
  if (!fs.existsSync(dataRoot)) return [];
  const hints: string[] = [];
  for (const layer of fs.readdirSync(dataRoot)) {
    const repoDir = path.join(dataRoot, layer, owner, repo);
    if (!isDirectory(repoDir)) continue;
    for (const file of fs.readdirSync(repoDir)) {
      hints.push(`  ${path.join(repoDir, file)}`);
    }
  }
  return hints;
}

/**
 * Build the "no cache" error message, appending whatever the on-disk scan
 * actually found (or a clear statement that nothing was found).
 *
 * @param repo The repo as typed by the user (`owner/repo`).
 * @param headline The primary error line (source-specific or generic).
 * @param owner Owner segment of the repo.
 * @param repoName Repo name segment.
 * @param missingFile When an explicit `--source` was requested, the file that
 *   was expected under that source's layered path.
 * @returns A complete, actionable error message.
 */
function noCacheMessage(repo: string, headline: string, owner: string, repoName: string, missingFile?: string): string {
  const hints = findCacheHints(owner, repoName);
  let msg =
    `${headline}. Pull it first, e.g.:\n` +
    `  tsx scripts/deepwiki.com.ts pull ${repo}\n` +
    `  tsx scripts/gitingest.com.ts pull ${repo}\n` +
    `  tsx scripts/gitdiagram.com.ts pull ${repo}\n` +
    `or pass --file <path> / --source <deepwiki|gitdiagram|gitingest>.`;
  if (hints.length > 0) {
    msg += `\n\n缓存实际存在于以下位置:${hints.join('')}`;
    if (missingFile) msg += `\n（其中不含目标文件 ${missingFile}——检查源是否匹配）`;
  } else if (!fs.existsSync(path.join(skillRoot(), 'data'))) {
    msg += `\n\ndata/ 目录尚不存在，本技能还没有拉取过任何仓库。`;
  } else {
    msg += `\n\n已扫描 data/ 下全部缓存目录，未找到 ${owner}/${repoName} 的任何缓存。`;
  }
  return msg;
}

/**
 * Resolve the source file path from either `--file` (direct path, relative to
 * the skill root) or `--repo` (cached `data/<source>/<owner>/<repo>/<file>`).
 *
 * Each source caches different artifacts:
 *   deepwiki   → data/deepwiki.com/<owner>/<repo>/contents.md   (markdown doc)
 *   gitdiagram → data/gitdiagram.com/<owner>/<repo>/explanation.md (markdown)
 *   gitingest  → data/gitingest.com/<owner>/<repo>/summary.md   (markdown)
 *
 * When `--source` is omitted, the cache is probed in that order and the first
 * source with an existing markdown file is used, so plain `--repo owner/repo`
 * keeps working for repos cached under any of the three sources. The chosen
 * source is announced on stderr so multi-source caches are never silent.
 *
 * @param args Parsed arguments.
 * @returns An absolute path to the Markdown file.
 */
function resolveSourcePath(args: Args): string {
  if (args.file) {
    return path.isAbsolute(args.file) ? args.file : path.resolve(skillRoot(), args.file);
  }
  const parts = args.repo!.split('/');
  if (parts.length < 2 || parts[0] === '' || parts[1] === '' || parts[0] === '.' || parts[1] === '.' || parts[0] === '..' || parts[1] === '..') {
    throw new Error(`Invalid repo "${args.repo}". Use <owner>/<repo>.`);
  }

  /** Which source provides the markdown entry file, and its filename. */
  const SOURCES: Array<{ name: string; file: string }> = [
    { name: 'deepwiki', file: 'contents.md' },
    { name: 'gitdiagram', file: 'explanation.md' },
    { name: 'gitingest', file: 'summary.md' },
  ];

  const explicit = SOURCES.find((s) => s.name === args.source);
  if (args.source && !explicit) {
    throw new Error(`Unknown --source "${args.source}". Expected deepwiki, gitdiagram, or gitingest.`);
  }
  if (explicit) {
    const p = path.join(skillRoot(), 'data', explicit.name + '.com', parts[0]!, parts[1]!, explicit.file);
    if (!fs.existsSync(p)) {
      throw new Error(
        noCacheMessage(args.repo!, `No ${args.source} cache for "${args.repo!}"`, parts[0]!, parts[1]!, explicit.file),
      );
    }
    return p;
  }

  // Auto-probe: first source that has this repo cached with its markdown file.
  for (const s of SOURCES) {
    const p = path.join(skillRoot(), 'data', s.name + '.com', parts[0]!, parts[1]!, s.file);
    if (fs.existsSync(p)) {
      // stderr so it never pollutes piped stdout output.
      console.error(`using ${s.name} from ${p}`);
      return p;
    }
  }
  throw new Error(noCacheMessage(args.repo!, `No cached markdown for "${args.repo!}"`, parts[0]!, parts[1]!));
}

/**
 * Read a file as UTF-8 text, throwing a friendly error if it is missing.
 *
 * @param filePath The path to read.
 * @returns The file contents.
 */
function readSource(filePath: string): string {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}\nHint: pull the repo first with \`tsx scripts/deepwiki.com.ts pull <owner>/<repo>\`, or check --file / --repo.`);
  }
  return fs.readFileSync(filePath, 'utf-8');
}

/**
 * Print a heading outline as an indented tree with 1-based line numbers.
 *
 * @param outline The flattened heading outline.
 */
function printOutline(outline: OutlineEntry[]): void {
  if (outline.length === 0) {
    console.log('(no headings found)');
    return;
  }
  for (const entry of outline) {
    const indent = '  '.repeat(entry.depth - 1);
    console.log(`${entry.line.toString().padStart(5)}  ${indent}#${entry.depth} ${entry.title}`);
  }
}

/**
 * Truncate output to at most `limit` lines (used by `--limit` to keep piped
 * consumers from forcing an early EOF / SIGPIPE on large sections or ranges).
 *
 * @param text The full output text.
 * @param limit Max lines, or undefined for no limit.
 * @returns The text, truncated with a notice appended when cut.
 */
function truncate(text: string, limit: number | undefined): string {
  if (!limit || limit <= 0) return text;
  const lines = text.split('\n');
  if (lines.length <= limit) return text;
  return lines.slice(0, limit).join('\n') + `\n... (输出已截断到 ${limit} 行，可用 --limit <N> 调整)`;
}

/**
 * Locate and print a section by title, showing the user a ranked candidate list
 * when no good match is found.
 *
 * @param source Raw markdown.
 * @param outline Heading outline.
 * @param title The requested section title.
 * @param limit Optional max output lines (`--limit`).
 * @returns The located section, or `null` if none matched.
 */
function printSectionByTitle(source: string, outline: OutlineEntry[], title: string, limit?: number): ReturnType<typeof locateSection> {
  const best = findBestSectionWithContent(source, outline, title);
  if (!best) {
    console.error(`Section "${title}" not found.`);
    const candidates = findSectionCandidates(outline, title);
    if (candidates.length > 0) {
      console.error('Did you mean one of these?');
      for (const c of candidates) {
        console.error(`  L${c.line}  (score ${c.score.toFixed(2)})  ${c.title}`);
      }
    }
    return null;
  }
  const section = locateSection(source, outline, best);
  if (!section) {
    console.error(`Could not compute range for section "${best.title}".`);
    return null;
  }
  console.log(`--- ${section.heading.title} (L${section.startLine}–${section.endLine >= 0 ? section.endLine : 'EOF'}) ---`);
  console.log(truncate(section.content.trimEnd(), limit));
  return section;
}

/**
 * Print a line-range slice of the document (`--range "start-end"`).
 *
 * @param source Raw markdown.
 * @param range The "start-end" string.
 * @param limit Optional max output lines (`--limit`).
 */
function printRange(source: string, range: string, limit?: number): void {
  const match = /^\s*(\d+)\s*-\s*(\d+)\s*$/.exec(range);
  if (!match) {
    throw new Error(`Invalid --range "${range}". Expected "start-end", e.g. --range "10-40".`);
  }
  const start = parseInt(match[1]!, 10);
  const end = parseInt(match[2]!, 10);
  if (start < 1 || end < start) {
    throw new Error(`Invalid --range "${range}". start must be >= 1 and end >= start.`);
  }
  const lines = splitLines(source);
  const body = lines.slice(start, end + 1);
  if (body.length === 0) {
    throw new Error(`Range ${start}-${end} is beyond the document (${lines.length - 1} lines).`);
  }
  console.log(`--- lines ${start}–${end} ---`);
  console.log(truncate(body.join('\n'), limit));
}

/**
 * Resolve the gitingest `digest.txt` path from `--file` / `--repo` by taking
 * the markdown main file's directory (same cache dir) and adding `digest.txt`.
 *
 * @param args Parsed arguments.
 * @returns Absolute path to `digest.txt`.
 */
function resolveDigestPath(args: Args): string {
  const md = resolveSourcePath(args);
  const digest = path.join(path.dirname(md), 'digest.txt');
  if (!fs.existsSync(digest)) {
    throw new Error(
      `No digest.txt next to ${md} (${digest}).\n` +
        `Pull the gitingest digest first: tsx scripts/gitingest.com.ts pull ${args.repo ?? '<owner/repo>'}`,
    );
  }
  return digest;
}

/** A single entry of the gitingest `files.json` index. */
interface FileIndexEntry {
  path: string;
  startLine: number;
  endLine: number;
  lines: number;
}

/**
 * Load the file index (`files.json`) generated by gitingest.com.ts at pull
 * time, throwing an actionable error when it is missing or stale.
 *
 * @param digestPath Path to `digest.txt` (index lives beside it).
 * @returns The parsed index entries.
 */
function loadFileIndex(digestPath: string): FileIndexEntry[] {
  const indexPath = path.join(path.dirname(digestPath), 'files.json');
  if (!fs.existsSync(indexPath)) {
    const repoDir = path.dirname(digestPath);
    const owner = path.basename(path.dirname(repoDir));
    const repo = path.basename(repoDir);
    throw new Error(
      `No files.json next to ${digestPath}.\n` +
        `Re-pull to generate the index: tsx scripts/gitingest.com.ts pull ${owner}/${repo}`,
    );
  }
  const parsed = JSON.parse(fs.readFileSync(indexPath, 'utf-8')) as { files?: FileIndexEntry[] };
  if (!parsed.files || parsed.files.length === 0) {
    throw new Error(`files.json at ${indexPath} has no entries; re-pull to regenerate.`);
  }
  return parsed.files;
}

/**
 * Look up a file in the digest index by name (exact, then path-suffix match),
 * offering near-miss candidates when nothing matches.
 *
 * @param digestPath Path to `digest.txt`.
 * @param wanted The file name / path as typed by the user.
 * @returns The 1-based inclusive line range of that file's body.
 */
function resolveFileRange(digestPath: string, wanted: string): { start: number; end: number } {
  const files = loadFileIndex(digestPath);
  const wantedNorm = wanted.replace(/\\/g, '/');
  const hit =
    files.find((f) => f.path === wantedNorm) ||
    files.find((f) => f.path.endsWith('/' + wantedNorm));
  if (hit) return { start: hit.startLine, end: hit.endLine };
  const cands = files
    .filter((f) => f.path.includes(wantedNorm))
    .slice(0, 5)
    .map((f) => `  L${f.startLine}  ${f.path}`);
  throw new Error(
    `File "${wanted}" not found in the digest index.` +
      (cands.length > 0 ? `\nDid you mean one of these?\n${cands.join('\n')}` : ''),
  );
}

/**
 * Print the digest's file → line index (`files` command), optionally filtered
 * by substring.
 *
 * @param digestPath Path to `digest.txt`.
 * @param filter Optional substring filter on file paths.
 */
function printFileIndex(digestPath: string, filter?: string): void {
  const files = loadFileIndex(digestPath);
  const shown = filter ? files.filter((f) => f.path.includes(filter)) : files;
  if (shown.length === 0) {
    console.error(`No files match "${filter ?? ''}" in the digest index.`);
    process.exit(1);
  }
  for (const f of shown) {
    console.log(`${String(f.startLine).padStart(7)}  ${f.path}`);
  }
  if (filter) console.log(`\n(${shown.length}/${files.length} files match "${filter}")`);
  else console.log(`\n(${files.length} files; 用 --filter <substr> 过滤，用 read --file <digest> --path <file> 精读)`);
}

/**
 * Build the edited document for `edit`: replace the located section's char span
 * with the replacement text. Returns `null` if the section can't be found.
 *
 * @param source Raw markdown.
 * @param outline Heading outline.
 * @param title The section to replace.
 * @param replacement The new markdown for that section.
 * @returns The new full document text, or `null` on no match.
 */
function buildEditedDocument(source: string, outline: OutlineEntry[], title: string, replacement: string): string | null {
  const best = findBestSectionWithContent(source, outline, title);
  if (!best) return null;
  const section = locateSection(source, outline, best);
  if (!section) return null;

  // Preserve the section's original trailing whitespace (blank lines before the
  // next heading / EOF) so a replacement that omits a trailing newline never
  // glues onto the following section.
  const original = source.slice(section.startChar, section.endChar);
  const trailingWs = original.match(/\s*$/)?.[0] ?? '';
  const clean = replacement.replace(/\s+$/, '');
  return source.slice(0, section.startChar) + clean + trailingWs + source.slice(section.endChar);
}

/**
 * Run the `edit` command (dry-run by default).
 *
 * In dry-run mode the proposed change is printed and nothing is written. With
 * `--write` the file is updated, optionally backing up the original first.
 *
 * @param args Parsed arguments.
 * @param filePath The resolved source path.
 * @param source Raw markdown.
 */
function runEdit(args: Args, filePath: string, source: string): void {
  if (!args.section) throw new Error('edit requires --section "<title>".');
  if (args.replace === undefined) throw new Error('edit requires --replace <text>.');
  if (args.range) throw new Error('edit does not support --range; use --section.');

  const outline = buildHeadingOutline(parseMarkdown(source));
  const edited = buildEditedDocument(source, outline, args.section, args.replace);
  if (edited === null) {
    printSectionByTitle(source, outline, args.section);
    throw new Error(`Cannot edit: section "${args.section}" not found.`);
  }

  if (!args.write) {
    console.log('=== DRY RUN — no changes written. Re-run with --write to apply. ===');
    console.log('Old section:');
    const sec = locateSection(source, outline, findBestSectionWithContent(source, outline, args.section)!);
    console.log(sec ? sec.content.trimEnd() : '(empty)');
    console.log('\nNew section:');
    console.log(args.replace.trimEnd());
    return;
  }

  if (!args.noBackup) {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backup = `${filePath}.backup.${stamp}`;
    fs.writeFileSync(backup, source, 'utf-8');
    console.log(`Backup written to ${backup}`);
  }
  fs.writeFileSync(filePath, edited, 'utf-8');
  console.log(`Edited ${filePath}`);
}

/**
 * CLI entry point — routes to the subcommand.
 */
function main(): void {
  // Junction-aware startup hint (stderr so piped stdout stays clean).
  console.error(`技能根（真实路径）: ${fs.realpathSync(skillRoot())}`);

  let args: Args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }

  let filePath: string;
  let source: string;
  try {
    filePath = resolveSourcePath(args);
    source = readSource(filePath);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }

  const doc = parseMarkdown(source);
  const outline = buildHeadingOutline(doc);

  try {
    if (args.command === 'outline') {
      printOutline(outline);
    } else if (args.command === 'read') {
      if (args.section) {
        if (printSectionByTitle(source, outline, args.section, args.limit) === null) process.exit(1);
      } else if (args.range) {
        printRange(source, args.range, args.limit);
      } else if (args.path) {
        // Read one file out of a gitingest digest via the pull-time index.
        const digest = resolveDigestPath(args);
        const { start, end } = resolveFileRange(digest, args.path);
        printRange(readSource(digest), `${start}-${end}`, args.limit);
      } else {
        console.error('read requires --section "<title>", --range "start-end", or --path <file>.');
        process.exit(1);
      }
    } else if (args.command === 'files') {
      printFileIndex(resolveDigestPath(args), args.filter);
    } else {
      runEdit(args, filePath, source);
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(2);
  }
}

// Allow importing this module as a library.
const isMain =
  process.argv[1] === fileURLToPath(import.meta.url) ||
  process.argv[1]?.endsWith('read.md.ts') ||
  process.argv[1]?.endsWith('read.md.js');

if (isMain) main();
