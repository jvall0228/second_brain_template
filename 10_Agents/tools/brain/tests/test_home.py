"""Generated Home correctness, privacy, portability, and ownership tests."""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain


UNCONFIGURED = {"slug": None, "source": "none", "state": "unconfigured"}


def note(title: str, body: str, tags: tuple[str, ...] = ("type/note",), *, updated: str = "2026-08-11") -> str:
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n"
        + "".join(f"  - {tag}\n" for tag in tags)
        + f"updated: {updated}\n"
        "---\n\n"
        f"# {title}\n\n{body}\n"
    )


class HomeVault:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="home-")
        self.root = Path(self.temp.name)
        self.tracked: set[str] = set()
        self.write(
            brain.ADOPT_EXAMPLES_RELPATH,
            json.dumps({"schema_version": 1, "delete": ["04_Projects/example-project/"]}),
            tracked=True,
        )
        for rel, title in (
            ("00_Meta/INDEX.md", "Index"),
            ("00_Meta/STATUS.md", "Status"),
            ("00_Meta/CHANGELOG.md", "Changelog"),
            ("01_Profile/NOW.md", "Now"),
            ("02_Inbox/README.md", "Inbox"),
            ("04_Projects/README.md", "Projects"),
            ("05_Areas/README.md", "Areas"),
            ("10_Agents/skills/README.md", "Skills"),
            ("10_Agents/environments/README.md", "Environments"),
        ):
            body = "## Current Focus\n\n- Keep the system useful" if rel.endswith("NOW.md") else "Safe navigation."
            self.write(rel, note(title, body, ("type/meta",)), tracked=True)

    def cleanup(self):
        self.temp.cleanup()

    def write(self, rel: str, content: str | bytes, *, tracked: bool = False) -> Path:
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content if isinstance(content, bytes) else content.encode())
        if tracked:
            self.tracked.add(rel)
        return target

    def build(self, **kwargs):
        with mock.patch.object(brain, "git_tracked", return_value=set(self.tracked)):
            return brain.build_home(
                self.root,
                today_d=kwargs.pop("today_d", date(2026, 8, 11)),
                selection=kwargs.pop("selection", UNCONFIGURED),
                **kwargs,
            )

    def write_index(self) -> None:
        notes, assets = brain.walk_corpus(self.root, selected_environment=None)
        notes = [rel for rel in notes if rel in self.tracked]
        assets = [rel for rel in assets if rel in self.tracked]
        rendered = brain.serialize(
            brain.reduce_restricted(brain.build_index(self.root, notes, assets))
        )
        self.write(brain.INDEX_RELPATH, rendered, tracked=True)


