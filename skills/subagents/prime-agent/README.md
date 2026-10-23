# prime-agent

Orchestrate prime-agent sessions: workspace/role isolation, task briefs,
delegate.sh / setup-profiles.sh scripts. Companion to the installed
prime-delegate Hermes plugin (prime_spawn/prime_status/prime_respond/prime_stop).

| Field | Value |
|---|---|
| Origin | Original work, authored in-repo (rewritten from a verified live workflow, commits 2bf5d6c → ce84787) |
| Related component | `omniroute-hermes-plugin` / prime-delegate plugin (separate repo, not vendored here) |
| License | MIT |

## For developers

- The scripts assume prime-agent ≥0.10.0 ACP behavior: no session/cancel, no
  permission protocol — see `references/known_issues.md` before relying on
  timeout or cancel semantics.

