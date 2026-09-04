#!/bin/sh
# Claude Code PostToolUse hook (matcher: Skill): append one line per skill
# invocation to the append-only skill-run log. The hook payload arrives on
# stdin and is passed straight through to skill-run-log.py; this wrapper
# never blocks the session (always exit 0).
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$root" ] || exit 0
here="$(dirname "$0")"
# The Python side authenticates every path component below the root with
# no-follow opens before appending; a symlinked log or parent is refused.
python3 "$here/skill-run-log.py" "$root" "10_Agents/docs/skill-runs.log" || exit 0
exit 0
