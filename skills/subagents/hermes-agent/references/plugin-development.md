# Developing a Hermes Plugin (native `plugin.yaml` + `register(ctx)`)

Authoritative docs, read before writing code:
- `plugins/AGENTS.md` in the repo — policy (never touch core, what may live in-tree)
- `website/docs/developer-guide/plugins/index.md` — full 2294-line build tutorial
- `hermes_agent` skill references/contributor-guide.md — core-tool vs plugin boundary

## Standing rules (always-on)

- Plugins NEVER modify core files (`run_agent.py`, `cli.py`, `gateway/run.py`, ...). Missing
  capability ⇒ widen the GENERIC plugin surface (new hook / ctx method) and use it — never
  hardcode plugin-specific logic into core.
- Third-party-product integrations ship as STANDALONE plugin repos (`~/.hermes/plugins/` or pip
  entry point), not merged into the hermes-agent tree.
- Handler contract: receive `args: dict`, ALWAYS return a JSON string (even on error), and accept
  `**kwargs` — Hermes inspects signatures to forward additive hook payload fields.
- No hook without a concrete consumer; speculative infrastructure is rejected.
- There is NO `ctx.register_mcp_server` plugin surface (verify on your branch). MCP servers are
  configured in config.yaml under `mcp_servers` (core-managed; see `hermes_cli/mcp_config.py`),
  written by setup/tools flows only. Plugin options for exposing an MCP server: (a) idempotently
  fill a MISSING `mcp_servers.<name>` entry in the profile's config.yaml — never overwrite an
  existing entry (core's full MCP stack then handles lifecycle); or (b) register a single
  `register_tool` that embeds its own stdio MCP client (subprocess + JSON-RPC
  initialize/tools-list/tools-call) and proxies the server's tools — pick this when the user wants
  zero config.yaml footprint. Ask the user which trade-off they want; it is a real decision point,
  not an implementation detail.

## Minimal build order

1. `mkdir -p <plugin-dir>` — user plugins live in `~/.hermes/plugins/<name>/` (real Windows path:
   `%LOCALAPPDATA%\hermes\plugins\`).
2. `plugin.yaml`: `name`, `version`, `description`, `provides_tools`, `provides_hooks` (optional
   `requires_env`, `capabilities`). `provides_tools` MUST match what `register()` actually
   registers — mismatch fails `hermes plugins validate` and blocks catalog admission.
3. `schemas.py` — JSON Schemas the LLM reads; descriptions drive tool selection, write them well.
4. `tools.py` — handlers per the contract above.
5. `__init__.py` — `def register(ctx)`: `ctx.register_tool(name, toolset, schema, handler)`,
   `ctx.register_hook(name, cb)`, `ctx.register_cli_command()`, `ctx.register_command()` (slash).
   `register()` runs exactly once at startup.
6. Validate (in order):
   ```bash
   hermes plugins doctor <path> --ci            # isolated HERMES_HOME, real discovery+register
   hermes plugins validate <path> --install-deps  # same check catalog CI runs
   HERMES_PLUGINS_DEBUG=1 hermes plugins list   # discovery troubleshooting
   hermes plugins enable <name>
   ```
7. Enable requires session restart (CLI relaunch / gateway `/restart`) for tools to appear.

## ctx surface cheat-sheet

- `register_tool` / `register_hook` / `register_cli_command` / `register_command`
- `ctx.dispatch_tool(name, args)` — call another tool with parent context (approvals, creds) wired
- `ctx.llm` — host-owned credentials, fail-closed trust gate
- `plugin_data_dir()` / `plugin_db()` — durable storage surviving `plugins update`/`remove`,
  profile-aware

## Pitfalls

- Assume only the documented arg shape when a handler may also be reached through the deferred
  `tool_call` dispatch layer — coerce defensively there (`isinstance(task, dict)` → unwrap) or the
  handler raises `AttributeError` on an unexpected type. Wrap only the boundary, not everything.
- Unknown `plugin.yaml` fields are ignored (manifests open to additions) — safe to add metadata
  newer than the running Hermes.
- Debugging non-loading plugins: `HERMES_PLUGINS_DEBUG=1` (stderr verbose) or
  `hermes logs --level WARNING | grep -i plugin`; common cause is simply not enabled in config.
