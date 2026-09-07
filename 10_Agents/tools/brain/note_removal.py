"""Source-bound note removal with durable, non-clobbering crash recovery.

The CLI owns locking and destination publication. This module owns only the
source snapshot, its authenticated parent, and the removal recovery record.
Existing no-follow readers and platform no-replace renames are supplied by it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys


ReadSource = Callable[..., tuple[bytes, os.stat_result]]
RenameNoReplace = Callable[..., None]


class RemovalError(RuntimeError):
    pass


class RemovalConflict(RemovalError):
    pass


def _identity(info: os.stat_result) -> list[int]:
    return [info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)]


def _parents(root: Path, rel: str) -> list[list[int]]:
    current = root
    result = []
    for part in (None, *Path(rel).parts[:-1]):
        if part is not None:
            current /= part
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise RemovalError("source parent is not an authenticated directory")
        result.append(_identity(info))
    return result


def _record_name(rel: str) -> str:
    return ".brain-note-removal-" + hashlib.sha256(rel.encode()).hexdigest() + ".json"


def _parse_record(raw: bytes, rel: str, parents: list[list[int]]) -> dict:
    try:
        record = json.loads(raw)
        if (
            set(record) != {"schemaVersion", "source", "quarantine", "identity", "parents", "sha256"}
            or type(record["schemaVersion"]) is not int or record["schemaVersion"] != 1
            or record["source"] != rel or record["parents"] != parents
            or not isinstance(record["quarantine"], str)
            or re.fullmatch(r"\.brain-note-removal-[0-9a-f]{32}\.source", record["quarantine"]) is None
            or not isinstance(record["identity"], list) or len(record["identity"]) != 3
            or any(type(value) is not int for value in record["identity"])
            or record["identity"][2] != stat.S_IFREG
            or not isinstance(record["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None
        ):
            raise ValueError
        return record
    except (ValueError, TypeError, KeyError):
        raise RemovalError("note removal recovery required: unrecognized recovery record") from None


def read_source(root: Path, rel: str, read: ReadSource) -> tuple[bytes | None, dict | None]:
    """Read the original or its claimed recovery source, never a replacement."""
    parents = _parents(root, rel)
    record_rel = _record_name(rel)
    try:
        record_raw, _ = read(root, record_rel, max_bytes=8192)
    except FileNotFoundError:
        record_raw = None
    record = _parse_record(record_raw, rel, parents) if record_raw is not None else None
    source_rel = rel
    if record is not None:
        quarantine_rel = (Path(rel).parent / record["quarantine"]).as_posix()
        # lexists does not admit the file: the bound no-follow reader below
        # authenticates it, including dangling symlinks and parent redirects.
        if os.path.lexists(root / quarantine_rel):
            source_rel = quarantine_rel
    try:
        raw, info = read(root, source_rel)
    except FileNotFoundError:
        if record is not None:
            raise RemovalError("note removal recovery required: source and claim are absent") from None
        if _parents(root, rel) != parents:
            raise RemovalConflict("source parent changed during snapshot") from None
        return None, None
    state = {"identity": _identity(info), "parents": parents, "sha256": hashlib.sha256(raw).hexdigest()}
    if _parents(root, rel) != parents:
        raise RemovalConflict("source parent changed during snapshot")
    if record is not None and any(record[key] != state[key] for key in state):
        raise RemovalConflict("note removal recovery required: claimed source changed")
    return raw, state


def require_supported() -> None:
    if (
        os.name != "posix" or not (sys.platform == "darwin" or sys.platform.startswith("linux"))
        or not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0)
        or os.open not in os.supports_dir_fd or os.unlink not in os.supports_dir_fd
    ):
        raise RemovalError("safe note removal is unavailable on this platform; preview remains available")
    # A supported OS name alone does not establish the required libc API.
    import ctypes

    libc = ctypes.CDLL(None)
    if not hasattr(libc, "renameatx_np" if sys.platform == "darwin" else "renameat2"):
        raise RemovalError("safe note removal is unavailable on this platform; preview remains available")


def preflight(root: Path, rel: str, expected: dict, read: ReadSource) -> None:
    require_supported()
    _raw, current = read_source(root, rel, read)
    if current != expected:
        raise RemovalConflict("source changed since this plan was computed — recompute the plan and retry")


@contextlib.contextmanager
def _bound_parent(root: Path, rel: str, expected: list[list[int]]) -> Iterator[tuple[int, int, Callable[[], None]]]:
    descriptors = []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptors.append(os.open(root, flags))
        for part in Path(rel).parts[:-1]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))

        def verify():
            if [_identity(os.fstat(fd)) for fd in descriptors] != expected or _parents(root, rel) != expected:
                raise RemovalConflict("note removal recovery required: source parent changed")

        verify()
        yield descriptors[-1], descriptors[0], verify
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_at(parent: int, name: str, *, limit: int | None = None) -> tuple[bytes, list[int]]:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise RemovalError("note removal recovery required: non-regular evidence")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read() if limit is None else handle.read(limit + 1)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise RemovalConflict("note removal recovery required: evidence changed while reading")
        if limit is not None and len(raw) > limit:
            raise RemovalError("note removal recovery required: oversized record")
        return raw, _identity(after)
    finally:
        os.close(fd)


def _discard_record(parent: int, name: str, expected: bytes, identity: list[int], rename: RenameNoReplace) -> None:
    """Claim cleanup evidence too; never unlink an unrecognized public name."""
    claimed = ".brain-note-removal-" + secrets.token_hex(16) + ".cleanup"
    rename(parent, name, claimed)
    raw, found_identity = _read_at(parent, claimed, limit=8192)
    if raw != expected or found_identity != identity:
        try:
            rename(parent, claimed, name)
        except OSError:
            pass
        raise RemovalError("note removal recovery required: record replacement preserved")
    os.unlink(claimed, dir_fd=parent)
    os.fsync(parent)


def remove(root: Path, rel: str, expected: dict, read: ReadSource, rename: RenameNoReplace) -> None:
    preflight(root, rel, expected, read)
    with _bound_parent(root, rel, expected["parents"]) as (parent, record_parent, verify_parents):
        name = _record_name(rel)
        try:
            record_raw, record_identity = _read_at(record_parent, name, limit=8192)
        except FileNotFoundError:
            record = {
                "schemaVersion": 1, "source": rel, **expected,
                "quarantine": ".brain-note-removal-" + secrets.token_hex(16) + ".source",
            }
            record_raw = (json.dumps(record, sort_keys=True) + "\n").encode()
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=record_parent)
            try:
                with os.fdopen(fd, "wb", closefd=False) as handle:
                    handle.write(record_raw)
                    handle.flush()
                    os.fsync(fd)
                record_identity = _identity(os.fstat(fd))
            finally:
                os.close(fd)
            os.fsync(record_parent)
        record = _parse_record(record_raw, rel, expected["parents"])
        if any(record[key] != expected[key] for key in expected):
            raise RemovalConflict("note removal recovery required: record does not match source plan")
        quarantine = record["quarantine"]

        def verify() -> None:
            verify_parents()
            current_raw, current_identity = _read_at(record_parent, name, limit=8192)
            if current_raw != record_raw or current_identity != record_identity:
                raise RemovalConflict("note removal recovery required: record changed")

        verify()
        try:
            os.stat(quarantine, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            rename(parent, Path(rel).name, quarantine)
            os.fsync(parent)
        verify()
        raw, identity = _read_at(parent, quarantine)
        if identity != expected["identity"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            try:
                rename(parent, quarantine, Path(rel).name)
            except OSError:
                raise RemovalConflict("note removal recovery required: replacement and claim preserved") from None
            _discard_record(record_parent, name, record_raw, record_identity, rename)
            raise RemovalConflict("source changed while claiming removal — replacement restored")
        verify()
        # The random claim is tool-owned; a recreated original name is never
        # touched. Hard stops retain the record and claim for the next read.
        os.unlink(quarantine, dir_fd=parent)
        os.fsync(parent)
        _discard_record(record_parent, name, record_raw, record_identity, rename)
