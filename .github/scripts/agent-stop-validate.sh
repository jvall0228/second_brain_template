#!/usr/bin/env bash
# agentStop hook for GitHub Copilot — see 10_Agents/harnesses/copilot/wiring.md.
# In the Copilot cloud agent (GITHUB_ACTIONS set) it blocks the agent from
# finishing while `brain validate --check-index` reports errors, with a
# repeat-block guard so an unfixable error cannot loop the session. Local
# sessions always allow: .githooks/pre-commit is the local gate, and a
# half-edited note is normal working-tree state.
# Never reads stdin. Set SECOND_BRAIN_HOOK_DISABLE=1 to skip entirely.
exec python3 - "$(cd "$(dirname "$0")" && pwd)" <<'PY'
import hashlib, json, os, subprocess, sys, tempfile


def emit(decision, reason=None):
    payload = {"decision": decision}
    if reason is not None:
        payload["reason"] = reason
    print(json.dumps(payload))
    sys.exit(0)


if os.environ.get("SECOND_BRAIN_HOOK_DISABLE") == "1":
    emit("allow")
if not os.environ.get("GITHUB_ACTIONS"):
    emit("allow")

script_dir = sys.argv[1]
brain = os.path.normpath(
    os.path.join(script_dir, "..", "..", "10_Agents", "tools", "brain", "brain.py")
)
proc = subprocess.run(
    [sys.executable, brain, "validate", "--check-index", "--json"],
    capture_output=True,
    text=True,
)
if proc.returncode != 1:
    emit("allow")

try:
    errors = json.loads(proc.stdout).get("errors", [])
except ValueError:
    errors = []
lines = [
    f"{e.get('path', '?')}: [{e.get('rule', '?')}] {e.get('message', '')}"
    for e in errors[:10]
]
if len(errors) > 10:
    lines.append(f"... and {len(errors) - 10} more")
summary = "\n".join(lines) or (proc.stdout or proc.stderr)[-2000:]
fix = (
    "Fix these before finishing. Run `python3 10_Agents/tools/brain/brain.py validate` "
    "to see every finding. For stale-index errors run "
    "`python3 10_Agents/tools/brain/brain.py index` and commit the refreshed "
    "10_Agents/tools/brain/vault-index.json."
)

digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()[:16]
state = os.path.join(tempfile.gettempdir(), f"second-brain-agentstop-{digest}")
try:
    with open(state) as fh:
        blocks = int(fh.read())
except (OSError, ValueError):
    blocks = 0
if blocks >= 2:
    emit(
        "allow",
        "brain validate is still failing after repeated blocks; allowing the "
        "session to end - CI will re-check.\n" + summary,
    )
try:
    with open(state, "w") as fh:
        fh.write(str(blocks + 1))
except OSError:
    pass
emit("block", f"brain validate found errors in the vault:\n{summary}\n\n{fix}")
PY