class HomeCollectorTests(unittest.TestCase):
    def setUp(self):
        self.vault = HomeVault()

    def tearDown(self):
        self.vault.cleanup()

    def test_empty_state_is_deterministic_and_markdown_only(self):
        first = self.vault.build()
        second = self.vault.build()
        self.assertEqual(first, second)
        rendered = brain.render_home(first)
        self.assertEqual(rendered, brain.render_home(second))
        self.assertIn(b"## Top actions", rendered)
        self.assertNotIn(b"[" * 2, rendered)

    def test_due_overdue_active_inbox_and_health_sections(self):
        self.vault.write(
            "04_Projects/real/PROJECT.md",
            note(
                "Real",
                "## Outcome\n\nShip it.\n\n## Completion Criteria\n\n- Verified.\n\n"
                "- [ ] Overdue task 📅 2026-08-10\n- [ ] Due task 📅 2026-08-12",
                ("type/project", "status/active", "project/real", "area/health"),
                updated="2026-01-01",
            ).replace("updated: 2026-01-01", "target: 2026-08-20\ntarget_status: estimated\nupdated: 2026-01-01"),
            tracked=True,
        )
        self.vault.write("05_Areas/health/AREA.md", note("Health", "Maintain.", ("type/area", "status/active", "area/health")), tracked=True)
        self.vault.write("02_Inbox/2026-07-01-old.md", note("Old", "Capture."), tracked=True)
        payload = self.vault.build()
        self.assertEqual([row["text"] for row in payload["tasks"]["overdue"]], ["Overdue task"])
        self.assertEqual([row["text"] for row in payload["tasks"]["due"]], ["Due task"])
        self.assertEqual(payload["active"]["projects"][0]["path"], "04_Projects/real/PROJECT.md")
        self.assertEqual(payload["active"]["projects"][0]["targetStatus"], "estimated")
        self.assertEqual(payload["active"]["areas"][0]["path"], "05_Areas/health/AREA.md")
        self.assertEqual(payload["inbox"]["count"], 1)
        self.assertEqual(payload["health"]["staleActiveCount"], 1)

    def test_malformed_active_project_renders_with_explicit_missing_target(self):
        self.vault.write(
            "04_Projects/incomplete/PROJECT.md",
            note(
                "Incomplete",
                "## Outcome\n\nShip it.\n\n## Completion Criteria\n\n- Verified.",
                ("type/project", "status/active", "project/incomplete", "area/health"),
            ),
            tracked=True,
        )
        self.vault.write(
            "05_Areas/health/AREA.md",
            note("Health", "Maintain.", ("type/area", "status/active", "area/health")),
            tracked=True,
        )

        payload = self.vault.build()
        rendered = brain.render_home(payload).decode()

        self.assertIn("target missing (unknown)", rendered)

    def test_only_explicitly_inactive_project_tasks_are_suppressed(self):
        self.vault.write(
            "05_Areas/work/AREA.md",
            note("Work", "Maintain.", ("type/area", "status/active", "area/work")),
            tracked=True,
        )
        self.vault.write(
            "04_Projects/malformed/PROJECT.md",
            note(
                "Malformed",
                "- [ ] Visible malformed Project task 📅 2026-08-10",
                ("type/project", "project/malformed", "area/work"),
            ),
            tracked=True,
        )
        self.vault.write(
            "04_Projects/paused/PROJECT.md",
            note(
                "Paused",
                "- [ ] Hidden inactive Project task 📅 2026-08-10",
                (
                    "type/project",
                    "status/deprioritized",
                    "project/paused",
                    "area/work",
                ),
            ),
            tracked=True,
        )

        payload = self.vault.build()

        self.assertIn(
            "Visible malformed Project task",
            [row["text"] for row in payload["tasks"]["overdue"]],
        )
        self.assertNotIn("Hidden inactive Project task", json.dumps(payload))

    def test_existing_current_daily_and_weekly_reviews_are_live_links(self):
        daily = "03_Journal/periodic/daily/2026-08-11.md"
        weekly = "03_Journal/periodic/weekly/2026-W33-review.md"
        self.vault.write(daily, note("Daily", "Recorded."), tracked=True)
        self.vault.write(weekly, note("Weekly", "Reviewed."), tracked=True)
        payload = self.vault.build()
        present = [row for row in payload["reviews"] if row["state"] == "present"]
        self.assertEqual([row["sources"][0]["path"] for row in present], [daily, weekly])
        rendered = brain.render_home(payload).decode()
        self.assertIn("../03_Journal/periodic/daily/2026-08-11.md", rendered)
        self.assertIn("../03_Journal/periodic/weekly/2026-W33-review.md", rendered)
        self.assertNotIn("No periodic review is due", rendered)

    def test_restricted_target_untracked_seed_and_environment_bodies_never_contribute(self):
        self.vault.write("06_Resources/private.md", note("PRIVATE-TITLE", "PRIVATE-BODY", ("type/reference", "restricted/private")), tracked=True)
        self.vault.write("04_Projects/linked.md", note("LINKED-SECRET", "[private](../06_Resources/private.md)\n- [ ] LINKED-TASK 📅 2026-08-10"), tracked=True)
        self.vault.write("04_Projects/example-project/fake.md", note("SEED-SECRET", "- [ ] SEED-TASK 📅 2026-08-10"), tracked=True)
        self.vault.write("02_Inbox/untracked.md", note("UNTRACKED-SECRET", "- [ ] UNTRACKED-TASK 📅 2026-08-10"))
        self.vault.write("10_Agents/environments/alpha/private.md", note("ENV-BODY-SECRET", "- [ ] ENV-TASK 📅 2026-08-10"), tracked=True)
        payload = self.vault.build()
        combined = json.dumps(payload) + brain.render_home(payload).decode()
        for secret in ("PRIVATE-TITLE", "LINKED-SECRET", "SEED-SECRET", "UNTRACKED-SECRET", "ENV-BODY-SECRET"):
            self.assertNotIn(secret, combined)

    def test_tracked_symlink_cannot_import_external_body_or_path_signal(self):
        outside_dir = tempfile.TemporaryDirectory(prefix="home-outside-")
        self.addCleanup(outside_dir.cleanup)
        outside = Path(outside_dir.name) / "secret.md"
        outside.write_text(note("EXTERNAL-HOME-SECRET", "- [ ] SECRET 📅 2026-08-10"))
        linked = self.vault.root / "04_Projects/external.md"
        linked.parent.mkdir(parents=True, exist_ok=True)
        linked.symlink_to(outside)
        self.vault.tracked.add("04_Projects/external.md")
        payload = self.vault.build()
        combined = json.dumps(payload) + brain.render_home(payload).decode()
        self.assertNotIn("EXTERNAL-HOME-SECRET", combined)
        self.assertNotIn("external.md", combined)

    def test_home_privacy_classification_and_extraction_share_snapshot(self):
        rel = "04_Projects/race.md"
        self.vault.write(rel, note("Public", "- [ ] PUBLIC-SNAPSHOT 📅 2026-08-10"), tracked=True)
        original = brain.build_aymt

        def restrict_after_aymt(*args, **kwargs):
            payload = original(*args, **kwargs)
            self.vault.write(rel, note("PRIVATE-RACE", "- [ ] PRIVATE-RACE-SECRET 📅 2026-08-10", ("type/project", "restricted/private")), tracked=True)
            return payload

        with mock.patch.object(brain, "build_aymt", side_effect=restrict_after_aymt):
            with self.assertRaises(brain.HomeError):
                self.vault.build()

    def test_aymt_is_consumed_as_structured_data_not_generated_markdown(self):
        self.vault.write(brain.AYMT_RELPATH, "AYMT-MARKDOWN-SECRET", tracked=True)
        with mock.patch.object(brain, "git_tracked", return_value=set(self.vault.tracked)):
            base = brain.build_aymt(
                self.vault.root, today_d=date(2026, 8, 11), selection=UNCONFIGURED
            )
        candidate = {
            "caveat": "safe",
            "id": "a" * 64,
            "kind": "test",
            "nextStep": "Use the structured next step",
            "outcome": "STRUCTURED-ACTION",
            "score": 99,
            "section": "do-next",
            "signals": {"confidence": 4, "dependency": 0, "effort": 1, "leverage": 4, "staleness": 0, "urgency": 4},
            "sources": [{"kind": "vault", "label": "Now", "path": "01_Profile/NOW.md"}],
            "whyNow": "Structured signal",
        }
        structured = {**base, "candidates": [candidate], "inputDigest": "b" * 64}
        with mock.patch.object(brain, "build_aymt", return_value=structured):
            payload = self.vault.build()
        combined = json.dumps(payload) + brain.render_home(payload).decode()
        self.assertIn("STRUCTURED-ACTION", combined)
        self.assertNotIn("AYMT-MARKDOWN-SECRET", combined)

    def test_selected_environment_uses_metadata_only(self):
        manifest_rel = "10_Agents/environments/alpha/environment.json"
        manifest = {
            "capabilities": {}, "class": "laptop", "fingerprints": [],
            "freshness": {"checkedAt": "2026-08-01", "expiresAt": "2026-08-20"},
            "maintenance": {"inventory": "orientation-inventory.md", "ownerReviewRequired": True},
            "schemaVersion": 1, "slug": "alpha", "surfaces": ["codex"],
        }
        self.vault.write(manifest_rel, json.dumps(manifest), tracked=True)
        selection = {"slug": "alpha", "source": "config", "state": "selected"}
        payload = self.vault.build(selection=selection)
        self.assertEqual(payload["environment"]["slug"], "alpha")
        self.assertEqual(set(payload["environment"]), {"freshness", "slug", "source", "state"})

    def test_git_discovery_failure_is_redacted_and_cannot_expand_to_untracked(self):
        self.vault.write("02_Inbox/secret.md", note("UNTRACKED-FALLBACK-SECRET", "- [ ] secret"))
        with mock.patch.object(brain, "git_tracked", return_value=None):
            with self.assertRaises(brain.HomeError):
                brain.build_home(self.vault.root, today_d=date(2026, 8, 11), selection=UNCONFIGURED)

    def test_untracked_seed_manifest_fails_closed_for_home_and_aymt(self):
        self.vault.tracked.remove(brain.ADOPT_EXAMPLES_RELPATH)
        self.vault.write(
            brain.ADOPT_EXAMPLES_RELPATH,
            json.dumps({"schema_version": 1, "delete": []}),
        )
        with mock.patch.object(brain, "git_tracked", return_value=set(self.vault.tracked)):
            with self.assertRaises(brain.AymtError):
                brain.build_aymt(
                    self.vault.root,
                    today_d=date(2026, 8, 11),
                    selection=UNCONFIGURED,
                )
            with self.assertRaises(brain.HomeError):
                brain.build_home(
                    self.vault.root,
                    today_d=date(2026, 8, 11),
                    selection=UNCONFIGURED,
                )
            home_args = SimpleNamespace(
                check=False,
                github_input=None,
                home_selection=UNCONFIGURED,
                json=True,
                write=False,
            )
            aymt_args = SimpleNamespace(
                aymt_selection=UNCONFIGURED,
                check=False,
                github_input=None,
                json=True,
                write=False,
            )
            outputs = []
            for command, args in ((brain.cmd_home, home_args), (brain.cmd_aymt, aymt_args)):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(command(self.vault.root, args), 1)
                outputs.append(json.loads(stream.getvalue()))
            self.assertEqual(outputs[0], {"error": "Home generation failed safely"})
            self.assertEqual(outputs[1], {"error": "AYMT generation failed safely"})

    def test_tracked_symlink_seed_manifest_is_never_authority(self):
        manifest = self.vault.root / brain.ADOPT_EXAMPLES_RELPATH
        manifest.unlink()
        outside = self.vault.write(
            "foreign-seed.json",
            json.dumps({"schema_version": 1, "delete": []}),
        )
        manifest.symlink_to(outside)
        with mock.patch.object(brain, "git_tracked", return_value=set(self.vault.tracked)):
            with self.assertRaises(brain.AymtError):
                brain.build_aymt(
                    self.vault.root,
                    today_d=date(2026, 8, 11),
                    selection=UNCONFIGURED,
                )
            with self.assertRaises(brain.HomeError):
                brain.build_home(
                    self.vault.root,
                    today_d=date(2026, 8, 11),
                    selection=UNCONFIGURED,
                )

    def test_safe_validation_index_and_near_expiry_are_bounded_and_redacted(self):
        tomorrow = note("Tomorrow", "Review this note.").replace(
            "updated: 2026-08-11\n", "updated: 2026-08-11\nexpires: 2026-08-12\n"
        )
        self.vault.write("06_Resources/tomorrow.md", tomorrow, tracked=True)
        self.vault.write("06_Resources/malformed.md", "MALFORMED-PRIVATE-BODY\n", tracked=True)
        self.vault.write(
            "04_Projects/bad-task.md",
            note("Bad task", "- [ ] DO-NOT-LEAK-TASK 📅 not-a-date"),
            tracked=True,
        )
        payload = self.vault.build()
        health = payload["health"]
        self.assertGreaterEqual(health["validation"]["errors"], 1)
        self.assertGreaterEqual(health["validation"]["warnings"], 1)
        self.assertLessEqual(len(health["validation"]["rules"]), 12)
        self.assertEqual(health["index"], {"fresh": False, "scope": "tracked-safe"})
        self.assertEqual(health["nearExpiryCount"], 1)
        self.assertEqual(health["nearExpiry"][0]["path"], "06_Resources/tomorrow.md")
        combined = json.dumps(payload) + brain.render_home(payload).decode()
        self.assertIn("../06_Resources/tomorrow.md", combined)
        self.assertNotIn("MALFORMED-PRIVATE-BODY", combined)
        self.assertNotIn("DO-NOT-LEAK-TASK", combined)

    def test_public_to_restricted_transition_marks_index_stale_without_disclosure(self):
        rel = "06_Resources/privacy-transition.md"
        self.vault.write(
            rel,
            note("Was Public", "Previously public content."),
            tracked=True,
        )
        self.vault.write_index()
        self.assertTrue(self.vault.build()["health"]["index"]["fresh"])

        self.vault.write(
            rel,
            note(
                "Now Private",
                "PRIVATE-TRANSITION-BODY",
                ("type/reference", "restricted/private"),
            ),
            tracked=True,
        )
        payload = self.vault.build()
        self.assertEqual(
            payload["health"]["index"],
            {"fresh": False, "scope": "tracked-safe"},
        )
        combined = json.dumps(payload) + brain.render_home(payload).decode()
        for sensitive in (
            "Was Public",
            "Now Private",
            "PRIVATE-TRANSITION-BODY",
            rel,
        ):
            self.assertNotIn(sensitive, combined)

    def test_untracked_config_cannot_change_health_or_digest(self):
        self.vault.write(
            "04_Projects/stale.md",
            note("Stale", "Work.", ("type/project", "status/active"), updated="2026-07-01"),
            tracked=True,
        )
        before = self.vault.build()
        self.vault.write(brain.CONFIG_RELPATH, "report:\n  stale_days: 1\n")
        after = self.vault.build()
        self.assertEqual(after, before)

    def test_late_committed_index_mutation_refuses_without_claiming_fresh(self):
        self.vault.write_index()
        target = self.vault.root / brain.INDEX_RELPATH
        original = brain._home_safe_index_fresh

        def mutate_after_comparison(*args, **kwargs):
            result = original(*args, **kwargs)
            target.write_bytes(target.read_bytes() + b" ")
            return result

        args = SimpleNamespace(
            check=False,
            github_input=None,
            home_selection=UNCONFIGURED,
            json=True,
            write=False,
        )
        stream = io.StringIO()
        with (
            mock.patch.object(
                brain, "git_tracked", side_effect=lambda _root: set(self.vault.tracked)
            ),
            mock.patch.object(
                brain, "_home_safe_index_fresh", side_effect=mutate_after_comparison
            ),
            contextlib.redirect_stdout(stream),
        ):
            self.assertEqual(brain.cmd_home(self.vault.root, args), 1)
        self.assertEqual(
            json.loads(stream.getvalue()),
            {"error": "Home generation failed safely"},
        )
        self.assertNotIn("fresh", stream.getvalue())

    def test_late_seed_inventory_mutation_refuses_seeded_output(self):
        seeded = "04_Projects/seeded-project.md"
        manifest = self.vault.root / brain.ADOPT_EXAMPLES_RELPATH
        manifest.write_text(json.dumps({"schema_version": 1, "delete": []}))
        self.vault.write(
            seeded,
            note(
                "SEEDED-LATE-SECRET",
                "- [ ] SEEDED-LATE-TASK 📅 2026-08-10",
                ("type/project", "status/active"),
            ),
            tracked=True,
        )
        original = brain.build_aymt

        def exclude_after_aymt(*args, **kwargs):
            payload = original(*args, **kwargs)
            manifest.write_text(
                json.dumps({"schema_version": 1, "delete": [seeded]})
            )
            return payload

        args = SimpleNamespace(
            check=False,
            github_input=None,
            home_selection=UNCONFIGURED,
            json=True,
            write=False,
        )
        stream = io.StringIO()
        with (
            mock.patch.object(
                brain, "git_tracked", side_effect=lambda _root: set(self.vault.tracked)
            ),
            mock.patch.object(brain, "build_aymt", side_effect=exclude_after_aymt),
            contextlib.redirect_stdout(stream),
        ):
            self.assertEqual(brain.cmd_home(self.vault.root, args), 1)
        output = stream.getvalue()
        self.assertEqual(
            json.loads(output), {"error": "Home generation failed safely"}
        )
        for secret in (seeded, "SEEDED-LATE-SECRET", "SEEDED-LATE-TASK"):
            self.assertNotIn(secret, output)

    def test_tracked_path_set_change_during_build_refuses(self):
        original = brain.build_aymt

        def add_tracked_path_after_aymt(*args, **kwargs):
            payload = original(*args, **kwargs)
            self.vault.write(
                "06_Resources/LATE-TRACKED-SECRET.md",
                note("LATE-TRACKED-SECRET", "Do not disclose."),
                tracked=True,
            )
            return payload

        args = SimpleNamespace(
            check=False,
            github_input=None,
            home_selection=UNCONFIGURED,
            json=True,
            write=False,
        )
        stream = io.StringIO()
        with (
            mock.patch.object(
                brain, "git_tracked", side_effect=lambda _root: set(self.vault.tracked)
            ),
            mock.patch.object(
                brain, "build_aymt", side_effect=add_tracked_path_after_aymt
            ),
            contextlib.redirect_stdout(stream),
        ):
            self.assertEqual(brain.cmd_home(self.vault.root, args), 1)
        output = stream.getvalue()
        self.assertEqual(
            json.loads(output), {"error": "Home generation failed safely"}
        )
        self.assertNotIn("LATE-TRACKED-SECRET", output)


