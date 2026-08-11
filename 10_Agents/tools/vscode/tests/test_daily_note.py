"""Tests for daily_note.py (VS Code daily-note task, PRD §6.5).

Run via the tools runner:
    python3 10_Agents/tools/run_tests.py
"""

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import daily_note  # noqa: E402

TEMPLATE = """---
title: "{{date}}"
tags:
  - type/journal
updated: {{date}}
---

# {{date}}

- Weekly review: [[{{RELATED_WEEKLY_REVIEW}}]]
- Yesterday: [[{{PREVIOUS_DAILY_NOTE}}]]
"""


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
        # Unresolved wikilinks are brain-validate errors, so absent notes must
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
        self.assertIn("[[03_Journal/periodic/weekly/2026-W33-review]]", content)
        self.assertIn("[[2026-08-10]]", content)

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
        self.assertIn("[[03_Journal/periodic/weekly/2026-W53-review]]", content)


class EnsureNoteTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
