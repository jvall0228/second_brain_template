"""Integration tests for the merge=regenerate driver (issue #25, spec §8.2).

The vault maps its two committed generated files to a custom merge driver in
`.gitattributes`; clones define the driver with

    git config merge.regenerate.driver true

which keeps ours on conflict (the `true` command exits 0 leaving %A = ours).
Correctness comes from regeneration (post-merge/pre-commit hooks + CI), not
from resolution. These tests build a hermetic throwaway git repo in a tmpdir,
create a two-branch conflicting edit to a fake generated file carrying the
attribute, and assert:

- with the driver configured, the merge succeeds cleanly keeping ours;
- without the driver configured, the merge degrades to a normal conflict
  (today's behavior — strictly additive).

Skips gracefully when git is unavailable.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GIT = shutil.which("git")
SH = shutil.which("sh")


def run_git(cwd, *args, check=True):
    """Run git in cwd with a hermetic config surface; return CompletedProcess."""
    # Layer the hermetic knobs over the real environment (keeps the platform's
    # PATH and required vars) and use os.devnull for portability.
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(cwd),
    }
    proc = subprocess.run(
        [GIT, *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    return proc


@unittest.skipIf(GIT is None, "git not available")
class MergeDriverIntegrationTests(unittest.TestCase):
    """Two-branch conflicting edit to a generated file marked merge=regenerate."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        run_git(self.repo, "init", "-b", "main")
        run_git(self.repo, "config", "user.name", "Test")
        run_git(self.repo, "config", "user.email", "test@example.invalid")

        # Fake committed generated file + the attribute mapping, mirroring the
        # real .gitattributes contract (vault-index.json / code-snippets).
        (self.repo / ".gitattributes").write_text(
            "gen-index.json merge=regenerate\n", encoding="utf-8"
        )
        (self.repo / "gen-index.json").write_text('{"notes": "base"}\n', encoding="utf-8")
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-m", "base")

        # Branch "theirs": conflicting regeneration of the generated file.
        run_git(self.repo, "checkout", "-b", "theirs")
        (self.repo / "gen-index.json").write_text('{"notes": "theirs"}\n', encoding="utf-8")
        run_git(self.repo, "commit", "-am", "theirs regen")

        # Back on main ("ours"): a different regeneration of the same line.
        run_git(self.repo, "checkout", "main")
        (self.repo / "gen-index.json").write_text('{"notes": "ours"}\n', encoding="utf-8")
        run_git(self.repo, "commit", "-am", "ours regen")

    def tearDown(self):
        self._tmp.cleanup()

    def test_configured_driver_merges_clean_keeping_ours(self):
        run_git(self.repo, "config", "merge.regenerate.driver", "true")
        proc = run_git(self.repo, "merge", "--no-edit", "theirs", check=False)
        self.assertEqual(
            proc.returncode,
            0,
            f"merge should succeed with the driver configured:\n{proc.stdout}\n{proc.stderr}",
        )
        content = (self.repo / "gen-index.json").read_text(encoding="utf-8")
        self.assertEqual(content, '{"notes": "ours"}\n', "driver must keep ours (%A as-is)")
        self.assertNotIn("<<<<<<<", content)
        # The merge fully committed — no unmerged paths left behind.
        status = run_git(self.repo, "status", "--porcelain").stdout
        self.assertEqual(status, "")

    def test_unconfigured_clone_degrades_to_normal_conflict(self):
        proc = run_git(self.repo, "merge", "--no-edit", "theirs", check=False)
        self.assertNotEqual(
            proc.returncode, 0, "without the driver, git must fall back to a normal conflict"
        )
        status = run_git(self.repo, "status", "--porcelain").stdout
        self.assertIn("UU gen-index.json", status)


@unittest.skipIf(GIT is None, "git not available")
@unittest.skipIf(SH is None, "no POSIX sh available")
class PostMergeHookTests(unittest.TestCase):
    def test_post_merge_hook_is_best_effort_outside_the_vault(self):
        """The hook must never fail a merge: in a repo with no brain tooling it
        finds nothing to regenerate and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run_git(repo, "init", "-b", "main")
            hook = ROOT / ".githooks" / "post-merge"
            proc = subprocess.run(
                [SH, str(hook)],
                cwd=str(repo),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)


class RepoContractTests(unittest.TestCase):
    """The tracked files carry the attribute mapping and the hook exists."""

    def test_gitattributes_maps_both_generated_files_to_regenerate(self):
        text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        lines = [line.split() for line in text.splitlines() if line and not line.startswith("#")]
        attrs = {parts[0]: parts[1:] for parts in lines}
        self.assertIn("merge=regenerate", attrs.get("10_Agents/tools/brain/vault-index.json", []))
        self.assertIn("merge=regenerate", attrs.get(".vscode/second-brain.code-snippets", []))
        # The newline shield on the byte-compared index must survive.
        self.assertIn("-text", attrs["10_Agents/tools/brain/vault-index.json"])

    def test_gitattributes_documents_the_one_liner_install(self):
        text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("git config merge.regenerate.driver true", text)

    def test_post_merge_hook_exists_and_regenerates_both_files(self):
        hook = ROOT / ".githooks" / "post-merge"
        self.assertTrue(hook.is_file(), "post-merge hook missing")
        text = hook.read_text(encoding="utf-8")
        self.assertIn("brain.py", text)
        self.assertIn("gen_snippets.py", text)
        self.assertTrue(text.rstrip().endswith("exit 0"), "hook must never fail the merge")


if __name__ == "__main__":
    unittest.main()
