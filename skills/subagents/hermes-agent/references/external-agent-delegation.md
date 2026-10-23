# Wrapping an External Coding Agent for Hermes (skill vs plugin vs ACP)

When the user wants an external coding agent (prime-agent, Codex, Claude Code, ...) usable from
Hermes as a delegateable subagent, pick the integration form by NEEDED CAPABILITY, not by default.

## Decision ladder (pick the lowest rung that covers the need)

1. **Skill** — if a CLI subprocess call (`agent exec --print` style) covers the task and Hermes's
   terminal tool can run it. Zero code. Choose this whenever the interaction is one-shot per call.
2. **Plugin + CLI tools** — only if the schema-typed tool face matters (structured params/return,
   check_fn gating). Still one process per call; no session continuity.
3. **Plugin + long-lived protocol (ACP/MCP/daemon)** — needed when the user wants SUBAGENT-LIKE
   semantics: spawn in background, keep session context across rounds (implement→test→review→fix),
   interrupt/steer mid-run, async completion notification. A CLI form cannot do this; do not
   build a CLI plugin for it — if the plan lands on CLI, a skill was the right answer all along.
Validate the long-lived protocol's ACTUAL surface with a throwaway probe script before committing to it (handshake alone proves nothing — cancel/permission/limits may be unimplemented).

Key trap: a HANDOFF/design doc written assuming "must write a plugin" is not evidence. Challenge
the form first: ask what the user actually wants the agent to DO. Multi-round delegation ⇒ rung 3.
One-shot delegation with status polling and completion notification is covered by rung 1 + Hermes
background terminal — background+notify gives you the async return without any protocol code.

## Standing user rule: implementation goes to external agent CLIs, not delegate_task

The user directs; agent CLIs (prime-agent, Codex, Claude Code) write the code. Hermes-side
`delegate_task` subagents are NOT the user's chosen executor — spawning one for implementation
work the user expected to go to prime-agent is a correction. When unsure which CLI, ask.

## prime_spawn operating rules (legacy ACP bridge, experimental)

Always pass `timeout_s: 1800` for multi-file tasks — the plugin's default 600s is a WHOLE-TASK wall
clock (not per-tool); on expiry the daemon is killed with no cancel (ACP has none), the final report
is lost, but files already written survive — re-spawn with a hand-off-only
"verify/finish remaining steps" task instead of re-running the whole thing.

Prefer the one-shot CLI over the ACP bridge whenever the task is self-contained (see
`~/.agents/skills/prime-agent/`): the bridge's only real advantage is in-session steering,
which the user's director-style workflow does not use.

## Writing wrapper skills for agent CLIs (skill-creator wrapper workflow)

When distilling a debugging session into a wrapper skill, these lessons are class-level:

- **Mine the session, don't invent.** Every command in the skill must have actually run and
  succeeded; unexecuted flags are speculation that will fail for the next session.
- **Verify the distilled skill end-to-end (diagnose-first loop).** Ship a read-only `diagnose.sh`
  and RUN it against the live install before declaring done — it catches both the skill's own
  bugs and real regressions. Two bugs found this way on first run: MSYS `/c/...` paths passed to
  native Windows python fail to open (wrap with `cygpath -w`); provider-pinned liveness probes
  must pin `--provider` explicitly or they fall back to another provider and report a misleading
  error. Fix the script in place, re-run, only then report.
- **Liveness checks verify body shape, not exit code.** The failure mode is exit-with-confirmation
  text missing or a generic error string; grep for the expected success token, don't trust RC.
- **Reference the incident report, but distill it.** Keep the repro command and the root cause
  rule in the skill; the full narrative lives in the user's Documents/*.md report — link it,
  don't copy it.
