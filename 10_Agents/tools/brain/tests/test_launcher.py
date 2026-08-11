"""Portable resolver and managed installer tests (spec §21, issue #4)."""

import contextlib
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
LAUNCHER = ROOT / "brain"
WINDOWS_LAUNCHER = ROOT / "brain.cmd"


def fake_vault(root: Path, marker: str, *, exit_code: int = 0) -> Path:
    tool = root / "10_Agents/tools/brain/brain.py"
    tool.parent.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# fixture\n", encoding="utf-8")
    tool.write_text(
        "import json, os, sys\n"
        f"print({marker!r})\n"
        "print(json.dumps(sys.argv[1:], ensure_ascii=False))\n"
        "print('fixture-stderr', file=sys.stderr)\n"
        f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    return root


@unittest.skipUnless(os.name == "posix", "executes the POSIX launcher")
class PosixResolverTests(unittest.TestCase):
    def run_launcher(self, cwd: Path, *args: str, env_changes=None):
        env = os.environ.copy()
        env.pop("BRAIN_VAULT", None)
        if env_changes:
            env.update(env_changes)
        return subprocess.run(
            [str(LAUNCHER), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_upward_walk_handles_nested_spaces_and_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            root = fake_vault(Path(td) / "Vault space 雪", "outer")
            nested = root / "deep space/子"
            nested.mkdir(parents=True)
            result = self.run_launcher(nested, "search", "two words", "雪")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.splitlines()[0], "outer")
            self.assertEqual(
                json.loads(result.stdout.splitlines()[1]),
                ["search", "two words", "雪"],
            )

    def test_nearest_nested_vault_and_sibling_forks_do_not_cross_select(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            outer = fake_vault(base / "outer", "outer")
            inner = fake_vault(outer / "nested", "inner")
            sibling = fake_vault(base / "sibling", "sibling")
            (inner / "work").mkdir()
            (sibling / "work").mkdir()
            self.assertTrue(self.run_launcher(inner / "work").stdout.startswith("inner\n"))
            self.assertTrue(
                self.run_launcher(sibling / "work").stdout.startswith("sibling\n")
            )

    def test_cli_override_beats_hostile_environment_and_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            selected = fake_vault(base / "selected vault", "selected")
            poisoned = fake_vault(base / "poisoned", "poisoned")
            cwd = base / "cwd"
            cwd.mkdir()
            hostile = "$(touch SHOULD_NOT_EXIST);&|!*"
            result = self.run_launcher(
                cwd,
                "search",
                hostile,
                "",
                "--vault",
                str(selected),
                env_changes={"BRAIN_VAULT": str(poisoned)},
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(result.stdout.startswith("selected\n"))
            self.assertEqual(
                json.loads(result.stdout.splitlines()[1]),
                ["search", hostile, "", "--vault", str(selected)],
            )
            self.assertFalse((cwd / "SHOULD_NOT_EXIST").exists())

    def test_environment_override_and_equals_form(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            one = fake_vault(base / "one", "one")
            two = fake_vault(base / "two", "two")
            result = self.run_launcher(
                base,
                "--vault=" + str(two),
                "list",
                env_changes={"BRAIN_VAULT": str(one)},
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(result.stdout.startswith("two\n"))

    def test_option_terminator_stops_vault_scanning(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            current = fake_vault(base / "current", "current")
            other = fake_vault(base / "other", "other")
            result = self.run_launcher(
                current, "--", "--vault", str(other)
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(result.stdout.startswith("current\n"))

    def test_child_stdout_stderr_and_exit_status_are_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = fake_vault(Path(td) / "vault", "marker", exit_code=37)
            result = self.run_launcher(root, "x")
            self.assertEqual(result.returncode, 37)
            self.assertEqual(result.stdout, 'marker\n["x"]\n')
            self.assertEqual(result.stderr, "fixture-stderr\n")

    def test_repeated_missing_and_invalid_overrides_fail_without_path_echo(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            valid = fake_vault(base / "valid", "valid")
            secret = base / "private-secret-path"
            cases = [
                (["--vault"], {}, 2),
                (["--vault", str(valid), "--vault", str(valid)], {}, 2),
                (["--vault", str(secret)], {}, 2),
                ([], {"BRAIN_VAULT": str(secret)}, 2),
            ]
            for args, env, expected in cases:
                with self.subTest(args=args, env=env):
                    result = self.run_launcher(base, *args, env_changes=env)
                    self.assertEqual(result.returncode, expected)
                    self.assertNotIn(str(secret), result.stderr)

    def test_symlinked_root_marker_and_tool_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            valid = fake_vault(base / "valid", "valid")
            root_link = base / "vault-link"
            os.symlink(valid, root_link)
            self.assertEqual(
                self.run_launcher(base, "--vault", str(root_link)).returncode, 2
            )
            bad_marker = fake_vault(base / "bad-marker", "bad")
            (bad_marker / "AGENTS.md").unlink()
            os.symlink(valid / "AGENTS.md", bad_marker / "AGENTS.md")
            self.assertEqual(
                self.run_launcher(base, "--vault", str(bad_marker)).returncode, 2
            )
            bad_tool = fake_vault(base / "bad-tool", "bad")
            (bad_tool / "10_Agents/tools/brain/brain.py").unlink()
            os.symlink(
                valid / "10_Agents/tools/brain/brain.py",
                bad_tool / "10_Agents/tools/brain/brain.py",
            )
            self.assertEqual(
                self.run_launcher(base, "--vault", str(bad_tool)).returncode, 2
            )
            bad_parent = base / "bad-parent"
            bad_parent.mkdir()
            (bad_parent / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
            os.symlink(valid / "10_Agents", bad_parent / "10_Agents")
            self.assertEqual(
                self.run_launcher(base, "--vault", str(bad_parent)).returncode, 2
            )

    def test_missing_python_returns_127(self):
        with tempfile.TemporaryDirectory() as td:
            root = fake_vault(Path(td) / "vault", "unused")
            result = subprocess.run(
                ["/bin/sh", str(LAUNCHER)],
                cwd=root,
                env={"PATH": ""},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 127)
            self.assertIn("python3 is unavailable", result.stderr)


class InstallerTests(unittest.TestCase):
    def run_install(self, bin_dir: Path, state_file: Path, *args: str):
        env = {"PATH": str(bin_dir), brain.INSTALL_MANIFEST_ENV: str(state_file)}
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(
            stdout
        ), contextlib.redirect_stderr(stderr):
            code = brain.main(["install", "--vault", str(ROOT), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_preview_apply_doctor_and_uninstall_are_reversible(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state/brain-install.json"
            rc = base / "shellrc"
            rc.write_text("owner data\n", encoding="utf-8")
            before = sorted(str(p.relative_to(base)) for p in base.rglob("*"))

            code, out, _ = self.run_install(bin_dir, state_file, "--json")
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out)["writesPerformed"])
            self.assertEqual(before, sorted(str(p.relative_to(base)) for p in base.rglob("*")))

            code, out, _ = self.run_install(bin_dir, state_file, "--apply", "--json")
            self.assertEqual(code, 0)
            target = bin_dir / "brain"
            self.assertEqual(target.read_bytes(), LAUNCHER.read_bytes())
            self.assertTrue(state_file.is_file())
            self.assertEqual(rc.read_text(encoding="utf-8"), "owner data\n")
            vault = fake_vault(base / "vault with spaces", "installed-copy")
            executed = subprocess.run(
                [str(target), "probe", "two words"],
                cwd=vault,
                env={**os.environ, "PATH": os.environ.get("PATH", "")},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(executed.returncode, 0)
            self.assertTrue(executed.stdout.startswith("installed-copy\n"))

            code, _, _ = self.run_install(bin_dir, state_file, "--doctor", "--json")
            self.assertEqual(code, 0)
            code, out, _ = self.run_install(bin_dir, state_file, "--uninstall", "--json")
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out)["writesPerformed"])
            self.assertTrue(target.exists())
            code, _, _ = self.run_install(
                bin_dir, state_file, "--uninstall", "--apply", "--json"
            )
            self.assertEqual(code, 0)
            self.assertFalse(target.exists())
            self.assertFalse(state_file.exists())
            self.assertEqual(rc.read_text(encoding="utf-8"), "owner data\n")

    def test_foreign_target_and_symlinks_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state.json"
            target = bin_dir / "brain"
            target.write_text("foreign\n", encoding="utf-8")
            code, _, err = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "foreign\n")
            self.assertFalse(state_file.exists())

            target.unlink()
            outside = base / "outside"
            outside.write_text("foreign\n", encoding="utf-8")
            os.symlink(outside, target)
            code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 1)
            self.assertEqual(outside.read_text(encoding="utf-8"), "foreign\n")

    def test_recognized_old_version_upgrades_but_drift_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state.json"
            target = bin_dir / "brain"
            old = b"#!/bin/sh\nexit 0\n"
            target.write_bytes(old)
            target.chmod(0o755)
            state_file.write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {
                                "installedDigest": hashlib.sha256(old).hexdigest(),
                                "platform": "posix",
                                "target": str(target),
                            }
                        ],
                        "schemaVersion": 1,
                    }
                ),
                encoding="utf-8",
            )
            state_file.chmod(0o600)
            code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 0)
            self.assertEqual(target.read_bytes(), LAUNCHER.read_bytes())
            target.write_text("owner changed it\n", encoding="utf-8")
            code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 1)
            code, _, _ = self.run_install(
                bin_dir, state_file, "--uninstall", "--apply"
            )
            self.assertEqual(code, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "owner changed it\n")

    def test_manifest_failure_rolls_back_new_target(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state.json"
            original_write = brain._atomic_external_write

            def fail_manifest(path, data, mode, guard):
                if path.name == "state.json":
                    raise OSError("injected")
                return original_write(path, data, mode, guard)

            with mock.patch.object(brain, "_atomic_external_write", side_effect=fail_manifest):
                code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 1)
            self.assertFalse((bin_dir / "brain").exists())
            self.assertFalse(state_file.exists())

    def test_keyboard_interrupt_during_install_manifest_write_rolls_back_target(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state/brain-install.json"
            original_write = brain._atomic_external_write

            def interrupt_manifest(path, data, mode, guard):
                if path == state_file.resolve(strict=False):
                    raise KeyboardInterrupt
                return original_write(path, data, mode, guard)

            with mock.patch.object(
                brain, "_atomic_external_write", side_effect=interrupt_manifest
            ), self.assertRaises(KeyboardInterrupt):
                self.run_install(bin_dir, state_file, "--apply")
            self.assertFalse((bin_dir / "brain").exists())
            self.assertFalse(state_file.exists())

    def test_keyboard_interrupt_during_uninstall_manifest_removal_restores_target(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state/brain-install.json"
            code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 0)
            target = bin_dir / "brain"
            original_remove = brain._remove_external

            def interrupt_manifest_removal(path, guard, *, missing_ok=False):
                if path == state_file.resolve(strict=False):
                    raise KeyboardInterrupt
                return original_remove(path, guard, missing_ok=missing_ok)

            with mock.patch.object(
                brain, "_remove_external", side_effect=interrupt_manifest_removal
            ), self.assertRaises(KeyboardInterrupt):
                self.run_install(bin_dir, state_file, "--uninstall", "--apply")
            self.assertEqual(target.read_bytes(), LAUNCHER.read_bytes())
            self.assertTrue(state_file.exists())

    @unittest.skipUnless(os.name == "posix", "symlink race fixture")
    def test_target_parent_swap_after_preflight_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state/brain-install.json"
            malicious = base / "malicious"
            malicious.mkdir()
            parked = base / "parked-bin"
            original_write = brain._atomic_external_write
            swapped = False

            def swap_before_target_write(path, data, mode, guard):
                nonlocal swapped
                if path.name == "brain" and not swapped:
                    swapped = True
                    bin_dir.rename(parked)
                    os.symlink(malicious, bin_dir)
                return original_write(path, data, mode, guard)

            try:
                with mock.patch.object(
                    brain, "_atomic_external_write", side_effect=swap_before_target_write
                ):
                    code, _, _ = self.run_install(bin_dir, state_file, "--apply")
                self.assertEqual(code, 1)
                self.assertFalse((malicious / "brain").exists())
                self.assertFalse((parked / "brain").exists())
            finally:
                if bin_dir.is_symlink():
                    bin_dir.unlink()
                if parked.exists():
                    parked.rename(bin_dir)

    @unittest.skipUnless(os.name == "posix", "symlink race fixture")
    def test_state_parent_swap_after_target_write_is_rejected_and_rolled_back(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_dir = base / "state"
            state_dir.mkdir()
            state_file = state_dir / "brain-install.json"
            malicious = base / "malicious"
            malicious.mkdir()
            parked = base / "parked-state"
            original_write = brain._atomic_external_write
            swapped = False

            def swap_before_manifest_write(path, data, mode, guard):
                nonlocal swapped
                if path.name == "brain-install.json" and not swapped:
                    swapped = True
                    state_dir.rename(parked)
                    os.symlink(malicious, state_dir)
                return original_write(path, data, mode, guard)

            try:
                with mock.patch.object(
                    brain, "_atomic_external_write", side_effect=swap_before_manifest_write
                ):
                    code, _, _ = self.run_install(bin_dir, state_file, "--apply")
                self.assertEqual(code, 1)
                self.assertFalse((bin_dir / "brain").exists())
                self.assertFalse((malicious / "brain-install.json").exists())
                self.assertFalse((parked / "brain-install.json").exists())
            finally:
                if state_dir.is_symlink():
                    state_dir.unlink()
                if parked.exists():
                    parked.rename(state_dir)

    @unittest.skipUnless(os.name == "posix", "symlink race fixture")
    def test_digest_refuses_parent_swap_without_reading_redirected_file(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            target = (bin_dir / "brain").resolve(strict=False)
            target.write_bytes(b"managed")
            guard = brain._capture_external_parent(ROOT, target, "target")
            parked = base / "parked-bin"
            malicious = base / "malicious"
            malicious.mkdir()
            (malicious / "brain").write_bytes(b"external-secret")
            bin_dir.rename(parked)
            os.symlink(malicious, bin_dir)
            try:
                with self.assertRaises(brain.InstallError):
                    brain._external_digest(target, guard)
            finally:
                bin_dir.unlink()
                parked.rename(bin_dir)

    def test_stale_or_foreign_manifest_is_refused_without_writes(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state.json"
            state_file.write_text('{"unexpected": true}\n', encoding="utf-8")
            before = state_file.read_bytes()
            code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 1)
            self.assertEqual(state_file.read_bytes(), before)
            self.assertFalse((bin_dir / "brain").exists())

    def test_windows_payload_can_be_managed_without_executing_cmd(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            state_file = base / "state.json"
            with mock.patch.object(brain, "_install_platform", return_value=("windows", "brain.cmd")):
                code, _, _ = self.run_install(bin_dir, state_file, "--apply")
            self.assertEqual(code, 0)
            self.assertEqual((bin_dir / "brain.cmd").read_bytes(), WINDOWS_LAUNCHER.read_bytes())


class WindowsContractTests(unittest.TestCase):
    def test_cmd_resolver_carries_precedence_passthrough_and_exit_contract(self):
        text = WINDOWS_LAUNCHER.read_text(encoding="utf-8")
        for token in (
            "--vault",
            "BRAIN_VAULT",
            "AGENTS.md",
            "10_Agents\\tools\\brain\\brain.py",
            "py -3",
            "%*",
            "exit /b %ERRORLEVEL%",
            "multiple --vault options are ambiguous",
        ):
            self.assertIn(token, text)

    def test_no_plugin_bin_or_shell_rc_invention(self):
        combined = WINDOWS_LAUNCHER.read_text() + LAUNCHER.read_text()
        self.assertNotIn("plugin.json", combined)
        self.assertNotIn(".bashrc", combined)
        self.assertNotIn("PowerShell", combined)


if __name__ == "__main__":
    unittest.main()
