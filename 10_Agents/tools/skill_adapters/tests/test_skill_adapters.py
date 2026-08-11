"""Tests for deterministic repository-local skill adapters (issue #82)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
TOOL = ROOT / "10_Agents/tools/skill_adapters/gen_skill_adapters.py"
SPEC = importlib.util.spec_from_file_location("gen_skill_adapters", TOOL)
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GEN
SPEC.loader.exec_module(GEN)


def add_skill(repo: Path, directory: str, name: str | None = None, description: str = "Do a thing.") -> None:
    target = repo / "10_Agents/skills" / directory / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"---\nname: {name or directory}\ndescription: {description}\n---\n\n# Instructions\n",
        encoding="utf-8",
    )


def copy_repo(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )


def init_clean_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Adapter Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "adapter@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "fixture"], cwd=repo, check=True)


def generated_snapshot(repo: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(repo): path.read_bytes()
        for root in GEN.OUTPUT_ROOTS
        for path in sorted((repo / root).rglob("SKILL.md"))
    }


def all_generated_working_state(repo: Path) -> dict[str, tuple[str, int, bytes | None]]:
    roots = (
        Path("10_Agents/tools/brain/vault-index.json"),
        Path(".vscode/second-brain.code-snippets"),
        *GEN.OUTPUT_ROOTS,
    )
    rows: dict[str, tuple[str, int, bytes | None]] = {}
    for root in roots:
        path = repo / root
        if not os.path.lexists(path):
            rows[root.as_posix()] = ("absent", 0, None)
            continue
        paths = [path] if path.is_file() else [path, *sorted(path.rglob("*"))]
        for child in paths:
            rel = child.relative_to(repo).as_posix()
            mode = child.lstat().st_mode
            if child.is_dir():
                rows[rel] = ("directory", mode, None)
            elif child.is_file():
                rows[rel] = ("file", mode, child.read_bytes())
            else:
                rows[rel] = ("other", mode, None)
    return rows


def raw_git_index(repo: Path) -> bytes:
    value = subprocess.run(
        ["git", "rev-parse", "--git-path", "index"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    return path.resolve().read_bytes()


class SkillAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-adapters-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)

    def test_generate_is_byte_stable_and_text_only(self):
        add_skill(self.repo, "alpha")
        add_skill(self.repo, "beta", description='Use when a value says "yes".')
        GEN.generate(self.repo)
        first = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("SKILL.md")}
        GEN.generate(self.repo)
        second = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("SKILL.md")}
        self.assertEqual(first, second)
        self.assertEqual(GEN.check(self.repo), [])
        for root in GEN.OUTPUT_ROOTS:
            for path in (self.repo / root).rglob("*"):
                self.assertFalse(path.is_symlink(), path)

    def test_metadata_parity_and_canonical_pointer(self):
        add_skill(self.repo, "alpha", description="Exact discovery description.")
        GEN.generate(self.repo)
        for root in GEN.OUTPUT_ROOTS:
            adapter = self.repo / root / "alpha/SKILL.md"
            self.assertEqual(GEN.read_metadata(adapter), ("alpha", "Exact discovery description."))
            text = adapter.read_text(encoding="utf-8")
            self.assertIn("second-brain-skill-adapter/v2", text)
            self.assertIn('adapter-version: "2"', text)
            self.assertRegex(text, r'content-sha256: "[0-9a-f]{64}"')
            self.assertIn("../../../10_Agents/skills/alpha/SKILL.md", text)

    def test_check_reports_missing_extra_and_parity_drift(self):
        add_skill(self.repo, "alpha")
        GEN.generate(self.repo)
        missing = self.repo / ".agents/skills/alpha/SKILL.md"
        missing.unlink()
        extra = self.repo / ".claude/skills/extra/SKILL.md"
        extra.parent.mkdir(parents=True)
        extra.write_text("foreign\n", encoding="utf-8")
        drift = self.repo / ".claude/skills/alpha/SKILL.md"
        drift.write_text(drift.read_text(encoding="utf-8").replace("Do a thing.", "Drift."), encoding="utf-8")
        findings = GEN.check(self.repo)
        self.assertIn("missing:.agents/skills/alpha/SKILL.md", findings)
        self.assertIn("extra:.claude/skills/extra/SKILL.md", findings)
        self.assertIn("drift:.claude/skills/alpha/SKILL.md", findings)

    def test_refuses_metadata_directory_mismatch(self):
        add_skill(self.repo, "alpha", name="other")
        with self.assertRaisesRegex(GEN.AdapterError, "must equal directory"):
            GEN.catalog(self.repo)

    def test_refuses_case_collisions_independent_of_filesystem(self):
        with self.assertRaisesRegex(GEN.AdapterError, "case-colliding"):
            GEN.require_case_unique(["Alpha", "alpha"], label="skill directories")

    def test_rejects_unsupported_yaml_and_agent_skill_limits(self):
        add_skill(self.repo, "alpha", description="|")
        with self.assertRaisesRegex(GEN.AdapterError, "block scalars"):
            GEN.catalog(self.repo)

        shutil.rmtree(self.repo / "10_Agents/skills/alpha")
        long_name = "a" * (GEN.MAX_SKILL_NAME_LENGTH + 1)
        add_skill(self.repo, long_name)
        with self.assertRaisesRegex(GEN.AdapterError, "name exceeds"):
            GEN.catalog(self.repo)

        shutil.rmtree(self.repo / "10_Agents/skills" / long_name)
        add_skill(
            self.repo,
            "alpha",
            description="d" * (GEN.MAX_SKILL_DESCRIPTION_LENGTH + 1),
        )
        with self.assertRaisesRegex(GEN.AdapterError, "description exceeds"):
            GEN.catalog(self.repo)

    def test_rejects_non_string_yaml_scalar_shapes(self):
        for value in (
            "[]", "{}", "null", "true", "42", "-3.14", "1.", "&anchor", "*alias",
            "[] # comment", "{} # comment", "null # comment", "true # comment",
            "42 # comment", "1. # comment",
        ):
            with self.subTest(value=value):
                isolated = self.repo / value.encode().hex()
                add_skill(isolated, "alpha", description=value)
                with self.assertRaisesRegex(GEN.AdapterError, "non-string YAML"):
                    GEN.catalog(isolated)

    def test_yaml_comment_stripping_keeps_quoted_hash_data(self):
        cases = {
            '"quoted # data" # actual comment': "quoted # data",
            "'single # data' # actual comment": "single # data",
            "plain#data # actual comment": "plain#data",
            "plain text # actual comment": "plain text",
        }
        for number, (value, expected) in enumerate(cases.items()):
            with self.subTest(value=value):
                isolated = self.repo / f"quoted-{number}"
                add_skill(isolated, "alpha", description=value)
                self.assertEqual(GEN.catalog(isolated)[0].description, expected)

    def test_refuses_foreign_expected_path_before_any_mutation(self):
        add_skill(self.repo, "alpha")
        add_skill(self.repo, "beta")
        foreign = self.repo / ".agents/skills/alpha/SKILL.md"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("owner content\n", encoding="utf-8")
        with self.assertRaisesRegex(GEN.AdapterError, "foreign adapter"):
            GEN.generate(self.repo)
        self.assertEqual(foreign.read_text(encoding="utf-8"), "owner content\n")
        self.assertFalse((self.repo / ".agents/skills/beta/SKILL.md").exists())
        self.assertFalse((self.repo / ".claude/skills/alpha/SKILL.md").exists())

    def test_refuses_directory_at_expected_file_before_any_mutation(self):
        add_skill(self.repo, "alpha")
        add_skill(self.repo, "beta")
        collision = self.repo / ".agents/skills/alpha/SKILL.md"
        collision.mkdir(parents=True)
        with self.assertRaisesRegex(GEN.AdapterError, "foreign adapter"):
            GEN.generate(self.repo)
        self.assertTrue(collision.is_dir())
        self.assertFalse((self.repo / ".agents/skills/beta/SKILL.md").exists())
        self.assertFalse((self.repo / ".claude/skills/alpha/SKILL.md").exists())

    def test_marker_quote_does_not_grant_delete_ownership(self):
        add_skill(self.repo, "alpha")
        GEN.generate(self.repo)
        extra = self.repo / ".agents/skills/foreign/SKILL.md"
        extra.parent.mkdir(parents=True)
        body = f"A note quoting {GEN.GENERATED_MARKER}, not a generated adapter.\n"
        extra.write_text(body, encoding="utf-8")
        with self.assertRaisesRegex(GEN.AdapterError, "foreign adapter"):
            GEN.generate(self.repo)
        self.assertEqual(extra.read_text(encoding="utf-8"), body)

    def test_removes_only_structurally_owned_obsolete_adapter(self):
        add_skill(self.repo, "alpha")
        add_skill(self.repo, "obsolete")
        GEN.generate(self.repo)
        (self.repo / "10_Agents/skills/obsolete/SKILL.md").unlink()
        (self.repo / "10_Agents/skills/obsolete").rmdir()
        GEN.generate(self.repo)
        for root in GEN.OUTPUT_ROOTS:
            self.assertFalse((self.repo / root / "obsolete/SKILL.md").exists())
        self.assertEqual(GEN.check(self.repo), [])

    def test_modified_obsolete_generated_looking_adapter_is_never_deleted(self):
        add_skill(self.repo, "alpha")
        add_skill(self.repo, "obsolete")
        GEN.generate(self.repo)
        foreign = self.repo / ".agents/skills/obsolete/SKILL.md"
        foreign.write_text(
            foreign.read_text(encoding="utf-8") + "\nowner appendix\n",
            encoding="utf-8",
        )
        shutil.rmtree(self.repo / "10_Agents/skills/obsolete")
        before = foreign.read_bytes()
        with self.assertRaisesRegex(GEN.AdapterError, "foreign adapter"):
            GEN.generate(self.repo)
        self.assertEqual(foreign.read_bytes(), before)
        self.assertTrue((self.repo / ".claude/skills/obsolete/SKILL.md").is_file())

    def test_generation_is_transactional_on_write_failure_and_interruption(self):
        add_skill(self.repo, "alpha")
        GEN.generate(self.repo)
        source = self.repo / "10_Agents/skills/alpha/SKILL.md"
        source.write_text(
            source.read_text(encoding="utf-8").replace("Do a thing.", "Changed."),
            encoding="utf-8",
        )
        before = generated_snapshot(self.repo)
        real_write = GEN._atomic_write
        for failure in (OSError("injected write failure"), KeyboardInterrupt()):
            calls = 0

            def fail_second(path, body):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise failure
                return real_write(path, body)

            with self.subTest(failure=type(failure).__name__), mock.patch.object(
                GEN, "_atomic_write", side_effect=fail_second
            ):
                expected_error = KeyboardInterrupt if isinstance(failure, KeyboardInterrupt) else GEN.AdapterError
                with self.assertRaises(expected_error):
                    GEN.generate(self.repo)
                self.assertEqual(generated_snapshot(self.repo), before)

    def test_generation_rolls_back_mid_swap_failure_and_interruption(self):
        add_skill(self.repo, "alpha")
        GEN.generate(self.repo)
        source = self.repo / "10_Agents/skills/alpha/SKILL.md"
        source.write_text(
            source.read_text(encoding="utf-8").replace("Do a thing.", "Changed."),
            encoding="utf-8",
        )
        before = generated_snapshot(self.repo)
        real_replace = GEN.os.replace
        for failure in (OSError("injected swap failure"), KeyboardInterrupt()):
            calls = 0

            def fail_fifth(src, dst, *args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 5:
                    raise failure
                return real_replace(src, dst, *args, **kwargs)

            with self.subTest(failure=type(failure).__name__), mock.patch.object(
                GEN.os, "replace", side_effect=fail_fifth
            ):
                expected_error = KeyboardInterrupt if isinstance(failure, KeyboardInterrupt) else GEN.AdapterError
                with self.assertRaises(expected_error):
                    GEN.generate(self.repo)
                self.assertEqual(generated_snapshot(self.repo), before)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_refuses_symlink_in_generated_tree(self):
        add_skill(self.repo, "alpha")
        target = self.repo / "target"
        target.write_text("x", encoding="utf-8")
        link = self.repo / ".agents/skills/alpha/SKILL.md"
        link.parent.mkdir(parents=True)
        os.symlink(target, link)
        with self.assertRaisesRegex(GEN.AdapterError, "unsafe output tree"):
            GEN.generate(self.repo)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_refuses_symlinked_output_ancestor_without_external_write(self):
        add_skill(self.repo, "alpha")
        outside = self.repo / "outside"
        outside.mkdir()
        os.symlink(outside, self.repo / ".agents")
        with self.assertRaisesRegex(GEN.AdapterError, "unsafe output tree"):
            GEN.generate(self.repo)
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_refuses_symlink_in_canonical_root_ancestors(self):
        outside = self.repo / "outside-canonical"
        (outside / "skills/alpha").mkdir(parents=True)
        (outside / "skills/alpha/SKILL.md").write_text(
            "---\nname: alpha\ndescription: Safe.\n---\n",
            encoding="utf-8",
        )
        os.symlink(outside, self.repo / "10_Agents")
        with self.assertRaisesRegex(GEN.AdapterError, "symlinked canonical path component"):
            GEN.generate(self.repo)
        self.assertFalse((self.repo / ".agents").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_parent_swap_after_final_preflight_cannot_escape_repo(self):
        add_skill(self.repo, "alpha")
        GEN.generate(self.repo)
        source = self.repo / "10_Agents/skills/alpha/SKILL.md"
        source.write_text(
            source.read_text(encoding="utf-8").replace("Do a thing.", "Changed."),
            encoding="utf-8",
        )
        outside = self.repo / "outside-output"
        outside.mkdir()
        held = self.repo / "held-agents"
        real_preflight = GEN.preflight
        calls = 0

        def swap_after_third(repo):
            nonlocal calls
            calls += 1
            result = real_preflight(repo)
            if calls == 3:
                os.rename(self.repo / ".agents", held)
                os.symlink(outside, self.repo / ".agents")
            return result

        with mock.patch.object(GEN, "preflight", side_effect=swap_after_third):
            with self.assertRaisesRegex(
                GEN.AdapterError, "output root changed|unsafe output parent|post-generation drift"
            ):
                GEN.generate(self.repo)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list(self.repo.glob(".skill-adapter-transaction-*")), [])

    def test_executable_project_and_global_preview_make_zero_home_writes(self):
        fake_home = Path(self.temp.name) / "canary-home"
        fake_home.mkdir()
        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        planner = ROOT / "10_Agents/tools/skill_adapters/harness_setup.py"
        for mode in ("project", "global-preview"):
            for harness in (
                "claude-code",
                "codex",
                "opencode",
                "pi",
                "cursor",
                "copilot",
                "muse-code",
            ):
                command = [
                    sys.executable,
                    str(planner),
                    mode,
                    "--repo",
                    str(ROOT),
                    "--harness",
                    harness,
                    "--json",
                ]
                if mode == "global-preview":
                    command.extend(("--home", str(fake_home)))
                proc = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                plan = json.loads(proc.stdout)
                self.assertEqual(plan["mode"], mode)
                self.assertEqual(plan["harness"], harness)
        self.assertEqual(list(fake_home.iterdir()), [])

    def test_precommit_refuses_unstaged_canonical_skill_before_staging_adapter(self):
        clone = self.repo / "clone"
        copy_repo(clone)
        init_clean_git_repo(clone)
        readme = clone / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nstaged note\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=clone, check=True)
        skill = clone / "10_Agents/skills/onboard-owner/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nunstaged note\n", encoding="utf-8")

        proc = subprocess.run(
            ["sh", ".githooks/pre-commit"],
            cwd=clone,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unstaged canonical skill changes", proc.stderr)
        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=clone,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(cached, ["README.md"])

    def test_precommit_foreign_adapter_fails_before_index_or_staging_mutation(self):
        clone = self.repo / "foreign-hook-clone"
        copy_repo(clone)
        init_clean_git_repo(clone)
        readme = clone / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nstaged note\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=clone, check=True)
        foreign = clone / ".agents/skills/foreign/SKILL.md"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("foreign owner content\n", encoding="utf-8")
        index = clone / "10_Agents/tools/brain/vault-index.json"
        index_before = index.read_bytes()
        cached_before = subprocess.run(
            ["git", "diff", "--cached", "--binary"],
            cwd=clone,
            check=True,
            capture_output=True,
        ).stdout

        proc = subprocess.run(
            ["sh", ".githooks/pre-commit"],
            cwd=clone,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("preflight failed", proc.stderr)
        self.assertEqual(index.read_bytes(), index_before)
        cached_after = subprocess.run(
            ["git", "diff", "--cached", "--binary"],
            cwd=clone,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(cached_after, cached_before)

    def test_precommit_late_failure_restores_worktree_and_exact_git_index(self):
        main = self.repo / "rollback-hook-main"
        clone = self.repo / "rollback-hook-clone"
        copy_repo(main)
        init_clean_git_repo(main)
        subprocess.run(
            ["git", "worktree", "add", "-qb", "rollback-hook-test", str(clone)],
            cwd=main,
            check=True,
        )
        self.assertTrue((clone / ".git").is_file(), "fixture must exercise a linked worktree")

        template = clone / "09_Templates/template-project.md"
        template.write_bytes(template.read_bytes() + b"\nStaged template addition.\n")
        subprocess.run(["git", "add", "09_Templates/template-project.md"], cwd=clone, check=True)

        # Deliberately preserve three distinct versions: HEAD, a staged
        # generated version, and a different generated working-tree version.
        index = clone / "10_Agents/tools/brain/vault-index.json"
        original = index.read_bytes()
        index.write_bytes(original + b"staged generated sentinel\n")
        subprocess.run(
            ["git", "add", "10_Agents/tools/brain/vault-index.json"], cwd=clone, check=True
        )
        index.write_bytes(original + b"working generated sentinel\n")
        adapter = clone / ".agents/skills/onboard-owner/SKILL.md"
        adapter_original = adapter.read_bytes()
        adapter.write_bytes(adapter_original + b"staged adapter sentinel\n")
        subprocess.run(
            ["git", "add", ".agents/skills/onboard-owner/SKILL.md"], cwd=clone, check=True
        )
        adapter.write_bytes(adapter_original)  # valid working adapter, distinct staged adapter

        invalid = clone / "06_Resources/hook-invalid.md"
        invalid.write_text("no frontmatter\n", encoding="utf-8")
        working_before = all_generated_working_state(clone)
        git_index_before = raw_git_index(clone)
        cached_before = subprocess.run(
            ["git", "diff", "--cached", "--binary"], cwd=clone, check=True, capture_output=True
        ).stdout

        proc = subprocess.run(
            ["sh", ".githooks/pre-commit"], cwd=clone, capture_output=True, text=True
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("brain validate found errors", proc.stderr)
        self.assertEqual(all_generated_working_state(clone), working_before)
        self.assertEqual(raw_git_index(clone), git_index_before)
        self.assertEqual(
            subprocess.run(
                ["git", "diff", "--cached", "--binary"],
                cwd=clone,
                check=True,
                capture_output=True,
            ).stdout,
            cached_before,
        )
        self.assertEqual(list(clone.glob(".precommit-generated-transaction-*")), [])

    @unittest.skipUnless(os.name == "posix", "signal test requires POSIX process signals")
    def test_precommit_term_interruption_restores_worktree_and_git_index(self):
        clone = self.repo / "signal-hook-clone"
        copy_repo(clone)
        init_clean_git_repo(clone)
        template = clone / "09_Templates/template-project.md"
        template.write_bytes(template.read_bytes() + b"\nSignal-stage template addition.\n")
        subprocess.run(["git", "add", "09_Templates/template-project.md"], cwd=clone, check=True)

        working_before = all_generated_working_state(clone)
        git_index_before = raw_git_index(clone)
        wrapper_dir = self.repo / "signal-bin"
        wrapper_dir.mkdir()
        wrapper = wrapper_dir / "python3"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, signal, sys\n"
            "if len(sys.argv) > 2 and sys.argv[1].endswith('/brain.py') and sys.argv[2] == 'validate':\n"
            "    os.kill(os.getppid(), signal.SIGTERM)\n"
            "    raise SystemExit(143)\n"
            f"os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(wrapper_dir) + os.pathsep + env.get("PATH", "")

        proc = subprocess.run(
            ["sh", ".githooks/pre-commit"],
            cwd=clone,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(all_generated_working_state(clone), working_before)
        self.assertEqual(raw_git_index(clone), git_index_before)
        self.assertEqual(list(clone.glob(".precommit-generated-transaction-*")), [])

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI is not installed")
    def test_codex_discovers_repo_adapters_from_clean_clone(self):
        clone = self.repo / "codex-clone"
        copy_repo(clone)
        init_clean_git_repo(clone)
        self.assertEqual(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=clone,
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
            "",
        )
        fake_home = self.repo / "codex-home"
        fake_codex_home = fake_home / ".codex"
        fake_codex_home.mkdir(parents=True)
        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        env["CODEX_HOME"] = str(fake_codex_home)
        proc = subprocess.run(
            ["codex", "-C", str(clone), "debug", "prompt-input", "adapter discovery smoke"],
            cwd=clone,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        json.loads(proc.stdout)  # The debug surface must remain machine-readable.
        prompt = proc.stdout
        adapter = (clone / ".agents/skills/onboard-owner/SKILL.md").as_posix()
        self.assertIn(adapter, prompt)
        self.assertIn("- onboard-owner:", prompt)
        self.assertIn("Verify this vault's", prompt)


if __name__ == "__main__":
    unittest.main()
