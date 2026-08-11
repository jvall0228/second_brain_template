"""Contract tests for the recommended community skills catalog (issue #7).

Mechanical structure checks only: the catalog note exists, every catalog item
carries either a Tracks branch ref or an explicit TODO-pin marker (community
components track their upstream branch and install latest, not a frozen SHA),
and the install/link surfaces reference the catalog. No prose is pinned.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CATALOG = ROOT / "06_Resources/recommended-skills.md"
SKILLS_README = ROOT / "10_Agents/skills/README.md"
ONBOARD = ROOT / "10_Agents/skills/onboard-harness/SKILL.md"

# A Tracks ref names the upstream branch the item follows (e.g. "@ `main`") or
# marks it "(latest)" — the install pulls that branch's tip, not a frozen SHA.
TRACKS_REF = re.compile(r"@\s*`[\w./-]+`|\(latest", re.IGNORECASE)
TODO_PIN = "TODO-pin"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def catalog_items(text: str) -> dict[str, str]:
    """Return {item-name: section-body} for ### sections under ## Catalog."""
    match = re.search(r"^## Catalog\s*$(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    section = match.group(1)
    items: dict[str, str] = {}
    parts = re.split(r"^### +(.+?)\s*$", section, flags=re.MULTILINE)
    for name, body in zip(parts[1::2], parts[2::2]):
        items[name.strip()] = body
    return items


class RecommendedSkillsCatalogTests(unittest.TestCase):
    def test_catalog_note_exists_with_frontmatter(self):
        self.assertTrue(CATALOG.is_file())
        text = read(CATALOG)
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---", 2)[1]
        for key in ("title:", "tags:", "updated:"):
            self.assertIn(key, frontmatter)

    def test_catalog_has_items(self):
        items = catalog_items(read(CATALOG))
        self.assertGreaterEqual(len(items), 2)

    def test_every_item_has_tracks_ref_or_todo_marker(self):
        for name, body in catalog_items(read(CATALOG)).items():
            with self.subTest(item=name):
                track_lines = [
                    line
                    for line in body.splitlines()
                    if re.match(r"^\s*-\s+\*\*Tracks:?\*\*", line)
                ]
                self.assertEqual(
                    len(track_lines), 1, f"item {name!r} needs exactly one Tracks field"
                )
                line = track_lines[0]
                self.assertTrue(
                    TRACKS_REF.search(line) or TODO_PIN in line,
                    f"item {name!r} Tracks must name a branch (e.g. \"@ `main`\" / "
                    f"\"(latest)\") or carry the {TODO_PIN} marker: {line!r}",
                )

    def test_every_item_has_required_fields(self):
        required = ("**Upstream:**", "**License:**", "**What it does:**",
                    "**Trust note:**", "**Sign-off:**")
        for name, body in catalog_items(read(CATALOG)).items():
            for field in required:
                with self.subTest(item=name, field=field):
                    self.assertIn(field, body)

    def test_skills_readme_links_to_catalog(self):
        self.assertIn("06_Resources/recommended-skills", read(SKILLS_README))

    def test_onboard_harness_references_catalog_and_signoff(self):
        text = read(ONBOARD)
        self.assertIn("06_Resources/recommended-skills", text)
        self.assertIn(TODO_PIN, text)


if __name__ == "__main__":
    unittest.main()
