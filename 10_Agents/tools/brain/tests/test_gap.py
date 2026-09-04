"""§29.3 `brain gap`: the vault-answer gap queue never takes multiline or
Markdown-active text, never lists a restricted note's title, and routes
sensitive or autonomous rows to Inbox captures instead of the public queue."""

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
from test_triage_trace import CONVENTIONS, note  # noqa: E402

TODAY = date(2026, 9, 1)
QUEUE = "10_Agents/docs/vault-answer-gaps.md"
QUEUE_TEXT = (
    '---\ntitle: "Vault Answer Gaps"\ntags:\n  - type/log\n  - audience/agent\nupdated: 2026-08-11\n---\n\n'
    "# Vault Answer Gaps\n\nIntro.\n\n## Open and filled gaps\n\n## Related\n\n- nothing\n"
)


def files():
    return {
        "00_Meta/CONVENTIONS.md": CONVENTIONS,
        QUEUE: QUEUE_TEXT,
        "06_Resources/public.md": note("Public Reference"),
        "05_Areas/health/private.md": note("Diagnosis And Dosage", tags=("type/note", "restricted/private")),
    }


def run_cli(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(brain, "vault_today", return_value=TODAY):
        code = brain.main([*argv, "--vault", str(root)])
    return code, out.getvalue(), err.getvalue()


class GapTests(unittest.TestCase):
    def test_plain_gap_appends_one_sanitized_row(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            code, out, err = run_cli(root, "gap", "--question", "What is the Q4 plan?", "--term", "q4", "--term", "plan `x`", "--nearest", "06_Resources/public.md", "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual((data["action"], data["path"], data["sensitive"]), ("append", QUEUE, False))
            text = (root / QUEUE).read_text(encoding="utf-8")
            self.assertRegex(
                text,
                r"## Open and filled gaps\n\n- \[ \] 2026-09-01 — What is the Q4 plan\? — searched: `q4`, `plan 'x'` — nearest: "
                r"\[Public Reference\]\(\.\./\.\./06_Resources/public\.md\) <!-- gap: [0-9a-f]{16} -->\n\n## Related",
            )
            # The same question the same day is one row, however often it is logged.
            code, out, _ = run_cli(root, "gap", "--question", "What is the Q4 plan?", "--write", "--json")
            self.assertEqual((code, json.loads(out)["action"]), (0, "skip"))
            self.assertEqual((root / QUEUE).read_text(encoding="utf-8").count("What is the Q4 plan?"), 1)
            self.assertIn("updated: 2026-09-01", text)
            self.assertEqual(data["validation"]["errors"], [])
            # Preview mode never writes.
            before = (root / QUEUE).read_bytes()
            code, _, _ = run_cli(root, "gap", "--question", "Another?")
            self.assertEqual(code, 0)
            self.assertEqual((root / QUEUE).read_bytes(), before)

    def test_multiline_and_markdown_injection_cannot_change_queue_structure(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            question = "first line\n\n## Injected heading\n- [x] fake done\n```\ncode\n```\n[link](../../etc/passwd) <script> `tick` --> end"
            code, out, err = run_cli(root, "gap", "--question", question, "--write")
            self.assertEqual(code, 0, err)
            text = (root / QUEUE).read_text(encoding="utf-8")
            rows = [l for l in text.split("\n") if l.startswith("- [ ] 2026-09-01")]
            self.assertEqual(len(rows), 1)
            self.assertEqual(text.count("\n## "), 2)  # the two original sections only
            self.assertNotIn("\n```", text)
            self.assertNotIn("- [x] fake done", text)
            self.assertNotIn("[link](", text)
            self.assertIn("\\[link\\](../../etc/passwd) \\<script\\> \\`tick\\` --\\> end", rows[0])
            self.assertIn("first line ## Injected heading - \\[x\\] fake done \\`\\`\\` code \\`\\`\\` ", rows[0])
            errors, _ = brain.run_validate(root, check_index=False)
            self.assertEqual([e for e in errors if e["path"] == QUEUE], [])
            long = "x" * 1000
            code, out, _ = run_cli(root, "gap", "--question", long, "--json")
            self.assertLessEqual(len(json.loads(out)["row"]), brain.GAP_QUESTION_MAX + 80)

    def test_sensitive_source_routes_to_restricted_capture_without_title_leak(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            before = (root / QUEUE).read_bytes()
            code, out, err = run_cli(root, "gap", "--question", "What dosage was I prescribed?", "--term", "dosage", "--nearest", "05_Areas/health/private.md", "--nearest", "06_Resources/public.md", "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual((data["action"], data["sensitive"], data["restricted"]), ("capture", True, True))
            self.assertEqual(data["path"], "02_Inbox/2026-09-01-vault-answer-gap.md")
            self.assertEqual((root / QUEUE).read_bytes(), before, "the public queue is untouched")
            capture = (root / data["path"]).read_text(encoding="utf-8")
            self.assertIn("  - restricted/private\n", capture)
            self.assertIn("[private.md](../05_Areas/health/private.md)", capture)
            self.assertNotIn("Diagnosis And Dosage", capture)
            self.assertIn("[Public Reference](../06_Resources/public.md)", capture)
            self.assertIn("What dosage was I prescribed?", capture)
            self.assertEqual(data["validation"]["errors"], [])
            # A second sensitive gap the same day gets its own capture.
            code, out, _ = run_cli(root, "gap", "--question", "Second?", "--sensitive", "--write", "--json")
            self.assertEqual(json.loads(out)["path"], "02_Inbox/2026-09-01-vault-answer-gap-2.md")
            self.assertIn("  - restricted/private\n", (root / "02_Inbox/2026-09-01-vault-answer-gap-2.md").read_text(encoding="utf-8"))

    def test_autonomous_inbox_route_is_not_restricted_unless_sensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            before = (root / QUEUE).read_bytes()
            code, out, err = run_cli(root, "gap", "--question", "Plain?", "--nearest", "06_Resources/public.md", "--inbox", "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual((data["action"], data["sensitive"], data["restricted"]), ("capture", False, False))
            capture = (root / data["path"]).read_text(encoding="utf-8")
            self.assertNotIn("restricted/private", capture)
            self.assertIn("- [ ] 2026-09-01 — Plain? — searched: — — nearest: [Public Reference](../06_Resources/public.md) <!-- gap: ", capture)
            self.assertEqual((root / QUEUE).read_bytes(), before)

    def test_missing_nearest_or_empty_question_is_an_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            self.assertEqual(run_cli(root, "gap", "--question", "Q?", "--nearest", "06_Resources/nope.md")[0], 1)
            self.assertEqual(run_cli(root, "gap", "--question", "  \n ")[0], 1)
            self.assertEqual(run_cli(root, "gap", "--question", "Q?", "--nearest", "../outside.md")[0], 1)


ACCEPTED_LOG = "10_Agents/docs/accepted-proposals.md"
ACCEPTED_TEXT = (
    '---\ntitle: "Accepted Proposals"\ntags:\n  - type/log\n  - audience/agent\nupdated: 2026-08-11\n---\n\n'
    "# Accepted Proposals\n\nIntro.\n\n| Date | Proposal | What changed | Verification owed |\n|------|----------|--------------|-------------------|\n"
    "| 2026-08-20 | [old](../skills/vault-answer/SKILL.md) | done | none |\n\n## Related\n\n- nothing\n"
)
RETRO = (
    '---\ntitle: "Spec Retrospective — 2026-09-01"\ntags:\n  - type/log\n  - audience/agent\n  - workflow/draft\nupdated: 2026-09-01\nauthor: claude-code\n---\n\n'
    "# Spec Retrospective — 2026-09-01\n\n## Evidence\n\nStuff.\n\n## Accepted proposals\n\n"
    "| Date | Proposal | What changed | Verification owed |\n|---|---|---|---|\n"
    "| 2026-09-01 | [gap queue](../10_Agents/skills/vault-answer/SKILL.md) | rows appear | check next cycle |\n"
    "| 2026-08-20 | [old](../10_Agents/skills/vault-answer/SKILL.md) | done | none |\n\n## Next\n\n| not | a | log | row |\n"
)


class IngestionRoundTripTests(unittest.TestCase):
    """R7: autonomous rows travel Inbox -> log through idempotent ingestion."""

    def files(self):
        data = files()
        data[ACCEPTED_LOG] = ACCEPTED_TEXT
        data["10_Agents/skills/vault-answer/SKILL.md"] = (
            "---\nname: vault-answer\ndescription: Answer.\ntitle: \"Skill: Vault Answer\"\ntags:\n  - type/reference\nupdated: 2026-08-11\n---\n\n# Vault Answer\n"
        )
        return data

    def test_gap_capture_round_trip_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files())
            code, out, err = run_cli(root, "gap", "--question", "Autonomous?", "--nearest", "06_Resources/public.md", "--inbox", "--write", "--json")
            self.assertEqual(code, 0, err)
            capture = json.loads(out)["path"]
            queue_before = (root / QUEUE).read_bytes()
            code, out, err = run_cli(root, "gap", "--ingest", capture, "--json")
            self.assertEqual(code, 0, err)
            self.assertEqual(len(json.loads(out)["ingested"]), 1)
            self.assertTrue((root / capture).exists(), "preview never writes")
            self.assertEqual((root / QUEUE).read_bytes(), queue_before)
            code, out, err = run_cli(root, "gap", "--ingest", capture, "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual((len(data["ingested"]), data["skipped"], data["validation"]["errors"]), (1, [], []))
            self.assertFalse((root / capture).exists())
            text = (root / QUEUE).read_text(encoding="utf-8")
            self.assertEqual(text.count("— Autonomous? —"), 1)
            self.assertIn("nearest: [Public Reference](../../06_Resources/public.md) <!-- gap: ", text, "links rebased to the queue's directory")
            self.assertIn("updated: 2026-09-01", text)
            # A second, identical autonomous capture (same day, same question) ingests as a skip.
            code, out, _ = run_cli(root, "gap", "--question", "Autonomous?", "--nearest", "06_Resources/public.md", "--inbox", "--write", "--json")
            capture2 = json.loads(out)["path"]
            after = (root / QUEUE).read_bytes()
            code, out, err = run_cli(root, "gap", "--ingest", capture2, "--write", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual((data["ingested"], len(data["skipped"])), ([], 1))
            self.assertEqual((root / QUEUE).read_bytes(), after)
            self.assertFalse((root / capture2).exists())
            # A direct interactive append of the same question is also a skip.
            code, out, _ = run_cli(root, "gap", "--question", "Autonomous?", "--nearest", "06_Resources/public.md", "--write", "--json")
            self.assertEqual(json.loads(out)["action"], "skip")

    def test_restricted_capture_needs_explicit_declassification(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files())
            code, out, _ = run_cli(root, "gap", "--question", "Dosage?", "--nearest", "05_Areas/health/private.md", "--write", "--json")
            capture = json.loads(out)["path"]
            queue_before = (root / QUEUE).read_bytes()
            code, _, err = run_cli(root, "gap", "--ingest", capture, "--write")
            self.assertEqual(code, 1)
            self.assertIn("--declassify", err)
            self.assertTrue((root / capture).exists())
            self.assertEqual((root / QUEUE).read_bytes(), queue_before)
            code, out, err = run_cli(root, "gap", "--ingest", capture, "--declassify", "--write", "--json")
            self.assertEqual(code, 0, err)
            self.assertTrue(json.loads(out)["declassified"])
            text = (root / QUEUE).read_text(encoding="utf-8")
            self.assertIn("— Dosage? —", text)
            self.assertIn("[private.md](../../05_Areas/health/private.md)", text)
            self.assertNotIn("Diagnosis And Dosage", text)
            self.assertFalse((root / capture).exists())

    def test_ingest_rejects_foreign_captures_and_bad_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files())
            (root / "02_Inbox").mkdir(exist_ok=True)
            (root / "02_Inbox/2026-09-01-other.md").write_text(note("Other"), encoding="utf-8")
            self.assertEqual(run_cli(root, "gap", "--ingest", "02_Inbox/2026-09-01-other.md", "--write")[0], 1)
            self.assertEqual(run_cli(root, "gap", "--ingest", "06_Resources/public.md", "--write")[0], 1)
            self.assertEqual(run_cli(root, "gap", "--ingest", "02_Inbox/nope.md", "--write")[0], 1)
            self.assertEqual(run_cli(root, "gap", "--write")[0], 1)
            self.assertEqual(run_cli(root, "gap", "--question", "Q?", "--ingest", "02_Inbox/x.md")[0], 1)

    def test_accepted_rows_round_trip_is_idempotent(self):
        data = self.files()
        data["02_Inbox/2026-09-01-spec-retrospective.md"] = RETRO
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), data)
            log_before = (root / ACCEPTED_LOG).read_bytes()
            code, out, err = run_cli(root, "accepted", "--ingest", "02_Inbox/2026-09-01-spec-retrospective.md", "--json")
            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual((len(data["ingested"]), len(data["skipped"])), (1, 1), "the already-present row is skipped after link rebasing")
            self.assertEqual((root / ACCEPTED_LOG).read_bytes(), log_before, "preview never writes")
            code, out, err = run_cli(root, "accepted", "--ingest", "02_Inbox/2026-09-01-spec-retrospective.md", "--write", "--json")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["validation"]["errors"], [])
            text = (root / ACCEPTED_LOG).read_text(encoding="utf-8")
            self.assertIn(
                "| 2026-08-20 | [old](../skills/vault-answer/SKILL.md) | done | none |\n"
                "| 2026-09-01 | [gap queue](../skills/vault-answer/SKILL.md) | rows appear | check next cycle |\n\n## Related",
                text,
            )
            self.assertNotIn("| not | a | log | row |", text)
            self.assertIn("updated: 2026-09-01", text)
            self.assertTrue((root / "02_Inbox/2026-09-01-spec-retrospective.md").exists(), "the report is left for triage")
            after = (root / ACCEPTED_LOG).read_bytes()
            code, out, _ = run_cli(root, "accepted", "--ingest", "02_Inbox/2026-09-01-spec-retrospective.md", "--write", "--json")
            self.assertEqual((code, json.loads(out)["ingested"]), (0, []))
            self.assertEqual((root / ACCEPTED_LOG).read_bytes(), after)
            # A restricted report and a report without the section are refused.
            (root / "02_Inbox/2026-09-01-spec-retrospective.md").write_text(RETRO.replace("  - workflow/draft\n", "  - workflow/draft\n  - restricted/private\n"), encoding="utf-8")
            self.assertEqual(run_cli(root, "accepted", "--ingest", "02_Inbox/2026-09-01-spec-retrospective.md", "--write")[0], 1)
            (root / "02_Inbox/2026-09-01-spec-retrospective.md").write_text(RETRO.replace("## Accepted proposals", "## Nope"), encoding="utf-8")
            self.assertEqual(run_cli(root, "accepted", "--ingest", "02_Inbox/2026-09-01-spec-retrospective.md", "--write")[0], 1)
            self.assertEqual((root / ACCEPTED_LOG).read_bytes(), after)


if __name__ == "__main__":
    unittest.main()
