#!/usr/bin/env python3
"""Build commit outputs from a staged snapshot; publish without losing other edits.

The live Git index is locked throughout. Generators and validation use a private
index/worktree, so failed checks never require restoring the user's staging.
Publication quarantines old generated files and installs with create-if-absent
links. Rollback removes only authenticated hook output and preserves collisions.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

TRANSACTION_PREFIX = ".precommit-generated-transaction-"
GENERATED_PATHS = (
    "00_Meta/BOOTSTRAP.md",
    "10_Agents/tools/brain/vault-index.json",
    ".vscode/second-brain.code-snippets",
    ".agents/skills",
    ".claude/skills",
)


class TransactionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FileState:
    body: bytes
    mode: int
    device: int
    inode: int


def state(path: Path | str, *, parent: int | None = None) -> FileState | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise TransactionError(f"non-regular generated file: {Path(path).name}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            body = handle.read()
        after = os.fstat(fd)
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise TransactionError("generated file changed while being read")
        return FileState(body, stat.S_IMODE(info.st_mode), info.st_dev, info.st_ino)
    finally:
        os.close(fd)


def safe_parent(root: Path, rel: str, *, create: bool = False) -> Path:
    current = root
    for part in Path(rel).parts[:-1]:
        current /= part
        if create:
            try:
                current.mkdir()
            except FileExistsError:
                pass
        if not current.exists() and not current.is_symlink():
            return root / rel
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise TransactionError(f"unsafe generated parent: {rel}")
    return root / rel


def adapter_module(root: Path):
    script = root / "10_Agents/tools/skill_adapters/gen_skill_adapters.py"
    if not script.is_file():
        return None
    name = "_commit_adapter_catalog_" + str(abs(hash(str(root))))
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def working_state(root: Path) -> dict[str, FileState]:
    adapters = adapter_module(root)
    files: dict[str, FileState] = {}
    for rel in GENERATED_PATHS:
        target = safe_parent(root, rel)
        if not os.path.lexists(target):
            continue
        if target.is_symlink():
            raise TransactionError(f"symlinked generated path: {rel}")
        paths = [target]
        if target.is_dir():
            if rel not in GENERATED_PATHS[3:]:
                raise TransactionError(f"non-regular generated path: {rel}")
            paths = []
            for parent, dirs, names in os.walk(target, followlinks=False):
                for name in dirs:
                    if (Path(parent) / name).is_symlink():
                        raise TransactionError(f"symlinked generated directory: {rel}")
                paths.extend(Path(parent) / name for name in names)
        for path in paths:
            item = state(path)
            if item is None:
                raise TransactionError("generated file disappeared while being read")
            relative = path.relative_to(root)
            if relative.parts[0] in (".agents", ".claude") and (
                adapters is None or not adapters._owned_adapter(path, relative)
            ):
                # Component-owned files are source content, never hook-owned
                # output. Their staged versions remain in the snapshot.
                continue
            files[relative.as_posix()] = item
    return files


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], env=env, capture_output=True
    )
    if proc.returncode:
        raise TransactionError(f"git {args[0]} failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def index_path(root: Path) -> Path:
    raw = Path(os.fsdecode(git(root, "rev-parse", "--git-path", "index")).strip())
    path = raw if raw.is_absolute() else root / raw
    if path.is_symlink() or not path.is_file():
        raise TransactionError("Git index is missing or unsafe")
    return path.absolute()


def export_index(root: Path, workspace: Path, original_index: Path, *, revision: str | None = None) -> tuple[Path, Path, dict[str, str]]:
    tree = workspace / "tree"
    tree.mkdir()
    copied_index = workspace / "staged-index"
    shutil.copy2(original_index, copied_index)
    git_dir = os.fsdecode(git(root, "rev-parse", "--absolute-git-dir")).strip()
    env = {
        **os.environ,
        "GIT_DIR": git_dir,
        "GIT_WORK_TREE": str(tree),
        "GIT_INDEX_FILE": str(copied_index),
        "GIT_OPTIONAL_LOCKS": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if revision is not None:
        git(root, "read-tree", revision, env=env)
    git(root, "checkout-index", "--all", "--ignore-skip-worktree-bits", f"--prefix={tree}/", env=env)
    # This is an existing explicit local selection, never an invented identity.
    selector = root / ".second-brain/environment"
    if revision is None and selector.is_file() and not selector.is_symlink():
        (tree / ".second-brain").mkdir(exist_ok=True)
        (tree / ".second-brain/environment").write_bytes(selector.read_bytes())
    return tree, copied_index, env


def command(tree: Path, env: dict[str, str], script: str, *args: str,
            allowed: tuple[int, ...] = (0,), message: str) -> None:
    proc = subprocess.run(["python3", str(tree / script), *args], cwd=tree, env=env,
                          stdout=subprocess.DEVNULL)
    if proc.returncode not in allowed:
        raise TransactionError(message)


def build(tree: Path, env: dict[str, str]) -> None:
    brain = "10_Agents/tools/brain/brain.py"
    adapters = "10_Agents/tools/skill_adapters/gen_skill_adapters.py"
    command(tree, env, brain, "bootstrap", "--write", message="brain bootstrap --write failed")
    command(tree, env, brain, "bootstrap", "--check", message="brain bootstrap --check failed")
    managed_before = set(working_state(tree))
    command(tree, env, brain, "index", "--shared-only", message="brain index failed")
    command(tree, env, "10_Agents/tools/vscode/gen_snippets.py", message="snippet generation failed")
    command(tree, env, adapters, message="skill-adapter generation failed")
    managed_after = set(working_state(tree))
    tracked = {os.fsdecode(path) for path in git(tree, "ls-files", "-z", env=env).split(b"\0") if path}
    staged_paths = sorted(managed_after | (managed_before & tracked))
    git(tree, "add", "--all", "--", *staged_paths, env=env)
    command(tree, env, brain, "validate", "--shared-only", allowed=(0, 2), message="brain validate found errors")
    command(tree, env, brain, "artifacts", "--check", "--shared-only",
            message="local artifacts are stale — run brain artifacts --write and stage them")


def same_output(a: FileState | None, b: FileState | None) -> bool:
    return a is not None and b is not None and (a.body, a.mode) == (b.body, b.mode)


class BoundParent:
    """Hold every ancestor; all publication/rollback operations use dir_fd."""
    def __init__(self, root: Path, rel: str):
        self.root = root
        self.name = Path(rel).name
        self.fds: list[int] = []
        self.edges: list[tuple[int, str, int]] = []
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            self.fds.append(os.open(root, flags))
            for part in Path(rel).parts[:-1]:
                parent = self.fds[-1]
                try:
                    os.mkdir(part, dir_fd=parent)
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=parent)
                self.fds.append(child)
                self.edges.append((parent, part, child))
            self.verify()
        except BaseException:
            self.close()
            raise

    @property
    def fd(self):
        return self.fds[-1]

    def verify(self):
        root_info, held = self.root.lstat(), os.fstat(self.fds[0])
        if not stat.S_ISDIR(root_info.st_mode) or (root_info.st_dev, root_info.st_ino) != (held.st_dev, held.st_ino):
            raise TransactionError("generated root changed during publication")
        for parent, name, child in self.edges:
            current, held = os.stat(name, dir_fd=parent, follow_symlinks=False), os.fstat(child)
            if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
                raise TransactionError("generated parent changed during publication")

    def close(self):
        for fd in reversed(self.fds):
            os.close(fd)
        self.fds.clear()


@dataclass
class Published:
    rel: str
    prior: FileState | None
    backup: Path
    parent: BoundParent
    installed: FileState | None = None


def restore_one(recovery_fd: int, row: Published) -> None:
    parent, name = row.parent.fd, row.parent.name
    current = state(name, parent=parent)
    if row.installed is not None and current is not None:
        # The rename uses the held parent even if its public path was replaced.
        displaced = row.backup.name + ".rollback-current"
        os.rename(name, displaced, src_dir_fd=parent, dst_dir_fd=recovery_fd)
        captured = state(displaced, parent=recovery_fd)
        if captured == row.installed:
            os.unlink(displaced, dir_fd=recovery_fd)
        else:
            try:
                os.link(displaced, name, src_dir_fd=recovery_fd, dst_dir_fd=parent, follow_symlinks=False)
            except FileExistsError:
                pass
            raise TransactionError(f"concurrent generated edit preserved: {row.rel}")
    if state(row.backup.name, parent=recovery_fd) is not None:
        try:
            os.link(row.backup.name, name, src_dir_fd=recovery_fd, dst_dir_fd=parent, follow_symlinks=False)
        except FileExistsError:
            raise TransactionError(f"concurrent generated edit preserved: {row.rel}") from None
        os.unlink(row.backup.name, dir_fd=recovery_fd)


@contextlib.contextmanager
def deferred_signals():
    watched = {signal.SIGINT, signal.SIGTERM, signal.SIGHUP}
    prior = signal.pthread_sigmask(signal.SIG_BLOCK, watched)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, prior)


def publish(root: Path, workspace: Path, before: dict[str, FileState],
            after: dict[str, FileState], index: Path, initial_index: bytes,
            copied_index: Path, lock: Path, lock_fd: int) -> None:
    if working_state(root) != before or index.read_bytes() != initial_index:
        raise TransactionError("Git index or generated files changed during validation; preserved without publication")
    rows: list[Published] = []
    recovery_fd = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    committed = False
    try:
        for number, rel in enumerate(sorted(before.keys() | after.keys())):
            prior, desired = before.get(rel), after.get(rel)
            if same_output(prior, desired):
                continue
            parent = BoundParent(root, rel)
            row = Published(rel, prior, workspace / f"prior-{number}", parent)
            rows.append(row)
            if prior is not None:
                os.rename(parent.name, row.backup.name, src_dir_fd=parent.fd, dst_dir_fd=recovery_fd)
                if state(row.backup.name, parent=recovery_fd) != prior:
                    raise TransactionError(f"generated file changed before publication: {rel}")
            if desired is not None:
                staged = f"new-{number}"
                fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, desired.mode, dir_fd=recovery_fd)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(desired.body)
                    handle.flush()
                    os.fchmod(handle.fileno(), desired.mode)
                    os.fsync(handle.fileno())
                # Record ownership BEFORE linking so caught interruption between
                # link and the next Python instruction can still undo our output.
                row.installed = state(staged, parent=recovery_fd)
                os.link(staged, parent.name, src_dir_fd=recovery_fd, dst_dir_fd=parent.fd, follow_symlinks=False)
                os.unlink(staged, dir_fd=recovery_fd)
            parent.verify()
        expected = dict(before)
        for row in rows:
            if row.installed is None:
                expected.pop(row.rel, None)
            else:
                expected[row.rel] = row.installed
        for row in rows:
            row.parent.verify()
            if row.prior is not None and state(row.backup.name, parent=recovery_fd) != row.prior:
                raise TransactionError("a quarantined generated file changed during publication")
        if working_state(root) != expected or index.read_bytes() != initial_index:
            raise TransactionError("Git index or generated files changed before commit; concurrent edits preserved")
        with os.fdopen(os.dup(lock_fd), "wb") as handle:
            handle.write(copied_index.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        with deferred_signals():
            os.replace(lock, index)
            committed = True
    except BaseException:
        if not committed:
            errors = []
            for row in reversed(rows):
                try:
                    restore_one(recovery_fd, row)
                except (OSError, TransactionError) as exc:
                    errors.append(str(exc))
            if errors:
                raise TransactionError("; ".join(errors) + f"; recovery evidence retained at {workspace}") from None
        raise
    finally:
        for row in rows:
            row.parent.close()
        os.close(recovery_fd)


def run(root: Path) -> None:
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(signal, "pthread_sigmask"):
        raise TransactionError("safe commit publication requires a POSIX runtime")
    root = root.resolve()
    if Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve() != root:
        raise TransactionError("hook root is not the Git worktree")
    # Authenticate live ownership before constructing or staging anything.
    command(root, os.environ.copy(), "10_Agents/tools/skill_adapters/gen_skill_adapters.py",
            "--preflight", message="skill-adapter preflight failed")
    before = working_state(root)
    index = index_path(root)
    lock = Path(str(index) + ".lock")
    workspace: Path | None = None
    keep_recovery = False
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise TransactionError("Git index is locked by another writer; retry after it finishes") from None
    try:
        os.fchmod(lock_fd, stat.S_IMODE(index.stat().st_mode))
        workspace = Path(tempfile.mkdtemp(prefix=TRANSACTION_PREFIX, dir=root))
        initial_index = index.read_bytes()
        tree, copied_index, env = export_index(root, workspace, index)
        # Generated files are rebuilt from staged canonical inputs. Use the
        # authenticated live ownership inventory rather than possibly staged
        # hand-edits to generated files when bootstrapping the generator.
        for rel in set(GENERATED_PATHS[:3]) | set(before):
            target = safe_parent(tree, rel)
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                raise TransactionError(f"non-regular staged generated path: {rel}")
        for rel, item in before.items():
            target = tree / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.body)
            target.chmod(item.mode)
        build(tree, env)
        after = working_state(tree)
        try:
            publish(root, workspace, before, after, index, initial_index, copied_index, lock, lock_fd)
        except TransactionError as exc:
            keep_recovery = "recovery evidence retained" in str(exc)
            raise
    finally:
        try:
            lock_identity = os.fstat(lock_fd)
            info = lock.lstat()
            if (info.st_dev, info.st_ino) == (lock_identity.st_dev, lock_identity.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass
        finally:
            os.close(lock_fd)
            if workspace is not None and not keep_recovery:
                shutil.rmtree(workspace)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    try:
        run(args.repo)
    except (OSError, TransactionError, KeyboardInterrupt) as exc:
        print(f"pre-commit: {exc} — commit aborted", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
