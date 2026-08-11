"""Mechanical contract tests for the agent-orientation output contract (#13).

Structure-only checks: required headings exist, required files exist. Full
sentences are deliberately NOT pinned (PR #33 lesson) — prose may be reworded
freely as long as the contract's structure stays intact.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
ORIENTATION = ROOT / "10_Agents/skills/agent-orientation/SKILL.md"
ENVIRONMENTS_README = ROOT / "10_Agents/environments/README.md"
RECOMMENDED_AUTOMATIONS = ROOT / "10_Agents/skills/recommended-automations/SKILL.md"
SELF_MAINTENANCE = ROOT / "10_Agents/skills/self-maintenance/SKILL.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def headings(text: str) -> list[str]:
    return [m.group(2).strip() for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.M)]


class OrientationOutputContractTests(unittest.TestCase):
    """The SKILL.md defines the required output contract structurally."""

    def test_skill_file_exists(self):
        self.assertTrue(ORIENTATION.is_file())

    def test_required_contract_section_headings_present(self):
        hs = headings(read(ORIENTATION))
        for required in [
            "Required output contract",
            "1. Solution inventory",
            "2. Harness introspection",
            "3. Ecosystem identification",
            "4. Environment capabilities & policy",
        ]:
            self.assertIn(required, hs, f"missing contract heading: {required}")

    def test_interface_ladder_heading_and_rungs_present(self):
        text = read(ORIENTATION)
        self.assertTrue(
            any(h.startswith("Interface ranking ladder") for h in headings(text)),
            "missing interface ranking ladder heading",
        )
        # Six numbered rungs, browser explicitly present as a rung (issue #13).
        # Scope the count to the ladder section so numbered-bold lists
        # elsewhere in the skill can't satisfy (or inflate) it.
        section = re.split(r"^#+ .*Interface ranking ladder.*$", text, flags=re.M)[1]
        section = re.split(r"^#+ ", section, maxsplit=1, flags=re.M)[0]
        rungs = re.findall(r"^[1-6]\. \*\*(.+?)\*\*", section, re.M)
        self.assertGreaterEqual(len(rungs), 6, "ladder must have six numbered rungs")
        joined = " ".join(rungs).lower()
        self.assertIn("browser", joined)
        self.assertIn("none", joined)

    def test_template_block_present_with_placeholders(self):
        text = read(ORIENTATION)
        self.assertTrue(
            any(h.startswith("Inventory note template") for h in headings(text)),
            "missing inventory note template heading",
        )
        self.assertIn("```markdown", text)
        self.assertIn("<env-slug>", text)

    def test_landing_convention_points_at_environments_dir(self):
        text = read(ORIENTATION)
        self.assertIn("10_Agents/environments/<env-slug>/", text)


class EnvironmentsConventionTests(unittest.TestCase):
    """Minimal landing convention (#13's slice of deferred #15)."""

    def test_environments_readme_exists_with_frontmatter(self):
        self.assertTrue(ENVIRONMENTS_README.is_file())
        text = read(ENVIRONMENTS_README)
        self.assertTrue(text.startswith("---"), "README must open with YAML frontmatter")
        for key in ("title:", "tags:", "updated:"):
            self.assertIn(key, text.split("---", 2)[1])

    def test_environments_readme_records_deferral(self):
        # Structural: the deferred-machinery marker (#15) must be referenced.
        self.assertIn("#15", read(ENVIRONMENTS_README))


class InventoryFeedTests(unittest.TestCase):
    """Downstream skills read the environment inventory note."""

    def test_recommended_automations_reads_inventory(self):
        self.assertIn(
            "10_Agents/environments/<env-slug>/orientation-inventory.md",
            read(RECOMMENDED_AUTOMATIONS),
        )

    def test_self_maintenance_reads_inventory(self):
        self.assertIn(
            "10_Agents/environments/<env-slug>/orientation-inventory.md",
            read(SELF_MAINTENANCE),
        )


class NeverBootstrapLinkedTests(unittest.TestCase):
    """The environments landing convention says inventory notes are never
    bootstrap-linked — enforce it mechanically over the bootstrap docs."""

    BOOTSTRAP_DOCS = [
        ROOT / "AGENTS.md",
        ROOT / "00_Meta" / "index.md",
        ROOT / "00_Meta" / "conventions.md",
        ROOT / "01_Profile" / "now.md",
        ROOT / "01_Profile" / "preferences.md",
        ROOT / "01_Profile" / "defaults.md",
    ]

    def test_no_bootstrap_wikilinks_into_environments(self):
        for doc in self.BOOTSTRAP_DOCS:
            if not doc.exists():
                continue
            for match in re.findall(r"\[\[([^\]|#]+)", doc.read_text(encoding="utf-8")):
                self.assertFalse(
                    match.strip().startswith("10_Agents/environments/"),
                    f"{doc.name} wikilinks into 10_Agents/environments/ — "
                    "environment notes must never be bootstrap-linked",
                )


if __name__ == "__main__":
    unittest.main()
