"""Derived classification preserves local use and explicit public-only synthesis."""

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
from test_bootstrap import bootstrap_files, doc
from test_brain import make_vault
from test_home import HomeVault, UNCONFIGURED, note


def indexed(root):
    notes, assets = brain.walk_corpus(root, selected_environment=None)
    return brain.build_index(root, notes, assets)


def derived_note(title, body, sources):
    return note(title, body).replace("updated:", "privacy-sources: " + json.dumps(sources) + "\nupdated:", 1)


class BootstrapClassificationTests(unittest.TestCase):
    def test_private_bootstrap_keeps_body_and_inherits_tag(self):
        files = bootstrap_files()
        files["01_Profile/NOW.md"] = doc("Now", "# Now\n\nSyntheticPrivateBootstrapSentinel", tags=("type/meta", "restricted/private"))
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            payload = brain.build_bootstrap(root)
            text = payload["rendered"].decode()
            fm, *_ = brain.parse_frontmatter(text.split("\n"))
            self.assertIn("SyntheticPrivateBootstrapSentinel", text)
            self.assertIn("restricted/private", fm["tags"])
            self.assertTrue(next(row for row in payload["sources"] if row["path"] == "01_Profile/NOW.md")["restricted"])
            self.assertEqual(payload["rendered"], brain.build_bootstrap(root)["rendered"])
            with contextlib.redirect_stdout(io.StringIO()):
                code = brain.main(["bootstrap", "--write", "--vault", str(root)])
            self.assertEqual(code, 0, "Private content is permitted in generated bootstrap output")


