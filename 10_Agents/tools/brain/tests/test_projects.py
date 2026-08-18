"""Canonical Project/Area registry, reporting, rollup, and validation tests."""

from __future__ import annotations

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
import brain


def note(
    title: str,
    tags: tuple[str, ...],
    body: str,
    **frontmatter: str,
) -> str:
    extra = "".join(f"{key}: {value}\n" for key, value in frontmatter.items())
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n"
        + "".join(f"  - {tag}\n" for tag in tags)
        + extra
        + "updated: 2026-08-18\n"
        "---\n\n"
        f"# {title}\n\n{body.rstrip()}\n"
    )


class ProjectVault:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="projects-")
        self.root = Path(self.temp.name)

    def cleanup(self) -> None:
        self.temp.cleanup()

    def write(self, rel: str, content: str | bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def area(self, slug: str, title: str | None = None, body: str | None = None) -> None:
        title = title or slug.replace("-", " ").title()
        body = body or "## Standard to Maintain\n\nKeep it healthy.\n\n## Active Projects\n\n_None._"
        self.write(
            f"05_Areas/{slug}/AREA.md",
            note(title, ("type/area", "status/active", f"area/{slug}"), body),
        )

    def project(
        self,
        slug: str,
        *,
        title: str | None = None,
        status: str = "active",
        areas: tuple[str, ...] = ("home",),
        target: str | None = "2026-08-17",
        target_status: str | None = "estimated",
        criteria: str = "- The bounded outcome is verified.",
        archived: bool = False,
        extra_tags: tuple[str, ...] = (),
    ) -> None:
        title = title or slug.replace("-", " ").title()
        tags = (
            "type/project",
            f"status/{status}",
            f"project/{slug}",
            *(f"area/{area}" for area in areas),
            *extra_tags,
        )
        fields: dict[str, str] = {}
        if target is not None:
            fields["target"] = target
        if target_status is not None:
            fields["target_status"] = target_status
        if status == "done":
            fields["closed"] = "2026-08-18"
        area_lines = "\n".join(
            f"- [{area.title()}](../../05_Areas/{area}/AREA.md)" for area in areas
        )
        body = (
            "## Outcome\n\nShip the bounded outcome.\n\n"
            f"## Completion Criteria\n\n{criteria}\n\n"
            + ("## Final Outcome\n\nCompleted and verified.\n\n" if status == "done" else "")
            + f"## Areas\n\n{area_lines or '_None._'}"
        )
        prefix = "07_Archives/projects" if archived else "04_Projects"
        self.write(f"{prefix}/{slug}/PROJECT.md", note(title, tags, body, **fields))

    def model(self, today: date = date(2026, 8, 18)) -> dict:
        notes, assets = brain.walk_corpus(self.root, selected_environment=None)
        index = brain.build_index(self.root, notes, assets)
        return brain.build_entity_registry(self.root, index, today_d=today)


class EntityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.vault = ProjectVault()

    def tearDown(self):
        self.vault.cleanup()

    def test_exact_entrypoints_build_one_multi_area_project(self):
        self.vault.area("home", "Home")
        self.vault.area("health", "Health")
        self.vault.project("home-gym", areas=("home", "health"))
        self.vault.write(
            "04_Projects/home-gym/research.md",
            note(
                "Research",
                ("type/reference", "status/active", "project/home-gym"),
                "Supporting material, not another Project.",
            ),
        )

        model = self.vault.model()

        self.assertEqual(list(model["projects"]), ["home-gym"])
        project = model["projects"]["home-gym"]
        self.assertEqual(project["path"], "04_Projects/home-gym/PROJECT.md")
        self.assertEqual([area["slug"] for area in project["areas"]], ["health", "home"])
        self.assertTrue(project["hasCompletionCriteria"])
        self.assertTrue(project["overdue"])
        self.assertEqual(project["attention"], ["estimated-target", "overdue"])

    def test_deprioritized_and_archived_projects_are_not_active(self):
        self.vault.area("home")
        self.vault.project(
            "paused", status="deprioritized", target=None, target_status=None
        )
        self.vault.project(
            "finished", status="done", target=None, target_status=None, archived=True
        )

        model = self.vault.model()

        self.assertEqual(model["activeProjects"], [])
        self.assertEqual(model["projects"]["paused"]["lifecycle"], "deprioritized")
        self.assertTrue(model["projects"]["finished"]["archived"])

    def test_active_and_archived_slug_collision_is_recorded(self):
        self.vault.area("home")
        self.vault.project("duplicate")
        self.vault.project(
            "duplicate", status="done", target=None, target_status=None, archived=True
        )

        model = self.vault.model()

        self.assertEqual(model["collisions"], ["duplicate"])

    def test_archived_project_preserves_archived_area_relationship(self):
        self.vault.write(
            "07_Archives/areas/legacy/AREA.md",
            note(
                "Legacy",
                ("type/area", "status/done", "area/legacy"),
                "## Standard to Maintain\n\nHistorical context.",
            ),
        )
        self.vault.project(
            "finished",
            status="done",
            areas=("legacy",),
            target=None,
            target_status=None,
            archived=True,
        )

        model = self.vault.model()

        self.assertEqual(
            model["projects"]["finished"]["areas"],
            [
                {
                    "path": "07_Archives/areas/legacy/AREA.md",
                    "slug": "legacy",
                    "title": "Legacy",
                }
            ],
        )
        self.assertNotIn(
            "project-area-missing", {row["rule"] for row in model["findings"]}
        )

    def test_active_and_archived_area_slug_collision_is_recorded(self):
        self.vault.area("duplicate")
        self.vault.write(
            "07_Archives/areas/duplicate/AREA.md",
            note(
                "Duplicate",
                ("type/area", "status/done", "area/duplicate"),
                "Historical context.",
            ),
        )

        model = self.vault.model()

        self.assertEqual(model["areaCollisions"], ["duplicate"])
        self.assertIn("area-collision", {row["rule"] for row in model["findings"]})


class ProjectValidationTests(unittest.TestCase):
    def setUp(self):
        self.vault = ProjectVault()

    def tearDown(self):
        self.vault.cleanup()

    def findings(self) -> list[dict]:
        return self.vault.model()["findings"]

    def test_valid_entity_contract_has_no_findings(self):
        self.vault.area("home", body=(
            "## Standard to Maintain\n\nKeep it healthy.\n\n"
            "## Active Projects\n\n- [Valid](../../04_Projects/valid/PROJECT.md)"
        ))
        self.vault.project("valid", target="2026-12-01", target_status="confirmed")

        self.assertEqual(self.findings(), [])

    def test_reports_membership_lifecycle_target_criteria_and_rollup_drift(self):
        self.vault.area("home")
        self.vault.project(
            "broken",
            areas=("missing",),
            target=None,
            target_status=None,
            criteria="{{COMPLETION_CRITERIA}}",
            extra_tags=("status/someday",),
        )
        self.vault.write(
            "04_Projects/broken/support.md",
            note("Support", ("type/note", "area/home"), "Missing Project membership."),
        )

        rules = {finding["rule"] for finding in self.findings()}

        self.assertTrue(
            {
                "project-area-missing",
                "project-completion-criteria",
                "project-lifecycle",
                "project-membership-missing",
                "project-rollup-missing",
                "project-target-missing",
                "project-target-status",
                "project-area-on-supporting-note",
            }.issubset(rules)
        )

    def test_inactive_project_rejects_active_target_fields(self):
        self.vault.area("home")
        self.vault.project("paused", status="deprioritized")

        rules = {finding["rule"] for finding in self.findings()}

        self.assertIn("project-inactive-target", rules)

    def test_overdue_and_archive_pending_are_visible_attention(self):
        self.vault.area("home")
        self.vault.project("late", target="2026-08-17")
        self.vault.project(
            "closed", status="done", target=None, target_status=None
        )

        rules = {finding["rule"] for finding in self.findings()}

        self.assertIn("project-target-overdue", rules)
        self.assertIn("project-archive-pending", rules)

    def test_done_project_requires_closeout_date_and_final_outcome(self):
        self.vault.area("home")
        self.vault.write(
            "04_Projects/closed/PROJECT.md",
            note(
                "Closed",
                ("type/project", "status/done", "project/closed", "area/home"),
                "## Outcome\n\nShip it.\n\n## Completion Criteria\n\n- Verified.",
            ),
        )

        rules = {finding["rule"] for finding in self.findings()}

        self.assertIn("project-closeout-date", rules)
        self.assertIn("project-final-outcome", rules)

    def test_placeholder_outcomes_are_not_substantive(self):
        self.vault.area("home")
        self.vault.project("active-placeholder", target="2026-12-01")
        active = self.vault.root / "04_Projects/active-placeholder/PROJECT.md"
        active.write_text(
            active.read_text(encoding="utf-8").replace(
                "Ship the bounded outcome.", "TBD"
            ),
            encoding="utf-8",
        )
        self.vault.project(
            "done-placeholder",
            status="done",
            target=None,
            target_status=None,
        )
        done = self.vault.root / "04_Projects/done-placeholder/PROJECT.md"
        done.write_text(
            done.read_text(encoding="utf-8").replace(
                "Completed and verified.", "None"
            ),
            encoding="utf-8",
        )

        by_path = {
            (finding["path"], finding["rule"])
            for finding in self.findings()
        }

        self.assertIn(
            ("04_Projects/active-placeholder/PROJECT.md", "project-outcome"),
            by_path,
        )
        self.assertIn(
            ("04_Projects/done-placeholder/PROJECT.md", "project-final-outcome"),
            by_path,
        )

    def test_area_rollup_rejects_inactive_or_unmapped_project(self):
        self.vault.area(
            "home",
            body=(
                "## Standard to Maintain\n\nKeep it healthy.\n\n"
                "## Active Projects\n\n"
                "- [Paused](../../04_Projects/paused/PROJECT.md)"
            ),
        )
        self.vault.project(
            "paused", status="deprioritized", target=None, target_status=None
        )

        rules = {finding["rule"] for finding in self.findings()}

        self.assertIn("area-rollup-drift", rules)

    def test_type_meta_supporting_note_is_membership_exempt(self):
        self.vault.area("home")
        self.vault.project("valid", target="2026-12-01")
        self.vault.write(
            "04_Projects/valid/README.md",
            note("Guide", ("type/meta",), "Directory guide."),
        )

        rules = {finding["rule"] for finding in self.findings()}

        self.assertNotIn("project-membership-missing", rules)

    def test_archived_area_supporting_note_requires_membership(self):
        self.vault.write(
            "07_Archives/areas/legacy/AREA.md",
            note(
                "Legacy",
                ("type/area", "status/done", "area/legacy"),
                "Historical context.",
            ),
        )
        self.vault.write(
            "07_Archives/areas/legacy/context.md",
            note("Context", ("type/note",), "Missing archived Area membership."),
        )

        findings = self.findings()

        self.assertIn(
            {
                "line": None,
                "message": "Supporting note must carry area/legacy",
                "path": "07_Archives/areas/legacy/context.md",
                "rule": "area-membership-missing",
            },
            findings,
        )

    def test_validate_surfaces_entity_contract_as_warnings(self):
        self.vault.area("home")
        self.vault.project(
            "paused", status="deprioritized", target="2026-12-01"
        )

        _errors, warnings = brain.run_validate(self.vault.root, False)

        self.assertIn(
            "project-inactive-target", {finding["rule"] for finding in warnings}
        )


class ProjectRollupTests(unittest.TestCase):
    def setUp(self):
        self.vault = ProjectVault()

    def tearDown(self):
        self.vault.cleanup()

    def test_rollup_preview_write_and_second_write_are_idempotent(self):
        self.vault.area(
            "home",
            "Home",
            "Intro that must survive.\n\n## Active Projects\n\n- [Stale](../../04_Projects/stale/PROJECT.md)\n\n## Notes\n\nKeep this too.",
        )
        self.vault.project("valid", title="Valid Project", target="2026-12-01")
        model = self.vault.model()

        preview = brain.reconcile_project_rollups(self.vault.root, model, write=False)
        self.assertEqual([row["path"] for row in preview["changes"]], ["05_Areas/home/AREA.md"])
        self.assertFalse(preview["written"])

        applied = brain.reconcile_project_rollups(self.vault.root, model, write=True)
        self.assertTrue(applied["written"])
        content = (self.vault.root / "05_Areas/home/AREA.md").read_text()
        self.assertIn("Intro that must survive.", content)
        self.assertIn("## Notes\n\nKeep this too.", content)
        self.assertIn("[Valid Project](../../04_Projects/valid/PROJECT.md)", content)
        self.assertNotIn("Stale", content)

        second = brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=True
        )
        self.assertEqual(second["changes"], [])
        self.assertFalse(second["written"])

    def test_canonical_rollup_format_is_already_idempotent(self):
        self.vault.area(
            "home",
            body=(
                "## Standard to Maintain\n\nKeep it healthy.\n\n"
                "## Active Projects\n\n"
                "- [Valid](../../04_Projects/valid/PROJECT.md)\n\n"
                "## Notes\n\nKeep this too."
            ),
        )
        self.vault.project("valid", title="Valid", target="2026-12-01")

        preview = brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=False
        )

        self.assertEqual(preview["changes"], [])

    def test_rollup_write_preserves_area_updated_outside_owned_section(self):
        self.vault.area("home")
        self.vault.project("valid", target="2026-12-01")

        brain.reconcile_project_rollups(
            self.vault.root,
            self.vault.model(today=date(2026, 8, 19)),
            write=True,
        )

        content = (self.vault.root / "05_Areas/home/AREA.md").read_text()
        self.assertIn("updated: 2026-08-18", content)

    def test_fenced_heading_is_not_treated_as_owned_rollup_section(self):
        self.vault.area(
            "home",
            body=(
                "```markdown\n## Active Projects\n"
                "- [Illustration](../../04_Projects/illustration/PROJECT.md)\n```\n\n"
                "## Active Projects\n\n- [Stale](../../04_Projects/stale/PROJECT.md)\n\n"
                "## Notes\n\nKeep this too."
            ),
        )
        self.vault.project("valid", title="Valid", target="2026-12-01")

        brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=True
        )

        content = (self.vault.root / "05_Areas/home/AREA.md").read_text()
        self.assertIn(
            "## Active Projects\n- [Illustration]"
            "(../../04_Projects/illustration/PROJECT.md)",
            content,
        )
        self.assertIn("[Valid](../../04_Projects/valid/PROJECT.md)", content)
        self.assertNotIn("[Stale]", content)

    def test_rollup_refuses_restricted_project_into_unrestricted_area(self):
        self.vault.area("home")
        self.vault.project(
            "private-project",
            title="PRIVATE PROJECT TITLE",
            target="2026-12-01",
            extra_tags=("restricted/private",),
        )
        path = self.vault.root / "05_Areas/home/AREA.md"
        before = path.read_bytes()

        preview = brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=False
        )
        applied = brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=True
        )

        self.assertEqual(preview["blockers"], applied["blockers"])
        self.assertEqual(
            preview["blockers"],
            [
                {
                    "message": (
                        "Restricted Project mapping cannot enter an unrestricted "
                        "Area rollup"
                    ),
                    "path": "05_Areas/home/AREA.md",
                    "rule": "restricted-project-unrestricted-area",
                }
            ],
        )
        self.assertFalse(applied["written"])
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn(b"PRIVATE PROJECT TITLE", path.read_bytes())
        self.assertNotIn(b"private-project", path.read_bytes())

    def test_rollup_escapes_labels_and_encodes_destinations(self):
        self.vault.area("home")
        self.vault.project(
            "odd name", title="A [bracket] \\ title", target="2026-12-01"
        )

        brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=True
        )

        content = (self.vault.root / "05_Areas/home/AREA.md").read_text()
        self.assertIn(
            "[A \\[bracket\\] \\\\ title]"
            "(../../04_Projects/odd%20name/PROJECT.md)",
            content,
        )

    def test_rollup_preserves_bom_crlf_final_newline_and_outside_bytes(self):
        area_text = note(
            "Home",
            ("type/area", "status/active", "area/home"),
            "Before.\n\n## Active Projects\n\n- [Stale](stale.md)\n\n"
            "## Notes\n\nAfter without a final newline.",
        ).rstrip("\n")
        before = b"\xef\xbb\xbf" + area_text.replace("\n", "\r\n").encode()
        path = self.vault.write("05_Areas/home/AREA.md", before)
        self.vault.project("valid", title="Valid", target="2026-12-01")
        heading_end = before.index(b"## Active Projects") + len(b"## Active Projects")
        notes_start = before.index(b"## Notes")

        brain.reconcile_project_rollups(
            self.vault.root, self.vault.model(), write=True
        )

        after = path.read_bytes()
        after_heading_end = after.index(b"## Active Projects") + len(
            b"## Active Projects"
        )
        after_notes_start = after.index(b"## Notes")
        self.assertEqual(before[:heading_end], after[:after_heading_end])
        self.assertEqual(before[notes_start:], after[after_notes_start:])
        self.assertTrue(after.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n", after.replace(b"\r\n", b""))
        self.assertFalse(after.endswith((b"\r", b"\n")))
        self.assertIn(b"updated: 2026-08-18", after)
        self.assertIn(
            b"[Valid](../../04_Projects/valid/PROJECT.md)", after
        )

    def test_rollup_refuses_when_project_mapping_source_changed(self):
        self.vault.area("home")
        self.vault.project("valid", target="2026-12-01")
        model = self.vault.model()
        project = self.vault.root / "04_Projects/valid/PROJECT.md"
        project.write_text(project.read_text() + "\nChanged after registry build.\n")
        before = (self.vault.root / "05_Areas/home/AREA.md").read_bytes()

        result = brain.reconcile_project_rollups(self.vault.root, model, write=True)

        self.assertFalse(result["written"])
        self.assertEqual(
            [row["rule"] for row in result["blockers"]],
            ["project-rollup-source-changed"],
        )
        self.assertEqual(
            (self.vault.root / "05_Areas/home/AREA.md").read_bytes(), before
        )

    def test_rollup_compare_and_swap_preserves_concurrent_area_edit(self):
        self.vault.area("home")
        self.vault.project("valid", target="2026-12-01")
        model = self.vault.model()
        path = self.vault.root / "05_Areas/home/AREA.md"
        owner_edit = path.read_bytes() + b"\nOwner edit.\n"
        real_write = brain._archive_write_guarded

        def race(target, content, mode, expected):
            target.write_bytes(owner_edit)
            return real_write(target, content, mode, expected)

        with (
            mock.patch.object(brain, "_archive_write_guarded", side_effect=race),
            self.assertRaises(brain.ProjectArchiveError),
        ):
            brain.reconcile_project_rollups(self.vault.root, model, write=True)

        self.assertEqual(path.read_bytes(), owner_edit)

    def test_rollup_recovery_preserves_owner_edit_and_requires_manual_review(self):
        self.vault.area("alpha")
        self.vault.area("beta")
        self.vault.project(
            "valid", areas=("alpha", "beta"), target="2026-12-01"
        )
        model = self.vault.model()
        alpha = self.vault.root / "05_Areas/alpha/AREA.md"
        beta = self.vault.root / "05_Areas/beta/AREA.md"
        alpha_owner = alpha.read_bytes() + b"\nOwner alpha edit.\n"
        beta_owner = beta.read_bytes() + b"\nOwner beta edit.\n"
        real_write = brain._archive_write_guarded
        calls = 0

        def race(target, content, mode, expected):
            nonlocal calls
            calls += 1
            if calls == 2:
                beta.write_bytes(beta_owner)
            elif calls == 3:
                alpha.write_bytes(alpha_owner)
            return real_write(target, content, mode, expected)

        with (
            mock.patch.object(brain, "_archive_write_guarded", side_effect=race),
            self.assertRaises(brain.ProjectRollupRecoveryRequired),
        ):
            brain.reconcile_project_rollups(self.vault.root, model, write=True)

        self.assertEqual(alpha.read_bytes(), alpha_owner)
        self.assertEqual(beta.read_bytes(), beta_owner)


class ProjectsCliTests(unittest.TestCase):
    def test_json_lists_active_projects_without_environment_selection(self):
        vault = ProjectVault()
        self.addCleanup(vault.cleanup)
        vault.area(
            "home",
            body=(
                "## Standard to Maintain\n\nKeep it healthy.\n\n"
                "## Active Projects\n\n- [Valid](../../04_Projects/valid/PROJECT.md)"
            ),
        )
        vault.project("valid", target="2026-12-01", target_status="confirmed")
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            code = brain.main(
                ["projects", "--vault", str(vault.root), "--json"]
            )

        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual([row["slug"] for row in payload["projects"]], ["valid"])

    def test_human_output_includes_project_attention_findings_and_digests(self):
        vault = ProjectVault()
        self.addCleanup(vault.cleanup)
        vault.area("home")
        vault.project("valid", target="2026-12-01", target_status="estimated")
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            code = brain.main(["projects", "--vault", str(vault.root)])

        output = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("target 2026-12-01 (estimated)", output)
        self.assertIn("criteria: yes", output)
        self.assertIn("attention: estimated-target", output)
        self.assertRegex(output, r"[0-9a-f]{64} -> [0-9a-f]{64}")
        self.assertIn(
            "project-rollup-missing  04_Projects/valid/PROJECT.md:", output
        )

    def test_preview_reports_restricted_rollup_blocker_without_failing(self):
        vault = ProjectVault()
        self.addCleanup(vault.cleanup)
        vault.area("home")
        vault.project(
            "private-project",
            title="PRIVATE PROJECT TITLE",
            target="2026-12-01",
            extra_tags=("restricted/private",),
        )
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            code = brain.main(
                ["projects", "--vault", str(vault.root), "--json"]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(
            payload["rollups"]["blockers"],
            [
                {
                    "message": (
                        "Restricted Project mapping cannot enter an unrestricted "
                        "Area rollup"
                    ),
                    "path": "05_Areas/home/AREA.md",
                    "rule": "restricted-project-unrestricted-area",
                }
            ],
        )
        self.assertNotIn(
            "PRIVATE PROJECT TITLE", json.dumps(payload["rollups"]["blockers"])
        )
        self.assertNotIn(
            "private-project", json.dumps(payload["rollups"]["blockers"])
        )

        write_stdout = io.StringIO()
        with contextlib.redirect_stdout(write_stdout):
            write_code = brain.main(
                [
                    "projects",
                    "--vault",
                    str(vault.root),
                    "--write-rollups",
                    "--json",
                ]
            )
        self.assertEqual(write_code, 1)
        self.assertEqual(
            json.loads(write_stdout.getvalue())["rollups"]["blockers"],
            payload["rollups"]["blockers"],
        )

    def test_recovery_required_has_distinct_machine_readable_response(self):
        vault = ProjectVault()
        self.addCleanup(vault.cleanup)
        vault.area("home")
        vault.project("valid", target="2026-12-01")
        stdout = io.StringIO()

        with (
            mock.patch.object(
                brain,
                "reconcile_project_rollups",
                side_effect=brain.ProjectRollupRecoveryRequired,
            ),
            contextlib.redirect_stdout(stdout),
        ):
            code = brain.main(
                [
                    "projects",
                    "--vault",
                    str(vault.root),
                    "--write-rollups",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(payload["code"], "project-rollup-recovery-required")
        self.assertTrue(payload["recoveryRequired"])
        self.assertIn("preserve owner edits", payload["remediation"])


class ProjectTagDriftTests(unittest.TestCase):
    def test_membership_namespaces_skip_single_use_and_near_duplicate_noise(self):
        index = {
            "notes": {
                "a.md": {
                    "backlinks": [],
                    "frontmatter": {"tags": ["project/ai", "area/home"]},
                    "headings": [],
                    "links": [],
                    "title": "A",
                    "updated": "2026-08-18",
                },
                "b.md": {
                    "backlinks": [],
                    "frontmatter": {"tags": ["project/ai-tools", "area/homes"]},
                    "headings": [],
                    "links": [],
                    "title": "B",
                    "updated": "2026-08-18",
                },
            }
        }
        taxonomy = {"project": None, "area": None}

        report = brain.compute_report(
            index,
            date(2026, 8, 18),
            {"staleDays": 90, "inboxDays": 14},
            taxonomy,
        )

        self.assertEqual(report["tagDrift"]["singleUse"], [])
        self.assertEqual(report["tagDrift"]["nearDuplicates"], [])


if __name__ == "__main__":
    unittest.main()
