"""Tests for the restricted/private namespace (spec §8.3, §10.2 restricted-link
and restricted-transition; issue #17): taxonomy acceptance, validate provenance
warning, committed-index reduction, query-row privacy metadata, and
tag-transition diagnostics against the tracked Git baseline.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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
    "Linking a sibling: [other secret](other-secret.md)\n"
)
OTHER_RESTRICTED = (
    "---\ntitle: Other Secret\ntags:\n  - type/note\n  - restricted/private\n"
    "updated: 2026-08-11\n---\n\nAlso sensitive. Back at [secret](secret.md)\n"
)
NORMAL_LINKER = (
    "---\ntitle: Normal\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
    "# Normal Heading\n\nSee [secret](secret.md) and embed ![secret](secret.md) and [plain](plain.md).\n"
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


class ArchiveSubstanceAuditTests(unittest.TestCase):
    """R5: in the live corpus, an archived note that is not itself restricted
    may cite a restricted note in prose (a bare evidence link) but never in a
    triage-table row — a table row that links a restricted note summarizes
    it (path, summary, tag changes, decisions) and inherits the tag."""

    ROOT = Path(__file__).resolve().parents[4]

    def test_archived_table_rows_linking_restricted_notes_are_classified(self):
        root = self.ROOT
        notes, assets = brain.walk_corpus(root, selected_environment=None)
        index = brain.build_index(root, notes, assets)
        records = index["notes"]
        restricted = {rel for rel, rec in records.items() if brain.is_restricted(rec)}
        offenders = []
        bare_links = []
        for rel in sorted(records):
            if not rel.startswith("07_Archives/") or rel in restricted:
                continue
            text, _ = brain.load_text(root, rel)
            lines = text.split("\n")
            for link in records[rel].get("links", []):
                target = link.get("resolved")
                if target not in restricted:
                    continue
                line = lines[link["line"] - 1]
                if line.lstrip().startswith("|"):
                    offenders.append(f"{rel}:{link['line']} -> {target}")
                else:
                    bare_links.append(f"{rel}:{link['line']} -> {target}")
        self.assertEqual(offenders, [], "archived table rows that summarize restricted notes must carry restricted/private")
        # Every remaining archive-lane link is an audited bare citation and is
        # recorded, by warning, in the committed baseline (not silently exempt).
        baseline = brain.load_baseline(root) or {}
        baselined = {path for (path, rule, _message) in baseline if rule == "restricted-link" and path.startswith("07_Archives/")}
        for entry in bare_links:
            self.assertIn(entry.split(":")[0], baselined, entry)


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

    def test_archive_lane_is_not_exempt(self):
        # §10.3: no lane is exempt. An archived (non-restricted) summary of a
        # restricted note warns exactly like the same link outside the lane.
        files = base_files()
        files["07_Archives/inbox/report.md"] = NORMAL_LINKER.replace("(secret.md)", "(../../secret.md)").replace(
            "(plain.md)", "(../../plain.md)"
        )
        errors, warnings = self.run_validate(files)
        hits = [f for f in warnings if f["rule"] == "restricted-link"]
        self.assertEqual(
            sorted(f["path"] for f in hits),
            ["07_Archives/inbox/report.md", "07_Archives/inbox/report.md", "normal.md", "normal.md"],
        )
        self.assertFalse(any(f["rule"] == "restricted-link" for f in errors))

    def test_classified_archived_record_is_clean(self):
        # An archived record that inherited restricted/private passes: the
        # warning asks for classification, and it has it.
        files = base_files()
        files["07_Archives/inbox/report.md"] = (
            NORMAL_LINKER.replace("  - type/note\n", "  - type/note\n  - restricted/private\n")
            .replace("(secret.md)", "(../../secret.md)")
            .replace("(plain.md)", "(../../plain.md)")
        )
        _, warnings = self.run_validate(files)
        self.assertFalse(
            [f for f in warnings if f["rule"] == "restricted-link" and f["path"].startswith("07_Archives/")],
            warnings,
        )

    def test_all_flag_exposes_archive_warnings_after_generation(self):
        # The archive warnings survive a baseline write: `--all` still lists
        # them (the baseline is a reporting filter, never a suppression).
        files = base_files()
        files["07_Archives/inbox/report.md"] = NORMAL_LINKER.replace("(secret.md)", "(../../secret.md)").replace(
            "(plain.md)", "(../../plain.md)"
        )
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(brain.main(["validate", "--write-baseline", "--vault", str(root)]), 0)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(brain.main(["validate", "--vault", str(root)]), 0)
            self.assertNotIn("07_Archives/inbox/report.md", out.getvalue())
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(brain.main(["validate", "--all", "--vault", str(root)]), 2)
            self.assertIn("WARN 07_Archives/inbox/report.md", out.getvalue())

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
            "See [body tagged](body-tagged.md).\n"
        )
        _, warnings = self.run_validate(files)
        self.assertFalse(
            any(
                f["rule"] == "restricted-link" and f["path"] == "linker.md"
                for f in warnings
            )
        )


def run_cli(root: Path, *argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = brain.main([*argv, "--vault", str(root)])
    return rc, buf.getvalue()


class RestrictedLinkWordingTests(unittest.TestCase):
    """R7/AE5: restricted-link is an informational provenance check, not a
    containment ban — and it never auto-propagates the tag."""

    def test_message_is_provenance_check_not_containment(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            _, warnings = brain.run_validate(root, check_index=False)
            hits = [f for f in warnings if f["rule"] == "restricted-link"]
            self.assertTrue(hits)
            for f in hits:
                self.assertIn("informational", f["message"])
                self.assertIn("restricted/private", f["message"])
                self.assertNotIn("never quote or summarize", f["message"])

    def test_bare_link_gets_no_auto_propagation(self):
        # The warning is advisory: validate never rewrites the linking note
        # and the linker stays classified non-restricted.
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            before = (root / "normal.md").read_text(encoding="utf-8")
            errors, warnings = brain.run_validate(root, check_index=False)
            self.assertEqual((root / "normal.md").read_text(encoding="utf-8"), before)
            self.assertFalse(any(f["rule"] == "restricted-link" for f in errors))
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            self.assertFalse(brain.is_restricted(index["notes"]["normal.md"]))


class RestrictedQueryMetadataTests(unittest.TestCase):
    """R11/AE7 (KTD3): content-bearing query rows carry the privacy
    classification in JSON and a visible [restricted] label in human output;
    every pre-existing key survives unchanged."""

    def test_search_json_rows_carry_restricted(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            rc, out = run_cli(root, "search", "sensitive", "--json")
            self.assertEqual(rc, 0)
            rows = json.loads(out)
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(
                    sorted(row), ["field", "line", "path", "restricted", "snippet"]
                )
            self.assertTrue(all(r["restricted"] for r in rows))
            rc, out = run_cli(root, "search", "Nothing", "--json")
            rows = [r for r in json.loads(out) if r["path"] == "plain.md"]
            self.assertTrue(rows)
            self.assertTrue(all(r["restricted"] is False for r in rows))

    def test_search_human_output_labels_restricted_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            rc, out = run_cli(root, "search", "Secret Heading")
            self.assertEqual(rc, 0)
            secret_lines = [l for l in out.splitlines() if l.startswith("secret.md")]
            self.assertTrue(secret_lines)
            self.assertTrue(all("[restricted]" in l for l in secret_lines))
            rc, out = run_cli(root, "search", "Normal Heading")
            normal_lines = [l for l in out.splitlines() if l.startswith("normal.md")]
            self.assertTrue(normal_lines)
            self.assertTrue(all("[restricted]" not in l for l in normal_lines))

    def test_recent_json_rows_carry_restricted(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            rc, out = run_cli(root, "recent", "10", "--json")
            self.assertEqual(rc, 0)
            rows = json.loads(out)
            for row in rows:
                self.assertEqual(
                    sorted(row), ["path", "restricted", "title", "updated"]
                )
            by_path = {r["path"]: r for r in rows}
            self.assertTrue(by_path["secret.md"]["restricted"])
            self.assertFalse(by_path["plain.md"]["restricted"])

    def test_recent_human_output_labels_restricted_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            rc, out = run_cli(root, "recent", "10")
            self.assertEqual(rc, 0)
            lines = {l.split()[-2] if l.endswith("[restricted]") else l.split()[-1]: l
                     for l in out.splitlines()}
            self.assertIn("[restricted]", lines["secret.md"])
            self.assertNotIn("[restricted]", lines["plain.md"])

    def test_list_rows_carry_restricted_like_other_title_bearing_rows(self):
        # `list` rows expose titles, so they carry the same additive
        # `restricted` field as `recent` (R11: provenance rides on every
        # content-bearing row shape) — but ONLY in JSON. Human output must
        # stay bare paths with no [restricted] label: the documented
        # .cursorignore generator (harnesses/cursor/wiring.md) consumes each
        # printed line verbatim as a path.
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            rc, out = run_cli(root, "list", "--json")
            self.assertEqual(rc, 0)
            rows = {row["path"]: row for row in json.loads(out)}
            for row in rows.values():
                self.assertEqual(sorted(row), ["path", "restricted", "title", "updated"])
            self.assertTrue(rows["secret.md"]["restricted"])
            self.assertFalse(rows["plain.md"]["restricted"])
            rc, human = run_cli(root, "list")
            self.assertEqual(rc, 0)
            human_lines = human.splitlines()
            self.assertIn("secret.md", human_lines)
            self.assertIn("plain.md", human_lines)
            for line in human_lines:
                self.assertNotIn("[restricted]", line)
                self.assertEqual(line, line.strip())


def git(root: Path, *argv: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *argv],
        check=True,
        capture_output=True,
    )


def git_vault(td: Path, files: dict[str, str]) -> Path:
    root = make_vault(td, files)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(
        root,
        "-c", "user.email=test@example.invalid",
        "-c", "user.name=Test",
        "commit", "-q", "-m", "baseline",
    )
    return root


class RestrictedTransitionTests(unittest.TestCase):
    """R8/AE6 (KTD4): adding or removing restricted/private on a tracked note
    emits a bounded advisory warning — path + direction, no title or body
    prose — and detection skips silently without a trustworthy Git baseline."""

    def transitions(self, root: Path) -> tuple[list[dict], list[dict]]:
        errors, warnings = brain.run_validate(root, check_index=False)
        return errors, [f for f in warnings if f["rule"] == "restricted-transition"]

    def test_tag_added_reports_path_and_direction_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            (root / "plain.md").write_text(
                "---\ntitle: Plain\ntags:\n  - type/note\n  - restricted/private\n"
                "updated: 2026-08-11\n---\n\nNothing.\n",
                encoding="utf-8",
            )
            errors, hits = self.transitions(root)
            self.assertEqual([f["path"] for f in hits], ["plain.md"])
            self.assertIn("added", hits[0]["message"])
            # Fixed reminder about generated surfaces, never note content.
            self.assertIn("committed index", hits[0]["message"])
            self.assertNotIn("Plain", hits[0]["message"])
            self.assertNotIn("Nothing", hits[0]["message"])
            # Warning severity only: validate still exits without new errors.
            self.assertFalse(any(f["rule"] == "restricted-transition" for f in errors))

    def test_tag_removed_reports_removed_direction(self):
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            (root / "secret.md").write_text(
                "---\ntitle: Secret Plans\ntags:\n  - type/note\n"
                "updated: 2026-08-11\n---\n\n# Secret Heading\n\nBody.\n",
                encoding="utf-8",
            )
            _, hits = self.transitions(root)
            self.assertEqual([f["path"] for f in hits], ["secret.md"])
            self.assertIn("removed", hits[0]["message"])
            self.assertNotIn("Secret Plans", hits[0]["message"])

    def test_staged_only_flip_still_warns(self):
        # The next commit ships the staged index, not the worktree: a flip
        # that is staged while the worktree copy was reverted to HEAD bytes
        # must still warn at the pre-commit moment.
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            original = (root / "plain.md").read_text(encoding="utf-8")
            (root / "plain.md").write_text(
                "---\ntitle: Plain\ntags:\n  - type/note\n  - restricted/private\n"
                "updated: 2026-08-11\n---\n\nNothing.\n",
                encoding="utf-8",
            )
            git(root, "add", "plain.md")
            (root / "plain.md").write_text(original, encoding="utf-8")
            _, hits = self.transitions(root)
            self.assertEqual([f["path"] for f in hits], ["plain.md"])
            self.assertIn("added", hits[0]["message"])

    def test_staged_flip_with_deleted_worktree_copy_still_warns(self):
        # Staged candidates derive BOTH states from blobs (HEAD vs :0:), so a
        # staged de-restriction whose worktree file was since deleted (and
        # thus has no index record) must still warn — the next commit ships
        # the staged content regardless of the worktree.
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            original = (root / "secret.md").read_text(encoding="utf-8")
            (root / "secret.md").write_text(
                original.replace("  - restricted/private\n", ""),
                encoding="utf-8",
            )
            git(root, "add", "secret.md")
            (root / "secret.md").unlink()
            _, hits = self.transitions(root)
            self.assertEqual([f["path"] for f in hits], ["secret.md"])
            self.assertIn("removed", hits[0]["message"])

    def test_rename_with_flip_keeps_old_path_baseline(self):
        # A flip riding a `git mv` must not lose its baseline to the rename:
        # the old path's HEAD state is compared against the new path's state.
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            git(root, "mv", "secret.md", "topic.md")
            moved = (root / "topic.md").read_text(encoding="utf-8")
            (root / "topic.md").write_text(
                moved.replace("  - restricted/private\n", ""), encoding="utf-8"
            )
            git(root, "add", "topic.md")
            _, hits = self.transitions(root)
            self.assertEqual([f["path"] for f in hits], ["topic.md"])
            self.assertIn("removed", hits[0]["message"])

    def test_pure_rename_is_not_a_transition(self):
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            git(root, "mv", "secret.md", "moved-secret.md")
            _, hits = self.transitions(root)
            self.assertEqual(hits, [])

    def test_unchanged_tracked_vault_has_no_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            _, hits = self.transitions(root)
            self.assertEqual(hits, [])

    def test_untracked_new_note_is_not_a_transition(self):
        with tempfile.TemporaryDirectory() as td:
            root = git_vault(Path(td), base_files())
            (root / "fresh-secret.md").write_text(
                "---\ntitle: Fresh\ntags:\n  - type/note\n  - restricted/private\n"
                "updated: 2026-08-11\n---\n\nNew.\n",
                encoding="utf-8",
            )
            _, hits = self.transitions(root)
            self.assertEqual(hits, [])

    def test_no_git_repo_skips_silently(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            errors, hits = self.transitions(root)
            self.assertEqual(hits, [])
            # Normal validation is unaffected by the missing baseline.
            self.assertFalse(any(f["rule"] == "restricted-transition" for f in errors))

    def test_vault_nested_in_foreign_repo_skips_silently(self):
        # The baseline is only trustworthy when the vault root is the repo
        # toplevel; a vault folder inside some other repo must skip.
        with tempfile.TemporaryDirectory() as td:
            outer = Path(td)
            git_vault(outer, {"unrelated.txt": "outer repo file\n"})
            root = make_vault(outer / "vault", base_files())
            git(outer, "add", "-A")
            git(
                outer,
                "-c", "user.email=test@example.invalid",
                "-c", "user.name=Test",
                "commit", "-q", "-m", "add vault",
            )
            (root / "plain.md").write_text(
                "---\ntitle: Plain\ntags:\n  - type/note\n  - restricted/private\n"
                "updated: 2026-08-11\n---\n\nNothing.\n",
                encoding="utf-8",
            )
            _, hits = self.transitions(root)
            self.assertEqual(hits, [])


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
                "See [the secret alias text](other-secret.md#hidden-section) "
                "and ![normal](normal.md).\n"
            )
            root = make_vault(Path(td), files)
            reduced = brain.reduce_restricted(self.build(root))
            links = reduced["notes"]["secret.md"]["links"]
            self.assertEqual(len(links), 2)
            for link in links:
                self.assertIsNone(link["display"])
                self.assertIsNone(link["fragment"])
            self.assertEqual(links[0]["raw"], "[](other-secret.md)")
            self.assertEqual(links[1]["raw"], "![](normal.md)")
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
