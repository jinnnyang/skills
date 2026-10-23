import fs from "fs";
import path from "path";
import https from "https";
import tls from "node:tls";
import { fileURLToPath } from "node:url";
import { startElapsedReporter } from "./utils/progress.js";
import { createTunneledConnection } from "./utils/tunnel.js";

/**
 * Gitingest crawler — pull / status LLM-friendly codebase digests.
 *
 * Gitingest (https://gitingest.com/<user>/<repo>) turns any GitHub repo into a
 * single text digest of its codebase. This script caches the digest text
 * locally, mirroring gitdiagram.com.ts (both are "repo -> cached text" tools).
 *
 * Usage: npx tsx scripts/gitingest.com.ts <command> <target>
 *   pull   <user/repo|url|all>   Call /api/ingest, download the digest text
 *                                (digest.txt) + summary + tree into
 *                                <SITES_ROOT|data>/gitingest.com/<user>/<repo>/.
 *   status <user/repo|url|all>   Show repo info (commit/files/tokens) + local
 *                                cache state. Does NOT download the digest.
 *
 * Environment:
 *   GITHUB_PAT    GitHub personal access token, for private repos (optional).
 *   GITINGEST_PROXY / HTTPS_PROXY   HTTP CONNECT proxy for all requests.
 */

// Storage root anchored to the skill root (not process.cwd()), so `pull all`
// enumerates and writes to the same location regardless of where tsx is run.
function gtStoragePath(subPath: string = ""): string {
  // import.meta.dirname is this file's dir (scripts/); its parent is the skill root.
  const skillRoot = path.resolve(path.dirname(import.meta.dirname));
  const root = path.resolve(skillRoot, "data");
  return path.join(root, subPath);
}

/** Reject path-traversal / empty segments in user/repo. */
function validateSegment(seg: string): boolean {
  return seg !== "" && seg !== "." && seg !== ".." && !seg.includes("\\");
}

function parseRepoInfo(input: string): { user: string; repo: string } {
  // Handle URL: https://gitingest.com/user/repo or https://github.com/user/repo
  if (input.startsWith("http")) {
    const url = new URL(input);
    const parts = url.pathname.split("/").filter(Boolean);
    if (parts.length < 2 || !validateSegment(parts[0]!) || !validateSegment(parts[1]!)) {
      console.error("Invalid URL. Use gitingest.com/user/repo or github.com/user/repo.");
      process.exit(1);
    }
    return {
      user: parts[0]!,
      repo: parts[1]!.replace(/\.git$/, ""),
    };
  }

  // Handle user/repo
  const parts = input.split("/");
  if (parts.length < 2 || !validateSegment(parts[0]!) || !validateSegment(parts[1]!)) {
    console.error("Invalid repo format. Use user/repo or a full URL.");
    process.exit(1);
  }
  return {
    user: parts[0]!,
    repo: parts[1]!.replace(/\.git$/, ""),
  };
}

/**
 * List existing local repos as their on-disk path "user/repo".
 */
function listLocalRepos(): string[] {
  const root = gtStoragePath("gitingest.com");
  if (!fs.existsSync(root)) return [];
  const repos: string[] = [];
  for (const user of fs.readdirSync(root)) {
    const userDir = path.join(root, user);
    let isDir = false;
    try {
      isDir = fs.statSync(userDir).isDirectory();
    } catch {
      continue;
    }
    if (!isDir) continue;
    for (const repo of fs.readdirSync(userDir)) {
      try {
        if (fs.statSync(path.join(userDir, repo)).isDirectory()) {
          repos.push(`${user}/${repo}`);
        }
      } catch {
        continue;
      }
    }
  }
  return repos.sort();
}

// ---------------------------------------------------------------------------
// Network helpers (zero-dependency: node https + optional HTTP CONNECT proxy)
// ---------------------------------------------------------------------------

const PROXY_URL =
  process.env.GITINGEST_PROXY || process.env.HTTPS_PROXY || process.env.https_proxy || "";

interface HttpResult {
  status: number;
  body: string;
}

