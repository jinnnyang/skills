# Known Issues in upstream prime-agent

Source of truth for every upstream failure mode this wrapper detects and
repairs. All issues reproduced in real sessions (2026-10-13/15,
prime-agent 0.10.0, Windows x64, aptapi.dev custom provider).

## How to use this file

`scripts/delegate.sh` neutralizes ISSUES 003/004 automatically. The
remaining entries need judgment:

1. Match the symptom below to an ISSUE.
2. Explain the failure to the user in plain language.
3. Config repairs (`~/.prime/agent/`) need user consent and a backup first.

## ISSUE-001 — Custom provider silently filtered when `apiKey` missing

**Status**: Observed on 0.10.0 with custom OpenAI-compatible providers in
`~/.prime/agent/models.json`. Structural to the provider loader.

**Symptom** (verbatim):
- `✓ ready` then silence, `RC=1`
- `Error: No models available. Check your installation or add models to models.json.`
- TUI `/login` picker shows no configured provider
- Default model falls back to `amazon.nova-2-lite-v1:0:low`, then
  `No AWS credentials available for Bedrock`

**Root cause**: the provider loader requires `apiKey` as a field *inside*
each custom provider object in `models.json`. Missing → the provider is
filtered with no error. Migrating config from pi (the TS predecessor)
breaks silently: pi stores keys in `auth.json`; the formats are
incompatible despite the shared lineage. `--api-key` at runtime does not
rescue it — bootstrap exits before provider resolution.

**Repair**: backup `models.json`, add `"apiKey": "<key>"` inside the
provider object (user types the key; never through the agent), re-run
diagnose.

## ISSUE-005 — Testing self-updating plugin code requires care

When verifying a self-update plugin that replaces its own installed copy:
- Force a trigger with the plugin's TTL env var set to `0` (e.g.
  `OMNIROUTE_SELF_UPDATE_TTL=0`) instead of waiting out the TTL or deleting
  the stamp file.
- Give a local repo as the update URL in **Windows form** (`C:/Users/x/repo`),
  never the MSYS form (`/c/Users/x/repo`) — the plugin shells out to native
  git.exe, which rejects MSYS paths and clone fails with exit 128.
- Verify the update actually landed by checking the installed copy (the
  patched lines should now appear there), and clean any leftover empty
  `omniroute-selfupdate-*` staging dirs under the hermes home.

## ISSUE-002 — External timeout kills the report, not the work

**Status**: Observed under supervisor kills (Hermes terminal timeout).

**Symptom**: `timed out after Ns ... output_chars: 0` — but files written
before the kill are intact.

**Root cause**: prime-agent emits its report only at end of turn; there
is no checkpoint/resume and no cancel API.

**Impact**: looks like total failure; the real loss is the report plus
the last unfinished step.

**Repair — finishing task re-dispatch**: delegate a narrow follow-up
("files X/Y/Z already exist; verify, complete remaining steps, report")
instead of re-running the whole task. Skip re-running only when the
interrupted run wrote nothing verifiable.

## ISSUE-003 — MSYS/git-bash launcher passes an unreadable agent dir

**Status**: every launch of the `~/.local/bin/prime-agent` sh launcher
from MSYS bash (git-bash, Hermes terminal on Windows). PowerShell/cmd
unaffected.

**Symptom**: `Error: No models available...` in <1s, before any network
activity — while `models.json` demonstrably exists and is valid.

**Root cause**: the sh launcher expands `$HOME` to an MSYS path
(`/c/Users/...`) and exports it as `PRIME_AGENT_CODING_AGENT_DIR`; the
native exe cannot open that form, models.json is "not found", every
custom provider is silently filtered (ISSUE-001's mechanism), the run
dies at startup with a misleading error.

**Repair**: bypass the launcher — call the exe directly with a
Windows-form env path. `scripts/delegate.sh` does exactly this; manual form:

```bash
PRIME_AGENT_CODING_AGENT_DIR='C:\Users\<user>\.prime\agent' \
  "$HOME/.local/share/prime-agent/prime-agent.exe" \
  --provider aptapi --model norm --print "<task>"
```

## ISSUE-004 — `--print` emits full output then never exits under MSYS pipes

**Status**: stdout piped or captured from MSYS bash. Interactive
PowerShell runs exit normally.

**Symptom**: complete response arrives on stdout, then the process hangs
indefinitely; the caller's timeout kills it (exit 124). A successful run
looks like a failure.

**Root cause**: stdin/stdout lifecycle under MSYS pipes — the turn
completes but the exit path never fires when stdout is a pipe. Not a
model/network issue.

**Repair**: wrap with `timeout ... || true` and judge success by
**non-empty output**, never exit code. `delegate.sh` implements this and
prints the byte count.

## ISSUE-005 — `--autonomous-max-turns` silently not enforced

**Status**: observed once, 2026-10-15, real delegation run.

**Symptom**: run stopped with `maxTurns reached (143/40)` — the limit
(40) was passed on the command line, the run took 143 turns, and the
final report carried no error about exceeding it.

**Root cause**: unverified (not worth source-diving for a wrapper); the
cap appears advisory or enforced too late in autonomous mode.

**Impact**: turn count cannot be used as a wall-clock or cost budget.
Treat it as a suggestion, not a guardrail.

**Repair**: budget by task sizing and `timeout`, not by turns. Keep the
flag (it may still cap runaway loops) but never rely on it to bound cost.

## ISSUE-006 — Child's self-report says "tests pass" for a state it never tested

**Status**: observed once, 2026-10-15, real delegation run (docx skill).

**Symptom**: the child's report listed "validate passes ✓" as its final
state; the parent's re-run of the same command on the delivered artifact
failed with a schema error. The child's test chain had validated an
intermediate state and not the final one.

**Root cause**: not a prime-agent bug — an LLM-agent failure mode. The
report reflects what the child believes it verified, and belief drifts
across 140 turns.

**Impact**: every claim in a report is a hypothesis until the parent
re-runs it.

**Repair**: the Verification protocol in SKILL.md — re-run the child's
own verify commands on the delivered artifacts; treat discrepancies as
parent-fixable bugs (fix, re-verify, amend the commit) before telling
the user anything succeeded.

## ISSUE-007 — Zero progress signal in background runs

**Status**: inherent to headless `--print`; observed every background run.

**Symptom**: stdout log stays 0 bytes for the entire run — the report
arrives only at end of turn. There is no streaming, no heartbeat, no
progress API.

**Root cause**: single-shot design: report-at-end, nothing in between.

**Impact**: polling the log is useless; the only mid-flight observability
is the work itself appearing on disk.

**Repair**: monitor by watching target paths — `git status`, file counts,
new directories — on a coarse checkpoint schedule (5-10 min). Never poll
the log; never re-dispatch because "the log is empty".
