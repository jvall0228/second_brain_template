"""§10.2 Agent Skills contract with group directories (e.g. setup/)."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402
from test_brain import FIXTURE, make_vault, note  # noqa: E402

CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(encoding="utf-8")


def skill(name: str, description: str = "Does a thing.") -> str:
    return (
        f"---\nname: {name}\ndescription: {description}\ntitle: {name}\ntags:\n  - type/reference\n"
        "updated: 2026-08-11\n---\n\n# Skill\n"
    )


class SkillGroupTests(unittest.TestCase):
    def validate(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), {"00_Meta/CONVENTIONS.md": CONVENTIONS, **files})
            errors, _ = brain.run_validate(root, check_index=False)
            return [(e["path"], e["rule"]) for e in errors if e["rule"].startswith("skill-")]

    def test_nested_skill_and_group_readme_are_clean(self):
        files = {
            "10_Agents/skills/flat/SKILL.md": skill("flat"),
            "10_Agents/skills/setup/README.md": note(),
            "10_Agents/skills/setup/nested/SKILL.md": skill("nested"),
            "10_Agents/skills/setup/nested/notes/extra.md": note(),
        }
        self.assertEqual(self.validate(files), [])

    def test_group_without_skills_and_nested_name_mismatch(self):
        files = {
            "10_Agents/skills/lonely/README.md": note(),
            "10_Agents/skills/setup/wrong/SKILL.md": skill("other"),
        }
        self.assertEqual(
            self.validate(files),
            [
                ("10_Agents/skills/lonely/", "skill-missing"),
                ("10_Agents/skills/setup/wrong/SKILL.md", "skill-name-mismatch"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
