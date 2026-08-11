"""Tests for brain.py against spec.md.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "vault"


def make_vault(tmp: Path, files: dict[str, str | bytes]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    return tmp


class FrontmatterTests(unittest.TestCase):
    def parse(self, text: str):
        return brain.parse_frontmatter(text.split("\n"))

    def test_scalars_quotes_and_lists(self):
        fm, errors, _, has = self.parse(
            '---\ntitle: "Quoted"\nplain: bare value\ntags:\n  - type/note\n'
            "  - 'workflow/draft'\nflow: [a, \"b, c\", d]\n---\nbody"
        )
        self.assertTrue(has)
        self.assertEqual(errors, [])
        self.assertEqual(fm["title"], "Quoted")
        self.assertEqual(fm["plain"], "bare value")
        self.assertEqual(fm["tags"], ["type/note", "workflow/draft"])
        self.assertEqual(fm["flow"], ["a", "b, c", "d"])

    def test_empty_value_null_and_list_close(self):
        fm, errors, _, _ = self.parse(
            "---\nempty:\nlater: x\n- stray\n---\n"
        )
        self.assertIsNone(fm["empty"])
        self.assertIn("list-item-without-key", errors)

    def test_duplicate_key_last_wins(self):
        fm, errors, _, _ = self.parse("---\ntitle: one\ntitle: two\n---\n")
        self.assertEqual(fm["title"], "two")
        self.assertIn("duplicate-key:title", errors)

    def test_unsupported_yaml(self):
        _, errors, _, _ = self.parse(
            "---\nkey:no-space\nnested:\n  child: x\nbadflow: [a, b\n---\n"
        )
        self.assertEqual(len([e for e in errors if e.startswith("unsupported-yaml")]), 3)

    def test_unterminated_frontmatter(self):
        fm, errors, body_start, has = self.parse("---\ntitle: x\nbody [[link]]")
        self.assertTrue(has)
        self.assertIn("unterminated-frontmatter", errors)
        self.assertEqual(body_start, 1)

    def test_typed_fields(self):
        fm, errors, _, _ = self.parse(
            "---\ntitle: T\ntags: single\nupdated: 2026-02-30\n---\n"
        )
        title, tags, updated = brain.typed_fields(fm, errors)
        self.assertEqual(title, "T")
        self.assertEqual(tags, ["single"])
        self.assertIn("tags-not-a-list", errors)
        self.assertIsNone(updated)
        self.assertIn("invalid-updated", errors)


class ExtractionTests(unittest.TestCase):
    def extract(self, body: str):
        lines = ("---\ntitle: x\n---\n" + body).split("\n")
        return brain.extract_body(lines, 3)

    def test_exclusion_zones(self):
        links, _, _ = self.extract(
            "span `[[a]]` out\n```\n[[b]]\n```\n~~~\n[[c]]\n~~~\n[[real]]\n"
            "``double `[[d]]` span``\n```\n[[e]] inside an unclosed fence\n"
        )
        self.assertEqual([l["target"] for l in links], ["real"])

    def test_link_forms(self):
        links, _, _ = self.extract(
            "[[t]] [[t|D]] [[t#h]] [[t#^b|D2]] ![[pic.png]] [[t\\|E]] "
            "[[file.md]] [[{{ph}}]] \\[[escaped]] [[#self]]"
        )
        by_raw = {l["raw"]: l for l in links}
        self.assertNotIn("[[escaped]]", by_raw)
        self.assertEqual(by_raw["[[t|D]]"]["display"], "D")
        self.assertEqual(by_raw["[[t#h]]"]["fragment"], "h")
        self.assertEqual(by_raw["[[t#^b|D2]]"]["fragment"], "^b")
        self.assertTrue(by_raw["![[pic.png]]"]["embed"])
        self.assertEqual(by_raw["[[t\\|E]]"]["target"], "t")
        self.assertEqual(by_raw["[[t\\|E]]"]["display"], "E")
        self.assertEqual(by_raw["[[file.md]]"]["target"], "file")
        self.assertTrue(by_raw["[[{{ph}}]]"]["placeholder"])
        self.assertEqual(by_raw["[[#self]]"]["target"], "")

    def test_headings(self):
        _, headings, _ = self.extract(
            "# One\n## Two ##\nSetext\n======\n####### seven hashes\n`# span`\n"
        )
        self.assertEqual(
            [(h["level"], h["text"], h["line"]) for h in headings],
            [(1, "One", 4), (2, "Two", 5)],
        )

    def test_body_tags(self):
        _, _, tags = self.extract(
            "#focus-mode mid #ok2 url https://x.io/a#anchor #123 #1a\n# Heading\n"
        )
        self.assertEqual(tags, ["1a", "focus-mode", "ok2"])


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        notes = ["01_Notes/alpha.md", "01_Notes/dup.md", "02_Other/dup.md"]
        self.r = brain.Resolver(notes, ["08_Assets/pic.png"], {"01_Notes/alpha.md": "The Alpha"})

    def test_ladder(self):
        self.assertEqual(self.r.resolve("alpha", "x"), ("01_Notes/alpha.md", []))
        self.assertEqual(self.r.resolve("01_Notes/alpha", "x"), ("01_Notes/alpha.md", []))
        self.assertEqual(self.r.resolve("", "01_Notes/alpha.md"), ("01_Notes/alpha.md", []))
        resolved, warnings = self.r.resolve("dup", "x")
        self.assertEqual(resolved, "01_Notes/dup.md")
        self.assertEqual(warnings, ["ambiguous"])
        resolved, warnings = self.r.resolve("ALPHA", "x")
        self.assertEqual(resolved, "01_Notes/alpha.md")
        self.assertEqual(warnings, ["case-mismatch"])

    def test_asset_and_hints(self):
        self.assertEqual(self.r.resolve("pic.png", "x"), ("08_Assets/pic.png", []))
        resolved, warnings = self.r.resolve("The Alpha", "x")
        self.assertIsNone(resolved)
        self.assertEqual(warnings, ["title-match:01_Notes/alpha.md"])
        self.assertEqual(self.r.resolve("nope", "x"), (None, []))


class IndexTests(unittest.TestCase):
    def test_fixture_index_and_determinism(self):
        notes, assets = brain.walk_corpus(FIXTURE)
        index = brain.build_index(FIXTURE, notes, assets)
        self.assertEqual(index["schemaVersion"], brain.SCHEMA_VERSION)
        self.assertEqual(index["assets"], ["08_Assets/pic.png"])
        alpha = index["notes"]["01_Notes/alpha.md"]
        targets = {l["raw"]: l["resolved"] for l in alpha["links"]}
        self.assertEqual(targets["[[beta]]"], "01_Notes/beta.md")
        self.assertEqual(targets["[[01_Notes/beta#Alpha Section|B]]"], "01_Notes/beta.md")
        self.assertEqual(targets["![[pic.png]]"], "08_Assets/pic.png")
        self.assertEqual(targets["[[beta\\|Beta]]"], "01_Notes/beta.md")
        self.assertNotIn("[[fenced-away]]", targets)
        self.assertNotIn("[[not-a-link]]", targets)
        beta = index["notes"]["01_Notes/beta.md"]
        self.assertIn("01_Notes/alpha.md", beta["backlinks"])
        self.assertEqual(beta["bodyTags"], ["focus-mode"])
        one = brain.serialize(index)
        two = brain.serialize(brain.build_index(FIXTURE, notes, assets))
        self.assertEqual(one, two)
        self.assertTrue(one.endswith(b"}\n"))

    def test_not_utf8_and_size_normalization(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {"latin.md": b"caf\xe9\r\nline\r\n", "ok.md": "---\ntitle: x\n---\nhi\r\n"},
            )
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            rec = index["notes"]["latin.md"]
            self.assertEqual(rec["frontmatterErrors"], ["not-utf8"])
            self.assertEqual(rec["sizeBytes"], len(b"caf\xe9\nline\n"))
            self.assertEqual(index["notes"]["ok.md"]["sizeBytes"], len("---\ntitle: x\n---\nhi\n"))


class TaxonomyTests(unittest.TestCase):
    def test_fixture_table(self):
        tax = brain.load_taxonomy(FIXTURE)
        self.assertEqual(tax["audience"], ["agent", "human"])
        self.assertEqual(tax["type"], ["meta", "note"])
        self.assertIsNone(tax["topic"])
        self.assertEqual(sorted(tax), ["audience", "status", "topic", "type", "workflow"])

    def test_unreadable(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), {"00_Meta/conventions.md": "# No table here\n"})
            self.assertIsNone(brain.load_taxonomy(root))


class ValidateTests(unittest.TestCase):
    def test_fixture_findings(self):
        errors, warnings = brain.run_validate(FIXTURE, check_index=False)
        by_rule = {}
        for f in errors:
            by_rule.setdefault(f["rule"], []).append(f)
        self.assertEqual(
            sorted(by_rule),
            [
                "filename-convention",
                "invalid-updated",
                "tag-not-namespaced",
                "unknown-tag-value",
                "unresolved-link",
            ],
        )
        self.assertTrue(all(f["path"] == "bad/Bad_Name.md" for fs in by_rule.values() for f in fs))
        unresolved = by_rule["unresolved-link"]
        self.assertEqual(len(unresolved), 2)
        hinted = [f for f in unresolved if "title matches: 02_Other/title-note.md" in f["message"]]
        self.assertEqual(len(hinted), 1)
        warn_rules = sorted({(f["rule"], f["path"]) for f in warnings})
        self.assertEqual(
            warn_rules,
            [("ambiguous-link", "01_Notes/beta.md"), ("case-mismatch", "01_Notes/beta.md")],
        )

    def test_exemptions_and_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/conventions.md": (FIXTURE / "00_Meta/conventions.md").read_text(),
                    "CLAUDE.md": "@AGENTS.md\n",
                    "A-note.md": "---\ntitle: x\ntags:\n  - type/note\nupdated: 2026-01-01\n---\n",
                    "a-note.md": "---\ntitle: x\ntags:\n  - type/note\nupdated: 2026-01-01\n---\n",
                    "no-fm.md": "just a body\n",
                },
            )
            errors, _ = brain.run_validate(root, check_index=False)
            rules = {f["rule"] for f in errors}
            self.assertIn("path-collision", rules)
            self.assertIn("missing-frontmatter", rules)
            # CLAUDE.md is exempt from frontmatter checks; A-note fails kebab-case.
            self.assertFalse(any(f["path"] == "CLAUDE.md" for f in errors))
            self.assertTrue(
                any(f["path"] == "A-note.md" and f["rule"] == "filename-convention" for f in errors)
            )

    def test_skills_contract(self):
        conventions = (FIXTURE / "00_Meta/conventions.md").read_text()
        good = (
            "---\nname: good-skill\ndescription: Does a thing well.\n"
            'title: "Skill: Good"\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n# Good\n'
        )
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/conventions.md": conventions,
                    "10_Agents/skills/good-skill/SKILL.md": good,
                    "10_Agents/skills/bad-name/SKILL.md": good,
                    "10_Agents/skills/no-desc/SKILL.md": (
                        "---\nname: no-desc\ntitle: \"Skill: X\"\ntags:\n  - type/note\n"
                        "updated: 2026-08-11\n---\n\n# X\n"
                    ),
                    "10_Agents/skills/empty-dir/notes.md": (
                        "---\ntitle: x\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n"
                    ),
                    "SKILL.md": good,
                },
            )
            errors, _ = brain.run_validate(root, check_index=False)
            rules = {(f["rule"], f["path"]) for f in errors}
            self.assertIn(("skill-name-mismatch", "10_Agents/skills/bad-name/SKILL.md"), rules)
            self.assertIn(("skill-missing-description", "10_Agents/skills/no-desc/SKILL.md"), rules)
            self.assertIn(("skill-missing", "10_Agents/skills/empty-dir/"), rules)
            # SKILL.md outside 10_Agents/skills/ is a filename violation; inside it is exempt.
            self.assertIn(("filename-convention", "SKILL.md"), rules)
            self.assertNotIn(("filename-convention", "10_Agents/skills/good-skill/SKILL.md"), rules)
            self.assertFalse(any(f["path"].startswith("10_Agents/skills/good-skill") for f in errors))

    def test_filename_rules(self):
        self.assertTrue(brain.NOTE_NAME_RE.match("2025-01-15.md"))
        self.assertTrue(brain.NOTE_NAME_RE.match("2024-01-review.md"))
        self.assertTrue(brain.NOTE_NAME_RE.match("kebab-case-note.md"))
        self.assertFalse(brain.NOTE_NAME_RE.match("Bad_Name.md"))
        self.assertFalse(brain.NOTE_NAME_RE.match("double--dash.md"))
        self.assertTrue(brain.PERIODIC_RE.match("2026-W01-review.md"))
        self.assertTrue(brain.PERIODIC_RE.match("2026-Q3-review.md"))
        self.assertFalse(brain.PERIODIC_RE.match("2026-W1-review.md"))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = brain.main([*argv, "--vault", str(FIXTURE)])
        return code, out.getvalue()

    def test_validate_exit_and_output(self):
        code, out = self.run_cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("ERROR bad/Bad_Name.md", out)
        self.assertIn("WARN 01_Notes/beta.md", out)
        self.assertRegex(out.strip().splitlines()[-1], r"^\d+ errors, \d+ warnings$")
        code, payload = self.run_cli("validate", "--json")
        data = json.loads(payload)
        self.assertEqual(code, 1)
        self.assertEqual(sorted(data), ["errors", "warnings"])

    def test_query_commands(self):
        code, out = self.run_cli("list", "--dir", "01_Notes", "--type", "note")
        self.assertEqual(code, 0)
        self.assertEqual(
            out.split(), ["01_Notes/alpha.md", "01_Notes/beta.md", "01_Notes/dup.md"]
        )
        code, out = self.run_cli("search", "Alpha Section", "--json")
        self.assertEqual(code, 0)
        fields = {(h["path"], h["field"]) for h in json.loads(out)}
        self.assertIn(("01_Notes/beta.md", "heading"), fields)
        code, out = self.run_cli("links", "beta", "--json")
        data = json.loads(out)
        self.assertEqual(data["path"], "01_Notes/beta.md")
        self.assertIn("01_Notes/alpha.md", data["backlinks"])
        code, out = self.run_cli("tags", "--json")
        self.assertEqual(json.loads(out)["type"]["note"], 6)
        code, out = self.run_cli("show", "01_Notes/alpha.md", "--json")
        self.assertEqual(json.loads(out)["title"], "Alpha")
        # Windows callers (VS Code ${relativeFile}) pass backslash paths.
        code, out = self.run_cli("show", "01_Notes\\alpha.md", "--json")
        self.assertEqual(json.loads(out)["title"], "Alpha")
        # A fresh checkout flattens every fixture mtime, so pin the ordering
        # `recent` is expected to report instead of inheriting clone timestamps.
        now = time.time()
        os.utime(FIXTURE / "01_Notes" / "alpha.md", (now + 60, now + 60))
        code, out = self.run_cli("recent", "3", "--json")
        rows = json.loads(out)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["path"], "01_Notes/alpha.md")
        code, _ = self.run_cli("show", "no-such-note")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
