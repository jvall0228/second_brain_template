"""Tests for the §10.6 warning ratchet: baseline identity, serialization,
matching, and the validate CLI's --all / --write-baseline behavior.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402
from test_brain import FIXTURE, make_vault  # noqa: E402

CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(encoding="utf-8")


def note(tags):
    body = "---\ntitle: Draft\ntags:\n" + "".join(f"  - {t}\n" for t in tags)
    return body + "updated: 2026-08-11\n---\n\nBody.\n"


def warning(path, rule, message, line=None):
    return {"line": line, "message": message, "path": path, "rule": rule}


class BaselineKeyTests(unittest.TestCase):
    def test_line_and_standalone_numbers_are_folded(self):
        a = warning("a.md", "oversized", "oversized: 21857 bytes / 158 lines exceeds 20000 bytes", 3)
        b = warning("a.md", "oversized", "oversized: 30001 bytes / 402 lines exceeds 20000 bytes", 9)
        self.assertEqual(brain.baseline_key(a), brain.baseline_key(b))

    def test_path_embedded_digits_survive(self):
        a = warning("a.md", "restricted-link", "[x](../05_Areas/one-2026-08-31.md) links", 1)
        b = warning("a.md", "restricted-link", "[x](../05_Areas/one-2026-09-01.md) links", 1)
        self.assertNotEqual(brain.baseline_key(a), brain.baseline_key(b))
        self.assertIn("05_Areas", brain.baseline_key(a)[2])

    def test_rule_and_path_distinguish(self):
        a = warning("a.md", "r1", "m")
        self.assertNotEqual(brain.baseline_key(a), brain.baseline_key(warning("b.md", "r1", "m")))
        self.assertNotEqual(brain.baseline_key(a), brain.baseline_key(warning("a.md", "r2", "m")))


class RatchetTests(unittest.TestCase):
    def test_no_baseline_everything_new(self):
        ws = [warning("a.md", "r", "m")]
        new, old, stale = brain.ratchet_warnings(ws, None)
        self.assertEqual((new, old, stale), (ws, [], 0))

    def test_counts_cover_first_occurrences_only(self):
        ws = [warning("a.md", "r", "m", 1), warning("a.md", "r", "m", 5), warning("a.md", "r", "m", 9)]
        baseline = {brain.baseline_key(ws[0]): 2}
        new, old, stale = brain.ratchet_warnings(ws, baseline)
        self.assertEqual([w["line"] for w in old], [1, 5])
        self.assertEqual([w["line"] for w in new], [9])
        self.assertEqual(stale, 0)

    def test_stale_entries_counted_never_fail(self):
        baseline = {("gone.md", "r", "m"): 1, ("a.md", "r", "m"): 1}
        new, old, stale = brain.ratchet_warnings([warning("a.md", "r", "m")], baseline)
        self.assertEqual((len(new), len(old), stale), (0, 1, 1))

    def test_serialize_round_trip_is_deterministic(self):
        ws = [warning("b.md", "r", "m 2", 4), warning("a.md", "r", "m 1", 2), warning("b.md", "r", "m 2", 8)]
        payload = brain.serialize_baseline(ws)
        self.assertEqual(payload, brain.serialize_baseline(list(reversed(ws))))
        data = json.loads(payload)
        self.assertEqual(data["schemaVersion"], brain.BASELINE_SCHEMA_VERSION)
        self.assertEqual([r["path"] for r in data["warnings"]], ["a.md", "b.md"])
        self.assertEqual(data["warnings"][1]["count"], 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / brain.BASELINE_RELPATH
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            self.assertEqual(brain.load_baseline(root), {brain.baseline_key(ws[1]): 1, brain.baseline_key(ws[0]): 2})

    def test_unreadable_or_wrong_schema_is_no_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertIsNone(brain.load_baseline(root))
            target = root / brain.BASELINE_RELPATH
            target.parent.mkdir(parents=True)
            target.write_text("{not json", encoding="utf-8")
            self.assertIsNone(brain.load_baseline(root))
            target.write_text(json.dumps({"schemaVersion": 99, "warnings": []}), encoding="utf-8")
            self.assertIsNone(brain.load_baseline(root))


class ValidateCliTests(unittest.TestCase):
    """A vault with one standing warning (a 02_Inbox agent draft without
    author:) exercises the flags end to end."""

    FILES = {
        "00_Meta/CONVENTIONS.md": CONVENTIONS,
        "02_Inbox/2026-08-11-draft.md": note(tags=("type/note", "audience/agent", "workflow/draft")),
    }

    def run_cli(self, root, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue()

    def test_write_baseline_then_hidden_then_all(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), dict(self.FILES))
            code, out = self.run_cli(root, "validate")
            self.assertEqual(code, 2)
            self.assertIn("missing-author", out)
            self.assertTrue(out.strip().endswith("0 errors, 1 warnings"))

            code, out = self.run_cli(root, "validate", "--write-baseline")
            self.assertEqual(code, 0)
            self.assertIn("1 warnings baselined", out)
            self.assertTrue((root / brain.BASELINE_RELPATH).exists())
            # The baseline file never enters the corpus as an asset.
            _notes, assets = brain.walk_corpus(root, selected_environment=None)
            self.assertNotIn(brain.BASELINE_RELPATH, assets)

            code, out = self.run_cli(root, "validate")
            self.assertEqual(code, 0)
            self.assertNotIn("missing-author", out)
            self.assertIn("0 errors, 0 warnings (1 baselined, hidden; --all shows them)", out)

            code, out = self.run_cli(root, "validate", "--all")
            self.assertEqual(code, 2)
            self.assertIn("missing-author", out)
            self.assertTrue(out.strip().endswith("0 errors, 1 warnings"))

            code, out = self.run_cli(root, "validate", "--json")
            data = json.loads(out)
            self.assertEqual(code, 0)
            self.assertEqual(data["warnings"], [])
            self.assertEqual([f["rule"] for f in data["baselined"]], ["missing-author"])

            # A second, new warning surfaces alone; the cleared entry is reported.
            (root / "02_Inbox/2026-08-11-draft.md").write_text(
                note(tags=("type/note", "workflow/draft")), encoding="utf-8"
            )
            (root / "02_Inbox/2026-08-12-other.md").write_text(
                note(tags=("type/note", "audience/agent", "workflow/draft")), encoding="utf-8"
            )
            code, out = self.run_cli(root, "validate")
            self.assertEqual(code, 2)
            self.assertIn("WARN 02_Inbox/2026-08-12-other.md missing-author", out)
            self.assertNotIn("2026-08-11-draft.md missing-author", out)
            self.assertIn("1 baseline entries cleared", out)


# Synthetic, never-valid token shape (the §10.5 github-token rule matches the
# prefix + 20 alphanumerics; this value is documented as an example).
FAKE_TOKEN = "ghp_" + "EXAMPLEEXAMPLEEXAMPLE1234"  # brain:allow-secret-pattern


class WriteBaselineSafetyTests(unittest.TestCase):
    """F1: a failing validation never persists anything into the baseline,
    and credential-shaped warning text is refused outright."""

    RESTRICTED = (
        "---\ntitle: Secret\ntags:\n  - type/note\n  - restricted/private\n"
        "updated: 2026-08-11\n---\n\nSensitive.\n"
    )
    CONV = CONVENTIONS + "| `restricted/*` | Privacy marking | `private` |\n"

    def run_cli(self, root, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue(), err.getvalue()

    def files(self, label="secret"):
        # An untagged note linking a restricted note with a token-shaped label:
        # one restricted-link warning whose message carries the label, plus a
        # secret-github-token error on the same line.
        return {
            "00_Meta/CONVENTIONS.md": self.CONV,
            "secret.md": self.RESTRICTED,
            "linker.md": (
                "---\ntitle: Linker\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
                f"See [{label}](secret.md).\n"
            ),
        }

    def test_errors_leave_existing_baseline_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files())
            code, out, _ = self.run_cli(root, "validate", "--write-baseline")
            self.assertEqual(code, 0)
            before = (root / brain.BASELINE_RELPATH).read_bytes()
            self.assertIn("secret.md", before.decode("utf-8"))
            (root / "linker.md").write_text(
                self.files(FAKE_TOKEN)["linker.md"], encoding="utf-8"
            )
            code, out, err = self.run_cli(root, "validate", "--write-baseline")
            self.assertEqual(code, 1)
            self.assertIn("ERROR linker.md:8 secret-github-token", out)
            self.assertIn("baseline not written", err)
            self.assertEqual((root / brain.BASELINE_RELPATH).read_bytes(), before)
            self.assertNotIn(FAKE_TOKEN.encode(), before)

    def test_errors_create_no_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files(FAKE_TOKEN))
            code, out, err = self.run_cli(root, "validate", "--write-baseline", "--json")
            self.assertEqual(code, 1)
            data = json.loads(out)
            self.assertFalse(data["written"])
            self.assertEqual(data["baselined"], 0)
            self.assertIn("secret-github-token", [f["rule"] for f in data["errors"]])
            self.assertFalse((root / brain.BASELINE_RELPATH).exists())
            self.assertFalse(list((root / "10_Agents").rglob("*")) if (root / "10_Agents").exists() else [])

    def test_serializer_refuses_credential_shaped_warning_text(self):
        # Backstop below the CLI: even a warning list handed straight to the
        # serializer cannot carry secret-shaped text into the baseline bytes.
        rows = [warning("a.md", "restricted-link", f"[{FAKE_TOKEN}](s.md) links a restricted note", 3)]
        with self.assertRaises(brain.BaselineError):
            brain.serialize_baseline(rows)
        payload = brain.serialize_baseline([warning("a.md", "restricted-link", "[x](s.md) links", 3)])
        self.assertNotIn(b"ghp_", payload)

    def test_successful_write_still_works_and_reports_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files())
            code, out, _ = self.run_cli(root, "validate", "--write-baseline", "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            # Written like every other note: world-readable (0644), so another
            # uid sharing the checkout still sees the ratchet, not a fresh set
            # of "new" warnings.
            mode = (root / brain.BASELINE_RELPATH).stat().st_mode
            self.assertEqual(stat.S_IMODE(mode) & 0o044, 0o044)
            self.assertEqual((data["written"], data["errors"], data["refusal"]), (True, [], None))
            loaded = brain.load_baseline(root)
            self.assertEqual(sum(loaded.values()), data["baselined"])
            self.assertIn(
                ("linker.md", "restricted-link", brain.baseline_key(warning(
                    "linker.md", "restricted-link",
                    "[secret](secret.md) links a restricted/private note (secret.md) — informational: "
                    "check whether nearby prose carries private substance; if it does, this note must "
                    "also carry restricted/private (a bare link alone does not propagate the tag)",
                ))[2]),
                loaded,
            )

    def test_write_refuses_symlinked_target_and_parent(self):
        if not hasattr(os, "symlink"):
            self.skipTest("no symlinks")
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), self.files())
            outside = Path(td) / "outside.json"
            outside.write_bytes(b"external\n")
            target = root / brain.BASELINE_RELPATH
            target.parent.mkdir(parents=True)
            os.symlink(outside, target)
            code, _, err = self.run_cli(root, "validate", "--write-baseline")
            self.assertEqual(code, 1)
            self.assertIn("not a regular file", err)
            self.assertEqual(outside.read_bytes(), b"external\n")
            target.unlink()
            # A symlinked parent component is refused the same way.
            parent = target.parent
            parent.rmdir()
            elsewhere = Path(td) / "elsewhere"
            elsewhere.mkdir()
            os.symlink(elsewhere, parent)
            code, _, err = self.run_cli(root, "validate", "--write-baseline")
            self.assertEqual(code, 1)
            self.assertIn("not a real directory", err)
            self.assertEqual(list(elsewhere.iterdir()), [])


class MalformedBaselineTests(unittest.TestCase):
    """F12: anything off-shape is no baseline at all — warnings stay visible."""

    def check(self, data, expect_none=True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / brain.BASELINE_RELPATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(data), encoding="utf-8")
            result = brain.load_baseline(root)
            if expect_none:
                self.assertIsNone(result, data)
            return result

    def test_non_list_warnings_is_no_baseline(self):
        self.check({"schemaVersion": 1, "warnings": 1})
        self.check({"schemaVersion": 1, "warnings": {"path": "a.md"}})
        self.check({"schemaVersion": 1, "warnings": None})

    def test_bad_rows_and_counts_are_no_baseline(self):
        good = {"count": 1, "message": "m", "path": "a.md", "rule": "r"}
        for bad in (
            "row",
            {**good, "path": 3},
            {**good, "path": ""},
            {**good, "rule": None},
            {**good, "message": ["m"]},
            {**good, "count": 0},
            {**good, "count": -1},
            {**good, "count": True},
            {**good, "count": "2"},
            {**good, "count": 1.0},
        ):
            self.check({"schemaVersion": 1, "warnings": [good, bad]})

    def test_malformed_baseline_reveals_warnings(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), dict(ValidateCliTests.FILES))
            target = root / brain.BASELINE_RELPATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({"schemaVersion": 1, "warnings": 1}), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = brain.main(["validate", "--vault", str(root)])
            self.assertEqual(code, 2)
            self.assertIn("missing-author", out.getvalue())

    def test_well_formed_rows_still_load(self):
        result = self.check(
            {"schemaVersion": 1, "warnings": [{"count": 2, "message": "m", "path": "a.md", "rule": "r"}]},
            expect_none=False,
        )
        self.assertEqual(result, {("a.md", "r", "m"): 2})


class BaselineReadSafetyTests(unittest.TestCase):
    """R3: a baseline reached through any symlink is no baseline — every
    warning stays visible, exactly as for a malformed file."""

    FILES = dict(ValidateCliTests.FILES)

    def run_cli(self, root, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue()

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_baseline_target_and_parent_are_no_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td) / "vault", dict(self.FILES))
            code, _ = self.run_cli(root, "validate", "--write-baseline")
            self.assertEqual(code, 0)
            target = root / brain.BASELINE_RELPATH
            valid = target.read_bytes()
            outside = Path(td) / "outside-baseline.json"
            outside.write_bytes(valid)  # a valid, matching baseline outside the vault
            target.unlink()
            os.symlink(outside, target)
            self.assertIsNone(brain.load_baseline(root))
            code, out = self.run_cli(root, "validate")
            self.assertEqual(code, 2)
            self.assertIn("missing-author", out)
            self.assertNotIn("baselined", out)
            target.unlink()
            # Parent directory replaced by a symlink to a directory holding
            # a valid baseline.
            parent = target.parent
            parent.rmdir()
            elsewhere = Path(td) / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / target.name).write_bytes(valid)
            os.symlink(elsewhere, parent)
            self.assertIsNone(brain.load_baseline(root))
            code, out = self.run_cli(root, "validate")
            self.assertEqual(code, 2)
            self.assertIn("missing-author", out)
            # Restoring a real directory and regular file restores the ratchet.
            parent.unlink()
            parent.mkdir()
            target.write_bytes(valid)
            self.assertEqual(sum(brain.load_baseline(root).values()), 1)
            code, out = self.run_cli(root, "validate")
            self.assertEqual(code, 0)
            self.assertIn("1 baselined", out)


if __name__ == "__main__":
    unittest.main()
