# github-read-repo

Pull a GitHub repo's understanding material — DeepWiki docs, Gitingest code digest, or GitDiagram architecture diagram — then read or edit it **section-by-section** so you never stuff a whole large document into context.

It pairs four TypeScript CLIs:

- **`deepwiki.com.ts`** — fetch a repo's wiki `structure.md` + `contents.md` and cache them locally.
- **`gitingest.com.ts`** — call Gitingest's `/api/ingest` and cache the full code digest (`digest.txt`) + `summary.md` + `tree.md` + `files.json` (file → line-range index of the digest).
- **`gitdiagram.com.ts`** — fetch a repo's Mermaid architecture diagram (`diagram.mmd`) + `explanation.md`, auto-triggering generation via SSE when none exists.
- **`read.md.ts`** — parse a cached (or any) Markdown file with [`md2ast`](https://github.com/jinnnyang/md2ast) and pull out / replace exactly one section at a time.

All are fully typed TypeScript with complete TSDoc, run via `tsx`, and depend only on the zero-dependency MCP client in `scripts/utils/mcp/mcp-client.ts` (used by deepwiki).

## Layout

```
github-read-repo/
├── SKILL.md               # Skill usage guide (Chinese-primary, English commands)
├── README.md              # This file
├── package.json           # deps: md2ast, tsx, typescript, @types/node
├── tsconfig.json          # strict ESM config
├── .gitignore             # ignores data/, node_modules/, *.backup.*
├── data/                  # runtime cache (gitignored), keyed by source
│   ├── deepwiki.com/<owner>/<repo>/
│   │   ├── structure.md   # DeepWiki page outline
│   │   └── contents.md    # DeepWiki full document
│   ├── gitingest.com/<owner>/<repo>/
│   │   ├── digest.txt     # full code digest (dir structure + file bodies)
│   │   ├── summary.md     # repo/commit/files/tokens summary
│   │   ├── tree.md        # directory structure text
│   │   ├── files.json     # file → line-range index (generated at pull)
│   │   └── meta.json      # pull metadata
│   └── gitdiagram.com/<owner>/<repo>/
│       ├── diagram.mmd    # Mermaid architecture diagram
│       ├── explanation.md # LLM-generated explanation (markdown)
│       └── meta.json      # pull metadata
└── scripts/
    ├── deepwiki.com.ts    # pull command (DeepWiki MCP)
    ├── gitingest.com.ts   # pull command (Gitingest REST)
    ├── gitdiagram.com.ts  # pull/status command (GitDiagram REST + SSE)
    ├── read.md.ts         # outline / read / edit commands
    ├── lib/ast.ts         # md2ast helpers: outline + section location
    └── utils/mcp/
        └── mcp-client.ts  # zero-dep Streamable-HTTP MCP client
```

## Prerequisites

- Node.js 20.11+ (for `import.meta.dirname`).
- Network access: DeepWiki `https://mcp.deepwiki.com/mcp`, Gitingest `https://gitingest.com`, GitDiagram `https://gitdiagram.com` (pull steps only; read/edit are offline).
- If the machine cannot reach the internet directly, set `HTTPS_PROXY=http://host:port` (HTTP CONNECT proxy, e.g. Clash's `http://127.0.0.1:7897`). All three sources honor it: Gitingest also accepts `GITINGEST_PROXY`, GitDiagram `GITDIAGRAM_PROXY`, and the DeepWiki MCP client `MCP_PROXY`. Requests go through a CONNECT tunnel with an explicit TLS handshake (`scripts/utils/tunnel.ts`), so no extra config is needed.

Install once (from the skill directory):

```bash
npm install
```

All commands are anchored to the skill directory (not `process.cwd()`), so they behave identically regardless of where you invoke them.

## Pull

```bash
# DeepWiki docs
npx tsx scripts/deepwiki.com.ts pull owner/repo
npx tsx scripts/deepwiki.com.ts pull https://github.com/owner/repo
npx tsx scripts/deepwiki.com.ts pull all        # refresh every cached repo

# Gitingest code digest (instant, no quota gate)
npx tsx scripts/gitingest.com.ts pull owner/repo
npx tsx scripts/gitingest.com.ts pull all

# GitDiagram architecture diagram (SSE generation when uncached)
npx tsx scripts/gitdiagram.com.ts status owner/repo   # check first
npx tsx scripts/gitdiagram.com.ts pull owner/repo
```

- Writes atomically (temp file + rename) to `data/<source>/<owner>/<repo>/`.
- DeepWiki `contents.md` under 10 KB is treated as a failed fetch (warn + error).
- Gitingest pull also generates `files.json` — a file → line-range index of the digest (used by `read.md.ts files` and `read --path`).
- GitDiagram env: `GITHUB_PAT` for private repos (optional), `GITDIAGRAM_PROXY`/`HTTPS_PROXY` for a proxy. Gitingest env: `GITINGEST_PROXY`/`HTTPS_PROXY`. DeepWiki MCP client env: `MCP_PROXY`/`HTTPS_PROXY`. GitDiagram follows 3xx `Location` redirects (up to 3 hops; 301/302/303 downgrade POST→GET, 307/308 preserve method + body) on both its REST and SSE calls.

## Read & Edit

```bash
# Outline (heading tree with line numbers); --source optional, auto-probed
npx tsx scripts/read.md.ts outline --repo owner/repo
npx tsx scripts/read.md.ts outline --repo owner/repo --source gitingest

# Read one section by title (exact match preferred, fuzzy otherwise)
npx tsx scripts/read.md.ts read --repo owner/repo --section "API Reference"

# Read a line range (fallback; also for digest.txt / diagram.mmd)
npx tsx scripts/read.md.ts read --file data/gitingest.com/owner/repo/digest.txt --range "10-40"

# List digest files → start line (from files.json), then read one by name
npx tsx scripts/read.md.ts files --file data/gitingest.com/owner/repo/digest.txt --filter "src/"
npx tsx scripts/read.md.ts read --file data/gitingest.com/owner/repo/digest.txt --path "src/main.ts"

# Cap output lines (avoid SIGPIPE when piping)
npx tsx scripts/read.md.ts read --repo owner/repo --section "X" --limit 80

# Edit — dry-run by default
npx tsx scripts/read.md.ts edit --repo owner/repo --section "Installation" --replace "## Installation\nNew text"

# Apply the edit (backs up first unless --no-backup)
npx tsx scripts/read.md.ts edit --repo owner/repo --section "Installation" --replace "..." --write
```

### How the commands read their content

Both scripts operate on **local files** — they never hit the network at read time. The content comes from exactly one of two sources:

| Source | Flag | Resolved path |
|--------|------|---------------|
| Skill cache (pull first) | `--repo <owner/repo>` | `data/<source>/<owner>/<repo>/` markdown main file |
| Arbitrary file | `--file <path>` | absolute path, or relative to the skill dir |

`--source` maps to the markdown main file: deepwiki→`contents.md`, gitdiagram→`explanation.md`, gitingest→`summary.md`. When `--source` is omitted, it is auto-probed in the order deepwiki → gitdiagram → gitingest (first source with that repo cached wins; the chosen source is announced on stderr), so plain `--repo owner/repo` keeps working.

### Flags

| Flag | Applies to | Meaning |
|------|-----------|---------|
| `--repo <owner/repo>` | all | Resolve to `data/<source>/<owner>/<repo>/` markdown main file |
| `--source <deepwiki\|gitdiagram\|gitingest>` | all | Pick the source (auto-probed when omitted) |
| `--file <path>` | all | Use an arbitrary path (relative to skill dir or absolute) |
| `--section "<title>"` | read, edit | Locate a section by heading (exact normalized match first) |
| `--range "start-end"` | read | Slice lines `start..end` (1-indexed, inclusive) |
| `--path <file>` | read | Read one file out of a gitingest digest by name (via files.json) |
| `--filter <substr>` | files | List only digest files whose path contains the substring |
| `--limit <N>` | read | Cap output at N lines |
| `--replace <text>` | edit | Replacement markdown for the whole section (heading included) |
| `--write` | edit | Actually apply the edit (default is dry-run) |
| `--no-backup` | edit | Skip the `<file>.backup.<timestamp>` backup |

`--file` and `--repo` are mutually exclusive; one is required. `--source` only pairs with `--repo`. `read` requires exactly one of `--section`/`--range`/`--path`; `edit` only supports `--section`; `files` only supports `--file`/`--repo`/`--source`/`--filter`.

### Section semantics

A "section" spans from its heading line down to the next heading of the **same or shallower** depth (sibling or ancestor). Title matching is **normalized, exact-first matching**: an exact normalized match always wins; otherwise a fuzzy score ranks the rest (case-, whitespace-, and punctuation-insensitive — backticks, brackets, parens stripped). If nothing matches, a ranked candidate list (with line numbers and similarity scores) is printed.

When several headings tie, the first one with a **non-empty body** is chosen. This avoids landing on DeepWiki's empty `# Page: <title>` separator stubs (which sit right before the real `# <title>` heading) — an empty match falls through to the next ranked candidate.

## Typical workflow

```bash
# 1. Pick a source and pull the repo
npx tsx scripts/deepwiki.com.ts pull Tencent/ncnn        # docs
npx tsx scripts/gitingest.com.ts pull Tencent/ncnn       # code digest
npx tsx scripts/gitdiagram.com.ts pull Tencent/ncnn      # architecture diagram

# 2. Get the outline to find the section you want
npx tsx scripts/read.md.ts outline --repo Tencent/ncnn

# 3. Read just that section (keeps context small)
npx tsx scripts/read.md.ts read --repo Tencent/ncnn --section "Getting Started Guide"

# 3b. Read raw code from the digest by file name or line range
npx tsx scripts/read.md.ts files --file data/gitingest.com/Tencent/ncnn/digest.txt --filter "src/"
npx tsx scripts/read.md.ts read --file data/gitingest.com/Tencent/ncnn/digest.txt --path "src/main.ts"
npx tsx scripts/read.md.ts read --file data/gitingest.com/Tencent/ncnn/digest.txt --range "10-40"

# 4. Preview an edit, then apply it (markdown sources only)
npx tsx scripts/read.md.ts edit --repo Tencent/ncnn --section "X" --replace "New text"
npx tsx scripts/read.md.ts edit --repo Tencent/ncnn --section "X" --replace "New text" --write
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | Input error (bad args, missing file, section not found, malformed repo) |
| 2    | Runtime / I/O / network failure |

## Implementation notes

- `lib/ast.ts` wraps `md2ast`: it flattens headings into an outline and locates a section by char offsets (`char_num`) between sibling/ancestor headings, then slices the raw source string — no re-rendering, so edits preserve the rest of the document byte-for-byte.
- Section scoring is exact-first: a normalized exact match always outranks fuzzy candidates (whose scores are capped below 1.0), so `--section "Overview"` cannot be stolen by `Diagram: Bend Syntax Overview`; ties prefer shallower headings, then document order.
- Edits preserve the section's original trailing whitespace, so a replacement that omits a trailing newline never glues onto the following section.
- A fresh `MarkdownParser` is created per document because it carries per-document state (`references`, `warnings`).
- `read.md.ts` auto-probes sources when `--source` is omitted and announces the pick on stderr. Missing caches trigger a scan of `data/` so the error lists where the repo actually lives (e.g. a non-standard layout) instead of a bare "pull it first".
- All CLIs print the resolved skill root (`fs.realpathSync`) to stderr at startup, so junction/symlink installs never hide where the cache lands.
- Long blocking fetches (DeepWiki MCP, digest download, SSE) report elapsed time via `scripts/utils/progress.ts`; wiki-builder's crawlers share the same helper at `utils/progress.ts`.
- Proxy support is centralized in `scripts/utils/tunnel.ts`: a CONNECT handshake to the proxy, then the raw socket is wrapped with `tls.connect` and only handed to `https.request` after `secureConnect`. Without that explicit TLS wrap Node sends plaintext HTTP to :443 behind a proxy (`400 plain HTTP request was sent to HTTPS port`). Wiki-builder's crawlers share the same helper at `utils/tunnel.ts`.
- Exit codes: `0` success, `1` input error, `2` runtime / I/O / network (pull failures exit 2). On Windows, truncating output with `| Select-Object -First N` yields `$LASTEXITCODE -1` (SIGPIPE) — expected; use `--limit` instead.
