"""Repository-level portable Markdown link contract tests (issue #74/WP9)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "10_Agents" / "tools" / "brain"))
import brain  # noqa: E402


# Raw double-bracket text is import syntax, historical evidence, a negative
# host-capability example, TOML array-table syntax, implementation code, or an
# explicitly named compatibility fixture/test. Exact counts make adding even
# one prescriptive occurrence a reviewed contract change.
RAW_LEGACY_LITERAL_COUNTS = {
    "00_Meta/CONVENTIONS.md": 1,
    "06_Resources/harness-codex.md": 3,
    "06_Resources/harness-opencode.md": 1,
    "07_Archives/inbox/2026-08-11-m5-m7-implementation-plan.md": 4,
    "07_Archives/inbox/2026-08-11-prd-review.md": 1,
    "10_Agents/harnesses/codex/wiring.md": 1,
    "10_Agents/tools/brain/brain.py": 4,
    "10_Agents/tools/brain/SPEC.md": 4,
    "10_Agents/tools/brain/tests/fixtures/link-migration/source.md": 3,
    "10_Agents/tools/brain/tests/fixtures/vault/01_Notes/beta.md": 2,
    "10_Agents/tools/brain/tests/fixtures/vault/bad/Bad_Name.md": 2,
    "10_Agents/tools/brain/tests/test_brain.py": 27,
    "10_Agents/tools/brain/tests/test_link_migration.py": 24,
    "10_Agents/tools/brain/tests/test_tasks.py": 1,
}


def note(body: str, title: str = "Note") -> str:
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n  - type/note\n"
        "updated: 2026-08-11\n"
        "---\n\n"
        + body
    )


class RepositoryMarkdownContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notes, assets = brain.index_corpus(ROOT)
        cls.index = brain.build_index(ROOT, notes, assets)

    def test_untracked_legacy_note_is_outside_the_maintained_corpus(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tracked.md").write_text(note("# Tracked\n"), encoding="utf-8")
            legacy = "[" * 2 + "tracked" + "]" * 2
            (root / "untracked.md").write_text(
                note(f"{legacy}\n", "Untracked"),
                encoding="utf-8",
            )
            with mock.patch.object(brain, "git_tracked", return_value={"tracked.md"}):
                notes, assets = brain.index_corpus(root)
            index = brain.build_index(root, notes, assets)
            self.assertEqual(notes, ["tracked.md"])
            self.assertEqual(index["linkCounts"]["legacy"], 0)
            self.assertNotIn("untracked.md", index["notes"])

    def test_maintained_corpus_is_markdown_only_and_resolved(self):
        counts = self.index["linkCounts"]
        self.assertEqual(counts["legacy"], 0)
        self.assertEqual(counts["wikilink"], 0)
        self.assertEqual(counts["markdown"], 835)
        failures = []
        for path, record in self.index["notes"].items():
            for link in record["links"]:
                if link["placeholder"]:
                    continue
                if (
                    link["format"] != "markdown"
                    or link["resolution"]["status"] != "resolved"
                    or link["resolved"] is None
                ):
                    failures.append((path, link["line"], link["raw"], link["resolution"]))
        self.assertEqual(failures, [])

        answer_links = self.index["notes"]["10_Agents/skills/vault-answer/SKILL.md"]["links"]
        citation = next(link for link in answer_links if link["label"] == "harness research")
        self.assertEqual(
            citation["destination"],
            "../../../06_Resources/harness-primitives-research.md",
        )
        self.assertEqual(citation["resolved"], "06_Resources/harness-primitives-research.md")
        self.assertEqual(citation["resolution"]["status"], "resolved")

    def test_all_twenty_placeholders_use_labeled_markdown_destinations(self):
        placeholders = [
            (path, link)
            for path, record in self.index["notes"].items()
            for link in record["links"]
            if link["placeholder"]
        ]
        self.assertEqual(len(placeholders), 20)
        for path, link in placeholders:
            with self.subTest(path=path, line=link["line"]):
                self.assertTrue(path.startswith("09_Templates/"))
                self.assertEqual(link["format"], "markdown")
                self.assertFalse(link["embed"])
                self.assertRegex(link["destination"], r"^\{\{[A-Z][A-Z0-9_]*\}\}$")
                self.assertTrue(link["label"])
                self.assertNotIn("{{", link["label"])
                self.assertEqual(link["raw"], f"[{link['label']}]({link['destination']})")

    def test_live_corpus_covers_every_present_path_and_label_class(self):
        relations = set()
        labels = fragments = 0
        for source, record in self.index["notes"].items():
            source_path = PurePosixPath(source)
            for link in record["links"]:
                if not link["resolved"]:
                    continue
                target_path = PurePosixPath(link["resolved"])
                if target_path == source_path:
                    relations.add("self")
                elif target_path.parent == source_path.parent:
                    relations.add("same")
                elif source_path.parent in target_path.parents:
                    relations.add("child")
                elif target_path.parent in source_path.parents:
                    relations.add("parent")
                else:
                    relations.add("cross")
                labels += bool(link["label"])
                fragments += bool(link["fragment"])
        self.assertEqual(relations, {"self", "same", "child", "parent", "cross"})
        self.assertGreater(labels, 300)
        self.assertGreater(fragments, 20)

    def test_three_surface_configuration_uses_one_link_form(self):
        app = json.loads((ROOT / ".obsidian" / "app.json").read_text(encoding="utf-8"))
        self.assertEqual(
            app,
            {
                "newLinkFormat": "relative",
                "openBehavior": "file:00_Meta/HOME.md",
                "useMarkdownLinks": True,
            },
        )
        vscode = (ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
        self.assertIn('"markdown.validate.enabled": true', vscode)
        self.assertIn('"markdown.suggest.paths.enabled": true', vscode)
        conventions = (ROOT / "00_Meta" / "CONVENTIONS.md").read_text(encoding="utf-8")
        self.assertIn("source-relative inline Markdown", conventions)
        self.assertIn("GitHub-compatible", conventions)

    def test_github_vscode_obsidian_syntax_matrix_resolves_in_brain(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {
                "parent.md": note("# Parent\n", "Parent"),
                "folder/source.md": note(
                    "# Source Heading\n"
                    "[same](same.md) [parent](../parent.md) "
                    "[child](child/note.md) [display label](same.md) "
                    "[Café notes](child/caf%C3%A9%20notes.md#r%C3%A9sum%C3%A9) "
                    "[self](#source-heading) ![diagram](assets/pic%20one.png)\n",
                    "Source",
                ),
                "folder/same.md": note("# Same\n", "Same"),
                "folder/child/note.md": note("# Child\n", "Child"),
                "folder/child/café notes.md": note("# Résumé\n", "Café"),
                "folder/assets/pic one.png": b"png",
            }
            for relative, content in files.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    target.write_bytes(content)
                else:
                    target.write_text(content, encoding="utf-8")
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            links = {
                link["label"]: link
                for link in index["notes"]["folder/source.md"]["links"]
            }
            self.assertEqual(
                {label: link["resolved"] for label, link in links.items()},
                {
                    "same": "folder/same.md",
                    "parent": "parent.md",
                    "child": "folder/child/note.md",
                    "display label": "folder/same.md",
                    "Café notes": "folder/child/café notes.md",
                    "self": "folder/source.md",
                    "diagram": "folder/assets/pic one.png",
                },
            )
            self.assertEqual(
                links["Café notes"]["resolution"]["fragment"]["slug"],
                "résumé",
            )
            self.assertTrue(links["diagram"]["embed"])

    def test_second_migration_is_an_exact_noop(self):
        plan = brain.build_link_migration_plan(ROOT)
        self.assertEqual(plan["edits"], [])
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["summary"]["legacyLinks"], 0)
        self.assertEqual(plan["summary"]["linksConverted"], 0)
        self.assertEqual(plan["summary"]["placeholders"], 0)

    def test_migration_check_cli_accepts_the_shipped_corpus(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "10_Agents" / "tools" / "brain" / "brain.py"),
                "migrate-links",
                "--check",
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["legacyLinks"], 0)
        self.assertEqual(payload["edits"], [])
        self.assertEqual(payload["blockers"], [])

    def test_raw_legacy_literals_match_the_exact_reviewed_allowlist(self):
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.split(b"\0")
        marker = "[" * 2
        actual = {}
        for raw_path in tracked:
            if not raw_path:
                continue
            relative = raw_path.decode("utf-8")
            path = ROOT / relative
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            count = text.count(marker)
            if count:
                actual[relative] = count
        self.assertEqual(actual, RAW_LEGACY_LITERAL_COUNTS)


if __name__ == "__main__":
    unittest.main()
