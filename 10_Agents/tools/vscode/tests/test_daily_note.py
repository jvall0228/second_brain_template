"""Tests for daily_note.py (VS Code daily-note task, PRD §6.5), including
the spec-§17.5 task carry-over into the new note's Backlog section.

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

### Backlog

What goals and tasks need to carry over to the next day?

-

### Health
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
