---
name: codex
description: "Delegate coding to OpenAI Codex CLI (features, PRs)."
license: MIT
metadata:
  version: 1.0.1
  author: Hermes Agent
  platforms: [linux, macos, windows]
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
    related_skills: [claude-code, hermes-agent]
---

# Codex CLI

Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.

## When to use

- Building features
- Refactoring
- PR reviews
- Batch issue fixing

Requires the codex CLI and a git repository.

## Prerequisites

- Codex installed: `npm install -g @openai/codex`. On Windows, the Codex Desktop app bundles a CLI that may not be on PATH; locate it with `search_files(target='files', path='C:/Programs/Codex')` for `codex.exe` under `resources/`, check `--version`, and call it by absolute path (e.g. `"C:/Programs/Codex/<ver>/windows/amd64/resources/codex.exe" exec ...`). Confirm with `codex --version` before delegating.
- OpenAI auth configured: either `OPENAI_API_KEY` or Codex OAuth credentials
  from the Codex CLI login flow
- **Must run inside a git repository** — Codex refuses to run outside one
- **Verify before letting it write:** run a read-only pass first with `codex exec -s read-only "<prompt>"`. It still runs read-only shell commands (e.g. directory listings) but cannot edit files, so it confirms the CLI, auth, and repo context work before a write task.
- **Scope prompts tightly.** A one-sentence read-only question consumed about 65k tokens on a large repo, so split big jobs and avoid open-ended "review everything" prompts.
- **No ACP mode in the CLI.** Codex CLI (checked 0.155.0-alpha) has no `acp` subcommand, so it does not speak Agent Client Protocol. Programmatic control uses `codex app-server` (JSON-RPC, experimental; `generate-json-schema` emits its schema) or one-shot `codex exec`. Re-run `codex --help` after upgrades and do not assume ACP support from the product name.
- **Custom providers print `Model metadata for <model> not found`.** This is a warning, not a failure; Codex falls back to default metadata, which can reduce quality. Check the output is still sound before trusting it.
- **Protocol surfaces differ.** Codex exposes `codex app-server` (its own JSON-RPC), not ACP. See `references/protocols.md` before wiring it into an ACP client. prime-agent (PrimeIntellect) DOES speak ACP — see `references/prime-agent-acp.md`.
- Use `pty=true` in terminal calls — Codex is an interactive terminal app

## Lessons from designing an external-agent plugin (generalize beyond Codex)

- **Match mechanism to deliverable.** One-shot CLI delegation doesn't need a plugin — a SKILL documenting the call form covers it. Write a plugin only when you need a persistent process, streaming, or lifecycle tools (spawn/steer/stop). Ask which tier the deliverable actually needs before coding.
- **Verify the full protocol chain before committing to an architecture.** One successful `initialize` handshake validates nothing — probe every method the design depends on (cancel, permission requests, streaming shapes) with a throwaway script FIRST; missing methods force design downgrades (e.g. no cancel -> task-level restart instead of in-session steering).
- **Never assume a plugin can't message the host.** Check the host's injection surface (in Hermes: plugin `ctx.inject_message`, gated by `plugins.entries.<id>.allow_gateway_injection`) before designing around 'async results must be polled'.
- For async bidirectional flows without protocol support, use a text-contract bridge: agent emits a sentinel line (e.g. `PRIME_ASK(key): question`) and stops; the bridge matches it in the stream, injects to the host, and the host's answer becomes the next prompt. Turn-boundary granularity, but protocol-independent.

For Hermes itself, `model.provider: openai-codex` uses Hermes-managed Codex
OAuth from `~/.hermes/auth.json` after `hermes auth add openai-codex`. For the
standalone Codex CLI, a valid CLI OAuth session may live under
`~/.codex/auth.json`; do not treat a missing `OPENAI_API_KEY` alone as proof
that Codex auth is missing.

## One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

## Background Mode (Long Tasks)

```
# Start in background with PTY
terminal(command="codex exec --sandbox workspace-write 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--sandbox workspace-write` (`-s`) | Sandboxed but auto-approves file changes in the workspace (the recommended auto-build mode) |
| `--dangerously-bypass-approvals-and-sandbox` | No sandbox, no approvals (fastest, most dangerous; `--yolo` still works as a hidden alias) |
| `--sandbox danger-full-access` | No Codex sandbox; useful when the host service context breaks bubblewrap |

> **Deprecated:** `--full-auto` still works but the live CLI warns to use `--sandbox workspace-write` instead.

## Hermes Gateway Caveat

When invoking the Codex CLI from a Hermes gateway/service context (for example,
Telegram-driven agent sessions), Codex `workspace-write` sandboxing may fail even
when the same command works in the user's interactive shell. A typical symptom is
bubblewrap/user-namespace errors such as `setting up uid map: Permission denied`
or `loopback: Failed RTM_NEWADDR: Operation not permitted`.

In that context, prefer:

```
codex exec --sandbox danger-full-access "<task>"
```

Use process boundaries as the safety layer instead: explicit `workdir`, clean git
status before launch, narrow task prompts, `git diff` review, targeted tests, and
human/agent confirmation before committing broad changes.

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 ~/.hermes/cache/scratch/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 ~/.hermes/cache/scratch/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex --sandbox workspace-write exec 'Fix issue #78: <description>. Commit when done.'", workdir="~/.hermes/cache/scratch/issue-78", background=true, pty=true)
terminal(command="codex --sandbox workspace-write exec 'Fix issue #99: <description>. Commit when done.'", workdir="~/.hermes/cache/scratch/issue-99", background=true, pty=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd ~/.hermes/cache/scratch/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove ~/.hermes/cache/scratch/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Rules

1. **Always use `pty=true`** — Codex is an interactive terminal app and hangs without a PTY
2. **Git repo required** — Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch
3. **Use `exec` for one-shots** — `codex exec "prompt"` runs and exits cleanly
4. **`--sandbox workspace-write` for building** — auto-approves changes within the sandbox (`--full-auto` is deprecated for this)
5. **Background for long tasks** — use `background=true` and monitor with `process` tool
6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks
7. **Parallel is fine** — run multiple Codex processes at once for batch work
