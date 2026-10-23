# Prime Agent skills: install, isolation, self-improvement

Verified against pa-core source (2026-10-22, Rust `main`,
`packages/resolve/auto.rs`, `skills/discovery.rs`,
`session_engine/runtime_wiring.rs`, `kernel/bootstrap/`).

## Installing a skill = directory + SKILL.md (no install command)

All three locations are auto-scanned at session start; the skill's
frontmatter (`name`, `description`) is injected into the system prompt
inventory. Discovery order and `!`/`+`/`-` settings filters: see
`isolation-and-resources.md`.

| Location | Scope |
|---|---|
| `~/.agents/skills/<name>/SKILL.md` | user global, every profile (ancestor scan) |
| `<agent_dir>/skills/<name>/SKILL.md` | one agent dir (default `~/.prime/agent/skills/`) |
| `<cwd>/.prime/agent/skills/<name>/SKILL.md` | project |
| `prime-agent --skill <path>` (repeatable) | one session; `--no-skills` kills discovery |

Scan details that matter when debugging why a skill didn't load: a
`SKILL.md` found in a directory stops the scan below it; root-level
loose `*.md` files count as skills only at the scan root of a
`.prime/agent/skills` dir (Pi mode), not inside `.agents/skills`
(Agents mode). Broken frontmatter shows up as a ResourceDiagnostic
warning, not a hard error.

Packages (npm/git/local-dir sources in settings.json `packages`) can
carry their own `skills/` dir; those are discovered too.

## Python skills: executable, run in the kernel venv

A skill dir becomes a Python skill when it also has `pyproject.toml`
plus `src/<import_name>/__init__.py` (`import_name` = skill name with
`-`→`_`; both files must exist or discovery downgrades it with a
warning — `skills/discovery.rs` `detect_python_skill`).

At kernel bootstrap the skills are uv-synced into the kernel venv
(`~/.prime/agent/kernel-venv`) and pre-imported into the Python REPL;
the model calls them by importing the module, per the SKILL.md call
contract — no `.run` entrypoint assumption. Skills that fail to import
are surfaced as an "unavailable skills" notice in the session instead
of failing the boot.

## Isolation: process-level, not a security sandbox

- Python skill code runs in a separate kernel process + dedicated venv,
  never the system Python.
- The kernel/worker processes are lifecycle isolation only — the code
  still runs with the user's OS permissions and full filesystem access.
  README states this verbatim: review third-party skills before
  installing; untrusted code belongs in an external sandbox.

## Self-improvement: the continual harness (separate from file skills)

State file: `<agent_dir>/harness/harness_state.json`
(`entries.{prompt,memory,skill,subagent}`, plus `refinements` history).
Two layers:

1. REPL API — the agent writes its own durable state mid-session:
   `rlm.create_skill / update_skill / delete_skill / create_memory /
   update_memory / delete_memory / create_subagent / create_prompt_note`
   (and `rlm.get_harness_state()` to read). Harness skills are Python
   REPL skills with an explicit `reference`/`arguments` contract, stored
   in harness_state.json — NOT the filesystem skills above.
2. `/refine` — extracts lessons from the current trajectory into
   Create/Update/Delete proposals against that state (like compaction
   for reusable state), with recorded refinement history and
   local-vs-global scope separation.

Product stance: `/refine` persists reusable descriptions and lessons;
it does not replace packaging a reviewed, executable skill. Recurring
heavy workflows should still graduate into a real skill directory.
