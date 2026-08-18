"""Actions You May Take correctness, privacy, and write-ownership tests."""

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


def note(title: str, body: str, tags: tuple[str, ...] = ("type/note",)) -> str:
    tag_lines = "".join(f"  - {tag}\n" for tag in tags)
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n"
        f"{tag_lines}"
        "updated: 2026-08-11\n"
        "---\n\n"
        f"# {title}\n\n{body}\n"
    )


def environment_manifest(slug: str, expires: str = "2026-08-25") -> dict:
    return {
        "capabilities": {"computer-use": True},
        "class": "laptop",
        "fingerprints": [],
        "freshness": {"checkedAt": "2026-08-01", "expiresAt": expires},
        "maintenance": {
            "inventory": "orientation-inventory.md",
            "ownerReviewRequired": True,
        },
        "schemaVersion": 1,
        "slug": slug,
        "surfaces": ["codex"],
    }


class VaultFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aymt-")
        self.root = Path(self.temp.name)
        self.tracked: set[str] = set()
        self.write(
            brain.ADOPT_EXAMPLES_RELPATH,
            json.dumps(
                {
                    "_comment": "fixture",
                    "bundle": "seeded-examples",
                    "cleanup_marker": "delete once you've seen the pattern",
                    "delete": ["04_Projects/example-project/"],
                    "schema_version": 1,
                }
            ),
            tracked=True,
        )
        self.write(
            "01_Profile/NOW.md",
            note("Now", "## Current Focus\n\n- Build calm systems\n\n## Active Projects\n\n- Real Project\n\n## Key Dates / Deadlines\n\n- Launch: 2026-08-15", ("type/meta",)),
            tracked=True,
        )
        self.write(
            "10_Agents/skills/README.md",
            note("Skills", "## The Rhythm\n", ("type/meta",)),
            tracked=True,
        )
        self.write(
            "02_Inbox/README.md", note("Inbox", "Queue."), tracked=True
        )
        self.write(
            "10_Agents/environments/README.md",
            note("Environments", "Metadata contract."),
            tracked=True,
        )

    def cleanup(self):
        self.temp.cleanup()

    def write(self, rel: str, content: str | bytes, *, tracked: bool = False):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        if tracked:
            self.tracked.add(rel)
        return path

    def build(self, **kwargs):
        with mock.patch.object(brain, "git_tracked", return_value=set(self.tracked)):
            return brain.build_aymt(
                self.root,
                today_d=kwargs.pop("today_d", date(2026, 8, 11)),
                selection=kwargs.pop("selection", UNCONFIGURED),
                **kwargs,
            )


