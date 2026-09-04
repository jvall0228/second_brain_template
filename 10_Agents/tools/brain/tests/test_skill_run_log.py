"""The Claude Code skill-run log hook appends one line per Skill call."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HOOK = ROOT / "10_Agents/harnesses/claude-code/skill-run-log.sh"


class SkillRunLogTests(unittest.TestCase):
    def run_hook(self, root: Path, payload) -> int:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
        proc = subprocess.run(
            ["sh", str(HOOK)],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )
        return proc.returncode

    def test_appends_skill_lines_and_never_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            log = root / "10_Agents/docs/skill-runs.log"
            log.parent.mkdir(parents=True)
            log.write_text("# header\n", encoding="utf-8")
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "daily-log"}, "tool_response": "ok"}), 0)
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "curate"}, "tool_response": {"is_error": True}}), 0)
            self.assertEqual(self.run_hook(root, {"tool_name": "Bash", "tool_input": {"command": "ls"}}), 0)
            self.assertEqual(self.run_hook(root, "not json"), 0)
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "bad name"}}), 0)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "# header")
            rows = [line.split("\t") for line in lines[1:]]
            self.assertEqual([(r[1], r[2], r[3]) for r in rows], [("claude-code", "daily-log", "ok"), ("claude-code", "curate", "error")])
            self.assertRegex(rows[0][0], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_log_is_never_followed(self):
        # F5: the log replaced by a symlink to a file outside the vault — the
        # external file must not gain a line, and the symlink stays as it was.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "vault"
            outside = Path(td) / "outside.log"
            outside.write_text("external\n", encoding="utf-8")
            log = root / "10_Agents/docs/skill-runs.log"
            log.parent.mkdir(parents=True)
            os.symlink(outside, log)
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "daily-log"}}), 0)
            self.assertEqual(outside.read_text(encoding="utf-8"), "external\n")
            self.assertTrue(log.is_symlink())
            self.assertEqual(os.readlink(log), str(outside))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_parent_component_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "vault"
            elsewhere = Path(td) / "elsewhere"
            elsewhere.mkdir()
            external = elsewhere / "skill-runs.log"
            external.write_text("# external\n", encoding="utf-8")
            (root / "10_Agents").mkdir(parents=True)
            os.symlink(elsewhere, root / "10_Agents/docs")
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "daily-log"}}), 0)
            self.assertEqual(external.read_text(encoding="utf-8"), "# external\n")
            # A symlinked vault root component above the vault is fine (the
            # root is trusted and resolved), only components below it are not.
            real = Path(td) / "real-vault"
            (real / "10_Agents/docs").mkdir(parents=True)
            (real / "10_Agents/docs/skill-runs.log").write_text("", encoding="utf-8")
            alias = Path(td) / "alias-root"
            os.symlink(real, alias)
            self.assertEqual(self.run_hook(alias, {"tool_name": "Skill", "tool_input": {"skill": "curate"}}), 0)
            self.assertIn("\tcurate\t", (real / "10_Agents/docs/skill-runs.log").read_text(encoding="utf-8"))

    def test_missing_log_is_not_created_and_directory_target_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "10_Agents/docs").mkdir(parents=True)
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "daily-log"}}), 0)
            self.assertFalse((root / "10_Agents/docs/skill-runs.log").exists())
            (root / "10_Agents/docs/skill-runs.log").mkdir()
            self.assertEqual(self.run_hook(root, {"tool_name": "Skill", "tool_input": {"skill": "daily-log"}}), 0)
            self.assertTrue((root / "10_Agents/docs/skill-runs.log").is_dir())

    def test_settings_wire_the_hook(self):
        data = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        post = data["hooks"]["PostToolUse"]
        self.assertEqual(post[0]["matcher"], "Skill")
        self.assertIn("skill-run-log.sh", post[0]["hooks"][0]["command"])
        self.assertTrue(os.access(HOOK, os.X_OK))


if __name__ == "__main__":
    unittest.main()
