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

    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
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
        area_lines = "\n".join(
            f"- [{area.title()}](../../05_Areas/{area}/AREA.md)" for area in areas
        )
        body = (
            "## Outcome\n\nShip the bounded outcome.\n\n"
            f"## Completion Criteria\n\n{criteria}\n\n"
            f"## Areas\n\n{area_lines or '_None._'}"
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
