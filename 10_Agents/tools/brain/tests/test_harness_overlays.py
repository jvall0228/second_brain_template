"""Mechanical contract tests for per-harness overlays (issue #3, M10.3).

Overlays live at 10_Agents/harnesses/<name>/overlay/ and ship harness-native
primitives plus a manifest.json describing what installs where and how each
artifact reverses. These tests pin structure only (JSON shape, required keys,
referenced files exist, portable placeholders) — never prose sentences.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HARNESS_DIR = ROOT / "10_Agents/harnesses"

# Overlays this template intentionally ships. Discovery below also picks up any
# overlay added later without editing this list.
EXPECTED_OVERLAYS = {"cursor", "copilot"}

ALLOWED_INSTALL_METHODS = {"copy", "marker-block", "generate", "shipped-in-repo"}
ALLOWED_REVERSE_METHODS = {"delete", "remove-marker-block", "none"}
ALLOWED_SOURCE_ROOTS = {"overlay", "repo"}
ALLOWED_SCOPES = {"project", "user"}

# Same adopter-path-leak patterns the harness-registration suite applies to
# wiring docs, extended here over every tracked overlay file.
PATH_LEAK_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
)


def overlay_dirs():
    return sorted(p for p in HARNESS_DIR.glob("*/overlay") if p.is_dir())


def load_manifest(overlay_dir: Path) -> dict:
    return json.loads((overlay_dir / "manifest.json").read_text(encoding="utf-8"))


class OverlayManifestShapeTests(unittest.TestCase):
    def test_expected_overlays_ship(self):
        found = {p.parent.name for p in overlay_dirs()}
        self.assertTrue(EXPECTED_OVERLAYS.issubset(found), f"missing overlays: {EXPECTED_OVERLAYS - found}")

    def test_every_overlay_has_a_parseable_manifest(self):
        for overlay in overlay_dirs():
            with self.subTest(overlay=overlay.parent.name):
                manifest_path = overlay / "manifest.json"
                self.assertTrue(manifest_path.is_file(), f"{manifest_path} missing")
                data = load_manifest(overlay)  # raises on invalid JSON
                self.assertIsInstance(data, dict)

    def test_manifest_top_level_keys(self):
        for overlay in overlay_dirs():
            with self.subTest(overlay=overlay.parent.name):
                data = load_manifest(overlay)
                self.assertEqual(data.get("overlay_version"), 1)
                self.assertEqual(data.get("harness"), overlay.parent.name)
                for key in ("description", "standards_gap"):
                    self.assertIsInstance(data.get(key), str)
                    self.assertTrue(data[key].strip(), f"{key} must be non-empty")
                self.assertIsInstance(data.get("artifacts"), list)
                self.assertTrue(data["artifacts"], "artifacts must be non-empty")

    def test_artifact_shape(self):
        for overlay in overlay_dirs():
            data = load_manifest(overlay)
            seen_ids = set()
            for artifact in data["artifacts"]:
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    artifact_id = artifact.get("id")
                    self.assertIsInstance(artifact_id, str)
                    self.assertTrue(artifact_id.strip())
                    self.assertNotIn(artifact_id, seen_ids, "artifact ids must be unique")
                    seen_ids.add(artifact_id)

                    self.assertIn(artifact.get("source_root"), ALLOWED_SOURCE_ROOTS)
                    self.assertIsInstance(artifact.get("source"), str)

                    install = artifact.get("install")
                    self.assertIsInstance(install, dict)
                    self.assertIn(install.get("method"), ALLOWED_INSTALL_METHODS)
                    self.assertIsInstance(install.get("target"), str)
                    self.assertTrue(install["target"].strip())
                    self.assertIn(install.get("scope"), ALLOWED_SCOPES)
                    if install["method"] == "generate":
                        self.assertIsInstance(install.get("generator"), str)
                        self.assertTrue(install["generator"].strip())

                    reverse = artifact.get("reverse")
                    self.assertIsInstance(reverse, dict)
                    self.assertIn(reverse.get("method"), ALLOWED_REVERSE_METHODS)

    def test_shipped_in_repo_reverses_as_none_and_only_shipped_in_repo_does(self):
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    shipped = artifact["install"]["method"] == "shipped-in-repo"
                    reverse_none = artifact["reverse"]["method"] == "none"
                    self.assertEqual(shipped, reverse_none)

    def test_artifact_sources_exist(self):
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    base = overlay if artifact["source_root"] == "overlay" else ROOT
                    source = base / artifact["source"]
                    self.assertTrue(source.is_file(), f"referenced source missing: {source}")

    def test_shipped_in_repo_targets_match_their_repo_sources(self):
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                if artifact["install"]["method"] != "shipped-in-repo":
                    continue
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    self.assertEqual(artifact["source_root"], "repo")
                    self.assertEqual(artifact["install"]["target"], artifact["source"])
                    self.assertTrue((ROOT / artifact["install"]["target"]).is_file())

    def test_targets_are_placeholder_portable(self):
        # Non-shipped targets land outside the repo tree at install time, so
        # they must be anchored by a portable placeholder, never an adopter path.
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                if artifact["install"]["method"] == "shipped-in-repo":
                    continue
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    target = artifact["install"]["target"]
                    self.assertTrue(
                        target.startswith("<vault>/") or target.startswith("~/"),
                        f"target must start with <vault>/ or ~/ : {target}",
                    )

    def test_overlay_files_contain_no_adopter_specific_home_path(self):
        for overlay in overlay_dirs():
            for path in sorted(p for p in overlay.rglob("*") if p.is_file()):
                text = path.read_text(encoding="utf-8")
                for pattern in PATH_LEAK_PATTERNS:
                    with self.subTest(path=str(path.relative_to(ROOT)), pattern=pattern.pattern):
                        self.assertIsNone(pattern.search(text))

    def test_overlay_shipping_harnesses_document_the_overlay_in_wiring(self):
        # Structural check: the wiring doc references the overlay path.
        for overlay in overlay_dirs():
            wiring = overlay.parent / "wiring.md"
            with self.subTest(overlay=overlay.parent.name):
                self.assertTrue(wiring.is_file())
                self.assertIn("overlay/manifest.json", wiring.read_text(encoding="utf-8"))

    def test_onboard_harness_and_harness_readme_reference_overlays(self):
        # Structural path references only — no prose sentences pinned.
        skill = (ROOT / "10_Agents/skills/onboard-harness/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("overlay/manifest.json", skill)
        readme = (HARNESS_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("overlay/", readme)
        self.assertIn("manifest.json", readme)


if __name__ == "__main__":
    unittest.main()
