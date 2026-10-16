---
name: prime-agent
description: Delegate self-contained coding tasks to prime-agent (PrimeIntellect coding agent) via its headless one-shot CLI. Use when the user asks to delegate/委托 a coding task, spawn a background coding agent, run autonomous implementation work, or mentions prime-agent, "HEADLESS_OK", "No models available", silent exit after "✓ ready", aptapi/AptAPI provider issues, "--print 静默退出", or "prime_spawn". Also use when a prime-agent headless run fails silently, hangs after producing output, or its self-reported results need verification.
---

# prime-agent delegation

Wrap the prime-agent CLI so delegation succeeds on the first try and its
reports are trusted only after verification.

## Why this is finicky

The CLI surface is tiny (`--print`, `--autonomous`). All friction lives in
four places: provider plumbing that fails with misleading errors, terminal
pipe semantics that make success look like failure, a report-only-at-end
design that gives zero progress signal, and LLM-report drift on long runs.
Each has a known fix; the wrapper script bakes in the mechanical ones.

## Routing

| Situation | Do |
|---|---|
| Delegate a self-contained task | One-shot delegate (below) |
| Task needs build/test gates | One-shot with `--autonomous` |
| `No models available` / silent exit / provider missing | `references/known_issues.md` (ISSUE-001/003) |
| Run hung after output / exit 124 | ISSUE-004 — output complete, exit unreliable |
| Run timed out / killed | ISSUE-002 — disk work survives; re-dispatch a finishing task |
| Suspicious "all tests pass" report | ISSUE-006 — run the Verification protocol |

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
liveness `delegate.sh "Reply with exactly: HEADLESS_OK"`. Config repairs
touch `~/.prime/agent/` only with user consent and a backup.

## Refuses

- Inventing flags not verified in a real session — check `prime-agent --help` first
- Handling API keys; repairs point at the field, never carry the value
- Patching `~/.prime/agent/` silently — consent + backup, always
- Reporting delegated work as done without the Verification protocol
