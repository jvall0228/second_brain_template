"""Golden-file tests: the exact bytes `brain` renders for the fixture index,
an empty-state Home, and an empty-state AYMT brief. Any change to these bytes
is a deliberate contract change — regenerate with

    BRAIN_UPDATE_GOLDEN=1 python3 10_Agents/tools/run_tests.py

and review the diff of tests/golden/ in the same commit as the code change.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402
from test_aymt import VaultFixture  # noqa: E402
from test_brain import FIXTURE  # noqa: E402
from test_home import HomeVault  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden"
UPDATE = os.environ.get("BRAIN_UPDATE_GOLDEN") == "1"


class GoldenTests(unittest.TestCase):
    def check(self, name: str, actual: bytes) -> None:
        path = GOLDEN / name
        if UPDATE:
            path.write_bytes(actual)
            return
        self.assertTrue(path.exists(), f"missing golden file {path.name}; run with BRAIN_UPDATE_GOLDEN=1")
        expected = path.read_bytes()
        if actual != expected:
            a = actual.decode("utf-8", "replace").splitlines()
            e = expected.decode("utf-8", "replace").splitlines()
            first = next((i for i, (x, y) in enumerate(zip(a, e)) if x != y), min(len(a), len(e)))
            self.fail(
                f"{path.name} differs from the rendered bytes (first difference at line {first + 1}):\n"
                f"  golden:   {e[first] if first < len(e) else '<eof>'!r}\n"
                f"  rendered: {a[first] if first < len(a) else '<eof>'!r}\n"
                "If the change is intended, regenerate with BRAIN_UPDATE_GOLDEN=1 and commit tests/golden/."
            )

    def test_fixture_index_bytes(self):
        notes, assets = brain.walk_corpus(FIXTURE)
        rendered = brain.serialize(brain.build_index(FIXTURE, notes, assets))
        self.check("fixture-index.json", rendered)

    def test_home_empty_state_bytes(self):
        vault = HomeVault()
        try:
            rendered = brain.render_home(vault.build())
        finally:
            vault.cleanup()
        self.assertEqual(rendered, rendered.replace(b"\r", b""))
        self.check("home-empty-state.md", rendered)

    def test_aymt_empty_state_bytes(self):
        vault = VaultFixture()
        try:
            rendered = brain.render_aymt(vault.build())
        finally:
            vault.cleanup()
        self.check("aymt-empty-state.md", rendered)


if __name__ == "__main__":
    unittest.main()
