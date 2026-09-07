"""Source interleavings must not mix note content, privacy, or embedding hashes."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain
from note_snapshots import NoteSnapshot


PUBLIC = "---\ntitle: Note\ntags: [type/note]\nupdated: 2026-09-05\n---\nPUBLIC_MARKER\n"
PRIVATE = PUBLIC.replace("type/note]", "type/note, restricted/private]").replace("PUBLIC_MARKER", "PRIVATE_MARKER")


def run(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = brain.main(args)
    return code, out.getvalue(), err.getvalue()


class QuerySnapshotTests(unittest.TestCase):
    def test_privacy_and_body_stay_on_one_snapshot_in_keyword_and_fallback_search(self):
        for flags in ([], ["--semantic"]):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                source = root / "note.md"
                source.write_text(PUBLIC)
                reader = brain._read_vault_bytes
                reads = []

                def read_then_edit(vault, rel, **kwargs):
                    raw = reader(vault, rel, **kwargs)
                    if rel == "note.md":
                        reads.append(rel)
                        source.write_text(PRIVATE)
                    return raw

                with patch.object(brain, "_read_vault_bytes", side_effect=read_then_edit):
                    code, out, _err = run(["search", "MARKER", "--json", "--vault", td, *flags])
                self.assertEqual(code, 0)
                rows = json.loads(out)
                self.assertEqual(reads, ["note.md"])
                self.assertEqual(rows, [{"field": "body", "line": 6, "path": "note.md", "restricted": False, "explicitRestricted": False, "privacy": "public", "snippet": "PUBLIC_MARKER"}])
                # A subsequent invocation observes the edit and its privacy.
                code, out, _err = run(["search", "MARKER", "--json", "--vault", td])
                self.assertEqual(code, 0)
                self.assertTrue(json.loads(out)[0]["restricted"])
                self.assertEqual(json.loads(out)[0]["snippet"], "PRIVATE_MARKER")

    def test_semantic_freshness_and_metadata_use_the_same_source_as_keyword_hits(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "note.md"
            source.write_text(PUBLIC)
            brain.save_embeddings(root, {
                "schemaVersion": 1, "model": "toy", "dim": 2,
                "notes": {"note.md": {"hash": brain.note_content_hash(PUBLIC), "vector": [1.0, 0.0]}},
            })
            reader = brain._read_vault_bytes

            def read_then_edit(vault, rel, **kwargs):
                raw = reader(vault, rel, **kwargs)
                if rel == "note.md":
                    source.write_text(PRIVATE)
                return raw

            with patch.object(brain, "_read_vault_bytes", side_effect=read_then_edit), patch.object(sys, "stdin", io.StringIO("[1.0, 0.0]")):
                code, out, _err = run(["search", "PUBLIC_MARKER", "--semantic", "--query-vector", "--json", "--vault", td])
            self.assertEqual(code, 0)
            row = json.loads(out)[0]
            self.assertFalse(row["restricted"])
            self.assertEqual(row["semanticScore"], 1.0)
            self.assertEqual(row["keywordHits"], 1)


class EmbeddingSnapshotTests(unittest.TestCase):
    def test_local_embedding_hash_identifies_the_exact_text_given_to_the_model(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "note.md"
            source.write_text(PUBLIC)
            encoded = []

            def model_loaded_after_edit(_model):
                source.write_text(PRIVATE)

                def encode(texts):
                    encoded.extend(texts)
                    return [list((1.0, 0.0)) for _ in texts]

                return encode

            with patch.object(brain, "local_embedder", side_effect=model_loaded_after_edit):
                code, _out, _err = run(["embed", "--local", "--json", "--vault", td])
            self.assertEqual(code, 0)
            self.assertEqual(encoded, [PUBLIC])
            stored = brain.load_embeddings(root)["notes"]["note.md"]
            self.assertEqual(stored["hash"], brain.note_content_hash(encoded[0]))
            code, out, _err = run(["embed", "--status", "--json", "--vault", td])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["stale"], 1)

    def test_snapshot_normalizes_bom_and_newlines_before_hashing(self):
        raw = ("\ufeff" + PUBLIC).replace("\n", "\r\n").encode("utf-8")
        snapshot = NoteSnapshot.from_bytes(raw)
        self.assertEqual(snapshot.text, PUBLIC)
        self.assertEqual(snapshot.size_bytes, len(PUBLIC.encode("utf-8")))
        self.assertEqual(snapshot.digest, brain.note_content_hash(PUBLIC))


if __name__ == "__main__":
    unittest.main()
