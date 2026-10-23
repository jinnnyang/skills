# Prime Agent system prompt: how to modify it

The prompt is layered: cache-stable static prefix (core / usage / opinionated
layers + per-model additions) then a dynamic tail (packages, project context,
skills, MCP, environment, session role). `prime-agent prompt` dumps the
assembled prompt with its layer breakdown — it is also the verification tool
for every route below (grep it, never trust the config file).

Assembly lives in `crates/pa-core/src/prompts/system_prompt.rs`
(`custom_prompt` branch picks replacement vs layered files).

## Routes, least to most invasive

### 1. APPEND_SYSTEM.md (append; no rebuild) — default choice
```bash
~/.prime/agent/APPEND_SYSTEM.md          # global, all projects
<proj>/.prime/agent/APPEND_SYSTEM.md     # project-level, wins if present
```
Appended to the dynamic tail. Discovered by
`discover_append_system_prompt_file` in `crates/pa-core/src/resources/mod.rs`.
Profile-aware: goes under the dir `PRIME_AGENT_CODING_AGENT_DIR` points at.

### 2. CLI flags
```bash
prime-agent --append-system-prompt "be terse"      # append (repeatable)
prime-agent --system-prompt "you are a translator" # REPLACE the static layers
```
Replacement keeps the dynamic tail (skills/MCP/environment still appear).
Parsed in `crates/pa-cli/src/args.rs` (`--system-prompt`,
`--append-system-prompt`).

### 3. Per-model additions (no rebuild)
`<agent_dir>/model-prompts.toml` + one or more md files beside it:
```toml
[[rule]]
match = ["glm-5.3*"]              # model-name glob
files = ["my-model-note.md"]      # resolves inside agent dir; ".." rejected
```
Matching rules live in `pa_core::prompts::model_prompts`; bundled example in
`crates/pa-core/src/prompts/layers/model_prompts.toml`.

### 4. Edit the built-in layers (rebuild required)
Layer files are `include_str!`-compiled into the binary:
`crates/pa-core/src/prompts/layers/{core,usage,opinionated}.md` (+ the
bash-over-subprocess model addition). Edit → `cargo build`.

Repo constraint: the prompt structure is a **surface contract** (AGENTS.md) —
changing built-in layers requires a parity-diff evidence section in the PR
(`prime-agent prompt` before/after is the cheap renderer diff). User-layer
files (routes 1–3) are exempt.

### 5. `settings.json` `prompts` array
Global/project settings support a `prompts` resource-path array
(`set_global_resource_array("prompts", …)` in
`crates/pa-core/src/settings/manager.rs`). Additional layer-ish content paths;
rarely needed — prefer APPEND_SYSTEM.md unless managing files out-of-tree.

## Verify (no tokens)
```bash
prime-agent prompt | grep -n "custom\|APPEND"          # segment sources
prime-agent prompt --json | python -c "import json,sys; d=json.load(sys.stdin); [print(s['name'], s['kind'], s['chars']) for s in d['segments']]"
```
Segment named `custom` with source `--system-prompt` = replacement took; an
`append` segment's char count = APPEND_SYSTEM.md content reached the model.
`--json` segments carry metadata only (no text) — grep the plain output for
content.
