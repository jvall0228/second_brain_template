"""Contract tests for user-level second-brain harness registration.

These tests intentionally exercise tracked specifications rather than a machine-specific
installer. The template must remain portable while onboard-harness owns all runtime paths.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SHARED = "~/.agents/second-brain/AGENTS.md"
ONBOARD = ROOT / "10_Agents/skills/onboard-harness/SKILL.md"
HARNESS_DIR = ROOT / "10_Agents/harnesses"
HARNESS_WIRING = {
    "claude-code": HARNESS_DIR / "claude-code/wiring.md",
    "codex": HARNESS_DIR / "codex/wiring.md",
    "opencode": HARNESS_DIR / "opencode/wiring.md",
    "pi": HARNESS_DIR / "pi/wiring.md",
    "cursor": HARNESS_DIR / "cursor/wiring.md",
    "copilot": HARNESS_DIR / "copilot/wiring.md",
    "muse-code": HARNESS_DIR / "muse-code/wiring.md",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SharedRegistrationContractTests(unittest.TestCase):
    def test_onboard_harness_defines_shared_registration_and_portability(self):
        text = read(ONBOARD)
        self.assertIn(SHARED, text)
        self.assertIn("Template portability invariant", text)
        self.assertIn("<resolved-vault-path>", text)
        self.assertIn("A fully-installed state is a no-op", text)
        self.assertIn("registration_id", text)

    def test_registry_is_explicitly_multi_vault_safe(self):
        text = read(ONBOARD)
        self.assertIn("multiple adopted vaults", text)
        self.assertIn("preserve all other registered vault entries", text)
        self.assertIn("do not derive the ID from the filesystem path", text)
        self.assertIn("replaces only the entry matching `registration_id`", text)
        self.assertIn("onboarding another vault does **not** add another harness-level block", text)
        self.assertIn("Never delete another vault's entry", text)

    def test_global_skills_have_shared_provider_consumer_ownership(self):
        text = read(ONBOARD)
        self.assertIn("shared-managed, not foreign", text)
        self.assertIn("provider/consumer ownership", text)
        self.assertIn("managed version drift", text)
        self.assertIn("Shared harness adapters and global skills are reference-counted", text)
        self.assertIn("only when its recorded content hash matches", text)
        self.assertIn("Never leave a broken symlink", text)

    def test_copilot_does_not_register_duplicate_vault_skill_sets(self):
        text = read(HARNESS_WIRING["copilot"])
        self.assertIn("become consumers rather than adding duplicate directories", text)
        self.assertIn("one manifest-owned global provider at a time", text)
        self.assertIn("Additional vaults are consumers, not duplicate registrations", text)

    def test_every_supported_harness_accounts_for_shared_registration(self):
        for name, path in HARNESS_WIRING.items():
            with self.subTest(harness=name):
                self.assertIn(SHARED, read(path))

    def test_claude_uses_native_include_of_stable_registration(self):
        text = read(HARNESS_WIRING["claude-code"])
        self.assertIn("@~/.agents/second-brain/AGENTS.md", text)
        self.assertNotIn("@/path/to/vault/AGENTS.md", text)
        self.assertNotIn("@/absolute/path/to/vault/AGENTS.md", text)

    def test_non_claude_adapters_do_not_assume_claude_include_semantics(self):
        # These adapters either explicitly lack @ imports, use a documented user-rules
        # surface, or deliberately defer persistent injection. Keep the baseline safe.
        for name in ("codex", "opencode", "pi", "cursor", "copilot", "muse-code"):
            with self.subTest(harness=name):
                self.assertNotIn("@~/.agents/second-brain/AGENTS.md", read(HARNESS_WIRING[name]))

    def test_harness_adapters_do_not_embed_legacy_direct_vault_import(self):
        forbidden = (
            "@/path/to/vault/AGENTS.md",
            "@/absolute/path/to/vault/AGENTS.md",
            "read `<vault>/AGENTS.md` first",
        )
        for name, path in HARNESS_WIRING.items():
            text = read(path)
            for pattern in forbidden:
                with self.subTest(harness=name, pattern=pattern):
                    self.assertNotIn(pattern, text)

    def test_changed_specs_contain_no_adopter_specific_home_path(self):
        paths = [ONBOARD, *HARNESS_WIRING.values()]
        patterns = (
            re.compile(r"/Users/[A-Za-z0-9._-]+/"),
            re.compile(r"/home/[A-Za-z0-9._-]+/"),
            re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
        )
        for path in paths:
            text = read(path)
            for pattern in patterns:
                with self.subTest(path=path.relative_to(ROOT), pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text))

    def test_shared_registration_is_not_claimed_as_auto_discovered_standard(self):
        onboard = read(ONBOARD)
        self.assertIn(
            "never depend on undocumented automatic discovery of `~/.agents/second-brain/AGENTS.md`",
            onboard,
        )
        for name in ("opencode", "cursor", "muse-code"):
            text = read(HARNESS_WIRING[name])
            with self.subTest(harness=name):
                self.assertIn(SHARED, text)
                self.assertIn("automat", text.lower())


if __name__ == "__main__":
    unittest.main()
