"""Tests for the vault config (spec.md §15, issue #2).

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

from test_brain import FIXTURE, make_vault, note  # noqa: E402


def vault(td: Path, files: dict) -> Path:
    return make_vault(
        td, {"00_Meta/conventions.md": (FIXTURE / "00_Meta/conventions.md").read_text(), **files}
    )


class ParseConfigTests(unittest.TestCase):
    def test_valid_subset(self):
        config, findings = brain.parse_config(
            "# comment\n"
            "extension_trust: relaxed\n"
            "write_exceptions:\n"
            "  - 06_Resources/\n"
            "  - '04_Projects/'\n"
            "flow: [a, \"b, c\"]\n"
            "report:\n"
            "  stale_days: 90\n"
            "  channels: [email, push]\n"
        )
        self.assertEqual(findings, [])
        self.assertEqual(config["extension_trust"], "relaxed")
        self.assertEqual(config["write_exceptions"], ["06_Resources/", "04_Projects/"])
        self.assertEqual(config["flow"], ["a", "b, c"])
        # One nested mapping level; values stay strings (no coercion, §4.3).
        self.assertEqual(config["report"], {"stale_days": "90", "channels": ["email", "push"]})

    def test_empty_and_all_comment_files_parse_to_defaults(self):
        for text in ("", "\n\n", "# only\n# comments\n"):
            config, findings = brain.parse_config(text)
            self.assertEqual((config, findings), ({}, []))

    def test_nesting_depth_violation(self):
        config, findings = brain.parse_config(
            "sync:\n  remote:\n    url: x\n"
        )
        rules = [f["rule"] for f in findings]
        self.assertIn("config-nesting-too-deep", rules)
        # The first level still parsed; the too-deep line was skipped.
        self.assertEqual(config["sync"], {"remote": None})

    def test_malformed_lines_are_findings_not_crashes(self):
        config, findings = brain.parse_config(
            "key:no-space\n"
            "- stray item\n"
            "badflow: [a, b\n"
            "  orphan: x\n"
            "dup: 1\n"
            "dup: 2\n"
        )
        rules = sorted(f["rule"] for f in findings)
        self.assertEqual(
            rules,
            [
                "config-duplicate-key",
                "config-list-item-without-key",
                "config-unsupported",  # key:no-space
                "config-unsupported",  # unterminated flow list
                "config-unsupported",  # indented key with no open mapping
            ],
        )
        self.assertEqual(config["dup"], "2")
        self.assertTrue(all(isinstance(f["line"], int) for f in findings))

    def test_list_then_indented_key_rejected(self):
        _, findings = brain.parse_config("write_exceptions:\n  - a/\n  b: c\n")
        self.assertIn("config-unsupported", [f["rule"] for f in findings])


class LoadConfigTests(unittest.TestCase):
    def test_absent_file_is_pure_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            root = vault(Path(td), {})
            self.assertEqual(brain.load_config(root), ({}, []))
            self.assertEqual(
                brain.write_exception_prefixes({}), brain.AGENT_WRITE_DEFAULT_PREFIXES
            )
            self.assertEqual(brain.extension_trust({}), brain.DEFAULT_EXTENSION_TRUST)

    def test_not_utf8_config_is_finding_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = vault(Path(td), {"00_Meta/config.yaml": b"\xff\xfe bad"})
            config, findings = brain.load_config(root)
            self.assertEqual(config, {})
            self.assertEqual([f["rule"] for f in findings], ["config-not-utf8"])

    def test_shipped_repo_config_is_clean(self):
        root = brain.default_vault_root()
        config, findings = brain.load_config(root)
        self.assertEqual(findings, [])
        # A fork may legitimately set documented keys (e.g. onboard-owner
        # records `context:`) — require only that whatever is set is clean
        # and among the known keys.
        self.assertLessEqual(
            set(config), brain.CONFIG_IMPLEMENTED_KEYS | brain.CONFIG_RESERVED_KEYS
        )
        errors, warnings = brain.check_config(root, config, findings)
        self.assertEqual((errors, warnings), ([], []))


class WriteExceptionTests(unittest.TestCase):
    def test_defaults_enforce_inbox_first(self):
        for rel, ok in [
            ("02_Inbox/capture.md", True),
            ("02_Outbox/packet.md", True),
            ("10_Agents/solutions/fix.md", True),
            ("06_Resources/topic.md", False),
            ("00_Meta/conventions.md", False),
            ("02_Inboxes/sneaky.md", False),
        ]:
            self.assertEqual(brain.agent_write_allowed(rel, {}), ok, rel)

    def test_config_widens_never_narrows(self):
        config = {"write_exceptions": ["06_Resources", "./03_Journal/"]}
        prefixes = brain.write_exception_prefixes(config)
        for p in brain.AGENT_WRITE_DEFAULT_PREFIXES:
            self.assertIn(p, prefixes)
        self.assertIn("06_Resources/", prefixes)
        self.assertIn("03_Journal/", prefixes)
        self.assertTrue(brain.agent_write_allowed("06_Resources/new.md", config))
        self.assertTrue(brain.agent_write_allowed("06_Resources\\new.md", config))
        self.assertFalse(brain.agent_write_allowed("05_Areas/new.md", config))

    def test_traversal_in_checked_path_fails_closed(self):
        # The checked rel is untrusted input: a prefix match must not
        # authorize climbing back out of the allowed directory.
        for rel in [
            "02_Inbox/../01_Profile/secrets.md",
            "02_Inbox\\..\\x.md",
            "02_Inbox/./../00_Meta/config.yaml",
            "02_Inbox/../../outside.md",
            "/02_Inbox/abs.md",
            "C:/02_Inbox/win.md",
            "02_Inbox/./nested/../x.md",
        ]:
            self.assertFalse(brain.agent_write_allowed(rel, {}), rel)
        # Plain nested paths under an allowed prefix still pass.
        self.assertTrue(brain.agent_write_allowed("02_Inbox/sub/note.md", {}))

    def test_effectively_empty_entries_are_reported(self):
        # '.', './' grant nothing — enforcement drops them AND validate
        # reports them (they must not validate clean as silent no-ops).
        for entry in [".", "./", ".//"]:
            config = {"write_exceptions": [entry]}
            self.assertEqual(
                brain.write_exception_prefixes(config),
                brain.AGENT_WRITE_DEFAULT_PREFIXES,
                entry,
            )
            errors, _ = brain.check_config(Path("."), config, [])
            self.assertTrue(
                any(e["rule"] == "config-bad-write-exception" for e in errors), entry
            )

    def test_malformed_entries_ignored_by_enforcement(self):
        config = {"write_exceptions": ["/etc", "../up", "a/../b", "C:/x", ""]}
        self.assertEqual(
            brain.write_exception_prefixes(config), brain.AGENT_WRITE_DEFAULT_PREFIXES
        )

    def test_extension_trust_accessor(self):
        self.assertEqual(brain.extension_trust({"extension_trust": "relaxed"}), "relaxed")
        self.assertEqual(brain.extension_trust({"extension_trust": None}), "first-party")
        self.assertEqual(brain.extension_trust({"extension_trust": ["x"]}), "first-party")


class ValidateConfigTests(unittest.TestCase):
    def run_validate(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = vault(Path(td), files)
            return brain.run_validate(root, check_index=False)

    def findings_for_config(self, files):
        errors, warnings = self.run_validate(files)
        return (
            [f for f in errors if f["path"] == brain.CONFIG_RELPATH],
            [f for f in warnings if f["path"] == brain.CONFIG_RELPATH],
        )

    def test_absent_config_changes_nothing(self):
        errors, warnings = self.findings_for_config({"02_Inbox/capture.md": note()})
        self.assertEqual((errors, warnings), ([], []))

    def test_valid_config_is_clean(self):
        errors, warnings = self.findings_for_config(
            {
                "06_Resources/README.md": note(),
                "00_Meta/config.yaml": (
                    "write_exceptions:\n  - 06_Resources/\nextension_trust: first-party\n"
                ),
            }
        )
        self.assertEqual((errors, warnings), ([], []))

    def test_malformed_config_is_per_file_error_not_crash(self):
        errors, _ = self.findings_for_config(
            {"00_Meta/config.yaml": "key:no-space\nsync:\n  a:\n    b: 1\n"}
        )
        rules = {f["rule"] for f in errors}
        self.assertEqual(rules, {"config-unsupported", "config-nesting-too-deep"})

    def test_unknown_key_warns_reserved_keys_silent(self):
        errors, warnings = self.findings_for_config(
            {
                "00_Meta/config.yaml": (
                    "modules: [health]\n"
                    "sync: enabled\n"
                    "environments:\n  - work\n"
                    "report:\n  stale_days: 30\n"
                    "provenance: strict\n"
                    "template_version: 3\n"
                    "totally_novel: x\n"
                )
            }
        )
        self.assertEqual(errors, [])
        self.assertEqual([f["rule"] for f in warnings], ["config-unknown-key"])
        self.assertIn("totally_novel", warnings[0]["message"])

    def test_write_exception_shape_errors_and_missing_dir_warning(self):
        errors, warnings = self.findings_for_config(
            {
                "00_Meta/config.yaml": (
                    "write_exceptions:\n  - /abs/path\n  - ../outside\n  - 11_Missing/\n"
                )
            }
        )
        self.assertEqual(
            [f["rule"] for f in errors],
            ["config-bad-write-exception", "config-bad-write-exception"],
        )
        self.assertEqual([f["rule"] for f in warnings], ["config-missing-directory"])

    def test_invalid_value_shapes(self):
        errors, warnings = self.findings_for_config(
            {
                "00_Meta/config.yaml": (
                    "write_exceptions: not-a-list\n"
                    "extension_trust:\n  nested: bad\n"
                )
            }
        )
        self.assertEqual(
            sorted(f["rule"] for f in errors),
            ["config-invalid-value", "config-invalid-value"],
        )
        self.assertEqual(warnings, [])

    def test_unknown_trust_value_warns(self):
        errors, warnings = self.findings_for_config(
            {"00_Meta/config.yaml": "extension_trust: yolo\n"}
        )
        self.assertEqual(errors, [])
        self.assertEqual([f["rule"] for f in warnings], ["config-unknown-value"])

    def test_null_values_equal_absent(self):
        errors, warnings = self.findings_for_config(
            {"00_Meta/config.yaml": "write_exceptions:\nextension_trust:\ncontext:\n"}
        )
        self.assertEqual((errors, warnings), ([], []))


class ContextKeyTests(unittest.TestCase):
    """Spec §15.3: `context` (issue #12) — one scalar, personal | work.
    Recorded by onboard-owner's specialization step; parse-and-report only."""

    def findings(self, text):
        with tempfile.TemporaryDirectory() as td:
            root = vault(Path(td), {"00_Meta/config.yaml": text})
            errors, warnings = brain.run_validate(root, check_index=False)
            return (
                [f for f in errors if f["path"] == brain.CONFIG_RELPATH],
                [f for f in warnings if f["path"] == brain.CONFIG_RELPATH],
            )

    def test_documented_values_are_clean(self):
        for value in ("personal", "work"):
            errors, warnings = self.findings(f"context: {value}\n")
            self.assertEqual((errors, warnings), ([], []), value)

    def test_non_scalar_is_invalid_value_error(self):
        for text in ("context: [work]\n", "context:\n  kind: work\n"):
            errors, _ = self.findings(text)
            self.assertEqual([f["rule"] for f in errors], ["config-invalid-value"], text)

    def test_undocumented_scalar_warns(self):
        errors, warnings = self.findings("context: school\n")
        self.assertEqual(errors, [])
        self.assertEqual([f["rule"] for f in warnings], ["config-unknown-value"])

    def test_vault_context_accessor(self):
        self.assertEqual(brain.vault_context({}), "personal")
        self.assertEqual(brain.vault_context({"context": None}), "personal")
        self.assertEqual(brain.vault_context({"context": ["work"]}), "personal")
        self.assertEqual(brain.vault_context({"context": "work"}), "work")
        self.assertEqual(brain.DEFAULT_CONTEXT, "personal")

    def test_context_no_longer_reserved(self):
        self.assertIn("context", brain.CONFIG_IMPLEMENTED_KEYS)
        self.assertNotIn("context", brain.CONFIG_RESERVED_KEYS)


class ConfigCliTests(unittest.TestCase):
    def run_cli(self, root, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue()

    def test_config_command_defaults_and_overrides(self):
        with tempfile.TemporaryDirectory() as td:
            root = vault(Path(td), {})
            code, out = self.run_cli(root, "config", "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertFalse(data["present"])
            self.assertEqual(data["raw"], {})
            self.assertEqual(data["extensionTrust"], "first-party")
            self.assertEqual(data["context"], "personal")
            self.assertEqual(
                data["writeExceptions"], list(brain.AGENT_WRITE_DEFAULT_PREFIXES)
            )
            self.assertEqual(data["reservedKeys"], sorted(brain.CONFIG_RESERVED_KEYS))
            self.assertEqual((data["errors"], data["warnings"]), ([], []))
        with tempfile.TemporaryDirectory() as td:
            root = vault(
                Path(td),
                {
                    "06_Resources/README.md": note(),
                    "00_Meta/config.yaml": (
                        "extension_trust: relaxed\ncontext: work\n"
                        "write_exceptions:\n  - 06_Resources\n"
                    ),
                },
            )
            code, out = self.run_cli(root, "config", "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertTrue(data["present"])
            self.assertEqual(data["extensionTrust"], "relaxed")
            self.assertEqual(data["context"], "work")
            self.assertIn("06_Resources/", data["writeExceptions"])
            code, human = self.run_cli(root, "config")
            self.assertEqual(code, 0)
            self.assertIn("extension trust: relaxed", human)
            self.assertIn("context: work", human)


if __name__ == "__main__":
    unittest.main()
