#!/usr/bin/env python3
"""Adopter-flow smoke test (issue #20).

Simulates the root README's "Adopt this template" journey in a scratch copy
of the working tree and requires the result to validate clean:

1. Copy the working tree to a scratch directory (dot-paths and __pycache__
   excluded — same corpus brain sees).
2. Build and atomically apply the seeded-example cleanup plan whose sole
   authority is ``adopt_examples.json``. The plan lists every deletion and
   marked reference edit and refuses missing, unsafe, unmarked, or stale
   inputs before mutation; its post-apply validation must pass.
3. "Dumb-fill" the ``01_Profile/`` shells: strip the template-note callouts,
   replace every ``<!-- ... -->`` placeholder with minimal plausible text,
   bump ``updated:``. Deliberately sed-level — this tests the template
   contract, not agent intelligence (``onboard-owner`` is the smart path).
4. Write one conventions-conforming capture note to ``02_Inbox/`` (the M0
   success criterion), then run ``brain index`` and ``brain validate`` in
   the scratch copy. Validation must report zero errors (exit 0 or 2).

Exit 0 on success, 1 with a clear report on any failure. Stdlib only.

Usage:
    python3 10_Agents/tools/adopt_check.py [--repo PATH] [--keep]
    python3 10_Agents/tools/adopt_check.py plan [--repo PATH] [--json] [--output PATH]
    python3 10_Agents/tools/adopt_check.py apply PLAN.json [--repo PATH]
    python3 10_Agents/tools/adopt_check.py recover [--repo PATH]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from adopt_cleanup import (
    AdoptionError,
    apply_plan,
    build_plan,
    plan_human,
    read_plan,
    recover_cleanup,
    write_plan,
)

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_REPO = TOOLS_DIR.parents[1]
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
CALLOUT_RE = re.compile(r"^> \*\*Template note:\*\*.*$\n?", re.MULTILINE)
UPDATED_RE = re.compile(r"^updated:\s*.*$", re.MULTILINE)
FILL_TEXT = "Filled in by the adopter."

INBOX_NOTE_BODY = """---
title: "First Capture After Adoption"
tags:
  - audience/human
  - type/note
  - workflow/draft
updated: {today}
---

# First Capture After Adoption

A first capture written right after adopting the template, per the
[CONVENTIONS](../00_Meta/CONVENTIONS.md) frontmatter and tagging rules. Triage me into the
right PARA directory (see [Inbox rules](README.md)).
"""


def copy_ignore(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if n.startswith(".") or n == "__pycache__"]


def run(repo: Path, keep: bool) -> list[str]:
    failures: list[str] = []
    repo = repo.resolve()

    scratch_root = Path(tempfile.mkdtemp(prefix="adopt-check-"))
    scratch = scratch_root / "vault"
    try:
        try:
            shutil.copytree(repo, scratch, ignore=copy_ignore)
        except (shutil.Error, OSError) as exc:
            # A broken symlink or unreadable file must flow through the
            # failure report, not a traceback (same posture as spec §3).
            failures.append(f"cannot copy working tree to scratch: {exc}")
            return failures

        # Step: exact, all-or-nothing seeded-example cleanup.
        try:
            apply_plan(scratch, build_plan(scratch))
        except AdoptionError as exc:
            failures.append(str(exc))
            return failures

        # Step: dumb-fill the 01_Profile/ shells.
        today = _dt.date.today().isoformat()
        for shell in sorted((scratch / "01_Profile").glob("*.md")):
            if shell.name == "README.md":
                continue
            text = shell.read_text(encoding="utf-8")
            text = CALLOUT_RE.sub("", text)
            text = COMMENT_RE.sub(FILL_TEXT, text)
            text = UPDATED_RE.sub(f"updated: {today}", text, count=1)
            shell.write_text(text, encoding="utf-8")

        # Step: first conventions-conforming Inbox capture (M0 criterion).
        (scratch / "02_Inbox" / f"{today}-first-capture-after-adoption.md").write_text(
            INBOX_NOTE_BODY.format(today=today), encoding="utf-8"
        )

        # Step: brain index && brain validate — zero errors required.
        brain = scratch / "10_Agents" / "tools" / "brain" / "brain.py"
        for cmd, ok_codes in (("index", {0}), ("validate", {0, 2})):
            proc = subprocess.run(
                [sys.executable, str(brain), cmd],
                capture_output=True,
                text=True,
            )
            if proc.returncode not in ok_codes:
                failures.append(
                    f"brain {cmd} failed in the adopted scratch copy "
                    f"(exit {proc.returncode}):\n{proc.stdout}{proc.stderr}"
                )
    finally:
        if keep:
            print(f"adopt_check: scratch copy kept at {scratch}")
        else:
            shutil.rmtree(scratch_root, ignore_errors=True)

    return failures


def _plan_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Preview the atomic seeded-example cleanup")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--json", action="store_true", help="print the machine-readable plan")
    parser.add_argument("--output", type=Path, help="write the machine-readable plan atomically")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(args.repo.resolve())
        if args.output:
            repo = args.repo.resolve()
            output = args.output.resolve()
            if output == repo or repo in output.parents:
                raise AdoptionError("cleanup plan output must be outside the repository")
            write_plan(args.output, plan)
        if args.json:
            import json

            print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(plan_human(plan), end="")
            if args.output:
                print(f"Machine-readable plan: {args.output.resolve()}")
        return 0
    except AdoptionError as exc:
        print(f"ADOPT-PLAN FAIL: {exc}", file=sys.stderr)
        return 1


def _apply_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Apply an approved seeded-example cleanup plan")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    args = parser.parse_args(argv)
    try:
        repo = args.repo.resolve()
        plan_path = args.plan.resolve()
        if plan_path == repo or repo in plan_path.parents:
            raise AdoptionError("cleanup plan input must be outside the repository")
        apply_plan(repo, read_plan(plan_path))
        print("adopt cleanup: OK — bundle removed atomically and validation passed")
        return 0
    except AdoptionError as exc:
        print(f"ADOPT-APPLY FAIL: {exc}", file=sys.stderr)
        return 1


def _recover_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Recover an interrupted adoption cleanup")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    args = parser.parse_args(argv)
    try:
        preserved = recover_cleanup(args.repo.resolve())
        print("adopt cleanup recovery: OK — original bundle restored and lock removed")
        if preserved:
            print("Preserved concurrent paths for owner review:")
            for path in preserved:
                print(f"  - {path}")
        return 0
    except AdoptionError as exc:
        print(f"ADOPT-RECOVER FAIL: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "plan":
        return _plan_main(argv[1:])
    if argv and argv[0] == "apply":
        return _apply_main(argv[1:])
    if argv and argv[0] == "recover":
        return _recover_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO,
                        help="repository root to check (default: this repo)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the scratch copy for inspection")
    args = parser.parse_args(argv)

    failures = run(args.repo, args.keep)
    if failures:
        for f in failures:
            print(f"ADOPT-CHECK FAIL: {f}", file=sys.stderr)
        print(f"adopt_check: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("adopt_check: OK — fresh adoption validates clean (0 errors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
