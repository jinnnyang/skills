# Prime Agent role / workspace isolation

How prime-agent partitions state, and how to verify a partition actually holds.
There is no `profile`, `workspace`, or `role` concept in the CLI. The prompt's
"session role" segment is recursion depth + daemon status, not a persona. All
isolation is directory-based, on three axes:

| What | Where | How to switch |
|---|---|---|
| memory, harness skills, auth, models, sessions, daemon socket, traces | `$PRIME_AGENT_CODING_AGENT_DIR` (default `~/.prime/agent`) | env var |
| project settings, project skills, local harness | `<cwd>/.prime/agent/` | `--cwd` or `cd` |
| MCP servers | `mcpServers` in the global and/or project `settings.json` | write either file |

Wire a stdio MCP server into a profile with the CLI (writes the resolved
agent-dir `settings.json`, so set `PRIME_AGENT_CODING_AGENT_DIR` first):

```bash
PRIME_AGENT_CODING_AGENT_DIR=~/.prime/profiles/cad \
  prime-agent mcp add cadcraft -- "C:/Programs/CADCraft/0.10.0/cadcraft-cli.exe" mcp
```

Verify it took by grepping the rendered prompt, not the settings file — the
prompt only lists servers whose executable actually resolves:

```bash
PRIME_AGENT_CODING_AGENT_DIR=~/.prime/profiles/cad \
  prime-agent prompt --cwd <proj> | grep -A1 'Enabled generic MCP servers'
# -> Enabled generic MCP servers: `cadcraft`.
```

Pitfall: if `prime-agent mcp add` fails with `the mcpServers setting must be a
JSON object`, the target settings.json has `mcpServers: null` from an older
save (or a stale default). Rerun the same command — the re-read normalizes
null to `{}` and the add succeeds; do not hand-edit the file mid-attempt.

Memory has no file of its own: it is `entries.memory` inside
`<agent_dir>/harness/harness_state.json` (global scope) and inside the session
artifact dir's `harness/harness_state.json` (local scope). Isolating the agent
dir therefore isolates memory for free.

One agent dir = one `sessions/` tree. The daemon is NOT isolated by agent dir:
its endpoint is a fixed named pipe (Windows `\\.\pipe\prime-agent-daemon`, Unix
`$XDG_RUNTIME_DIR`/`~/.prime/agent-daemon` socket), so separate profiles default to
sharing one daemon. Isolate a profile's daemon explicitly by setting
`PRIME_AGENT_DAEMON_SOCKET` to a per-profile path.

## Profile layout

```bash
for p in cad circuit rust; do mkdir -p ~/.prime/profiles/$p/skills; done
# seed login state instead of re-authenticating per profile
for p in cad circuit rust; do
  cp ~/.prime/agent/auth.json    ~/.prime/profiles/$p/auth.json
  cp ~/.prime/agent/models.json  ~/.prime/profiles/$p/models.json
done
PRIME_AGENT_CODING_AGENT_DIR=~/.prime/profiles/cad prime-agent --cwd ~/iot/cad
```

`scripts/setup-profiles.sh <name>...` does this without hand-typing it.

Reach for profiles only when the work lives in separate repositories. Same repo,
several subject areas: one agent dir plus per-project skill dirs is cheaper —
memory is shared but there is one login and one session store.

Copy `auth.json`, never symlink it. Auth writes go through
`atomic_write_with`: a temp file plus `rename_onto`, which replaces the inode.
Rename onto a symlink overwrites the link itself, so after the first token
refresh the profile has a standalone file and the shared link is gone. Copies
are independent: re-authenticating an MCP server in one profile does not reach
the others (that is usually what you want per role, and it is why you seed by
copying rather than hoisting one file).

`harness/`, `sessions/`, `session-artifacts/`, and `mcp-connections.json` need
no pre-creation — the first session creates them.

## Verifying a partition actually holds

Do not trust the layout, prove it. Two probes, both cheap:

```bash
# skills: each profile must see only its own
for prof in cad circuit rust; do
  echo -n "$prof -> "
  PRIME_AGENT_CODING_AGENT_DIR=~/.prime/profiles/$prof prime-agent prompt \
    --cwd ~/.prime/profiles/$prof/proj 2>/dev/null \
    | grep -o "<name>\(kicad-draw\|ngspice-sim\|svd2rust\)</name>" | tr '\n' ' '; echo
done

# memory: write in one profile, then ask another for its ids -- expect NONE
PRIME_AGENT_CODING_AGENT_DIR=~/.prime/profiles/cad prime-agent --model <prov>/<id> \
  --cwd <dir> --print "用 rlm.harness.create_memory 记一条：<fact>"
PRIME_AGENT_CODING_AGENT_DIR=~/.prime/profiles/circuit prime-agent --model <prov>/<id> \
  --cwd <dir> --print "调用 rlm.get_harness_state()，列出所有 memory 条目的 id。没有就说 NONE"
```

