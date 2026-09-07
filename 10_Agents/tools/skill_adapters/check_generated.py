#!/usr/bin/env python3
"""Read-only freshness checks for generated commit surfaces and pushed ref tips."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import hook_transaction as transaction


def check(root: Path, env: dict[str, str] | None = None) -> bool:
    process_env = {**(os.environ if env is None else env), "PYTHONDONTWRITEBYTECODE": "1"}
    ok = True
    checks = (
        ("10_Agents/tools/brain/brain.py", "bootstrap", "--check", "--shared-only"),
        ("10_Agents/tools/vscode/gen_snippets.py", "--check"),
        ("10_Agents/tools/skill_adapters/gen_skill_adapters.py", "--check"),
        ("10_Agents/tools/brain/brain.py", "artifacts", "--check", "--shared-only"),
    )
    for script, *args in checks:
        result = subprocess.run(["python3", str(root / script), *args], cwd=root,
                                env=process_env, stdout=subprocess.DEVNULL)
        ok = result.returncode == 0 and ok
    # index_corpus explicitly excludes every environment; avoid environment
    # selection and full unrelated vault validation in this lightweight gate.
    code = (
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(sys.argv[1]) / '10_Agents/tools/brain'))\n"
        "import brain\nroot = Path(sys.argv[1])\n"
        "notes, assets = brain.index_corpus(root)\n"
        "expected = brain.serialize(brain.reduce_restricted(brain.build_index(root, notes, assets)))\n"
        "path = root / brain.INDEX_RELPATH\n"
        "fresh = path.is_file() and not path.is_symlink() and path.read_bytes() == expected\n"
        "if not fresh: print('stale committed vault index — run brain index and commit the output', file=sys.stderr)\n"
        "raise SystemExit(0 if fresh else 1)\n"
    )
    result = subprocess.run(["python3", "-c", code, str(root)], cwd=root, env=process_env)
    return result.returncode == 0 and ok


def check_revision(root: Path, revision: str) -> bool:
    commit = os.fsdecode(transaction.git(root, "rev-parse", "--verify", f"{revision}^{{commit}}")).strip()
    with tempfile.TemporaryDirectory(prefix="second-brain-generated-check-") as td:
        tree, index, env = transaction.export_index(root, Path(td), transaction.index_path(root), revision=commit)
        return check(tree, env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--revision", help="check this committed tree, ignoring worktree edits")
    mode.add_argument("--pre-push", action="store_true", help="read Git pre-push ref updates from stdin")
    args = parser.parse_args()
    root = args.repo.resolve()
    try:
        if args.pre_push:
            revisions = set()
            for line in sys.stdin:
                fields = line.split()
                if len(fields) != 4 or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", fields[1]) is None:
                    raise transaction.TransactionError("malformed pre-push ref update")
                if set(fields[1]) != {"0"}:
                    revisions.add(fields[1])
            return 0 if all(check_revision(root, revision) for revision in sorted(revisions)) else 1
        return 0 if (check_revision(root, args.revision) if args.revision else check(root)) else 1
    except (OSError, transaction.TransactionError) as exc:
        print(f"generated consistency: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
