#!/bin/sh
# validate-hook.sh — Claude Code PostToolUse shim around `brain validate`.
#
# Claude Code's PostToolUse hook contract: exit 0 = success; exit 2 =
# blocking error whose STDERR is fed back to the agent; any other exit
# code is non-blocking and the output never reaches the agent. `brain
# validate` uses a different contract (0 clean / 1 errors / 2 warnings
# only, spec.md section 10.4), so calling it directly — or worse, with
# `|| true` — means findings never reach the agent (issue #11). This
# shim translates between the two contracts:
#
#   brain exit 0 (clean)         -> hook exit 0
#   brain exit 2 (warnings only) -> hook exit 0  (warnings never block)
#   brain exit 1 (errors)        -> findings re-emitted on STDERR, hook exit 2
#   anything else (tool broken)  -> output re-emitted on STDERR, hook exit 2
#
# POSIX sh, no dependencies beyond python3. Works from any cwd: brain.py
# is located relative to this script. Extra arguments are forwarded to
# `brain validate` (e.g. `--vault <root>` for tests).

set -u

dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH='' cd -- "$dir/../../.." && pwd)

out=$("${PYTHON:-python3}" "$root/10_Agents/tools/brain/brain.py" validate "$@" 2>&1)
status=$?

case $status in
  0|2) exit 0 ;;
esac

printf '%s\n' "$out" >&2
exit 2
