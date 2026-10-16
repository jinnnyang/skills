#!/usr/bin/env bash
# delegate.sh — one correct way to call prime-agent headless from MSYS bash.
#
# Fixes three upstream traps in a single wrapper (see references/known_issues.md):
#   ISSUE-003  launcher exports MSYS $HOME; the exe can't read /c/... paths
#   ISSUE-004  under pipes --print emits its full output then never exits
#   ISSUE-002  external timeout kills a nearly-finished run; disk work survives
#
# Success = non-empty output (captured verbatim). Exit code is unreliable
# under MSYS pipes and is reported but not trusted.
#
# Usage:
#   delegate.sh "TASK PROMPT"                     # one-shot --print, 30 min budget
#   delegate.sh -t 1800 "TASK PROMPT"             # custom timeout seconds
#   delegate.sh -a "TASK PROMPT"                  # autonomous mode, 40 turns default
#   delegate.sh -a -n 80 "TASK PROMPT"            # autonomous, 80 max turns
#   delegate.sh -m heavy "TASK PROMPT"            # pick model (light|norm|heavy)
#   delegate.sh -b "TASK PROMPT"                  # background-friendly: append &> log yourself
#
# Exit codes: 0 output captured · 1 empty output (real failure) · 2 bad usage

set -uo pipefail

TIMEOUT=1800
TURNS=40
MODEL=norm
AUTON=0

while getopts "t:n:m:a" opt; do
  case "$opt" in
    t) TIMEOUT="$OPTARG" ;;
    n) TURNS="$OPTARG" ;;
    m) MODEL="$OPTARG" ;;
    a) AUTON=1 ;;
    *) echo "usage: delegate.sh [-t sec] [-n turns] [-m model] [-a] \"prompt\"" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

[ $# -lt 1 ] && { echo "usage: delegate.sh [-t sec] [-n turns] [-m model] [-a] \"prompt\"" >&2; exit 2; }
PROMPT="$1"

EXE="$HOME/.local/share/prime-agent/prime-agent.exe"
[ -f "$EXE" ] || { echo "delegate.sh: prime-agent.exe not found at $EXE" >&2; exit 2; }

# ISSUE-003: the exe needs a Windows-form agent dir, never the MSYS form
AGENT_DIR_WIN=$(cygpath -w "$HOME/.prime/agent" 2>/dev/null || echo "$USERPROFILE\\.prime\\agent")

ARGS=(--provider aptapi --model "$MODEL")
if [ "$AUTON" = "1" ]; then
  ARGS+=(--autonomous --autonomous-max-turns "$TURNS")
fi
ARGS+=(--print "$PROMPT")

# ISSUE-004: timeout is expected to fire after output is complete; judge by output
OUT=""
if command -v timeout >/dev/null 2>&1; then
  OUT=$(PRIME_AGENT_CODING_AGENT_DIR="$AGENT_DIR_WIN" timeout "$TIMEOUT" "$EXE" "${ARGS[@]}" 2>&1) || true
else
  OUT=$(PRIME_AGENT_CODING_AGENT_DIR="$AGENT_DIR_WIN" "$EXE" "${ARGS[@]}" 2>&1) || true
fi

if [ -n "$OUT" ]; then
  printf '%s\n' "$OUT"
  echo "---"
  echo "delegate.sh: output captured ($(printf '%s' "$OUT" | wc -c) bytes). exit code not trusted (ISSUE-004)."
  exit 0
fi
echo "delegate.sh: EMPTY output after ${TIMEOUT}s — real failure (see references/known_issues.md). Work already written to disk survives (ISSUE-002): check the target repo's git status before re-running." >&2
exit 1
