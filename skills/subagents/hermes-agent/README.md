# hermes-agent

Use, configure, theme, extend, and orchestrate Hermes Agent itself; references cover CLI, plugins, providers, security, Windows quirks.

| Field | Value |
|---|---|
| Origin | Vendored from the Hermes Agent bundled skill library (commit f5ec6a0 ingest; folder renamed `meta` → `subagents` since) |
| Upstream | `%LOCALAPPDATA%/hermes/hermes-agent/skills/autonomous-ai-agents/hermes-agent` |
| Author / License | Hermes Agent + Teknium / MIT |
| Local modifications | Frontmatter only: `version`/`author`/`platforms` moved under `metadata:` for agentskills.io spec compliance (quick_validate). Content otherwise identical |

## Sync notes

Upstream is updated by `hermes update`. The two copies already differ slightly
(SKILL.md frontmatter shape); re-diff before re-syncing.

