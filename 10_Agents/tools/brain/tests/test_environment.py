"""Environment identity, isolation, and privacy tests (spec §20, issue #15)."""

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
import brain  # noqa: E402


def manifest(slug: str, digest: str, **changes) -> dict:
    data = {
        "capabilities": {"computer-use": True, "network-egress": False},
        "class": "laptop",
        "fingerprints": [
            {"algorithm": "sha256", "digest": digest, "source": "machine-v1"}
        ],
        "freshness": {"checkedAt": "2026-08-11", "expiresAt": "2026-11-11"},
        "maintenance": {
            "inventory": "orientation-inventory.md",
            "ownerReviewRequired": True,
        },
        "schemaVersion": 1,
        "slug": slug,
        "surfaces": ["codex", "vscode"],
    }
    data.update(changes)
    return data


def write_environment(root: Path, slug: str, digest: str, **changes) -> None:
    directory = root / "10_Agents/environments" / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "environment.json").write_text(
        json.dumps(manifest(slug, digest, **changes)), encoding="utf-8"
    )
    (directory / "README.md").write_text(
        f"---\ntitle: {slug}\ntags:\n  - type/meta\nupdated: 2026-08-11\n---\n"
        f"# {slug}\n\n> Applies only to `{slug}`. Other environments must ignore it.\n",
        encoding="utf-8",
    )


