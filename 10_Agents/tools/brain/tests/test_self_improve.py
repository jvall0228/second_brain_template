"""Contract tests for the self-improve skill (issue #22, M12.2).

Mechanical structure checks only: the skill file exists with its required
frontmatter and stage headings; the rejected-proposals log exists with valid
frontmatter and its append-only table header; the operating rules carry the
never-push-upstream line; the skill is registered in the skills README stage
table and cadence table. No prose is pinned.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILL = ROOT / "10_Agents/skills/self-improve/SKILL.md"
REJECTED = ROOT / "10_Agents/docs/rejected-proposals.md"
OPERATING_RULES = ROOT / "10_Agents/docs/OPERATING-RULES.md"
SKILLS_README = ROOT / "10_Agents/skills/README.md"
AUTOMATIONS = ROOT / "10_Agents/skills/recommended-automations/SKILL.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> str:
    return text.split("---", 2)[1] if text.startswith("---\n") else ""


class SelfImproveSkillFileTests(unittest.TestCase):
    def test_skill_exists_with_contract_frontmatter(self):
        self.assertTrue(SKILL.is_file())
        text = read(SKILL)
        self.assertTrue(text.startswith("---\n"))
        fm = frontmatter(text)
        self.assertIn("name: self-improve", fm)
        for key in ("description:", "title:", "tags:", "updated:"):
            self.assertIn(key, fm)

    def test_required_stage_headings_present(self):
        text = read(SKILL)
        for heading in (
            "## Ground rules (guardrails)",
            "## Observe",
            "## Propose",
            "## Owner review",
            "## Record rejections",
            "## Recur",
            "## Worked example (dry-run cycle)",
        ):
            self.assertRegex(text, rf"(?m)^{re.escape(heading)}\s*$")

    def test_skill_states_the_upstream_boundary(self):
        self.assertIn("Never push upstream", read(SKILL))

    def test_skill_consults_rejection_log(self):
        self.assertIn("rejected-proposals", read(SKILL))


class RejectedProposalsLogTests(unittest.TestCase):
    def test_log_exists_with_valid_frontmatter(self):
        self.assertTrue(REJECTED.is_file())
        text = read(REJECTED)
        self.assertTrue(text.startswith("---\n"))
        fm = frontmatter(text)
        for key in ("title:", "tags:", "updated:"):
            self.assertIn(key, fm)

    def test_log_has_the_append_only_table_header(self):
        text = read(REJECTED)
        header = next(
            (
                line
                for line in text.splitlines()
                if line.strip().startswith("|") and "Date" in line
            ),
            None,
        )
        self.assertIsNotNone(header, "no table header row found")
        cells = [c.strip().lower() for c in header.strip().strip("|").split("|")]
        for column in ("date", "proposal"):
            self.assertTrue(
                any(column in cell for cell in cells),
                f"table header lacks a {column!r} column: {header!r}",
            )


class RegistrationTests(unittest.TestCase):
    def test_operating_rules_state_never_push_upstream(self):
        self.assertIn("Never push upstream", read(OPERATING_RULES))

    def test_registered_in_skills_readme_stage_table(self):
        self.assertIn("self-improve/SKILL", read(SKILLS_README))

    def test_cadence_table_has_a_self_improve_row(self):
        rows = [
            line
            for line in read(SKILLS_README).splitlines()
            if line.strip().startswith("|") and "self-improve/SKILL" in line
        ]
        self.assertTrue(rows, "no cadence/stage table row mentions self-improve")
        monthly = [r for r in rows if r.strip("| ").startswith("Monthly")]
        self.assertTrue(monthly, "no Monthly cadence row includes self-improve")

    def test_recommended_automations_lists_the_rhythm_job(self):
        self.assertIn("self-improve", read(AUTOMATIONS))


if __name__ == "__main__":
    unittest.main()
