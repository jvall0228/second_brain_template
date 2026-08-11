#!/usr/bin/env python3
"""Adopter-flow smoke test (issue #20).

Simulates the root README's "Adopt this template" journey in a scratch copy
of the working tree and requires the result to validate clean:

1. Copy the working tree to a scratch directory (dot-paths and __pycache__
   excluded — same corpus brain sees).
2. Delete the seeded examples and shipped capture notes. The delete list is
   data-driven from ``adopt_examples.json`` (one source of truth); every
   listed path must actually exist, and the list must agree with the bullet
   list under "Delete the seeded examples" in the root README, so neither
   can drift from reality or from each other.
3. Drop the example-pointer lines in structural docs — every such line is
   marked with the (case-insensitive) cleanup marker phrase from the data
   file ("delete once you've seen the pattern"). A wikilink to a seeded
   example WITHOUT that marker survives to step 5 and turns the check red.
4. "Dumb-fill" the ``01_Profile/`` shells: strip the template-note callouts,
   replace every ``<!-- ... -->`` placeholder with minimal plausible text,
   bump ``updated:``. Deliberately sed-level — this tests the template
   contract, not agent intelligence (``onboard-owner`` is the smart path).
5. Write one conventions-conforming capture note to ``02_Inbox/`` (the M0
   success criterion), then run ``brain index`` and ``brain validate`` in
   the scratch copy. Validation must report zero errors (exit 0 or 2).

Exit 0 on success, 1 with a clear report on any failure. Stdlib only.

Usage:
    python3 10_Agents/tools/adopt_check.py [--repo PATH] [--keep]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_REPO = TOOLS_DIR.parents[1]
DATA_FILE_REL = "10_Agents/tools/adopt_examples.json"

README_HEADER = "**Delete the seeded examples**"
BULLET_RE = re.compile(r"^\s*-\s+`([^`]+)`")
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
[[00_Meta/conventions]] frontmatter and tagging rules. Triage me into the
right PARA directory (see [[02_Inbox/README]]).
"""


def copy_ignore(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if n.startswith(".") or n == "__pycache__"]


def readme_delete_list(readme_text: str) -> list[str] | None:
    """The backticked paths bulleted under the 'Delete the seeded examples'
    step, or None if the header is missing."""
    lines = readme_text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if README_HEADER in l)
    except StopIteration:
        return None
    items: list[str] = []
    for line in lines[start + 1 :]:
        m = BULLET_RE.match(line)
        if not m:
            break  # first non-bullet line (blank or prose) ends the list
        items.append(m.group(1))
    return items


def run(repo: Path, keep: bool) -> list[str]:
    failures: list[str] = []
    repo = repo.resolve()

    data_file = repo / DATA_FILE_REL  # read from the checked repo, so
    try:                              # scratch-copy tests see their own list
        data = json.loads(data_file.read_text(encoding="utf-8"))
        delete_list: list[str] = data["delete"]
        marker: str = data["cleanup_marker"].casefold()
    except (OSError, KeyError, ValueError) as exc:
        return [f"cannot read {DATA_FILE_REL}: {exc}"]

    # Anti-drift: README bullet list must equal the data file's list.
    readme = repo / "README.md"
    if not readme.is_file():
        return [f"no README.md at {repo}"]
    listed = readme_delete_list(readme.read_text(encoding="utf-8"))
    if listed is None:
        failures.append(f'README.md has no "{README_HEADER}" step')
    elif listed != delete_list:
        failures.append(
            "README delete list and adopt_examples.json disagree:\n"
            f"  README only: {sorted(set(listed) - set(delete_list)) or '(none)'}\n"
            f"  data file only: {sorted(set(delete_list) - set(listed)) or '(none)'}\n"
            "  (order must match too — README.md is rendered from the data file)"
        )

    scratch_root = Path(tempfile.mkdtemp(prefix="adopt-check-"))
    scratch = scratch_root / "vault"
    try:
        shutil.copytree(repo, scratch, ignore=copy_ignore)

        # Step: delete the seeded examples; every listed path must exist.
        for entry in delete_list:
            target = scratch / entry.rstrip("/")
            if entry.endswith("/"):
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    failures.append(f"listed directory does not exist: {entry}")
            elif target.is_file():
                target.unlink()
            else:
                failures.append(f"listed file does not exist: {entry}")

        # Step: drop marker-tagged example-pointer lines in structural docs.
        removed = 0
        for md in sorted(scratch.rglob("*.md")):
            lines = md.read_text(encoding="utf-8").split("\n")
            kept = [l for l in lines if marker not in l.casefold()]
            if len(kept) != len(lines):
                removed += len(lines) - len(kept)
                md.write_text("\n".join(kept), encoding="utf-8")
        if removed == 0:
            failures.append(
                f'no line carried the cleanup marker "{data["cleanup_marker"]}" — '
                "structural docs no longer tag their example pointers"
            )

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


def main(argv: list[str] | None = None) -> int:
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
