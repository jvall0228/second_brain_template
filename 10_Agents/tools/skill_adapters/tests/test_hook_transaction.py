"""Commit/merge integration and concurrent publication regression cases."""
from __future__ import annotations

import errno
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_skill_adapters import ROOT, copy_repo, init_clean_git_repo, raw_git_index

SPEC = importlib.util.spec_from_file_location("hook_transaction_review_tests", ROOT / "10_Agents/tools/skill_adapters/hook_transaction.py")
TX = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TX
SPEC.loader.exec_module(TX)


def git(root, *args, check=True):
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if check and proc.returncode:
        raise AssertionError(proc.stdout + proc.stderr)
    return proc


@unittest.skipUnless(os.name == "posix", "safe hook publication requires POSIX")
class HookTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hook-transaction-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"

    def clone(self):
        copy_repo(self.root)
        init_clean_git_repo(self.root)
        return self.root

    def test_actual_commit_excludes_unstaged_note_and_template_content(self):
        root = self.clone()
        note = root / "README.md"
        template = root / "09_Templates/template-daily-log.md"
        template.write_text(template.read_text() + "\nSTAGED-TEMPLATE-ADDITION\n")
        git(root, "add", "09_Templates/template-daily-log.md")
        staged_template = git(root, "show", ":09_Templates/template-daily-log.md").stdout
        template.write_text(template.read_text() + "\nUNSTAGED-TEMPLATE-MARKER\n")
        note.write_text(note.read_text() + "\n## UNSTAGED-NOTE-HEADING\n")
        working = (note.read_bytes(), template.read_bytes())
        git(root, "config", "core.hooksPath", ".githooks")
        git(root, "commit", "-m", "commit only staged sources")
        self.assertEqual(git(root, "show", "HEAD:09_Templates/template-daily-log.md").stdout, staged_template)
        snippets = git(root, "show", "HEAD:.vscode/second-brain.code-snippets").stdout
        self.assertIn("STAGED-TEMPLATE-ADDITION", snippets)
        self.assertNotIn("UNSTAGED-TEMPLATE-MARKER", snippets)
        self.assertNotIn("UNSTAGED-NOTE-HEADING", git(root, "show", "HEAD:10_Agents/tools/brain/vault-index.json").stdout)
        self.assertEqual((note.read_bytes(), template.read_bytes()), working)
        self.assertEqual(set(git(root, "diff", "--name-only").stdout.splitlines()), {"README.md", "09_Templates/template-daily-log.md"})

    def test_actual_merge_commits_fresh_outputs_and_push_rejects_stale_tip(self):
        root = self.clone()
        base_branch = git(root, "branch", "--show-current").stdout.strip()
        git(root, "config", "merge.regenerate.driver", "true")
        git(root, "checkout", "-b", "other")
        (root / "README.md").write_text((root / "README.md").read_text() + "\nOther branch.\n")
        git(root, "add", "README.md")
        subprocess.run(["python3", "10_Agents/tools/brain/brain.py", "index"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        git(root, "add", "10_Agents/tools/brain/vault-index.json")
        git(root, "commit", "--no-verify", "-m", "other source")
        git(root, "checkout", base_branch)
        (root / "02_Inbox/README.md").write_text((root / "02_Inbox/README.md").read_text() + "\nMain branch.\n")
        git(root, "add", "02_Inbox/README.md")
        subprocess.run(["python3", "10_Agents/tools/brain/brain.py", "index"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        git(root, "add", "10_Agents/tools/brain/vault-index.json")
        git(root, "commit", "--no-verify", "-m", "main source")
        git(root, "config", "core.hooksPath", ".githooks")
        paused = git(root, "merge", "--no-edit", "other", check=False)
        self.assertNotEqual(paused.returncode, 0)
        self.assertIn("run git commit to finish", paused.stderr)
        git(root, "commit", "--no-edit")
        self.assertEqual(git(root, "status", "--porcelain").stdout, "")
        sha = git(root, "rev-parse", "HEAD").stdout.strip()
        good = subprocess.run(["sh", ".githooks/pre-push"], cwd=root,
            input=f"refs/heads/test {sha} refs/heads/test {'0' * 40}\n", capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        (root / "README.md").write_text((root / "README.md").read_text() + "\nBypassed hook.\n")
        git(root, "add", "README.md")
        git(root, "commit", "--no-verify", "-m", "stale generated commit")
        stale = git(root, "rev-parse", "HEAD").stdout.strip()
        # A freshly regenerated WORKTREE must not hide stale bytes in the tip.
        subprocess.run(["python3", "10_Agents/tools/brain/brain.py", "index"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        bad = subprocess.run(["sh", ".githooks/pre-push"], cwd=root,
            input=f"refs/heads/test {stale} refs/heads/test {'0' * 40}\n", capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("stale committed vault index", bad.stderr)

    def test_git_lock_blocks_other_staging_and_failure_preserves_live_edit(self):
        root = self.clone()
        before_index = raw_git_index(root)
        generated = root / "10_Agents/tools/brain/vault-index.json"
        marker = b"another actor changed the generated file\n"
        observed = []
        def fail_after_other_actor(tree, env):
            readme = root / "README.md"
            readme.write_text(readme.read_text() + "\nOther actor note edit.\n")
            observed.append(git(root, "add", "README.md", check=False))
            generated.write_bytes(marker)
            raise TX.TransactionError("injected validation failure")
        with mock.patch.object(TX, "build", side_effect=fail_after_other_actor):
            with self.assertRaisesRegex(TX.TransactionError, "injected validation failure"):
                TX.run(root)
        self.assertNotEqual(observed[0].returncode, 0)
        self.assertIn("index.lock", observed[0].stderr)
        self.assertEqual(raw_git_index(root), before_index)
        self.assertEqual(generated.read_bytes(), marker)
        self.assertFalse(Path(str(TX.index_path(root)) + ".lock").exists())

    def test_setup_failures_release_owned_lock_and_allow_retry(self):
        for step in ("mkdtemp", "fchmod", "read_index"):
            with self.subTest(step=step):
                root = (self.root / step).resolve()
                root.mkdir(parents=True)
                git(root, "init", "-b", "main")
                source = root / "source.md"
                source.write_bytes(b"staged source\n")
                git(root, "add", "source.md")
                source.write_bytes(b"unstaged source\n")
                index = TX.index_path(root)
                lock = Path(str(index) + ".lock")
                before_index = index.read_bytes()
                opened = []
                real_open, real_read = os.open, Path.read_bytes
                def record_lock(path, *args, **kwargs):
                    fd = real_open(path, *args, **kwargs)
                    if Path(path) == lock:
                        opened.append(fd)
                    return fd
                failure = OSError(errno.ENOSPC, "injected setup failure")
                def fail_index_read(path):
                    if path == index:
                        raise failure
                    return real_read(path)
                if step == "read_index":
                    fault = mock.patch.object(Path, "read_bytes", fail_index_read)
                else:
                    module = TX.tempfile if step == "mkdtemp" else TX.os
                    fault = mock.patch.object(module, step, side_effect=failure)
                with mock.patch.object(TX, "command"), mock.patch.object(TX, "build"):
                    with mock.patch.object(TX.os, "open", side_effect=record_lock), fault:
                        with self.assertRaisesRegex(OSError, "injected setup failure"):
                            TX.run(root)
                    self.assertEqual(len(opened), 1)
                    try:
                        os.fstat(opened[0])
                    except OSError as exc:
                        self.assertEqual(exc.errno, errno.EBADF)
                        closed = True
                    else:
                        os.close(opened[0])
                        closed = False
                    self.assertEqual(index.read_bytes(), before_index)
                    self.assertEqual(source.read_bytes(), b"unstaged source\n")
                    self.assertFalse(lock.exists())
                    self.assertTrue(closed, "the acquired lock descriptor leaked")
                    self.assertEqual(list(root.glob(TX.TRANSACTION_PREFIX + "*")), [])
                    TX.run(root)
                self.assertEqual(index.read_bytes(), before_index)
                self.assertEqual(source.read_bytes(), b"unstaged source\n")
                self.assertFalse(lock.exists())

    def test_setup_failure_preserves_replaced_lock(self):
        root = self.root.resolve()
        root.mkdir()
        git(root, "init", "-b", "main")
        source = root / "source.md"
        source.write_bytes(b"source\n")
        git(root, "add", "source.md")
        index = TX.index_path(root)
        before_index = index.read_bytes()
        lock = Path(str(index) + ".lock")
        def replace_lock_then_fail(**kwargs):
            lock.unlink()
            lock.write_bytes(b"another writer's lock\n")
            raise OSError(errno.ENOSPC, "injected setup failure")
        with mock.patch.object(TX, "command"), mock.patch.object(
            TX.tempfile, "mkdtemp", side_effect=replace_lock_then_fail
        ):
            with self.assertRaisesRegex(OSError, "injected setup failure"):
                TX.run(root)
        self.assertEqual(index.read_bytes(), before_index)
        self.assertEqual(source.read_bytes(), b"source\n")
        self.assertEqual(lock.read_bytes(), b"another writer's lock\n")

    def test_export_includes_skip_worktree_paths_for_staging_and_revision(self):
        root = self.root
        root.mkdir()
        git(root, "init", "-b", "main")
        git(root, "config", "user.name", "Hook Test")
        git(root, "config", "user.email", "hook@example.invalid")
        (root / "skipped.md").write_text("committed source\n")
        git(root, "add", "skipped.md")
        git(root, "commit", "-m", "base")
        git(root, "update-index", "--skip-worktree", "skipped.md")
        (root / "skipped.md").unlink()
        for revision in (None, "HEAD"):
            with tempfile.TemporaryDirectory() as td:
                tree, _, _ = TX.export_index(root, Path(td), TX.index_path(root), revision=revision)
                self.assertEqual((tree / "skipped.md").read_text(), "committed source\n")

    def test_parent_substitution_never_touches_outside_file(self):
        root = self.root
        root.mkdir()
        rel = "00_Meta/BOOTSTRAP.md"
        target = root / rel
        target.parent.mkdir()
        target.write_bytes(b"old output\n")
        before = TX.working_state(root)
        after = {rel: TX.FileState(b"new output\n", before[rel].mode, 0, 0)}
        outside = root.parent / "outside"
        outside.mkdir()
        external = outside / "BOOTSTRAP.md"
        external.write_bytes(b"unrelated outside file\n")
        index = root / "git-index"
        index.write_bytes(b"original index")
        copied = root / "staged-index"
        copied.write_bytes(b"new index")
        lock = root / "git-index.lock"
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        self.addCleanup(os.close, lock_fd)
        workspace = root / "recovery"
        workspace.mkdir()
        real_rename = os.rename
        raced = False
        def swap_parent_before_rename(source, destination, **kwargs):
            nonlocal raced
            if not raced and source == "BOOTSTRAP.md":
                raced = True
                real_rename(root / "00_Meta", root / "moved-meta")
                (root / "00_Meta").symlink_to(outside, target_is_directory=True)
            return real_rename(source, destination, **kwargs)
        with mock.patch.object(TX.os, "rename", side_effect=swap_parent_before_rename):
            with self.assertRaises(TX.TransactionError):
                TX.publish(root, workspace, before, after, index, b"original index", copied, lock, lock_fd)
        self.assertEqual(external.read_bytes(), b"unrelated outside file\n")
        self.assertEqual((root / "moved-meta/BOOTSTRAP.md").read_bytes(), b"old output\n")
        self.assertTrue((root / "00_Meta").is_symlink())
        self.assertEqual(index.read_bytes(), b"original index")

    def test_publication_collision_preserves_concurrent_file_and_recovery(self):
        root = self.root
        root.mkdir()
        rel = "00_Meta/BOOTSTRAP.md"
        target = root / rel
        target.parent.mkdir()
        target.write_bytes(b"old output\n")
        before = TX.working_state(root)
        after = {rel: TX.FileState(b"new output\n", before[rel].mode, 0, 0)}
        index = root / "git-index"
        index.write_bytes(b"original index")
        copied = root / "staged-index"
        copied.write_bytes(b"new index")
        lock = root / "git-index.lock"
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        self.addCleanup(os.close, lock_fd)
        workspace = root / "recovery"
        workspace.mkdir()
        real_link = os.link
        raced = False
        def replace_after_install(source, destination, **kwargs):
            nonlocal raced
            real_link(source, destination, **kwargs)
            if not raced and Path(source).name.startswith("new-"):
                raced = True
                fd = os.open(destination, os.O_WRONLY | os.O_TRUNC, dir_fd=kwargs.get("dst_dir_fd"))
                with os.fdopen(fd, "wb") as handle:
                    handle.write(b"concurrent user edit\n")
        with mock.patch.object(TX.os, "link", side_effect=replace_after_install):
            with self.assertRaisesRegex(TX.TransactionError, "recovery evidence retained"):
                TX.publish(root, workspace, before, after, index, b"original index", copied, lock, lock_fd)
        self.assertEqual(target.read_bytes(), b"concurrent user edit\n")
        self.assertEqual(index.read_bytes(), b"original index")
        self.assertEqual((workspace / "prior-0").read_bytes(), b"old output\n")


if __name__ == "__main__":
    unittest.main()
