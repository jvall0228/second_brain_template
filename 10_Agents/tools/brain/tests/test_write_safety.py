"""§29 write safety: archive identity by full marker (R1) and the vault
write lock plus compare-and-swap that make concurrent triage-archive, trace,
and gap invocations keep every accepted record exactly once (R2)."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402
from test_brain import make_vault  # noqa: E402
from test_gap import QUEUE, QUEUE_TEXT  # noqa: E402
from test_triage_trace import REPORT, TODAY, base_files, run_cli  # noqa: E402

BRAIN = Path(__file__).resolve().parents[1] / "brain.py"
REPORT_REL = "02_Inbox/2026-08-30-triage-report.md"
LOG = "07_Archives/inbox/2026-08-triage-log.md"


def files():
    data = base_files()
    data[QUEUE] = QUEUE_TEXT
    return data


class ArchiveIdentityTests(unittest.TestCase):
    def archive(self, root, *extra):
        return run_cli(root, "triage-archive", REPORT_REL, "--write", "--json", *extra)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO required")
    def test_fifo_source_is_refused_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            source = root / REPORT_REL
            source.unlink()
            os.mkfifo(source)
            result = subprocess.run([
                sys.executable, str(BRAIN), "triage-archive", REPORT_REL,
                "--write", "--vault", str(root),
            ], capture_output=True, text=True, timeout=2)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue(source.exists())
            self.assertFalse((root / LOG).exists())

    def test_changed_report_after_completed_archive_is_a_conflict_until_revised(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (0, "create"))
            log_after_first = (root / LOG).read_bytes()
            changed = REPORT.replace("Done.", "Done, with a late correction.")
            (root / REPORT_REL).write_text(changed, encoding="utf-8")
            code, out, _ = self.archive(root)
            data = json.loads(out)
            self.assertEqual((code, data["action"], data["priorVersions"]), (1, "conflict", 1))
            self.assertIn("--revise", data["conflict"])
            self.assertEqual((root / REPORT_REL).read_text(encoding="utf-8"), changed, "source retained")
            self.assertEqual((root / LOG).read_bytes(), log_after_first, "log untouched")
            # Preview mode reports the same conflict without --write.
            code, out, _ = run_cli(root, "triage-archive", REPORT_REL, "--json")
            self.assertEqual((code, json.loads(out)["action"]), (1, "conflict"))
            code, out, _ = self.archive(root, "--revise")
            self.assertEqual((code, json.loads(out)["action"]), (0, "append"))
            log = (root / LOG).read_text(encoding="utf-8")
            self.assertEqual(len(brain._marker_values(log, brain.TRIAGE_ARCHIVE_MARKER)), 2)
            self.assertIn("## 2026-08-30 — Triage Report — 2026-08-30 (revision 2)\n", log)
            self.assertIn("Done, with a late correction.", log)
            self.assertFalse((root / REPORT_REL).exists())
            # Exact-byte retry after the revision is done, not a conflict.
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (0, "done"))

    def test_changed_report_after_interrupted_append_is_a_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            (root / LOG).parent.mkdir(parents=True)
            (root / LOG).write_text(plan["rendered"], encoding="utf-8")
            log_after_append = (root / LOG).read_bytes()
            # Exact bytes: the retry only finishes the delete.
            code, out, _ = run_cli(root, "triage-archive", REPORT_REL, "--json")
            self.assertEqual(json.loads(out)["action"], "delete-only")
            # Changed bytes before the retry: nothing is deleted.
            (root / REPORT_REL).write_text(REPORT.replace("Done.", "Edited."), encoding="utf-8")
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (1, "conflict"))
            self.assertTrue((root / REPORT_REL).exists())
            self.assertEqual((root / LOG).read_bytes(), log_after_append)

    def test_restricted_archive_collision_is_a_conflict_and_exact_retry_finishes(self):
        data = files()
        restricted = REPORT.replace("  - workflow/review\n", "  - workflow/review\n  - restricted/private\n")
        data[REPORT_REL] = restricted
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), data)
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (0, "move"))
            archived = root / "07_Archives/inbox/2026-08-30-triage-report.md"
            moved = archived.read_text(encoding="utf-8")
            self.assertEqual(len(brain._marker_values(moved, brain.TRIAGE_ARCHIVE_MARKER)), 1)
            self.assertIn("# Triage Report — 2026-08-30\n\n<!-- triage-archive: 02_Inbox/2026-08-30-triage-report.md sha256:", moved)
            # Same path, changed bytes: conflict, archived note untouched, source kept.
            (root / REPORT_REL).write_text(restricted.replace("Done.", "Edited."), encoding="utf-8")
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (1, "conflict"))
            self.assertEqual(archived.read_text(encoding="utf-8"), moved)
            self.assertTrue((root / REPORT_REL).exists())
            # Same path, exact original bytes (an interrupted move): delete only.
            (root / REPORT_REL).write_text(restricted, encoding="utf-8")
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (0, "delete-only"))
            self.assertFalse((root / REPORT_REL).exists())
            self.assertEqual(archived.read_text(encoding="utf-8"), moved)
            # A pre-existing archived note without a marker is never overwritten.
            archived.write_text(moved.split("<!-- triage-archive")[0] + "Legacy archive.\n", encoding="utf-8")
            (root / REPORT_REL).write_text(restricted, encoding="utf-8")
            code, out, _ = self.archive(root)
            self.assertEqual((code, json.loads(out)["action"]), (1, "conflict"))
            self.assertTrue((root / REPORT_REL).exists())

    def test_source_replaced_between_plan_and_delete_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            (root / REPORT_REL).write_text(REPORT.replace("Done.", "Swapped."), encoding="utf-8")
            with self.assertRaises(brain.WriteConflictError):
                brain.apply_triage_archive(root, plan)
            self.assertTrue((root / REPORT_REL).exists())


class SourceRemovalSafetyTests(unittest.TestCase):
    def test_archive_refuses_symlinked_inbox_without_touching_external_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td) / "vault", files())
            external = Path(td) / "external"
            (root / "02_Inbox").rename(external)
            (root / "02_Inbox").symlink_to(external, target_is_directory=True)
            before = (external / Path(REPORT_REL).name).read_bytes()
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
            self.assertEqual(code, 1, out + err)
            self.assertEqual((external / Path(REPORT_REL).name).read_bytes(), before)
            self.assertFalse((root / LOG).exists())

    def test_archive_refuses_final_symlink_in_preview_and_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td) / "vault", files())
            external = Path(td) / "report.md"
            (root / REPORT_REL).rename(external)
            (root / REPORT_REL).symlink_to(external)
            for flags in ((), ("--write",)):
                code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--json", *flags)
                self.assertEqual(code, 1, out + err)
            self.assertEqual(external.read_text(), REPORT)

    def test_same_bytes_replacement_after_planning_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            source = root / REPORT_REL
            replacement = source.with_suffix(".replacement")
            replacement.write_bytes(source.read_bytes())
            replacement.replace(source)
            with self.assertRaises(brain.WriteConflictError):
                brain.apply_triage_archive(root, plan)
            self.assertEqual(source.read_text(), REPORT)


    def gap_capture(self, root):
        plan = brain.gap_plan(root, day=TODAY, question="Synthetic audit question?", terms=[], nearest=[], sensitive=False, inbox=True)
        (root / plan["path"]).write_text(plan["rendered"], encoding="utf-8")
        return plan["path"]

    def test_gap_ingestion_refuses_symlinked_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td) / "vault", files())
            capture = self.gap_capture(root)
            external = Path(td) / "external"
            (root / "02_Inbox").rename(external)
            (root / "02_Inbox").symlink_to(external, target_is_directory=True)
            code, out, err = run_cli(root, "gap", "--ingest", capture, "--write", "--json")
            self.assertEqual(code, 1, out + err)
            self.assertTrue((external / Path(capture).name).exists())
            self.assertEqual((root / QUEUE).read_text(), QUEUE_TEXT)

    def test_parent_replacement_after_planning_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            (root / "02_Inbox").rename(root / "saved-inbox")
            (root / "02_Inbox").mkdir()
            (root / REPORT_REL).write_text(REPORT)
            with self.assertRaises(brain.WriteConflictError):
                brain.apply_triage_archive(root, plan)
            self.assertEqual((root / REPORT_REL).read_text(), REPORT)
            self.assertTrue((root / "saved-inbox" / Path(REPORT_REL).name).exists())
            self.assertFalse((root / LOG).exists())

    def test_replacement_at_claim_is_restored_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            real_rename = brain._rename_external_at
            replacement = REPORT.replace("Done.", "Replacement.")
            def replace_before_claim(parent, source, target, **kwargs):
                if source == Path(REPORT_REL).name and target.endswith(".source"):
                    temporary = root / "02_Inbox/new-file"
                    temporary.write_text(replacement)
                    temporary.replace(root / REPORT_REL)
                return real_rename(parent, source, target, **kwargs)
            with mock.patch.object(brain, "_rename_external_at", side_effect=replace_before_claim):
                with self.assertRaises(brain.WriteConflictError):
                    brain.apply_triage_archive(root, plan)
            self.assertEqual((root / REPORT_REL).read_text(), replacement)
            self.assertEqual(list(root.rglob(".brain-note-removal-*")), [])

    def test_original_name_recreation_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            real_rename = brain._rename_external_at
            replacement = REPORT.replace("Done.", "New owner report.")
            def recreate_after_claim(parent, source, target, **kwargs):
                result = real_rename(parent, source, target, **kwargs)
                if source == Path(REPORT_REL).name and target.endswith(".source"):
                    (root / REPORT_REL).write_text(replacement)
                return result
            with mock.patch.object(brain, "_rename_external_at", side_effect=recreate_after_claim):
                brain.apply_triage_archive(root, plan)
            self.assertEqual((root / REPORT_REL).read_text(), replacement)
            self.assertEqual(len(brain._marker_values((root / LOG).read_text(), brain.TRIAGE_ARCHIVE_MARKER)), 1)
            self.assertEqual(list(root.rglob(".brain-note-removal-*")), [])

    def test_restore_collision_preserves_both_replacements_and_recovery_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            real_rename = brain._rename_external_at
            first = REPORT.replace("Done.", "First replacement.")
            second = REPORT.replace("Done.", "Second replacement.")
            def collide(parent, source, target, **kwargs):
                if source == Path(REPORT_REL).name and target.endswith(".source"):
                    temporary = root / "02_Inbox/new-file"
                    temporary.write_text(first)
                    temporary.replace(root / REPORT_REL)
                    result = real_rename(parent, source, target, **kwargs)
                    (root / REPORT_REL).write_text(second)
                    return result
                return real_rename(parent, source, target, **kwargs)
            with mock.patch.object(brain, "_rename_external_at", side_effect=collide):
                with self.assertRaisesRegex(brain.WriteConflictError, "recovery required"):
                    brain.apply_triage_archive(root, plan)
            self.assertEqual((root / REPORT_REL).read_text(), second)
            claims = list((root / "02_Inbox").glob(".brain-note-removal-*.source"))
            self.assertEqual([p.read_text() for p in claims], [first])
            self.assertEqual(len(list(root.glob(".brain-note-removal-*.json"))), 1)
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
            self.assertEqual(code, 1, out + err)
            self.assertIn("recovery required", out)
            self.assertEqual((root / REPORT_REL).read_text(), second)
            self.assertEqual(claims[0].read_text(), first)

    def test_parent_changed_after_claim_preserves_held_evidence_and_new_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            real_rename = brain._rename_external_at
            def move_parent(parent, source, target, **kwargs):
                result = real_rename(parent, source, target, **kwargs)
                if source == Path(REPORT_REL).name and target.endswith(".source"):
                    (root / "02_Inbox").rename(root / "saved-inbox")
                    (root / "02_Inbox").mkdir()
                    (root / REPORT_REL).write_text(REPORT)
                return result
            with mock.patch.object(brain, "_rename_external_at", side_effect=move_parent):
                with self.assertRaisesRegex(brain.WriteConflictError, "parent changed"):
                    brain.apply_triage_archive(root, plan)
            self.assertEqual((root / REPORT_REL).read_text(), REPORT)
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
            self.assertEqual(code, 1, out + err)
            self.assertIn("recovery required", out)
            self.assertEqual((root / REPORT_REL).read_text(), REPORT)
            self.assertEqual([p.read_text() for p in (root / "saved-inbox").glob("*.source")], [REPORT])

    def crash_claim(self, root, argv, *, before=False):
        code = (
            "import os,sys\nfrom pathlib import Path\n"
            "sys.path.insert(0, sys.argv[1])\nimport brain\nfrom datetime import date\nbrain.vault_today = lambda config: date(2026, 9, 1)\n"
            "original = brain._rename_external_at\n"
            "def crash(parent, source, target, **kwargs):\n"
            + ("    if target.endswith('.source'): os._exit(91)\n" if before else "")
            + "    result = original(parent, source, target, **kwargs)\n"
            + ("" if before else "    if target.endswith('.source'): os._exit(91)\n")
            + "    return result\n"
            "brain._rename_external_at = crash\n"
            "raise SystemExit(brain.main(sys.argv[2:]))\n"
        )
        result = subprocess.run([sys.executable, "-c", code, str(BRAIN.parent), *argv, "--vault", str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 91, result.stdout + result.stderr)

    def test_process_termination_after_claim_recovers_public_and_private_archive(self):
        for restricted in (False, True):
            with self.subTest(restricted=restricted), tempfile.TemporaryDirectory() as td:
                data = files()
                if restricted:
                    data[REPORT_REL] = REPORT.replace("  - workflow/review", "  - restricted/private\n  - workflow/review")
                root = make_vault(Path(td), data)
                self.crash_claim(root, ["triage-archive", REPORT_REL, "--write", "--json"])
                self.assertFalse((root / REPORT_REL).exists())
                self.assertEqual(len(list((root / "02_Inbox").glob(".brain-note-removal-*.source"))), 1)
                code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
                self.assertEqual(code, 0, out + err)
                self.assertEqual(json.loads(out)["action"], "delete-only")
                archived = root / ("07_Archives/inbox/" + Path(REPORT_REL).name) if restricted else root / LOG
                self.assertEqual(len(brain._marker_values(archived.read_text(), brain.TRIAGE_ARCHIVE_MARKER)), 1)
                self.assertFalse((root / REPORT_REL).exists())
                self.assertEqual(list(root.rglob(".brain-note-removal-*")), [])

    def test_process_termination_before_claim_recovers_prepared_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            self.crash_claim(root, ["triage-archive", REPORT_REL, "--write", "--json"], before=True)
            self.assertTrue((root / REPORT_REL).exists())
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
            self.assertEqual(code, 0, out + err)
            self.assertFalse((root / REPORT_REL).exists())
            self.assertEqual(list(root.rglob(".brain-note-removal-*")), [])

    def test_process_termination_after_gap_claim_recovers_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            capture = self.gap_capture(root)
            self.crash_claim(root, ["gap", "--ingest", capture, "--write", "--json"])
            self.assertFalse((root / capture).exists())
            code, out, err = run_cli(root, "gap", "--ingest", capture, "--write", "--json")
            self.assertEqual(code, 0, out + err)
            result = json.loads(out)
            self.assertEqual(result["ingested"], [])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual((root / QUEUE).read_text().count("Synthetic audit question?"), 1)
            self.assertEqual(list(root.rglob(".brain-note-removal-*")), [])

    def test_unsupported_removal_allows_preview_and_refuses_before_destination_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            with mock.patch.object(brain.note_removal, "require_supported", side_effect=brain.note_removal.RemovalError("unsupported safe removal")):
                code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--json")
                self.assertEqual(code, 0, out + err)
                code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
                self.assertEqual(code, 1, out + err)
            self.assertEqual((root / REPORT_REL).read_text(), REPORT)
            self.assertFalse((root / LOG).exists())


    def test_retry_preserves_recreated_original_and_hides_private_claim_from_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            data = files()
            data[REPORT_REL] = REPORT.replace("  - workflow/review", "  - restricted/private\n  - workflow/review")
            root = make_vault(Path(td), data)
            self.crash_claim(root, ["triage-archive", REPORT_REL, "--write", "--json"])
            notes, assets = brain.walk_corpus(root)
            self.assertFalse(any(".brain-note-removal-" in path for path in notes + assets))
            replacement = REPORT.replace("Done.", "A newly captured report.")
            (root / REPORT_REL).write_text(replacement)
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
            self.assertEqual(code, 0, out + err)
            self.assertEqual(json.loads(out)["action"], "delete-only")
            self.assertEqual((root / REPORT_REL).read_text(), replacement)
            self.assertEqual(list(root.rglob(".brain-note-removal-*")), [])

    def test_malformed_recovery_record_is_refused_without_deleting_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            self.crash_claim(root, ["triage-archive", REPORT_REL, "--write", "--json"])
            record = next(root.glob(".brain-note-removal-*.json"))
            claim = next((root / "02_Inbox").glob(".brain-note-removal-*.source"))
            data = json.loads(record.read_text())
            data["quarantine"] = "../unrelated.md"
            record.write_text(json.dumps(data))
            before = record.read_bytes()
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--write", "--json")
            self.assertEqual(code, 1, out + err)
            self.assertIn("recovery required", out)
            self.assertEqual(record.read_bytes(), before)
            self.assertEqual(claim.read_text(), REPORT)

    def test_absent_source_and_claim_with_remaining_record_requires_inspection(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            plan = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            with mock.patch.object(brain.note_removal, "_discard_record", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    brain.apply_triage_archive(root, plan)
            self.assertFalse((root / REPORT_REL).exists())
            self.assertEqual(list((root / "02_Inbox").glob(".brain-note-removal-*.source")), [])
            code, out, err = run_cli(root, "triage-archive", REPORT_REL, "--json")
            self.assertEqual(code, 1, out + err)
            self.assertIn("recovery required", out)
            self.assertEqual(len(list(root.glob(".brain-note-removal-*.json"))), 1)
            self.assertEqual(len(brain._marker_values((root / LOG).read_text(), brain.TRIAGE_ARCHIVE_MARKER)), 1)


class CompareAndSwapTests(unittest.TestCase):
    """Two plans computed from the same state: the second apply is refused,
    and a recomputed plan lands both records exactly once."""

    def second_report(self):
        return REPORT.replace("2026-08-30", "2026-08-31").replace("2026-08-31-other.md", "2026-08-30-other.md")

    def test_archive_plans_do_not_overwrite_each_other(self):
        data = files()
        data["02_Inbox/2026-08-31-triage-report.md"] = self.second_report()
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), data)
            first = brain.triage_archive_plan(root, REPORT_REL, TODAY)
            second = brain.triage_archive_plan(root, "02_Inbox/2026-08-31-triage-report.md", TODAY)
            brain.apply_triage_archive(root, first)
            with self.assertRaises(brain.WriteConflictError):
                brain.apply_triage_archive(root, second)
            self.assertTrue((root / "02_Inbox/2026-08-31-triage-report.md").exists(), "second source not deleted")
            second = brain.triage_archive_plan(root, "02_Inbox/2026-08-31-triage-report.md", TODAY)
            brain.apply_triage_archive(root, second)
            log = (root / LOG).read_text(encoding="utf-8")
            markers = brain._marker_values(log, brain.TRIAGE_ARCHIVE_MARKER)
            self.assertEqual(sorted(m.split(" sha256:")[0] for m in markers), [REPORT_REL, "02_Inbox/2026-08-31-triage-report.md"])
            self.assertEqual(log.count("## 2026-08-3"), 2)

    def test_trace_plans_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            kwargs = dict(day=TODAY.replace(day=20, month=8), destination="05_Areas/x.md", summary="S", kind=None, today_d=TODAY)
            first = brain.trace_plan(root, identity="one", **kwargs)
            second = brain.trace_plan(root, identity="two", **kwargs)
            brain.apply_trace(root, first)
            with self.assertRaises(brain.WriteConflictError):
                brain.apply_trace(root, second)
            second = brain.trace_plan(root, identity="two", **kwargs)
            brain.apply_trace(root, second)
            for rel in (first["notes"][0]["path"], first["notes"][1]["path"]):
                text = (root / rel).read_text(encoding="utf-8")
                self.assertEqual(sorted(brain._marker_values(text, brain.TRACE_MARKER)), ["one", "two"])

    def test_gap_plans_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            kwargs = dict(day=TODAY, terms=[], nearest=[], sensitive=False, inbox=False)
            first = brain.gap_plan(root, question="First?", **kwargs)
            second = brain.gap_plan(root, question="Second?", **kwargs)
            brain._write_note_atomic(root, first["path"], first["rendered"].encode("utf-8"), expected=first["base"])
            with self.assertRaises(brain.WriteConflictError):
                brain._write_note_atomic(root, second["path"], second["rendered"].encode("utf-8"), expected=second["base"])
            second = brain.gap_plan(root, question="Second?", **kwargs)
            brain._write_note_atomic(root, second["path"], second["rendered"].encode("utf-8"), expected=second["base"])
            text = (root / QUEUE).read_text(encoding="utf-8")
            self.assertEqual(text.count("- [ ] 2026-09-01 — First?"), 1)
            self.assertEqual(text.count("- [ ] 2026-09-01 — Second?"), 1)


class ConcurrentProcessTests(unittest.TestCase):
    """Real concurrent CLI processes released together: the vault write lock
    serializes them, and every record survives exactly once."""

    def launch(self, root, argv_list):
        env = dict(os.environ)
        procs = [
            subprocess.Popen([sys.executable, str(BRAIN), *argv, "--vault", str(root)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for argv in argv_list
        ]
        results = [(p.wait(timeout=120), *p.communicate()) for p in procs]
        for code, out, err in results:
            self.assertEqual(code, 0, out + err)
        return results

    def test_concurrent_archives_traces_and_gaps_keep_every_record_once(self):
        data = files()
        data["02_Inbox/2026-08-31-triage-report.md"] = CompareAndSwapTests().second_report()
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), data)
            self.launch(root, [
                ["triage-archive", REPORT_REL, "--write"],
                ["triage-archive", "02_Inbox/2026-08-31-triage-report.md", "--write"],
            ])
            log = (root / LOG).read_text(encoding="utf-8")
            self.assertEqual(len(brain._marker_values(log, brain.TRIAGE_ARCHIVE_MARKER)), 2)
            self.assertFalse((root / REPORT_REL).exists())
            self.assertFalse((root / "02_Inbox/2026-08-31-triage-report.md").exists())

            base = ["trace", "--date", "2026-08-20", "--destination", "05_Areas/x.md", "--write"]
            self.launch(root, [
                [*base, "--summary", "A", "--id", "id-a"],
                [*base, "--summary", "B", "--id", "id-b"],
                [*base, "--summary", "C", "--id", "id-c"],
            ])
            for rel in ("03_Journal/periodic/daily/2026-08-20.md", "03_Journal/periodic/weekly/2026-W34-review.md"):
                text = (root / rel).read_text(encoding="utf-8")
                self.assertEqual(sorted(brain._marker_values(text, brain.TRACE_MARKER)), ["id-a", "id-b", "id-c"], rel)

            gap_argv = [ ["gap", "--question", f"Question {n}?", "--write"] for n in range(4)]
            self.launch(root, gap_argv)
            text = (root / QUEUE).read_text(encoding="utf-8")
            for n in range(4):
                self.assertEqual(text.count(f"— Question {n}? —"), 1)

    def test_lock_reports_a_stray_second_brain_file_as_a_command_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            (root / ".second-brain").write_text("some-env\n", encoding="utf-8")
            with self.assertRaises(brain.NoteWriteError):
                with brain.vault_write_lock(root):
                    pass
            code, _, err = run_cli(root, "gap", "--question", "Q?", "--write")
            self.assertEqual(code, 1)
            self.assertIn("write lock", err)
            self.assertEqual((root / ".second-brain").read_text(encoding="utf-8"), "some-env\n")

    def test_lock_is_reentrant_within_one_process(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files())
            with brain.vault_write_lock(root):
                with brain.vault_write_lock(root):
                    # The compare-and-swap writer takes the lock itself; a
                    # caller already holding it must not deadlock.
                    brain._write_note_atomic(root, "05_Areas/y.md", b"---\ntitle: Y\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n", expected=None)
            self.assertTrue((root / "05_Areas/y.md").is_file())
            self.assertEqual(brain._WRITE_LOCK_DEPTH.get(os.path.realpath(root)), None)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_lock_refuses_symlinked_second_brain_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "vault"
            root.mkdir()
            elsewhere = Path(td) / "elsewhere"
            elsewhere.mkdir()
            os.symlink(elsewhere, root / ".second-brain")
            with self.assertRaises(brain.NoteWriteError):
                with brain.vault_write_lock(root):
                    pass
            self.assertEqual(list(elsewhere.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
