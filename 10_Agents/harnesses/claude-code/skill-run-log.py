#!/usr/bin/env python3
"""Append one skill-run line from a Claude Code PostToolUse payload (stdin).

Usage: skill-run-log.py <vault root> <vault-relative log path>
Never raises; exit 0 always — the hook must not block a session.
Line shape: <UTC timestamp>\t<harness>\t<skill>\t<outcome>

The log path is authenticated before anything is written: every component
below the vault root is opened relative to its parent with O_NOFOLLOW (a
symlink anywhere on the path — the file itself or a parent directory — is
refused), the opened object is verified with fstat to be a regular file
with a single link, and the line goes through that descriptor with append
semantics. There is no window between validation and the write: the
descriptor used for the write is the one that was validated. An unsafe
target is never created, mutated, or followed.
"""

import datetime
import json
import os
import stat
import sys


def _open_dir(name: str, dir_fd: int | None) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    return os.open(name, flags, dir_fd=dir_fd)


def _reparse_point(path: str) -> bool:
    """Windows: a junction or symlink shows as a reparse point on lstat."""
    try:
        info = os.lstat(path)
    except OSError:
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def open_log_nofollow(root: str, relative: str) -> int | None:
    """Descriptor for append, or None when any component is unsafe."""
    parts = [p for p in relative.replace("\\", "/").split("/") if p]
    if not parts or any(p in (".", "..") for p in parts):
        return None
    root = os.path.realpath(root)
    if not hasattr(os, "O_NOFOLLOW") or os.name == "nt":
        # No no-follow open primitive: refuse on any reparse point, then open
        # by full path. Best effort on this platform.
        current = root
        for part in parts:
            current = os.path.join(current, part)
            if _reparse_point(current):
                return None
        try:
            descriptor = os.open(current, os.O_WRONLY | os.O_APPEND)
        except OSError:
            return None
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                os.close(descriptor)
                return None
        except OSError:
            os.close(descriptor)
            return None
        return descriptor
    dir_fd = None
    try:
        dir_fd = _open_dir(root, None)
        for part in parts[:-1]:
            next_fd = _open_dir(part, dir_fd)
            os.close(dir_fd)
            dir_fd = next_fd
        flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(parts[-1], flags, dir_fd=dir_fd)
    except OSError:
        return None
    finally:
        if dir_fd is not None:
            try:
                os.close(dir_fd)
            except OSError:
                pass
    try:
        info = os.fstat(descriptor)
    except OSError:
        os.close(descriptor)
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        os.close(descriptor)
        return None
    return descriptor


def main() -> int:
    if len(sys.argv) != 3:
        return 0
    root, relative = sys.argv[1], sys.argv[2]
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Skill":
        return 0
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    skill = str(tool_input.get("skill") or tool_input.get("name") or "").strip()
    if not skill or any(ch.isspace() for ch in skill):
        return 0
    response = payload.get("tool_response")
    outcome = "ok"
    if isinstance(response, dict) and (response.get("is_error") or response.get("error")):
        outcome = "error"
    elif isinstance(response, str) and response.lstrip().lower().startswith("error"):
        outcome = "error"
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp}\tclaude-code\t{skill}\t{outcome}\n".encode("utf-8")
    descriptor = open_log_nofollow(root, relative)
    if descriptor is None:
        return 0
    try:
        os.write(descriptor, line)
    except OSError:
        pass
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
