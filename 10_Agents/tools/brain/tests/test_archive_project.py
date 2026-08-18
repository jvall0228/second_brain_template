"""Whole-directory Project archive planning, link repair, and rollback tests."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain


def note(title: str, tags: tuple[str, ...], body: str, fields: str = "") -> str:
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n"
        + "".join(f"  - {tag}\n" for tag in tags)
        + fields
        + "updated: 2026-08-18\n"
        "---\n\n"
        f"# {title}\n\n{body.rstrip()}\n"
    )


CONVENTIONS = """---
title: "Conventions"
tags:
  - type/meta
updated: 2026-08-18
---

# Conventions

## Tag Namespaces

| Namespace | Purpose | Values |
|---|---|---|
| `type/*` | Type | `meta`, `project`, `area`, `reference`, `note` |
| `status/*` | State | `active`, `deprioritized`, `someday`, `done` |
| `project/*` | Identity | Free-form |
| `area/*` | Identity | Free-form |
"""


class ArchiveVault:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="archive-project-")
        self.root = Path(self.temp.name)
        self.write("00_Meta/CONVENTIONS.md", CONVENTIONS)
        self.write(
            "05_Areas/home/AREA.md",
            note(
                "Home",
                ("type/area", "status/active", "area/home"),
                "## Standard to Maintain\n\nKeep it healthy.\n\n"
                "## Active Projects\n\n_No active Projects currently map to this Area._",
            ),
        )
        self.write(
            "07_Archives/projects/README.md",
            note("Archived Projects", ("type/meta",), "Done Projects."),
        )
        self.write(
            "06_Resources/guide.md",
            note("Guide", ("type/reference",), "## Advice\n\nUseful guidance."),
        )
        self.write(
            "04_Projects/sample/PROJECT.md",
            note(
                "Sample",
                ("type/project", "status/done", "project/sample", "area/home"),
                "## Outcome\n\nFinished.\n\n"
                "## Completion Criteria\n\n- Verified.\n\n"
                "## Final Outcome\n\nCompleted and verified.\n\n"
                "## Areas\n\n- [Home](../../05_Areas/home/AREA.md)\n\n"
                "## Reference\n\n[Guide](../../06_Resources/guide.md \"Guide title\")",
                fields="closed: 2026-08-18\n",
            ),
        )
        self.write(
            "04_Projects/sample/notes/detail.md",
            note(
                "Detail",
                ("type/note", "project/sample"),
                "[Map](../assets/map.png) and [advice](../../../06_Resources/guide.md#advice).",
            ),
        )
        self.write("04_Projects/sample/assets/map.png", b"PNG-fixture")
        self.write(
            "06_Resources/inbound.md",
            note(
                "Inbound",
                ("type/reference",),
                "See [the outcome](../04_Projects/sample/PROJECT.md#outcome).",
            ),
        )
        self.write("10_Agents/tools/brain/vault-index.json", b"{}\n")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)

    def cleanup(self) -> None:
        self.temp.cleanup()

    def write(self, rel: str, content: str | bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def status(self) -> str:
        return subprocess.run(
            ["git", "status", "--short"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout


class ProjectArchiveTests(unittest.TestCase):
    def setUp(self):
        self.vault = ArchiveVault()

    def tearDown(self):
        self.vault.cleanup()

    def test_preview_is_zero_write_and_describes_bidirectional_repairs(self):
        before = self.status_snapshot()

        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        public = brain._public_archive_plan(plan)

        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["summary"]["filesMoved"], 3)
        self.assertGreaterEqual(plan["summary"]["linksRewritten"], 3)
        self.assertEqual(len(public["moves"]), 3)
        self.assertEqual(
            {
                "resultPath",
                "resultSha256",
                "sourcePath",
                "sourceSha256",
            },
            set(public["moves"][0]),
        )
        self.assertEqual(
            {
                "line",
                "newDestination",
                "oldDestination",
                "resultPath",
                "resultSha256",
                "sourcePath",
                "sourceSha256",
            },
            set(public["linkRewrites"][0]),
        )
        self.assertNotIn("Guide title", json.dumps(public["linkRewrites"]))
        self.assertEqual(self.status_snapshot(), before)

        original_id = plan["planId"]
        asset = self.vault.root / "04_Projects/sample/assets/map.png"
        asset.write_bytes(b"different non-note bytes")
        changed = brain.build_project_archive_plan(self.vault.root, "sample")
        self.assertNotEqual(changed["planId"], original_id)

    def test_human_preview_bounds_exact_plan_rows(self):
        for number in range(25):
            self.vault.write(
                f"04_Projects/sample/assets/extra-{number:02d}.bin",
                f"asset-{number}".encode(),
            )
        subprocess.run(
            ["git", "add", "04_Projects/sample/assets"],
            cwd=self.vault.root,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "more assets"],
            cwd=self.vault.root,
            check=True,
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = brain.main(
                ["archive-project", "sample", "--vault", str(self.vault.root)]
            )
        lines = stdout.getvalue().splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(sum(line.strip().startswith("MOVE ") for line in lines), 20)
        self.assertTrue(any("more moves (use --json)" in line for line in lines))

    def test_write_moves_whole_directory_preserves_tags_and_repairs_links(self):
        before_tags = self.tags("04_Projects/sample/PROJECT.md")
        plan = brain.build_project_archive_plan(self.vault.root, "sample")

        result = brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue(result["staged"])
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())
        archived = self.vault.root / "07_Archives/projects/sample"
        self.assertTrue((archived / "assets/map.png").is_file())
        self.assertEqual(self.tags("07_Archives/projects/sample/PROJECT.md"), before_tags)
        project_text = (archived / "PROJECT.md").read_text()
        self.assertIn('../../../06_Resources/guide.md "Guide title"', project_text)
        inbound = (self.vault.root / "06_Resources/inbound.md").read_text()
        self.assertIn("../07_Archives/projects/sample/PROJECT.md#outcome", inbound)
        detail = (archived / "notes/detail.md").read_text()
        self.assertIn("../assets/map.png", detail)
        self.assertIn("../../../../06_Resources/guide.md#advice", detail)
        errors, _warnings = brain.run_validate(self.vault.root, True)
        self.assertEqual(errors, [])
        self.assertIn(
            "04_Projects/sample/PROJECT.md -> 07_Archives/projects/sample/PROJECT.md",
            self.vault.status(),
        )

    def test_write_requires_explicit_approval_at_cli_boundary(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = brain.main(
                [
                    "archive-project",
                    "sample",
                    "--vault",
                    str(self.vault.root),
                    "--write",
                    "--json",
                ]
            )

        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), {"error": "Project archive failed safely"})
        self.assertEqual(self.vault.status(), "")

    def test_validation_failure_rolls_back_files_and_raw_git_index(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        failure = {"line": None, "message": "forced", "path": "x", "rule": "forced"}

        with (
            mock.patch.object(brain, "run_validate", return_value=([failure], [])),
            self.assertRaises(brain.ProjectArchiveError),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue((self.vault.root / "04_Projects/sample/PROJECT.md").is_file())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())
        self.assertEqual(self.vault.status(), "")
        self.assertFalse((self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists())

    def test_dirty_worktree_refuses_before_mutation(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        self.vault.write("untracked.txt", "owner work")

        with self.assertRaises(brain.ProjectArchiveError):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue((self.vault.root / "04_Projects/sample/PROJECT.md").is_file())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())

    def test_journal_file_fsync_failure_removes_only_owned_inode(self):
        payload = self.journal_payload()
        original_fsync = brain.os.fsync
        failed = False

        def fail_first_fsync(descriptor):
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected journal fsync failure")
            return original_fsync(descriptor)

        with (
            mock.patch.object(brain.os, "fsync", side_effect=fail_first_fsync),
            self.assertRaises(OSError),
        ):
            brain._archive_create_journal(self.vault.root, payload)

        self.assertTrue(failed)
        self.assertFalse(
            (self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists()
        )

    def test_journal_guard_failure_preserves_foreign_replacement(self):
        payload = self.journal_payload()
        journal = self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH

        def replace_with_foreign(_root, _guard):
            journal.unlink()
            journal.write_text("foreign owner state\n", encoding="utf-8")
            return False

        with (
            mock.patch.object(
                brain,
                "_archive_journal_guard_matches",
                side_effect=replace_with_foreign,
            ),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain._archive_create_journal(self.vault.root, payload)

        self.assertEqual(journal.read_text(encoding="utf-8"), "foreign owner state\n")

    def test_pre_manifest_snapshot_failure_cleans_evidence_and_rethrows(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")

        with (
            mock.patch.object(
                brain.shutil,
                "copytree",
                side_effect=OSError("injected snapshot failure"),
            ),
            self.assertRaisesRegex(OSError, "injected snapshot failure"),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue((self.vault.root / "04_Projects/sample").is_dir())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())
        self.assertFalse(
            (self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists()
        )
        self.assertEqual(
            list(self.vault.root.glob(brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX + "*")),
            [],
        )
        self.assertEqual(self.vault.status(), "")

    def test_invalid_slug_blocks_without_touching_filesystem_or_git(self):
        before = self.status_snapshot()
        with (
            mock.patch.object(brain, "_archive_inventory") as inventory,
            mock.patch.object(brain, "git_tracked") as tracked,
            mock.patch.object(brain, "walk_corpus") as walk,
            mock.patch.object(brain.os.path, "lexists") as lexists,
        ):
            plan = brain.build_project_archive_plan(self.vault.root, "../escape")

        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["source"], "")
        self.assertEqual(plan["destination"], "")
        self.assertEqual([row["rule"] for row in plan["blockers"]], ["archive-slug"])
        inventory.assert_not_called()
        tracked.assert_not_called()
        walk.assert_not_called()
        lexists.assert_not_called()
        self.assertEqual(self.status_snapshot(), before)

    def test_other_done_project_pending_archive_remains_baseline(self):
        self.vault.write(
            "04_Projects/other/PROJECT.md",
            note(
                "Other",
                ("type/project", "status/done", "project/other", "area/home"),
                "## Outcome\n\nFinished.\n\n"
                "## Completion Criteria\n\n- Verified.\n\n"
                "## Final Outcome\n\nCompleted.\n\n"
                "## Areas\n\n- [Home](../../05_Areas/home/AREA.md)",
                fields="closed: 2026-08-18\n",
            ),
        )
        subprocess.run(["git", "add", "."], cwd=self.vault.root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "second done project"],
            cwd=self.vault.root,
            check=True,
        )

        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        self.assertEqual(plan["status"], "ready")
        self.assertTrue(
            any(
                path == "04_Projects/other/PROJECT.md"
                and rule == "project-archive-pending"
                for path, rule, _message in plan["_baselineEntityFindings"]
            )
        )

        result = brain.apply_project_archive_plan(self.vault.root, plan)
        self.assertTrue(result["written"])
        self.assertTrue((self.vault.root / "04_Projects/other/PROJECT.md").is_file())

    def test_placeholder_final_outcome_blocks_archive(self):
        project = self.vault.root / "04_Projects/sample/PROJECT.md"
        project.write_text(
            project.read_text(encoding="utf-8").replace(
                "Completed and verified.", "None"
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=self.vault.root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "placeholder final outcome"],
            cwd=self.vault.root,
            check=True,
        )

        plan = brain.build_project_archive_plan(self.vault.root, "sample")

        self.assertEqual(plan["status"], "blocked")
        self.assertIn(
            "project-final-outcome", {row["rule"] for row in plan["blockers"]}
        )

    def test_blocked_approved_write_renders_same_plan_as_preview(self):
        project = self.vault.root / "04_Projects/sample/PROJECT.md"
        project.write_text(
            project.read_text(encoding="utf-8").replace(
                "  - status/done", "  - status/active"
            ),
            encoding="utf-8",
        )

        preview_json = io.StringIO()
        write_json = io.StringIO()
        with contextlib.redirect_stdout(preview_json):
            preview_code = brain.main(
                [
                    "archive-project",
                    "sample",
                    "--vault",
                    str(self.vault.root),
                    "--json",
                ]
            )
        with contextlib.redirect_stdout(write_json):
            write_code = brain.main(
                [
                    "archive-project",
                    "sample",
                    "--vault",
                    str(self.vault.root),
                    "--write",
                    "--approve-archive",
                    "--json",
                ]
            )
        self.assertEqual(preview_code, 1)
        self.assertEqual(write_code, 1)
        self.assertEqual(json.loads(write_json.getvalue()), json.loads(preview_json.getvalue()))

        preview_human = io.StringIO()
        write_human = io.StringIO()
        with contextlib.redirect_stdout(preview_human):
            brain.main(
                ["archive-project", "sample", "--vault", str(self.vault.root)]
            )
        with contextlib.redirect_stdout(write_human):
            brain.main(
                [
                    "archive-project",
                    "sample",
                    "--vault",
                    str(self.vault.root),
                    "--write",
                    "--approve-archive",
                ]
            )
        self.assertEqual(write_human.getvalue(), preview_human.getvalue())

    def test_archive_inventory_normalizes_decomposed_filename_like_corpus(self):
        decomposed = "cafe\u0301.bin"
        composed_rel = "04_Projects/sample/assets/" + brain.nfc(decomposed)
        self.vault.write("04_Projects/sample/assets/" + decomposed, b"unicode")
        subprocess.run(["git", "add", "."], cwd=self.vault.root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "unicode asset"],
            cwd=self.vault.root,
            check=True,
        )

        inventory = brain._archive_inventory(self.vault.root, "04_Projects/sample")
        tracked = brain.git_tracked(self.vault.root)
        _notes, assets = brain.walk_corpus(
            self.vault.root, selected_environment=None
        )

        self.assertIn(composed_rel, inventory)
        self.assertIn(composed_rel, tracked)
        self.assertIn(composed_rel, assets)

    def test_archive_git_ignores_ambient_repository_and_index_selectors(self):
        with tempfile.TemporaryDirectory(prefix="foreign-git-") as foreign_name:
            foreign = Path(foreign_name)
            (foreign / "foreign.txt").write_text("foreign\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=foreign, check=True)
            subprocess.run(
                ["git", "config", "user.email", "foreign@example.com"],
                cwd=foreign,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Foreign"], cwd=foreign, check=True
            )
            subprocess.run(["git", "add", "."], cwd=foreign, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "foreign"], cwd=foreign, check=True
            )
            foreign_index = foreign / ".git/index"
            foreign_before = foreign_index.read_bytes()
            actual_vault_index = brain._archive_git_index_path(self.vault.root)
            selectors = {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.worktree",
                "GIT_CONFIG_VALUE_0": str(foreign),
                "GIT_DIR": str(foreign / ".git"),
                "GIT_INDEX_FILE": str(foreign_index),
                "GIT_WORK_TREE": str(foreign),
            }

            with mock.patch.dict(brain.os.environ, selectors):
                self.assertEqual(
                    brain._archive_git_index_path(self.vault.root), actual_vault_index
                )
                plan = brain.build_project_archive_plan(self.vault.root, "sample")
                result = brain.apply_project_archive_plan(self.vault.root, plan)

            self.assertTrue(result["written"])
            self.assertEqual(foreign_index.read_bytes(), foreign_before)
            self.assertEqual(
                subprocess.run(
                    ["git", "status", "--short"],
                    cwd=foreign,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout,
                "",
            )

    def test_external_race_during_exact_staging_preserves_foreign_bytes(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        live_index = brain._archive_git_index_path(self.vault.root)
        initial_index = live_index.read_bytes()
        inbound = self.vault.root / "06_Resources/inbound.md"
        original_build = brain._archive_build_exact_index
        raced = False

        def race_before_index_build(*args, **kwargs):
            nonlocal raced
            if not raced:
                raced = True
                inbound.write_bytes(b"foreign concurrent note\n")
            return original_build(*args, **kwargs)

        with (
            mock.patch.object(
                brain,
                "_archive_build_exact_index",
                side_effect=race_before_index_build,
            ),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue(raced)
        self.assertEqual(inbound.read_bytes(), b"foreign concurrent note\n")
        self.assertEqual(live_index.read_bytes(), initial_index)
        self.assertEqual(
            brain._archive_git(
                self.vault.root,
                ["diff", "--cached", "--name-only", "-z"],
            ).stdout,
            b"",
        )

    def test_exact_staging_preserves_git_mode_from_source_entry(self):
        subprocess.run(
            [
                "git",
                "update-index",
                "--chmod=+x",
                "04_Projects/sample/assets/map.png",
            ],
            cwd=self.vault.root,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "mark project asset executable"],
            cwd=self.vault.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "core.filemode", "false"],
            cwd=self.vault.root,
            check=True,
        )
        plan = brain.build_project_archive_plan(self.vault.root, "sample")

        brain.apply_project_archive_plan(self.vault.root, plan)

        staged = brain._archive_git(
            self.vault.root,
            [
                "ls-files",
                "--stage",
                "--",
                "07_Archives/projects/sample/assets/map.png",
            ],
        ).stdout.decode("ascii")
        self.assertTrue(staged.startswith("100755 "))

    def test_source_parent_swap_is_detected_before_descriptor_relative_move(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        original_rename = brain._archive_rename_guarded
        original_parent = self.vault.root / "04_Projects"
        displaced_parent = self.vault.root / "04_Projects-owner"
        swapped = False

        def swap_then_rename(*args, **kwargs):
            nonlocal swapped
            if not swapped:
                swapped = True
                original_parent.rename(displaced_parent)
                original_parent.mkdir()
                (original_parent / "foreign-marker").write_text(
                    "foreign\n", encoding="utf-8"
                )
            return original_rename(*args, **kwargs)

        with (
            mock.patch.object(
                brain, "_archive_rename_guarded", side_effect=swap_then_rename
            ),
            self.assertRaises(brain.ProjectArchiveError),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue(swapped)
        self.assertTrue((original_parent / "foreign-marker").is_file())
        self.assertTrue((displaced_parent / "sample/PROJECT.md").is_file())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())

    def test_concurrent_archive_loses_exclusive_journal_without_evidence(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        transaction = brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX + "0" * 24
        payload = {
            "destination": "07_Archives/projects/sample",
            "owner": "brain-project-archive",
            "pid": 1,
            "planId": plan["planId"],
            "schemaVersion": brain.PROJECT_ARCHIVE_SCHEMA_VERSION,
            "slug": "sample",
            "source": "04_Projects/sample",
            "transaction": transaction,
        }
        guard = brain._archive_create_journal(self.vault.root, payload)
        try:
            with self.assertRaises(brain.ProjectArchiveError):
                brain.apply_project_archive_plan(self.vault.root, plan)
            evidence = list(
                self.vault.root.glob(brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX + "*")
            )
            self.assertEqual(evidence, [])
            self.assertTrue((self.vault.root / "04_Projects/sample").is_dir())
        finally:
            brain._archive_remove_journal(self.vault.root, guard)
            brain._archive_close_journal(guard)

    def test_recovery_requires_matching_slug_and_plan_evidence_before_mutation(self):
        transaction = self.leave_interrupted_archive()
        destination = self.vault.root / "07_Archives/projects/sample"

        with self.assertRaises(brain.ProjectArchiveRecoveryRequired):
            brain.recover_project_archive(self.vault.root, "different")
        self.assertTrue(destination.is_dir())

        manifest_path = transaction / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["planId"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        with self.assertRaises(brain.ProjectArchiveRecoveryRequired):
            brain.recover_project_archive(self.vault.root, "sample")
        self.assertTrue(destination.is_dir())
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())

    def test_recovery_refuses_symlinked_snapshot_before_mutation(self):
        transaction = self.leave_interrupted_archive()
        snapshot = transaction / "external/0"
        snapshot.unlink()
        snapshot.symlink_to(self.vault.root / "06_Resources/inbound.md")

        with self.assertRaises(brain.ProjectArchiveRecoveryRequired):
            brain.recover_project_archive(self.vault.root, "sample")
        self.assertTrue((self.vault.root / "07_Archives/projects/sample").is_dir())
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())

    def test_recovery_validates_source_snapshot_before_removing_destination(self):
        transaction = self.leave_interrupted_archive()
        (transaction / "source/PROJECT.md").write_text(
            "corrupted recovery evidence\n", encoding="utf-8"
        )

        with self.assertRaises(brain.ProjectArchiveRecoveryRequired):
            brain.recover_project_archive(self.vault.root, "sample")

        self.assertTrue((self.vault.root / "07_Archives/projects/sample").is_dir())
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())

    def test_recovery_refuses_escaping_external_path_before_mutation(self):
        transaction = self.leave_interrupted_archive()
        manifest_path = transaction / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["externalEdits"][0]["path"] = "../outside.md"
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

        with self.assertRaises(brain.ProjectArchiveRecoveryRequired):
            brain.recover_project_archive(self.vault.root, "sample")
        self.assertTrue((self.vault.root / "07_Archives/projects/sample").is_dir())
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())

    def test_recovery_refuses_foreign_git_index_before_mutation(self):
        self.leave_interrupted_archive()
        git_index = brain._archive_git_index_path(self.vault.root)
        git_index.write_bytes(b"foreign staged state")

        with self.assertRaises(brain.ProjectArchiveRecoveryRequired):
            brain.recover_project_archive(self.vault.root, "sample")
        self.assertTrue((self.vault.root / "07_Archives/projects/sample").is_dir())
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())

    def test_concurrent_external_identity_change_aborts_before_move(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        original_copytree = brain.shutil.copytree
        changed = False

        def copytree_then_replace(*args, **kwargs):
            nonlocal changed
            result = original_copytree(*args, **kwargs)
            if not changed:
                changed = True
                inbound = self.vault.root / "06_Resources/inbound.md"
                replacement = inbound.with_suffix(".replacement")
                replacement.write_bytes(inbound.read_bytes())
                replacement.replace(inbound)
            return result

        with (
            mock.patch.object(brain.shutil, "copytree", side_effect=copytree_then_replace),
            self.assertRaises(brain.ProjectArchiveError),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue((self.vault.root / "04_Projects/sample").is_dir())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())
        self.assertFalse((self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists())

    def test_index_install_failure_after_manifest_update_rolls_back(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        original_write = brain._archive_write_guarded
        injected = False

        def write_then_fail(path, content, mode, expected):
            nonlocal injected
            result = original_write(path, content, mode, expected)
            if path == self.vault.root / brain.INDEX_RELPATH and not injected:
                injected = True
                raise OSError("injected after index install")
            return result

        with (
            mock.patch.object(brain, "_archive_write_guarded", side_effect=write_then_fail),
            self.assertRaises(OSError),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue(injected)
        self.assertTrue((self.vault.root / "04_Projects/sample").is_dir())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())
        self.assertFalse((self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists())
        self.assertEqual(self.vault.status(), "")

    def test_cli_reports_recovery_required_without_internal_paths(self):
        original_restore = brain._archive_restore_transaction

        def refuse_rollback(*_args, **_kwargs):
            raise brain.ProjectArchiveError("raw subprocess /private/path")

        stdout = io.StringIO()
        with (
            mock.patch.object(brain, "run_validate", return_value=([{"rule": "x"}], [])),
            mock.patch.object(brain, "_archive_restore_transaction", side_effect=refuse_rollback),
            contextlib.redirect_stdout(stdout),
        ):
            code = brain.main(
                [
                    "archive-project",
                    "sample",
                    "--vault",
                    str(self.vault.root),
                    "--write",
                    "--approve-archive",
                    "--json",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(payload["code"], "project-archive-recovery-required")
        self.assertTrue(payload["recoveryRequired"])
        self.assertEqual(
            payload["remediation"],
            "Inspect preserved archive evidence before retrying "
            "brain archive-project sample --recover",
        )
        self.assertNotIn("private", stdout.getvalue())
        brain._archive_restore_transaction = original_restore

    def test_interrupted_evidence_is_durable_and_recovers(self):
        transaction = self.leave_interrupted_archive()
        journal = self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH
        self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
        self.assertEqual(transaction.stat().st_mode & 0o777, 0o700)
        self.assertFalse((transaction / "source").is_symlink())
        self.assertTrue((transaction / "source/PROJECT.md").is_file())

        result = brain.recover_project_archive(self.vault.root, "sample")

        self.assertTrue(result["recovered"])
        self.assertTrue((self.vault.root / "04_Projects/sample/PROJECT.md").is_file())
        self.assertFalse((self.vault.root / "07_Archives/projects/sample").exists())
        self.assertFalse(journal.exists())
        self.assertEqual(self.vault.status(), "")

    def test_success_retires_journal_before_deleting_evidence(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        original_rmtree = brain.shutil.rmtree
        observations = []

        def observe_rmtree(path, *args, **kwargs):
            if Path(path).name.startswith(brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX):
                observations.append(
                    (self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists()
                )
            return original_rmtree(path, *args, **kwargs)

        with mock.patch.object(brain.shutil, "rmtree", side_effect=observe_rmtree):
            brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertEqual(observations, [False])

    def test_committed_archive_returns_cleanup_warning_when_evidence_delete_fails(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")

        with mock.patch.object(
            brain.shutil, "rmtree", side_effect=OSError("injected cleanup failure")
        ):
            result = brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue(result["written"])
        self.assertEqual(
            result["cleanupWarnings"],
            [
                {
                    "code": "project-archive-cleanup-pending",
                    "evidenceRetained": True,
                    "message": "Archive committed; local transaction cleanup remains pending",
                }
            ],
        )
        self.assertFalse(
            (self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists()
        )
        evidence = list(
            self.vault.root.glob(brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX + "*")
        )
        self.assertEqual(len(evidence), 1)
        self.assertTrue((self.vault.root / "07_Archives/projects/sample").is_dir())

    def test_committed_archive_returns_cleanup_warning_when_root_fsync_fails(self):
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        original_fsync_directory = brain._archive_fsync_directory
        failed = False

        def fail_after_evidence_delete(path):
            nonlocal failed
            transactions = list(
                self.vault.root.glob(brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX + "*")
            )
            journal = self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH
            if path == self.vault.root and not transactions and not journal.exists():
                failed = True
                raise OSError("injected cleanup fsync failure")
            return original_fsync_directory(path)

        with mock.patch.object(
            brain, "_archive_fsync_directory", side_effect=fail_after_evidence_delete
        ):
            result = brain.apply_project_archive_plan(self.vault.root, plan)

        self.assertTrue(failed)
        self.assertTrue(result["written"])
        self.assertEqual(result["cleanupWarnings"][0]["evidenceRetained"], False)

    def test_recovery_retires_journal_before_deleting_evidence(self):
        self.leave_interrupted_archive()
        original_rmtree = brain.shutil.rmtree
        observations = []

        def observe_rmtree(path, *args, **kwargs):
            if Path(path).name.startswith(brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX):
                observations.append(
                    (self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).exists()
                )
            return original_rmtree(path, *args, **kwargs)

        with mock.patch.object(brain.shutil, "rmtree", side_effect=observe_rmtree):
            brain.recover_project_archive(self.vault.root, "sample")

        self.assertEqual(observations, [False])

    def test_recovery_destination_race_is_preserved_before_removal(self):
        self.leave_interrupted_archive()
        destination_file = (
            self.vault.root / "07_Archives/projects/sample/assets/map.png"
        )
        original_assert = brain._archive_assert_tree_state
        raced = False

        def race_destination(root, prefix, expected):
            nonlocal raced
            if prefix == "07_Archives/projects/sample" and not raced:
                raced = True
                destination_file.write_bytes(b"foreign destination bytes")
            return original_assert(root, prefix, expected)

        with (
            mock.patch.object(
                brain, "_archive_assert_tree_state", side_effect=race_destination
            ),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain.recover_project_archive(self.vault.root, "sample")

        self.assertTrue(raced)
        self.assertEqual(destination_file.read_bytes(), b"foreign destination bytes")
        self.assertFalse((self.vault.root / "04_Projects/sample").exists())

    def test_recovery_external_race_is_preserved_before_overwrite(self):
        self.leave_interrupted_archive()
        inbound = self.vault.root / "06_Resources/inbound.md"
        original_assert = brain._archive_assert_state
        raced = False

        def race_external(path, expected):
            nonlocal raced
            if path == inbound and not raced:
                raced = True
                inbound.write_bytes(b"foreign recovery note\n")
            return original_assert(path, expected)

        with (
            mock.patch.object(brain, "_archive_assert_state", side_effect=race_external),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain.recover_project_archive(self.vault.root, "sample")

        self.assertTrue(raced)
        self.assertEqual(inbound.read_bytes(), b"foreign recovery note\n")

    def test_recovery_vault_index_race_is_preserved_before_overwrite(self):
        self.leave_interrupted_archive()
        vault_index = self.vault.root / brain.INDEX_RELPATH
        original_assert = brain._archive_assert_state
        raced = False

        def race_vault_index(path, expected):
            nonlocal raced
            if path == vault_index and not raced:
                raced = True
                vault_index.write_bytes(b"foreign vault index\n")
            return original_assert(path, expected)

        with (
            mock.patch.object(
                brain, "_archive_assert_state", side_effect=race_vault_index
            ),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain.recover_project_archive(self.vault.root, "sample")

        self.assertTrue(raced)
        self.assertEqual(vault_index.read_bytes(), b"foreign vault index\n")

    def test_recovery_git_index_race_is_preserved_before_overwrite(self):
        self.leave_interrupted_archive()
        git_index = brain._archive_git_index_path(self.vault.root)
        original_assert = brain._archive_assert_state
        raced = False

        def race_git_index(path, expected):
            nonlocal raced
            if path == git_index and not raced:
                raced = True
                git_index.write_bytes(b"foreign git index\n")
            return original_assert(path, expected)

        with (
            mock.patch.object(
                brain, "_archive_assert_state", side_effect=race_git_index
            ),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain.recover_project_archive(self.vault.root, "sample")

        self.assertTrue(raced)
        self.assertEqual(git_index.read_bytes(), b"foreign git index\n")

    def status_snapshot(self) -> tuple[str, tuple[str, ...]]:
        paths = tuple(
            sorted(
                path.relative_to(self.vault.root).as_posix()
                for path in self.vault.root.rglob("*")
                if ".git" not in path.parts
            )
        )
        return self.vault.status(), paths

    def tags(self, rel: str) -> list[str]:
        lines = (self.vault.root / rel).read_text().splitlines()
        frontmatter, _errors, _body, _has = brain.parse_frontmatter(lines)
        return frontmatter["tags"]

    def leave_interrupted_archive(self) -> Path:
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        failure = {"line": None, "message": "forced", "path": "x", "rule": "forced"}
        with (
            mock.patch.object(brain, "run_validate", return_value=([failure], [])),
            mock.patch.object(
                brain,
                "_archive_restore_transaction",
                side_effect=brain.ProjectArchiveError("leave evidence"),
            ),
            self.assertRaises(brain.ProjectArchiveRecoveryRequired),
        ):
            brain.apply_project_archive_plan(self.vault.root, plan)
        journal = json.loads(
            (self.vault.root / brain.PROJECT_ARCHIVE_JOURNAL_RELPATH).read_text(
                encoding="utf-8"
            )
        )
        return self.vault.root / journal["transaction"]

    def journal_payload(self) -> dict:
        plan = brain.build_project_archive_plan(self.vault.root, "sample")
        return {
            "destination": plan["destination"],
            "owner": "brain-project-archive",
            "pid": 1,
            "planId": plan["planId"],
            "schemaVersion": brain.PROJECT_ARCHIVE_SCHEMA_VERSION,
            "slug": plan["slug"],
            "source": plan["source"],
            "transaction": brain.PROJECT_ARCHIVE_TRANSACTION_PREFIX + "0" * 24,
        }


if __name__ == "__main__":
    unittest.main()
