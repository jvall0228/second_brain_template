"""§29: `brain triage-archive` (monthly rollup of applied Inbox reports) and
`brain trace` (daily/weekly traces for a capture's event date).

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402
from test_brain import make_vault  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]

CONVENTIONS = (
    "---\ntitle: Conventions\ntags:\n  - type/meta\nupdated: 2026-08-11\nexpires: 2027-01-01\n---\n\n"
    "# Conventions\n\n## Tag Namespaces\n\n| Namespace | Purpose | Values |\n|---|---|---|\n"
    "| `audience/*` | Who | `agent`, `human` |\n"
    "| `type/*` | Kind | `meta`, `note`, `log`, `journal`, `reference` |\n"
    "| `topic/*` | Subject | Free-form |\n"
    "| `workflow/*` | Stage | `canonical`, `draft`, `review` |\n"
    "| `status/*` | Actionability | `active`, `done` |\n"
    "| `restricted/*` | Privacy | `private` |\n"
)
TODAY = date(2026, 9, 1)


def note(title="Note", tags=("type/note", "audience/human"), body="Body.\n", updated="2026-08-11"):
    return (
        f'---\ntitle: "{title}"\ntags:\n' + "".join(f"  - {t}\n" for t in tags) + f"updated: {updated}\n---\n\n# {title}\n\n{body}"
    )


REPORT = (
    '---\ntitle: "Triage Report — 2026-08-30"\ntags:\n  - type/log\n  - audience/agent\n  - workflow/review\n'
    "updated: 2026-08-30\nauthor: claude-code\nsession: https://example.invalid/session/1\n---\n\n"
    "# Triage Report — 2026-08-30\n\n"
    "Intro with [plain](../05_Areas/x.md), [frag](../05_Areas/x.md#section-one \"Title here\"), "
    "[angle](<../05_Areas/x.md>), sibling [other](2026-08-30-other.md), and `[code](../05_Areas/x.md)`.\n\n"
    "## Disposition\n\n| # | Note | Dest |\n|---|---|---|\n| 1 | [x](../05_Areas/x.md) | `05_Areas/` |\n\n"
    "### New filings\n\n```\n[fenced](../05_Areas/x.md)\n# not a heading\n```\n\n"
    "###### Deep\n\nDone.\n"
)


def base_files():
    return {
        "00_Meta/CONVENTIONS.md": CONVENTIONS,
        "05_Areas/x.md": note("X", body="## Section One\n\nText.\n"),
        "02_Inbox/2026-08-30-triage-report.md": REPORT,
        "02_Inbox/2026-08-30-other.md": note("Other"),
        "01_Profile/NOW.md": note("Now"),
        "10_Agents/skills/triage-inbox/SKILL.md": (
            "---\nname: triage-inbox\ndescription: Triage.\ntitle: \"Skill: Triage Inbox\"\ntags:\n  - type/reference\n"
            "updated: 2026-08-11\n---\n\n# Triage Inbox\n"
        ),
        "09_Templates/template-daily-log.md": (ROOT / "09_Templates/template-daily-log.md").read_text(encoding="utf-8"),
        "09_Templates/template-weekly-review.md": (ROOT / "09_Templates/template-weekly-review.md").read_text(encoding="utf-8"),
    }


def run_cli(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(
        brain, "vault_today", return_value=TODAY
    ):
        code = brain.main([*argv, "--vault", str(root)])
    return code, out.getvalue(), err.getvalue()


class TriageArchiveTests(unittest.TestCase):
    LOG = "07_Archives/inbox/2026-08-triage-log.md"

    def test_links_rebased_headings_nested_and_validation_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, out, err = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--json")
            self.assertEqual(code, 0, err)
            plan = json.loads(out)
            self.assertEqual(plan["action"], "create")
            self.assertTrue((root / "02_Inbox/2026-08-30-triage-report.md").exists(), "preview never writes")
            self.assertFalse((root / self.LOG).exists())
            code, out, err = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write")
            self.assertEqual(code, 0, out + err)
            self.assertFalse((root / "02_Inbox/2026-08-30-triage-report.md").exists())
            log = (root / self.LOG).read_text(encoding="utf-8")
            # Cross-directory rebasing, anchors, titles, angle destinations.
            self.assertIn("[plain](../../05_Areas/x.md)", log)
            self.assertIn('[frag](../../05_Areas/x.md#section-one "Title here")', log)
            self.assertIn("[angle](<../../05_Areas/x.md>)", log)
            self.assertIn("[other](../../02_Inbox/2026-08-30-other.md)", log)
            self.assertIn("`[code](../05_Areas/x.md)`", log)
            self.assertIn("```\n[fenced](../05_Areas/x.md)\n# not a heading\n```", log)
            # Heading nesting under the run heading; the document H1 is gone.
            self.assertIn("\n## 2026-08-30 — Triage Report — 2026-08-30\n", log)
            self.assertIn("\n### Disposition\n", log)
            self.assertIn("\n#### New filings\n", log)
            self.assertIn("\n###### Deep\n", log)
            self.assertNotIn("\n# Triage Report", log)
            prose_h1 = [l for l, code in brain.iter_fenced_lines(log.split("\n"), 0) if not code and l.startswith("# ")]
            self.assertEqual(prose_h1, ["# Triage Log — 2026-08"])
            self.assertIn("*Run: claude-code, https://example.invalid/session/1*", log)
            self.assertEqual(len(brain._marker_values(log, brain.TRIAGE_ARCHIVE_MARKER)), 1)
            self.assertIn("updated: 2026-09-01", log.split("---")[1])
            errors, _ = brain.run_validate(root, check_index=False)
            self.assertEqual([e for e in errors if e["rule"] == "unresolved-link"], [])
            self.assertEqual([e for e in errors if e["path"] == self.LOG], [])

    def test_interrupted_append_then_retry_yields_exactly_one_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            plan = brain.triage_archive_plan(root, "02_Inbox/2026-08-30-triage-report.md", TODAY)
            # Simulate a crash after the log write, before the delete.
            (root / self.LOG).parent.mkdir(parents=True)
            (root / self.LOG).write_text(plan["rendered"], encoding="utf-8")
            after_write = (root / self.LOG).read_bytes()
            code, out, err = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual(data["action"], "delete-only")
            self.assertFalse((root / "02_Inbox/2026-08-30-triage-report.md").exists())
            self.assertEqual((root / self.LOG).read_bytes(), after_write)
            self.assertEqual(len(brain._marker_values(after_write.decode("utf-8"), brain.TRIAGE_ARCHIVE_MARKER)), 1)

    def test_repeated_execution_is_byte_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, _, _ = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write")
            self.assertEqual(code, 0)
            first = (root / self.LOG).read_bytes()
            code, out, _ = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write", "--json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["action"], "done")
            self.assertEqual((root / self.LOG).read_bytes(), first)
            # A second report the same month appends a second run only.
            files = {"02_Inbox/2026-08-31-triage-report.md": REPORT.replace("2026-08-30", "2026-08-31").replace("2026-08-31-other.md", "2026-08-30-other.md")}
            make_vault(root, files)
            code, _, _ = run_cli(root, "triage-archive", "02_Inbox/2026-08-31-triage-report.md", "--write")
            self.assertEqual(code, 0)
            log = (root / self.LOG).read_text(encoding="utf-8")
            self.assertEqual(log.count("\n## 2026-08-3"), 2)
            self.assertTrue(log.startswith(first.decode("utf-8").rstrip("\n")))

    def test_final_validation_catches_a_transformation_defect(self):
        files = base_files()
        files["02_Inbox/2026-08-30-triage-report.md"] = REPORT.replace("[plain](../05_Areas/x.md)", "[gone](../05_Areas/missing.md)")
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            code, out, _ = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write")
            self.assertEqual(code, 1)
            self.assertIn(f"ERROR {self.LOG}", out)
            self.assertIn("unresolved-link", out)

    def test_restricted_report_moves_as_its_own_note(self):
        files = base_files()
        files["02_Inbox/2026-08-30-triage-report.md"] = REPORT.replace("  - workflow/review\n", "  - workflow/review\n  - restricted/private\n")
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            code, out, err = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual(data["action"], "move")
            self.assertFalse((root / self.LOG).exists())
            moved = (root / "07_Archives/inbox/2026-08-30-triage-report.md").read_text(encoding="utf-8")
            self.assertIn("status/done", brain.parse_frontmatter(moved.split("\n"))[0]["tags"])
            self.assertNotIn("workflow/review", moved)
            self.assertIn("restricted/private", brain.parse_frontmatter(moved.split("\n"))[0]["tags"])
            self.assertIn("[plain](../../05_Areas/x.md)", moved)
            self.assertIn("# Triage Report — 2026-08-30", moved)
            self.assertFalse((root / "02_Inbox/2026-08-30-triage-report.md").exists())
            code, out, _ = run_cli(root, "triage-archive", "02_Inbox/2026-08-30-triage-report.md", "--write", "--json")
            self.assertEqual((code, json.loads(out)["action"]), (0, "done"))

    def test_rejects_paths_outside_the_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            for bad in ("05_Areas/x.md", "02_Inbox/README.md", "02_Inbox/sub/2026-08-30-x.md", "../02_Inbox/2026-08-30-triage-report.md"):
                code, _, err = run_cli(root, "triage-archive", bad)
                self.assertEqual(code, 1, bad)


class TraceTests(unittest.TestCase):
    DAILY = "03_Journal/periodic/daily/2026-08-20.md"
    WEEKLY = "03_Journal/periodic/weekly/2026-W34-review.md"

    def trace(self, root, *extra, day="2026-08-20", dest="05_Areas/x.md", summary="Filed the X capture", identity="02_Inbox/2026-08-20-x.md"):
        return run_cli(root, "trace", "--date", day, "--destination", dest, "--summary", summary, "--id", identity, *extra)

    def test_iso_week_year_at_year_boundaries(self):
        self.assertEqual(brain.periodic_targets(date(2027, 1, 1))["weekId"], "2026-W53")
        self.assertEqual(brain.periodic_targets(date(2026, 12, 31))["weekId"], "2026-W53")
        self.assertEqual(brain.periodic_targets(date(2024, 12, 30))["weekId"], "2025-W01")
        self.assertEqual(brain.periodic_targets(date(2021, 1, 3))["weekId"], "2020-W53")
        self.assertEqual(brain.periodic_targets(date(2027, 1, 4))["weekId"], "2027-W01")
        targets = brain.periodic_targets(date(2027, 1, 1))
        self.assertEqual(targets["weekly"], "03_Journal/periodic/weekly/2026-W53-review.md")
        self.assertEqual(targets["daily"], "03_Journal/periodic/daily/2027-01-01.md")

    def test_older_capture_backfills_daily_and_weekly_from_templates(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, out, err = self.trace(root, "--json")
            self.assertEqual(code, 0, err)
            self.assertFalse((root / self.DAILY).exists(), "preview never writes")
            code, out, err = self.trace(root, "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual([(n["action"], n["path"]) for n in data["notes"]], [("create", self.DAILY), ("create", self.WEEKLY)])
            daily = (root / self.DAILY).read_text(encoding="utf-8")
            weekly = (root / self.WEEKLY).read_text(encoding="utf-8")
            self.assertNotIn("{{", daily)
            self.assertNotIn("{{", weekly)
            self.assertIn('title: "2026-08-20"', daily)
            self.assertIn("updated: 2026-09-01", daily)
            self.assertIn("[Current weekly review](../weekly/2026-W34-review.md)", daily)
            self.assertNotIn("Yesterday", daily)  # no 2026-08-19 note exists: line dropped
            self.assertIn("### Activity Log\n\n- [Filed the X capture](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-x.md -->\n", daily)
            self.assertIn('title: "2026-W34 Review"', weekly)
            self.assertIn("[Related daily note](../daily/2026-08-20.md)", weekly)
            self.assertNotIn("Monthly review", weekly)
            self.assertIn("- [Filed the X capture](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-x.md -->", weekly.split("## Get Clear")[1].split("## Get Current")[0])
            self.assertEqual(data["validation"]["errors"], [])

    def test_work_variant_templates_backfill_cleanly(self):
        # The template's own Work context specialization (onboard-owner)
        # copies 09_Templates/variants/work-daily-log.md and
        # work-weekly-review.md over template-daily-log.md /
        # template-weekly-review.md. Those variants carry
        # {{HIGH_PRIORITY_GOAL}}/{{MEDIUM_PRIORITY_GOAL}}/{{LOW_PRIORITY_GOAL}}
        # placeholders the default templates don't have; brain trace must
        # still produce a clean instantiation (no leftover placeholders) and
        # file the trace line under the work variant's own headings.
        #
        # Exercised via trace_plan/apply_trace directly (not the CLI) because
        # the variants, copied verbatim "in place" one directory level
        # shallower than 09_Templates/variants/, carry relative links
        # (../template-decision-record.md, ../../01_Profile/NOW.md) that are
        # correct only at their original depth — a pre-existing link-depth
        # defect in the variant files themselves, orthogonal to the
        # placeholder handling this test targets, and not owned by this
        # cluster; see CompareAndSwapTests for the same direct-call pattern.
        files = base_files()
        files["09_Templates/template-daily-log.md"] = (ROOT / "09_Templates/variants/work-daily-log.md").read_text(encoding="utf-8")
        files["09_Templates/template-weekly-review.md"] = (ROOT / "09_Templates/variants/work-weekly-review.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            plan = brain.trace_plan(
                root,
                day=date(2026, 8, 20),
                destination="05_Areas/x.md",
                summary="Filed the X capture",
                identity="02_Inbox/2026-08-20-x.md",
                kind=None,
                today_d=TODAY,
            )
            self.assertEqual([(n["action"], n["path"]) for n in plan["notes"]], [("create", self.DAILY), ("create", self.WEEKLY)])
            brain.apply_trace(root, plan)
            daily = (root / self.DAILY).read_text(encoding="utf-8")
            weekly = (root / self.WEEKLY).read_text(encoding="utf-8")
            self.assertNotIn("{{", daily)
            self.assertNotIn("{{", weekly)
            self.assertIn("### Activity Log\n\n- [Filed the X capture](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-x.md -->\n", daily)
            self.assertIn("- [Filed the X capture](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-x.md -->", weekly.split("## Get Clear")[1].split("## Get Current")[0])

    def test_two_captures_same_day_same_destination_both_land_and_reruns_are_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            self.assertEqual(self.trace(root, "--write")[0], 0)
            code, _, _ = self.trace(root, "--write", summary="Second capture, same destination", identity="02_Inbox/2026-08-20-y.md")
            self.assertEqual(code, 0)
            daily = (root / self.DAILY).read_bytes()
            weekly = (root / self.WEEKLY).read_bytes()
            text = daily.decode("utf-8")
            self.assertIn("- [Filed the X capture](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-x.md -->\n- [Second capture, same destination](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-y.md -->", text)
            code, out, _ = self.trace(root, "--write", "--json")
            self.assertEqual(code, 0)
            self.assertEqual({n["action"] for n in json.loads(out)["notes"]}, {"skip"})
            self.assertEqual((root / self.DAILY).read_bytes(), daily)
            self.assertEqual((root / self.WEEKLY).read_bytes(), weekly)
            code, _, _ = self.trace(root, "--write", summary="Same identity, different words")
            self.assertEqual(code, 0)
            self.assertEqual((root / self.DAILY).read_bytes(), daily)

    def test_existing_notes_are_appended_in_place_and_project_kind_adds_get_current(self):
        files = base_files()
        files[self.DAILY] = (
            '---\ntitle: "2026-08-20"\ntags:\n  - type/journal\n  - audience/human\nupdated: 2026-08-20\n---\n\n# 2026-08-20\n\n'
            "## Review\n\n### Activity Log\n\n- Existing entry.\n\n### Backlog\n\n-\n"
        )
        files[self.WEEKLY] = (
            '---\ntitle: "2026-W34 Review"\ntags:\n  - type/journal\n  - audience/human\nupdated: 2026-08-20\n---\n\n# 2026-W34 Review\n\n'
            "## Get Clear\n\n- [ ] Process Inbox to zero\n\n## Get Current — Projects\n\nReview.\n\n## Get Current — Areas\n\nReview.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            code, out, err = self.trace(root, "--write", "--kind", "project", "--json")
            self.assertEqual(code, 0, err)
            daily = (root / self.DAILY).read_text(encoding="utf-8")
            weekly = (root / self.WEEKLY).read_text(encoding="utf-8")
            self.assertIn("### Activity Log\n\n- Existing entry.\n- [Filed the X capture](../../../05_Areas/x.md) <!-- trace: 02_Inbox/2026-08-20-x.md -->\n\n### Backlog", daily)
            self.assertIn("updated: 2026-09-01", daily)
            self.assertIn("- [ ] Process Inbox to zero\n- [Filed the X capture]", weekly)
            self.assertIn("## Get Current — Projects\n\nReview.\n- [Filed the X capture]", weekly)
            self.assertNotIn("## Get Current — Areas\n\nReview.\n- [Filed", weekly)
            code, _, err = self.trace(root, "--write", "--kind", "area", identity="02_Inbox/2026-08-20-z.md")
            self.assertEqual(code, 0, err)
            self.assertIn("## Get Current — Areas\n\nReview.\n- [Filed the X capture]", (root / self.WEEKLY).read_text(encoding="utf-8"))

    def test_restricted_destination_is_traced_by_title_only_and_markup_is_neutralized(self):
        files = base_files()
        files["05_Areas/secret.md"] = note("Secret Record", tags=("type/note", "restricted/private"))
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            code, out, err = self.trace(root, "--write", "--json", dest="05_Areas/secret.md", summary="Diagnosis and dosage details")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertTrue(data["substanceDropped"])
            daily = (root / self.DAILY).read_text(encoding="utf-8")
            self.assertIn("[Secret Record](../../../05_Areas/secret.md)", daily)
            self.assertNotIn("dosage", daily)
            code, out, err = self.trace(root, "--write", summary="a [link](x.md) <b> `code` ]", identity="02_Inbox/2026-08-20-m.md")
            self.assertEqual(code, 0, err)
            daily = (root / self.DAILY).read_text(encoding="utf-8")
            self.assertIn("- [a \\[link\\](x.md) \\<b\\> \\`code\\` \\]](../../../05_Areas/x.md)", daily)
            code, _, err = self.trace(root, "--write", identity="bad --> id")
            self.assertEqual(code, 1)
            code, _, err = self.trace(root, "--write", identity="line1\nline2")
            self.assertEqual(code, 0, err)  # newlines collapse to one line
            self.assertIn("<!-- trace: line1 line2 -->", (root / self.DAILY).read_text(encoding="utf-8"))

    def test_missing_destination_or_section_is_an_error_without_writes(self):
        files = base_files()
        files[self.DAILY] = '---\ntitle: "2026-08-20"\ntags:\n  - type/journal\nupdated: 2026-08-20\n---\n\n# 2026-08-20\n\nNo sections.\n'
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            before = (root / self.DAILY).read_bytes()
            code, _, err = self.trace(root, "--write", dest="05_Areas/nope.md")
            self.assertEqual(code, 1)
            code, _, err = self.trace(root, "--write")
            self.assertEqual(code, 1)
            self.assertIn("Activity Log", err)
            self.assertEqual((root / self.DAILY).read_bytes(), before)
            self.assertFalse((root / self.WEEKLY).exists())


if __name__ == "__main__":
    unittest.main()
