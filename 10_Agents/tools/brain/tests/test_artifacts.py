"""Offline artifact privacy, determinism, rendering, and ownership tests."""

from __future__ import annotations

import contextlib
import base64
import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
import time
import unittest
import webbrowser
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import artifacts
import brain


def note(
    title: str,
    body: str = "",
    *,
    tags: tuple[str, ...] = ("type/reference",),
    updated: str = "2026-08-11",
) -> str:
    tag_rows = "".join(f"  - {tag}\n" for tag in tags)
    return (
        "---\n"
        f"title: '{title}'\n"
        "tags:\n"
        f"{tag_rows}"
        f"updated: {updated}\n"
        "expires: 2027-08-11\n"
        "---\n\n"
        f"# {title}\n\n{body}\n"
    )


class ArtifactVault:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-artifacts-")
        self.root = Path(self.temp.name)
        (self.root / brain.ARTIFACT_DIR_RELPATH).mkdir(parents=True)
        self.tracked: set[str] = set()

    def cleanup(self):
        self.temp.cleanup()

    def write(
        self, rel: str, content: str | bytes, *, tracked: bool = False
    ) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        if tracked:
            self.tracked.add(rel)
        return path

    def data(self, *, as_of: str | None = None) -> dict:
        with mock.patch.object(brain, "git_tracked", return_value=set(self.tracked)):
            return artifacts.build_data(brain, self.root, as_of=as_of)

    def plan(self, *, as_of: str | None = None):
        with mock.patch.object(brain, "git_tracked", return_value=set(self.tracked)):
            return artifacts.build_plan(brain, self.root, as_of=as_of)