/** HTTPS GET/POST with optional HTTP CONNECT proxy tunneling (TLS-wrapped). */
function httpRequest(
  method: "GET" | "POST",
  rawUrl: string,
  headers: Record<string, string>,
  body?: string,
  timeoutMs = 30000,
  proxyUrl = "",
): Promise<HttpResult> {
  const u = new URL(rawUrl);
  const doRequest = (createConnection?: () => tls.TLSSocket) =>
    new Promise<HttpResult>((resolve, reject) => {
      const req = https.request(
        u,
        {
          method,
          headers: { ...headers },
          timeout: timeoutMs,
          ...(createConnection ? { createConnection } : {}),
        },
        (res) => {
          const chunks: Buffer[] = [];
          res.on("data", (c) => chunks.push(c as Buffer));
          res.on("end", () =>
            resolve({ status: res.statusCode ?? 0, body: Buffer.concat(chunks).toString("utf-8") }),
          );
        },
      );
      req.on("timeout", () => req.destroy(new Error(`timeout after ${timeoutMs}ms: ${rawUrl}`)));
      req.on("error", reject);
      if (body) req.write(body);
      req.end();
    });

  if (!proxyUrl) return doRequest();

  // CONNECT tunnel + explicit TLS wrap: Node does NOT TLS-wrap custom
  // createConnection sockets, so the raw socket from the tunnel would send
  // plaintext HTTP to :443 and get "400 plain HTTP request was sent to HTTPS
  // port". createTunneledConnection hands back an already-secured socket.
  return createTunneledConnection(u, proxyUrl, timeoutMs).then((createConnection) =>
    doRequest(createConnection),
  );
}

// ---------------------------------------------------------------------------
// Gitingest API
// ---------------------------------------------------------------------------

interface IngestResult {
  repo_url: string;
  short_repo_url: string;
  summary: string;
  digest_url: string;
  tree: string;
}

const GITHUB_PAT = process.env.GITHUB_PAT || "";
const DEFAULT_MAX_FILE_SIZE = 50_000;

/** Call /api/ingest. Returns metadata; the digest text is at digest_url. */
async function fetchIngest(repoName: string): Promise<IngestResult> {
  const repoUrl = `https://github.com/${repoName}`;
  const url = "https://gitingest.com/api/ingest";
  const headers: Record<string, string> = {
    "content-type": "application/json",
    "user-agent": "github-read-repo/2.0.0",
    accept: "*/*",
  };
  const body = JSON.stringify({
    input_text: repoUrl,
    max_file_size: DEFAULT_MAX_FILE_SIZE,
    ...(GITHUB_PAT ? { token: GITHUB_PAT } : {}),
  });
  const res = await httpRequest("POST", url, headers, body, 30000, PROXY_URL);
  if (res.status !== 200) {
    let detail = "";
    try {
      detail = JSON.parse(res.body).detail ?? "";
    } catch {
      detail = res.body.slice(0, 200);
    }
    throw new Error(`ingest failed (HTTP ${res.status}): ${typeof detail === "string" ? detail : JSON.stringify(detail).slice(0, 200)}`);
  }
  try {
    return JSON.parse(res.body) as IngestResult;
  } catch {
    throw new Error(`unexpected ingest body: ${res.body.slice(0, 200)}`);
  }
}

/** Download the full digest text from the CDN. */
async function downloadDigest(digestUrl: string): Promise<string> {
  const res = await httpRequest("GET", digestUrl, { "user-agent": "github-read-repo/2.0.0" }, undefined, 60000, PROXY_URL);
  if (res.status !== 200) throw new Error(`digest download failed (HTTP ${res.status})`);
  return res.body;
}

// ---------------------------------------------------------------------------
// Local cache helpers
// ---------------------------------------------------------------------------

function localPullInfo(localName: string): { date: string } | undefined {
  const [user, repo] = localName.split("/");
  const dir = gtStoragePath(path.join("gitingest.com", user!, repo!));
  try {
    const st = fs.statSync(path.join(dir, "digest.txt"));
    return { date: st.mtime.toISOString().slice(0, 10) };
  } catch {
    return undefined;
  }
}

/** Atomic write: write to temp file, then rename into place. */
function atomicWrite(dir: string, name: string, content: string): void {
  const tmp = path.join(dir, `.${name}.tmp`);
  fs.writeFileSync(tmp, content, "utf-8");
  fs.renameSync(tmp, path.join(dir, name));
}

// Extract commit / files / tokens from the summary text.
function parseSummary(summary: string): { commit: string; files: string; tokens: string } {
  const commit = summary.match(/Commit:\s*([0-9a-f]+)/)?.[1] ?? "";
  const files = summary.match(/Files analyzed:\s*([\d,]+)/)?.[1] ?? "";
  const tokens = summary.match(/Estimated tokens:\s*([\d.]+[kKmM]?)/)?.[1] ?? "";
  return { commit, files, tokens };
}

