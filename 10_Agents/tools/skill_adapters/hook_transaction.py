#!/usr/bin/env python3
"""Snapshot/restore generated working files and the raw Git index for hooks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


TRANSACTION_PREFIX = ".precommit-generated-transaction-"
GENERATED_PATHS = (
    "10_Agents/tools/brain/vault-index.json",
    ".vscode/second-brain.code-snippets",
    ".agents/skills",
    ".claude/skills",
)


class TransactionError(RuntimeError):
    pass


def _repo(raw: Path) -> Path:
    repo = raw.resolve()
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TransactionError(f"cannot resolve repository: {exc}") from exc
    if Path(proc.stdout.strip()).resolve() != repo:
        raise TransactionError("transaction repository is not the Git toplevel")
    return repo


def _safe_generated(repo: Path, rel: str, *, allow_absent: bool = True) -> Path:
    if rel not in GENERATED_PATHS:
        raise TransactionError(f"unexpected generated path in transaction: {rel!r}")
    pure = PurePosixPath(rel)
    current = repo
    for part in pure.parts[:-1]:
        current = current / part
        if not os.path.lexists(current):
            if allow_absent:
                return repo / rel
            raise TransactionError(f"missing generated-path ancestor: {current}")
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise TransactionError(f"unsafe generated-path ancestor: {current}")
    target = repo / rel
    if os.path.lexists(target) and target.is_symlink():
        raise TransactionError(f"symlinked generated path is unsafe: {rel}")
    return target


def _assert_regular_tree(path: Path) -> None:
    if path.is_symlink():
        raise TransactionError(f"symlink in generated snapshot source: {path}")
    if path.is_file():
        return
    if not path.is_dir():
        raise TransactionError(f"non-regular generated snapshot source: {path}")
    for parent, directories, files in os.walk(path, followlinks=False):
        parent_path = Path(parent)
        for name in [*directories, *files]:
            child = parent_path / name
            if child.is_symlink():
                raise TransactionError(f"symlink in generated snapshot source: {child}")
            if name in files and not child.is_file():
                raise TransactionError(f"non-regular generated snapshot source: {child}")


def _git_index(repo: Path) -> Path:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--git-path", "index"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TransactionError(f"cannot locate Git index: {exc}") from exc
    raw = Path(proc.stdout.strip())
    path = raw if raw.is_absolute() else repo / raw
    path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise TransactionError(f"Git index path is missing: {current}") from exc
        if stat.S_ISLNK(mode):
            raise TransactionError(f"symlinked Git index path is unsafe: {current}")
    if not path.is_file():
        raise TransactionError("Git index is non-regular")
    return path


def _write_json(path: Path, value: Any) -> None:
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def begin(repo: Path) -> Path:
    repo = _repo(repo)
    transaction = Path(tempfile.mkdtemp(prefix=TRANSACTION_PREFIX, dir=repo))
    snapshot_root = transaction / "working"
    snapshot_root.mkdir()
    try:
        index = _git_index(repo)
        index_snapshot = transaction / "git-index"
        shutil.copy2(index, index_snapshot)
        rows: list[dict[str, Any]] = []
        for number, rel in enumerate(GENERATED_PATHS):
            source = _safe_generated(repo, rel)
            row: dict[str, Any] = {"path": rel, "state": "absent"}
            if os.path.lexists(source):
                _assert_regular_tree(source)
                destination = snapshot_root / str(number)
                if source.is_file():
                    shutil.copy2(source, destination)
                    row["state"] = "file"
                else:
                    shutil.copytree(source, destination, copy_function=shutil.copy2)
                    row["state"] = "directory"
            rows.append(row)
        _write_json(
            transaction / "manifest.json",
            {
                "schemaVersion": 1,
                "gitIndex": str(index),
                "gitIndexMode": stat.S_IMODE(index.stat().st_mode),
                "paths": rows,
            },
        )
        return transaction
    except BaseException:
        shutil.rmtree(transaction, ignore_errors=True)
        raise


def _transaction(repo: Path, raw: Path) -> Path:
    repo = _repo(repo)
    transaction = raw.absolute()
    if (
        transaction.parent != repo
        or not transaction.name.startswith(TRANSACTION_PREFIX)
        or transaction.name == TRANSACTION_PREFIX
        or transaction.is_symlink()
        or not transaction.is_dir()
    ):
        raise TransactionError("unsafe or missing hook transaction")
    return transaction


def _load_manifest(transaction: Path) -> dict[str, Any]:
    path = transaction / "manifest.json"
    if path.is_symlink() or not path.is_file():
        raise TransactionError("hook transaction manifest is missing or unsafe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"cannot read hook transaction manifest: {exc}") from exc
    if (
        not isinstance(data, dict)
        or data.get("schemaVersion") != 1
        or not isinstance(data.get("paths"), list)
        or [row.get("path") for row in data["paths"] if isinstance(row, dict)]
        != list(GENERATED_PATHS)
    ):
        raise TransactionError("hook transaction manifest is malformed")
    return data


def _remove_generated(path: Path) -> None:
    if not os.path.lexists(path):
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        raise TransactionError(f"cannot replace non-regular generated path: {path}")


def _restore_index(repo: Path, transaction: Path, manifest: dict[str, Any]) -> None:
    current = _git_index(repo)
    recorded = Path(manifest.get("gitIndex", "")).absolute()
    if current != recorded:
        raise TransactionError("Git index location changed during hook transaction")
    snapshot = transaction / "git-index"
    if snapshot.is_symlink() or not snapshot.is_file():
        raise TransactionError("Git index snapshot is missing or unsafe")
    mode = manifest.get("gitIndexMode")
    if type(mode) is not int:
        raise TransactionError("Git index snapshot mode is malformed")
    fd, temp_name = tempfile.mkstemp(prefix=".index.precommit-restore-", dir=current.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(snapshot.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, current)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def restore(repo: Path, raw_transaction: Path) -> None:
    repo = _repo(repo)
    transaction = _transaction(repo, raw_transaction)
    manifest = _load_manifest(transaction)
    errors: list[str] = []
    try:
        _restore_index(repo, transaction, manifest)
    except BaseException as exc:
        errors.append(f"Git index: {exc}")
    for number, row in enumerate(manifest["paths"]):
        try:
            destination = _safe_generated(repo, row["path"])
            _remove_generated(destination)
            state = row.get("state")
            if state == "absent":
                continue
            snapshot = transaction / "working" / str(number)
            if snapshot.is_symlink() or not snapshot.exists():
                raise TransactionError(f"missing generated snapshot for {row['path']}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if state == "file" and not snapshot.is_file():
                raise TransactionError(f"wrong generated snapshot kind for {row['path']}")
            if state == "directory" and not snapshot.is_dir():
                raise TransactionError(f"wrong generated snapshot kind for {row['path']}")
            if state not in {"file", "directory"}:
                raise TransactionError(f"unknown generated snapshot state for {row['path']}")
            os.replace(snapshot, destination)
        except BaseException as exc:
            errors.append(f"{row.get('path')}: {exc}")
    if errors:
        raise TransactionError("hook rollback incomplete: " + "; ".join(errors))
    shutil.rmtree(transaction)


def discard(repo: Path, raw_transaction: Path) -> None:
    transaction = _transaction(_repo(repo), raw_transaction)
    _load_manifest(transaction)
    shutil.rmtree(transaction)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("begin", "restore", "discard"))
    parser.add_argument("repo", type=Path)
    parser.add_argument("transaction", type=Path, nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.action == "begin":
            if args.transaction is not None:
                raise TransactionError("begin does not accept a transaction path")
            print(begin(args.repo))
        else:
            if args.transaction is None:
                raise TransactionError(f"{args.action} requires a transaction path")
            (restore if args.action == "restore" else discard)(args.repo, args.transaction)
        return 0
    except TransactionError as exc:
        print(f"hook transaction: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