class ArtifactRenderingTests(unittest.TestCase):
    def setUp(self):
        self.vault = ArtifactVault()

    def tearDown(self):
        self.vault.cleanup()

    def test_deterministic_bytes_injection_csp_and_offline_contract(self):
        self.vault.write(
            "06_Resources/quote Ω.md",
            note(
                "</script><img src=x onerror=alert(1)> \" Ω",
                "RAW-BODY-MUST-NOT-APPEAR <b>private prose</b>",
                tags=("type/reference", "topic/unicode"),
            ),
            tracked=True,
        )
        data = self.vault.data()
        first = artifacts.render_all(brain, data)
        second = artifacts.render_all(brain, self.vault.data())
        self.assertEqual(first, second)
        graph = first[brain.ARTIFACT_OUTPUTS[0]].decode("utf-8")
        dashboard = first[brain.ARTIFACT_OUTPUTS[1]].decode("utf-8")
        for rendered in (graph, dashboard):
            self.assertNotIn("RAW-BODY-MUST-NOT-APPEAR", rendered)
            self.assertNotIn("</script><img", rendered)
            self.assertNotIn("unsafe-inline", rendered)
            self.assertNotIn("http://", rendered)
            self.assertNotIn("https://", rendered)
            self.assertNotIn("fetch(", rendered)
            self.assertNotIn("XMLHttpRequest", rendered)
            self.assertNotIn("WebSocket", rendered)
            self.assertNotIn("EventSource", rendered)
            self.assertIn("connect-src &#x27;none&#x27;", rendered)
            self.assertIn("sha256-", rendered)
            self.assertIn("textContent", rendered)
            self.assertIn("<noscript>", rendered)
            self.assertIn("prefers-reduced-motion", rendered)
            self.assertIn(":focus-visible", rendered)
            self.assertIn("@media(max-width:760px)", rendered)
        self.assertIn("\\u003c/script\\u003e", artifacts.json_for_html({"x": "</script>"}))
        self.assertIn("../../06_Resources/quote%20%CE%A9.md", graph)
        self.assertIn("aria-live=", graph)
        self.assertIn("ArrowDown", graph)
        self.assertNotIn("location.assign", graph)
        policy = re.search(r'Content-Security-Policy" content="([^"]+)"', graph).group(1)
        policy = policy.replace("&#x27;", "'")
        blocks = re.findall(r"<(style|script)(?: [^>]*)?>(.*?)</(?:style|script)>", graph, re.DOTALL)
        hashes = {
            base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
            for _kind, body in blocks
        }
        self.assertTrue(all(f"'sha256-{digest}'" in policy for digest in hashes))

    def test_private_targeting_sensitive_untracked_and_environment_are_excluded(self):
        self.vault.write(
            "06_Resources/safe.md", note("Safe", "Bounded public metadata."), tracked=True
        )
        self.vault.write(
            "06_Resources/private.md",
            note("PRIVATE-TITLE", "PRIVATE-BODY", tags=("restricted/private",)),
            tracked=True,
        )
        self.vault.write(
            "06_Resources/linker.md",
            note("LINKER-TITLE", "[private](private.md)"),
            tracked=True,
        )
        self.vault.write(
            "06_Resources/credential.md",
            note("CREDENTIAL-TITLE", "api_key=Abcdef1234567890"),
            tracked=True,
        )
        self.vault.write(
            "02_Inbox/untracked.md", note("UNTRACKED-TITLE", "UNTRACKED-BODY")
        )
        self.vault.write(
            "10_Agents/environments/work/orientation-inventory.md",
            note("ENVIRONMENT-TITLE", "ENVIRONMENT-BODY"),
            tracked=True,
        )
        rendered = b"\n".join(artifacts.render_all(brain, self.vault.data()).values()).decode()
        self.assertIn("Safe", rendered)
        for forbidden in (
            "PRIVATE-TITLE",
            "PRIVATE-BODY",
            "LINKER-TITLE",
            "CREDENTIAL-TITLE",
            "Abcdef1234567890",
            "UNTRACKED-TITLE",
            "UNTRACKED-BODY",
            "ENVIRONMENT-TITLE",
            "ENVIRONMENT-BODY",
            str(self.vault.root),
            Path.home().name,
        ):
            self.assertNotIn(forbidden, rendered)

    def test_tracked_symlink_never_imports_external_bytes(self):
        external = tempfile.TemporaryDirectory(prefix="artifact-external-")
        self.addCleanup(external.cleanup)
        source = Path(external.name) / "outside.md"
        source.write_text(note("EXTERNAL-TITLE", "EXTERNAL-BODY"), encoding="utf-8")
        target = self.vault.root / "06_Resources/linked.md"
        target.parent.mkdir(parents=True)
        try:
            target.symlink_to(source)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self.vault.tracked.add("06_Resources/linked.md")
        rendered = b"\n".join(artifacts.render_all(brain, self.vault.data()).values()).decode()
        self.assertNotIn("EXTERNAL-TITLE", rendered)
        self.assertNotIn("EXTERNAL-BODY", rendered)
        self.assertNotIn(str(source), rendered)

    def test_in_place_source_mutation_during_descriptor_read_is_excluded(self):
        target = self.vault.write(
            "06_Resources/large.md",
            note("MUTATING-TITLE", "x" * (96 * 1024)),
            tracked=True,
        )
        original = brain.os.read
        changed = False

        def mutate_after_first_chunk(descriptor, size):
            nonlocal changed
            chunk = original(descriptor, size)
            if chunk and not changed:
                changed = True
                target.write_text(note("REPLACED-TITLE", "replacement"), encoding="utf-8")
            return chunk

        with mock.patch.object(brain.os, "read", side_effect=mutate_after_first_chunk):
            rendered = b"\n".join(artifacts.render_all(brain, self.vault.data()).values()).decode()
        self.assertTrue(changed)
        self.assertNotIn("MUTATING-TITLE", rendered)
        self.assertNotIn("REPLACED-TITLE", rendered)

    def test_host_identity_and_absolute_metadata_are_redacted(self):
        self.assertEqual(
            artifacts.host_identifiers(Path("/Users/example-owner/Documents/vault")),
            frozenset({"example-owner"}),
        )
        self.assertEqual(
            artifacts.safe_text(brain, "Open /private/tmp/report.txt", "fallback"),
            "fallback",
        )
        for value in (
            "Report (/private/tmp/secret.txt)",
            "path=/private/tmp/secret.txt",
            "Report (C:\\Users\\owner\\secret.txt)",
            "path=C:/Users/owner/secret.txt",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    artifacts.safe_text(brain, value, "fallback"), "fallback"
                )
        self.assertEqual(
            artifacts.safe_text(
                brain,
                "example-owner plan",
                "fallback",
                forbidden=frozenset({"example-owner"}),
            ),
            "fallback",
        )

    def test_empty_state_and_controlled_timestamp(self):
        data = self.vault.data(as_of="2026-01-02")
        self.assertEqual(data["source"]["generatedAt"], "2026-01-02T00:00:00Z")
        self.assertEqual(data["health"]["notes"], 0)
        outputs = artifacts.render_all(brain, data)
        graph = outputs[brain.ARTIFACT_OUTPUTS[0]].decode()
        self.assertIn("No safe tracked notes are available", graph)
        with self.assertRaises(artifacts.ArtifactError):
            self.vault.data(as_of="01/02/2026")

    def test_manifest_binds_exact_outputs_and_content_digest(self):
        self.vault.write("06_Resources/a.md", note("A"), tracked=True)
        outputs = artifacts.render_all(brain, self.vault.data())
        manifest = json.loads(outputs[brain.ARTIFACT_OUTPUTS[2]])
        self.assertEqual([row["path"] for row in manifest["artifacts"]], list(brain.ARTIFACT_OUTPUTS[:2]))
        for row in manifest["artifacts"]:
            self.assertEqual(row["sha256"], brain._sha256_bytes(outputs[row["path"]]))
            self.assertEqual(row["sizeBytes"], len(outputs[row["path"]]))
        self.assertTrue(
            artifacts.owned(
                brain,
                brain.ARTIFACT_OUTPUTS[2],
                outputs[brain.ARTIFACT_OUTPUTS[2]],
                0o644,
            )
        )

    def test_large_vault_is_bounded_and_fast(self):
        for number in range(620):
            target = (number + 1) % 620
            self.vault.write(
                f"06_Resources/note-{number:04d}.md",
                note(f"Note {number:04d}", f"[next](note-{target:04d}.md)"),
                tracked=True,
            )
        started = time.monotonic()
        data = self.vault.data()
        outputs = artifacts.render_all(brain, data)
        elapsed = time.monotonic() - started
        self.assertEqual(len(data["graph"]["nodes"]), brain.ARTIFACT_MAX_NODES)
        self.assertEqual(data["graph"]["truncatedNodes"], 120)
        self.assertLessEqual(len(data["graph"]["edges"]), brain.ARTIFACT_MAX_EDGES)
        self.assertLess(len(outputs[brain.ARTIFACT_OUTPUTS[0]]), 2 * 1024 * 1024)
        self.assertLess(elapsed, 8.0)

    def test_no_git_inventory_fails_closed(self):
        with mock.patch.object(brain, "git_tracked", return_value=None):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.build_data(brain, self.vault.root)

    def test_filtered_note_additions_do_not_influence_bytes(self):
        self.vault.write("06_Resources/safe.md", note("Safe"), tracked=True)
        before = artifacts.render_all(brain, self.vault.data())
        self.vault.write(
            "06_Resources/private.md",
            note("PRIVATE", tags=("restricted/private",)),
            tracked=True,
        )
        self.vault.write(
            "06_Resources/secret.md",
            note("SECRET", "password=CorrectHorse123"),
            tracked=True,
        )
        self.vault.write("02_Inbox/untracked.md", note("UNTRACKED"))
        self.vault.write(
            "10_Agents/environments/other/orientation-inventory.md",
            note("OTHER-ENV"),
            tracked=True,
        )
        self.assertEqual(before, artifacts.render_all(brain, self.vault.data()))

    def test_filtered_basename_collision_does_not_influence_safe_resolution(self):
        self.vault.write(
            "06_Resources/public-target.md", note("Public target"), tracked=True
        )
        self.vault.write(
            "06_Resources/source.md",
            note("Source", "[" * 2 + "public-target" + "]" * 2),
            tracked=True,
        )
        before = artifacts.render_all(brain, self.vault.data())
        self.vault.write(
            "07_Archives/public-target.md",
            note("Private duplicate", tags=("restricted/private",)),
            tracked=True,
        )
        self.assertEqual(before, artifacts.render_all(brain, self.vault.data()))

    def test_cli_artifacts_never_selects_or_reads_an_environment(self):
        with mock.patch.object(brain, "git_tracked", return_value=set(self.vault.tracked)), mock.patch.object(
            brain, "select_environment", side_effect=AssertionError("environment selected")
        ), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                brain.main(["--vault", str(self.vault.root), "artifacts", "--json"]),
                0,
            )


