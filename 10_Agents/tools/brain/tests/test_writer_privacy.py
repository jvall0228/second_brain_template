"""Derivative writers classify the exact source they transform."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain
from test_brain import make_vault
from test_triage_trace import TODAY, base_files, note
from test_gap import QUEUE, QUEUE_TEXT, RETRO, ACCEPTED_LOG, ACCEPTED_TEXT


PRIVATE = "06_Resources/private.md"
DERIVED = "06_Resources/derived.md"
SENTINEL = "PrivateSubstanceMustNotBecomePublic"


def derived(text, sources):
    return text.replace("updated:", "privacy-sources: " + json.dumps(sources) + "\nupdated:", 1)


class WriterPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        files = base_files()
        files.update({
            PRIVATE: note("Private", tags=("type/note", "restricted/private")),
            DERIVED: derived(note("Summary", body="- [ ] " + SENTINEL), [PRIVATE]),
            QUEUE: QUEUE_TEXT,
            ACCEPTED_LOG: ACCEPTED_TEXT,
        })
        self.root = make_vault(Path(self.temp.name), files)

    def test_trace_private_or_unknown_derivative_uses_only_a_bare_link(self):
        for sources in ([PRIVATE], ["06_Resources/missing.md"]):
            with self.subTest(sources=sources):
                (self.root / DERIVED).write_text(derived(note("Summary"), sources))
                plan = brain.trace_plan(self.root, day=TODAY, destination=DERIVED,
                                        summary=SENTINEL, identity="privacy-test",
                                        kind=None, today_d=TODAY)
                self.assertTrue(plan["substanceDropped"])
                for row in plan["notes"]:
                    self.assertNotIn(SENTINEL, row["rendered"])

    def test_archive_inherits_derived_privacy_in_its_own_note(self):
        rel = "02_Inbox/2026-08-30-triage-report.md"
        (self.root / rel).write_text(derived(note("Report", body=SENTINEL), [PRIVATE]))
        plan = brain.triage_archive_plan(self.root, rel, TODAY)
        self.assertEqual(plan["action"], "move")
        self.assertIn("restricted/private", brain.parse_frontmatter(plan["rendered"].split("\n"))[0]["tags"])
        self.assertIn(SENTINEL, plan["rendered"])

    def test_archive_accepts_inline_tags_and_preserves_other_frontmatter(self):
        rel = "02_Inbox/2026-08-30-triage-report.md"
        source = derived(note("Report", tags=("type/note",), body=SENTINEL), [PRIVATE])
        source = source.replace("tags:\n  - type/note", 'tags: ["type/note", "workflow/draft"]')
        (self.root / rel).write_text(source)
        plan = brain.triage_archive_plan(self.root, rel, TODAY)
        fm, errors, _, has = brain.parse_frontmatter(plan["rendered"].split("\n"))
        self.assertTrue(has)
        self.assertEqual(errors, [])
        self.assertIn("restricted/private", fm["tags"])
        self.assertIn("status/done", fm["tags"])
        self.assertNotIn("workflow/draft", fm["tags"])
        self.assertEqual(fm["privacy-sources"], [PRIVATE])

    def test_public_trace_keeps_dependency_when_its_source_later_becomes_private(self):
        (self.root / DERIVED).write_text(note("Summary", body="Public source"))
        plan = brain.trace_plan(self.root, day=TODAY, destination=DERIVED,
                                summary=SENTINEL, identity="public-trace",
                                kind=None, today_d=TODAY)
        for row in plan["notes"]:
            target = self.root / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(row["rendered"])
        (self.root / DERIVED).write_text(derived(note("Summary"), [PRIVATE]))
        for row in plan["notes"]:
            with self.assertRaises(brain.NoteContextError):
                brain.read_note_context(self.root, [row["path"]], public_only=True)

    def test_gap_nearest_and_ingest_use_effective_privacy(self):
        plan = brain.gap_plan(self.root, day=TODAY, question=SENTINEL, terms=[],
                              nearest=[DERIVED], sensitive=False, inbox=False)
        self.assertEqual(plan["action"], "capture")
        self.assertTrue(plan["restricted"])
        rel = "02_Inbox/2026-09-01-vault-answer-gap.md"
        capture = derived(plan["rendered"].replace("  - restricted/private\n", ""), [PRIVATE])
        (self.root / rel).write_text(capture)
        with self.assertRaises(brain.NoteWriteError):
            brain.gap_ingest_plan(self.root, rel, declassify=False, today_d=TODAY)

    def test_accepted_ingest_rejects_private_and_unknown_source_provenance(self):
        rel = "02_Inbox/2026-09-01-spec-retrospective.md"
        (self.root / rel).write_text(RETRO)
        self.assertTrue(brain.accepted_ingest_plan(self.root, rel, today_d=TODAY)["ingested"])
        for sources in ([PRIVATE], ["06_Resources/missing.md"]):
            with self.subTest(sources=sources):
                (self.root / rel).write_text(derived(RETRO, sources))
                with self.assertRaisesRegex(brain.NoteWriteError, "cannot enter the public acceptance log"):
                    brain.accepted_ingest_plan(self.root, rel, today_d=TODAY)

    def test_task_provenance_identifies_all_effective_classifications(self):
        cases = {
            "06_Resources/public-task.md": (note("Public", body="- [ ] Public task"), "public", False),
            PRIVATE: (note("Private", tags=("type/note", "restricted/private"), body="- [ ] Private task"), "private", True),
            DERIVED: (derived(note("Derived", body="- [ ] Derived task"), [PRIVATE]), "private", False),
            "06_Resources/two-hops.md": (derived(note("Two hops", body="- [ ] Two hops task"), [DERIVED]), "private", False),
            "06_Resources/unknown-task.md": (derived(note("Unknown", body="- [ ] Unknown task"), ["missing.md"]), "unknown", False),
        }
        for rel, (text, _privacy, _explicit) in cases.items():
            (self.root / rel).write_text(text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = brain.main(["tasks", "--open", "--json", "--vault", str(self.root)])
        self.assertEqual(code, 0)
        rows = {row["path"]: row for row in json.loads(out.getvalue())}
        for rel, (_text, privacy, explicit) in cases.items():
            with self.subTest(path=rel):
                self.assertEqual(rows[rel]["restricted"], privacy != "public")
                self.assertEqual(rows[rel]["privacy"], privacy)
                self.assertEqual(rows[rel]["explicitRestricted"], explicit)

    def test_transform_classifies_the_already_captured_bytes(self):
        rel = "02_Inbox/2026-08-30-triage-report.md"
        original = brain.transform_triage_report
        (self.root / rel).write_text(derived(note("Report", body=SENTINEL), [PRIVATE]))

        def replace_after_capture(*args):
            (self.root / rel).write_text(note("Replacement", body="Public"))
            return original(*args)

        with mock.patch.object(brain, "transform_triage_report", side_effect=replace_after_capture):
            plan = brain.triage_archive_plan(self.root, rel, TODAY)
        self.assertEqual(plan["action"], "move")
        self.assertIn("restricted/private", brain.parse_frontmatter(plan["rendered"].split("\n"))[0]["tags"])
        self.assertIn(SENTINEL, plan["rendered"])