class AymtCollectorTests(unittest.TestCase):
    def setUp(self):
        self.vault = VaultFixture()

    def tearDown(self):
        self.vault.cleanup()

    def test_score_formula_and_dependency_lowers_rank(self):
        ready = {
            "urgency": 4,
            "leverage": 3,
            "confidence": 4,
            "staleness": 2,
            "effort": 1,
            "dependency": 0,
        }
        blocked = {**ready, "dependency": 4}
        self.assertEqual(brain._aymt_score(ready), 58)
        self.assertEqual(brain._aymt_score(blocked), 38)

    def test_untracked_inbox_and_private_looking_body_do_not_change_output(self):
        before = self.vault.build()
        before_markdown = brain.render_aymt(before)
        legacy = "[" * 2 + "private-target" + "]" * 2
        self.vault.write(
            "02_Inbox/untracked-owner-note.md",
            note("SECRET OWNER TITLE", f"{legacy}\n- [ ] DO-NOT-LEAK-TASK"),
        )
        after = self.vault.build()
        self.assertEqual(after, before)
        self.assertEqual(brain.render_aymt(after), before_markdown)
        self.assertNotIn("SECRET OWNER", json.dumps(after))

    def test_tracked_symlinked_note_never_imports_external_text(self):
        external_dir = tempfile.TemporaryDirectory(prefix="aymt-external-")
        self.addCleanup(external_dir.cleanup)
        external = Path(external_dir.name) / "secret.md"
        external.write_text(
            note("EXTERNAL-SECRET-TITLE", "- [ ] EXTERNAL-SECRET-TASK"),
            encoding="utf-8",
        )
        linked = self.vault.root / "04_Projects/external.md"
        linked.parent.mkdir(parents=True, exist_ok=True)
        linked.symlink_to(external)
        self.vault.tracked.add("04_Projects/external.md")
        payload = self.vault.build()
        combined = json.dumps(payload) + brain.render_aymt(payload).decode()
        self.assertNotIn("EXTERNAL-SECRET", combined)
        self.assertTrue(linked.is_symlink())

    def test_privacy_classification_and_candidates_share_one_authenticated_snapshot(self):
        original = brain.build_index

        def swap_after_snapshot(root, notes, assets, **kwargs):
            self.vault.write(
                "01_Profile/NOW.md",
                note(
                    "RESTRICTED-RACE",
                    "## Current Focus\n\n- RESTRICTED-RACE-SECRET",
                    ("type/meta", "restricted/private"),
                ),
                tracked=True,
            )
            return original(root, notes, assets, **kwargs)

        with mock.patch.object(brain, "build_index", side_effect=swap_after_snapshot):
            payload = self.vault.build()
        combined = json.dumps(payload) + brain.render_aymt(payload).decode()
        self.assertIn("Build calm systems", combined)
        self.assertNotIn("RESTRICTED-RACE", combined)

    def test_in_place_rewrite_between_chunks_discards_mixed_snapshot(self):
        rel = "04_Projects/large-public.md"
        public = note(
            "Large public",
            ("P" * 70_000) + "\n- [ ] PUBLIC-LARGE-TASK",
            ("type/project",),
        )
        restricted = note(
            "RESTRICTED-MIDREAD-TITLE",
            ("S" * 70_000) + "\n- [ ] RESTRICTED-MIDREAD-SECRET",
            ("type/project", "restricted/private"),
        )
        target = self.vault.write(rel, public, tracked=True)
        target_inode = target.stat().st_ino
        original_read = brain.os.read
        rewrote = False

        def rewrite_after_first_chunk(descriptor, size):
            nonlocal rewrote
            chunk = original_read(descriptor, size)
            if (
                not rewrote
                and chunk
                and os.fstat(descriptor).st_ino == target_inode
            ):
                rewrote = True
                target.write_text(restricted, encoding="utf-8")
            return chunk

        with mock.patch.object(brain.os, "read", side_effect=rewrite_after_first_chunk):
            payload = self.vault.build()
        self.assertTrue(rewrote)
        combined = json.dumps(payload) + brain.render_aymt(payload).decode()
        self.assertNotIn("PUBLIC-LARGE-TASK", combined)
        self.assertNotIn("RESTRICTED-MIDREAD", combined)

    def test_git_unavailable_fails_closed_before_untracked_secret_can_enter(self):
        self.vault.write(
            "02_Inbox/untracked-secret.md",
            note("GIT-FALLBACK-SECRET", "- [ ] NEVER-INDEX-ME"),
        )
        with mock.patch.object(brain, "git_tracked", return_value=None):
            with self.assertRaises(brain.AymtError) as raised:
                brain.build_aymt(
                    self.vault.root,
                    today_d=date(2026, 8, 11),
                    selection=UNCONFIGURED,
                )
        self.assertNotIn("GIT-FALLBACK-SECRET", str(raised.exception))

    def test_restricted_restricted_target_and_environment_bodies_never_enter_candidates(self):
        restricted = "04_Projects/restricted.md"
        public = "04_Projects/public.md"
        env_body = "10_Agents/environments/alpha/orientation-inventory.md"
        self.vault.write(
            restricted,
            note("RESTRICTED-SECRET", "- [ ] RESTRICTED-TASK", ("type/project", "status/active", "restricted/private")),
            tracked=True,
        )
        self.vault.write(
            public,
            note("PUBLIC-WITH-SECRET-TARGET", f"[private](restricted.md)\n- [ ] TARGET-LEAK", ("type/project", "status/active")),
            tracked=True,
        )
        self.vault.write(
            "10_Agents/environments/alpha/environment.json",
            json.dumps(environment_manifest("alpha")),
            tracked=True,
        )
        self.vault.write(env_body, note("ENV-BODY-SECRET", "- [ ] ENV-TASK"), tracked=True)
        payload = self.vault.build(
            selection={"slug": "alpha", "source": "cli", "state": "selected"}
        )
        combined = json.dumps(payload) + brain.render_aymt(payload).decode()
        for secret in ("RESTRICTED-SECRET", "RESTRICTED-TASK", "TARGET-LEAK", "ENV-BODY-SECRET", "ENV-TASK"):
            self.assertNotIn(secret, combined)
        self.assertEqual(payload["environment"]["slug"], "alpha")

    def test_unconfigured_environment_is_useful_empty_state(self):
        payload = self.vault.build()
        self.assertEqual(payload["environment"], {"freshness": None, **UNCONFIGURED})
        self.assertIn("not configured; shared tracked sources only", brain.render_aymt(payload).decode())

    def test_environment_expiry_candidate_uses_metadata_only(self):
        self.vault.write(
            "10_Agents/environments/alpha/environment.json",
            json.dumps(environment_manifest("alpha", "2026-08-10")),
            tracked=True,
        )
        payload = self.vault.build(
            selection={"slug": "alpha", "source": "selector", "state": "selected"}
        )
        row = next(row for row in payload["candidates"] if row["kind"] == "environment")
        self.assertEqual(row["section"], "do-next")
        self.assertEqual(row["sources"][0]["path"], "10_Agents/environments/README.md")

    def test_selected_untracked_environment_manifest_is_refused(self):
        self.vault.write(
            "10_Agents/environments/alpha/environment.json",
            json.dumps(environment_manifest("alpha")),
        )
        with self.assertRaises(brain.AymtError) as raised:
            self.vault.build(
                selection={"slug": "alpha", "source": "selector", "state": "selected"}
            )
        self.assertNotIn("alpha", str(raised.exception))

    def test_selected_valid_manifest_ignores_malformed_unselected_environment(self):
        self.vault.write(
            "10_Agents/environments/alpha/environment.json",
            json.dumps(environment_manifest("alpha")),
            tracked=True,
        )
        self.vault.write(
            "10_Agents/environments/beta/environment.json",
            "{malformed-unselected",
            tracked=True,
        )
        self.vault.write(".second-brain/environment", "alpha\n")
        payload = self.vault.build(selection=None)
        self.assertEqual(payload["environment"]["slug"], "alpha")
        self.assertEqual(payload["environment"]["state"], "selected")

    def test_profile_template_readiness_and_filled_profile_keep_now_signals(self):
        profile_paths = [brain.CORE_FRAMEWORK_PATHS[key] for key in (
            "identity", "work", "preferences", "defaults", "tooling-stack"
        )]
        for rel in profile_paths:
            self.vault.write(
                rel,
                note(rel, "> **Template note:** Fill this in."),
                tracked=True,
            )
        template_payload = self.vault.build()
        self.assertIn("profile-readiness", {row["kind"] for row in template_payload["candidates"]})
        for rel in profile_paths:
            self.vault.write(rel, note(rel, "Owner-provided profile context."), tracked=True)
        filled_payload = self.vault.build()
        kinds = {row["kind"] for row in filled_payload["candidates"]}
        outcomes = {row["outcome"] for row in filled_payload["candidates"]}
        self.assertNotIn("profile-readiness", kinds)
        # NOW is a curated priority view, not the Project source of truth.
        self.assertNotIn("Real Project", outcomes)
        self.assertIn("Launch: 2026-08-15", outcomes)

    def test_canonical_project_target_is_visible_and_support_note_is_not_duplicated(self):
        self.vault.write(
            "05_Areas/work/AREA.md",
            note("Work", "## Active Projects\n", ("type/area", "status/active", "area/work")),
            tracked=True,
        )
        project = note(
            "Canonical",
            "## Outcome\n\nShip it.\n\n## Completion Criteria\n\n- Verified.\n\n- [ ] Next move",
            ("type/project", "status/active", "project/canonical", "area/work"),
        ).replace("updated: 2026-08-11", "target: 2026-08-20\ntarget_status: estimated\nupdated: 2026-08-11")
        self.vault.write("04_Projects/canonical/PROJECT.md", project, tracked=True)
        self.vault.write(
            "04_Projects/canonical/support.md",
            note("Support", "Reference.", ("type/note", "project/canonical")),
            tracked=True,
        )

        payload = self.vault.build(today_d=date(2026, 8, 21))
        projects = [row for row in payload["candidates"] if row["kind"] == "project"]

        self.assertEqual(len(projects), 1)
        self.assertIn("estimated, overdue", projects[0]["outcome"])

    def test_restricted_profile_is_filtered_before_readiness(self):
        rel = brain.CORE_FRAMEWORK_PATHS["identity"]
        self.vault.write(
            rel,
            note("PRIVATE-PROFILE", "> **Template note:** SECRET", ("type/meta", "restricted/private")),
            tracked=True,
        )
        serialized = json.dumps(self.vault.build())
        self.assertNotIn("PRIVATE-PROFILE", serialized)
        self.assertNotIn("SECRET", serialized)

    def test_cadence_windows_suppress_existing_period_notes(self):
        paths = {
            "03_Journal/periodic/daily/2026-12-31.md",
            "03_Journal/periodic/weekly/2026-W53-review.md",
            "03_Journal/periodic/monthly/2026-12-review.md",
            "03_Journal/periodic/quarterly/2026-Q4-review.md",
            "03_Journal/periodic/yearly/2026-review.md",
        }
        self.assertEqual(brain._aymt_cadence_candidates(date(2026, 12, 31), paths), [])
        outcomes = [row["outcome"] for row in brain._aymt_cadence_candidates(date(2026, 12, 31), set())]
        self.assertEqual(len(outcomes), 4)

    def test_due_tasks_anywhere_are_included_plain_procedural_tasks_are_not(self):
        self.vault.write(
            "02_Inbox/actionable.md",
            note("Actionable", "- [ ] Send reviewed packet 📅 2026-08-12"),
            tracked=True,
        )
        self.vault.write(
            "10_Agents/docs/procedure.md",
            note("Procedure", "- [ ] PROCEDURAL-CHECKLIST-ONLY", ("type/meta",)),
            tracked=True,
        )
        payload = self.vault.build()
        outcomes = {row["outcome"] for row in payload["candidates"]}
        self.assertIn("Send reviewed packet", outcomes)
        self.assertNotIn("PROCEDURAL-CHECKLIST-ONLY", json.dumps(payload))

    def test_priority_task_outside_owner_lanes_is_actionable(self):
        self.vault.write(
            "02_Inbox/priority.md",
            note("Priority", "- [ ] Review priority capture ⏫"),
            tracked=True,
        )
        payload = self.vault.build()
        self.assertIn("Review priority capture", {row["outcome"] for row in payload["candidates"]})

    def test_malformed_due_task_surfaces_redacted_repair_action(self):
        self.vault.write(
            "02_Inbox/malformed.md",
            note("Malformed", "- [ ] SECRET-TASK-TEXT 📅 2026-99-99"),
            tracked=True,
        )
        payload = self.vault.build()
        row = next(row for row in payload["candidates"] if row["kind"] == "task-metadata")
        self.assertEqual(row["section"], "unblock-or-decide")
        self.assertNotIn("SECRET-TASK-TEXT", json.dumps(row))

    def test_seed_inventory_excludes_fresh_partial_and_remaining_examples(self):
        example = "04_Projects/example-project/README.md"
        self.vault.write(
            example,
            note("FAKE SAMPLE WORK", "- [ ] SHIP FAKE SAMPLE", ("type/project", "status/active")),
            tracked=True,
        )
        fresh = self.vault.build()
        self.vault.write("04_Projects/example-project/extra.md", note("MORE FAKE", "- [ ] MORE FAKE"), tracked=True)
        partial = self.vault.build()
        self.vault.tracked.remove(example)
        adopted = self.vault.build()
        for payload in (fresh, partial, adopted):
            serialized = json.dumps(payload) + brain.render_aymt(payload).decode()
            self.assertNotIn("FAKE SAMPLE", serialized)
            self.assertNotIn("MORE FAKE", serialized)

    def test_exact_outcome_dedupe_and_soft_caps_fill_to_seven(self):
        for index in range(8):
            outcome = "Same outcome" if index < 2 else f"Task {index}"
            rel = f"04_Projects/real-{index}.md"
            self.vault.write(
                rel,
                note(f"Real {index}", f"- [ ] {outcome}", ("type/project",)),
                tracked=True,
            )
        payload = self.vault.build()
        self.assertEqual(payload["summary"]["selected"], 7)
        self.assertGreater(payload["summary"]["collected"], payload["summary"]["deduplicated"])
        self.assertGreater(sum(row["section"] == "keep-warm" for row in payload["candidates"]), 2)
        self.assertTrue(all(len(row["id"]) == 64 for row in payload["candidates"]))

    def test_soft_cap_overflow_uses_global_score_and_dedupe_merges_sources(self):
        def candidate(outcome, section, urgency, source, kind="test"):
            return brain._aymt_candidate(
                kind=kind,
                outcome=outcome,
                section=section,
                why_now="why",
                next_step="next",
                caveat="caveat",
                sources=[brain._aymt_source(source)],
                urgency=urgency,
                leverage=urgency,
                effort=1,
                confidence=4,
                dependency=0,
                staleness=urgency,
            )

        rows = [candidate(f"Do {index}", "do-next", 4 if index < 3 else 0, f"do-{index}.md") for index in range(5)]
        rows += [candidate(f"Warm {index}", "keep-warm", 4, f"warm-{index}.md") for index in range(4)]
        selected, summary = brain._select_aymt_candidates(rows)
        outcomes = {row["outcome"] for row in selected}
        self.assertEqual(summary["selected"], 7)
        self.assertIn("Warm 2", outcomes)
        self.assertIn("Warm 3", outcomes)
        self.assertNotIn("Do 3", outcomes)
        self.assertNotIn("Do 4", outcomes)

        duplicates = [
            candidate("Same", "keep-warm", 1, "one.md", kind="low"),
            candidate("same", "do-next", 4, "two.md", kind="high"),
        ]
        merged, merged_summary = brain._select_aymt_candidates(duplicates)
        self.assertEqual(merged_summary["deduplicated"], 1)
        self.assertEqual(merged[0]["kind"], "high")
        self.assertEqual(
            [source["path"] for source in merged[0]["sources"]],
            ["one.md", "two.md"],
        )

    def test_safe_report_stale_active_and_orphans_do_not_depend_on_inbox(self):
        stale = note("Stale", "No links.", ("type/project", "status/active")).replace(
            "updated: 2026-08-11", "updated: 2026-06-01"
        )
        self.vault.write("04_Projects/stale.md", stale, tracked=True)
        self.vault.write("06_Resources/orphan.md", note("Orphan", "Disconnected."), tracked=True)
        payload = self.vault.build()
        kinds = {row["kind"] for row in payload["candidates"]}
        self.assertIn("report-stale-active", kinds)
        self.assertIn("report-orphans", kinds)

    def test_restricted_backlink_cannot_change_safe_orphan_report(self):
        target = "06_Resources/orphan.md"
        self.vault.write(target, note("Orphan", "Disconnected."), tracked=True)
        before = self.vault.build()
        self.vault.write(
            "04_Projects/restricted-linker.md",
            note(
                "RESTRICTED-LINKER",
                "[secret influence](../06_Resources/orphan.md)",
                ("type/project", "restricted/private"),
            ),
            tracked=True,
        )
        after = self.vault.build()
        self.assertEqual(after, before)

    def test_markdown_escaping_and_nfc_are_stable(self):
        row = brain._aymt_candidate(
            kind="test",
            outcome="Cafe\u0301 *[x]*",
            section="keep-warm",
            why_now="why *now*",
            next_step="next [step]",
            caveat="caveat `code`",
            sources=[brain._aymt_source("01_Profile/NOW.md")],
            urgency=1, leverage=1, effort=1, confidence=1, dependency=0, staleness=0,
        )
        payload = {
            "candidates": [row], "date": "2026-08-11", "environment": {"freshness": None, **UNCONFIGURED},
            "inputDigest": "0" * 64, "schemaVersion": 1, "summary": {"collected": 1, "deduplicated": 1, "selected": 1, "truncated": 0},
        }
        rendered = brain.render_aymt(payload).decode()
        self.assertIn("Café \\*\\[x\\]\\*", rendered)
        self.assertIn("why \\*now\\*", rendered)
        self.assertTrue(rendered.endswith("\n"))
        self.assertFalse(rendered.endswith("\n\n"))

    def test_github_input_is_strict_computed_and_process_free(self):
        path = self.vault.write(
            "github.json",
            json.dumps({
                "schemaVersion": 1,
                "repository": "owner/repo",
                "issues": [{"number": 79, "title": "Ship AYMT", "status": "ready", "updated": "2026-08-10", "labels": ["effort/s"]}],
            }),
        )
        with mock.patch.object(brain.subprocess, "run", side_effect=AssertionError("no process")):
            rows = brain._load_aymt_github_input(str(path), io.StringIO(), date(2026, 8, 11))
        self.assertEqual(rows[0]["sources"][0]["url"], "https://github.com/owner/repo/issues/79")
        markdown_payload = {
            "candidates": rows, "date": "2026-08-11", "environment": {"freshness": None, **UNCONFIGURED},
            "inputDigest": "0" * 64, "schemaVersion": 1, "summary": {"collected": 1, "deduplicated": 1, "selected": 1, "truncated": 0},
        }
        self.assertIn("[owner/repo#79](https://github.com/owner/repo/issues/79)", brain.render_aymt(markdown_payload).decode())

    def test_github_input_rejects_urls_duplicates_bad_identity_and_types(self):
        base_issue = {"number": 1, "title": "One", "status": "ready", "updated": "2026-08-10", "labels": []}
        cases = [
            {"schemaVersion": 1, "repository": "../repo", "issues": [base_issue]},
            {"schemaVersion": 1, "repository": "owner/repo", "issues": [base_issue, dict(base_issue)]},
            {"schemaVersion": 1, "repository": "owner/repo", "issues": [{**base_issue, "url": "https://evil.invalid"}]},
            {"schemaVersion": True, "repository": "owner/repo", "issues": [base_issue]},
            {"schemaVersion": 1, "repository": ["owner", "repo"], "issues": [base_issue]},
            {"schemaVersion": 1, "repository": "owner/repo", "issues": [{**base_issue, "status": []}]},
            {"schemaVersion": 1, "repository": "owner/repo", "issues": [{**base_issue, "updated": []}]},
            {"schemaVersion": 1, "repository": "owner/repo", "issues": [{**base_issue, "number": True}]},
        ]
        for index, data in enumerate(cases):
            path = self.vault.write(f"bad-{index}.json", json.dumps(data))
            with self.subTest(index=index), self.assertRaises(brain.AymtError):
                brain._load_aymt_github_input(str(path), io.StringIO(), date(2026, 8, 11))


class AymtWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aymt-write-")
        self.root = Path(self.temp.name)
        (self.root / "00_Meta").mkdir()
        self.payload = {
            "candidates": [],
            "date": "2026-08-11",
            "environment": {"freshness": None, **UNCONFIGURED},
            "inputDigest": "a" * 64,
            "schemaVersion": 1,
            "summary": {"collected": 0, "deduplicated": 0, "selected": 0, "truncated": 0},
        }
        self.desired = brain.render_aymt(self.payload)

    def tearDown(self):
        self.temp.cleanup()

    @property
    def target(self):
        return self.root / brain.AYMT_RELPATH

    def artifacts(self):
        return sorted(path.name for path in (self.root / "00_Meta").iterdir() if path.name != "AYMT.md")

    def test_absent_write_identical_noop_and_no_artifacts(self):
        self.assertEqual(brain.write_aymt(self.root, self.desired), "written")
        before = self.target.stat()
        self.assertEqual(brain.write_aymt(self.root, self.desired), "unchanged")
        self.assertEqual(self.target.read_bytes(), self.desired)
        self.assertEqual(self.target.stat().st_ino, before.st_ino)
        self.assertEqual(self.artifacts(), [])

    def test_foreign_and_symlink_targets_are_preserved(self):
        self.target.write_bytes(b"foreign")
        with self.assertRaises(brain.AymtError):
            brain.write_aymt(self.root, self.desired)
        self.assertEqual(self.target.read_bytes(), b"foreign")
        self.target.unlink()
        foreign = self.root / "foreign.md"
        foreign.write_bytes(b"linked")
        self.target.symlink_to(foreign)
        with self.assertRaises(brain.AymtError):
            brain.write_aymt(self.root, self.desired)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(foreign.read_bytes(), b"linked")

    def test_casefold_sibling_collision_is_preserved_and_refused(self):
        lower = self.root / "00_Meta/aymt.md"
        lower.write_bytes(b"foreign-lowercase")
        prior = lower.stat()
        with self.assertRaises(brain.AymtError):
            brain.write_aymt(self.root, self.desired)
        self.assertEqual(lower.read_bytes(), b"foreign-lowercase")
        self.assertEqual((lower.stat().st_dev, lower.stat().st_ino), (prior.st_dev, prior.st_ino))
        self.assertEqual(
            sum(name.casefold() == "aymt.md" for name in os.listdir(self.root / "00_Meta")),
            1,
        )
        args = SimpleNamespace(github_input=None, write=False, json=True, check=True, aymt_selection=UNCONFIGURED)
        with mock.patch.object(brain, "build_aymt", return_value=self.payload), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brain.cmd_aymt(self.root, args), 1)
        self.assertEqual(lower.read_bytes(), b"foreign-lowercase")

    def test_casefold_sibling_inserted_after_preflight_is_preserved(self):
        lower = self.root / "00_Meta/aymt.md"
        lower.write_bytes(b"probe")
        case_sensitive = not self.target.exists()
        lower.unlink()
        if not case_sensitive:
            self.skipTest("filesystem cannot materialize two casefold-equivalent names")
        original = brain._stage_migration_at

        def stage_then_insert(*args, **kwargs):
            staged = original(*args, **kwargs)
            lower.write_bytes(b"foreign-late-case")
            return staged

        with mock.patch.object(brain, "_stage_migration_at", side_effect=stage_then_insert):
            with self.assertRaises(brain.AymtError):
                brain.write_aymt(self.root, self.desired)
        self.assertEqual(lower.read_bytes(), b"foreign-late-case")
        self.assertFalse(self.target.exists())
        self.assertEqual(list((self.root / "00_Meta").glob(".AYMT.md.migrate-new-*")), [])

    def test_interrupt_restores_prior_and_removes_owned_stage(self):
        brain.write_aymt(self.root, self.desired)
        prior = self.target.read_bytes()
        changed = self.desired.replace(b"No safe", b"Still safe")
        with mock.patch.object(brain, "_install_migration_at", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                brain.write_aymt(self.root, changed)
        self.assertEqual(self.target.read_bytes(), prior)
        self.assertEqual(self.artifacts(), [])

    def test_interrupt_after_real_publication_rolls_back_absent_and_prior(self):
        original = brain._install_migration_at

        def install_then_interrupt(parent, staged, name):
            original(parent, staged, name)
            raise KeyboardInterrupt

        with mock.patch.object(brain, "_install_migration_at", side_effect=install_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                brain.write_aymt(self.root, self.desired)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.artifacts(), [])

        brain.write_aymt(self.root, self.desired)
        prior = self.target.read_bytes()
        changed = self.desired.replace(b"No safe", b"Still safe")
        with mock.patch.object(brain, "_install_migration_at", side_effect=install_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                brain.write_aymt(self.root, changed)
        self.assertEqual(self.target.read_bytes(), prior)
        self.assertEqual(self.artifacts(), [])

    def test_fsync_failure_after_backup_unlink_keeps_committed_result(self):
        brain.write_aymt(self.root, self.desired)
        changed = self.desired.replace(b"No safe", b"Still safe")
        original_fsync = brain.os.fsync
        saw_backup = False
        failed = False

        def fail_after_backup_unlink(descriptor):
            nonlocal failed, saw_backup
            backups = list((self.root / "00_Meta").glob(".AYMT.md.migrate-old-*"))
            if backups:
                saw_backup = True
            elif saw_backup and not failed:
                failed = True
                raise OSError("injected post-commit fsync failure")
            return original_fsync(descriptor)

        with mock.patch.object(brain.os, "fsync", side_effect=fail_after_backup_unlink):
            with self.assertRaises(brain.AymtError):
                brain.write_aymt(self.root, changed)
        self.assertTrue(failed)
        self.assertEqual(self.target.read_bytes(), changed)
        self.assertEqual(self.artifacts(), [])

    def test_stage_cleanup_fsync_failure_is_redacted_and_parent_closes(self):
        original = brain.os.fsync
        failed = False

        def fail_after_stage_unlink(descriptor):
            nonlocal failed
            stages = list((self.root / "00_Meta").glob(".AYMT.md.migrate-new-*"))
            if not failed and self.target.exists() and not stages:
                failed = True
                raise OSError("injected cleanup fsync failure")
            return original(descriptor)

        with mock.patch.object(brain.os, "fsync", side_effect=fail_after_stage_unlink):
            with self.assertRaises(brain.AymtError):
                brain.write_aymt(self.root, self.desired)
        self.assertTrue(failed)
        self.assertEqual(self.target.read_bytes(), self.desired)
        self.assertEqual(self.artifacts(), [])
        self.assertEqual(brain.write_aymt(self.root, self.desired), "unchanged")

    def test_signal_restore_failure_still_cleans_stage_and_closes_parent(self):
        if not hasattr(brain.signal, "SIGTERM"):
            self.skipTest("SIGTERM unavailable")
        original = brain.signal.signal
        prior = brain.signal.getsignal(brain.signal.SIGTERM)
        calls = 0

        def fail_restore(sig, handler):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected restore failure")
            return original(sig, handler)

        try:
            with mock.patch.object(brain.signal, "signal", side_effect=fail_restore):
                with self.assertRaises(brain.AymtError):
                    brain.write_aymt(self.root, self.desired)
        finally:
            original(brain.signal.SIGTERM, prior)
        self.assertEqual(self.target.read_bytes(), self.desired)
        self.assertEqual(self.artifacts(), [])
        self.assertEqual(brain.write_aymt(self.root, self.desired), "unchanged")

    def test_foreign_final_insertion_preserves_foreign_and_explicit_prior_backup(self):
        brain.write_aymt(self.root, self.desired)
        prior = self.target.read_bytes()
        changed = self.desired.replace(b"No safe", b"Still safe")

        def insert_foreign(parent, _staged, name):
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent)
            os.write(descriptor, b"foreign-final")
            os.close(descriptor)
            raise FileExistsError

        with mock.patch.object(brain, "_install_migration_at", side_effect=insert_foreign):
            with self.assertRaisesRegex(brain.AymtError, "prior retained at"):
                brain.write_aymt(self.root, changed)
        self.assertEqual(self.target.read_bytes(), b"foreign-final")
        backups = list((self.root / "00_Meta").glob(".AYMT.md.migrate-old-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), prior)
        self.assertEqual(list((self.root / "00_Meta").glob(".AYMT.md.migrate-new-*")), [])

    def test_last_boundary_mutation_preserves_foreign_and_prior_recovery(self):
        brain.write_aymt(self.root, self.desired)
        prior = self.target.read_bytes()
        changed = self.desired.replace(b"No safe", b"Still safe")
        original = brain._read_migration_at
        calls = 0

        def mutate_on_retirement(parent, name):
            nonlocal calls
            if name == "AYMT.md":
                calls += 1
                if calls == 5:
                    descriptor = os.open(name, os.O_WRONLY | os.O_TRUNC, dir_fd=parent)
                    os.write(descriptor, b"foreign-late")
                    os.close(descriptor)
            return original(parent, name)

        with mock.patch.object(brain, "_read_migration_at", side_effect=mutate_on_retirement):
            with self.assertRaises(brain.AymtError):
                brain.write_aymt(self.root, changed)
        self.assertEqual(self.target.read_bytes(), b"foreign-late")
        backups = list((self.root / "00_Meta").glob(".AYMT.md.migrate-old-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), prior)

    def test_check_rejects_mode_symlink_and_foreign_without_writes(self):
        self.target.write_bytes(self.desired)
        self.target.chmod(0o600)
        before = {path.name: (path.lstat().st_mode, path.read_bytes()) for path in (self.root / "00_Meta").iterdir()}
        args = SimpleNamespace(github_input=None, write=False, json=True, check=True, aymt_selection=UNCONFIGURED)
        with mock.patch.object(brain, "build_aymt", return_value=self.payload), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brain.cmd_aymt(self.root, args), 1)
        after = {path.name: (path.lstat().st_mode, path.read_bytes()) for path in (self.root / "00_Meta").iterdir()}
        self.assertEqual(after, before)

        self.target.unlink()
        foreign = self.root / "foreign"
        foreign.write_bytes(self.desired)
        self.target.symlink_to(foreign)
        before_target = os.readlink(self.target)
        with mock.patch.object(brain, "build_aymt", return_value=self.payload), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brain.cmd_aymt(self.root, args), 1)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(os.readlink(self.target), before_target)
        self.assertEqual(foreign.read_bytes(), self.desired)

        self.target.unlink()
        self.target.write_bytes(b"foreign")
        foreign_before = self.target.read_bytes()
        with mock.patch.object(brain, "build_aymt", return_value=self.payload), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brain.cmd_aymt(self.root, args), 1)
        self.assertEqual(self.target.read_bytes(), foreign_before)

    def test_unsupported_runtime_fails_before_write(self):
        with mock.patch.object(brain, "_migration_mutation_supported", return_value=False):
            with self.assertRaises(brain.AymtError):
                brain.write_aymt(self.root, self.desired)
        self.assertFalse(self.target.exists())

    def test_portable_check_stays_fresh_when_mutation_is_unsupported(self):
        self.target.write_bytes(self.desired)
        self.target.chmod(0o644)
        args = SimpleNamespace(github_input=None, write=False, json=True, check=True, aymt_selection=UNCONFIGURED)
        with (
            mock.patch.object(brain, "build_aymt", return_value=self.payload),
            mock.patch.object(brain, "_migration_mutation_supported", return_value=False),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(brain.cmd_aymt(self.root, args), 0)

    def test_missing_parent_preview_and_check_are_zero_write_and_redacted(self):
        (self.root / "00_Meta").rmdir()
        check_args = SimpleNamespace(github_input=None, write=False, json=True, check=True, aymt_selection=UNCONFIGURED)
        preview_args = SimpleNamespace(github_input=None, write=False, json=True, check=False, aymt_selection=UNCONFIGURED)
        for args, expected in ((check_args, 1), (preview_args, 0)):
            stdout = io.StringIO()
            with mock.patch.object(brain, "build_aymt", return_value=self.payload), contextlib.redirect_stdout(stdout):
                self.assertEqual(brain.cmd_aymt(self.root, args), expected)
            output = stdout.getvalue()
            self.assertNotIn(str(self.root), output)
            self.assertEqual(json.loads(output)["fresh"], False)
        self.assertFalse((self.root / "00_Meta").exists())


class AymtCliPrivacyTests(unittest.TestCase):
    def test_repository_has_exact_twenty_four_canonical_skills(self):
        root = Path(__file__).resolve().parents[4]
        names = sorted(
            path.parent.name
            for path in (root / "10_Agents/skills").glob("*/SKILL.md")
        )
        self.assertEqual(len(names), 24)
        self.assertIn("aymt", names)
        self.assertIn("generate-artifacts", names)
        wiring = (root / "10_Agents/harnesses/copilot/wiring.md").read_text(encoding="utf-8")
        self.assertIn("twenty-four canonical skill names", wiring)

    def test_selection_failure_codes_have_identical_redacted_cli_output(self):
        outputs = []
        for code in ("invalid-manifest", "ambiguous-fingerprint"):
            stdout = io.StringIO()
            with mock.patch.object(brain, "select_aymt_environment", side_effect=brain.EnvironmentSelectionError(code)), contextlib.redirect_stdout(stdout):
                exit_code = brain.main(["aymt", "--json"])
            self.assertEqual(exit_code, 1)
            outputs.append(stdout.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(json.loads(outputs[0]), {"error": "AYMT generation failed safely"})


if __name__ == "__main__":
    unittest.main()