Then confirm the write landed where expected by reading the file directly —
`<agent_dir>/harness/harness_state.json`, `entries.memory.<id>` with
`scope: global` (global here means "global to this agent dir", not to the
machine).

`prime-agent prompt --json` returns each segment's name/kind/chars only, not
the segment text — grep the plain `prompt` output to see whether a skill or
server actually made it into the prompt.

## Excluding a globally-visible skill

`~/.agents/skills` and every ancestor `<dir>/.agents/skills` are scanned for
every profile, so they leak across a partition. Suppress per profile through
the `skills` settings array: `"skills": ["!**/<skill-name>/**"]` works, and so
does an absolute path (`!C:/Users/<user>/.agents/skills/<name>/**`). A relative
`!../../.agents/skills/<name>/**` does NOT — patterns resolve against the
agent dir, so `../..` walks out of the tree the matcher is anchored on.

On Windows, export `HOME`/`USERPROFILE` in native form (`C:/Users/<user>`). An
MSYS-style `/c/Users/<user>` makes `~/.prime/agent` resolve to a path that does
not exist, and the whole user skills dir silently loads nothing.

## Skill discovery order (first wins on name collisions)

1. project `<cwd>/.prime/agent/skills/` — auto-discovered, no settings entry needed
2. user `<agent_dir>/skills/`
3. `~/.agents/skills/` — ancestor scan from cwd up to home
4. built-in Python skills shipped with the runtime

`~/.agents/skills/` is shared by every agent dir, so a profile cannot exclude it
by choosing a different `PRIME_AGENT_CODING_AGENT_DIR`; exclude by name (below).

## Turning skills on and off

- `--skill <path>` adds one skill; repeatable.
- `-ns` / `--no-skills` disables discovery entirely.
- Settings `skills` array takes `!` (exclude), `+` (force include), `-` (force
exclude, applied last) glob forms. Patterns resolve against the agent dir for the
global file and against `<cwd>/.prime/agent` for the project file.

Use `"!**/name/**"`, not a `../..`-relative path: `!../../.agents/skills/x/**`
silently matches nothing because the base dir is the agent dir, three levels
shallower than the ancestors the scan actually reads.

## MCP isolation

`mcpServers` lives in `settings.json` and is **deep-merged** global-then-project;
a project entry overrides a global one, and `null` never overrides a real value.
Two agent dirs with different `settings.json` therefore expose different servers
with no extra configuration. Per-server `enabled: false`, `enabledTools` and
`disabledTools` narrow a server without deleting it.

## Verifying a partition (30 seconds, no LLM call)

`prime-agent prompt` assembles the real system prompt with its layer breakdown
and costs no tokens — it is the inspection tool, not `prime-agent config`.

```bash
# which skills actually reach the model
prime-agent prompt --json | python -c "import json,sys; print(json.load(sys.stdin)['prompt'])" \
  | grep -o '<name>[^<]*</name>' | sort

# did the partition hold?
for d in agentA agentB; do
  echo -n "$d: "; PRIME_AGENT_CODING_AGENT_DIR="$T/$d" prime-agent prompt --cwd "$T/proj" \
    | grep -o '<name>\(cad-draw\|rust-fw\)</name>' | sort | tr '\n' ' '; echo
done
```

## Pitfalls

- **`prime-agent config` is an interactive TUI.** It never returns in a
  non-tty shell and burns the whole tool timeout. For inspection use
  `prime-agent prompt` (`--json` for the segment list).
- **`--json` segments carry metadata only** — `name`/`kind`/`source`/`chars`, no
  `text`. Read the `prompt` key for content and grep it.
- **`--offline` is not a `prompt` subcommand flag** — it belongs to the run-level
  option set; `prime-agent prompt --offline` errors with "unknown option".
- **`HOME` must be a native path on Windows.** `HOME=/c/Users/...` (MSYS form)
  makes the agent dir resolve somewhere unusable and `~/.prime/agent/skills`
  loads nothing, with no error. Use `C:/Users/...`. To prove a skill came from a
  profile rather than the real home, point `HOME`/`USERPROFILE` at a scratch
  home and check the baseline is empty first.
- **`prompt` reads the project dir of its `--cwd`.** Asking for a cwd that is an
  ancestor of the project yields different skill sets; always pass the exact
  project root you will run the session in.
- **Name must equal the parent directory** (lowercase, digits, single hyphens)
  or the skill is dropped with a diagnostic rather than surfaced.
