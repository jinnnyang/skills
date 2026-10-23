/**
 * deepwiki.com.ts — Pull DeepWiki-generated documentation for a GitHub repo.
 *
 * Connects to the DeepWiki MCP server (https://mcp.deepwiki.com/mcp), fetches
 * the wiki structure and full contents for a repo, and stores them under the
 * skill's `data/<owner>/<repo>/` directory so the companion `read.md.ts` script
 * can read/edit them locally without re-fetching.
 *
 * Usage (run from the skill root):
 *   tsx scripts/deepwiki.com.ts pull <owner/repo|url>   # fetch one repo
 *   tsx scripts/deepwiki.com.ts pull all                # refresh every cached repo
 *
 * Exit codes:
 *   0  success
 *   1  input / argument error
 *   2  runtime, I/O, or network failure
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { McpClient } from './utils/mcp/mcp-client.js';
import { startElapsedReporter } from './utils/progress.js';

/** DeepWiki's public MCP endpoint. */
const SERVER_URL = 'https://mcp.deepwiki.com/mcp';

/** Contents shorter than this (bytes) are treated as a failed fetch. */
const MIN_CONTENTS_BYTES = 10_000;

/**
 * Resolve the skill root directory (parent of `scripts/`), anchoring storage to
 * it rather than to `process.cwd()` so commands work from any working directory.
 */
function skillRoot(): string {
  return path.resolve(import.meta.dirname, '..');
}

/**
 * Resolve a path under the skill's `data/` directory.
 *
 * @param subPath Optional sub-path relative to `data/`.
 * @returns An absolute path inside `data/`.
 */
function dataPath(subPath = ''): string {
  return path.join(skillRoot(), 'data', subPath);
}

/**
 * Reject empty, traversal, or backslash segments in user/repo names.
 *
 * @param seg A path segment to validate.
 * @returns `true` if the segment is safe to use as a directory name.
 */
function validateSegment(seg: string): boolean {
  return seg !== '' && seg !== '.' && seg !== '..' && !seg.includes('\\');
}

/**
 * Parse a user-supplied repo reference (`owner/repo` or a full GitHub URL) into
 * its owner and repo name.
 *
 * @param input The raw argument.
 * @returns `{ owner, repo }` with any `.git` suffix stripped.
 * @throws Error if the input cannot be parsed safely.
 */
function parseRepoInfo(input: string): { owner: string; repo: string } {
  let owner: string;
  let repo: string;

  if (input.startsWith('http')) {
    const url = new URL(input);
    const parts = url.pathname.split('/').filter(Boolean);
    if (parts.length < 2 || !validateSegment(parts[0]!) || !validateSegment(parts[1]!)) {
      throw new Error('Invalid GitHub URL. Expected https://github.com/<owner>/<repo>.');
    }
    owner = parts[0]!;
    repo = parts[1]!.replace(/\.git$/, '');
  } else {
    const parts = input.split('/');
    if (parts.length < 2 || !validateSegment(parts[0]!) || !validateSegment(parts[1]!)) {
      throw new Error('Invalid repo format. Use <owner>/<repo> or a full GitHub URL.');
    }
    owner = parts[0]!;
    repo = parts[1]!.replace(/\.git$/, '');
  }

  return { owner, repo };
}

/**
 * List all locally cached repos as `owner/repo` strings (sorted).
 *
 * Enumerates `data/deepwiki.com/` (the source-layered root), NOT the bare
 * `data/` root — the latter would mistake `deepwiki.com` itself for an owner.
 *
 * @returns An array of cached repo paths.
 */
