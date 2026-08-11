"""Tests for the restricted/private namespace (spec §8.3, §10.2 restricted-link;
issue #17): taxonomy acceptance, validate containment warning, and committed-index
reduction.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "vault"

# Fixture conventions plus the restricted row — the closed-list namespace the
# real 00_Meta/CONVENTIONS.md registers (single value: private).
CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(encoding="utf-8") + (
    "| `restricted/*` | Privacy marking | `private` |\n"
)

RESTRICTED_NOTE = (
    "---\ntitle: Secret Plans\ntags:\n  - type/note\n  - restricted/private\n"
    "updated: 2026-08-11\n---\n\n# Secret Heading\n\nSensitive body #topic/secretive\n"
    "Linking a sibling: [[other-secret]]\n"
)
OTHER_RESTRICTED = (
    "---\ntitle: Other Secret\ntags:\n  - type/note\n  - restricted/private\n"
    "updated: 2026-08-11\n---\n\nAlso sensitive. Back at [[secret]]\n"
)
NORMAL_LINKER = (
    "---\ntitle: Normal\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
    "# Normal Heading\n\nSee [[secret]] and embed ![[secret]] and [[plain]].\n"
)
PLAIN_NOTE = (
    "---\ntitle: Plain\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\nNothing.\n"
)


def make_vault(tmp: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def base_files() -> dict[str, str]:
    return {
        "00_Meta/CONVENTIONS.md": CONVENTIONS,
        "secret.md": RESTRICTED_NOTE,
        "other-secret.md": OTHER_RESTRICTED,
        "normal.md": NORMAL_LINKER,
        "plain.md": PLAIN_NOTE,
    }


class RestrictedTaxonomyTests(unittest.TestCase):
    """restricted/* is a closed namespace with the single value `private`."""

    def test_table_registers_closed_restricted_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), {"00_Meta/CONVENTIONS.md": CONVENTIONS})
            tax = brain.load_taxonomy(root)
            self.assertEqual(tax["restricted"], ["private"])

    def test_restricted_private_is_valid(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            errors, _ = brain.run_validate(root, check_index=False)
            self.assertFalse(
                any(
                    f["rule"] in ("unknown-namespace", "unknown-tag-value")
                    for f in errors
                ),
                errors,
            )

    def test_restricted_other_is_unknown_value(self):
        files = base_files()
        files["odd.md"] = (
            "---\ntitle: Odd\ntags:\n  - type/note\n  - restricted/other\n"
            "updated: 2026-08-11\n---\n\nBody.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            errors, _ = brain.run_validate(root, check_index=False)
            self.assertTrue(
                any(
                    f["rule"] == "unknown-tag-value"
                    and f["path"] == "odd.md"
                    and "restricted/other" in f["message"]
                    for f in errors
                ),
                errors,
            )

    def test_real_conventions_table_registers_restricted(self):
        # The repo's own 00_Meta/CONVENTIONS.md, not the fixture copy.
        tax = brain.load_taxonomy(brain.default_vault_root())
        self.assertEqual(tax["restricted"], ["private"])


class RestrictedLinkWarningTests(unittest.TestCase):
    """§10.2: non-restricted → restricted links warn; restricted → restricted don't."""

    def run_validate(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            return brain.run_validate(root, check_index=False)

    def test_normal_to_restricted_warns_link_and_embed(self):
        errors, warnings = self.run_validate(base_files())
        hits = [f for f in warnings if f["rule"] == "restricted-link"]
        # normal.md links AND embeds secret.md — one warning per link occurrence.
        self.assertEqual(sorted(f["path"] for f in hits), ["normal.md", "normal.md"])
        self.assertTrue(all("secret.md" in f["message"] for f in hits))
        self.assertTrue(all(isinstance(f["line"], int) for f in hits))
        # Warning severity, never an error.
        self.assertFalse(any(f["rule"] == "restricted-link" for f in errors))

    def test_restricted_to_restricted_is_clean(self):
        _, warnings = self.run_validate(base_files())
        self.assertFalse(
            any(
                f["rule"] == "restricted-link"
                and f["path"] in ("secret.md", "other-secret.md")
                for f in warnings
            ),
            warnings,
        )

    def test_normal_to_normal_is_clean(self):
        _, warnings = self.run_validate(base_files())
        self.assertFalse(
            any(
                f["rule"] == "restricted-link" and "plain.md" in f["message"]
                for f in warnings
            )
        )

    def test_body_tag_alone_does_not_restrict(self):
        # bodyTags are informal (§10.2 posture): a body #restricted/private
        # never makes the note restricted, so linking it stays clean.
        files = base_files()
        files["body-tagged.md"] = (
            "---\ntitle: Body Tagged\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
            "#restricted/private in the body only.\n"
        )
        files["linker.md"] = (
            "---\ntitle: Linker\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
            "See [[body-tagged]].\n"
        )
        _, warnings = self.run_validate(files)
        self.assertFalse(
            any(
                f["rule"] == "restricted-link" and f["path"] == "linker.md"
                for f in warnings
            )
        )


class RestrictedIndexReductionTests(unittest.TestCase):
    """§8.3: the committed index keeps path/title/tags but drops body-derived
    fields for restricted notes; in-memory query indexes stay unreduced."""

    def build(self, root: Path) -> dict:
        notes, assets = brain.walk_corpus(root)
        return brain.build_index(root, notes, assets)

    def test_reduce_restricted_record_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            index = self.build(root)
            # Unreduced: body-derived fields present.
            self.assertTrue(index["notes"]["secret.md"]["headings"])
            self.assertEqual(
                index["notes"]["secret.md"]["bodyTags"], ["topic/secretive"]
            )
            reduced = brain.reduce_restricted(index)
            rec = reduced["notes"]["secret.md"]
            # Kept: path (the key), title, tags, updated, links, backlinks.
            self.assertEqual(rec["title"], "Secret Plans")
            self.assertIn("restricted/private", rec["frontmatter"]["tags"])
            self.assertEqual(rec["updated"], "2026-08-11")
            self.assertEqual(rec["backlinks"], ["normal.md", "other-secret.md"])
            self.assertTrue(
                any(l["resolved"] == "other-secret.md" for l in rec["links"])
            )
            # Dropped: emptied, not omitted — the §8.1 shape holds.
            self.assertEqual(rec["headings"], [])
            self.assertEqual(rec["bodyTags"], [])
            self.assertIn("headings", rec)
            self.assertIn("bodyTags", rec)
            # Non-restricted notes are untouched.
            self.assertTrue(reduced["notes"]["normal.md"]["headings"])

    def test_reduction_strips_link_prose(self):
        # Alias text, fragments, and verbatim raw markup are body prose —
        # a reduced record's links keep only structure (§8.3).
        with tempfile.TemporaryDirectory() as td:
            files = base_files()
            files["secret.md"] = (
                "---\ntitle: \"Secret Plans\"\ntags:\n  - type/note\n"
                "  - restricted/private\nupdated: 2026-08-11\n---\n\n"
                "See [[other-secret#Hidden Section|the secret alias text]] "
                "and ![[normal]].\n"
            )
            root = make_vault(Path(td), files)
            reduced = brain.reduce_restricted(self.build(root))
            links = reduced["notes"]["secret.md"]["links"]
            self.assertEqual(len(links), 2)
            for link in links:
                self.assertIsNone(link["display"])
                self.assertIsNone(link["fragment"])
            self.assertEqual(links[0]["raw"], "[[other-secret]]")
            self.assertEqual(links[1]["raw"], "![[normal]]")
            # Non-restricted notes keep full link records.
            normal_links = reduced["notes"]["normal.md"]["links"]
            self.assertTrue(all("raw" in l for l in normal_links))

    def test_cmd_index_writes_reduced_index(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            rc = brain.main(["index", "--vault", str(root)])
            self.assertEqual(rc, 0)
            data = json.loads(
                (root / brain.INDEX_RELPATH).read_text(encoding="utf-8")
            )
            self.assertEqual(data["notes"]["secret.md"]["headings"], [])
            self.assertEqual(data["notes"]["secret.md"]["bodyTags"], [])
            self.assertEqual(data["notes"]["secret.md"]["title"], "Secret Plans")
            self.assertTrue(data["notes"]["normal.md"]["headings"])

    def test_check_index_accepts_reduced_and_rejects_unreduced(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            brain.main(["index", "--vault", str(root)])
            errors, _ = brain.run_validate(root, check_index=True)
            self.assertFalse(any(f["rule"] == "stale-index" for f in errors), errors)
            # An unreduced index on disk is stale by byte-compare.
            notes, assets = brain.walk_corpus(root)
            unreduced = brain.serialize(brain.build_index(root, notes, assets))
            (root / brain.INDEX_RELPATH).write_bytes(unreduced)
            errors, _ = brain.run_validate(root, check_index=True)
            self.assertTrue(any(f["rule"] == "stale-index" for f in errors))


if __name__ == "__main__":
    unittest.main()
