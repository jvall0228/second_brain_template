"""Tests for daily_note.py (VS Code daily-note task, PRD §6.5), including
the spec-§17.5 task carry-over into the new note's Backlog section.

Run via the tools runner:
    python3 10_Agents/tools/run_tests.py
"""

import contextlib
import datetime
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import daily_note  # noqa: E402

TEMPLATE = (
    daily_note.ROOT / "09_Templates" / "template-daily-log.md"
).read_text(encoding="utf-8")


def make_root(tmp: str) -> Path:
    root = Path(tmp)
    (root / "09_Templates").mkdir()
    (root / "09_Templates" / "template-daily-log.md").write_text(TEMPLATE, encoding="utf-8")
    (root / "03_Journal" / "periodic" / "daily").mkdir(parents=True)
    return root


class RenderTests(unittest.TestCase):
    def test_all_placeholders_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            content = daily_note.render_note(root, datetime.date(2026, 8, 11))
        self.assertNotIn("{{", content)
        self.assertIn('title: "2026-08-11"', content)
        self.assertIn("# 2026-08-11", content)

    def test_missing_related_notes_degrade_to_plain_text(self):
        # Unresolved links are brain-validate errors, so absent notes must
        # not be linked.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            content = daily_note.render_note(root, datetime.date(2026, 8, 11))
        self.assertIn("Weekly review: not yet created", content)
        self.assertIn("Yesterday: none", content)

    def test_existing_related_notes_are_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            weekly_dir = root / "03_Journal" / "periodic" / "weekly"
            weekly_dir.mkdir(parents=True)
            (weekly_dir / "2026-W33-review.md").write_text("w\n", encoding="utf-8")
            daily = root / "03_Journal" / "periodic" / "daily"
            (daily / "2026-08-10.md").write_text("y\n", encoding="utf-8")
            content = daily_note.render_note(root, datetime.date(2026, 8, 11))
        self.assertIn("[2026-W33 review](../weekly/2026-W33-review.md)", content)
        self.assertIn("[2026-08-10](2026-08-10.md)", content)

    def test_iso_week_year_boundary(self):
        # 2027-01-01 falls in ISO week 2026-W53 — the weekly path must use the
        # ISO year, not the calendar year.
        self.assertEqual(datetime.date(2027, 1, 1).isocalendar()[:2], (2026, 53))
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            weekly_dir = root / "03_Journal" / "periodic" / "weekly"
            weekly_dir.mkdir(parents=True)
            (weekly_dir / "2026-W53-review.md").write_text("w\n", encoding="utf-8")
            content = daily_note.render_note(root, datetime.date(2027, 1, 1))
        self.assertIn("[2026-W53 review](../weekly/2026-W53-review.md)", content)