function listLocalRepos(): string[] {
  const root = dataPath('deepwiki.com');
  if (!fs.existsSync(root)) return [];
  const repos: string[] = [];
  for (const owner of fs.readdirSync(root)) {
    const ownerDir = path.join(root, owner);
    if (!isDirectory(ownerDir)) continue;
    for (const repo of fs.readdirSync(ownerDir)) {
      if (isDirectory(path.join(ownerDir, repo))) {
        repos.push(`${owner}/${repo}`);
      }
    }
  }
  return repos.sort();
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
 * Extract the human-readable text from a DeepWiki MCP tool result, falling back
 * to pretty-printed JSON when no `content[0].text` is present.
 *
 * @param result The raw tool-call result.
 * @returns A string body suitable for writing to disk.
 */
function extractText(result: { content?: Array<{ type: string; text?: string }> }): string {
  const first = result.content?.[0];
  if (first && typeof first.text === 'string') return first.text;
  return JSON.stringify(result, null, 2);
}

/**
 * Atomically write a file (temp file + rename) to avoid a reader ever observing
 * a partially-written document.
 *
 * @param filePath The destination path.
 * @param content The text to write.
 */
function atomicWrite(filePath: string, content: string): void {
  const tmp = `${filePath}.tmp`;
  fs.writeFileSync(tmp, content, 'utf-8');
  fs.renameSync(tmp, filePath);
}

/**
 * Fetch and store both the structure and the full contents for a single repo.
 *
 * @param client The initialized MCP client.
 * @param localName The cached name `owner/repo`.
 */
async function pullRepo(client: McpClient, localName: string): Promise<void> {
  const [owner, repo] = localName.split('/');
  const repoName = `${owner}/${repo!.replace(/\.git$/, '')}`;
  // Source-layered layout: data/deepwiki.com/<owner>/<repo>/ — must match
  // read.md.ts's resolver and the layout documented in SKILL.md.
  const targetDir = dataPath(path.join('deepwiki.com', owner!, repo!));

  console.log(`Fetching wiki structure + contents for ${repoName}...`);
  const stop = startElapsedReporter(`正在拉取 ${repoName} 的 wiki（结构+正文）`);
  let structureContent: string;
  let contentsContent: string;
  try {
    const structureResult = await client.callTool('read_wiki_structure', { repoName });
    structureContent = extractText(structureResult);

    const contentsResult = await client.callTool('read_wiki_contents', { repoName });
    contentsContent = extractText(contentsResult);
  } finally {
    stop();
  }

  fs.mkdirSync(targetDir, { recursive: true });
  console.log(`Saving files to ${targetDir}...`);
  atomicWrite(path.join(targetDir, 'structure.md'), structureContent);
  atomicWrite(path.join(targetDir, 'contents.md'), contentsContent);
  console.log('Saved: structure.md, contents.md');

  // A too-small contents file usually means the fetch silently failed.
  const contentsBytes = Buffer.byteLength(contentsContent, 'utf-8');
  if (contentsBytes < MIN_CONTENTS_BYTES) {
    console.warn(`⚠ Warning: contents.md only ${contentsBytes} bytes (< ${MIN_CONTENTS_BYTES}). Possible fetch failure. Output kept for inspection.`);
    throw new Error(`contents.md too small (${contentsBytes} bytes) for ${repoName}`);
  }

  console.log(`Successfully pulled data for ${repoName}`);
}

/**
 * Print usage help and exit with code 1.
 */
function usage(): never {
  console.log('DeepWiki Pull — github-read-repo skill');
  console.log('Usage:');
  console.log('  tsx scripts/deepwiki.com.ts pull all                  # refresh all cached repos');
  console.log('  tsx scripts/deepwiki.com.ts pull <owner/repo|url>     # fetch one repo');
  process.exit(1);
}

/**
 * CLI entry point.
 */
async function main(): Promise<void> {
  // Junction-aware startup hint: the skill may be invoked through a junction /
  // symlink whose path differs from the real one the cache is written under.
  console.error(`技能根（真实路径）: ${fs.realpathSync(skillRoot())}`);

  const [, , sub, repoInput] = process.argv;
  if (sub !== 'pull' || !repoInput) usage();

  let targets: string[];
  try {
    if (repoInput === '*' || repoInput === 'all') {
      targets = listLocalRepos();
      if (targets.length === 0) {
        console.error('No cached repos found. Run `pull <owner/repo>` to fetch one first.');
        process.exit(1);
      }
    } else {
      const { owner, repo } = parseRepoInfo(repoInput);
      targets = [`${owner}/${repo}`];
    }
  } catch (error) {
    // Malformed repo input is a caller error → exit 1, not a runtime failure.
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }

  console.log('Connecting to DeepWiki MCP server...');
  const client = new McpClient(SERVER_URL);
  try {
    await client.initialize();
    console.log('Connected and initialized successfully.\n');
  } catch (error) {
    console.error('!!! MCP Client Error !!!');
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(2);
  }

  let failed = 0;
  for (const target of targets) {
    try {
      await pullRepo(client, target);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`\n!!! Failed to pull ${target}: ${msg}`);
      failed++;
    }
  }

  console.log(`\n=== Done: ${targets.length - failed}/${targets.length} repos pulled, ${failed} failed ===`);
  process.exit(failed > 0 ? 2 : 0);
}

// Allow importing this module as a library (its main() is never run then).
const isMain =
  process.argv[1] === fileURLToPath(import.meta.url) ||
  process.argv[1]?.endsWith('deepwiki.com.ts') ||
  process.argv[1]?.endsWith('deepwiki.com.js');

if (isMain) {
  main().catch((error) => {
    console.error('Fatal Error:', error instanceof Error ? error.message : String(error));
    process.exit(2);
  });
}
