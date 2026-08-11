"""Mechanical contract tests for onboard-owner's people-map and
vault-intent/role stages (#14).

Structure-only checks: required stage names and section headings exist,
standing-exception bullets mention the people-map destination. Full sentences
are deliberately NOT pinned (PR #33 lesson) — prose may be reworded freely as
long as the structure stays intact.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
ONBOARD_OWNER = ROOT / "10_Agents/skills/onboard-owner/SKILL.md"
AGENTS = ROOT / "AGENTS.md"
CONVENTIONS = ROOT / "00_Meta/CONVENTIONS.md"

PEOPLE_DIR = "03_Journal/people/"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def headings(text: str) -> list[str]:
    return [m.group(2).strip() for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.M)]


def stage_names(text: str) -> list[str]:
    """Bold stage names from the numbered Stages list (e.g. '1. **Welcome.**')."""
    return [m.group(1) for m in re.finditer(r"^\d+\. \*\*(.+?)\*\*", text, re.M)]


class OnboardOwnerStagesTests(unittest.TestCase):
    """The two #14 stages exist in the skill, structurally."""

    def test_skill_file_exists(self):
        self.assertTrue(ONBOARD_OWNER.is_file())

    def test_intent_and_people_map_stages_present(self):
        names = " ".join(stage_names(read(ONBOARD_OWNER))).lower()
        self.assertIn("vault intent", names, "missing vault-intent/role stage")
        self.assertIn("people map", names, "missing people-map stage")

    def test_people_map_destination_and_source_list(self):
        text = read(ONBOARD_OWNER)
        self.assertIn(PEOPLE_DIR, text, "people map must land in 03_Journal/people/")
        self.assertIn(
            "orientation-inventory.md",
            text,
            "observable sources must come from the #13 orientation inventory",
        )

    def test_sensitivity_rule_quoted(self):
        # Fragment of the PRD §16.2 third-party rule, quoted in the stage.
        self.assertIn("stand behind if read back", read(ONBOARD_OWNER))

    def test_role_destinations_referenced(self):
        text = read(ONBOARD_OWNER)
        self.assertIn("01_Profile/WORK", text)
        self.assertIn("01_Profile/IDENTITY", text)

    def test_specialization_recorded_in_config_not_duplicated(self):
        # The intent answer still records context: in config exactly once
        # (the M9.4 stage is integrated, not duplicated).
        text = read(ONBOARD_OWNER)
        self.assertEqual(text.count("`context: work` or `context: personal`"), 1)

    def test_worked_example_present(self):
        text = read(ONBOARD_OWNER)
        self.assertTrue(
            any(h.lower().startswith("people map: worked example") for h in headings(text)),
            "missing people-map worked example section",
        )
        self.assertIn("```markdown", text)

    def test_starter_intent_is_open_recommendable_and_reversible(self):
        text = read(ONBOARD_OWNER).lower()
        for choice in ("work", "personal life", "exploring both", "not sure yet"):
            with self.subTest(choice=choice):
                self.assertIn(choice, text)
        self.assertIn("free-form answer", text)
        self.assertIn("recommend exactly one", text)
        self.assertIn("explain why in one sentence", text)
        self.assertIn("change direction later", text)
        self.assertIn("otherwise present all four neutrally", text)

    def test_example_cleanup_is_manifest_owned_and_atomic(self):
        text = read(ONBOARD_OWNER)
        self.assertIn("sole authority is `10_Agents/tools/adopt_examples.json`", text)
        self.assertIn("never offer selective deletion", text)
        self.assertIn("exact all-or-nothing deletion", text)
        self.assertIn("changed/dirty inputs", text)
        self.assertIn("keep the whole bundle", text)

    def test_people_guidance_never_depends_on_deleted_example(self):
        text = read(ONBOARD_OWNER)
        self.assertIn("[[03_Journal/people/README|people-note guidance]]", text)
        self.assertNotIn("example-person", text)


class StandingExceptionTests(unittest.TestCase):
    """Both standing-exception bullets cover the people-map destination."""

    def test_agents_md_exception_mentions_people_dir(self):
        self.assertIn(PEOPLE_DIR, read(AGENTS))

    def test_conventions_exception_mentions_people_dir(self):
        self.assertIn(PEOPLE_DIR, read(CONVENTIONS))

    def test_skill_write_policy_mentions_people_dir(self):
        # The skill's own write-policy section names the destination too.
        write_policy = read(ONBOARD_OWNER).split("## Write policy")[1].split("##")[0]
        self.assertIn(PEOPLE_DIR, write_policy)


if __name__ == "__main__":
    unittest.main()