export interface FileIndexEntry {
  path: string;
  startLine: number;
  endLine: number;
  lines: number;
}

/**
 * Build a file → line-range index for a gitingest digest.
 *
 * A digest is: a leading directory tree, then each file's body introduced by a
 * bare `FILE: <path>` line. The index maps every `FILE:` marker to its 1-based
 * line (the file body runs from the line after the marker until the next
 * marker or EOF). Streams the string with indexOf so the multi-MB digest is
 * never split into a full line array.
 */
export function buildFileIndex(digest: string): FileIndexEntry[] {
  const files: FileIndexEntry[] = [];
  let current: FileIndexEntry | null = null;
  let line = 0;
  let start = 0;
  for (;;) {
    const nl = digest.indexOf("\n", start);
    const raw = nl === -1 ? digest.slice(start) : digest.slice(start, nl);
    line++;
    const m = raw.match(/^FILE:\s*(.+)$/);
    if (m) {
      if (current) {
        current.endLine = line - 1;
        current.lines = current.endLine - current.startLine;
      }
      current = { path: m[1]!.trim(), startLine: line, endLine: 0, lines: 0 };
      files.push(current);
    }
    if (nl === -1) break;
    start = nl + 1;
  }
  if (current) {
    current.endLine = line;
    current.lines = current.endLine - current.startLine;
  }
  return files;
}

async function pullRepo(localName: string): Promise<void> {
  const [user, repoRaw] = localName.split("/");
  const repoName = `${user!}/${repoRaw!.replace(/\.git$/, "")}`;
  const targetDir = gtStoragePath(path.join("gitingest.com", user!, repoRaw!));

  console.log(`Ingesting ${repoName}...`);
  const stopIngest = startElapsedReporter(`正在向 gitingest 提交 ${repoName} 的 ingest 请求`);
  let ingest: IngestResult;
  try {
    ingest = await fetchIngest(repoName);
  } finally {
    stopIngest();
  }

  console.log(`  summary: ${ingest.summary.split("\n")[0]}`);
  console.log(`  downloading digest (${ingest.summary.match(/Files analyzed:\s*([\d,]+)/)?.[1] ?? "?"} files)...`);
  const stopDigest = startElapsedReporter(`正在下载 ${repoName} 的 digest`);
  let digest: string;
  try {
    digest = await downloadDigest(ingest.digest_url);
  } finally {
    stopDigest();
  }

  console.log(`Saving files to ${targetDir}...`);
  fs.mkdirSync(targetDir, { recursive: true });

  const { commit, files, tokens } = parseSummary(ingest.summary);
  const meta = {
    repoUrl: ingest.repo_url,
    shortRepoUrl: ingest.short_repo_url,
    commit,
    filesAnalyzed: files,
    estimatedTokens: tokens,
    pulledAt: new Date().toISOString(),
    digestBytes: Buffer.byteLength(digest, "utf-8"),
  };

  atomicWrite(targetDir, "digest.txt", digest);
  atomicWrite(targetDir, "summary.md", ingest.summary);
  atomicWrite(targetDir, "tree.md", ingest.tree);

  // File → line-range index so digest reads can locate a file without scanning
  // the whole multi-MB digest (see read.md.ts `files` / `--path`).
  const index = buildFileIndex(digest);
  atomicWrite(
    targetDir,
    "files.json",
    JSON.stringify(
      { generatedAt: new Date().toISOString(), fileCount: index.length, files: index },
      null,
      2,
    ),
  );

  atomicWrite(targetDir, "meta.json", JSON.stringify(meta, null, 2));
  console.log(`Saved: digest.txt (${meta.digestBytes} bytes), summary.md, tree.md, files.json (${index.length} files), meta.json`);
  console.log(`\nSuccessfully pulled digest for ${repoName}`);
}