def local_fingerprint(digest: str) -> list[dict[str, str]]:
    return [{"algorithm": "sha256", "digest": digest, "source": "machine-v1"}]


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_environment(self.root, "alpha", "a" * 64)
        write_environment(self.root, "beta", "b" * 64)

    def tearDown(self):
        self.tmp.cleanup()

    def select(self, requested=None, environ=None, digest="a" * 64):
        return brain.select_environment(
            self.root,
            requested=requested,
            environ={} if environ is None else environ,
            fingerprints=local_fingerprint(digest),
        )

    def test_precedence_cli_then_variable_then_selector_then_fingerprint(self):
        selector = self.root / ".second-brain/environment"
        selector.parent.mkdir()
        selector.write_text("alpha\n", encoding="utf-8")
        self.assertEqual(
            self.select("beta", {"SECOND_BRAIN_ENV": "alpha"})["slug"], "beta"
        )
        self.assertEqual(
            self.select(environ={"SECOND_BRAIN_ENV": "beta"})["slug"], "beta"
        )
        self.assertEqual(self.select()["source"], "selector")
        selector.unlink()
        self.assertEqual(self.select()["source"], "fingerprint")

    def test_higher_precedence_invalid_value_never_falls_back(self):
        cases = [
            ({"SECOND_BRAIN_ENV": ""}, "invalid-environment-variable"),
            ({"SECOND_BRAIN_ENV": "../alpha"}, "invalid-environment-variable"),
            ({"SECOND_BRAIN_ENV": "missing"}, "environment-variable-not-found"),
        ]
        for environ, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(
                brain.EnvironmentSelectionError, code
            ):
                self.select(environ=environ)

    def test_selector_only_environment_may_have_no_fingerprint(self):
        alpha_path = self.root / "10_Agents/environments/alpha/environment.json"
        alpha_path.write_text(
            json.dumps(manifest("alpha", "a" * 64, fingerprints=[])),
            encoding="utf-8",
        )
        selector = self.root / ".second-brain/environment"
        selector.parent.mkdir()
        selector.write_text("alpha\n", encoding="utf-8")
        self.assertEqual(self.select(digest="c" * 64)["slug"], "alpha")
        self.assertEqual(self.select(requested="alpha", digest="c" * 64)["slug"], "alpha")

    def test_no_match_and_ambiguous_match_fail_closed(self):
        with self.assertRaisesRegex(brain.EnvironmentSelectionError, "no-fingerprint-match"):
            self.select(digest="c" * 64)
        beta_path = self.root / "10_Agents/environments/beta/environment.json"
        beta_path.write_text(json.dumps(manifest("beta", "a" * 64)), encoding="utf-8")
        with self.assertRaisesRegex(brain.EnvironmentSelectionError, "ambiguous-fingerprint"):
            self.select()

    @unittest.skipUnless(os.name == "posix", "symlink check")
    def test_selector_symlink_is_rejected_without_following(self):
        local = self.root / ".second-brain"
        local.mkdir()
        (self.root / "outside").write_text("alpha\n", encoding="utf-8")
        os.symlink(self.root / "outside", local / "environment")
        with self.assertRaisesRegex(brain.EnvironmentSelectionError, "unsafe-selector"):
            self.select()

    @unittest.skipUnless(os.name == "posix", "symlink check")
    def test_selector_parent_symlink_is_rejected_without_following(self):
        outside = self.root / "outside-local"
        outside.mkdir()
        (outside / "environment").write_text("alpha\n", encoding="utf-8")
        os.symlink(outside, self.root / ".second-brain")
        with self.assertRaisesRegex(
            brain.EnvironmentSelectionError, "unsafe-selector-parent"
        ):
            self.select()

    def test_unconfigured_vault_is_shared_only(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(
                brain.select_environment(Path(td), environ={}),
                {"slug": None, "source": "none", "state": "unconfigured"},
            )


class IsolationTests(unittest.TestCase):
    def test_selected_corpus_excludes_other_environment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "shared.md").write_text("shared", encoding="utf-8")
            write_environment(root, "alpha", "a" * 64)
            write_environment(root, "beta", "b" * 64)
            with mock.patch.object(brain, "machine_fingerprints", return_value=local_fingerprint("a" * 64)):
                notes, assets = brain.walk_corpus(root)
            self.assertIn("shared.md", notes)
            self.assertIn("10_Agents/environments/alpha/README.md", notes)
            self.assertNotIn("10_Agents/environments/beta/README.md", notes)
            self.assertIn("10_Agents/environments/alpha/environment.json", assets)
            self.assertNotIn("10_Agents/environments/beta/environment.json", assets)

    @unittest.skipUnless(os.name == "posix", "openat no-follow check")
    def test_selected_note_replaced_by_symlink_after_discovery_is_never_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "vault"
            write_environment(root, "alpha", "a" * 64)
            local = root / ".second-brain"
            local.mkdir()
            (local / "environment").write_text("alpha\n", encoding="utf-8")
            note = root / "10_Agents/environments/alpha/private-note.md"
            note.write_text("safe-before-discovery", encoding="utf-8")
            outside = Path(td) / "outside-secret.md"
            outside.write_text("EXTERNAL-SECRET-SENTINEL", encoding="utf-8")
            notes, assets = brain.walk_corpus(root)
            note.unlink()
            os.symlink(outside, note)
            index = brain.build_index(root, notes, assets)
            rendered = json.dumps(index, sort_keys=True)
            self.assertNotIn("EXTERNAL-SECRET-SENTINEL", rendered)
            self.assertIn("not-readable", rendered)
            hits = brain.keyword_hits(root, index, "EXTERNAL-SECRET-SENTINEL", [])
            self.assertEqual(hits, [])

    def test_two_sibling_forks_use_their_own_selectors(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            roots = [base / "fork-one", base / "fork-two"]
            for root in roots:
                write_environment(root, "alpha", "a" * 64)
                write_environment(root, "beta", "b" * 64)
                (root / ".second-brain").mkdir()
            (roots[0] / ".second-brain/environment").write_text("alpha\n")
            (roots[1] / ".second-brain/environment").write_text("beta\n")
            self.assertEqual(brain.select_environment(roots[0], environ={})["slug"], "alpha")
            self.assertEqual(brain.select_environment(roots[1], environ={})["slug"], "beta")

    def test_index_corpus_excludes_all_environment_content(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_environment(root, "alpha", "a" * 64)
            with mock.patch.object(brain, "git_tracked", return_value=None):
                notes, assets = brain.index_corpus(root)
            self.assertEqual(notes, [])
            self.assertEqual(assets, [])

    def test_embedding_write_prunes_noncurrent_environment_vectors(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_environment(root, "alpha", "a" * 64)
            write_environment(root, "beta", "b" * 64)
            alpha = root / "10_Agents/environments/alpha/private-note.md"
            beta = root / "10_Agents/environments/beta/current-note.md"
            alpha.write_text("alpha body", encoding="utf-8")
            beta.write_text("beta body", encoding="utf-8")
            local = root / ".second-brain"
            local.mkdir()
            (local / "environment").write_text("beta\n", encoding="utf-8")
            sidecar = root / brain.EMBED_RELPATH
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(
                json.dumps(
                    {
                        "dim": 2,
                        "model": "test",
                        "notes": {
                            "10_Agents/environments/alpha/private-note.md": {
                                "hash": brain.note_content_hash("alpha body"),
                                "vector": [1.0, 0.0],
                            }
                        },
                        "schemaVersion": 1,
                    }
                ),
                encoding="utf-8",
            )
            payload = json.dumps(
                {
                    "model": "test",
                    "vectors": {
                        "10_Agents/environments/beta/current-note.md": [0.0, 1.0]
                    },
                }
            )
            with mock.patch.object(sys, "stdin", io.StringIO(payload)):
                code = brain.main(
                    ["embed", "--stdin-json", "--vault", str(root)]
                )
            self.assertEqual(code, 0)
            stored = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(
                sorted(stored["notes"]),
                ["10_Agents/environments/beta/current-note.md"],
            )


class PrivacyAndDiagnosticsTests(unittest.TestCase):
    def test_metadata_suppresses_digest_and_capability_values(self):
        row = brain.environment_metadata(manifest("alpha", "a" * 64), "alpha")
        rendered = json.dumps(row, sort_keys=True)
        self.assertNotIn("a" * 64, rendered)
        self.assertNotIn("capabilities", rendered)
        self.assertNotIn("class", rendered)
        self.assertNotIn("surfaces", rendered)
        self.assertNotIn("fingerprint", rendered)
        self.assertEqual(row["status"], "selected")

    def test_machine_detection_has_no_hostname_fallback(self):
        with mock.patch.object(brain.sys, "platform", "unsupported-os"):
            self.assertEqual(brain.machine_fingerprints(), [])

    def test_linux_fingerprint_rejects_malformed_nil_and_placeholder_ids(self):
        weak = [b"x", b"0" * 32, b"f" * 32, b"deadbeef" * 4]
        for raw in weak:
            with self.subTest(raw=raw), mock.patch.object(
                brain.sys, "platform", "linux"
            ), mock.patch.object(brain.Path, "read_bytes", return_value=raw):
                self.assertEqual(brain.machine_fingerprints(), [])

    def test_macos_fingerprint_uses_pinned_system_ioreg(self):
        completed = mock.Mock(
            returncode=0,
            stdout=b'"IOPlatformUUID" = "12345678-1234-1234-1234-123456789ABC"',
        )
        with mock.patch.object(brain.sys, "platform", "darwin"), mock.patch.object(
            brain.subprocess, "run", return_value=completed
        ) as run:
            rows = brain.machine_fingerprints()
        self.assertEqual(run.call_args.args[0][0], "/usr/sbin/ioreg")
        self.assertEqual(rows[0]["source"], "machine-v1")
        self.assertEqual(len(rows[0]["digest"]), 64)

    def test_manifest_rejects_private_shaped_capability_key_and_unknown_key(self):
        data = manifest("alpha", "a" * 64)
        data["capabilities"] = {"webhook-url": True}
        data["rawHostname"] = "must-not-be-echoed"
        findings = brain.validate_environment_manifest(data, "alpha")
        rendered = json.dumps(findings)
        self.assertIn("environment-private-key", rendered)
        self.assertIn("environment-schema", rendered)
        self.assertNotIn("rawHostname", rendered)
        self.assertNotIn("must-not-be-echoed", rendered)

    def test_manifest_allows_empty_fingerprint_list_for_explicit_selection(self):
        findings = brain.validate_environment_manifest(
            manifest("alpha", "a" * 64, fingerprints=[]), "alpha"
        )
        self.assertNotIn("environment-fingerprints", json.dumps(findings))

    def test_manifest_malformed_json_types_always_return_redacted_findings(self):
        cases = []
        for field in ("algorithm", "digest", "source"):
            data = manifest("alpha", "a" * 64)
            data["fingerprints"][0][field] = ["PRIVATE-TOKEN-SENTINEL"]
            cases.append(data)
        for version in (True, 1.0, "1"):
            cases.append(manifest("alpha", "a" * 64, schemaVersion=version))
        cases.append(manifest("alpha", "a" * 64, **{"class": []}))
        mixed_key = manifest("alpha", "a" * 64)
        mixed_key[7] = "PRIVATE-TOKEN-SENTINEL"
        cases.append(mixed_key)

        for data in cases:
            with self.subTest(data_type=type(data.get("schemaVersion"))):
                findings = brain.validate_environment_manifest(data, "alpha")
                rendered = json.dumps(findings, sort_keys=True)
                self.assertTrue(findings)
                self.assertNotIn("PRIVATE-TOKEN-SENTINEL", rendered)

    def test_manifest_loader_handles_unhashable_fingerprint_values_without_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_environment(root, "alpha", "a" * 64)
            path = root / "10_Agents/environments/alpha/environment.json"
            data = manifest("alpha", "a" * 64)
            data["fingerprints"][0]["algorithm"] = []
            path.write_text(json.dumps(data), encoding="utf-8")
            manifests, findings = brain.load_environment_manifests(root)
            self.assertEqual(manifests, {})
            self.assertIn("environment-fingerprints", json.dumps(findings))

    def test_detect_json_contains_hash_not_raw_machine_identity(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(
            brain, "machine_fingerprints", return_value=local_fingerprint("d" * 64)
        ):
            root = Path(td)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = brain.main(["env", "detect", "--json", "--vault", str(root)])
            self.assertEqual(code, 0)
            output = stream.getvalue()
            self.assertIn("d" * 64, output)
            self.assertNotIn(str(root), output)

    def test_list_remains_metadata_only_when_matching_fails(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(
            brain, "machine_fingerprints", return_value=local_fingerprint("c" * 64)
        ):
            root = Path(td)
            write_environment(root, "alpha", "a" * 64)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = brain.main(["env", "list", "--json", "--vault", str(root)])
            self.assertEqual(code, 0)
            output = stream.getvalue()
            self.assertIn("no-fingerprint-match", output)
            self.assertNotIn("a" * 64, output)
            self.assertNotIn(str(root), output)

    @unittest.skipUnless(os.name == "posix", "symlink check")
    def test_symlinked_environments_root_is_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "vault"
            root.mkdir()
            outside = Path(td) / "outside"
            write_environment(outside, "alpha", "a" * 64)
            (root / "10_Agents").mkdir()
            os.symlink(outside / "10_Agents/environments", root / "10_Agents/environments")
            manifests, findings = brain.load_environment_manifests(root)
            self.assertEqual(manifests, {})
            self.assertEqual(findings[0]["rule"], "environment-unsafe-path")

    def test_invalid_environment_directory_name_is_redacted_from_diagnostics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            secret_name = "alice@example.com-TOKEN-abc123"
            directory = root / "10_Agents/environments" / secret_name
            directory.mkdir(parents=True)
            (directory / "environment.json").write_text("{}", encoding="utf-8")
            manifests, findings = brain.load_environment_manifests(root)
            rendered = json.dumps({"manifests": manifests, "findings": findings})
            self.assertNotIn(secret_name, rendered)
            self.assertIn("<invalid-entry-001>", rendered)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = brain.main(["env", "list", "--json", "--vault", str(root)])
            self.assertEqual(code, 1)
            self.assertNotIn(secret_name, stream.getvalue())


class ValidationTests(unittest.TestCase):
    def test_validation_is_neutral_when_only_foreign_manifest_is_tracked(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(
            brain, "machine_fingerprints", return_value=[]
        ):
            root = Path(td)
            write_environment(root, "foreign-machine", "a" * 64)
            errors, _warnings = brain.run_validate(root, check_index=False)
            rules = {row["rule"] for row in errors}
            self.assertNotIn("environment-selection", rules)
            self.assertNotIn("environment-fingerprints", rules)


class MigrationTests(unittest.TestCase):
    def test_preview_lists_exact_moves_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "10_Agents/environments/old-machine"
            old.mkdir(parents=True)
            (old / "orientation-inventory.md").write_text("legacy", encoding="utf-8")
            before = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            plan = brain._environment_migration_preview(root, "old-machine", "work-laptop")
            after = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse(plan["applySupported"])
            self.assertEqual(
                plan["files"],
                [
                    {
                        "from": "10_Agents/environments/old-machine/orientation-inventory.md",
                        "to": "10_Agents/environments/work-laptop/orientation-inventory.md",
                    }
                ],
            )

    def test_cli_preview_accepts_unregistered_source_and_performs_no_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "10_Agents/environments/old-machine"
            old.mkdir(parents=True)
            (old / "orientation-inventory.md").write_text("legacy", encoding="utf-8")
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = brain.main(
                    [
                        "env",
                        "migrate",
                        "old-machine",
                        "work-laptop",
                        "--json",
                        "--vault",
                        str(root),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn('"writesPerformed": false', stream.getvalue())
            self.assertTrue((old / "orientation-inventory.md").exists())
            self.assertFalse((root / "10_Agents/environments/work-laptop").exists())

    @unittest.skipUnless(os.name == "posix", "symlink check")
    def test_preview_refuses_symlink_and_target_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "10_Agents/environments/old-machine"
            old.mkdir(parents=True)
            (root / "outside").write_text("private", encoding="utf-8")
            os.symlink(root / "outside", old / "inventory.md")
            with self.assertRaisesRegex(brain.EnvironmentSelectionError, "unsafe-migration-path"):
                brain._environment_migration_preview(root, "old-machine", "target")

    def test_preview_refuses_any_existing_target_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "10_Agents/environments/old-machine"
            source.mkdir(parents=True)
            (source / "orientation-inventory.md").write_text("legacy", encoding="utf-8")
            target = root / "10_Agents/environments/target"
            target.mkdir()
            with self.assertRaisesRegex(
                brain.EnvironmentSelectionError, "migration-target-exists"
            ):
                brain._environment_migration_preview(root, "old-machine", "target")

    def test_preview_refuses_registered_target_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "10_Agents/environments/old-machine"
            source.mkdir(parents=True)
            (source / "orientation-inventory.md").write_text("legacy", encoding="utf-8")
            write_environment(root, "target", "a" * 64)
            with self.assertRaisesRegex(
                brain.EnvironmentSelectionError, "migration-target-exists"
            ):
                brain._environment_migration_preview(root, "old-machine", "target")

    @unittest.skipUnless(os.name == "posix", "symlink check")
    def test_preview_refuses_symlinked_subdirectory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "10_Agents/environments/old-machine"
            old.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            os.symlink(outside, old / "nested")
            with self.assertRaisesRegex(
                brain.EnvironmentSelectionError, "unsafe-migration-path"
            ):
                brain._environment_migration_preview(root, "old-machine", "target")

    @unittest.skipUnless(os.name == "posix", "descriptor no-follow check")
    def test_preview_discards_rows_when_source_becomes_external_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "10_Agents/environments/old-machine"
            source.mkdir(parents=True)
            (source / "safe.md").write_text("safe", encoding="utf-8")
            parked = root / "parked-source"
            outside = root / "outside"
            outside.mkdir()
            secret_name = "EXTERNAL-PRIVATE-FILENAME-TOKEN.md"
            (outside / secret_name).write_text("private", encoding="utf-8")
            original_identity = brain._migration_identity
            swapped = False

            def swap_after_initial_identity(info):
                nonlocal swapped
                identity = original_identity(info)
                if not swapped:
                    swapped = True
                    source.rename(parked)
                    os.symlink(outside, source)
                return identity

            try:
                with mock.patch.object(
                    brain, "_migration_identity", side_effect=swap_after_initial_identity
                ), self.assertRaises(brain.EnvironmentSelectionError) as raised:
                    brain._environment_migration_preview(
                        root, "old-machine", "target"
                    )
                self.assertEqual(raised.exception.code, "unsafe-migration-path")
                self.assertNotIn(secret_name, str(raised.exception))
            finally:
                if source.is_symlink():
                    source.unlink()
                if parked.exists():
                    parked.rename(source)


if __name__ == "__main__":
    unittest.main()
