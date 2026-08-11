"""Contract tests for the sync-upstream skill (issue #6, M12.1).

Mechanical structure checks only: the skill file exists with its required
frontmatter and stage headings; the classify path map is parsed from the
SKILL.md table and checked for exact, exhaustive, non-overlapping coverage
of the repo's top-level paths; override rows refine paths the map covers.
No prose is pinned.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILL = ROOT / "10_Agents/skills/sync-upstream/SKILL.md"
SKILLS_README = ROOT / "10_Agents/skills/README.md"

LANES = {"machinery", "owner-content", "canonical-docs"}
# Top-level entries that are not template content and never sync.
IGNORED_TOP_LEVEL = {".git", ".DS_Store"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Body of a markdown section from its heading line to the next heading
    of the same or higher level."""
    match = re.search(
        rf"^(#+) {re.escape(heading)}\s*$(.*?)(?=^#+ |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(2) if match else ""


def table_rows(body: str) -> list[list[str]]:
    """Data rows of the first markdown table in body: lists of cell strings,
    header and separator rows dropped."""
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set(":- ") for c in cells):
            continue  # separator row
        rows.append(cells)
    return rows[1:] if rows else []  # drop the header row


def first_backticked(cell: str) -> str | None:
    match = re.search(r"`([^`]+)`", cell)
    return match.group(1) if match else None


class SyncUpstreamSkillFileTests(unittest.TestCase):
    def test_skill_exists_with_contract_frontmatter(self):
        self.assertTrue(SKILL.is_file())
        text = read(SKILL)
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---", 2)[1]
        self.assertIn("name: sync-upstream", frontmatter)
        for key in ("description:", "title:", "tags:", "updated:"):
            self.assertIn(key, frontmatter)

    def test_required_stage_headings_present(self):
        text = read(SKILL)
        for heading in (
            "## Ground rules",
            "## Detect",
            "## Classify",
            "## Apply",
            "## Backfill",
            "## Report",
            "## Upstream release duty",
        ):
            self.assertRegex(text, rf"(?m)^{re.escape(heading)}\s*$")

    def test_registered_in_skills_readme(self):
        self.assertIn("sync-upstream/SKILL", read(SKILLS_README))


class ClassifyTableCoverageTests(unittest.TestCase):
    """The heart of the skill: every top-level path in today's repo is
    covered by exactly one lane in the SKILL.md path map."""

    def path_map(self) -> dict[str, str]:
        rows = table_rows(section(read(SKILL), "Path map"))
        self.assertTrue(rows, "no path-map table found under '### Path map'")
        mapping: dict[str, str] = {}
        for cells in rows:
            self.assertGreaterEqual(len(cells), 2, cells)
            path = first_backticked(cells[0])
            self.assertIsNotNone(path, f"path-map row without a `path`: {cells}")
            self.assertNotIn(path, mapping, f"duplicate path-map row: {path}")
            mapping[path] = cells[1]
        return mapping

    def repo_top_level(self) -> set[str]:
        entries = set()
        for entry in ROOT.iterdir():
            if entry.name in IGNORED_TOP_LEVEL:
                continue
            entries.add(entry.name + "/" if entry.is_dir() else entry.name)
        return entries

    # Template-shipped top-level entries the path map must always cover.
    # Fork-added top-level paths are deliberately NOT failures: the skill's
    # "when in doubt, treat as owner content" ground rule classifies them,
    # and a fork's own additions must not break its test suite.
    TEMPLATE_TOP_LEVEL = frozenset(
        {
            "AGENTS.md", "CLAUDE.md", "README.md",
            "00_Meta/", "01_Profile/", "02_Inbox/", "02_Outbox/",
            "03_Journal/", "04_Projects/", "05_Areas/", "06_Resources/",
            "07_Archives/", "08_Assets/", "09_Templates/", "10_Agents/",
        }
    )

    def test_every_template_top_level_path_covered(self):
        mapping = self.path_map()
        repo = self.repo_top_level()
        self.assertEqual(
            (self.TEMPLATE_TOP_LEVEL & repo) - set(mapping),
            set(),
            "template top-level paths missing from the classify path map",
        )
        # Rows must name real paths — but only template-known ones are
        # required, so a leaner fork doesn't fail on rows for pruned dirs.
        self.assertEqual(
            (set(mapping) & self.TEMPLATE_TOP_LEVEL) - repo,
            set(),
            "classify rows naming template paths absent from this tree",
        )

    def test_every_lane_is_a_known_lane(self):
        for path, lane in self.path_map().items():
            self.assertIn(lane, LANES, f"{path}: unknown lane {lane!r}")

    def test_all_three_lanes_are_used(self):
        self.assertEqual(set(self.path_map().values()), LANES)

    def test_owner_dirs_are_never_machinery(self):
        """The never-touch guarantee for the owner's data directories is
        structural: profile, journal, PARA, and the in/out boxes."""
        mapping = self.path_map()
        for path in (
            "01_Profile/",
            "02_Inbox/",
            "02_Outbox/",
            "03_Journal/",
            "04_Projects/",
            "05_Areas/",
            "06_Resources/",
            "07_Archives/",
        ):
            self.assertEqual(mapping.get(path), "owner-content", path)

    def test_override_rows_refine_mapped_paths(self):
        mapping = self.path_map()
        rows = table_rows(section(read(SKILL), "Overrides"))
        self.assertTrue(rows, "no overrides table found under '### Overrides'")
        for cells in rows:
            self.assertGreaterEqual(len(cells), 2, cells)
            path = first_backticked(cells[0])
            self.assertIsNotNone(path, f"override row without a `path`: {cells}")
            self.assertTrue(
                any(path.startswith(top) for top in mapping),
                f"override path {path!r} is under no path-map entry",
            )
            self.assertIn(cells[1], LANES, f"{path}: unknown lane {cells[1]!r}")
            if (ROOT / path).suffix or path.endswith("/"):
                self.assertTrue((ROOT / path).exists(), f"stale override path {path!r}")


if __name__ == "__main__":
    unittest.main()