async function statusOne(localName: string): Promise<void> {
  const [user, repoRaw] = localName.split("/");
  const repoName = `${user!}/${repoRaw!.replace(/\.git$/, "")}`;
  console.log(`== ${repoName} ==`);
  const local = localPullInfo(localName);

  let ingest: IngestResult;
  try {
    ingest = await fetchIngest(repoName);
  } catch (e) {
    console.log(`  ingest API : error (${e instanceof Error ? e.message : String(e)})`);
    console.log("");
    return;
  }

  const { commit, files, tokens } = parseSummary(ingest.summary);
  const bits = [commit && `commit ${commit.slice(0, 8)}`, files && `${files} files`, tokens && `${tokens} tokens`]
    .filter(Boolean)
    .join(", ");
  console.log(`  ingest API : ok  (${bits})`);
  console.log(`  local copy : ${local ? `pulled ${local.date}` : "none"}`);

  if (!local) {
    console.log(`\n  → Not pulled yet:\n      npx tsx scripts/gitingest.com.ts pull ${repoName}`);
  }
  console.log("");
}

async function statusAll(): Promise<void> {
  const targets = listLocalRepos();
  if (targets.length === 0) {
    console.error("No local repos found. Run pull <user/repo> to fetch one first.");
    process.exit(1);
  }
  for (const t of targets) {
    await statusOne(t);
  }
}

const USAGE = `Gitingest crawler — pull / status LLM-friendly codebase digests

Usage: npx tsx scripts/gitingest.com.ts <command> <target>
       (legacy shorthand: a bare "user/repo" or URL is treated as "pull")

Commands:
  pull  <user/repo|url|all>   Call /api/ingest and download the digest text
                              (digest.txt + summary.md + tree.md + meta.json)
                              into <SITES_ROOT|data>/gitingest.com/<user>/<repo>/.
  status <user/repo|url|all>  Show repo info (commit/files/tokens) + local cache.
                              Does not download the digest.

Environment:
  GITHUB_PAT    GitHub PAT for private repos (optional, sent as token field)
  GITINGEST_PROXY / HTTPS_PROXY   HTTP CONNECT proxy for all requests

Examples:
  npx tsx scripts/gitingest.com.ts status encode/fastapi
  npx tsx scripts/gitingest.com.ts pull ahmedkhaleel2004/gitdiagram
  npx tsx scripts/gitingest.com.ts pull all`;

async function main() {
  // Junction-aware startup hint: the skill may be invoked through a junction
  // whose path differs from the real path the cache is written under.
  console.error(`技能根（真实路径）: ${fs.realpathSync(path.resolve(path.dirname(import.meta.dirname)))}`);

  const argv = process.argv.slice(2);
  const [cmd, targetRaw] = argv;
  const COMMANDS = ["pull", "status"];

  if (cmd === "help" || cmd === "--help" || cmd === "-h") {
    console.log(USAGE);
    process.exit(0);
  }

  // Legacy shorthand: a bare "user/repo" or URL means pull.
  const command = targetRaw ? (cmd as string) : "pull";
  const target = targetRaw ?? cmd;

  if (!target || !COMMANDS.includes(command) || (!targetRaw && cmd !== undefined && COMMANDS.includes(cmd))) {
    console.log(USAGE);
    process.exit(target ? 0 : 1);
  }

  if (command === "pull") {
    let targets: string[];
    if (target === "*" || target === "all") {
      targets = listLocalRepos();
      if (targets.length === 0) {
        console.error("No local repos found. Run pull <user/repo> to fetch one first.");
        process.exit(1);
      }
    } else {
      const { user, repo } = parseRepoInfo(target);
      targets = [`${user}/${repo}`];
    }

    let failed = 0;
    for (const t of targets) {
      try {
        await pullRepo(t);
      } catch (e) {
        console.error(`\n!!! Failed to pull ${t}: ${e instanceof Error ? e.message : String(e)}`);
        failed++;
      }
    }
    console.log(`\n=== Done: ${targets.length - failed}/${targets.length} repos pulled, ${failed} failed ===`);
    // Runtime/network failures exit 2 per SKILL.md's exit-code contract
    // (0 success, 1 input error, 2 runtime / I/O / network).
    if (failed > 0) process.exit(2);
    return;
  }

  if (command === "status") {
    if (target === "*" || target === "all") {
      await statusAll();
    } else {
      const { user, repo } = parseRepoInfo(target);
      await statusOne(`${user}/${repo}`);
    }
    return;
  }
}

// Allow importing this module as a library (main() never runs then).
const isMain =
  process.argv[1] === fileURLToPath(import.meta.url) ||
  process.argv[1]?.endsWith("gitingest.com.ts") ||
  process.argv[1]?.endsWith("gitingest.com.js");

if (isMain) {
  main().catch((error) => {
    console.error("Fatal Error:", error instanceof Error ? error.message : String(error));
    process.exit(2);
  });
}
