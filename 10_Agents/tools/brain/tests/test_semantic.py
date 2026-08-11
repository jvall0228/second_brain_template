"""Tests for semantic search (spec §17, issue #8 QMD): sidecar round-trip,
hash staleness, hybrid-ranking determinism, keyword degradation, the
`embed --stdin-json` contract, and restricted/private containment.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

try:  # the one sanctioned optional dependency (spec §17.3)
    import sentence_transformers  # noqa: F401

    HAVE_LOCAL_MODEL = True
except Exception:
    HAVE_LOCAL_MODEL = False

NOTE_ALPHA = (
    "---\ntitle: Alpha\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
    "# Alpha\n\nGardening and compost heaps.\n"
)
NOTE_BETA = (
    "---\ntitle: Beta\ntags:\n  - type/note\nupdated: 2026-08-11\n---\n\n"
    "# Beta\n\nSoftware testing strategies.\n"
)
NOTE_SECRET = (
    "---\ntitle: Secret\ntags:\n  - type/note\n  - restricted/private\n"
    "updated: 2026-08-11\n---\n\nSensitive gardening body.\n"
)


def make_vault(tmp: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def base_files() -> dict[str, str]:
    return {"alpha.md": NOTE_ALPHA, "beta.md": NOTE_BETA, "secret.md": NOTE_SECRET}


def run(argv: list[str], stdin_text: str | None = None) -> tuple[int, str, str]:
    """Run brain.main capturing stdout/stderr, optionally feeding stdin."""
    out, err = io.StringIO(), io.StringIO()
    old_stdin = sys.stdin
    if stdin_text is not None:
        sys.stdin = io.StringIO(stdin_text)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = brain.main(argv)
    finally:
        sys.stdin = old_stdin
    return code, out.getvalue(), err.getvalue()


def ingest(root: Path, vectors: dict[str, list[float]], model: str = "toy") -> tuple[int, str, str]:
    payload = json.dumps({"model": model, "vectors": vectors})
    return run(["embed", "--stdin-json", "--json", "--vault", str(root)], payload)


class StoreRoundTripTests(unittest.TestCase):
    """§17.1/§17.2: sidecar write/read identity and best-effort loading."""

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            store = {
                "dim": 2,
                "model": "toy",
                "notes": {"alpha.md": {"hash": "a" * 64, "vector": [0.5, -0.25]}},
                "schemaVersion": brain.EMBED_SCHEMA_VERSION,
            }
            brain.save_embeddings(root, store)
            self.assertEqual(brain.load_embeddings(root), store)

    def test_missing_sidecar_is_empty_store(self):
        with tempfile.TemporaryDirectory() as td:
            store = brain.load_embeddings(Path(td))
            self.assertEqual(store["notes"], {})

    def test_malformed_sidecar_treated_as_absent_with_notice(self):
        cases = [
            "not json at all",
            json.dumps({"schemaVersion": 999, "model": "m", "dim": 2, "notes": {}}),
            json.dumps({"schemaVersion": 1, "model": "", "dim": 2, "notes": {}}),
            json.dumps(
                {
                    "schemaVersion": 1,
                    "model": "m",
                    "dim": 2,
                    "notes": {"alpha.md": {"hash": "x", "vector": [1.0]}},
                }
            ),
        ]
        for content in cases:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / brain.EMBED_RELPATH).parent.mkdir(parents=True)
                (root / brain.EMBED_RELPATH).write_text(content, encoding="utf-8")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    store = brain.load_embeddings(root)
                self.assertEqual(store["notes"], {}, content)
                self.assertIn("ignoring embeddings sidecar", err.getvalue())

    def test_sidecar_is_pruned_from_the_corpus(self):
        # §2: like the index file, the sidecar never appears as an asset.
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]})
            self.assertTrue((root / brain.EMBED_RELPATH).exists())
            _notes, assets = brain.walk_corpus(root)
            self.assertNotIn(brain.EMBED_RELPATH, assets)

    def test_hash_is_over_normalized_text(self):
        # §17.1: CRLF and LF copies of a note hash identically (§3).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "lf.md").write_bytes(b"---\ntitle: X\n---\nbody\n")
            (root / "crlf.md").write_bytes(b"---\r\ntitle: X\r\n---\r\nbody\r\n")
            lf, _ = brain.load_text(root, "lf.md")
            crlf, _ = brain.load_text(root, "crlf.md")
            self.assertEqual(
                brain.note_content_hash(lf), brain.note_content_hash(crlf)
            )


class EmbedStdinJsonTests(unittest.TestCase):
    """§17.3: the --stdin-json ingestion contract."""

    def test_happy_path_writes_hashed_entries(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, out, _err = ingest(root, {"alpha.md": [1.0, 0.0], "beta.md": [0.0, 1.0]})
            self.assertEqual(code, 0)
            summary = json.loads(out)
            self.assertEqual(summary["stored"], 2)
            self.assertEqual(summary["dim"], 2)
            store = brain.load_embeddings(root)
            self.assertEqual(set(store["notes"]), {"alpha.md", "beta.md"})
            text, _ = brain.load_text(root, "alpha.md")
            self.assertEqual(
                store["notes"]["alpha.md"]["hash"], brain.note_content_hash(text)
            )

    def test_partial_update_merges_same_model(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]})
            ingest(root, {"beta.md": [0.0, 1.0]})
            store = brain.load_embeddings(root)
            self.assertEqual(set(store["notes"]), {"alpha.md", "beta.md"})

    def test_model_change_replaces_wholesale(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]}, model="toy")
            code, _out, err = ingest(root, {"beta.md": [0.0, 1.0, 0.0]}, model="other")
            self.assertEqual(code, 0)
            self.assertIn("replacing the sidecar wholesale", err)
            store = brain.load_embeddings(root)
            self.assertEqual(set(store["notes"]), {"beta.md"})
            self.assertEqual(store["model"], "other")
            self.assertEqual(store["dim"], 3)

    def test_malformed_inputs_are_operational_errors(self):
        cases = [
            "not json",
            json.dumps(["not", "an", "object"]),
            json.dumps({"model": "toy"}),  # missing vectors
            json.dumps({"model": "", "vectors": {"alpha.md": [1.0]}}),
            json.dumps({"model": "toy", "vectors": {}}),
            json.dumps({"model": "toy", "vectors": {"alpha.md": []}}),
            json.dumps({"model": "toy", "vectors": {"alpha.md": [1.0, "x"]}}),
            json.dumps({"model": "toy", "vectors": {"alpha.md": [1.0], "beta.md": [1.0, 2.0]}}),
        ]
        for payload in cases:
            with tempfile.TemporaryDirectory() as td:
                root = make_vault(Path(td), base_files())
                code, _out, err = run(
                    ["embed", "--stdin-json", "--vault", str(root)], payload
                )
                self.assertEqual(code, 1, payload)
                self.assertIn("error:", err)
                self.assertFalse((root / brain.EMBED_RELPATH).exists())

    def test_unknown_path_fails_all_or_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, _out, err = ingest(
                root, {"alpha.md": [1.0, 0.0], "no-such.md": [0.0, 1.0]}
            )
            self.assertEqual(code, 1)
            self.assertIn("unknown note paths", err)
            self.assertFalse((root / brain.EMBED_RELPATH).exists())

    def test_status_reports_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]})
            code, out, _err = run(["embed", "--status", "--json", "--vault", str(root)])
            self.assertEqual(code, 0)
            status = json.loads(out)
            # secret.md is restricted — outside the embeddable universe.
            self.assertEqual(status["notes"], 2)
            self.assertEqual(status["embedded"], 1)
            self.assertEqual(status["missing"], 1)
            self.assertEqual(status["stale"], 0)

    @unittest.skipIf(HAVE_LOCAL_MODEL, "optional dependency is installed here")
    def test_local_without_dependency_degrades_with_message(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, _out, err = run(["embed", "--local", "--vault", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("sentence-transformers", err)
            self.assertNotIn("Traceback", err)
            self.assertFalse((root / brain.EMBED_RELPATH).exists())


class StalenessTests(unittest.TestCase):
    """§17.2: hash mismatch excludes the entry from semantic ranking."""

    def test_edited_note_goes_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0], "beta.md": [0.0, 1.0]})
            (root / "alpha.md").write_text(
                NOTE_ALPHA + "\nEdited after embedding.\n", encoding="utf-8"
            )
            notes, assets = brain.walk_corpus(root)
            index = brain.build_index(root, notes, assets)
            store = brain.load_embeddings(root)
            fresh = brain.fresh_entries(index, store, brain.note_hashes(root, index))
            self.assertEqual(set(fresh), {"beta.md"})
            code, out, _err = run(
                ["search", "--semantic", "gardening", "--json", "--query-vector", "--vault", str(root)],
                "[1.0, 0.0]",
            )
            self.assertEqual(code, 0)
            rows = {r["path"]: r for r in json.loads(out)}
            # Stale alpha participates through the keyword component only.
            self.assertIsNone(rows["alpha.md"]["semanticScore"])
            self.assertEqual(rows["alpha.md"]["score"], 0.3)
            self.assertIsNotNone(rows["beta.md"]["semanticScore"])

    def test_all_stale_degrades_to_keyword(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]})
            (root / "alpha.md").write_text(NOTE_ALPHA + "\nEdit.\n", encoding="utf-8")
            code, out, err = run(
                ["search", "--semantic", "gardening", "--json", "--vault", str(root)]
            )
            self.assertEqual(code, 0)
            self.assertIn("falling back to keyword search", err)
            self.assertTrue(all("field" in r for r in json.loads(out)))


class SemanticRankingTests(unittest.TestCase):
    """§17.4: exact hybrid scores, ordering, and determinism."""

    def search(self, root: Path, query: str, qvec: list[float]) -> tuple[int, str, str]:
        return run(
            ["search", "--semantic", query, "--json", "--query-vector", "--vault", str(root)],
            json.dumps(qvec),
        )

    def test_exact_hybrid_scores(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0], "beta.md": [0.0, 1.0]})
            code, out, _err = self.search(root, "gardening", [1.0, 0.0])
            self.assertEqual(code, 0)
            rows = json.loads(out)
            # alpha:  sem = (1+1)/2 = 1.0, kw hit -> 0.7*1 + 0.3 = 1.0 (rank 1)
            # beta:   sem = (0+1)/2 = 0.5, no kw -> 0.35
            # secret: restricted, no vector, but its body mentions gardening —
            #         keyword component only (§17.1), 0.3.
            self.assertEqual(
                [(r["path"], r["score"]) for r in rows],
                [("alpha.md", 1.0), ("beta.md", 0.35), ("secret.md", 0.3)],
            )
            self.assertIsNone(rows[2]["semanticScore"])
            self.assertEqual(rows[0]["semanticScore"], 1.0)
            self.assertEqual(rows[1]["semanticScore"], 0.5)
            self.assertGreater(rows[0]["keywordHits"], 0)
            self.assertEqual(rows[1]["keywordHits"], 0)

    def test_two_runs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [0.6, 0.8], "beta.md": [0.8, 0.6]})
            first = self.search(root, "strategies", [0.7, 0.7])
            second = self.search(root, "strategies", [0.7, 0.7])
            self.assertEqual(first, second)

    def test_ties_break_by_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0], "beta.md": [1.0, 0.0]})
            code, out, _err = self.search(root, "zzz-no-keyword-match", [1.0, 0.0])
            self.assertEqual(code, 0)
            self.assertEqual([r["path"] for r in json.loads(out)], ["alpha.md", "beta.md"])

    def test_top_truncates(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0], "beta.md": [0.0, 1.0]})
            code, out, _err = run(
                [
                    "search", "--semantic", "zzz", "--json", "--query-vector",
                    "--top", "1", "--vault", str(root),
                ],
                "[1.0, 0.0]",
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(json.loads(out)), 1)

    def test_bad_query_vector_is_operational_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]})
            for stdin_text in ("not json", '["x"]', "[1.0]"):  # wrong dim last
                code, _out, err = run(
                    ["search", "--semantic", "q", "--query-vector", "--vault", str(root)],
                    stdin_text,
                )
                self.assertEqual(code, 1, stdin_text)
                self.assertIn("error:", err)


class DegradationTests(unittest.TestCase):
    """§17.4: --semantic never hard-fails on a vectorless vault."""

    def test_no_sidecar_matches_plain_search_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, sem_out, err = run(
                ["search", "--semantic", "gardening", "--json", "--vault", str(root)]
            )
            self.assertEqual(code, 0)
            self.assertIn("semantic search unavailable", err)
            plain_code, plain_out, _ = run(
                ["search", "gardening", "--json", "--vault", str(root)]
            )
            self.assertEqual(plain_code, 0)
            self.assertEqual(sem_out, plain_out)

    def test_query_vector_flag_still_degrades_on_empty_store(self):
        # Degradation is checked before stdin is consumed (spec §17.4).
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, _out, err = run(
                ["search", "--semantic", "gardening", "--query-vector", "--vault", str(root)]
            )
            self.assertEqual(code, 0)
            self.assertIn("falling back to keyword search", err)

    @unittest.skipIf(HAVE_LOCAL_MODEL, "optional dependency is installed here")
    def test_no_query_source_degrades(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0]})
            code, _out, err = run(
                ["search", "--semantic", "gardening", "--json", "--vault", str(root)]
            )
            self.assertEqual(code, 0)
            self.assertIn("no query embedding source", err)


class RestrictedContainmentTests(unittest.TestCase):
    """§17.1: restricted/private notes never enter or rank via the sidecar."""

    def test_embed_skips_restricted_with_notice(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            code, out, err = ingest(
                root, {"alpha.md": [1.0, 0.0], "secret.md": [1.0, 0.0]}
            )
            self.assertEqual(code, 0)
            self.assertIn("restricted/private", err)
            summary = json.loads(out)
            self.assertEqual(summary["skippedRestricted"], ["secret.md"])
            self.assertEqual(summary["stored"], 1)
            self.assertNotIn("secret.md", brain.load_embeddings(root)["notes"])

    def test_search_ignores_sidecar_entry_for_now_restricted_note(self):
        # A vector embedded before the note was tagged restricted must stop
        # ranking the moment the tag lands, sidecar regeneration or not.
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), base_files())
            ingest(root, {"alpha.md": [1.0, 0.0], "beta.md": [0.0, 1.0]})
            tagged = NOTE_ALPHA.replace(
                "tags:\n  - type/note\n", "tags:\n  - type/note\n  - restricted/private\n"
            )
            (root / "alpha.md").write_text(tagged, encoding="utf-8")
            # Recompute the hash so ONLY restriction (not staleness) excludes it.
            text, _ = brain.load_text(root, "alpha.md")
            store = brain.load_embeddings(root)
            store["notes"]["alpha.md"]["hash"] = brain.note_content_hash(text)
            brain.save_embeddings(root, store)
            code, out, _err = run(
                ["search", "--semantic", "zzz", "--json", "--query-vector", "--vault", str(root)],
                "[1.0, 0.0]",
            )
            self.assertEqual(code, 0)
            self.assertEqual([r["path"] for r in json.loads(out)], ["beta.md"])


if __name__ == "__main__":
    unittest.main()