class ArtifactWriterTests(unittest.TestCase):
    def setUp(self):
        self.vault = ArtifactVault()
        self.vault.write("06_Resources/a.md", note("A"), tracked=True)
        self.initial = artifacts.render_all(brain, self.vault.data(as_of="2026-08-11"))

    def tearDown(self):
        self.vault.cleanup()

    def transaction_files(self) -> list[str]:
        return sorted(
            path.name
            for path in (self.vault.root / brain.ARTIFACT_DIR_RELPATH).iterdir()
            if ".migrate-" in path.name
        )

    def test_exact_inventory_write_noop_modes_and_check(self):
        self.assertEqual(artifacts.write(brain, self.vault.root, self.initial)["filesChanged"], 3)
        inodes = {}
        for rel in brain.ARTIFACT_OUTPUTS:
            path = self.vault.root / rel
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
            inodes[rel] = path.stat().st_ino
        self.assertEqual(artifacts.write(brain, self.vault.root, self.initial)["status"], "unchanged")
        self.assertEqual(inodes, {rel: (self.vault.root / rel).stat().st_ino for rel in brain.ARTIFACT_OUTPUTS})
        self.assertEqual(self.transaction_files(), [])

    def test_foreign_occupant_and_case_collision_are_preserved(self):
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        target.write_bytes(b"foreign")
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.write(brain, self.vault.root, self.initial)
        self.assertEqual(target.read_bytes(), b"foreign")
        self.assertFalse((self.vault.root / brain.ARTIFACT_OUTPUTS[1]).exists())
        target.unlink()
        collision = target.with_name("Link-Graph.html")
        collision.write_bytes(b"case-foreign")
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.write(brain, self.vault.root, self.initial)
        self.assertEqual(collision.read_bytes(), b"case-foreign")
        self.assertEqual(self.transaction_files(), [])

    def test_concurrent_absent_occupant_is_preserved(self):
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        original = brain._stage_migration_at
        inserted = False

        def stage_then_insert(*args, **kwargs):
            nonlocal inserted
            result = original(*args, **kwargs)
            if not inserted:
                target.write_bytes(b"late-foreign")
                inserted = True
            return result

        with mock.patch.object(brain, "_stage_migration_at", side_effect=stage_then_insert):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, self.initial)
        self.assertEqual(target.read_bytes(), b"late-foreign")
        self.assertEqual(self.transaction_files(), [])

    def test_late_casefold_inventory_blocks_before_publication(self):
        original = brain._stage_migration_at
        original_listdir = artifacts.os.listdir
        staged = False

        def stage_then_expose_case(*args, **kwargs):
            nonlocal staged
            result = original(*args, **kwargs)
            staged = True
            return result

        def case_aware_inventory(parent):
            names = original_listdir(parent)
            if staged and "Link-Graph.html" not in names:
                names.append("Link-Graph.html")
            return names

        with mock.patch.object(
            brain, "_stage_migration_at", side_effect=stage_then_expose_case
        ), mock.patch.object(
            artifacts.os, "listdir", side_effect=case_aware_inventory
        ):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, self.initial)
        self.assertTrue(staged)
        self.assertFalse(any((self.vault.root / rel).exists() for rel in brain.ARTIFACT_OUTPUTS))
        self.assertEqual(self.transaction_files(), [])

    def test_late_physical_casefold_sibling_is_preserved_when_supported(self):
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        collision = target.with_name("Link-Graph.html")
        collision.write_bytes(b"probe")
        if target.exists():
            collision.unlink()
            self.skipTest("filesystem cannot materialize casefold siblings")
        collision.unlink()
        original = brain._stage_migration_at
        inserted = False

        def stage_then_insert_case(*args, **kwargs):
            nonlocal inserted
            result = original(*args, **kwargs)
            if not inserted:
                collision.write_bytes(b"late-case-foreign")
                inserted = True
            return result

        with mock.patch.object(
            brain, "_stage_migration_at", side_effect=stage_then_insert_case
        ):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, self.initial)
        self.assertTrue(inserted)
        self.assertEqual(collision.read_bytes(), b"late-case-foreign")
        self.assertFalse(any((self.vault.root / rel).exists() for rel in brain.ARTIFACT_OUTPUTS))
        self.assertEqual(self.transaction_files(), [])

    def test_concurrent_replacement_of_owned_output_is_preserved(self):
        artifacts.write(brain, self.vault.root, self.initial)
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        changed = artifacts.render_all(brain, self.vault.data(as_of="2026-08-12"))
        original = brain._stage_migration_at
        replaced = False

        def stage_then_replace(*args, **kwargs):
            nonlocal replaced
            result = original(*args, **kwargs)
            if not replaced:
                target.unlink()
                target.write_bytes(b"replacement-foreign")
                replaced = True
            return result

        with mock.patch.object(brain, "_stage_migration_at", side_effect=stage_then_replace):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, changed)
        self.assertEqual(target.read_bytes(), b"replacement-foreign")
        self.assertEqual(self.transaction_files(), [])

    def test_symlinked_output_parent_cannot_write_outside(self):
        artifact_dir = self.vault.root / brain.ARTIFACT_DIR_RELPATH
        artifact_dir.rmdir()
        external = tempfile.TemporaryDirectory(prefix="artifact-output-external-")
        self.addCleanup(external.cleanup)
        outside = Path(external.name)
        try:
            artifact_dir.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaises((artifacts.ArtifactError, OSError)):
            artifacts.write(brain, self.vault.root, self.initial)
        self.assertEqual(list(outside.iterdir()), [])

    def test_interrupt_after_first_publication_rolls_back_all_exactly(self):
        artifacts.write(brain, self.vault.root, self.initial)
        before = {rel: (self.vault.root / rel).read_bytes() for rel in brain.ARTIFACT_OUTPUTS}
        changed = artifacts.render_all(brain, self.vault.data(as_of="2026-08-12"))
        original = brain._install_migration_at
        calls = 0

        def interrupt_second(parent, staged, name):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt
            return original(parent, staged, name)

        with mock.patch.object(brain, "_install_migration_at", side_effect=interrupt_second):
            with self.assertRaises(KeyboardInterrupt):
                artifacts.write(brain, self.vault.root, changed)
        self.assertEqual(before, {rel: (self.vault.root / rel).read_bytes() for rel in brain.ARTIFACT_OUTPUTS})
        self.assertEqual(self.transaction_files(), [])

    def test_interrupt_after_real_quarantine_restores_prior_exactly(self):
        artifacts.write(brain, self.vault.root, self.initial)
        before = {rel: (self.vault.root / rel).read_bytes() for rel in brain.ARTIFACT_OUTPUTS}
        changed = artifacts.render_all(brain, self.vault.data(as_of="2026-08-12"))
        original = brain._quarantine_migration_at
        interrupted = False

        def quarantine_then_interrupt(parent, name, backup):
            nonlocal interrupted
            original(parent, name, backup)
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt

        with mock.patch.object(brain, "_quarantine_migration_at", side_effect=quarantine_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                artifacts.write(brain, self.vault.root, changed)
        self.assertTrue(interrupted)
        self.assertEqual(before, {rel: (self.vault.root / rel).read_bytes() for rel in brain.ARTIFACT_OUTPUTS})
        self.assertEqual(self.transaction_files(), [])

    def test_final_edit_between_check_and_quarantine_is_restored_and_refused(self):
        artifacts.write(brain, self.vault.root, self.initial)
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        changed = artifacts.render_all(brain, self.vault.data(as_of="2026-08-12"))
        original = brain._quarantine_migration_at
        raced = b"concurrent-foreign"
        injected = False

        def edit_then_quarantine(parent, name, backup):
            nonlocal injected
            if not injected:
                descriptor = os.open(name, os.O_WRONLY | os.O_TRUNC, dir_fd=parent)
                os.write(descriptor, raced)
                os.close(descriptor)
                injected = True
            original(parent, name, backup)

        with mock.patch.object(brain, "_quarantine_migration_at", side_effect=edit_then_quarantine):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, changed)
        self.assertTrue(injected)
        self.assertEqual(target.read_bytes(), raced)
        self.assertFalse((self.vault.root / brain.ARTIFACT_OUTPUTS[1]).read_bytes() == changed[brain.ARTIFACT_OUTPUTS[1]])
        self.assertEqual(self.transaction_files(), [])

    def test_stage_replacement_during_install_never_becomes_canonical(self):
        artifacts.write(brain, self.vault.root, self.initial)
        before = {rel: (self.vault.root / rel).read_bytes() for rel in brain.ARTIFACT_OUTPUTS}
        changed = artifacts.render_all(brain, self.vault.data(as_of="2026-08-12"))
        original = brain._install_migration_at
        replaced = False

        def replace_stage_then_install(parent, staged, name):
            nonlocal replaced
            if not replaced:
                os.unlink(staged, dir_fd=parent)
                descriptor = os.open(
                    staged,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o644,
                    dir_fd=parent,
                )
                os.write(descriptor, b"foreign-stage")
                os.close(descriptor)
                replaced = True
            original(parent, staged, name)

        with mock.patch.object(brain, "_install_migration_at", side_effect=replace_stage_then_install):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, changed)
        self.assertTrue(replaced)
        self.assertEqual(before, {rel: (self.vault.root / rel).read_bytes() for rel in brain.ARTIFACT_OUTPUTS})
        foreign_stages = [
            path
            for path in (self.vault.root / brain.ARTIFACT_DIR_RELPATH).iterdir()
            if ".migrate-new-" in path.name
        ]
        self.assertEqual(len(foreign_stages), 1)
        self.assertEqual(foreign_stages[0].read_bytes(), b"foreign-stage")

    def test_interrupted_stage_creation_preserves_foreign_name_replacement(self):
        artifact_dir = self.vault.root / brain.ARTIFACT_DIR_RELPATH
        parent = os.open(artifact_dir, os.O_RDONLY)
        self.addCleanup(os.close, parent)
        basename = "link-graph.html"
        reserved = f".{basename}.migrate-new-{'1' * 24}"
        foreign = b"foreign-stage-replacement"
        original_write = brain.os.write
        replaced = False

        def write_then_replace(descriptor, data):
            nonlocal replaced
            written = original_write(descriptor, data)
            if not replaced:
                os.unlink(reserved, dir_fd=parent)
                replacement = os.open(
                    reserved,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=parent,
                )
                try:
                    original_write(replacement, foreign)
                finally:
                    os.close(replacement)
                replaced = True
                raise KeyboardInterrupt
            return written

        ownership = {}
        with mock.patch.object(brain.os, "write", side_effect=write_then_replace):
            with self.assertRaises(KeyboardInterrupt):
                brain._stage_migration_at(
                    parent,
                    basename,
                    b"owned-stage-bytes",
                    0o644,
                    ownership=ownership,
                    reserved_name=reserved,
                )
        self.assertTrue(replaced)
        self.assertEqual((artifact_dir / reserved).read_bytes(), foreign)
        self.assertNotIn("identity", ownership)

    def test_preview_check_and_json_are_zero_write(self):
        before = sorted(path.name for path in (self.vault.root / brain.ARTIFACT_DIR_RELPATH).iterdir())
        args = SimpleNamespace(as_of="2026-08-11", check=True, json=True, open=False, write=False)
        with mock.patch.object(brain, "git_tracked", return_value=set(self.vault.tracked)), contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(artifacts.command(brain, self.vault.root, args), 1)
        self.assertFalse(json.loads(stream.getvalue())["fresh"])
        self.assertEqual(before, sorted(path.name for path in (self.vault.root / brain.ARTIFACT_DIR_RELPATH).iterdir()))

    def test_local_open_uses_only_two_file_uris_and_fake_spy(self):
        artifacts.write(brain, self.vault.root, self.initial)
        calls: list[str] = []

        def opener(uri: str) -> bool:
            calls.append(uri)
            return True

        self.assertEqual(artifacts.open_local(brain, self.vault.root, opener=opener), 2)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(uri.startswith("file://") for uri in calls))
        self.assertTrue(calls[0].endswith("/link-graph.html"))
        self.assertTrue(calls[1].endswith("/health-dashboard.html"))

    def test_local_open_uses_authenticated_snapshot_after_original_symlink_swap(self):
        artifacts.write(brain, self.vault.root, self.initial)
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        expected = target.read_bytes()
        external = self.vault.write("external.html", b"external-bytes")
        opened_paths: list[Path] = []
        seen: list[bytes] = []

        def opener(uri: str) -> bool:
            opened = Path(unquote(urlparse(uri).path))
            opened_paths.append(opened)
            if not target.is_symlink():
                target.unlink()
                target.symlink_to(external)
            seen.append(opened.read_bytes())
            return True

        try:
            self.assertEqual(
                artifacts.open_local(brain, self.vault.root, opener=opener),
                2,
            )
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self.assertEqual(seen[0], expected)
        self.assertNotEqual(seen[0], external.read_bytes())
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.read_bytes(), b"external-bytes")
        self.assertTrue(all(not path.exists() for path in opened_paths))

    def test_post_write_refresh_rejects_replacement_and_keeps_recovery(self):
        artifacts.write(brain, self.vault.root, self.initial)
        rel = brain.ARTIFACT_OUTPUTS[0]
        target = self.vault.root / rel
        prior = target.read_bytes()
        foreign = b"post-write-foreign"
        args = SimpleNamespace(
            as_of="2026-08-12",
            check=False,
            json=True,
            open=False,
            write=True,
        )
        original_plan = artifacts.build_plan
        calls = 0

        def replace_before_refreshed_plan(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                target.unlink()
                target.write_bytes(foreign)
            return original_plan(*args, **kwargs)

        with mock.patch.object(
            artifacts,
            "build_plan",
            side_effect=replace_before_refreshed_plan,
        ), mock.patch.object(
            brain, "git_tracked", return_value=set(self.vault.tracked)
        ), contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(
                artifacts.command(brain, self.vault.root, args), 1
            )
        self.assertEqual(
            json.loads(stream.getvalue()),
            {"error": "artifact generation failed safely"},
        )
        self.assertEqual(target.read_bytes(), foreign)
        backups = [
            path
            for path in target.parent.iterdir()
            if path.name.startswith(".link-graph.html.migrate-old-")
        ]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), prior)

    def test_create_mode_replacement_after_refreshed_plan_is_refused(self):
        rel = brain.ARTIFACT_OUTPUTS[0]
        target = self.vault.root / rel
        foreign = b"foreign-after-refreshed-plan"
        args = SimpleNamespace(
            as_of="2026-08-11",
            check=False,
            json=True,
            open=False,
            write=True,
        )
        original_plan = artifacts.build_plan
        calls = 0

        def replace_after_refreshed_plan(*args, **kwargs):
            nonlocal calls
            plan, outputs = original_plan(*args, **kwargs)
            calls += 1
            if calls == 2:
                target.unlink()
                target.write_bytes(foreign)
            return plan, outputs

        with mock.patch.object(
            artifacts,
            "build_plan",
            side_effect=replace_after_refreshed_plan,
        ), mock.patch.object(
            brain, "git_tracked", return_value=set(self.vault.tracked)
        ), contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(
                artifacts.command(brain, self.vault.root, args), 1
            )
        self.assertEqual(
            json.loads(stream.getvalue()),
            {"error": "artifact generation failed safely"},
        )
        self.assertEqual(target.read_bytes(), foreign)
        self.assertFalse(
            any(
                (self.vault.root / other).exists()
                for other in brain.ARTIFACT_OUTPUTS[1:]
            )
        )
        self.assertEqual(self.transaction_files(), [])

    def test_update_replacement_after_refreshed_plan_keeps_recovery(self):
        artifacts.write(brain, self.vault.root, self.initial)
        before = {
            rel: (self.vault.root / rel).read_bytes()
            for rel in brain.ARTIFACT_OUTPUTS
        }
        rel = brain.ARTIFACT_OUTPUTS[0]
        target = self.vault.root / rel
        foreign = b"foreign-after-update-refresh"
        original_plan = artifacts.build_plan
        calls = 0

        def replace_after_refreshed_plan(*args, **kwargs):
            nonlocal calls
            plan, outputs = original_plan(*args, **kwargs)
            calls += 1
            if calls == 2:
                target.unlink()
                target.write_bytes(foreign)
            return plan, outputs

        args = SimpleNamespace(
            as_of="2026-08-12",
            check=False,
            json=True,
            open=False,
            write=True,
        )
        stream = io.StringIO()
        with mock.patch.object(
            artifacts,
            "build_plan",
            side_effect=replace_after_refreshed_plan,
        ), mock.patch.object(
            brain, "git_tracked", return_value=set(self.vault.tracked)
        ), contextlib.redirect_stdout(stream):
            self.assertEqual(
                artifacts.command(brain, self.vault.root, args), 1
            )
        self.assertEqual(
            json.loads(stream.getvalue()),
            {"error": "artifact generation failed safely"},
        )
        self.assertEqual(target.read_bytes(), foreign)
        backups = [
            path
            for path in target.parent.iterdir()
            if path.name.startswith(".link-graph.html.migrate-old-")
        ]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before[rel])
        for other in brain.ARTIFACT_OUTPUTS[1:]:
            self.assertEqual((self.vault.root / other).read_bytes(), before[other])

    def test_unchanged_replacement_after_refreshed_plan_is_refused(self):
        artifacts.write(brain, self.vault.root, self.initial)
        rel = brain.ARTIFACT_OUTPUTS[0]
        target = self.vault.root / rel
        foreign = b"foreign-after-unchanged-refresh"
        original_plan = artifacts.build_plan
        calls = 0

        def replace_after_refreshed_plan(*args, **kwargs):
            nonlocal calls
            plan, outputs = original_plan(*args, **kwargs)
            calls += 1
            if calls == 2:
                target.unlink()
                target.write_bytes(foreign)
            return plan, outputs

        args = SimpleNamespace(
            as_of="2026-08-11",
            check=False,
            json=True,
            open=False,
            write=True,
        )
        stream = io.StringIO()
        with mock.patch.object(
            artifacts,
            "build_plan",
            side_effect=replace_after_refreshed_plan,
        ), mock.patch.object(
            brain, "git_tracked", return_value=set(self.vault.tracked)
        ), contextlib.redirect_stdout(stream):
            self.assertEqual(
                artifacts.command(brain, self.vault.root, args), 1
            )
        self.assertEqual(
            json.loads(stream.getvalue()),
            {"error": "artifact generation failed safely"},
        )
        self.assertEqual(target.read_bytes(), foreign)
        self.assertEqual(self.transaction_files(), [])

    def test_browser_exception_is_redacted_after_snapshot_cleanup(self):
        artifacts.write(brain, self.vault.root, self.initial)
        args = SimpleNamespace(
            as_of="2026-08-11",
            check=False,
            json=True,
            open=True,
            write=False,
        )
        opened_paths: list[Path] = []

        def fail(uri: str) -> bool:
            opened_paths.append(Path(unquote(urlparse(uri).path)))
            self.assertEqual(
                stat.S_IMODE(opened_paths[-1].stat().st_mode), 0o400
            )
            self.assertEqual(
                stat.S_IMODE(opened_paths[-1].parent.stat().st_mode), 0o700
            )
            raise webbrowser.Error(f"browser failed for {uri}")

        stream = io.StringIO()
        with mock.patch.object(
            brain, "git_tracked", return_value=set(self.vault.tracked)
        ), mock.patch(
            "webbrowser.open_new_tab", side_effect=fail
        ), contextlib.redirect_stdout(stream):
            self.assertEqual(
                artifacts.command(brain, self.vault.root, args), 1
            )
        output = stream.getvalue()
        self.assertEqual(
            json.loads(output), {"error": "artifact generation failed safely"}
        )
        self.assertEqual(len(opened_paths), 1)
        self.assertFalse(opened_paths[0].exists())
        self.assertNotIn(str(opened_paths[0]), output)

    def test_browser_interrupt_cleans_snapshot_and_propagates(self):
        artifacts.write(brain, self.vault.root, self.initial)
        opened_paths: list[Path] = []

        def interrupt(uri: str) -> bool:
            opened_paths.append(Path(unquote(urlparse(uri).path)))
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            artifacts.open_local(brain, self.vault.root, opener=interrupt)
        self.assertEqual(len(opened_paths), 1)
        self.assertFalse(opened_paths[0].exists())

    def test_local_open_refuses_late_symlink_without_calling_spy(self):
        artifacts.write(brain, self.vault.root, self.initial)
        target = self.vault.root / brain.ARTIFACT_OUTPUTS[0]
        target.unlink()
        external = self.vault.root / "external.html"
        external.write_bytes(b"external")
        try:
            target.symlink_to(external)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        opener = mock.Mock(return_value=True)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.open_local(brain, self.vault.root, opener=opener)
        opener.assert_not_called()
        self.assertEqual(external.read_bytes(), b"external")

    def test_invalid_inventory_is_refused(self):
        partial = dict(self.initial)
        partial.pop(brain.ARTIFACT_OUTPUTS[-1])
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.write(brain, self.vault.root, partial)

    def test_unsupported_runtime_is_preview_only(self):
        with mock.patch.object(brain, "_migration_mutation_supported", return_value=False):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.write(brain, self.vault.root, self.initial)
        self.assertFalse(any((self.vault.root / rel).exists() for rel in brain.ARTIFACT_OUTPUTS))


if __name__ == "__main__":
    unittest.main()