class EnsureNoteTests(unittest.TestCase):
    def test_untouched_shipped_template_produces_no_tasks_over_three_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            contents = []
            for offset in range(3):
                day = datetime.date(2026, 8, 11) + datetime.timedelta(days=offset)
                target, created = daily_note.ensure_note(root, day)
                self.assertTrue(created)
                contents.append(target.read_text(encoding="utf-8"))
            notes, assets = daily_note.brain.walk_corpus(root)
            index = daily_note.brain.build_index(root, notes, assets)
            task_counts = [
                len(rec["tasks"]) for rel, rec in sorted(index["notes"].items())
                if rel.startswith(daily_note.DAILY_DIR + "/")
            ]
        self.assertEqual(task_counts, [0, 0, 0])
        self.assertTrue(all("{{" not in content for content in contents))
        self.assertTrue(all("privacy-sources:" not in content for content in contents))

    def test_creates_note_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            target, created = daily_note.ensure_note(root, datetime.date(2026, 8, 11))
            self.assertTrue(created)
            self.assertEqual(target.name, "2026-08-11.md")
            self.assertTrue(target.exists())

    def test_existing_note_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            existing = root / "03_Journal" / "periodic" / "daily" / "2026-08-11.md"
            existing.write_text("owner edits\n", encoding="utf-8")
            target, created = daily_note.ensure_note(root, datetime.date(2026, 8, 11))
            self.assertFalse(created)
            self.assertEqual(target.read_text(encoding="utf-8"), "owner edits\n")

    def test_creates_missing_daily_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            (root / "03_Journal" / "periodic" / "daily").rmdir()
            _, created = daily_note.ensure_note(root, datetime.date(2026, 8, 11))
            self.assertTrue(created)

    def test_main_uses_configured_vault_date_across_utc_midnight(self):
        class HostDate(datetime.date):
            @classmethod
            def today(cls):
                return cls(2026, 8, 12)

        class FrozenDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 8, 12, 1, tzinfo=datetime.timezone.utc).astimezone(tz)

        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            (root / "00_Meta").mkdir()
            (root / "00_Meta" / "config.yaml").write_text(
                "timezone: America/New_York\n", encoding="utf-8"
            )
            with (
                mock.patch.object(daily_note, "ROOT", root),
                mock.patch.object(daily_note.datetime, "date", HostDate),
                mock.patch.object(daily_note.brain, "datetime", FrozenDatetime),
                mock.patch.object(daily_note.shutil, "which", return_value=None),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(daily_note.main(), 0)
            self.assertTrue((root / daily_note.DAILY_DIR / "2026-08-11.md").exists())
            self.assertFalse((root / daily_note.DAILY_DIR / "2026-08-12.md").exists())


YESTERDAY_NOTE = """---
title: "2026-08-10"
tags:
  - type/journal
updated: 2026-08-10
---

# 2026-08-10

- [ ] carry me 📅 2026-08-15
- [x] already done
  - [ ] nested open child
```
- [ ] inside a code fence — never carries
```
`- [ ] inside a code span — never carries`
"""

TODAY = datetime.date(2026, 8, 11)


def write_yesterday(root: Path, day: str = "2026-08-10", content: str = YESTERDAY_NOTE):
    (root / "03_Journal" / "periodic" / "daily" / f"{day}.md").write_text(
        content, encoding="utf-8"
    )


class CarryOverTests(unittest.TestCase):
    """Spec §17.5: yesterday's unchecked tasks land in today's Backlog."""

    def test_open_tasks_carry_verbatim_done_and_code_do_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_yesterday(root)
            target, created = daily_note.ensure_note(root, TODAY)
            self.assertTrue(created)
            content = target.read_text(encoding="utf-8")
        self.assertIn("- [ ] carry me 📅 2026-08-15", content)
        self.assertIn("  - [ ] nested open child", content)  # indentation kept
        self.assertNotIn("already done", content)
        self.assertNotIn("code fence", content)
        self.assertNotIn("code span", content)
        # Carried lines sit inside the Backlog section, before ### Health.
        self.assertLess(
            content.index("### Backlog"), content.index("- [ ] carry me")
        )
        self.assertLess(content.index("- [ ] carry me"), content.index("### Health"))

    def test_restricted_yesterday_carries_nothing(self):
        # Containment (spec §17.5): task text never flows out of a
        # restricted note into the new, non-restricted daily note.
        restricted = (
            "---\ntitle: \"2026-08-10\"\ntags:\n  - type/journal\n"
            "  - restricted/private\nupdated: 2026-08-10\n---\n\n"
            "- [ ] secret errand\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_yesterday(root, content=restricted)
            target, created = daily_note.ensure_note(root, TODAY)
            self.assertTrue(created)
            content = target.read_text(encoding="utf-8")
        self.assertNotIn("secret errand", content)

    def test_derived_private_and_unknown_yesterday_carry_nothing(self):
        for provenance in (
            '["06_Resources/private.md"]',
            '["06_Resources/missing.md"]',
            'malformed',
        ):
            with self.subTest(provenance=provenance), tempfile.TemporaryDirectory() as tmp:
                root = make_root(tmp)
                resources = root / "06_Resources"
                resources.mkdir()
                (resources / "private.md").write_text(
                    YESTERDAY_NOTE.replace("  - type/journal", "  - restricted/private"),
                    encoding="utf-8",
                )
                write_yesterday(root, content=YESTERDAY_NOTE.replace(
                    "updated:", f"privacy-sources: {provenance}\nupdated:", 1
                ))
                target, _ = daily_note.ensure_note(root, TODAY)
                self.assertNotIn("carry me", target.read_text(encoding="utf-8"))

    def test_carry_uses_classified_snapshot_and_keeps_reclassifiable_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_yesterday(root)
            original_build = daily_note.brain.build_index

            def replace_yesterday_after_capture(*args, **kwargs):
                write_yesterday(root, content=YESTERDAY_NOTE.replace(
                    "  - type/journal", "  - restricted/private"
                ).replace("carry me", "new private task"))
                return original_build(*args, **kwargs)

            with mock.patch.object(
                daily_note.brain, "build_index", side_effect=replace_yesterday_after_capture
            ):
                target, _ = daily_note.ensure_note(root, TODAY)
            content = target.read_text(encoding="utf-8")
            self.assertIn("- [ ] carry me", content)
            self.assertNotIn("new private task", content)
            notes, assets = daily_note.brain.walk_corpus(root)
            states = daily_note.brain.effective_privacy(original_build(root, notes, assets))
            self.assertEqual(states[target.relative_to(root).as_posix()], "private")
            tomorrow, _ = daily_note.ensure_note(root, TODAY + datetime.timedelta(days=1))
            self.assertNotIn("carry me", tomorrow.read_text(encoding="utf-8"))

    def test_carry_merges_template_provenance_without_duplicates(self):
        source = f"{daily_note.DAILY_DIR}/2026-08-10.md"
        for provenance in (
            f'["06_Resources/context.md", "{source}"]',
            "\n  - 06_Resources/context.md",
        ):
            with self.subTest(provenance=provenance), tempfile.TemporaryDirectory() as tmp:
                root = make_root(tmp)
                template = root / "09_Templates" / "template-daily-log.md"
                template.write_text(TEMPLATE.replace(
                    "updated:", f"privacy-sources: {provenance}\nupdated:", 1
                ), encoding="utf-8")
                write_yesterday(root)
                target, _ = daily_note.ensure_note(root, TODAY)
                fm, errors, *_ = daily_note.brain.parse_frontmatter(
                    target.read_text(encoding="utf-8").split("\n")
                )
                self.assertEqual(errors, [])
                self.assertEqual(fm["privacy-sources"], [source, "06_Resources/context.md"])

    def test_malformed_template_provenance_refuses_creation(self):
        for provenance in ('malformed', '["../outside.md"]', '[]\nprivacy-sources: []'):
            with self.subTest(provenance=provenance), tempfile.TemporaryDirectory() as tmp:
                root = make_root(tmp)
                template = root / "09_Templates" / "template-daily-log.md"
                template.write_text(TEMPLATE.replace(
                    "updated:", f"privacy-sources: {provenance}\nupdated:", 1
                ), encoding="utf-8")
                write_yesterday(root)
                with self.assertRaises(daily_note.brain.NoteWriteError):
                    daily_note.ensure_note(root, TODAY)
                self.assertFalse((root / daily_note.DAILY_DIR / "2026-08-11.md").exists())

    def test_no_yesterday_note_means_no_carry_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            target, created = daily_note.ensure_note(root, TODAY)
            self.assertTrue(created)
            content = target.read_text(encoding="utf-8")
        self.assertNotIn("carry me", content)
        self.assertIn("### Backlog", content)

    def test_iso_week_year_boundary_carries_from_previous_year(self):
        # Yesterday of 2027-01-01 is 2026-12-31 (ISO week 2026-W53).
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_yesterday(root, day="2026-12-31")
            target, _ = daily_note.ensure_note(root, datetime.date(2027, 1, 1))
            content = target.read_text(encoding="utf-8")
        self.assertIn("- [ ] carry me 📅 2026-08-15", content)

    def test_config_toggle_off_disables_carry_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_yesterday(root)
            (root / "00_Meta").mkdir()
            (root / "00_Meta" / "config.yaml").write_text(
                "tasks:\n  carry_over: off\n", encoding="utf-8"
            )
            target, _ = daily_note.ensure_note(root, TODAY)
            content = target.read_text(encoding="utf-8")
        self.assertNotIn("carry me", content)

    def test_template_without_backlog_heading_gains_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            template = root / "09_Templates" / "template-daily-log.md"
            template.write_text(
                template.read_text(encoding="utf-8").split("### Backlog")[0],
                encoding="utf-8",
            )
            write_yesterday(root)
            target, _ = daily_note.ensure_note(root, TODAY)
            content = target.read_text(encoding="utf-8")
        self.assertIn("### Backlog", content)
        self.assertIn("- [ ] carry me 📅 2026-08-15", content)

    def test_existing_note_is_untouched_by_carry_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            write_yesterday(root)
            existing = root / "03_Journal" / "periodic" / "daily" / "2026-08-11.md"
            existing.write_text("owner edits\n", encoding="utf-8")
            _, created = daily_note.ensure_note(root, TODAY)
            self.assertFalse(created)
            self.assertEqual(existing.read_text(encoding="utf-8"), "owner edits\n")


if __name__ == "__main__":
    unittest.main()
