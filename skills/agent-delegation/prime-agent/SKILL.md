---
name: prime-agent
description: "Delegate tasks to prime-agent CLI (coding, MCP)."
license: MIT
metadata:
  version: 2.3.0
  author: Hermes Agent + Teknium
  platforms: [linux, macos, windows]
  hermes:
    tags: [Coding-Agent, Prime-Intellect, Delegation, Verification, MCP, Profiles]
---

# prime-agent delegation

Wrap the prime-agent CLI so delegation succeeds on the first try and its
reports are trusted only after verification.

## When to Use

- User asks to delegate/委托 a task to prime — coding first (implement, refactor, fix, run tests), but any self-contained task it can do in a terminal: research, file processing, long-running scripts.
- Mentions prime-agent, prime_spawn, "HEADLESS_OK", "No models available", silent exit after "✓ ready", aptapi/AptAPI provider issues, "--print 静默退出".
- A prime-agent headless run fails silently, hangs after producing output, or its self-reported results need verification.
- How to install skills (markdown vs Python), what isolation they get, and how the continual-harness self-improvement (`rlm.harness` CRUD, `/refine`) differs from file skills: `references/skills.md`.
- How to isolate prime-agent state — separate memory / skills / MCP servers per project or role; which config file/directory a skill or server comes from.
- How to modify prime-agent's system prompt (APPEND_SYSTEM.md, --system-prompt, model-prompts.toml, prompt layers).
- How to configure prime-agent MCP servers (add/list/get/remove, HTTP vs stdio, OAuth).

**Don't use for:** delegating to Claude Code (`claude-code`), Codex (`codex`), or OpenCode (`opencode`) — sibling skills.

Isolation of memory / skills / MCP servers per role: see
`references/isolation-and-resources.md`. Two rules worth knowing before you
open it — copy `auth.json` into each profile, never symlink it (auth writes
rename onto the path and eat the link); and prove a partition with
`prime-agent prompt` grep probes plus a cross-profile `rlm.get_harness_state()`
check rather than trusting the directory layout.

## Why this is finicky

The CLI surface is tiny (`--print`, `--autonomous`). All friction lives in
four places: provider plumbing that fails with misleading errors, terminal
pipe semantics that make success look like failure, a report-only-at-end
design that gives zero progress signal, and LLM-report drift on long runs.
Each has a known fix; the wrapper script bakes in the mechanical ones.

## Role / workspace isolation

No `profile`/`workspace`/`role` flag exists. Memory, harness skills, sessions and
the daemon socket follow `PRIME_AGENT_CODING_AGENT_DIR`; project skills and project
settings follow `--cwd`; MCP servers follow `settings.json` (global + project,
deep-merged). Verify any partition with `prime-agent prompt`, never
`prime-agent config` (interactive TUI, never returns in a non-tty shell).

Layout, discovery order, `!`/`+`/`-` skill filters, MCP merge semantics, and the
Windows `HOME` path trap: `references/isolation-and-resources.md`.

## MCP servers: add / list / get / remove

CLI (writes `mcpServers` in the resolved agent-dir `settings.json` — set
`PRIME_AGENT_CODING_AGENT_DIR` first for profiles):

```bash
prime-agent mcp list                  # list all
prime-agent mcp get <name>            # show one
prime-agent mcp add <name> --url <url> [--bearer-token-env-var <env>|--oauth] [--force]  # HTTP
prime-agent mcp add <name> [--cwd <dir>] [--env CHILD=SOURCE] -- <command> [args...]     # stdio
prime-agent mcp remove <name>         # delete
```

No `update` — change = remove + add (or hand-edit `settings.json`).
stdio flags: `--cwd` = child working dir, `--env CHILD=SOURCE` = pass host env
var SOURCE as CHILD. `--oauth` triggers browser OAuth on first use; in TUI
`/mcp login` / `/mcp logout` run the client-side flow and persist to the shared
auth store the daemon sessions read.

Verify with `prime-agent prompt | grep 'Enabled generic MCP servers'` — the
prompt only lists servers whose command/URL actually resolves. The
`the mcpServers setting must be a JSON object` failure and rerun fix are in
`references/isolation-and-resources.md`, along with global-vs-project merge
semantics.

## System prompt modification

Five routes, least invasive first: `APPEND_SYSTEM.md` (global
`~/.prime/agent/` or project `.prime/agent/`, appended to the dynamic tail) →
CLI `--system-prompt` (replaces static layers) / `--append-system-prompt` →
per-model `model-prompts.toml` in the agent dir → edit built-in layer files
(compile-time, rebuild; parity-diff evidence required) → settings.json
`prompts` array. Verify any change with `prime-agent prompt` (no tokens) —
grep the plain output for content, `--json` segments are metadata-only.
Details and file paths: `references/system-prompt.md`.

## Routing

