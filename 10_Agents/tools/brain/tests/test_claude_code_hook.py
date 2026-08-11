"""Contract tests for the Claude Code edit-time validation hook (issue #11).

Claude Code's PostToolUse contract feeds hook output back to the agent only on
exit 2 with findings on STDERR. `brain validate` exits 0 clean / 1 errors /
2 warnings-only (spec.md section 10.4). The shim
`10_Agents/harnesses/claude-code/validate-hook.sh` translates between the two:

    brain 0 (clean)         -> 0
    brain 2 (warnings only) -> 0
    brain 1 (errors)        -> 2, findings on STDERR

These tests pin (a) the reference settings JSON no longer swallows validation
with `|| true` and calls the shim instead, and (b) the shim's three exit-code
paths, exercised via subprocess against temp vaults (skipped when no POSIX sh
is available).

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HARNESS = ROOT / "10_Agents/harnesses/claude-code"
SETTINGS = HARNESS / "settings-example.json"
SHIM = HARNESS / "validate-hook.sh"
SH = shutil.which("sh")


class SettingsExampleContractTests(unittest.TestCase):
    def test_settings_example_is_valid_json(self):
        json.loads(SETTINGS.read_text(encoding="utf-8"))

    def test_settings_example_does_not_swallow_validation(self):
        self.assertNotIn("|| true", SETTINGS.read_text(encoding="utf-8"))

    def test_post_tool_use_hook_calls_the_shim(self):
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entry in data["hooks"]["PostToolUse"]
            for hook in entry["hooks"]
        ]
        self.assertTrue(
            any("validate-hook.sh" in cmd for cmd in commands),
            f"no PostToolUse command references validate-hook.sh: {commands}",
        )

    def test_shim_exists_next_to_settings_example(self):
        self.assertTrue(SHIM.is_file())

    def test_session_start_arms_hooks_and_merge_driver(self):
        # The repo's own Claude Code settings must install everything the
        # docs promise per-clone setup does: hooksPath AND the merge driver.
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entry in settings["hooks"]["SessionStart"]
            for hook in entry["hooks"]
        ]
        joined = " ; ".join(commands)
        self.assertIn("core.hooksPath .githooks", joined)
        self.assertIn("merge.regenerate.driver true", joined)


def write_note(root: Path, relpath: str, body: str) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


CONVENTIONS = """---
title: "Conventions"
tags:
  - type/meta
updated: 2026-08-11
expires: 2027-01-01
---

# Conventions

## Tag Namespaces

| Namespace | Purpose | Values |
|-----------|---------|--------|
| `type/*` | Kind of content | `meta`, `reference` |
"""


def make_vault(tmp: Path, note_body: str) -> Path:
    """Minimal vault; validity is controlled by note_body."""
    vault = tmp / "vault"
    write_note(vault, "00_Meta/conventions.md", CONVENTIONS)
    write_note(vault, "06_Resources/note.md", note_body)
    return vault


CLEAN_NOTE = """---
title: "Note"
tags:
  - type/reference
updated: 2026-08-11
expires: 2027-01-01
---

# Note

Body.
"""

# Duplicate frontmatter key -> warning (exit 2), no errors.
WARNING_NOTE = """---
title: "Note"
title: "Note again"
tags:
  - type/reference
updated: 2026-08-11
expires: 2027-01-01
---

# Note

Body.
"""

# No frontmatter at all -> error (exit 1).
ERROR_NOTE = "# Note\n\nNo frontmatter here.\n"


@unittest.skipIf(SH is None, "no POSIX sh available")
class ShimExitCodeTests(unittest.TestCase):
    def run_shim(self, vault: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [SH, str(SHIM), "--vault", str(vault)],
            capture_output=True,
            text=True,
            cwd=str(vault),  # any cwd; shim must locate brain.py itself
            timeout=120,
        )

    def brain_status(self, vault: Path) -> int:
        """Sanity-check the fixture produces the intended brain exit code."""
        import sys

        return subprocess.run(
            [sys.executable, str(ROOT / "10_Agents/tools/brain/brain.py"),
             "validate", "--vault", str(vault)],
            capture_output=True,
            timeout=120,
        ).returncode

    def test_clean_vault_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = make_vault(Path(tmp), CLEAN_NOTE)
            self.assertEqual(self.brain_status(vault), 0)
            proc = self.run_shim(vault)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_warnings_only_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = make_vault(Path(tmp), WARNING_NOTE)
            self.assertEqual(self.brain_status(vault), 2)
            proc = self.run_shim(vault)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_errors_exit_two_with_findings_on_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = make_vault(Path(tmp), ERROR_NOTE)
            self.assertEqual(self.brain_status(vault), 1)
            proc = self.run_shim(vault)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("note.md", proc.stderr)


if __name__ == "__main__":
    unittest.main()