class DerivedClassificationTests(unittest.TestCase):
    def test_internal_views_include_private_work_and_classify_indirect_inputs(self):
        vault = HomeVault()
        self.addCleanup(vault.cleanup)
        rel = "04_Projects/private/PROJECT.md"
        vault.write("05_Areas/work/AREA.md", note("Work", "Maintain.",
                    ("type/area", "status/active", "area/work")), tracked=True)
        vault.write(rel, note("Private Project", "## Outcome\n\nDeliver.\n\n"
                    "## Completion Criteria\n\n- Finished.\n\n## Next Actions\n\n"
                    "- [ ] Private next action ⏫ 📅 2026-08-10",
                    ("type/project", "status/active", "project/private", "area/work", "restricted/private"))
                    .replace("updated:", "target: 2026-12-31\ntarget_status: confirmed\nupdated:"), tracked=True)
        payload = vault.build()
        self.assertIn(rel, [p["path"] for p in payload["active"]["projects"]])
        self.assertIn("Private next action", brain.render_home(payload).decode())
        self.assertIn("  - restricted/private\n", brain.render_home(payload).decode())
        self.assertIn(rel, payload["privacySources"])
        # A source counted in the Inbox but hidden by output caps is still
        # a dependency; reclassification must cover its indirect contribution.
        for n in range(15):
            vault.write(f"02_Inbox/{n:02}.md", note("Capture", "Body"), tracked=True)
        hidden = "02_Inbox/14.md"
        payload = vault.build()
        self.assertIn(hidden, payload["privacySources"])

    def test_both_candidate_paths_obey_project_actions_and_future_scheduling(self):
        vault = HomeVault()
        self.addCleanup(vault.cleanup)
        rel = "04_Projects/action/PROJECT.md"
        vault.write(rel, note("Action", "## Completion Criteria\n\n"
                    "- [ ] OLD-CRITERION ⏫ 📅 2026-01-01\n\n## Next Actions\n\n"
                    "- [ ] ACTUAL-ACTION ⏫ 📅 2026-08-11\n"
                    "- [ ] FUTURE-ACTION ⏫ 🛫 2026-09-01\n\n## History\n\n"
                    "- [ ] HISTORICAL-ACTION ⏫ 📅 2026-01-01",
                    ("type/project", "status/active", "project/action", "area/work"))
                    .replace("updated:", "target: 2026-12-31\ntarget_status: confirmed\nupdated:"), tracked=True)
        vault.write("04_Projects/action/support.md", note("Supporting plan",
                    "## Next Actions\n\n- [ ] SUPPORT-BYPASS ⏫ 📅 2026-01-01"), tracked=True)
        with mock.patch.object(brain, "git_tracked", return_value=set(vault.tracked)):
            payload = brain.build_aymt(vault.root, today_d=brain.date(2026, 8, 11), selection=UNCONFIGURED)
        candidates = json.dumps(payload["candidates"])
        self.assertIn("ACTUAL-ACTION", candidates)
        for excluded in ("OLD-CRITERION", "HISTORICAL-ACTION", "FUTURE-ACTION", "SUPPORT-BYPASS"):
            self.assertNotIn(excluded, candidates)

    def test_internal_active_counts_explain_capped_inventory(self):
        vault = HomeVault()
        self.addCleanup(vault.cleanup)
        for n in range(brain.HOME_ACTIVE_CAP + 1):
            slug = f"area-{n}"
            vault.write(f"05_Areas/{slug}/AREA.md", note(slug, "Maintain.",
                ("type/area", "status/active", f"area/{slug}")), tracked=True)
        payload = vault.build()
        self.assertEqual(payload["active"]["areaCount"], brain.HOME_ACTIVE_CAP + 1)
        self.assertEqual(len(payload["active"]["areas"]), brain.HOME_ACTIVE_CAP)
        self.assertIn("Showing 8 of 9 active areas", brain.render_home(payload).decode())

    def test_urgent_project_action_outranks_a_future_generic_reminder(self):
        vault = HomeVault()
        self.addCleanup(vault.cleanup)
        rel = "04_Projects/action/PROJECT.md"
        vault.write(rel, note("Action", "## Completion Criteria\n\n- Finished.\n\n"
            "## Next Actions\n\n- [ ] URGENT-APPROVED-ACTION 📅 2026-08-11",
            ("type/project", "status/active", "project/action", "area/work"))
            .replace("updated:", "target: 2026-12-31\ntarget_status: confirmed\nupdated:"), tracked=True)
        vault.write("01_Profile/NOW.md", note("Now", "## Key Dates / Deadlines\n\n"
            "- 2026-12-31 — GENERIC-FUTURE-REMINDER"), tracked=True)
        with mock.patch.object(brain, "git_tracked", return_value=set(vault.tracked)):
            payload = brain.build_aymt(vault.root, today_d=brain.date(2026, 8, 11), selection=UNCONFIGURED)
        urgent = next(row for row in payload["candidates"] if row["outcome"] == "URGENT-APPROVED-ACTION")
        reminder = next(row for row in payload["candidates"] if "GENERIC-FUTURE-REMINDER" in row["outcome"])
        self.assertGreater(urgent["score"], reminder["score"])
        self.assertLess(payload["candidates"].index(urgent), payload["candidates"].index(reminder))

    def test_availability_uses_last_token_for_each_field(self):
        task = {"line": 1}
        today = brain.date(2026, 8, 11)
        self.assertTrue(brain._aymt_task_ready(task, today,
            "- [ ] Ready 🛫 2026-09-01 🛫 2026-08-01"))
        self.assertFalse(brain._aymt_task_ready(task, today,
            "- [ ] Future ⏳ 2026-08-01 ⏳ 2026-09-01"))
        self.assertFalse(brain._aymt_task_ready(task, today,
            "- [ ] Waiting 🛫 2026-08-01 ⏳ 2026-09-01"))

    def test_generic_provenance_cycles_and_missing_rollup_sources(self):
        private = "06_Resources/private.md"
        first = "06_Resources/first.md"
        second = "06_Resources/second.md"
        area = "05_Areas/example/AREA.md"
        files = {
            private: note("Private", "SyntheticPrivateLeaf", ("type/note", "restricted/private")),
            first: derived_note("First", "SyntheticFirstSummary", [second]),
            second: derived_note("Second", "SyntheticSecondSummary", [first]),
            area: note("Area", "## Active Projects\n\n[Missing](../../04_Projects/deleted/PROJECT.md)"),
        }
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            states = brain.effective_privacy(indexed(root))
            self.assertEqual(states[first], "unknown")
            self.assertEqual(states[second], "unknown")
            self.assertEqual(states[area], "unknown")
            (root / second).write_text(derived_note("Second", "SyntheticSecondSummary", [first, private]))
            states = brain.effective_privacy(indexed(root))
            self.assertEqual(states[first], "private")
            self.assertEqual(states[second], "private")
            (root / first).write_text(derived_note("First", "SyntheticFirstSummary", [private]))
            self.assertNotIn(first, brain.public_only_index(indexed(root))["notes"])
            (root / first).write_text(derived_note("First", "HistoricalPrivateSummary", [private]).replace("  - type/note\n", "  - type/note\n  - restricted/private\n"))
            (root / private).write_text(note("Now public", "Public replacement"))
            self.assertEqual(brain.effective_privacy(indexed(root))[first], "private", "An inherited tag is not cleared by a source's later declassification")

    def test_reclassification_filters_stale_briefs_without_blocking_index_or_local_reads(self):
        vault = HomeVault()
        self.addCleanup(vault.cleanup)
        source = "01_Profile/NOW.md"
        marker = "SyntheticPrivateFocusSentinel"
        body = "## Current Focus\n\n- " + marker
        vault.write(source, note("Now", body, ("type/meta",)), tracked=True)
        with mock.patch.object(brain, "git_tracked", return_value=set(vault.tracked)):
            aymt = brain.build_aymt(vault.root, selection=UNCONFIGURED)
        vault.write(brain.AYMT_RELPATH, brain.render_aymt(aymt), tracked=True)
        vault.write(brain.HOME_RELPATH, brain.render_home(vault.build()), tracked=True)
        before = indexed(vault.root)
        self.assertEqual(brain.effective_privacy(before)[brain.AYMT_RELPATH], "public")
        self.assertIn(marker, json.dumps(brain.public_only_index(before)))

        # No Git baseline is required: a new clone of these bytes gets the
        # same current classification, even if the source tag flip predates it.
        vault.write(source, note("Now", body, ("type/meta", "restricted/private")), tracked=True)
        snapshot = indexed(vault.root)
        with mock.patch.object(brain.subprocess, "run", side_effect=AssertionError("classification is snapshot-only")):
            states = brain.effective_privacy(snapshot)
            public = brain.public_only_index(snapshot)
        for rel in (source, brain.AYMT_RELPATH, brain.HOME_RELPATH):
            self.assertEqual(states[rel], "private", rel)
            self.assertNotIn(rel, public["notes"])
        self.assertNotIn(marker, json.dumps(public))
        self.assertIn(marker, json.dumps(snapshot), "local query data remains fully available")
        self.assertIn(marker, (vault.root / brain.AYMT_RELPATH).read_text(), "classification does not hand-edit generated files")

        reduced = brain.reduce_restricted(indexed(vault.root))
        self.assertNotIn(marker, json.dumps(reduced))
        self.assertIn("restricted/private", reduced["notes"][brain.AYMT_RELPATH]["frontmatter"]["tags"])
        self.assertEqual(reduced["notes"][brain.AYMT_RELPATH]["frontmatter"]["effective-privacy"], "private")
        notes, assets = brain.walk_corpus(vault.root, selected_environment=None)
        with mock.patch.object(brain, "index_corpus", return_value=(notes, assets)), contextlib.redirect_stdout(io.StringIO()):
            code = brain.cmd_index(vault.root, None)
        self.assertEqual(code, 0, "A private source or derived note never blocks ordinary indexing")

    def test_missing_or_malformed_provenance_is_unknown_only_for_public_filtering(self):
        files = {
            brain.AYMT_RELPATH: note("AYMT", "## SyntheticLegacyPrivateSentinel"),
            brain.HOME_RELPATH: derived_note("Home", "## SyntheticMissingSourceSentinel", ["01_Profile/missing.md"]),
        }
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            snapshot = indexed(root)
            states = brain.effective_privacy(snapshot)
            self.assertEqual(states[brain.AYMT_RELPATH], "unknown")
            self.assertEqual(states[brain.HOME_RELPATH], "unknown")
            self.assertEqual(brain.public_only_index(snapshot)["notes"], {})
            reduced = brain.reduce_restricted(indexed(root))
            self.assertIn(brain.AYMT_RELPATH, reduced["notes"])
            self.assertIn("SyntheticLegacyPrivateSentinel", json.dumps(reduced), "unknown provenance does not censor ordinary indexes")
            self.assertEqual(brain.public_only_index(reduced)["notes"], {})

    def test_rollup_derivation_propagates_but_ordinary_private_links_do_not(self):
        project = "04_Projects/secret/PROJECT.md"
        area = "05_Areas/example/AREA.md"
        public_note = "06_Resources/public.md"
        files = {
            project: note("Private project", "Private body.", ("type/project", "restricted/private")),
            area: note("Area", "## Active Projects\n\n- [Private project](../../04_Projects/secret/PROJECT.md)\n\n## Notes\n\nPreserved owner prose.", ("type/area",)),
            public_note: note("Public", "An intentional [bare link](../04_Projects/secret/PROJECT.md)."),
            brain.AYMT_RELPATH: derived_note("AYMT", "## SyntheticRollupSummarySentinel", [area]),
            brain.HOME_RELPATH: derived_note("Home", "## SyntheticDerivedSummarySentinel", [brain.AYMT_RELPATH]),
        }
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            snapshot = indexed(root)
            states = brain.effective_privacy(snapshot)
            for rel in (project, area, brain.AYMT_RELPATH, brain.HOME_RELPATH):
                self.assertEqual(states[rel], "private", rel)
            self.assertEqual(states[public_note], "public")
            self.assertIn(public_note, brain.public_only_index(snapshot)["notes"])
            self.assertNotIn("SyntheticRollupSummarySentinel", json.dumps(brain.reduce_restricted(indexed(root))))

            # Moving the same link outside the owned rollup removes the
            # derivation edge. Bare links never taint unrelated owner prose.
            (root / area).write_text(note("Area", "## Active Projects\n\n_None._\n\n## Notes\n\n[Private project](../../04_Projects/secret/PROJECT.md)", ("type/area",)))
            states = brain.effective_privacy(indexed(root))
            self.assertEqual(states[area], "public")
            self.assertEqual(states[brain.AYMT_RELPATH], "public")


class PublicContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = "06_Resources/private.md"
        self.public = "06_Resources/public.md"
        self.derived = "06_Resources/summary.md"
        self.root = make_vault(Path(self.temp.name), {
            self.private: note("Private", "SyntheticPrivateReplySentinel", ("type/note", "restricted/private")),
            self.public: note("Public", "SyntheticPublicReplySentinel"),
            self.derived: derived_note("Summary", "SyntheticDerivedReplySentinel", [self.private]),
        })

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = brain.main([*argv, "--vault", str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_public_only_search_show_read_and_default_local_read(self):
        code, out, err = self.run_cli("search", "ReplySentinel", "--public-only", "--json")
        self.assertEqual(code, 0, err)
        self.assertIn("SyntheticPublicReplySentinel", out)
        self.assertNotIn("SyntheticPrivateReplySentinel", out)
        self.assertNotIn("SyntheticDerivedReplySentinel", out)
        code, out, err = self.run_cli("show", self.derived, "--public-only", "--json")
        self.assertEqual(code, 1)
        self.assertNotIn("SyntheticDerivedReplySentinel", out + err)
        code, out, err = self.run_cli("read", self.public, "--public-only", "--shared-only", "--json")
        self.assertEqual(code, 0, err)
        row = json.loads(out)[0]
        self.assertEqual(row["contentScope"], "public-only")
        self.assertEqual(row["contentHash"], brain.note_content_hash(row["content"]))
        code, out, err = self.run_cli("read", self.private, "--json")
        self.assertEqual(code, 0, err)
        self.assertIn("SyntheticPrivateReplySentinel", out)
        self.assertEqual(json.loads(out)[0]["contentScope"], "local")

    def test_multi_note_refusal_emits_no_partial_sources(self):
        code, out, err = self.run_cli("read", self.public, self.private, "--public-only", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(set(json.loads(out)), {"error"})
        self.assertNotIn("SyntheticPublicReplySentinel", out + err)
        self.assertNotIn("SyntheticPrivateReplySentinel", out + err)

    def test_semantic_search_receives_only_public_source_records(self):
        def search_public(root, index, args, **kwargs):
            self.assertEqual(set(index["notes"]), {self.public})
            self.assertNotIn("SyntheticPrivateReplySentinel", json.dumps(index))
            self.assertNotIn("SyntheticDerivedReplySentinel", json.dumps(index))
            return 0

        with mock.patch.object(brain, "semantic_search", side_effect=search_public) as search:
            code, out, err = self.run_cli("search", "ReplySentinel", "--semantic", "--public-only", "--json")
        self.assertEqual(code, 0, err)
        search.assert_called_once()

    def test_read_classification_and_body_share_snapshot_across_tag_race(self):
        original = brain.build_index

        def reclassify_after_capture(root, notes, assets, **kwargs):
            (root / self.private).write_text(note("Now public", "SyntheticNewPublicText"))
            return original(root, notes, assets, **kwargs)

        with mock.patch.object(brain, "build_index", side_effect=reclassify_after_capture):
            with self.assertRaises(brain.NoteContextError):
                brain.read_note_context(self.root, [self.private], public_only=True)

        def replace_with_private_after_capture(root, notes, assets, **kwargs):
            (root / self.public).write_text(note("Now private", "SyntheticNewPrivateText", ("type/note", "restricted/private")))
            return original(root, notes, assets, **kwargs)

        with mock.patch.object(brain, "build_index", side_effect=replace_with_private_after_capture):
            rows = brain.read_note_context(self.root, [self.public], public_only=True)
        self.assertIn("SyntheticPublicReplySentinel", rows[0]["content"])
        self.assertNotIn("SyntheticNewPrivateText", json.dumps(rows))


if __name__ == "__main__":
    unittest.main()
