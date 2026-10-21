#!/usr/bin/env bash
# Create prime-agent role profiles: one agent dir per role, so harness memory,
# skills, MCP servers, sessions and the daemon socket are each private.
#   usage: bash setup-profiles.sh cad circuit rust
#   env:   PRIME_PROFILES_ROOT (default ~/.prime/profiles)
#          PRIME_AGENT_CODING_AGENT_DIR (the source agent dir to seed from)
set -euo pipefail

ROOT="${PRIME_PROFILES_ROOT:-$HOME/.prime/profiles}"
BASE="${PRIME_AGENT_CODING_AGENT_DIR:-$HOME/.prime/agent}"

[ $# -gt 0 ] || { echo "usage: $0 <profile> [profile...]" >&2; exit 1; }

for p in "$@"; do
  dir="$ROOT/$p"
  mkdir -p "$dir/skills"
  # copy, never symlink: auth writes are atomic rename, which replaces the inode
  # and would turn a symlink into an independent file after the first refresh
  for f in auth.json models.json; do
    if [ -f "$BASE/$f" ] && [ ! -f "$dir/$f" ]; then
      cp "$BASE/$f" "$dir/$f"
      echo "seeded $f -> $dir/$f"
    fi
  done
  # harness/, sessions/, session-artifacts/ appear on first session
  [ -f "$dir/settings.json" ] || printf '{\n  "mcpServers": {}\n}\n' > "$dir/settings.json"
  echo "ready: $dir"
  echo "  run: PRIME_AGENT_CODING_AGENT_DIR=$dir prime-agent --cwd <project>"
done
