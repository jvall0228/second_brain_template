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

# Managed-block markers for the Cursor read-restriction template. The manifest's
# generator_semantics and the template itself must agree on these exact lines.
MARKER_BEGIN = "# BEGIN second-brain restricted/private (generated)"
MARKER_END = "# END second-brain restricted/private (generated)"

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


class OwnerOptInTests(unittest.TestCase):
    """Default overlay installation must omit the managed privacy exclusion.

    restricted/private is publication classification, not agent access control
    (CONVENTIONS §restricted/private). Harness-level read restriction is an
    owner-selected opt-in: the artifact that generates the managed
    .cursorignore block carries install.owner_opt_in true, and every artifact
    without that flag is part of the default install and must not create it.
    """

    def test_owner_opt_in_is_boolean_when_present(self):
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                install = artifact["install"]
                if "owner_opt_in" in install:
                    with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                        self.assertIsInstance(install["owner_opt_in"], bool)

    def test_privacy_generation_artifacts_are_owner_opt_in(self):
        # Covers AE10: any artifact that derives exclusions from the
        # restricted tag family installs only on explicit owner selection —
        # regardless of install method, and matching the whole `restricted`
        # namespace so `restricted/*` variants cannot slip past the guard.
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                install = artifact["install"]
                sources = " ".join(
                    str(install.get(key, ""))
                    for key in ("generator", "source", "template")
                )
                if "restricted" not in sources:
                    continue
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    self.assertIs(install.get("owner_opt_in"), True)

    def test_default_install_artifacts_never_target_ignore_files(self):
        # Covers AE10 from the target side: the default artifact set (no
        # owner_opt_in flag) contains nothing that creates or refreshes a
        # harness read-restriction/ignore file (.cursorignore,
        # .cursorindexingignore, or any dot-ignore sibling).
        for overlay in overlay_dirs():
            for artifact in load_manifest(overlay)["artifacts"]:
                install = artifact["install"]
                if install.get("owner_opt_in") is True:
                    continue
                basename = install["target"].rsplit("/", 1)[-1]
                with self.subTest(overlay=overlay.parent.name, artifact=artifact.get("id")):
                    self.assertFalse(
                        basename.startswith(".") and basename.endswith("ignore"),
                        f"default-install artifact targets ignore file {basename}",
                    )

    def test_opt_in_semantics_are_documented_where_installs_run(self):
        # Structural token references only — no prose sentences pinned.
        skill = (ROOT / "10_Agents/skills/onboard-harness/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("owner_opt_in", skill)
        readme = (HARNESS_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("owner_opt_in", readme)


def rewrite_managed_block(text: str, paths):
    """The documented owner-selected sync: rewrite the managed block wholesale.

    Mirrors the recipe in cursor/wiring.md (Restricted content) and the
    manifest's generator_semantics — one line per restricted path between the
    markers, owner lines outside the markers untouched.
    """
    lines = text.splitlines()
    begin = lines.index(MARKER_BEGIN)
    end = lines.index(MARKER_END)
    rebuilt = lines[: begin + 1] + list(paths) + lines[end:]
    return "\n".join(rebuilt) + "\n"


class CursorignoreManagedBlockTests(unittest.TestCase):
    """Template/recipe mechanics for the opt-in read-restriction file."""

    TEMPLATE = HARNESS_DIR / "cursor/overlay/cursorignore-template.txt"

    def template_text(self):
        return self.TEMPLATE.read_text(encoding="utf-8")

    def test_template_ships_exactly_one_empty_managed_block(self):
        lines = self.template_text().splitlines()
        self.assertEqual(lines.count(MARKER_BEGIN), 1)
        self.assertEqual(lines.count(MARKER_END), 1)
        begin, end = lines.index(MARKER_BEGIN), lines.index(MARKER_END)
        self.assertEqual(end, begin + 1, "shipped managed block must be empty")

    def test_manifest_generator_semantics_name_the_template_markers(self):
        manifest = load_manifest(HARNESS_DIR / "cursor/overlay")
        artifacts = {a["id"]: a for a in manifest["artifacts"]}
        semantics = artifacts["cursorignore-privacy"]["install"]["generator_semantics"]
        self.assertIn(MARKER_BEGIN, semantics)

    def test_opt_in_sync_touches_only_the_managed_block(self):
        seeded = self.template_text() + "owner-extra-exclusion/\n"
        synced = rewrite_managed_block(seeded, ["03_Journal/private-note.md"])
        self.assertIn("owner-extra-exclusion/", synced)
        self.assertIn("03_Journal/private-note.md", synced)
        before_block = seeded.split(MARKER_BEGIN)[0]
        self.assertEqual(synced.split(MARKER_BEGIN)[0], before_block)

    def test_sync_is_idempotent_and_handles_gained_and_lost_tags(self):
        seeded = self.template_text() + "owner-extra-exclusion/\n"
        both = rewrite_managed_block(seeded, ["a.md", "b.md"])
        self.assertEqual(rewrite_managed_block(both, ["a.md", "b.md"]), both)
        dropped = rewrite_managed_block(both, ["a.md"])
        self.assertIn("a.md", dropped)
        self.assertNotIn("b.md", dropped)
        emptied = rewrite_managed_block(dropped, [])
        self.assertEqual(emptied, rewrite_managed_block(seeded, []))
        self.assertIn("owner-extra-exclusion/", emptied)


class ComponentRegistrationTests(unittest.TestCase):
    """The shipped overlays stay registered in the component registry."""

    def test_component_registry_still_registers_shipped_overlays(self):
        registry = json.loads(
            (ROOT / "10_Agents/components/manifest.json").read_text(encoding="utf-8")
        )
        overlays = {c["id"]: c for c in registry["components"] if c["kind"] == "overlay"}
        for harness in sorted(EXPECTED_OVERLAYS):
            with self.subTest(harness=harness):
                component = overlays[f"{harness}-overlay"]
                expected = f"10_Agents/harnesses/{harness}/overlay/manifest.json"
                self.assertEqual(component["source"]["path"], expected)
                self.assertEqual(component["install"]["method"], "shipped-in-repo")
                self.assertTrue((ROOT / expected).is_file())


if __name__ == "__main__":
    unittest.main()
