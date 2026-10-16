# Fork Branch Topology (jinnnyang/hermes-agent)

Current branch layout after the 2026-10 upstream sync. Keep this current when branches are added.

```
upstream → main → moirai → iris        (one-way merges; feature-branch work never flows back)
              ↘ feat/aptapi             (aptapi-server-specific; never merged into others)
```

| Branch | Role |
|---|---|
| `upstream` | Mirror of NousResearch upstream; sync-only, never developed on |
| `main` | Upstream content + user's own fixes; generic baseline |
| `moirai` | Release branch: Windows install UX fixes + aptapi integration (install scripts default to aptapi.dev/v1, clone aptapi branch, aptapi-bootstrap plugin, OmniRoute plugin auto-deploy) |
| `iris` | Software-development distro cut from moirai: github skill suite, gitnexus, oh-my-hermes plugin, prime-agent as coding agent. Branch itself holds near-zero source customization — all customization lives in standalone plugin repos (prime-hermes-plugin, gitnexus-hermes-plugin) + config presets + a bootstrap plugin |
| `feat/aptapi` / `feat/omniroute` | aptapi server-specific features; never merged into each other or cherry-picked across |

## Merge policy

- Update flow: fetch upstream → merge into `main` → merge `main` into each downstream branch in order (moirai, then feat branches). Merge, never rebase downstream (their old history is disconnected from upstream).
- `iris` merges from `moirai` (not directly from main) to keep the layering.
- Conflict pattern to expect on Windows-related files: the fork carries a `-Utf8Output` switch on `Invoke-Logged`/`Invoke-Native` in `scripts/install.ps1` (CP936 mojibake fix) that upstream lacks. Resolution: keep the fork's switch + forward it, adopt upstream's new body logic.
- Another recurring fork-only commit: `_track_current_branch` in `hermes_cli/update_cmd.py` (update tracks the current checkout branch). When upstream refactors the surrounding code, re-express the fork behavior against the new structure (e.g. pass a `Namespace(branch=...)` to skip channel resolution for tracked branches) rather than restoring the old code block.

## External plugin repos (standalone, never in the hermes-agent tree)

- `C:\Users\jinnn\Documents\omniroute-hermes-plugin` — OmniRoute provider (main = generic; aptapi branch = server-specific; never cross-merge)
- `C:\Users\jinnn\Documents\prime-hermes-plugin` — prime_delegate tool (prime-agent headless); HANDOFF.md is the implementation contract
- `C:\Users\jinnn\Documents\gitnexus-hermes-plugin` — GitNexus MCP auto-config; HANDOFF.md is the implementation contract

Plugin scaffolding convention: `plugins/<name>/plugin.yaml` (id, name, kind: utility, version, description, author) + `__init__.py` + HANDOFF.md with verified integration facts, design contract, YAGNI list, and acceptance criteria. Implementation is delegated to a fresh session by pointing it at HANDOFF.md.
