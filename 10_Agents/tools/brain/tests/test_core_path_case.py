"""Exact-case contract for the 14 uppercase framework notes (issue #75)."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path, PurePosixPath


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402


ROOT = Path(__file__).resolve().parents[4]


EXPECTED_CORE_PATHS = {
    "00_Meta/CHANGELOG.md",
    "00_Meta/CONVENTIONS.md",
    "00_Meta/INDEX.md",
    "00_Meta/PRD.md",
    "00_Meta/STATUS.md",
    "01_Profile/DEFAULTS.md",
    "01_Profile/IDENTITY.md",
    "01_Profile/LONG-RUNNING-THEMES.md",
    "01_Profile/NOW.md",
    "01_Profile/PREFERENCES.md",
    "01_Profile/TOOLING-STACK.md",
    "01_Profile/WORK.md",
    "10_Agents/docs/OPERATING-RULES.md",
    "10_Agents/docs/TASK-PATTERNS.md",
}


def legacy_case(path: str) -> str:
    parsed = PurePosixPath(path)
    return str(parsed.with_name(parsed.name.lower()))


class CorePathCaseTests(unittest.TestCase):
    def test_manifest_is_exact_and_filename_exception_is_path_scoped(self):
        self.assertEqual(set(brain.CORE_FRAMEWORK_PATHS.values()), EXPECTED_CORE_PATHS)
        self.assertEqual(len(brain.CORE_FRAMEWORK_PATHS), 14)
        for path in EXPECTED_CORE_PATHS:
            with self.subTest(path=path):
                self.assertTrue(brain.valid_note_filename(path))
                self.assertFalse(brain.valid_note_filename(legacy_case(path)))
        self.assertFalse(brain.valid_note_filename("06_Resources/NOW.md"))
        self.assertTrue(brain.valid_note_filename("06_Resources/ordinary-note.md"))

    def test_git_tree_uses_only_exact_manifest_case(self):
        tracked = set(
            subprocess.run(
                ["git", "ls-files"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )
        for path in EXPECTED_CORE_PATHS:
            with self.subTest(path=path):
                case_matches = sorted(item for item in tracked if item.casefold() == path.casefold())
                self.assertEqual(case_matches, [path])

    def test_tracked_text_has_no_stale_legacy_full_path(self):
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        stale_tokens = {
            token
            for path in EXPECTED_CORE_PATHS
            for token in (legacy_case(path), legacy_case(path).removesuffix(".md"))
        }
        findings = []
        for rel in tracked:
            try:
                text = (ROOT / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for token in stale_tokens:
                if token in text:
                    findings.append(f"{rel}: {token}")
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
