"""Dual-format link engine and source-hashed migration tests (issue #74)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402


ROOT = Path(__file__).resolve().parents[4]
MIGRATION_FIXTURE = Path(__file__).parent / "fixtures" / "link-migration"


def note(body: str, title: str = "Note") -> str:
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n  - type/note\n"
        "updated: 2026-08-11\n"
        "---\n\n"
        + body
    )


def write_files(root: Path, files: dict[str, str | bytes]) -> None:
    for relative, contents in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, bytes):
            path.write_bytes(contents)
        else:
            path.write_text(contents, encoding="utf-8")


def git_vault(root: Path, files: dict[str, str | bytes]) -> Path:
    write_files(root, files)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Link Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "link@test.invalid"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    return root


def fixture_files(*, crlf: bool = False, bom: bool = False) -> dict[str, str | bytes]:
    files: dict[str, str | bytes] = {}
    for name in ("source.md", "target.md", "image.png"):
        data = (MIGRATION_FIXTURE / name).read_bytes()
        if name == "source.md" and crlf:
            data = data.replace(b"\n", b"\r\n")
        if name == "source.md" and bom:
            data = b"\xef\xbb\xbf" + data
        files[name] = data
    return files


class GenericLinkParserTests(unittest.TestCase):
    def test_both_formats_ranges_and_false_positive_exclusions(self):
        text = (
            "---\n"
            "title: x\n"
            "sample: [yaml](hidden.md)\n"
            "---\n"
            "é [Child](child/note.md#Some%20Heading) ![Alt](../pic%20one.png)\n"
            "[Angle](<space%20note.md>) [web](https://example.com/x) https://example.com/raw\n"
            "[Title](yes.md \"title\") [Angle title](<space%20note.md> 'title') "
            "[garbage](yes.md garbage) [angle-junk](<yes.md>junk)\n"
            "`[inline](no.md)` \\[odd](no.md) \\\\[even](yes.md)\n"
            "```md\n[fenced](no.md) [[hidden]]\n```\n"
            "[[legacy|Label]] \\[[odd-wiki]] \\\\[[even-wiki]]\n"
        )
        lines = text.split("\n")
        _fm, _errors, body_start, _has = brain.parse_frontmatter(lines)
        links, _headings, _tags, _tasks = brain.extract_body(lines, body_start)
        by_raw = {link["raw"]: link for link in links}
        self.assertEqual(
            set(by_raw),
            {
                "[Child](child/note.md#Some%20Heading)",
                "![Alt](../pic%20one.png)",
                "[Angle](<space%20note.md>)",
                "[Title](yes.md \"title\")",
                "[Angle title](<space%20note.md> 'title')",
                "[even](yes.md)",
                "[[legacy|Label]]",
                "[[even-wiki]]",
            },
        )
        child = by_raw["[Child](child/note.md#Some%20Heading)"]
        self.assertEqual(child["format"], "markdown")
        self.assertEqual(child["destination"], "child/note.md")
        self.assertEqual(child["fragment"], "Some Heading")
        self.assertEqual(child["label"], "Child")
        legacy = by_raw["[[legacy|Label]]"]
        self.assertEqual((legacy["format"], legacy["label"]), ("wikilink", "Label"))
        encoded = text.encode("utf-8")
        for link in links:
            start = link["range"]["start"]["offset"]
            end = link["range"]["end"]["offset"]
            self.assertEqual(encoded[start:end].decode("utf-8"), link["raw"])

    def test_heading_slugs_are_github_compatible_and_duplicates_are_unique(self):
        lines = note(
            "# A_B!\n# A_B!\n# Café — déjà?\n"
            "# [Foo](target.md) &amp; B\n"
            "# [Foo](target.md) &amp; B\n"
        ).split("\n")
        _fm, _errors, body_start, _has = brain.parse_frontmatter(lines)
        _links, headings, _tags, _tasks = brain.extract_body(lines, body_start)
        self.assertEqual(
            [heading["slug"] for heading in headings],
            ["ab", "ab-1", "café-déjà", "foo-b", "foo-b-1"],
        )


class GenericResolutionTests(unittest.TestCase):
    def test_source_relative_encoding_self_assets_and_absolute_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_files(
                root,
                {
                    "a/parent.md": note("# Parent heading\n", "Parent"),
                    "a/b/source.md": note(
                        "# Local\n"
                        "[parent](../parent.md#parent-heading) "
                        "[child](child/%C3%BCnicode%20note.md) "
                        "![pic](../pic%20one.png) [self](#local) "
                        "[absolute](/a/parent.md) [bad-percent](bad%ZZ.md) "
                        "[bad-fragment](../parent.md#bad%) "
                        "[bad-nul](bad%00.md) [bad-separator](child%2Fnote.md) "
                        "[query](child.md?q=1) [encoded-scheme](%61:/parent.md) "
                        "[web](https://example.com)\n",
                        "Source",
                    ),
                    "a/b/child/ünicode note.md": note("child\n", "Child"),
                    "a/pic one.png": b"png",
                },
            )
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            links = {link["label"]: link for link in index["notes"]["a/b/source.md"]["links"]}
            self.assertEqual(links["parent"]["resolved"], "a/parent.md")
            self.assertEqual(links["parent"]["resolution"]["fragment"]["slug"], "parent-heading")
            self.assertEqual(links["child"]["resolved"], "a/b/child/ünicode note.md")
            self.assertEqual(links["pic"]["resolved"], "a/pic one.png")
            self.assertEqual(links["self"]["resolved"], "a/b/source.md")
            self.assertEqual(links["absolute"]["resolution"]["status"], "unsupported-destination")
            for label in (
                "bad-percent",
                "bad-fragment",
                "bad-nul",
                "bad-separator",
                "query",
            ):
                self.assertIsNone(links[label]["resolved"])
                self.assertEqual(
                    links[label]["resolution"]["status"], "unsupported-destination"
                )
                self.assertEqual(links[label]["warnings"], ["invalid-url-encoding"])
            self.assertNotIn("web", links)
            self.assertNotIn("encoded-scheme", links)

    def test_migration_preserves_self_heading_and_explicit_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_files(
                root,
                {
                    "source.md": note(
                        "# Local heading\n[[#Local heading|Stay here]]\n", "Source"
                    )
                },
            )
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            link = index["notes"]["source.md"]["links"][0]
            self.assertEqual(link["resolved"], "source.md")
            self.assertEqual(
                brain.render_migrated_link("source.md", link),
                "[Stay here](#local-heading)",
            )

    def test_duplicate_legacy_heading_is_ambiguous_but_markdown_slug_is_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_files(
                root,
                {
                    "source.md": note(
                        "[second](target.md#ab-1) [[target#A_B!]]\n", "Source"
                    ),
                    "target.md": note("# A_B!\n# A_B!\n", "Target"),
                },
            )
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            markdown, legacy = index["notes"]["source.md"]["links"]
            self.assertEqual(markdown["resolved"], "target.md")
            self.assertEqual(markdown["resolution"]["fragment"]["slug"], "ab-1")
            self.assertIsNone(legacy["resolved"])
            self.assertEqual(legacy["resolution"]["status"], "ambiguous")
            self.assertIn("ambiguous-fragment", legacy["warnings"])

    def test_path_ambiguity_never_falls_through(self):
        resolver = brain.Resolver(
            ["a/dup.md", "b/dup.md"],
            ["assets/dup.png"],
            {"a/dup.md": "Different", "b/dup.md": "Different"},
        )
        resolved, warnings = resolver.resolve("dup", "source.md")
        self.assertIsNone(resolved)
        self.assertEqual(warnings[0], "ambiguous")


@unittest.skipUnless(os.name == "posix", "held-parent mutation contract is POSIX-only")
class LinkMigrationTests(unittest.TestCase):
    def _simulate_crash_state(
        self,
        root: Path,
        plan: dict,
        *,
        installed: bool,
        committed: bool,
        remove_backup: bool = False,
    ) -> tuple[bytes, bytes]:
        row = plan["edits"][0]
        parent, name = brain._open_migration_parent(root, row["path"])
        root_parent, _unused = brain._open_migration_parent(root, "journal-placeholder")
        source, info = brain._read_migration_at(parent, name)
        desired = brain._desired_migration_bytes(source, row)
        item = {
            "backup": brain._unused_migration_name(parent, name, "old"),
            "desired": desired,
            "identity": brain._link_migration_identity(info),
            "name": name,
            "new": brain._stage_migration_at(parent, name, desired, stat.S_IMODE(info.st_mode)),
            "parent": parent,
            "rel": row["path"],
            "source": source,
        }
        payload = brain._journal_payload(plan, [item])
        payload["pid"] = 99_999_999
        guard = brain._write_migration_journal(root_parent, payload, create=True)
        brain._quarantine_migration_at(parent, name, item["backup"])
        if installed:
            brain._install_migration_at(parent, item["new"], name)
        if committed:
            payload["committed"] = True
            brain._write_migration_journal(
                root_parent, payload, create=False, guard=guard
            )
        if remove_backup:
            os.unlink(item["backup"], dir_fd=parent)
        brain._close_migration_journal_guard(guard)
        os.close(parent)
        os.close(root_parent)
        return source, desired

    def test_plan_write_line_endings_labels_hashes_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files(crlf=True, bom=True))
            original = (root / "source.md").read_bytes()
            plan = brain.build_link_migration_plan(root)
            self.assertEqual(plan, brain.build_link_migration_plan(root))
            self.assertEqual(plan["status"], "ready")
            self.assertEqual(
                plan["summary"],
                {
                    "filesChanged": 1,
                    "filesScanned": 2,
                    "legacyLinks": 3,
                    "linksConverted": 2,
                    "markdownLinks": 0,
                    "placeholders": 1,
                    "unsupportedBlockReferences": 0,
                },
            )
            edit = plan["edits"][0]
            self.assertEqual(edit["sourceSha256"], brain._sha256_bytes(original))
            after_values = [row["after"] for row in edit["replacements"]]
            self.assertEqual(
                after_values,
                [
                    "[Readable label](target.md#ab)",
                    "![image.png](image.png)",
                ],
            )
            result = brain.apply_link_migration_plan(root, plan)
            self.assertEqual(result["linksConverted"], 2)
            migrated = (root / "source.md").read_bytes()
            self.assertTrue(migrated.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(migrated.count(b"\r\n"), original.count(b"\r\n"))
            self.assertIn(b"[[{{placeholder}}]]", migrated)
            second = brain.build_link_migration_plan(root)
            self.assertEqual(second["edits"], [])
            self.assertEqual(second["summary"]["legacyLinks"], 1)
            self.assertEqual(brain.apply_link_migration_plan(root, second)["filesChanged"], 0)

    def test_restricted_plan_redacts_alias_in_preview_and_write_payloads(self):
        secret = "DO-NOT-LEAK-ALIAS"
        with tempfile.TemporaryDirectory() as temporary:
            restricted = note(f"[[target|{secret}]]\n", "Restricted").replace(
                "  - type/note\n", "  - type/note\n  - restricted/private\n"
            )
            root = git_vault(
                Path(temporary),
                {
                    "restricted.md": restricted,
                    "target.md": note("target\n", "Target"),
                },
            )
            internal = brain.build_link_migration_plan(root)
            self.assertTrue(internal["edits"][0]["restricted"])
            self.assertIn(secret, internal["edits"][0]["replacements"][0]["before"])
            for mode in ([], ["--write"]):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = brain.main(
                        ["--vault", str(root), "migrate-links", *mode, "--json"]
                    )
                self.assertEqual(code, 0)
                self.assertNotIn(secret, output.getvalue())
                replacement = json.loads(output.getvalue())["plan"]["edits"][0][
                    "replacements"
                ][0] if mode else json.loads(output.getvalue())["edits"][0]["replacements"][0]
                self.assertTrue(replacement["redacted"])
                self.assertIsNone(replacement["before"])
                self.assertIsNone(replacement["after"])
                if not mode:
                    continue
                break

    def test_check_cli_requires_zero_legacy_links_including_placeholders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = brain.main(["--vault", str(root), "migrate-links", "--check", "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.getvalue())["status"], "ready")
            plan = brain.build_link_migration_plan(root)
            brain.apply_link_migration_plan(root, plan)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                code = brain.main(["--vault", str(root), "migrate-links", "--check"])
            self.assertEqual(code, 1)
            self.assertEqual(brain.build_link_migration_plan(root)["edits"], [])
            (root / "source.md").write_text(
                (root / "source.md").read_text(encoding="utf-8").replace(
                    "[[{{placeholder}}]]", "placeholder"
                ),
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                code = brain.main(["--vault", str(root), "migrate-links", "--check"])
            self.assertEqual(code, 0)

    def test_preview_and_check_do_not_recover_interrupted_transaction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            self._simulate_crash_state(root, plan, installed=True, committed=False)

            def snapshot() -> list[tuple[str, int, bytes]]:
                return sorted(
                    (
                        path.relative_to(root).as_posix(),
                        stat.S_IMODE(path.lstat().st_mode),
                        path.read_bytes(),
                    )
                    for path in root.rglob("*")
                    if path.is_file() and ".git/" not in path.relative_to(root).as_posix()
                )

            before = snapshot()
            for option in ([], ["--check"]):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = brain.main(
                        ["--vault", str(root), "migrate-links", *option, "--json"]
                    )
                self.assertEqual(code, 1)
                self.assertIn("interrupted-migration", json.loads(output.getvalue())["error"])
                self.assertEqual(snapshot(), before)

    def test_recovery_artifacts_are_ignored_but_still_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = fixture_files()
            files[".gitignore"] = (ROOT / ".gitignore").read_bytes()
            root = git_vault(Path(temporary), files)
            plan = brain.build_link_migration_plan(root)
            self._simulate_crash_state(root, plan, installed=False, committed=False)
            self.assertTrue((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())
            self.assertTrue(list(root.glob(".source.md.migrate-new-*")))
            self.assertTrue(list(root.glob(".source.md.migrate-old-*")))
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn(".brain-link-migration", status)
            self.assertNotIn(".migrate-new-", status)
            self.assertNotIn(".migrate-old-", status)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                code = brain.main(["--vault", str(root), "migrate-links", "--check"])
            self.assertEqual(code, 1)

    def test_dirty_planned_path_stale_mode_symlink_and_no_dirfd_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            source = root / "source.md"
            source.write_bytes(source.read_bytes() + b"late\n")
            with self.assertRaisesRegex(brain.LinkMigrationError, "dirty"):
                brain.apply_link_migration_plan(root, plan)
            subprocess.run(["git", "checkout", "--", "source.md"], cwd=root, check=True)
            source.write_bytes(source.read_bytes() + b"late\n")
            with mock.patch.object(brain, "dirty_migration_paths", return_value=[]):
                with self.assertRaisesRegex(brain.LinkMigrationError, "stale"):
                    brain.apply_link_migration_plan(root, plan)
            subprocess.run(["git", "checkout", "--", "source.md"], cwd=root, check=True)
            source.chmod(0o600 if plan["edits"][0]["mode"] != 0o600 else 0o644)
            with mock.patch.object(brain, "dirty_migration_paths", return_value=[]):
                with self.assertRaisesRegex(brain.LinkMigrationError, "mode"):
                    brain.apply_link_migration_plan(root, plan)
            source.chmod(plan["edits"][0]["mode"])
            source.unlink()
            source.symlink_to("target.md")
            with mock.patch.object(brain, "dirty_migration_paths", return_value=[]):
                with self.assertRaises((brain.LinkMigrationError, OSError)):
                    brain.apply_link_migration_plan(root, plan)
            source.unlink()
            subprocess.run(["git", "checkout", "--", "source.md"], cwd=root, check=True)
            with mock.patch.object(brain, "_migration_mutation_supported", return_value=False):
                with self.assertRaisesRegex(brain.LinkMigrationError, "preview/check only"):
                    brain.apply_link_migration_plan(root, plan)
            self.assertIn("[[target", source.read_text(encoding="utf-8"))

    def test_unrelated_dirty_path_does_not_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = fixture_files()
            files["unrelated.md"] = note("unchanged\n", "Unrelated")
            root = git_vault(Path(temporary), files)
            plan = brain.build_link_migration_plan(root)
            (root / "unrelated.md").write_text(note("owner edit\n", "Unrelated"), encoding="utf-8")
            brain.apply_link_migration_plan(root, plan)
            self.assertIn("owner edit", (root / "unrelated.md").read_text())

    def _two_source_vault(self, root: Path) -> tuple[Path, dict, dict[str, bytes]]:
        files = fixture_files()
        files["second.md"] = note("[[target|Second]]\n", "Second")
        git_vault(root, files)
        plan = brain.build_link_migration_plan(root)
        originals = {row["path"]: (root / row["path"]).read_bytes() for row in plan["edits"]}
        return root, plan, originals

    def test_second_install_failure_and_interrupt_restore_exact_tree(self):
        for failure in (OSError("injected write failure"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as temporary:
                root, plan, originals = self._two_source_vault(Path(temporary))
                original_install = brain._install_migration_at
                calls = 0

                def fail_second(parent, staged, name):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise failure
                    return original_install(parent, staged, name)

                with mock.patch.object(brain, "_install_migration_at", side_effect=fail_second):
                    with self.assertRaises(type(failure)):
                        brain.apply_link_migration_plan(root, plan)
                for relative, expected in originals.items():
                    self.assertEqual((root / relative).read_bytes(), expected)
                self.assertEqual(list(root.rglob(".*.migrate-*-*")), [])

    def test_preparation_failure_cleans_all_staged_files_and_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(
                Path(temporary),
                {
                    "a.md": note("[[target]]\n", "A"),
                    "b.md": note("[[target]]\n", "B"),
                    "target.md": note("target\n", "Target"),
                },
            )
            before = {path.name: path.read_bytes() for path in root.glob("*.md")}
            plan = brain.build_link_migration_plan(root)
            original_stage = brain._stage_migration_at

            def fail_second_source(parent, basename, data, mode, **kwargs):
                if basename == "b.md":
                    raise KeyboardInterrupt
                return original_stage(parent, basename, data, mode, **kwargs)

            with mock.patch.object(brain, "_stage_migration_at", side_effect=fail_second_source):
                with self.assertRaises(KeyboardInterrupt):
                    brain.apply_link_migration_plan(root, plan)
            self.assertEqual(
                {path.name: path.read_bytes() for path in root.glob("*.md")}, before
            )
            self.assertEqual(list(root.glob(".*.migrate-*-*")), [])
            self.assertFalse((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())

    def test_stage_name_is_durable_in_journal_before_stage_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            original_stage = brain._stage_migration_at
            saw_source_stage = False

            def inspect_order(parent, basename, data, mode, **kwargs):
                nonlocal saw_source_stage
                reserved = kwargs.get("reserved_name")
                if basename == "source.md":
                    payload = json.loads(
                        (root / brain.LINK_MIGRATION_JOURNAL_RELPATH)
                        .read_text(encoding="utf-8")
                        .splitlines()[-1]
                    )
                    self.assertEqual(payload["rows"][0]["new"], reserved)
                    saw_source_stage = True
                return original_stage(parent, basename, data, mode, **kwargs)

            with mock.patch.object(brain, "_stage_migration_at", side_effect=inspect_order):
                brain.apply_link_migration_plan(root, plan)
            self.assertTrue(saw_source_stage)

    def test_interrupt_after_stage_return_removes_owned_stage_before_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            original = (root / "source.md").read_bytes()
            original_stage = brain._stage_migration_at

            def interrupt_after_return(parent, basename, data, mode, **kwargs):
                staged = original_stage(parent, basename, data, mode, **kwargs)
                if basename == "source.md":
                    raise KeyboardInterrupt
                return staged

            with mock.patch.object(
                brain, "_stage_migration_at", side_effect=interrupt_after_return
            ):
                with self.assertRaises(KeyboardInterrupt):
                    brain.apply_link_migration_plan(root, plan)
            self.assertEqual((root / "source.md").read_bytes(), original)
            self.assertEqual(list(root.glob(".source.md.migrate-*-*")), [])
            self.assertFalse((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())

    def test_foreign_journal_replacement_is_never_overwritten_or_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            original = (root / "source.md").read_bytes()
            sentinel = b"foreign journal sentinel\n"
            sentinel_mode = 0o640
            original_journal_write = brain._write_migration_journal
            replaced = False

            def replace_before_update(parent, payload, *, create, guard=None):
                nonlocal replaced
                if not create and not replaced:
                    replacement = root / ".foreign-journal"
                    replacement.write_bytes(sentinel)
                    replacement.chmod(sentinel_mode)
                    os.replace(
                        replacement, root / brain.LINK_MIGRATION_JOURNAL_RELPATH
                    )
                    replaced = True
                return original_journal_write(
                    parent, payload, create=create, guard=guard
                )

            with mock.patch.object(
                brain,
                "_write_migration_journal",
                side_effect=replace_before_update,
            ):
                with self.assertRaisesRegex(
                    brain.LinkMigrationError, "foreign replacement preserved"
                ):
                    brain.apply_link_migration_plan(root, plan)
            journal = root / brain.LINK_MIGRATION_JOURNAL_RELPATH
            self.assertEqual(journal.read_bytes(), sentinel)
            self.assertEqual(stat.S_IMODE(journal.stat().st_mode), sentinel_mode)
            self.assertEqual((root / "source.md").read_bytes(), original)
            self.assertEqual(list(root.glob(".source.md.migrate-*-*")), [])

    def test_post_publication_failure_rolls_back_and_commit_race_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            original = (root / "source.md").read_bytes()
            original_install = brain._install_migration_at

            def publish_then_fail(parent, staged, name):
                original_install(parent, staged, name)
                raise OSError("injected post-publication fsync failure")

            with mock.patch.object(
                brain, "_install_migration_at", side_effect=publish_then_fail
            ):
                with self.assertRaisesRegex(OSError, "post-publication"):
                    brain.apply_link_migration_plan(root, plan)
            self.assertEqual((root / "source.md").read_bytes(), original)
            self.assertEqual(list(root.glob(".source.md.migrate-*-*")), [])
            self.assertFalse((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())

        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            original = (root / "source.md").read_bytes()
            foreign = b"concurrent writer after result verification\n"
            original_journal_write = brain._write_migration_journal

            def mutate_before_commit(parent, payload, *, create, guard=None):
                if not create and payload.get("committed"):
                    (root / "source.md").write_bytes(foreign)
                return original_journal_write(
                    parent, payload, create=create, guard=guard
                )

            with mock.patch.object(
                brain, "_write_migration_journal", side_effect=mutate_before_commit
            ):
                with self.assertRaisesRegex(brain.LinkMigrationError, "preserved"):
                    brain.apply_link_migration_plan(root, plan)
            self.assertEqual((root / "source.md").read_bytes(), foreign)
            backups = list(root.glob(".source.md.migrate-old-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            self.assertTrue((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())
            stages = list(root.glob(".source.md.migrate-new-*"))
            self.assertEqual(len(stages), 1)
            self.assertEqual(stages[0].read_bytes(), foreign)

    def test_mixed_line_endings_and_missing_final_newline_are_byte_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = (
                b'---\r\ntitle: "Source"\ntags:\r\n  - type/note\n'
                b'updated: 2026-08-11\r\n---\n\r\nbefore\xe2\x80\xa8[[target]]'
            )
            root = git_vault(
                Path(temporary),
                {"source.md": source, "target.md": note("target\n", "Target")},
            )
            plan = brain.build_link_migration_plan(root)
            brain.apply_link_migration_plan(root, plan)
            migrated = (root / "source.md").read_bytes()
            self.assertFalse(migrated.endswith((b"\n", b"\r")))
            self.assertEqual(migrated.count(b"\r\n"), source.count(b"\r\n"))
            self.assertEqual(migrated.count(b"\n"), source.count(b"\n"))
            self.assertIn("before\u2028[target](target.md)".encode("utf-8"), migrated)

    def test_concurrent_final_insertion_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            original = (root / "source.md").read_bytes()
            foreign = b"concurrent owner contents\n"

            def insert_foreign(parent, _staged, name):
                descriptor = os.open(
                    name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=parent
                )
                os.write(descriptor, foreign)
                os.close(descriptor)
                raise FileExistsError(name)

            with mock.patch.object(brain, "_install_migration_at", side_effect=insert_foreign):
                with self.assertRaisesRegex(brain.LinkMigrationError, "originals retained"):
                    brain.apply_link_migration_plan(root, plan)
            self.assertEqual((root / "source.md").read_bytes(), foreign)
            backups = list(root.glob(".source.md.migrate-old-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)

    def test_crash_recovery_rolls_back_after_quarantine_or_mid_install(self):
        for installed in (False, True):
            with self.subTest(installed=installed), tempfile.TemporaryDirectory() as temporary:
                root = git_vault(Path(temporary), fixture_files())
                plan = brain.build_link_migration_plan(root)
                source, _desired = self._simulate_crash_state(
                    root, plan, installed=installed, committed=False
                )
                self.assertTrue(brain.recover_link_migration(root))
                self.assertEqual((root / "source.md").read_bytes(), source)
                self.assertFalse((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())
                self.assertEqual(list(root.glob(".source.md.migrate-*-*")), [])

    def test_committed_recovery_finishes_commit_before_or_mid_cleanup(self):
        for remove_backup in (False, True):
            with self.subTest(remove_backup=remove_backup), tempfile.TemporaryDirectory() as temporary:
                root = git_vault(Path(temporary), fixture_files())
                plan = brain.build_link_migration_plan(root)
                _source, desired = self._simulate_crash_state(
                    root,
                    plan,
                    installed=True,
                    committed=True,
                    remove_backup=remove_backup,
                )
                self.assertTrue(brain.recover_link_migration(root))
                self.assertEqual((root / "source.md").read_bytes(), desired)
                self.assertFalse((root / brain.LINK_MIGRATION_JOURNAL_RELPATH).exists())
                self.assertEqual(list(root.glob(".source.md.migrate-*-*")), [])

    def test_journal_lock_create_race_has_stable_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(Path(temporary), fixture_files())
            plan = brain.build_link_migration_plan(root)
            root_parent, _unused = brain._open_migration_parent(root, "journal-placeholder")
            payload = brain._journal_payload(plan, [])
            guard = brain._write_migration_journal(
                root_parent, payload, create=True
            )
            with self.assertRaisesRegex(brain.LinkMigrationError, "another link migration is active"):
                brain._write_migration_journal(root_parent, payload, create=True)
            brain._remove_migration_journal(root_parent, guard)
            brain._close_migration_journal_guard(guard)
            os.close(root_parent)

    def test_unsupported_block_and_overlapping_or_stale_plans_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(
                Path(temporary),
                {
                    "source.md": note("[[target#^block]]\n", "Source"),
                    "target.md": note("target\n", "Target"),
                },
            )
            blocked = brain.build_link_migration_plan(root)
            self.assertEqual(blocked["blockers"][0]["rule"], "unsupported-block-reference")
            with self.assertRaisesRegex(brain.LinkMigrationError, "blockers"):
                brain.apply_link_migration_plan(root, blocked)
        with tempfile.TemporaryDirectory() as temporary:
            root = git_vault(
                Path(temporary),
                {
                    "source.md": note("[outer [[target]]](other.md)\n", "Source"),
                    "target.md": note("target\n", "Target"),
                    "other.md": note("other\n", "Other"),
                },
            )
            blocked = brain.build_link_migration_plan(root)
            self.assertEqual(blocked["edits"], [])
            self.assertEqual(
                [finding["rule"] for finding in blocked["blockers"]],
                ["overlapping-edits"],
            )
        with self.assertRaisesRegex(brain.LinkMigrationError, "overlapping"):
            brain._desired_migration_bytes(
                b"[[a]] [[b]]",
                {
                    "resultSha256": "irrelevant",
                    "replacements": [
                        {"range": {"start": 0, "end": 5}, "before": "[[a]]", "after": "[a](a.md)"},
                        {"range": {"start": 4, "end": 11}, "before": "] [[b]]", "after": "[b](b.md)"},
                    ],
                },
            )


class CorpusPerformanceTests(unittest.TestCase):
    def test_synthetic_workload_at_or_above_current_corpus(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {"target.md": note("# Heading\n", "Target")}
            for index in range(140):
                files[f"notes/source-{index}.md"] = note(
                    " ".join("[[target]]" for _ in range(6)) + "\n",
                    f"Source {index}",
                )
            write_files(root, files)
            started = time.monotonic()
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            elapsed = time.monotonic() - started
            self.assertGreaterEqual(len(notes), 140)
            self.assertGreaterEqual(index["linkCounts"]["legacy"], 767)
            self.assertLess(elapsed, 5.0)

    def test_live_corpus_placeholder_and_resolution_regression(self):
        notes, assets = brain.walk_corpus(ROOT)
        index = brain.build_index(ROOT, notes, assets)
        self.assertEqual(index["linkCounts"]["placeholder"], 20)
        unresolved_paths = [
            (path, link["raw"])
            for path, record in index["notes"].items()
            for link in record["links"]
            if not link["placeholder"] and link["resolved"] is None
        ]
        self.assertEqual(unresolved_paths, [])


if __name__ == "__main__":
    unittest.main()
