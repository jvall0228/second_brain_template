"""Tests for brain.py against SPEC.md.

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
from datetime import date
from pathlib import Path
from unittest import mock

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
        links, _, _, _ = self.extract(
            "span `[[a]]` out\n```\n[[b]]\n```\n~~~\n[[c]]\n~~~\n[[real]]\n"
            "``double `[[d]]` span``\n```\n[[e]] inside an unclosed fence\n"
        )
        self.assertEqual([l["target"] for l in links], ["real"])

    def test_link_forms(self):
        links, _, _, _ = self.extract(
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
        _, headings, _, _ = self.extract(
            "# One\n## Two ##\nSetext\n======\n####### seven hashes\n`# span`\n"
        )
        self.assertEqual(
            [(h["level"], h["text"], h["line"]) for h in headings],
            [(1, "One", 4), (2, "Two", 5)],
        )

    def test_body_tags(self):
        _, _, tags, _ = self.extract(
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
        self.assertIsNone(resolved)
        self.assertEqual(
            warnings,
            [
                "ambiguous",
                "candidate:01_Notes/dup.md",
                "candidate:02_Other/dup.md",
            ],
        )
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
        self.assertEqual(targets["[beta](beta.md)"], "01_Notes/beta.md")
        self.assertEqual(targets["[B](beta.md#alpha-section)"], "01_Notes/beta.md")
        self.assertEqual(targets["![pic](../08_Assets/pic.png)"], "08_Assets/pic.png")
        self.assertEqual(targets["[Beta](beta.md)"], "01_Notes/beta.md")
        self.assertNotIn("[fenced away](fenced-away.md)", targets)
        self.assertNotIn("[not a link](not-a-link.md)", targets)
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


@unittest.skipUnless(os.name == "posix", "relies on POSIX symlinks and file modes")
class UnreadableNoteTests(unittest.TestCase):
    """Spec §3 read failure: OSError on a note is a finding, never a crash."""

    def broken_symlink_vault(self, td: Path) -> Path:
        root = make_vault(
            td,
            {
                "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                "ok.md": note(),
                "02_Inbox/README.md": note(),
            },
        )
        os.symlink("../missing.md", root / "02_Inbox" / "dangling.md")
        return root

    def test_broken_symlink_indexed_as_not_readable(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.broken_symlink_vault(Path(td))
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            rec = index["notes"]["02_Inbox/dangling.md"]
            self.assertEqual(rec["frontmatterErrors"], ["not-readable"])
            self.assertEqual(rec["sizeBytes"], 0)
            self.assertEqual(rec["frontmatter"], {})
            self.assertEqual(rec["links"], [])

    def test_broken_symlink_validate_reports_finding(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.broken_symlink_vault(Path(td))
            errors, _ = brain.run_validate(root, check_index=False)
            rules = {f["rule"] for f in errors if f["path"] == "02_Inbox/dangling.md"}
            # §10.2: the read failure is the note's ONLY finding — derived
            # frontmatter-field checks are suppressed.
            self.assertEqual(rules, {"not-readable"})

    def test_not_utf8_note_gets_single_finding(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                    "02_Inbox/binary.md": b"\xff\xfe garbage \x80\x81",
                },
            )
            errors, _ = brain.run_validate(root, check_index=False)
            rules = {f["rule"] for f in errors if f["path"] == "02_Inbox/binary.md"}
            self.assertEqual(rules, {"not-utf8"})

    def test_tool_test_trees_pruned_from_corpus(self):
        # Any 10_Agents/tools/*/tests tree stays out of the corpus (spec §2),
        # so secret-shaped test data in a non-brain tool suite is never
        # scanned and never indexed as an asset.
        with tempfile.TemporaryDirectory() as td:
            fake_secret = "ghp_" + "a1B2" * 9  # runtime-concatenated
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                    "10_Agents/tools/vscode/tests/test_x.py": f'token = "{fake_secret}"\n',
                    "10_Agents/tools/vscode/gen.py": "print('kept')\n",
                },
            )
            notes, assets = brain.walk_corpus(root)
            self.assertNotIn("10_Agents/tools/vscode/tests/test_x.py", assets)
            self.assertIn("10_Agents/tools/vscode/gen.py", assets)
            errors, _ = brain.run_validate(root, check_index=False)
            self.assertEqual([f for f in errors if f["rule"].startswith("secret-")], [])

    def test_broken_symlink_commands_do_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.broken_symlink_vault(Path(td))
            for argv in (
                ["index"],
                ["list"],
                ["search", "x"],
                ["recent", "5"],
                ["curate"],
                ["validate"],
            ):
                out, err_s = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err_s):
                    code = brain.main([*argv, "--vault", str(root)])
                expected = {1} if argv == ["validate"] else {0}
                self.assertIn(code, expected, f"{argv} exited {code}")

    # getattr guard: os.geteuid does not exist on Windows, and skipIf's
    # condition evaluates at import time.
    @unittest.skipIf(getattr(os, "geteuid", lambda: -1)() == 0, "root ignores file modes")
    def test_permission_denied_is_not_readable(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                    "locked.md": note(),
                },
            )
            locked = root / "locked.md"
            os.chmod(locked, 0o000)
            try:
                notes, assets = brain.walk_corpus(root)
                index = brain.build_index(root, notes, assets)
                self.assertEqual(
                    index["notes"]["locked.md"]["frontmatterErrors"], ["not-readable"]
                )
                errors, _ = brain.run_validate(root, check_index=False)
                self.assertTrue(
                    any(
                        f["rule"] == "not-readable" and f["path"] == "locked.md"
                        for f in errors
                    )
                )
            finally:
                os.chmod(locked, 0o644)


class EmptyTagsTests(unittest.TestCase):
    """Spec §10.2: `tags: []` fails missing-tags like an absent/null key."""

    def validate(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                    **files,
                },
            )
            return brain.run_validate(root, check_index=False)

    def test_empty_flow_list_is_missing_tags(self):
        errors, _ = self.validate(
            {"no-tags.md": "---\ntitle: x\ntags: []\nupdated: 2026-08-11\n---\n"}
        )
        self.assertTrue(
            any(f["rule"] == "missing-tags" and f["path"] == "no-tags.md" for f in errors)
        )

    def test_null_tags_still_missing(self):
        errors, _ = self.validate(
            {"null-tags.md": "---\ntitle: x\ntags:\nupdated: 2026-08-11\n---\n"}
        )
        self.assertTrue(
            any(f["rule"] == "missing-tags" and f["path"] == "null-tags.md" for f in errors)
        )

    def test_template_placeholder_tags_stay_exempt(self):
        errors, _ = self.validate(
            {
                "09_Templates/template-thing.md": (
                    "---\ntitle: \"{{title}}\"\ntags:\n  - \"{{tag}}\"\n"
                    "updated: \"{{date}}\"\n---\n"
                )
            }
        )
        self.assertFalse(
            any(f["path"] == "09_Templates/template-thing.md" for f in errors)
        )

    def test_variants_dir_shares_placeholder_exemption(self):
        # Spec §10.3: the 09_Templates/** exemption is recursive, so the
        # issue #12 specialization sources under variants/ validate clean
        # with the same placeholder frontmatter as the templates they mirror.
        errors, _ = self.validate(
            {
                "09_Templates/variants/work-daily-log.md": (
                    "---\ntitle: \"{{date}}\"\ntags:\n  - \"{{tag}}\"\n"
                    "updated: \"{{date}}\"\n---\n"
                )
            }
        )
        self.assertFalse(
            any(f["path"] == "09_Templates/variants/work-daily-log.md" for f in errors)
        )


class TaxonomyTests(unittest.TestCase):
    def test_fixture_table(self):
        tax = brain.load_taxonomy(FIXTURE)
        self.assertEqual(tax["audience"], ["agent", "human"])
        self.assertEqual(tax["type"], ["meta", "note"])
        self.assertIsNone(tax["topic"])
        self.assertEqual(sorted(tax), ["audience", "status", "topic", "type", "workflow"])

    def test_unreadable(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), {"00_Meta/CONVENTIONS.md": "# No table here\n"})
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
                "ambiguous-link",
                "filename-convention",
                "invalid-updated",
                "tag-not-namespaced",
                "unknown-tag-value",
                "unresolved-link",
            ],
        )
        self.assertEqual(by_rule["ambiguous-link"][0]["path"], "01_Notes/beta.md")
        self.assertTrue(
            all(
                f["path"] == "bad/Bad_Name.md"
                for rule, findings in by_rule.items()
                if rule != "ambiguous-link"
                for f in findings
            )
        )
        unresolved = by_rule["unresolved-link"]
        self.assertEqual(len(unresolved), 2)
        hinted = [f for f in unresolved if "title matches: 02_Other/title-note.md" in f["message"]]
        self.assertEqual(len(hinted), 1)
        warn_rules = sorted({(f["rule"], f["path"]) for f in warnings})
        self.assertEqual(
            warn_rules,
            [("case-mismatch", "01_Notes/beta.md")],
        )

    def test_exemptions_and_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                    "CLAUDE.md": "@AGENTS.md\n",
                    "A-note.md": "---\ntitle: x\ntags:\n  - type/note\nupdated: 2026-01-01\n---\n",
                    "a-note.md": "---\ntitle: x\ntags:\n  - type/note\nupdated: 2026-01-01\n---\n",
                    "no-fm.md": "just a body\n",
                },
            )
            errors, _ = brain.run_validate(root, check_index=False)
            rules = {f["rule"] for f in errors}
            materialized = {path.name for path in root.iterdir()}
            if {"A-note.md", "a-note.md"} <= materialized:
                self.assertIn("path-collision", rules)
            else:
                # Case-insensitive filesystems cannot materialize both fixture
                # names. Keep the collision key contract covered there while
                # Linux CI exercises the end-to-end finding above.
                self.assertEqual(brain.fold("A-note.md"), brain.fold("a-note.md"))
            self.assertIn("missing-frontmatter", rules)
            # CLAUDE.md is exempt from frontmatter checks; A-note fails kebab-case.
            self.assertFalse(any(f["path"] == "CLAUDE.md" for f in errors))
            self.assertTrue(
                any(f["path"] == "A-note.md" and f["rule"] == "filename-convention" for f in errors)
            )

    def test_skills_contract(self):
        conventions = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text()
        good = (
            "---\nname: good-skill\ndescription: Does a thing well.\n"
            'title: "Skill: Good"\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n# Good\n'
        )
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": conventions,
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
        self.assertTrue(brain.valid_note_filename("04_Projects/example/PROJECT.md"))
        self.assertTrue(brain.valid_note_filename("05_Areas/health/AREA.md"))
        self.assertTrue(brain.valid_note_filename("06_Resources/homelab/RESOURCE.md"))


class ProvenanceTests(unittest.TestCase):
    """Spec §10.2 missing-author (issue #18): warn on an agent-tagged
    02_Inbox/ draft with no author: field; never an error."""

    AGENT_DRAFT = (
        "---\ntitle: x\ntags:\n  - audience/agent\n  - workflow/draft\n"
        "  - type/note\nupdated: 2026-08-11\n{extra}---\nbody\n"
    )

    def validate(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(),
                    **files,
                },
            )
            return brain.run_validate(root, check_index=False)

    def missing_author(self, findings, path):
        return any(
            f["rule"] == "missing-author" and f["path"] == path for f in findings
        )

    def test_agent_inbox_draft_without_author_warns(self):
        path = "02_Inbox/2026-08-11-capture.md"
        errors, warnings = self.validate({path: self.AGENT_DRAFT.format(extra="")})
        self.assertTrue(self.missing_author(warnings, path))
        # Warning-mapped, never an error.
        self.assertFalse(any(f["rule"] == "missing-author" for f in errors))
        self.assertFalse(any(f["path"] == path for f in errors))

    def test_author_present_no_warning(self):
        path = "02_Inbox/2026-08-11-capture.md"
        _, warnings = self.validate(
            {path: self.AGENT_DRAFT.format(extra="author: claude-code\n")}
        )
        self.assertFalse(self.missing_author(warnings, path))

    def test_null_author_still_warns(self):
        path = "02_Inbox/2026-08-11-capture.md"
        _, warnings = self.validate({path: self.AGENT_DRAFT.format(extra="author:\n")})
        self.assertTrue(self.missing_author(warnings, path))

    def test_human_note_exempt(self):
        # No audience/agent + workflow/draft pair → absence means human-authored.
        path = "02_Inbox/2026-08-11-human-note.md"
        content = (
            "---\ntitle: x\ntags:\n  - audience/human\n  - type/note\n"
            "updated: 2026-08-11\n---\nbody\n"
        )
        _, warnings = self.validate({path: content})
        self.assertFalse(self.missing_author(warnings, path))

    def test_agent_draft_outside_inbox_exempt(self):
        path = "06_Resources/agent-draft.md"
        _, warnings = self.validate({path: self.AGENT_DRAFT.format(extra="")})
        self.assertFalse(self.missing_author(warnings, path))

    def test_template_exempt(self):
        # §10.3 pattern: templates are never flagged — placeholder frontmatter
        # (and living outside 02_Inbox/) satisfies the rule by construction.
        path = "09_Templates/template-capture.md"
        content = (
            "---\ntitle: \"{{title}}\"\ntags:\n  - audience/agent\n"
            "  - workflow/draft\n  - type/note\nupdated: \"{{date}}\"\n"
            "author: \"{{author}}\"\n---\nbody\n"
        )
        errors, warnings = self.validate({path: content})
        self.assertFalse(self.missing_author(warnings, path))
        self.assertFalse(any(f["path"] == path for f in errors))


def note(body: str = "", **fm_extra) -> str:
    fm = {"title": "x", "updated": "2026-08-01", **fm_extra}
    lines = ["---", f'title: {fm["title"]}', "tags:", "  - type/note"]
    for k, v in fm.items():
        if k not in ("title", "tags"):
            lines.append(f"{k}: {v}")
    lines += ["---", body, ""]
    return "\n".join(lines)


class CurationTests(unittest.TestCase):
    CONVENTIONS = None

    @classmethod
    def setUpClass(cls):
        cls.CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text()

    def vault(self, td, files):
        return make_vault(Path(td), {"00_Meta/CONVENTIONS.md": self.CONVENTIONS, **files})

    def test_invalid_expires(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(
                td,
                {
                    "bad-date.md": note(expires="2026-13-40"),
                    "empty-val.md": note(expires=""),
                    "good.md": note(expires="2027-01-01"),
                    "09_Templates/template-t.md": note(expires="{{expires}}"),
                },
            )
            errors, _ = brain.run_validate(root, check_index=False)
            paths = {f["path"] for f in errors if f["rule"] == "invalid-expires"}
            self.assertEqual(paths, {"bad-date.md", "empty-val.md"})

    def test_curation_warnings_gated(self):
        files = {"plain.md": note()}
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            with mock.patch.object(brain, "VALIDATE_CURATION_WARNINGS", False):
                _, warnings = brain.run_validate(root, check_index=False)
            self.assertFalse(any(f["rule"] == "missing-expires" for f in warnings))
            with mock.patch.object(brain, "VALIDATE_CURATION_WARNINGS", True):
                _, warnings = brain.run_validate(root, check_index=False)
            self.assertTrue(
                any(f["rule"] == "missing-expires" and f["path"] == "plain.md" for f in warnings)
            )

    def test_missing_expires_exemptions(self):
        files = {
            "02_Inbox/2026-08-11-capture.md": note(),
            "02_Outbox/2026-08-11-packet.md": note(),
            "03_Journal/day.md": note(),
            "07_Archives/old.md": note(),
            "10_Agents/solutions/fix.md": note(),
            "00_Meta/CHANGELOG.md": note(),
            "00_Meta/STATUS.md": note(),
            "needs-one.md": note(),
        }
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            with mock.patch.object(brain, "VALIDATE_CURATION_WARNINGS", True):
                _, warnings = brain.run_validate(root, check_index=False)
            missing = {f["path"] for f in warnings if f["rule"] == "missing-expires"}
            self.assertEqual(missing, {"needs-one.md"})

    def test_type_decision_exempt_from_expires_not_orphan(self):
        # A type/decision note needs no expires: (event record), but an unlinked
        # one is still an orphan — the two exemptions are deliberately different.
        files = {
            "04_Projects/p/decision-records/2025-01-10-dr.md": (
                "---\ntitle: DR\ntags:\n  - type/decision\n"
                "updated: 2025-01-10\n---\n\nbody\n"
            ),
            "claim.md": note(),  # ordinary note: should be flagged missing-expires
        }
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            cur = brain.compute_curation(root, index, date(2026, 8, 11))
            self.assertNotIn("04_Projects/p/decision-records/2025-01-10-dr.md", cur["missingExpires"])
            self.assertIn("claim.md", cur["missingExpires"])
            # exempt from expires, but not from the orphan check
            self.assertIn("04_Projects/p/decision-records/2025-01-10-dr.md", cur["orphans"])

    def test_beyond_cap_and_oversized_warnings(self):
        big = note("word\n" * 401, expires="2027-02-01")
        files = {
            "over-cap.md": note(expires="2028-01-01"),  # updated 2026-08-01
            "big.md": big,
        }
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            with mock.patch.object(brain, "VALIDATE_CURATION_WARNINGS", True):
                _, warnings = brain.run_validate(root, check_index=False)
            rules = {(f["rule"], f["path"]) for f in warnings}
            self.assertIn(("expires-beyond-cap", "over-cap.md"), rules)
            self.assertIn(("oversized", "big.md"), rules)

    def test_compute_curation_signals(self):
        files = {
            "expired.md": note("[stale hub](stale-hub.md)", expires="2020-01-01"),
            "fresh.md": note("[expired](expired.md) ![used](08_Assets/used.png)", expires="2999-01-01"),
            "stale-hub.md": note("[fresh](fresh.md)", updated="2020-01-01", expires="2999-01-01"),
            "orphan.md": note(expires="2999-01-01"),
            "08_Assets/used.png": b"x",
            "08_Assets/unused.png": b"x",
        }
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            cur = brain.compute_curation(root, index, date(2026, 8, 11))
            self.assertEqual([r["path"] for r in cur["expired"]], ["expired.md"])
            self.assertEqual([r["path"] for r in cur["stale"]], ["stale-hub.md"])
            self.assertEqual(cur["stale"][0]["backlinks"], 1)
            self.assertEqual(cur["stale"][0]["score"], cur["stale"][0]["daysOld"] * 2)
            self.assertIn("orphan.md", cur["orphans"])
            self.assertNotIn("fresh.md", cur["orphans"])
            self.assertEqual(cur["unreferencedAssets"], ["08_Assets/unused.png"])
            self.assertEqual(cur["missingExpires"], [])

    def test_context_report_and_budget_warning(self):
        files = {"AGENTS.md": "a" * 9000}
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            ctx = brain.context_report(root)
            by_path = {r["path"]: r for r in ctx["docs"]}
            self.assertEqual(by_path["AGENTS.md"]["sizeBytes"], 9000)
            self.assertIsNone(by_path["01_Profile/NOW.md"]["sizeBytes"])
            with mock.patch.object(brain, "VALIDATE_CURATION_WARNINGS", True):
                _, warnings = brain.run_validate(root, check_index=False)
            self.assertTrue(
                any(f["rule"] == "bootstrap-budget" and f["path"] == "AGENTS.md" for f in warnings)
            )

    def test_curate_and_context_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = brain.main(["curate", "--json", "--vault", str(FIXTURE)])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(
            sorted(data),
            [
                "beyondCap",
                "expired",
                "missingExpires",
                "orphans",
                "oversized",
                "stale",
                "unreferencedAssets",
            ],
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = brain.main(["context", "--json", "--vault", str(FIXTURE)])
        self.assertEqual(code, 0)
        ctx = json.loads(out.getvalue())
        self.assertEqual(sorted(ctx), ["docs", "totalBudget", "totalBytes"])

    def test_collect_urls(self):
        files = {
            "src.md": note(
                "See https://example.com/a. And (https://example.com/b) plus "
                "`https://example.com/code-span`\n"
                "```\nhttps://example.com/fenced\n```\n"
            )
        }
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            urls = brain.collect_urls(root, ["src.md"])
            self.assertIn("https://example.com/a", urls)
            self.assertIn("https://example.com/b", urls)
            # code spans and fenced blocks are excluded, like every other extractor
            self.assertNotIn("https://example.com/code-span", urls)
            self.assertNotIn("https://example.com/fenced", urls)

    def test_check_urls_classification(self):
        import urllib.error

        files = {
            "src.md": note(
                "prose links: https://ok.example/a https://dead.example/b "
                "https://forbidden.example/c https://gone.example/d\n"
            )
        }

        def fake_urlopen(req, timeout=None):
            url = req.full_url
            if "ok.example" in url:
                return contextlib.nullcontext()
            if "forbidden.example" in url:
                raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
            if "gone.example" in url:
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            raise urllib.error.URLError("dns failure")

        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, files)
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                dead = brain.check_urls(root, ["src.md"])
            urls = {d["url"] for d in dead}
            self.assertIn("https://gone.example/d", urls)     # 404 -> dead
            self.assertIn("https://dead.example/b", urls)      # URLError -> dead
            self.assertNotIn("https://forbidden.example/c", urls)  # 403 -> HEAD-hostile, skipped
            self.assertNotIn("https://ok.example/a", urls)     # 200 -> alive

    def test_bootstrap_budget_total_warning(self):
        # Inflate a bootstrap doc past BOOTSTRAP_TOTAL_BUDGET (keep the tag
        # table intact so validate can still read the taxonomy).
        big_conventions = self.CONVENTIONS + "\n" + ("padding line\n" * 4000)
        with tempfile.TemporaryDirectory() as td:
            root = self.vault(td, {"00_Meta/CONVENTIONS.md": big_conventions})
            ctx = brain.context_report(root)
            self.assertGreater(ctx["totalBytes"], brain.BOOTSTRAP_TOTAL_BUDGET)
            with mock.patch.object(brain, "VALIDATE_CURATION_WARNINGS", True):
                _, warnings = brain.run_validate(root, check_index=False)
            self.assertTrue(any(f["rule"] == "bootstrap-budget-total" for f in warnings))


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


class SecretScanTests(unittest.TestCase):
    """Spec §10.5. Fake secrets are assembled at runtime by concatenation so
    no committed file — not even this excluded test tree — carries one."""

    # Assembled fakes (all are documentation-safe example shapes).
    FAKE_AWS = "AKIA" + "IOSFODNN7EXAMPLE"
    FAKE_GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0" + "k1L2m3N4o5P6"
    FAKE_SLACK = "xoxb-" + "123456789012-abcdefABCDEF"
    FAKE_PEM = "-----BEGIN RSA " + "PRIVATE KEY" + "-----"
    FAKE_GENERIC = 'api_key: "' + "s3cretvalue12345" + '"'
    FAKE_ENTROPY = 'blob = "' + "Ab1" * 14 + '"'

    @classmethod
    def setUpClass(cls):
        cls.CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text()

    def scan(self, files: dict):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td), {"00_Meta/CONVENTIONS.md": self.CONVENTIONS, **files}
            )
            errors, _ = brain.run_validate(root, check_index=False)
        return [f for f in errors if f["rule"].startswith("secret-")]

    def test_each_rule_positive(self):
        body = "\n".join(
            [
                self.FAKE_AWS,
                "a token line " + self.FAKE_GH,
                "slack: " + self.FAKE_SLACK,
                self.FAKE_PEM,
                self.FAKE_GENERIC,
                self.FAKE_ENTROPY,
            ]
        )
        findings = self.scan({"seeded.md": note(body)})
        rules = sorted(f["rule"] for f in findings)
        self.assertEqual(
            rules,
            [
                "secret-aws-access-key-id",
                "secret-generic-credential",
                "secret-github-token",
                "secret-high-entropy-string",
                "secret-private-key",
                "secret-slack-token",
            ],
        )
        self.assertTrue(all(f["path"] == "seeded.md" for f in findings))
        self.assertTrue(all(isinstance(f["line"], int) for f in findings))
        # The matched secret is never echoed into the message (§10.5).
        self.assertFalse(any(self.FAKE_AWS in f["message"] for f in findings))

    def test_validate_exits_1_and_names_rule(self):
        with tempfile.TemporaryDirectory() as td:
            make_vault(
                Path(td),
                {
                    "00_Meta/CONVENTIONS.md": self.CONVENTIONS,
                    "leak.md": note(self.FAKE_AWS),
                },
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = brain.main(["validate", "--vault", td])
            self.assertEqual(code, 1)
            self.assertIn("secret-aws-access-key-id", buf.getvalue())

    def test_non_markdown_text_files_scanned(self):
        findings = self.scan({"06_Resources/creds.txt": "key = " + self.FAKE_AWS + "\n"})
        self.assertEqual(
            [(f["path"], f["rule"]) for f in findings],
            [("06_Resources/creds.txt", "secret-aws-access-key-id")],
        )

    def test_binary_files_skipped(self):
        payload = b"\x00\x01" + self.FAKE_AWS.encode() + b"\x00"
        findings = self.scan({"08_Assets/blob.png": payload})
        self.assertEqual(findings, [])

    def test_allowlist_marker_suppresses(self):
        marked = (
            self.FAKE_AWS + " <!-- " + brain.SECRET_ALLOW_MARKER + " -->"
        )
        findings = self.scan({"documented.md": note(marked)})
        self.assertEqual(findings, [])
        # Marker on a different line does not suppress.
        findings = self.scan(
            {
                "leaky.md": note(
                    self.FAKE_AWS + "\n<!-- " + brain.SECRET_ALLOW_MARKER + " -->"
                )
            }
        )
        self.assertEqual([f["rule"] for f in findings], ["secret-aws-access-key-id"])

    def test_negatives_do_not_flag(self):
        body = "\n".join(
            [
                "Prose about AWS AKIA prefixes and akiaiosfodnn7example shapes.",
                "See [some note](06_Resources/some-note.md) and #topic/software tags.",
                'commit = "d3b07384d113edec49eaa6238ad5ff00c0ffee12"',  # git SHA: no uppercase
                "https://example.com/AbC123defGHI456jklMNO789pqrSTU012vwxYZ345",
                "the token: value pair syntax (unquoted, not a credential)",
                'display_name: "A Perfectly Ordinary Quoted Title 2026"',
                "ghp_ and github_pat_ are GitHub token prefixes.",
            ]
        )
        self.assertEqual(self.scan({"clean.md": note(body)}), [])

    def test_repo_self_scan_clean(self):
        root = brain.default_vault_root()
        notes, assets = brain.walk_corpus(root)
        self.assertEqual(brain.scan_secrets(root, notes + assets), [])


if __name__ == "__main__":
    unittest.main()


class FutureUpdatedTests(unittest.TestCase):
    """§10.2 future-updated: a valid updated: date past the vault-today
    horizon is an error — exact with a configured timezone, one day of
    grace without one (host could sit anywhere in UTC-12..UTC+14)."""

    NOTE = "---\ntitle: x\ntags:\n  - type/note\nupdated: {d}\n---\n"

    def rules(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {"00_Meta/CONVENTIONS.md": (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(), **files},
            )
            errors, _ = brain.run_validate(root, check_index=False)
            return [f["rule"] for f in errors if f["path"] == "note.md"]

    def test_far_future_is_error_without_timezone(self):
        self.assertIn("future-updated", self.rules({"note.md": self.NOTE.format(d="2999-01-01")}))

    def test_tomorrow_gets_grace_without_timezone(self):
        d = (brain.today() + brain.timedelta(days=1)).isoformat()
        self.assertNotIn("future-updated", self.rules({"note.md": self.NOTE.format(d=d)}))

    def test_day_after_tomorrow_is_error_without_timezone(self):
        d = (brain.today() + brain.timedelta(days=2)).isoformat()
        self.assertIn("future-updated", self.rules({"note.md": self.NOTE.format(d=d)}))

    def test_tomorrow_is_error_with_utc_timezone(self):
        import datetime as _dt
        import zoneinfo as _zi

        d = (_dt.datetime.now(_zi.ZoneInfo("UTC")).date() + brain.timedelta(days=1)).isoformat()
        self.assertIn(
            "future-updated",
            self.rules(
                {
                    "note.md": self.NOTE.format(d=d),
                    "00_Meta/config.yaml": "timezone: UTC\n",
                }
            ),
        )

    def test_today_is_clean(self):
        self.assertNotIn(
            "future-updated",
            self.rules(
                {
                    "note.md": self.NOTE.format(d=brain.today().isoformat()),
                    "00_Meta/config.yaml": "timezone: UTC\n",
                }
            ),
        )

    def test_invalid_updated_is_not_double_flagged(self):
        self.assertNotIn("future-updated", self.rules({"note.md": self.NOTE.format(d="2999-13-99")}))
