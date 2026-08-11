"""Tests for the adopter-flow smoke test (10_Agents/tools/adopt_check.py, issue #20).

Lives in brain/tests/ so the shared runner (run_tests.py, issue #5) discovers
it — adopt_check has no tests/ directory of its own because it is a single
script, and this tree is already excluded from the vault corpus.

The suite invokes adopt_check.py via subprocess, exactly as CI does:
- green on the real repository (the shipped adoption contract holds);
- red when a kept structural doc gains an unmarked canonical wikilink to a
  seeded example (the issue's acceptance criterion);
- red when the data file lists a path that no longer exists;
- red when the README's delete list drifts from adopt_examples.json.

Red cases run against modified scratch copies of the real repo — copying and
validating this vault takes well under a second per run.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ADOPT_CHECK = REPO_ROOT / "10_Agents" / "tools" / "adopt_check.py"


def run_adopt_check(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ADOPT_CHECK), "--repo", str(repo)],
        capture_output=True,
        text=True,
    )


def copy_repo(dst: Path) -> None:
    shutil.copytree(
        REPO_ROOT,
        dst,
        ignore=lambda _d, names: [
            n for n in names if n.startswith(".") or n == "__pycache__"
        ],
    )


class AdoptCheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="adopt-check-test-")
        self.addCleanup(self._tmp.cleanup)
        self.copy = Path(self._tmp.name) / "repo"

    def test_green_on_real_repo(self):
        proc = run_adopt_check(REPO_ROOT)
        self.assertEqual(
            proc.returncode, 0,
            f"adopt_check must pass on the shipped repo:\n{proc.stdout}{proc.stderr}",
        )
        self.assertIn("adopt_check: OK", proc.stdout)

    def test_red_on_canonical_wikilink_to_seeded_example(self):
        # Acceptance criterion (issue #20): a kept doc linking AT a seeded
        # example (without the cleanup marker) must turn the check red.
        copy_repo(self.copy)
        index = self.copy / "00_Meta" / "index.md"
        index.write_text(
            index.read_text(encoding="utf-8")
            + "\n- [[06_Resources/example-resource]] pinned reference\n",
            encoding="utf-8",
        )
        proc = run_adopt_check(self.copy)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("unresolved-link", proc.stderr)
        self.assertIn("example-resource", proc.stderr)

    def test_red_when_listed_example_is_missing(self):
        # The delete list may not drift from reality.
        copy_repo(self.copy)
        (self.copy / "03_Journal" / "ideas" / "example-idea.md").unlink()
        proc = run_adopt_check(self.copy)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("does not exist", proc.stderr)
        self.assertIn("example-idea", proc.stderr)

    @unittest.skipUnless(os.name == "posix", "relies on POSIX symlinks")
    def test_red_not_traceback_on_broken_symlink(self):
        # An unreadable entry in the working tree flows through the failure
        # report (spec §3 posture), never an unhandled shutil traceback.
        copy_repo(self.copy)
        os.symlink("../missing-target.md", self.copy / "02_Inbox" / "dangling.md")
        proc = run_adopt_check(self.copy)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn("cannot copy working tree", proc.stderr)

    def test_red_on_readme_drift(self):
        # README's bullet list and adopt_examples.json must agree.
        copy_repo(self.copy)
        readme = self.copy / "README.md"
        text = readme.read_text(encoding="utf-8")
        needle = "   - `06_Resources/example-resource.md`\n"
        self.assertIn(needle, text)
        readme.write_text(text.replace(needle, "", 1), encoding="utf-8")
        proc = run_adopt_check(self.copy)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("disagree", proc.stderr)


if __name__ == "__main__":
    unittest.main()
