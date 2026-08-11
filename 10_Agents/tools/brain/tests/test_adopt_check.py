"""Tests for the adopter-flow smoke test (10_Agents/tools/adopt_check.py, issue #20).

Lives in brain/tests/ so the shared runner (run_tests.py, issue #5) discovers
it — adopt_check has no tests/ directory of its own because it is a single
script, and this tree is already excluded from the vault corpus.

The suite exercises both the CI smoke command and the atomic planner/apply
library: exact bundle scope, cross-links and aliases, unsafe paths, dirty/stale
plans, transactional rollback, and post-apply validation.

Red cases run against modified scratch copies of the real repo — copying and
validating this vault takes well under a second per run.
"""

import os
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[4]
ADOPT_CHECK = REPO_ROOT / "10_Agents" / "tools" / "adopt_check.py"
TOOLS_DIR = REPO_ROOT / "10_Agents" / "tools"
sys.path.insert(0, str(TOOLS_DIR))
from adopt_cleanup import (  # noqa: E402
    AdoptionError,
    apply_plan,
    build_plan,
    recover_cleanup,
    write_plan,
)


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
        self.assertIn("unmarked surviving references", proc.stderr)
        self.assertIn("example-resource", proc.stderr)

    def test_plan_covers_reported_four_cross_links_as_one_bundle(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        deleted = {row["path"] for row in plan["delete"]}
        edited = {row["path"] for row in plan["edits"]}
        # Reported #84 fallout: two surviving sources are edited, while the
        # other two sources disappear with the same atomic bundle.
        self.assertIn("00_Meta/index.md", edited)
        self.assertIn("04_Projects/README.md", edited)
        self.assertIn("05_Areas/example-area", deleted)
        self.assertIn("03_Journal/periodic/weekly/2025-W03-review.md", deleted)
        self.assertIn("04_Projects/example-project", deleted)

    def test_plan_is_deterministic_and_lists_exact_marked_edits(self):
        copy_repo(self.copy)
        first = build_plan(self.copy)
        second = build_plan(self.copy)
        self.assertEqual(first, second)
        self.assertEqual(len(first["delete"]), 9)
        self.assertEqual(
            [row["path"] for row in first["edits"]],
            sorted(row["path"] for row in first["edits"]),
        )
        for row in first["edits"]:
            self.assertTrue(row["removeLines"])
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(row["desiredSha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            [row["path"] for row in first["regenerate"]],
            ["10_Agents/tools/brain/vault-index.json"],
        )
        self.assertEqual(
            [row["path"] for row in first["dependencies"]],
            ["10_Agents/tools/brain/brain.py"],
        )
        project = next(row for row in first["delete"] if row["path"] == "04_Projects/example-project")
        self.assertTrue(project["contents"])
        self.assertIn(
            "decision-records/2025-01-10-example-decision.md",
            {row["path"] for row in project["contents"]},
        )
        for item in project["contents"]:
            self.assertIn(item["kind"], {"directory", "file"})
            if item["kind"] == "file":
                self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_manifest_is_the_only_enumerated_bundle_authority(self):
        data = json.loads((REPO_ROOT / "10_Agents/tools/adopt_examples.json").read_text(encoding="utf-8"))
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for target in data["delete"]:
            with self.subTest(target=target):
                self.assertNotIn(f"`{target}`", readme)

    def test_marked_alias_is_planned_but_unmarked_alias_refuses(self):
        copy_repo(self.copy)
        kept = self.copy / "06_Resources/kept-reference.md"
        kept.write_text(
            "---\ntitle: Kept\ntags:\n  - type/reference\nupdated: 2026-08-11\n---\n\n"
            "- [[04_Projects/example-project/README|Aliased example]]\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(AdoptionError, "unmarked surviving references"):
            build_plan(self.copy)
        kept.write_text(
            kept.read_text(encoding="utf-8").replace(
                "Aliased example]]", "Aliased example]] — Delete once you've seen the pattern"
            ),
            encoding="utf-8",
        )
        plan = build_plan(self.copy)
        self.assertIn("06_Resources/kept-reference.md", {row["path"] for row in plan["edits"]})

    def test_restricted_marker_line_is_redacted_from_serialized_plan(self):
        copy_repo(self.copy)
        secret = "private context must not enter the plan"
        kept = self.copy / "06_Resources/private-reference.md"
        kept.write_text(
            "---\ntitle: Private\ntags:\n  - type/reference\n  - restricted/private\n"
            "updated: 2026-08-11\n---\n\n"
            f"- {secret}: [[04_Projects/example-project/README|Alias]] — "
            "Delete once you've seen the pattern\n",
            encoding="utf-8",
        )
        plan = build_plan(self.copy)
        serialized = json.dumps(plan)
        self.assertNotIn(secret, serialized)
        row = next(row for row in plan["edits"] if row["path"] == "06_Resources/private-reference.md")
        self.assertIsNone(row["removeLines"][0]["text"])
        self.assertTrue(row["removeLines"][0]["restricted"])

    def test_apply_removes_whole_bundle_and_marked_references(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        apply_plan(self.copy, plan)
        for row in plan["delete"]:
            self.assertFalse((self.copy / row["path"]).exists(), row["path"])
        marker = "delete once you've seen the pattern"
        for row in plan["edits"]:
            text = (self.copy / row["path"]).read_text(encoding="utf-8").casefold()
            self.assertNotIn(marker, text)
        index_text = (self.copy / "10_Agents/tools/brain/vault-index.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("04_Projects/example-project/README.md", index_text)

    def test_stale_plan_refuses_before_mutation(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        target = self.copy / "04_Projects/README.md"
        before = target.read_bytes()
        target.write_bytes(before + b"\nchanged after preview\n")
        with self.assertRaisesRegex(AdoptionError, "stale cleanup plan"):
            apply_plan(self.copy, plan)
        self.assertTrue((self.copy / "04_Projects/example-project").is_dir())

    def test_empty_directory_change_makes_plan_stale(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        (self.copy / "04_Projects/example-project/new-empty-directory").mkdir()
        with self.assertRaisesRegex(AdoptionError, "stale cleanup plan"):
            apply_plan(self.copy, plan)
        self.assertTrue((self.copy / "04_Projects/example-project").is_dir())

    def test_dirty_planned_path_refuses_before_mutation(self):
        main = Path(self._tmp.name) / "main"
        copy_repo(main)
        subprocess.run(["git", "init", "-q"], cwd=main, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=main, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=main, check=True)
        subprocess.run(["git", "add", "."], cwd=main, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=main, check=True)
        subprocess.run(
            ["git", "worktree", "add", "-qb", "adopt-test", str(self.copy)],
            cwd=main,
            check=True,
        )
        self.assertTrue((self.copy / ".git").is_file(), "fixture must exercise linked-worktree metadata")
        plan = build_plan(self.copy)
        target = self.copy / "04_Projects/README.md"
        target.write_text(target.read_text(encoding="utf-8") + "\ndirty\n", encoding="utf-8")
        with self.assertRaisesRegex(AdoptionError, "paths are dirty"):
            apply_plan(self.copy, plan)
        self.assertTrue((self.copy / "04_Projects/example-project").is_dir())

    def test_dirty_brain_dependency_refuses_in_linked_worktree(self):
        main = Path(self._tmp.name) / "main"
        copy_repo(main)
        subprocess.run(["git", "init", "-q"], cwd=main, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=main, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=main, check=True)
        subprocess.run(["git", "add", "."], cwd=main, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=main, check=True)
        subprocess.run(
            ["git", "worktree", "add", "-qb", "brain-dirty-test", str(self.copy)],
            cwd=main,
            check=True,
        )
        plan = build_plan(self.copy)
        brain = self.copy / "10_Agents/tools/brain/brain.py"
        brain.write_bytes(brain.read_bytes() + b"\n# late validator change\n")
        with self.assertRaisesRegex(AdoptionError, "paths are dirty"):
            apply_plan(self.copy, plan)
        self.assertTrue((self.copy / "04_Projects/example-project").is_dir())

    def test_ignored_or_untracked_directory_occupant_refuses_preview(self):
        copy_repo(self.copy)
        (self.copy / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.copy, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.copy, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.copy, check=True)
        subprocess.run(["git", "add", "."], cwd=self.copy, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.copy, check=True)
        late = self.copy / "04_Projects/example-project/__pycache__/owner-notes.pyc"
        late.parent.mkdir()
        late.write_bytes(b"owner bytes")
        with self.assertRaisesRegex(AdoptionError, "ignored or untracked occupants"):
            build_plan(self.copy)
        self.assertEqual(late.read_bytes(), b"owner bytes")

    def test_cli_requires_plan_output_outside_repository(self):
        copy_repo(self.copy)
        output = self.copy / "adopt-plan.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(ADOPT_CHECK),
                "plan",
                "--repo",
                str(self.copy),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("must be outside the repository", proc.stderr)
        self.assertFalse(output.exists())

    def test_cli_requires_plan_input_outside_repository(self):
        copy_repo(self.copy)
        plan_path = self.copy / "adopt-plan.json"
        plan_path.write_text(json.dumps(build_plan(self.copy)), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(ADOPT_CHECK),
                "apply",
                str(plan_path),
                "--repo",
                str(self.copy),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("input must be outside the repository", proc.stderr)
        self.assertTrue((self.copy / "04_Projects/example-project").is_dir())

    def test_plan_output_refuses_foreign_schema_and_symlink(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        output = Path(self._tmp.name) / "plan.json"
        foreign = b'{"schemaVersion": 1, "owner": "not this tool"}\n'
        output.write_bytes(foreign)
        with self.assertRaisesRegex(AdoptionError, "foreign cleanup-plan output"):
            write_plan(output, plan)
        self.assertEqual(output.read_bytes(), foreign)

        if hasattr(os, "symlink"):
            target = Path(self._tmp.name) / "target.json"
            target.write_text("owner file\n", encoding="utf-8")
            output.unlink()
            os.symlink(target, output)
            with self.assertRaisesRegex(AdoptionError, "symlinked cleanup-plan output"):
                write_plan(output, plan)
            self.assertEqual(target.read_text(encoding="utf-8"), "owner file\n")

    def test_validation_failure_rolls_back_every_change(self):
        copy_repo(self.copy)
        # Unrelated invalid content is deliberately present before planning;
        # the transaction must restore all planned files when final validate fails.
        (self.copy / "06_Resources/invalid.md").write_text("no frontmatter\n", encoding="utf-8")
        plan = build_plan(self.copy)
        originals = {
            row["path"]: (self.copy / row["path"]).read_bytes()
            for row in plan["edits"]
        }
        index = self.copy / "10_Agents/tools/brain/vault-index.json"
        index_original = index.read_bytes()
        with self.assertRaisesRegex(AdoptionError, "atomic cleanup rolled back"):
            apply_plan(self.copy, plan)
        for path, body in originals.items():
            self.assertEqual((self.copy / path).read_bytes(), body)
        for row in plan["delete"]:
            self.assertTrue((self.copy / row["path"]).exists(), row["path"])
        self.assertEqual(index.read_bytes(), index_original)

    def test_interruption_rolls_back_every_change(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        originals = {
            row["path"]: (self.copy / row["path"]).read_bytes()
            for row in plan["edits"]
        }
        with mock.patch("adopt_cleanup._post_apply_validate", side_effect=KeyboardInterrupt()):
            with self.assertRaisesRegex(AdoptionError, "atomic cleanup rolled back"):
                apply_plan(self.copy, plan)
        for path, body in originals.items():
            self.assertEqual((self.copy / path).read_bytes(), body)
        for row in plan["delete"]:
            self.assertTrue((self.copy / row["path"]).exists(), row["path"])

    def test_late_file_before_delete_move_is_authenticated_and_rolled_back(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        target = (self.copy / "04_Projects/example-project").resolve()
        late = target / "__pycache__/owner-notes.pyc"
        real_replace = os.replace
        injected = False

        def inject_before_move(src, dst, *args, **kwargs):
            nonlocal injected
            if not injected and Path(src) == target:
                late.parent.mkdir()
                late.write_bytes(b"late owner bytes")
                injected = True
            return real_replace(src, dst, *args, **kwargs)

        with mock.patch("adopt_cleanup.os.replace", side_effect=inject_before_move):
            with self.assertRaisesRegex(AdoptionError, "moved source failed authentication"):
                apply_plan(self.copy, plan)
        self.assertEqual(late.read_bytes(), b"late owner bytes")
        for row in plan["delete"]:
            self.assertTrue((self.copy / row["path"]).exists(), row["path"])

    def test_manifest_change_after_final_preflight_rolls_back(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        manifest = (self.copy / "10_Agents/tools/adopt_examples.json").resolve()
        first_edit = (self.copy / plan["edits"][0]["path"]).resolve()
        real_replace = os.replace
        injected = False

        def inject_manifest_change(src, dst, *args, **kwargs):
            nonlocal injected
            if not injected and Path(src) == first_edit:
                manifest.write_bytes(manifest.read_bytes() + b" \n")
                injected = True
            return real_replace(src, dst, *args, **kwargs)

        with mock.patch("adopt_cleanup.os.replace", side_effect=inject_manifest_change):
            with self.assertRaisesRegex(AdoptionError, "manifest changed during apply"):
                apply_plan(self.copy, plan)
        self.assertTrue(manifest.read_bytes().endswith(b" \n"))
        for row in plan["delete"]:
            self.assertTrue((self.copy / row["path"]).exists(), row["path"])

    def test_recreated_delete_path_is_preserved_before_rollback(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        target = (self.copy / "04_Projects/example-project").resolve()
        real_replace = os.replace
        injected = False

        def recreate_after_move(src, dst, *args, **kwargs):
            nonlocal injected
            result = real_replace(src, dst, *args, **kwargs)
            if not injected and Path(src) == target:
                target.mkdir()
                (target / "late-owner.txt").write_text("preserve me\n", encoding="utf-8")
                injected = True
            return result

        with mock.patch("adopt_cleanup.os.replace", side_effect=recreate_after_move):
            with self.assertRaisesRegex(AdoptionError, "preserved late paths"):
                apply_plan(self.copy, plan)
        self.assertTrue((target / "README.md").is_file(), "original bundle must be restored")
        recoveries = list(self.copy.glob(".adopt-recovery-*/**/late-owner.txt"))
        self.assertEqual(len(recoveries), 1)
        self.assertEqual(recoveries[0].read_text(encoding="utf-8"), "preserve me\n")

    def test_recreated_edit_path_is_never_overwritten_and_is_preserved(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        target = (self.copy / plan["edits"][0]["path"]).resolve()
        original = target.read_bytes()
        late = b"late concurrent owner edit\n"
        real_link = os.link
        injected = False

        def recreate_before_install(src, dst, *args, **kwargs):
            nonlocal injected
            if not injected and Path(dst) == target:
                target.write_bytes(late)
                injected = True
            return real_link(src, dst, *args, **kwargs)

        with mock.patch("adopt_cleanup.os.link", side_effect=recreate_before_install):
            with self.assertRaisesRegex(AdoptionError, "preserved late paths"):
                apply_plan(self.copy, plan)
        self.assertTrue(injected)
        self.assertEqual(target.read_bytes(), original)
        recoveries = list(self.copy.glob(".adopt-recovery-*/**/*"))
        self.assertTrue(any(path.is_file() and path.read_bytes() == late for path in recoveries))

    def test_file_to_directory_swap_fails_kind_authentication_and_restores_directory(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        row = next(item for item in plan["delete"] if item["kind"] == "file")
        target = (self.copy / row["path"]).resolve()
        original = target.read_bytes()
        real_replace = os.replace
        injected = False

        def replace_file_with_directory(src, dst, *args, **kwargs):
            nonlocal injected
            if not injected and Path(src) == target:
                target.unlink()
                target.mkdir()
                (target / "owner-layout.md").write_bytes(original)
                injected = True
            return real_replace(src, dst, *args, **kwargs)

        with mock.patch("adopt_cleanup.os.replace", side_effect=replace_file_with_directory):
            with self.assertRaisesRegex(AdoptionError, "moved source failed authentication"):
                apply_plan(self.copy, plan)
        self.assertTrue(injected)
        self.assertTrue(target.is_dir())
        self.assertEqual((target / "owner-layout.md").read_bytes(), original)

    def test_lock_retains_interrupted_transaction_and_recover_restores_it(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        with mock.patch("adopt_cleanup._post_apply_validate", side_effect=KeyboardInterrupt()), mock.patch(
            "adopt_cleanup._rollback_transaction", return_value=(["injected rollback stop"], [])
        ):
            with self.assertRaisesRegex(AdoptionError, "rollback failures"):
                apply_plan(self.copy, plan)
        self.assertTrue((self.copy / ".adopt-cleanup.lock").is_file())
        with self.assertRaisesRegex(AdoptionError, "cleanup lock exists"):
            apply_plan(self.copy, plan)
        self.assertEqual(recover_cleanup(self.copy), [])
        self.assertFalse((self.copy / ".adopt-cleanup.lock").exists())
        for row in plan["delete"]:
            self.assertTrue((self.copy / row["path"]).exists(), row["path"])

    def test_independent_index_mismatch_rolls_back(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        original_index = (self.copy / "10_Agents/tools/brain/vault-index.json").read_bytes()
        index_path = (self.copy / "10_Agents/tools/brain/vault-index.json").resolve()
        from adopt_cleanup import _atomic_write as real_atomic_write

        def corrupt_index(path, data, mode):
            if Path(path) == index_path:
                return real_atomic_write(path, b"not-the-generated-index\n", mode)
            return real_atomic_write(path, data, mode)

        with mock.patch("adopt_cleanup._atomic_write", side_effect=corrupt_index):
            with self.assertRaisesRegex(AdoptionError, "independent trusted computation"):
                apply_plan(self.copy, plan)
        self.assertEqual(
            (self.copy / "10_Agents/tools/brain/vault-index.json").read_bytes(),
            original_index,
        )

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "secure descriptor traversal unavailable")
    def test_brain_file_or_ancestor_swap_never_executes_external_python(self):
        for swap_kind in ("file", "ancestor"):
            with self.subTest(swap_kind=swap_kind):
                repo = Path(self._tmp.name) / f"brain-swap-{swap_kind}"
                copy_repo(repo)
                marker = Path(self._tmp.name) / f"external-executed-{swap_kind}"
                outside = Path(self._tmp.name) / f"outside-brain-{swap_kind}"
                real_open = os.open
                injected = False

                if swap_kind == "file":
                    outside.write_text(
                        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
                        encoding="utf-8",
                    )
                    target = repo / "10_Agents/tools/brain/brain.py"
                    held = repo / "10_Agents/tools/brain/brain.held"
                    trigger = "brain.py"
                else:
                    outside.mkdir()
                    (outside / "brain.py").write_text(
                        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
                        encoding="utf-8",
                    )
                    target = repo / "10_Agents/tools/brain"
                    held = repo / "10_Agents/tools/brain-held"
                    trigger = "brain"

                def swap_before_open(path, flags, *args, **kwargs):
                    nonlocal injected
                    if not injected and path == trigger and kwargs.get("dir_fd") is not None:
                        target.rename(held)
                        os.symlink(outside, target)
                        injected = True
                    return real_open(path, flags, *args, **kwargs)

                with mock.patch("adopt_cleanup.os.open", side_effect=swap_before_open):
                    with self.assertRaises(AdoptionError):
                        build_plan(repo)
                self.assertTrue(injected, "test must reach the vulnerable open boundary")
                self.assertFalse(marker.exists(), "external Python must never execute")

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "secure descriptor traversal unavailable")
    def test_deletion_top_swap_never_inventories_external_directory(self):
        copy_repo(self.copy)
        target = (self.copy / "04_Projects/example-project").resolve()
        held = (self.copy / "04_Projects/example-project-held").resolve()
        outside = Path(self._tmp.name) / "outside-example-project"
        outside.mkdir()
        secret_name = "private-owner-filename-never-previewed.md"
        secret = outside / secret_name
        secret.write_text("private bytes never hashed\n", encoding="utf-8")
        real_open = os.open
        injected = False

        def swap_before_open(path, flags, *args, **kwargs):
            nonlocal injected
            if not injected and path == "example-project" and kwargs.get("dir_fd") is not None:
                target.rename(held)
                os.symlink(outside, target)
                injected = True
            return real_open(path, flags, *args, **kwargs)

        with mock.patch("adopt_cleanup.os.open", side_effect=swap_before_open):
            with self.assertRaises(AdoptionError) as raised:
                build_plan(self.copy)
        self.assertTrue(injected, "test must reach the vulnerable inventory boundary")
        self.assertNotIn(secret_name, str(raised.exception))
        self.assertEqual(secret.read_text(encoding="utf-8"), "private bytes never hashed\n")

    def test_red_when_listed_example_is_missing(self):
        # The delete list may not drift from reality.
        copy_repo(self.copy)
        (self.copy / "03_Journal" / "ideas" / "example-idea.md").unlink()
        proc = run_adopt_check(self.copy)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("missing expected adoption target", proc.stderr)
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

    def test_manifest_rejects_path_traversal_and_case_collisions(self):
        copy_repo(self.copy)
        manifest = self.copy / "10_Agents/tools/adopt_examples.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["schema_version"] = True
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(AdoptionError, "schema_version"):
            build_plan(self.copy)
        data["schema_version"] = 1
        data["delete"].append("../outside.md")
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(AdoptionError, "unsafe manifest path"):
            build_plan(self.copy)
        data["delete"][-1] = "06_Resources/EXAMPLE-RESOURCE.md"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(AdoptionError, "case-colliding"):
            build_plan(self.copy)

    def test_manifest_rejects_case_mismatch_control_and_nested_dot_paths(self):
        copy_repo(self.copy)
        manifest = self.copy / "10_Agents/tools/adopt_examples.json"
        original = json.loads(manifest.read_text(encoding="utf-8"))

        data = dict(original)
        data["delete"] = [
            "06_resources/example-resource.md"
            if path == "06_Resources/example-resource.md"
            else path
            for path in original["delete"]
        ]
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(AdoptionError, "case-mismatched"):
            build_plan(self.copy)

        for unsafe in ("safe/control\nname.md", "safe/.git/config"):
            data["delete"] = [*original["delete"], unsafe]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.subTest(unsafe=unsafe), self.assertRaisesRegex(
                AdoptionError, "unsafe manifest path|dot-paths"
            ):
                build_plan(self.copy)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_target_refuses_without_touching_outside(self):
        copy_repo(self.copy)
        target = self.copy / "03_Journal/ideas/example-idea.md"
        target.unlink()
        outside = Path(self._tmp.name) / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        os.symlink(outside, target)
        with self.assertRaisesRegex(AdoptionError, "symlinked adoption path"):
            build_plan(self.copy)
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_git_metadata_refuses_apply(self):
        copy_repo(self.copy)
        plan = build_plan(self.copy)
        outside = Path(self._tmp.name) / "outside-git"
        outside.mkdir()
        os.symlink(outside, self.copy / ".git")
        with self.assertRaisesRegex(AdoptionError, "symlinked .git"):
            apply_plan(self.copy, plan)
        self.assertTrue((self.copy / "04_Projects/example-project").is_dir())


if __name__ == "__main__":
    unittest.main()
