"""Contract tests for the recommended-component registry.

Mechanical structure checks only (no prose pinned): the component manifest
parses and every component has a valid shape; community items require
owner-per-item sign-off; community submodule components TRACK an upstream
branch (they install the latest, not a frozen SHA) and .gitmodules configures
that branch-tracking; every in-repo source path and submodule path exists;
every catalog anchor resolves; vault-config presets are valid bounded-YAML that
set only known config keys; and the onboarder docs reference the components home.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
COMPONENTS_DIR = ROOT / "10_Agents/components"
MANIFEST = COMPONENTS_DIR / "manifest.json"
GITMODULES = ROOT / ".gitmodules"
CATALOG = ROOT / "06_Resources/recommended-skills.md"
ONBOARD_HARNESS = ROOT / "10_Agents/skills/onboard-harness/SKILL.md"
ONBOARD_OWNER = ROOT / "10_Agents/skills/onboard-owner/SKILL.md"
COMPONENTS_README = COMPONENTS_DIR / "README.md"
AGENTS_README = ROOT / "10_Agents/README.md"

KINDS = {"skill", "memory-block", "overlay", "vault-config-preset"}
PROVENANCE = {"first-party", "community"}
SIGNOFF = {"default-ok", "owner-per-item"}
SOURCE_TYPES = {"submodule", "remote", "repo"}
INSTALL_METHODS = {"copy", "marker-block", "generate", "shipped-in-repo", "merge-config"}
SCOPES = {"user", "vault", "project"}
REVERSE_METHODS = {"delete", "remove-marker-block", "restore-config", "none"}

HEX40 = re.compile(r"^[0-9a-f]{40}$")
PATH_LEAK_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_manifest() -> dict:
    return json.loads(read(MANIFEST))


def components() -> list[dict]:
    return load_manifest()["components"]


def heading_slugs(text: str) -> set[str]:
    """GitHub-style anchor slugs for every ATX heading in a markdown note."""
    slugs = set()
    for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE):
        title = m.group(1).strip()
        slug = re.sub(r"[^\w\s-]", "", title).strip().lower()
        slug = re.sub(r"\s+", "-", slug)
        slugs.add(slug)
    return slugs


def gitmodules_branches() -> dict[str, bool]:
    """Map each submodule `path` to whether its stanza sets `branch = ...`."""
    result: dict[str, bool] = {}
    path: str | None = None
    has_branch = False
    for raw in read(GITMODULES).splitlines():
        line = raw.strip()
        if line.startswith("[submodule"):
            if path is not None:
                result[path] = has_branch
            path, has_branch = None, False
        elif line.startswith("path"):
            path = line.split("=", 1)[1].strip()
        elif line.startswith("branch"):
            has_branch = True
    if path is not None:
        result[path] = has_branch
    return result


class ManifestShapeTests(unittest.TestCase):
    def test_manifest_parses_with_version(self):
        data = load_manifest()
        self.assertEqual(data.get("manifest_version"), 1)
        self.assertIsInstance(data.get("components"), list)
        self.assertTrue(data["components"], "components must be non-empty")

    def test_ids_unique(self):
        ids = [c.get("id") for c in components()]
        self.assertTrue(all(isinstance(i, str) and i.strip() for i in ids))
        self.assertEqual(len(ids), len(set(ids)), "component ids must be unique")

    def test_every_component_has_valid_core_fields(self):
        for c in components():
            with self.subTest(component=c.get("id")):
                self.assertIn(c.get("kind"), KINDS)
                self.assertIn(c.get("provenance"), PROVENANCE)
                self.assertIn(c.get("signoff"), SIGNOFF)
                for field in ("description", "license"):
                    self.assertIsInstance(c.get(field), str)
                    self.assertTrue(c[field].strip(), f"{field} must be non-empty")

    def test_source_shape(self):
        for c in components():
            with self.subTest(component=c.get("id")):
                source = c.get("source")
                self.assertIsInstance(source, dict)
                stype = source.get("type")
                self.assertIn(stype, SOURCE_TYPES)
                if stype == "submodule":
                    for key in ("path", "repo", "content"):
                        self.assertIsInstance(source.get(key), str)
                        self.assertTrue(source[key].strip())
                elif stype == "remote":
                    for key in ("repo", "content"):
                        self.assertIsInstance(source.get(key), str)
                        self.assertTrue(source[key].strip())
                elif stype == "repo":
                    self.assertIsInstance(source.get("path"), str)
                    self.assertTrue(source["path"].strip())

    def test_install_shape(self):
        for c in components():
            with self.subTest(component=c.get("id")):
                install = c.get("install")
                self.assertIsInstance(install, dict)
                self.assertIn(install.get("method"), INSTALL_METHODS)
                self.assertIn(install.get("scope"), SCOPES)
                target = install.get("target")
                self.assertIsInstance(target, str)
                self.assertTrue(target.strip())
                # Portable target: no adopter home-path leak, no bare absolute.
                self.assertFalse(target.startswith("/"), f"absolute target: {target}")
                for pat in PATH_LEAK_PATTERNS:
                    self.assertIsNone(pat.search(target), f"path leak in target: {target}")

    def test_reverse_shape(self):
        for c in components():
            with self.subTest(component=c.get("id")):
                reverse = c.get("reverse")
                self.assertIsInstance(reverse, dict)
                self.assertIn(reverse.get("method"), REVERSE_METHODS)


class SignoffPolicyTests(unittest.TestCase):
    def test_community_components_require_owner_per_item(self):
        for c in components():
            if c.get("provenance") == "community":
                with self.subTest(component=c.get("id")):
                    self.assertEqual(c.get("signoff"), "owner-per-item")

    def test_at_least_one_default_ok_first_party(self):
        # first-party MAY be default-ok; assert the model actually exercises it.
        self.assertTrue(
            any(
                c.get("provenance") == "first-party" and c.get("signoff") == "default-ok"
                for c in components()
            )
        )


class BranchTrackingTests(unittest.TestCase):
    """Community submodule components track a branch (install latest), and
    .gitmodules configures that branch-tracking — no frozen SHA."""

    def submodule_components(self) -> list[dict]:
        return [c for c in components() if c.get("source", {}).get("type") == "submodule"]

    def test_submodule_components_exist(self):
        self.assertTrue(self.submodule_components(), "expected submodule-source components")

    def test_submodule_components_declare_track_branch_not_sha(self):
        for c in self.submodule_components():
            with self.subTest(component=c.get("id")):
                source = c["source"]
                track = source.get("track")
                self.assertIsInstance(track, str, "submodule source must declare `track`")
                self.assertTrue(track.strip())
                self.assertIsNone(
                    HEX40.match(track),
                    f"`track` must be a branch, not a 40-hex SHA: {track!r}",
                )
                self.assertNotIn("sha", source, "tracking components must not carry a frozen `sha`")

    def test_gitmodules_configures_branch_tracking(self):
        branches = gitmodules_branches()
        for c in self.submodule_components():
            path = c["source"]["path"]
            with self.subTest(component=c.get("id"), path=path):
                self.assertIn(path, branches, f".gitmodules has no stanza for {path}")
                self.assertTrue(
                    branches[path],
                    f".gitmodules stanza for {path} must set `branch = ...` (tracking)",
                )


class SourcePathTests(unittest.TestCase):
    def test_repo_source_paths_exist(self):
        for c in components():
            source = c["source"]
            if source["type"] == "repo":
                with self.subTest(component=c.get("id")):
                    self.assertTrue((ROOT / source["path"]).exists(), source["path"])

    def test_submodule_paths_exist(self):
        # The .extern/<name> gitlink dir exists even uninitialized; the content
        # inside it is materialized opt-in and is NOT asserted here.
        for c in components():
            source = c["source"]
            if source["type"] == "submodule":
                with self.subTest(component=c.get("id")):
                    self.assertTrue((ROOT / source["path"]).exists(), source["path"])


class CatalogAnchorTests(unittest.TestCase):
    def test_catalog_anchors_resolve(self):
        catalog_slugs = heading_slugs(read(CATALOG))
        for c in components():
            anchor = c.get("catalog")
            if anchor is None:
                continue
            with self.subTest(component=c.get("id"), anchor=anchor):
                file_part, _, fragment = anchor.partition("#")
                self.assertEqual(file_part, "06_Resources/recommended-skills.md")
                self.assertTrue(fragment, "catalog anchor needs a #fragment")
                self.assertIn(fragment, catalog_slugs, f"unresolved catalog anchor: {anchor}")

    def test_community_components_carry_a_catalog_anchor(self):
        for c in components():
            if c.get("provenance") == "community":
                with self.subTest(component=c.get("id")):
                    self.assertIsInstance(c.get("catalog"), str)


class PresetTests(unittest.TestCase):
    KNOWN_KEYS = brain.CONFIG_IMPLEMENTED_KEYS | brain.CONFIG_RESERVED_KEYS

    def test_vault_config_presets_parse_clean_and_use_known_keys(self):
        found = False
        for c in components():
            if c.get("kind") != "vault-config-preset":
                continue
            found = True
            path = c["source"]["path"]
            with self.subTest(component=c.get("id"), preset=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                config, findings = brain.parse_config(text)
                self.assertEqual(findings, [], f"preset {path} has parse findings: {findings}")
                for key in config:
                    self.assertIn(
                        key, self.KNOWN_KEYS, f"preset {path} sets unknown config key {key!r}"
                    )
        self.assertTrue(found, "expected at least one vault-config-preset component")


class DocReferenceTests(unittest.TestCase):
    def test_onboarder_and_readme_reference_components_home(self):
        # The onboarder skills and the agent-library README point at the
        # components home. (The components README itself refers to its own
        # siblings by bare name, so it is not checked for a self-path.)
        for path in (ONBOARD_HARNESS, ONBOARD_OWNER, AGENTS_README):
            with self.subTest(doc=str(path.relative_to(ROOT))):
                self.assertIn("10_Agents/components", read(path))

    def test_manifest_named_as_source_of_truth(self):
        for path in (ONBOARD_HARNESS, AGENTS_README):
            with self.subTest(doc=str(path.relative_to(ROOT))):
                self.assertIn("10_Agents/components/manifest.json", read(path))

    def test_components_readme_exists_with_frontmatter(self):
        self.assertTrue(COMPONENTS_README.is_file())
        text = read(COMPONENTS_README)
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---", 2)[1]
        for key in ("title:", "tags:", "updated:"):
            self.assertIn(key, frontmatter)


if __name__ == "__main__":
    unittest.main()