class HomeWriterTests(unittest.TestCase):
    def setUp(self):
        self.vault = HomeVault()
        self.desired = brain.render_home(self.vault.build())
        (self.vault.root / "00_Meta").mkdir(exist_ok=True)

    def tearDown(self):
        self.vault.cleanup()

    def test_exact_owned_write_and_identical_noop_do_not_widen_agent_authority(self):
        self.assertEqual(brain.write_home(self.vault.root, self.desired), "written")
        self.assertEqual(brain.write_home(self.vault.root, self.desired), "unchanged")
        target = self.vault.root / brain.HOME_RELPATH
        self.assertEqual(target.read_bytes(), self.desired)
        self.assertFalse(brain.agent_write_allowed(brain.HOME_RELPATH, {}))
        with self.assertRaises(brain.AymtError):
            brain._write_generated_exact(
                self.vault.root,
                self.desired,
                relpath="01_Profile/NOW.md",
                marker=brain.HOME_MARKER,
            )

    def test_foreign_and_symlinked_home_are_preserved(self):
        target = self.vault.write(brain.HOME_RELPATH, b"FOREIGN")
        with self.assertRaises(brain.HomeError):
            brain.write_home(self.vault.root, self.desired)
        self.assertEqual(target.read_bytes(), b"FOREIGN")
        target.unlink()
        outside = self.vault.write("outside.md", b"OUTSIDE")
        target.symlink_to(outside)
        with self.assertRaises(brain.HomeError):
            brain.write_home(self.vault.root, self.desired)
        self.assertTrue(target.is_symlink())
        self.assertEqual(outside.read_bytes(), b"OUTSIDE")

    def test_interrupt_after_publication_restores_prior_and_cleans_stage(self):
        target = self.vault.root / brain.HOME_RELPATH
        self.assertEqual(brain.write_home(self.vault.root, self.desired), "written")
        prior = target.read_bytes()
        updated = self.desired.replace(b"# Home", b"# Home updated", 1)
        original = brain._install_migration_at

        def install_then_interrupt(*args, **kwargs):
            original(*args, **kwargs)
            raise KeyboardInterrupt

        with mock.patch.object(brain, "_install_migration_at", side_effect=install_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                brain.write_home(self.vault.root, updated)
        self.assertEqual(target.read_bytes(), prior)
        self.assertFalse(list(target.parent.glob(".*.migrate-*")))

    def test_concurrent_foreign_final_is_preserved_with_prior_recovery(self):
        target = self.vault.root / brain.HOME_RELPATH
        self.assertEqual(brain.write_home(self.vault.root, self.desired), "written")
        prior = target.read_bytes()
        updated = self.desired.replace(b"# Home", b"# Home updated", 1)
        original = brain._install_migration_at

        def collide(parent, staged, name):
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent)
            try:
                os.write(descriptor, b"FOREIGN-RACE")
            finally:
                os.close(descriptor)
            return original(parent, staged, name)

        with mock.patch.object(brain, "_install_migration_at", side_effect=collide):
            with self.assertRaises(brain.HomeError):
                brain.write_home(self.vault.root, updated)
        self.assertEqual(target.read_bytes(), b"FOREIGN-RACE")
        backups = list(target.parent.glob(".*.migrate-old-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), prior)

    def test_portable_check_is_zero_write_when_mutation_is_unsupported(self):
        target = self.vault.root / brain.HOME_RELPATH
        # `cmd_home` evaluates the actual current date; build matching bytes so
        # this portability contract stays deterministic across midnight.
        current = brain.render_home(self.vault.build(today_d=date.today()))
        target.write_bytes(current)
        os.chmod(target, 0o644)
        before = {p.name: p.read_bytes() for p in target.parent.iterdir() if p.is_file()}
        args = SimpleNamespace(check=True, write=False, json=True, github_input=None, home_selection=UNCONFIGURED)
        with mock.patch.object(brain, "git_tracked", return_value=set(self.vault.tracked)), mock.patch.object(brain, "_migration_mutation_supported", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()):
                result = brain.cmd_home(self.vault.root, args)
        after = {p.name: p.read_bytes() for p in target.parent.iterdir() if p.is_file()}
        self.assertEqual(result, 0)
        self.assertEqual(after, before)

    def test_home_write_never_changes_static_index(self):
        index = self.vault.root / "00_Meta/INDEX.md"
        before = index.read_bytes()
        brain.write_home(self.vault.root, self.desired)
        self.assertEqual(index.read_bytes(), before)


class HomeRepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[4]

    def test_editor_startup_surfaces_open_home_without_refreshing(self):
        obsidian = json.loads((self.root / ".obsidian/app.json").read_text())
        self.assertEqual(obsidian["openBehavior"], "file:00_Meta/HOME.md")
        tasks = (self.root / ".vscode/tasks.json").read_text()
        self.assertIn('"label": "Homepage: Open Home"', tasks)
        self.assertIn("code -r 00_Meta/HOME.md", tasks)
        self.assertNotIn("brain\" home --write", tasks)

    def test_exact_case_and_generic_authority_contract(self):
        self.assertTrue(brain.valid_note_filename(brain.HOME_RELPATH))
        self.assertFalse(brain.valid_note_filename("00_Meta/home.md"))
        self.assertNotIn(brain.HOME_RELPATH, brain.AGENT_WRITE_DEFAULT_FILES)
        self.assertFalse(brain.agent_write_allowed(brain.HOME_RELPATH, {}))

    def test_skill_inventory_and_adapters_include_refresh_home(self):
        skills = sorted((self.root / "10_Agents/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 24)
        self.assertTrue((self.root / ".agents/skills/refresh-home/SKILL.md").is_file())
        self.assertTrue((self.root / ".claude/skills/refresh-home/SKILL.md").is_file())

    def test_generated_home_is_not_hook_or_merge_driver_managed(self):
        attributes = (self.root / ".gitattributes").read_text()
        hook = (self.root / ".githooks/pre-commit").read_text()
        self.assertNotIn("00_Meta/HOME.md", attributes)
        self.assertNotIn("brain home", hook)

    def test_live_tracked_safe_index_and_validation_signals_are_current(self):
        payload = brain.build_home(
            self.root,
            today_d=date(2026, 8, 11),
            selection=UNCONFIGURED,
        )
        self.assertTrue(payload["health"]["index"]["fresh"])
        self.assertEqual(payload["health"]["validation"]["errors"], 0)


if __name__ == "__main__":
    unittest.main()
