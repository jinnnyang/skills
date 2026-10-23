/**
 * ast.ts — Markdown AST utilities built on top of the `md2ast` package.
 *
 * This module centralizes everything that touches the parsed Markdown tree so
 * the CLI entry points stay thin:
 *
 *  - {@link parseMarkdown} wraps the md2ast parser.
 *  - {@link buildHeadingOutline} flattens every heading into a scannable,
 *    indented outline with 1-based line numbers (for the `outline` command).
 *  - {@link locateSection} finds the section a heading owns — from the heading
 *    line down to the next heading of the same or shallower depth — and returns
 *    the raw markdown slice covering exactly that section (for `read`/`edit`).
 *  - {@link findSectionCandidates} is the fuzzy fallback used when an exact
 *    title match fails; it scores headings by normalized text similarity.
 *
 *  - {@link findBestSectionWithContent} is the content-aware variant used by
 *    `read`/`edit`: it skips empty-body sections (e.g. DeepWiki `# Page: X`
 *    separators) and falls through to the next ranked candidate.
 * All matching is done on *normalized* title text (lower-cased, trimmed,
 * whitespace-collapsed, punctuation stripped) so a user can type a partial or
 * differently-punctuated heading and still land on the right section.
 */

import type { Document, Heading, AnyNode, Text } from 'md2ast';
import { MarkdownParser } from 'md2ast';

/** A single heading entry in an outline. `line` and `char` are 1-based / 0-based source coordinates. */
export interface OutlineEntry {
  /** Heading depth (1 = H1 … 6 = H6). */
  depth: number;
  /** Plain-text title of the heading (inline markdown stripped). */
  title: string;
  /** 1-based line number where the heading starts. */
  line: number;
  /** 0-based absolute character offset where the heading starts. */
  char: number;
}

/** A located section: the heading that owns it plus the raw markdown slice. */
export interface Section {
  /** The heading that opens the section. */
  heading: OutlineEntry;
  /** Raw markdown of the section body, from the heading line to the next boundary. */
  content: string;
  /** 0-based char offset where the section starts (== heading.char). */
  startChar: number;
  /** 0-based char offset just past the last char of the section. */
  endChar: number;
  /** 1-based line where the section starts. */
  startLine: number;
  /** 1-based line where the section ends (inclusive), or -1 if it runs to EOF. */
  endLine: number;
}

/**
 * Parse a Markdown source string into an AST document.
 *
 * A fresh `MarkdownParser` is created on every call because the parser carries
 * per-document state (`references`, `warnings`); sharing one across documents
 * would leak state.
 *
 * @param source Raw markdown text.
 * @returns The parsed document root.
 */
export function parseMarkdown(source: string): Document {
  return new MarkdownParser().parse(source);
}

/**
 * Extract the plain-text title of a heading by recursively walking its inline
 * children, dropping markdown syntax but keeping the visible text.
 *
 * @param heading The heading node to read.
 * @returns The visible title text, trimmed and whitespace-collapsed.
 */
export function headingText(heading: Heading): string {
  const parts: string[] = [];
  collectText(heading, parts);
  return collapse(parts.join(''));
}

/**
 * Recursively collect visible text from an inline node tree into `out`.
 *
 * Handles `text`, `inlineCode`, `link`/`emphasis`/`strong`/`delete` (descend
 * into children), and `image` (uses its `alt`). Any unknown leaf is skipped.
 *
 * @param node The node to walk.
 * @param out Accumulator array the text fragments are pushed into.
 */
function collectText(node: AnyNode, out: string[]): void {
  switch (node.type) {
    case 'text':
    case 'inlineCode':
      out.push((node as Text).value);
      return;
    case 'image':
      if (node.alt) out.push(node.alt);
      return;
    default:
      break;
  }
  // Any container (heading, link, emphasis, strong, delete, …) descends into
  // its children to reach the visible text leaves.
  if ('children' in node && Array.isArray(node.children)) {
    for (const child of node.children) collectText(child, out);
  }
}

/**
 * Collapse runs of whitespace and trim a string — the normalization used for
 * title matching.
 *
 * @param s Raw string.
 * @returns A single-line, trimmed string.
 */
function collapse(s: string): string {
  return s.replace(/\s+/g, ' ').trim();
}

/**
 * Recursively collect every heading node in document order into `out`, along
 * with its computed source coordinates.
 *
 * @param node The node (or document root) to scan.
 * @param out Accumulator array.
 */
