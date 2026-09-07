"""Explicit shared corpus access without borrowing an environment identity (§20)."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain


class SharedScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.environments = self.root / brain.ENVIRONMENTS_RELPATH
        self.environments.mkdir(parents=True)
        self.note(self.root / "shared.md", "SHARED-SENTINEL")
        self.note(self.environments / "README.md", "Shared registry")
        self.environment("alpha")

    def note(self, path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\ntitle: Fixture\ntags:\n  - type/reference\n"
            "updated: 2026-09-05\n---\n" + body + "\n",
            encoding="utf-8",
        )

    def environment(self, slug):
        directory = self.environments / slug
        self.note(directory / "README.md", "ENVIRONMENT-SENTINEL")
        (directory / "environment.json").write_text(json.dumps({
            "capabilities": {}, "class": "container", "fingerprints": [],
            "freshness": {"checkedAt": "2026-09-05", "expiresAt": "2026-11-05"},
            "maintenance": {"inventory": "orientation-inventory.md", "ownerReviewRequired": True},
            "schemaVersion": 1, "slug": slug, "surfaces": ["codex"],
        }), encoding="utf-8")

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = brain.main(["--vault", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_default_still_fails_before_and_after_shared_query(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            brain, "machine_fingerprints", return_value=[]
        ):
            code, out, err = self.cli("list", "--json")
            self.assertEqual(code, 1)
            self.assertEqual(out, "")
            self.assertIn("no-fingerprint-match", err)
            code, out, err = self.cli("--shared-only", "list", "--json")
            self.assertEqual(code, 0, err)
            self.assertNotIn("alpha/", out)
            code, out, err = self.cli("list", "--json")
            self.assertEqual(code, 1)
            self.assertIn("no-fingerprint-match", err)

    def test_shared_scope_excludes_valid_unmatched_and_malformed_environments(self):
        self.environment("beta")
        for slug in ("unregistered", "INVALID DIRECTORY"):
            self.note(self.environments / slug / "note.md", "ENVIRONMENT-SENTINEL")
            (self.environments / slug / "environment.json").write_text("broken JSON")
        selector = self.root / brain.ENVIRONMENT_SELECTOR_RELPATH
        selector.parent.mkdir()
        selector.write_text("alpha\n")
        with mock.patch.dict(os.environ, {"SECOND_BRAIN_ENV": "beta"}), mock.patch.object(
            brain, "select_environment", side_effect=AssertionError("must not select")
        ), mock.patch.object(
            brain, "load_environment_manifests", side_effect=AssertionError("must not load manifests")
        ):
            with brain.shared_corpus_scope():
                notes, assets = brain.walk_corpus(self.root)
                self.assertEqual(notes, [brain.ENVIRONMENTS_RELPATH + "/README.md", "shared.md"])
                self.assertEqual(assets, [])
                for slug in ("alpha", "beta", "unregistered", "INVALID DIRECTORY"):
                    with self.subTest(slug=slug), self.assertRaises(OSError):
                        brain._read_vault_bytes(
                            self.root, f"{brain.ENVIRONMENTS_RELPATH}/{slug}/README.md"
                        )
                with self.assertRaisesRegex(brain.EnvironmentSelectionError, "shared-only-with-environment"):
                    brain.walk_corpus(self.root, selected_environment="alpha")
            code, out, err = self.cli("search", "SENTINEL", "--shared-only", "--json")
            self.assertEqual(code, 0, err)
            self.assertIn("SHARED-SENTINEL", out)
            self.assertNotIn("ENVIRONMENT-SENTINEL", out)

    def test_shared_scope_restores_after_nested_failure(self):
        with mock.patch.object(brain, "_ACTIVE_ENVIRONMENT", "alpha"):
            self.assertEqual(brain._environment_for_corpus(self.root), "alpha")
            with self.assertRaisesRegex(RuntimeError, "probe"):
                with brain.shared_corpus_scope():
                    with brain.shared_corpus_scope():
                        self.assertIsNone(brain._environment_for_corpus(self.root))
                    self.assertIsNone(brain._environment_for_corpus(self.root))
                    raise RuntimeError("probe")
            self.assertEqual(brain._environment_for_corpus(self.root), "alpha")

    def test_mixed_explicit_flags_fail_before_query(self):
        for args in (
            ["--shared-only", "--env", "alpha", "list"],
            ["--env", "alpha", "list", "--shared-only"],
            ["--shared-only", "list", "--env", "current"],
        ):
            with self.subTest(args=args), mock.patch.object(brain, "cmd_list") as handler:
                with self.assertRaises(SystemExit) as error:
                    self.cli(*args)
                self.assertEqual(error.exception.code, 2)
                handler.assert_not_called()

    def test_environment_operations_and_migration_writes_refuse_shared_scope(self):
        for args in (
            ["--shared-only", "env", "detect"],
            ["--shared-only", "install"],
            ["--shared-only", "migrate-links", "--write"],
        ):
            with self.subTest(args=args), self.assertRaises(SystemExit) as error:
                self.cli(*args)
            self.assertEqual(error.exception.code, 2)

    def test_shared_generators_keep_owning_write_route_without_selecting(self):
        seed = self.root / brain.ADOPT_EXAMPLES_RELPATH
        seed.parent.mkdir(parents=True, exist_ok=True)
        seed.write_text(json.dumps({"schema_version": 1, "delete": []}))
        for rel in set(brain.BOOTSTRAP_ORDER) | {
            "00_Meta/STATUS.md", "00_Meta/CHANGELOG.md", "02_Inbox/README.md",
            "04_Projects/README.md", "05_Areas/README.md", "10_Agents/skills/README.md",
        }:
            self.note(self.root / rel, "## Current Focus\n\n- SHARED-SENTINEL")
        tracked = {path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file()}
        for command in ("aymt", "home", "bootstrap"):
            with self.subTest(command=command), mock.patch.object(
                brain, "git_tracked", return_value=tracked
            ), mock.patch.object(brain, "select_environment", side_effect=AssertionError("must not select")), mock.patch.object(
                brain, "select_aymt_environment", side_effect=AssertionError("must not select")
            ):
                code, out, err = self.cli("--shared-only", command, "--write", "--json")
                self.assertEqual(code, 0, out + err)
                self.assertNotIn("ENVIRONMENT-SENTINEL", out)
                generated_rel = getattr(brain, command.upper() + "_RELPATH")
                generated = (self.root / generated_rel).read_text()
                if command == "bootstrap":
                    self.assertIn("SHARED-SENTINEL", generated)
                self.assertNotIn("ENVIRONMENT-SENTINEL", generated)
                if command in {"aymt", "home"}:
                    self.assertEqual(json.loads(out)["environment"], {
                        "slug": None, "source": "shared-only", "state": "shared-only", "freshness": None,
                    })
                if command == "home":
                    self.assertIn("Shared-only scope; no environment selected.", generated)


if __name__ == "__main__":
    unittest.main()
