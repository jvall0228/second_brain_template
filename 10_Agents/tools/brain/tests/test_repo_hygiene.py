"""Repo-wide hygiene guards.

Born from the M11 phase gate: a merge resolution staged committed conflict
markers into a README unseen. This suite makes that class of mistake fail
the test run instead of shipping.

Run via the tools runner:
    python3 10_Agents/tools/run_tests.py
"""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GIT = shutil.which("git")

MARKERS = ("<<<<<<< ", ">>>>>>> ")
# ======= alone is legal markdown (setext underline), so require the
# angle-bracket markers; a real conflict always carries those.

TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".yml", ".yaml", ".txt", ".sh", ".mdc",
    ".gitignore", ".gitattributes", ".code-snippets",
}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        [GIT, "ls-files", "-z"], cwd=str(ROOT), capture_output=True, text=True
    ).stdout
    return [ROOT / p for p in out.split("\0") if p]


@unittest.skipIf(GIT is None, "git not available")
class ConflictMarkerTests(unittest.TestCase):
    def test_no_committed_conflict_markers(self):
        offenders = []
        for path in tracked_files():
            if path.suffix not in TEXT_SUFFIXES and path.name not in (
                ".gitignore",
                ".gitattributes",
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if any(line.startswith(m) for m in MARKERS):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}")
        self.assertEqual(
            offenders, [], f"committed merge-conflict markers: {offenders}"
        )


if __name__ == "__main__":
    unittest.main()