| Situation | Do |
|---|---|
| Hermes prime-delegate plugin installed (prime_spawn in tool catalog) | Use `prime_spawn` directly — no wrapper script needed; it handles cwd/timeout/notification. Default timeout_s=600 is the WHOLE-task wall clock and there is no cancel: pass timeout_s:900 for anything non-trivial. prime_spawn is the primary route even when delegate.sh is missing from the skills dir.
| User says '让prime修改/委托prime, 你负责验收' | prime does the edit; you NEVER apply it yourself. Review flow: prime_status(full_output) → git diff to eyeball hunks → syntax check / small runtime probe to verify the actual claim (e.g. simulate the failure path) → report. Trust the diff, not prime's self-report. Pass large tasks an explicit `timeout_s` (default 600 is a wall-clock kill with no cancel). |
| `scripts/delegate.sh` missing from this skill's directory | Don't hunt for it: fall back to `prime_spawn`. |
| Delegate a self-contained task | One-shot delegate (below) |
| Task needs build/test gates | One-shot with `--autonomous` |
| `No models available` / silent exit / provider missing | `references/known_issues.md` (ISSUE-001/003) |
| Run hung after output / exit 124 | ISSUE-004 — output complete, exit unreliable |
| Run timed out / killed | ISSUE-002 — disk work survives; re-dispatch a finishing task |
| Suspicious "all tests pass" report | ISSUE-006 — run the Verification protocol |
| Provider "Unknown" in session, or `spawn session worker ... rejected` after reinstall/uninstall | ISSUE-008 — stale process; kill it, clear leases |

## One-shot delegate

Use `scripts/delegate.sh` — it fixes the MSYS path trap, the no-exit
trap, and the timeout strategy in one place (ISSUES 003/004/002):

```bash
bash <skill-path>/scripts/delegate.sh "Reply with exactly: HEADLESS_OK"
bash <skill-path>/scripts/delegate.sh -t 3600 -m norm "task prompt"
bash <skill-path>/scripts/delegate.sh -a -n 80 "task prompt"   # autonomous
```

Success = non-empty captured output; exit codes are reported but not
trusted (ISSUE-004). From PowerShell/cmd the stock launcher works:
`prime-agent --provider aptapi --model norm --print "<task>"`.

For anything long-running, background it and write the task brief to a
file first — see `references/brief-template.md`:

```bash
bash delegate.sh "Read the brief at <abs path> and execute it completely" \
  > run.log 2>&1 &        # or the terminal tool's background mode
```

## Brief discipline

prime-agent sees none of this conversation. Follow the template in
`references/brief-template.md`: absolute paths, files to study, an
explicit READ-ONLY marking on any reference directory (study, don't
copy), hard requirements as a checklist, the exact commit message, a
scoped fence, and a "Report back" section demanding pasted verify
output. The template explains why each section earns its place.

Turn limits are not a budget: `--autonomous-max-turns` was silently
exceeded in real use (ISSUE-005). Size tasks to finish inside the
timeout; split bigger work at the brief stage.

## Monitoring a background run

The log stays 0 bytes until the end (ISSUE-007). Never poll it; never
re-dispatch because it is empty. Watch the work instead — `git status`,
new files, directory counts — on 5-10 minute checkpoints. If a run dies
to the timeout, re-dispatch a narrow finishing task ("files X/Y exist;
verify, complete, report"); the disk work survives (ISSUE-002).

## Verification protocol (mandatory before reporting success)

The child's report is a hypothesis, not a result. On long autonomous
runs it demonstrably drifts (ISSUE-006):

1. Re-run the child's own verify commands yourself, on the delivered
   artifacts.
2. Run the repo's own validators if any exist (structure checks, schema
   validation, quick smoke of each new script's `--help` and main path).
3. Fix what fails yourself when small (schema-order bugs, placeholder
   text, stray fixture files), re-verify, amend or follow-up commit.
4. Only then report to the user — listing what was delegated, what you
   fixed in review, and what remains unverified.

## Diagnosing a broken install

Check in order: exe present (`~/.local/share/prime-agent/prime-agent.exe`),
`models.json` valid with `apiKey` inside each provider object (ISSUE-001),
liveness `delegate.sh "Reply with exactly: HEADLESS_OK"` — run it via the
  terminal tool's background mode (or a foreground timeout ≥300s): even the
  trivial probe takes 2+ minutes wall clock under `--print`, so a 90–120s
  kill is NOT evidence of breakage; judge only by captured output, and keep
  the agent-side tool timeout ABOVE the wrapper's `-t` (the outer timeout
  fires first and throws away a healthy run).
Before uninstalling, upgrading, or rebuilding prime-agent, stop every
running `prime-agent` process (`Get-Process prime-agent`) — deleting files
leaves old daemons alive and they break the new binary (ISSUE-008).

Config repairs touch `~/.prime/agent/` only with user consent and a backup.

## Refuses

- Inventing flags not verified in a real session — check `prime-agent --help` first
- Handling API keys; repairs point at the field, never carry the value
- Patching `~/.prime/agent/` silently — consent + backup, always
- Reporting delegated work as done without the Verification protocol
