"""Tests for `brain report` (spec.md §16, issue #16).

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

from test_brain import FIXTURE, make_vault  # noqa: E402

TODAY = date(2026, 8, 11)


def note(body: str = "", tags=("type/note",), updated="2026-08-01", title="x") -> str:
    lines = ["---", f"title: {title}", "tags:"]
    lines += [f"  - {t}" for t in tags]
    if updated is not None:
        lines.append(f"updated: {updated}")
    lines += ["---", body, ""]
    return "\n".join(lines)


# A fixture vault with known counts for every section (ages against TODAY):
#   stale-active: active-stale (71d) — active-fresh (10d) stays under 30d.
#   orphans: 06_Resources/loner.md only (hub links out; linked has a backlink;
#            README/07_Archives/09_Templates excluded).
#   inbox aging: 1d (filename), 71d (filename, triage debt), 6d (updated:),
#                one unknown; README excluded.
#   tag drift: type/bogus unknown-value, madeup/x unknown-namespace, plain
#              not-namespaced; topic/sw single-use + near-duplicate of
#              topic/software (used twice).
#   unresolved: one Markdown link to missing-note.md.
REPORT_FILES = {
    "04_Projects/active-stale.md": note(tags=("type/note", "status/active"), updated="2026-06-01"),
    "04_Projects/active-fresh.md": note(tags=("type/note", "status/active"), updated="2026-08-01"),
    "06_Resources/hub.md": note(body="[linked](linked.md) and [missing](missing-note.md)", tags=("type/note", "topic/software")),
    "06_Resources/linked.md": note(tags=("type/note", "topic/software")),
    "06_Resources/loner.md": note(tags=("type/note", "topic/sw")),
    "06_Resources/README.md": note(),
    "07_Archives/dead.md": note(),
    "09_Templates/template-thing.md": note(),
    "02_Inbox/README.md": note(),
    "02_Inbox/2026-08-10-capture.md": note(updated="2026-08-10"),
    "02_Inbox/2026-06-01-old.md": note(updated="2026-08-01"),
    "02_Inbox/no-date.md": note(updated="2026-08-05"),
    "02_Inbox/mystery.md": "---\ntitle: x\ntags:\n  - type/note\n---\n",
    "05_Areas/drifty.md": note(tags=("type/bogus", "madeup/x", "plain"), updated="2026-08-09"),
}


class ReportTestCase(unittest.TestCase):
    CONVENTIONS = None

    @classmethod
    def setUpClass(cls):
        cls.CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text()

    def vault(self, td, extra=None):
        return make_vault(
            Path(td),
            {"00_Meta/CONVENTIONS.md": self.CONVENTIONS, **REPORT_FILES, **(extra or {})},
        )

    def run_cli(self, root, *argv):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(
            brain, "today", lambda: TODAY
        ):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue(), err.getvalue()

    def report_json(self, root, *argv):
        code, out, _ = self.run_cli(root, "report", "--json", *argv)
        self.assertEqual(code, 0)
        return json.loads(out)


class SectionTests(ReportTestCase):
    def test_stale_active(self):
        with tempfile.TemporaryDirectory() as td:
            rep = self.report_json(self.vault(td))
            self.assertEqual(
                rep["staleActive"],
                [
                    {
                        "daysOld": 71,
                        "path": "04_Projects/active-stale.md",
                        "title": "x",
                        "updated": "2026-06-01",
                    }
                ],
            )
            self.assertEqual(rep["thresholds"], {"inboxDays": 14, "staleDays": 30})

    def test_inbox_date_prefix_requires_boundary(self):
        # '2026-08-1234-weird.md' must not parse as capture date 2026-08-12 —
        # it falls back to updated:, keeping real triage debt visible.
        with tempfile.TemporaryDirectory() as td:
            extra = {
                "02_Inbox/2026-08-1234-weird.md": (
                    "---\ntitle: \"w\"\ntags:\n  - type/log\nupdated: 2026-06-01\n---\nx\n"
                )
            }
            rep = self.report_json(self.vault(td, extra))
            rows = [
                r
                for bucket in rep["inboxAging"]["buckets"].values()
                for r in bucket
                if r["path"].endswith("weird.md")
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "updated")
            self.assertIn("02_Inbox/2026-08-1234-weird.md", rep["inboxAging"]["triageDebt"])

    def test_orphans_exclude_readmes_templates_archives(self):
        with tempfile.TemporaryDirectory() as td:
            rep = self.report_json(self.vault(td))
            # loner: no links either way. drifty/mystery/actives are also
            # link-free -> orphans too; the structural exclusions are what
            # this test pins.
            self.assertIn("06_Resources/loner.md", rep["orphans"])
            self.assertNotIn("06_Resources/README.md", rep["orphans"])
            self.assertNotIn("07_Archives/dead.md", rep["orphans"])
            self.assertNotIn("09_Templates/template-thing.md", rep["orphans"])
            self.assertNotIn("06_Resources/hub.md", rep["orphans"])  # has outgoing
            self.assertNotIn("06_Resources/linked.md", rep["orphans"])  # has backlink
            self.assertEqual(rep["orphans"], sorted(rep["orphans"]))

    def test_inbox_aging_buckets_sources_and_triage_debt(self):
        with tempfile.TemporaryDirectory() as td:
            rep = self.report_json(self.vault(td))
            buckets = rep["inboxAging"]["buckets"]
            self.assertEqual(sorted(buckets), sorted(brain.REPORT_BUCKET_LABELS))
            self.assertEqual(
                buckets["0-7d"],
                [
                    {"ageDays": 1, "path": "02_Inbox/2026-08-10-capture.md", "source": "filename"},
                    {"ageDays": 6, "path": "02_Inbox/no-date.md", "source": "updated"},
                ],
            )
            self.assertEqual(
                buckets["31-90d"],
                [{"ageDays": 71, "path": "02_Inbox/2026-06-01-old.md", "source": "filename"}],
            )
            self.assertEqual(
                buckets["unknown"],
                [{"ageDays": None, "path": "02_Inbox/mystery.md", "source": "unknown"}],
            )
            self.assertEqual(buckets["8-30d"], [])
            self.assertEqual(buckets["90+d"], [])
            self.assertEqual(rep["inboxAging"]["triageDebt"], ["02_Inbox/2026-06-01-old.md"])
            # README.md never counts as Inbox aging.
            for rows in buckets.values():
                self.assertNotIn("02_Inbox/README.md", [r["path"] for r in rows])

    def test_tag_drift_reuses_validate_taxonomy(self):
        with tempfile.TemporaryDirectory() as td:
            rep = self.report_json(self.vault(td))
            drift = rep["tagDrift"]
            self.assertTrue(drift["taxonomyReadable"])
            self.assertEqual(
                drift["unknown"],
                [
                    {"count": 1, "reason": "unknown-namespace", "tag": "madeup/x"},
                    {"count": 1, "reason": "not-namespaced", "tag": "plain"},
                    {"count": 1, "reason": "unknown-value", "tag": "type/bogus"},
                ],
            )
            self.assertEqual(drift["singleUse"], ["topic/sw"])
            self.assertEqual(
                drift["nearDuplicates"],
                [{"namespace": "topic", "values": ["sw", "software"]}],
            )

    def test_is_abbreviation_heuristic(self):
        for short, long, expected in [
            ("sw", "software", True),  # abbreviation (the issue's example)
            ("tool", "tools", True),  # prefix
            ("ml", "machine-learning", True),  # in-order subsequence
            ("os", "software", False),  # first chars differ
            ("a", "anything", False),  # too short to signal
            ("software", "software", False),  # not strictly shorter
            ("ws", "software", False),  # out of order
        ]:
            self.assertEqual(brain.is_abbreviation(short, long), expected, (short, long))

    def test_unresolved_links(self):
        with tempfile.TemporaryDirectory() as td:
            rep = self.report_json(self.vault(td))
            self.assertEqual(rep["unresolvedLinks"]["count"], 1)
            self.assertEqual(
                rep["unresolvedLinks"]["links"],
                [{"line": 8, "path": "06_Resources/hub.md", "target": "missing-note.md"}],
            )

    def test_unreadable_taxonomy_disables_drift_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), dict(REPORT_FILES))  # no CONVENTIONS.md
            rep = self.report_json(root)
            drift = rep["tagDrift"]
            self.assertFalse(drift["taxonomyReadable"])
            self.assertEqual(
                (drift["unknown"], drift["singleUse"], drift["nearDuplicates"]),
                ([], [], []),
            )
            self.assertEqual(len(rep["staleActive"]), 1)  # other sections intact


class SinceTests(ReportTestCase):
    def test_since_scopes_drift_and_unresolved_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td)
            rep = self.report_json(root, "--since", "2026-08-05")
            self.assertEqual(rep["since"], "2026-08-05")
            # hub.md (updated 2026-08-01) falls outside the window.
            self.assertEqual(rep["unresolvedLinks"], {"count": 0, "links": []})
            # drifty.md (2026-08-09) stays in; loner/hub/linked drop out.
            self.assertEqual(
                [r["tag"] for r in rep["tagDrift"]["unknown"]],
                ["madeup/x", "plain", "type/bogus"],
            )
            self.assertEqual(rep["tagDrift"]["singleUse"], [])
            self.assertEqual(rep["tagDrift"]["nearDuplicates"], [])
            # Debt sections are never scoped.
            full = self.report_json(root)
            self.assertEqual(rep["staleActive"], full["staleActive"])
            self.assertEqual(rep["orphans"], full["orphans"])
            self.assertEqual(rep["inboxAging"], full["inboxAging"])

    def test_bad_since_is_operational_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td)
            for bad in ("notadate", "2026-13-40", "2026/08/01"):
                code, _, err = self.run_cli(root, "report", "--since", bad)
                self.assertEqual(code, 1, bad)
                self.assertIn("--since", err)


class ConfigThresholdTests(ReportTestCase):
    def test_config_overrides_thresholds(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(
                td,
                {"00_Meta/config.yaml": "report:\n  stale_days: 5\n  inbox_days: 1\n"},
            )
            rep = self.report_json(root)
            self.assertEqual(rep["thresholds"], {"inboxDays": 1, "staleDays": 5})
            self.assertEqual(
                [r["path"] for r in rep["staleActive"]],
                ["04_Projects/active-stale.md", "04_Projects/active-fresh.md"],
            )
            self.assertEqual(
                rep["inboxAging"]["triageDebt"],
                ["02_Inbox/2026-06-01-old.md", "02_Inbox/no-date.md"],
            )

    def test_report_thresholds_defaults_and_malformed(self):
        self.assertEqual(
            brain.report_thresholds({}),
            {"inboxDays": brain.REPORT_INBOX_TRIAGE_DAYS, "staleDays": brain.REPORT_STALE_ACTIVE_DAYS},
        )
        self.assertEqual(
            brain.report_thresholds({"report": {"stale_days": "abc", "inbox_days": None}}),
            {"inboxDays": 14, "staleDays": 30},
        )
        self.assertEqual(
            brain.report_thresholds({"report": "5"}),  # wrong shape -> defaults
            {"inboxDays": 14, "staleDays": 30},
        )

    def test_check_config_report_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Not a mapping -> error.
            errors, warnings = brain.check_config(root, {"report": "30"}, [])
            self.assertEqual([f["rule"] for f in errors], ["config-invalid-value"])
            # Bad integer -> error; unknown subkey -> dotted warning.
            errors, warnings = brain.check_config(
                root, {"report": {"stale_days": "-3", "channels": "email"}}, []
            )
            self.assertEqual([f["rule"] for f in errors], ["config-invalid-value"])
            self.assertEqual([f["rule"] for f in warnings], ["config-unknown-key"])
            self.assertIn("report.channels", warnings[0]["message"])
            # Valid / null / absent subkeys -> clean.
            errors, warnings = brain.check_config(
                root, {"report": {"stale_days": "90", "inbox_days": None}}, []
            )
            self.assertEqual((errors, warnings), ([], []))
            errors, warnings = brain.check_config(root, {"report": None}, [])
            self.assertEqual((errors, warnings), ([], []))
        # `report` is implemented now, not reserved (spec §15.3).
        self.assertIn("report", brain.CONFIG_IMPLEMENTED_KEYS)
        self.assertNotIn("report", brain.CONFIG_RESERVED_KEYS)


class DeterminismTests(ReportTestCase):
    def test_two_runs_identical(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td)
            for argv in (("report", "--json"), ("report",), ("report", "--since", "2026-08-05")):
                first = self.run_cli(root, *argv)
                second = self.run_cli(root, *argv)
                self.assertEqual(first, second, argv)

    def test_json_shape(self):
        with tempfile.TemporaryDirectory() as td:
            rep = self.report_json(self.vault(td))
            self.assertEqual(
                sorted(rep),
                [
                    "inboxAging",
                    "orphans",
                    "since",
                    "staleActive",
                    "tagDrift",
                    "thresholds",
                    "unresolvedLinks",
                ],
            )
            self.assertIsNone(rep["since"])
            self.assertEqual(sorted(rep["inboxAging"]), ["buckets", "triageDebt"])
            self.assertEqual(
                sorted(rep["tagDrift"]),
                ["nearDuplicates", "singleUse", "taxonomyReadable", "unknown"],
            )
            self.assertEqual(sorted(rep["unresolvedLinks"]), ["count", "links"])

    def test_human_output_section_order(self):
        with tempfile.TemporaryDirectory() as td:
            code, out, _ = self.run_cli(self.vault(td), "report")
            self.assertEqual(code, 0)
            positions = [
                out.index("stale-active:"),
                out.index("orphans"),
                out.index("inbox aging:"),
                out.index("tag drift:"),
                out.index("unresolved links:"),
            ]
            self.assertEqual(positions, sorted(positions))

    def test_real_vault_report_runs_clean(self):
        root = brain.default_vault_root()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = brain.main(["report", "--json", "--vault", str(root)])
        self.assertEqual(code, 0)
        json.loads(out.getvalue())


if __name__ == "__main__":
    unittest.main()