function collectHeadings(node: AnyNode, out: OutlineEntry[]): void {
  if (node.type === 'heading') {
    out.push({
      depth: node.depth,
      title: headingText(node),
      line: (node.line_num ?? 0) + 1,
      char: node.char_num ?? 0,
    });
    // A heading's own inline children never contain nested headings, but keep
    // walking for safety so a heading inside a blockquote is still found.
  }
  if ('children' in node && Array.isArray(node.children)) {
    for (const child of node.children) collectHeadings(child, out);
  }
}

/**
 * Build a flattened heading outline for a document, in document order.
 *
 * @param doc The parsed document.
 * @returns Every heading in source order with its coordinates.
 */
export function buildHeadingOutline(doc: Document): OutlineEntry[] {
  const out: OutlineEntry[] = [];
  collectHeadings(doc, out);
  return out;
}

/**
 * Normalize a string for fuzzy matching: lower-case, strip markdown-significant
 * punctuation, and collapse whitespace.
 *
 * @param s The string to normalize.
 * @returns A comparison-ready key.
 */
function normalizeKey(s: string): string {
  return collapse(s)
    .toLowerCase()
    .replace(/[`*_~#[\]()|\\<>]/g, '');
}

/**
 * Score how well `heading` matches `query`. Higher is better.
 *
 * Exact normalized equality yields the max score (1.0) and is the only way to
 * reach it: fuzzy bonuses (substring + token overlap) are capped below 1.0 so
 * a perfect title match can never lose to a longer, token-heavy heading
 * (e.g. `Diagram: Bend Syntax Overview` vs a query of `Overview`).
 * All scores stay small so ranking stays deterministic.
 *
 * @param heading The candidate heading title.
 * @param query The normalized search string.
 * @returns A non-negative similarity score (1 for exact, <1 otherwise).
 */
function scoreHeading(heading: string, query: string): number {
  const title = normalizeKey(heading);
  if (title === query) return 1;
  let score = 0;
  if (title.includes(query)) score += 0.6;
  if (query.includes(title)) score += 0.3;
  const titleTokens = title.split(/\s+/).filter(Boolean);
  const queryTokens = query.split(/\s+/).filter(Boolean);
  if (titleTokens.length && queryTokens.length) {
    const hits = queryTokens.filter((t) => titleTokens.includes(t)).length;
    score += hits / queryTokens.length;
  }
  // Exact matches (1.0) must always win; fuzzy matches are capped strictly below.
  return Math.min(score, 0.99);
}

/**
 * Find the best-matching heading for a user-supplied section title.
 *
 * Exact normalized matches are always preferred and returned first; only when
 * no exact match exists are headings scored by {@link scoreHeading} and the
 * best positive-score match returned.
 *
 * @param entries The heading outline to search.
 * @param title The user-supplied section title.
 * @returns The best {@link OutlineEntry} or `null` if nothing scores.
 */
export function findBestSection(entries: OutlineEntry[], title: string): OutlineEntry | null {
  const query = normalizeKey(title);
  if (!query) return null;
  // Pass 1: exact normalized match wins outright (document order → first is earliest).
  for (const entry of entries) {
    if (normalizeKey(entry.title) === query) return entry;
  }
  // Pass 2: fuzzy scoring.
  let best: OutlineEntry | null = null;
  let bestScore = 0;
  for (const entry of entries) {
    const s = scoreHeading(entry.title, query);
    if (s > bestScore) {
      bestScore = s;
      best = entry;
    }
  }
  return bestScore > 0 ? best : null;
}

/**
 * List all candidate headings that plausibly match a title (score > 0), sorted
 * best-first. Used to present the user a shortlist when no strong match exists.
 *
 * @param entries The heading outline.
 * @param title The user-supplied section title.
 * @param limit Maximum number of candidates to return.
 * @returns Ranked candidates, each with its score.
 */
export function findSectionCandidates(
  entries: OutlineEntry[],
  title: string,
  limit = 5,
): Array<OutlineEntry & { score: number }> {
  const query = normalizeKey(title);
  if (!query) return [];
  return entries
    .map((entry) => ({ ...entry, score: scoreHeading(entry.title, query) }))
    .filter((entry) => entry.score > 0)
    // Exact (1.0) always ranks above fuzzy (<1); then score; ties prefer
    // shallower headings (#1/#2 main titles over deep #### sub-diagrams),
    // then document order.
    .sort((a, b) => b.score - a.score || a.depth - b.depth || a.line - b.line)
    .slice(0, limit);
}

/**
 * Determine whether a section has any body content beyond its own heading.
 *
 * A section is considered *empty* when everything after the heading line is
 * blank or whitespace — i.e. the heading is a pure structural stub. DeepWiki's
 * `contents.md` uses `# Page: <title>` separator headings that own such empty
 * sections, sitting immediately before the real `# <title>` section.
 *
 * @param section A located section.
 * @returns `true` if the section has no body text (just its heading + blanks).
 */
export function isSectionEmpty(section: Section): boolean {
  // `content` starts at the heading line; the body is everything after it.
  const body = section.content.split('\n').slice(1).join('\n');
  return body.trim() === '';
}

/**
 * Find the best-matching heading *with a non-empty body*, falling through to the
 * next ranked candidate when a higher-scoring match is an empty stub.
 *
 * When several headings tie on similarity (e.g. a `# Page: X` separator and the
 * real `# X` heading normalize to the same key), the plain {@link findBestSection}
 * returns the first — which may be the empty separator. This variant walks the
 * ranked candidate list in score order, skips empty-body sections, and returns
 * the first one that actually has content. If every candidate is empty it falls
 * back to the overall best match so the caller still gets a usable result.
 *
 * @param source The raw markdown (needed to compute section bodies).
 * @param outline The heading outline.
 * @param title The user-supplied section title.
 * @returns The best content-bearing {@link OutlineEntry}, or `null` if nothing
 *   scores at all.
 */
export function findBestSectionWithContent(
  source: string,
  outline: OutlineEntry[],
  title: string,
): OutlineEntry | null {
  const candidates = findSectionCandidates(outline, title);
  if (candidates.length === 0) return null;

  let fallback: OutlineEntry | null = null;
  for (const cand of candidates) {
    if (!fallback) fallback = cand;
    const section = locateSection(source, outline, cand);
    if (section && !isSectionEmpty(section)) return cand;
  }
  return fallback;
}

/**
 * Compute the end boundary of the section opened by `start` within `outline`.
 *
 * A section ends just before the next heading whose depth is the same as or
 * shallower than the opener (a sibling or ancestor). If no such heading exists,
 * the section runs to the end of the document (returned as `null`).
 *
 * @param outline The full heading outline.
 * @param startIndex Index of the opening heading in `outline`.
 * @returns The boundary {@link OutlineEntry} or `null` for EOF.
 */
function nextSectionBoundary(outline: OutlineEntry[], startIndex: number): OutlineEntry | null {
  const depth = outline[startIndex]?.depth ?? 0;
  for (let i = startIndex + 1; i < outline.length; i++) {
    const entry = outline[i];
    if (entry && entry.depth <= depth) return entry;
  }
  return null;
}

/**
 * Locate the section owned by the given heading.
 *
 * The section content is the raw source slice starting at the heading's char
 * offset and ending at the next same-or-shallower heading's char offset (or the
 * end of the document). The slice therefore includes the heading line itself.
 *
 * @param source The original raw markdown.
 * @param outline The heading outline for the document.
 * @param heading The opening heading.
 * @returns A {@link Section}, or `null` if the heading is unknown.
 */
export function locateSection(
  source: string,
  outline: OutlineEntry[],
  heading: OutlineEntry,
): Section | null {
  const index = outline.findIndex(
    (e) => e.line === heading.line && e.title === heading.title && e.depth === heading.depth,
  );
  if (index < 0) return null;
  const boundary = nextSectionBoundary(outline, index);
  const startChar = heading.char;
  const endChar = boundary ? boundary.char : source.length;

  // Derive 1-based start/end lines from the char offsets.
  const startLine = heading.line;
  let endLine = -1;
  if (boundary) {
    // Boundary char offset belongs to the boundary heading's line; the section
    // body ends on the line before it.
    endLine = Math.max(startLine, boundary.line - 1);
  } else {
    endLine = source.length > 0 ? countLines(source) : startLine;
  }

  return {
    heading,
    content: source.slice(startChar, endChar),
    startChar,
    endChar,
    startLine,
    endLine,
  };
}

/**
 * Count the number of lines in a string (a trailing newline does not add a line).
 *
 * @param source The source text.
 * @returns The 1-based line count.
 */
function countLines(source: string): number {
  if (source.length === 0) return 0;
  const matches = source.match(/\n/g);
  return (matches ? matches.length : 0) + 1;
}

/**
 * Split raw source into 1-indexed lines for the `--range "start-end"` fallback.
 *
 * @param source Raw markdown.
 * @returns An array where index 1 is the first line (index 0 is unused).
 */
export function splitLines(source: string): string[] {
  const lines = source.split('\n');
  lines.unshift(''); // 1-indexed: lines[1] is the first line
  return lines;
}
