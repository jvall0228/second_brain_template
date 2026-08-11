#!/usr/bin/env python3
"""Atomic seeded-example cleanup planning and application (issue #84)."""

from __future__ import annotations

import hashlib
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path, PurePosixPath
from typing import Any


PLAN_SCHEMA_VERSION = 1
MANIFEST_REL = "10_Agents/tools/adopt_examples.json"
BRAIN_REL = "10_Agents/tools/brain/brain.py"
VAULT_INDEX_REL = "10_Agents/tools/brain/vault-index.json"
LOCK_REL = ".adopt-cleanup.lock"
TRANSACTION_PREFIX = ".adopt-transaction-"


class AdoptionError(RuntimeError):
    """A cleanup preflight, transaction, or validation failure."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def safe_rel(raw: str, *, directory: bool | None = None) -> str:
    if (
        not isinstance(raw, str)
        or not raw
        or "\\" in raw
        or ":" in raw
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
    ):
        raise AdoptionError(f"unsafe manifest path: {raw!r}")
    trailing = raw.endswith("/")
    value = raw[:-1] if trailing else raw
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise AdoptionError(f"unsafe manifest path: {raw!r}")
    if value != pure.as_posix():
        raise AdoptionError(f"non-canonical manifest path: {raw!r}")
    if any(part.startswith(".") for part in pure.parts):
        raise AdoptionError(f"dot-paths cannot be adoption targets: {raw!r}")
    if directory is True and not trailing:
        raise AdoptionError(f"directory adoption target must end in '/': {raw!r}")
    if directory is False and trailing:
        raise AdoptionError(f"file adoption target cannot end in '/': {raw!r}")
    return pure.as_posix()


def _check_no_overlap(paths: list[str]) -> None:
    folded: dict[str, str] = {}
    pure_paths: list[tuple[str, PurePosixPath]] = []
    for raw in paths:
        value = safe_rel(raw)
        key = value.casefold()
        if key in folded:
            raise AdoptionError(f"duplicate or case-colliding adoption targets: {folded[key]!r}, {raw!r}")
        folded[key] = raw
        pure_paths.append((raw, PurePosixPath(value)))
    for i, (left_raw, left) in enumerate(pure_paths):
        for right_raw, right in pure_paths[i + 1 :]:
            if left in right.parents or right in left.parents:
                raise AdoptionError(f"overlapping adoption targets: {left_raw!r}, {right_raw!r}")


def load_manifest(repo: Path) -> tuple[dict[str, Any], bytes]:
    path = repo / MANIFEST_REL
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdoptionError(f"cannot read {MANIFEST_REL}: {exc}") from exc
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data.get("schema_version") != 1
    ):
        raise AdoptionError(f"{MANIFEST_REL}: unsupported or missing schema_version")
    delete = data.get("delete")
    marker = data.get("cleanup_marker")
    bundle = data.get("bundle")
    if not isinstance(bundle, str) or not bundle.strip():
        raise AdoptionError(f"{MANIFEST_REL}: bundle must be a non-empty string")
    if not isinstance(delete, list) or not delete or not all(isinstance(item, str) for item in delete):
        raise AdoptionError(f"{MANIFEST_REL}: delete must be a non-empty string list")
    if not isinstance(marker, str) or not marker.strip():
        raise AdoptionError(f"{MANIFEST_REL}: cleanup_marker must be a non-empty string")
    _check_no_overlap(delete)
    return data, raw


def safe_existing(repo: Path, raw: str, *, expected_kind: str | None = None) -> Path:
    rel = safe_rel(raw, directory=(expected_kind == "directory") if expected_kind else None)
    path = repo / rel
    current = repo
    for part in PurePosixPath(rel).parts:
        try:
            names = os.listdir(current)
        except OSError as exc:
            raise AdoptionError(f"cannot inspect adoption path component for {raw}: {exc}") from exc
        folded = [name for name in names if name.casefold() == part.casefold()]
        if len(folded) > 1:
            raise AdoptionError(f"case-colliding adoption path component for {raw}: {folded}")
        if part not in names:
            if folded:
                raise AdoptionError(
                    f"case-mismatched adoption path component for {raw}: expected {part!r}, found {folded[0]!r}"
                )
            raise AdoptionError(f"missing expected adoption target: {raw}")
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise AdoptionError(f"missing expected adoption target: {raw}") from exc
        if stat.S_ISLNK(mode):
            raise AdoptionError(f"symlinked adoption path is unsafe: {raw}")
    if expected_kind == "directory" and not path.is_dir():
        raise AdoptionError(f"expected directory adoption target: {raw}")
    if expected_kind == "file" and not path.is_file():
        raise AdoptionError(f"expected file adoption target: {raw}")
    return path


def _open_bound_path(path: Path) -> tuple[int, os.stat_result]:
    """Open an absolute path component-by-component without following links."""
    path = path.absolute()
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path.anchor, directory_flags)
    try:
        for number, part in enumerate(path.parts[1:], 1):
            names = os.listdir(fd)
            folded = [name for name in names if name.casefold() == part.casefold()]
            if part not in names:
                if folded:
                    raise AdoptionError(f"case-mismatched bound path component: {part!r}")
                raise AdoptionError(f"missing bound path component: {part!r}")
            before = os.stat(part, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                raise AdoptionError(f"symlinked bound path component: {part!r}")
            final = number == len(path.parts) - 1
            flags = os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0)
            if not final:
                flags |= getattr(os, "O_DIRECTORY", 0)
            next_fd = os.open(part, flags, dir_fd=fd)
            after = os.fstat(next_fd)
            if (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode)) != (
                after.st_dev,
                after.st_ino,
                stat.S_IFMT(after.st_mode),
            ):
                os.close(next_fd)
                raise AdoptionError(f"bound path component changed while opening: {part!r}")
            os.close(fd)
            fd = next_fd
        return fd, os.fstat(fd)
    except BaseException:
        os.close(fd)
        raise


def _read_regular_fd(fd: int, *, label: str) -> bytes:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise AdoptionError(f"non-regular bound file: {label}")
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _inventory_directory(fd: int, prefix: str, rows: list[dict[str, str]]) -> None:
    names = os.listdir(fd)
    folded: dict[str, str] = {}
    for name in names:
        key = name.casefold()
        if key in folded:
            raise AdoptionError(
                f"case collision inside adoption target: {prefix}{folded[key]} and {prefix}{name}"
            )
        folded[key] = name
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    for name in sorted(names):
        rel = f"{prefix}{name}"
        metadata = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow,
                dir_fd=fd,
            )
            try:
                opened = os.fstat(child_fd)
                if (metadata.st_dev, metadata.st_ino) != (opened.st_dev, opened.st_ino):
                    raise AdoptionError(f"adoption directory changed while opening: {rel}")
                rows.append({"path": rel + "/", "kind": "directory"})
                _inventory_directory(child_fd, rel + "/", rows)
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(metadata.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | nofollow,
                dir_fd=fd,
            )
            try:
                opened = os.fstat(child_fd)
                if (metadata.st_dev, metadata.st_ino) != (opened.st_dev, opened.st_ino):
                    raise AdoptionError(f"adoption file changed while opening: {rel}")
                rows.append(
                    {
                        "path": rel,
                        "kind": "file",
                        "sha256": sha256_bytes(_read_regular_fd(child_fd, label=rel)),
                    }
                )
            finally:
                os.close(child_fd)
        elif stat.S_ISLNK(metadata.st_mode):
            raise AdoptionError(f"symlink inside adoption target: {rel}")
        else:
            raise AdoptionError(f"non-regular file inside adoption target: {rel}")


def inventory_target(path: Path, *, expected_kind: str | None = None) -> list[dict[str, str]]:
    try:
        fd, metadata = _open_bound_path(path)
        try:
            if stat.S_ISREG(metadata.st_mode):
                if expected_kind == "directory":
                    raise AdoptionError(f"expected directory adoption target: {path.name}")
                return [
                    {
                        "path": path.name,
                        "kind": "file",
                        "sha256": sha256_bytes(_read_regular_fd(fd, label=path.name)),
                    }
                ]
            if not stat.S_ISDIR(metadata.st_mode):
                raise AdoptionError(f"non-regular adoption target: {path.name}")
            if expected_kind == "file":
                raise AdoptionError(f"expected file adoption target: {path.name}")
            rows: list[dict[str, str]] = []
            _inventory_directory(fd, "", rows)
            return rows
        finally:
            os.close(fd)
    except AdoptionError as exc:
        detail = str(exc)
        if detail.startswith("missing bound path component"):
            raise AdoptionError(f"missing expected adoption target: {path}") from exc
        if detail.startswith("symlinked bound path component"):
            raise AdoptionError(f"symlinked adoption path is unsafe: {path}") from exc
        if detail.startswith("case-mismatched bound path component"):
            raise AdoptionError(f"case-mismatched adoption path component: {path}") from exc
        raise
    except OSError as exc:
        raise AdoptionError(f"cannot securely inventory adoption target {path.name}: {exc}") from exc


def hash_target(path: Path) -> str:
    if path.is_file():
        return inventory_target(path)[0]["sha256"]
    return sha256_bytes(canonical_json(inventory_target(path)))


def _git_probe(repo: Path) -> bool:
    marker = repo / ".git"
    marker_present = os.path.lexists(marker)
    if marker.is_symlink():
        raise AdoptionError("symlinked .git metadata is unsafe; refusing mutation")
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        if marker_present:
            raise AdoptionError(f"git metadata exists but git cannot inspect adoption state: {exc}") from exc
        return False
    if proc.returncode != 0:
        if marker_present or "not a git repository" not in proc.stderr.lower():
            raise AdoptionError(
                "cannot determine git worktree state: "
                + (proc.stderr.strip() or f"git exited {proc.returncode}")
            )
        return False
    if proc.stdout.strip() != "true":
        raise AdoptionError("git did not confirm an inside-work-tree state")
    return True


def _refuse_untracked_delete_occupants(repo: Path, rows: list[dict[str, Any]]) -> None:
    if not _git_probe(repo):
        return
    pathspecs = [row["path"] for row in rows]
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--", *pathspecs],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AdoptionError(f"cannot classify adoption targets with git: {exc}") from exc
    tracked = {item.decode("utf-8") for item in proc.stdout.split(b"\0") if item}
    foreign: list[str] = []
    for row in rows:
        if row["kind"] == "file":
            if row["path"] not in tracked:
                foreign.append(row["path"])
            continue
        prefix = row["path"].rstrip("/") + "/"
        contents = row.get("contents", [])
        if not contents:
            foreign.append(prefix + "<empty-directory>")
        for item in contents:
            full = prefix + item["path"].rstrip("/")
            if item["kind"] == "file":
                if full not in tracked:
                    foreign.append(full)
            elif not any(path == full or path.startswith(full + "/") for path in tracked):
                foreign.append(full + "/")
    if foreign:
        raise AdoptionError(
            "refusing ignored or untracked occupants inside adoption targets:\n  "
            + "\n  ".join(sorted(set(foreign)))
        )


def _read_bound_file(repo: Path, rel: str) -> bytes:
    try:
        fd, _ = _open_bound_path(repo / safe_rel(rel))
        try:
            return _read_regular_fd(fd, label=rel)
        finally:
            os.close(fd)
    except AdoptionError:
        raise
    except OSError as exc:
        raise AdoptionError(f"cannot securely read {rel}: {exc}") from exc


def _load_brain(
    repo: Path, *, source: bytes | None = None, expected_sha256: str | None = None
):
    source = _read_bound_file(repo, BRAIN_REL) if source is None else source
    digest = sha256_bytes(source)
    if expected_sha256 is not None and digest != expected_sha256:
        raise AdoptionError(f"stale cleanup plan: dependency changed during apply: {BRAIN_REL}")
    module_name = (
        f"adopt_brain_{sha256_bytes(str(repo).encode())[:12]}_{digest[:12]}"
    )
    module = types.ModuleType(module_name)
    module.__file__ = str(repo / BRAIN_REL)
    module.__package__ = ""
    sys.modules[module_name] = module
    try:
        code = compile(source, module.__file__, "exec")
        exec(code, module.__dict__)
    except Exception as exc:  # the checked-in brain tool is a required boundary
        if sys.modules.get(module_name) is module:
            del sys.modules[module_name]
        raise AdoptionError(f"cannot import {BRAIN_REL}: {exc}") from exc
    return module


def _deleted_notes(repo: Path, delete_rows: list[dict[str, Any]]) -> set[str]:
    notes: set[str] = set()
    for row in delete_rows:
        if row["kind"] == "file" and Path(row["path"]).suffix == ".md":
            notes.add(row["path"])
        elif row["kind"] == "directory":
            prefix = row["path"].rstrip("/") + "/"
            notes.update(
                prefix + item["path"]
                for item in row.get("contents", [])
                if item["kind"] == "file" and item["path"].endswith(".md")
            )
    return notes


def _line_bytes(lines: list[bytes], line_number: int) -> bytes:
    try:
        return lines[line_number - 1]
    except IndexError as exc:
        raise AdoptionError(f"link index reported nonexistent line {line_number}") from exc


def build_plan(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    manifest, manifest_raw = load_manifest(repo)
    delete_rows: list[dict[str, Any]] = []
    for raw in manifest["delete"]:
        kind = "directory" if raw.endswith("/") else "file"
        normalized = safe_rel(raw, directory=(kind == "directory"))
        path = repo / normalized
        row: dict[str, Any] = {"path": normalized, "kind": kind}
        if kind == "directory":
            contents = inventory_target(path, expected_kind=kind)
            row["contents"] = contents
            row["sha256"] = sha256_bytes(canonical_json(contents))
        else:
            row["sha256"] = inventory_target(path, expected_kind=kind)[0]["sha256"]
        delete_rows.append(row)

    # The manifest owns the bundle paths, but it may never implicitly claim
    # ignored or untracked material that happens to live beneath one of them.
    # This runs while the complete directory inventory is still available, so
    # the preview enumerates and authenticates everything deletion would move.
    _refuse_untracked_delete_occupants(repo, delete_rows)

    deleted_notes = _deleted_notes(repo, delete_rows)
    brain_source = _read_bound_file(repo, BRAIN_REL)
    brain_sha256 = sha256_bytes(brain_source)
    brain = _load_brain(repo, source=brain_source)
    notes, assets = brain.walk_corpus(repo)
    # The brain index follows regular file reads; reject symlinked note paths
    # first so a preview can never read through the clone boundary.
    for rel in notes:
        safe_existing(repo, rel, expected_kind="file")
    index = brain.build_index(repo, notes, assets)
    marker = manifest["cleanup_marker"].casefold()
    remove_by_file: dict[str, set[int]] = {}
    unmarked: list[str] = []
    for rel, record in index["notes"].items():
        if rel in deleted_notes:
            continue
        raw_lines = (repo / rel).read_bytes().splitlines(keepends=True)
        for link in record["links"]:
            if link.get("resolved") not in deleted_notes:
                continue
            line_number = int(link["line"])
            line = _line_bytes(raw_lines, line_number)
            try:
                decoded = line.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise AdoptionError(f"cannot inspect cleanup line {rel}:{line_number}: {exc}") from exc
            if marker in decoded.casefold():
                remove_by_file.setdefault(rel, set()).add(line_number)
            else:
                unmarked.append(f"{rel}:{line_number}:{link['raw']}")
    if unmarked:
        raise AdoptionError(
            "unmarked surviving references to seeded examples:\n  " + "\n  ".join(sorted(unmarked))
        )

    edit_rows: list[dict[str, Any]] = []
    for rel in sorted(remove_by_file):
        path = safe_existing(repo, rel, expected_kind="file")
        source = path.read_bytes()
        lines = source.splitlines(keepends=True)
        remove_lines = sorted(remove_by_file[rel])
        restricted = brain.is_restricted(index["notes"][rel])
        desired = b"".join(line for number, line in enumerate(lines, 1) if number not in remove_by_file[rel])
        edit_rows.append(
            {
                "path": rel,
                "sha256": sha256_bytes(source),
                "desiredSha256": sha256_bytes(desired),
                "removeLines": [
                    {
                        "line": number,
                        "sha256": sha256_bytes(_line_bytes(lines, number)),
                        "restricted": restricted,
                        "text": None
                        if restricted
                        else _line_bytes(lines, number).decode("utf-8").rstrip("\r\n"),
                    }
                    for number in remove_lines
                ],
            }
        )

    body: dict[str, Any] = {
        "schemaVersion": PLAN_SCHEMA_VERSION,
        "bundle": manifest.get("bundle", "seeded-examples"),
        "manifest": MANIFEST_REL,
        "manifestSha256": sha256_bytes(manifest_raw),
        "dependencies": [
            {
                "path": BRAIN_REL,
                "sha256": brain_sha256,
            }
        ],
        "delete": delete_rows,
        "edits": edit_rows,
        "regenerate": [],
    }
    index_path = safe_existing(repo, VAULT_INDEX_REL, expected_kind="file")
    body["regenerate"].append(
        {
            "path": VAULT_INDEX_REL,
            "sha256": sha256_bytes(index_path.read_bytes()),
            "mode": stat.S_IMODE(index_path.stat().st_mode),
        }
    )
    body["planId"] = sha256_bytes(canonical_json(body))
    return body


def _planned_paths(plan: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    try:
        for row in plan["delete"]:
            paths.append(safe_rel(row["path"]))
        for row in plan["edits"]:
            paths.append(safe_rel(row["path"]))
        for row in plan["regenerate"]:
            paths.append(safe_rel(row["path"]))
        for row in plan["dependencies"]:
            paths.append(safe_rel(row["path"]))
        paths.append(safe_rel(plan["manifest"]))
    except (KeyError, TypeError) as exc:
        raise AdoptionError(f"malformed cleanup plan: {exc}") from exc
    return sorted(set(paths))


def dirty_planned_paths(repo: Path, plan: dict[str, Any]) -> list[str]:
    if not _git_probe(repo):
        return []
    paths = _planned_paths(plan)
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all", "--", *paths],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AdoptionError(f"cannot inspect planned paths with git: {exc}") from exc
    return [line for line in proc.stdout.splitlines() if line]


def _validate_plan_shape(plan: Any) -> dict[str, Any]:
    if (
        not isinstance(plan, dict)
        or type(plan.get("schemaVersion")) is not int
        or plan.get("schemaVersion") != PLAN_SCHEMA_VERSION
    ):
        raise AdoptionError("unsupported or malformed cleanup plan")
    supplied_id = plan.get("planId")
    without_id = {key: value for key, value in plan.items() if key != "planId"}
    if not isinstance(supplied_id, str) or supplied_id != sha256_bytes(canonical_json(without_id)):
        raise AdoptionError("cleanup plan ID does not match its contents")
    _planned_paths(plan)
    return plan


def _desired_edit(repo: Path, row: dict[str, Any]) -> bytes:
    path = safe_existing(repo, row["path"], expected_kind="file")
    source = path.read_bytes()
    if sha256_bytes(source) != row.get("sha256"):
        raise AdoptionError(f"stale cleanup plan: changed edit source {row['path']}")
    lines = source.splitlines(keepends=True)
    remove: set[int] = set()
    for line_row in row.get("removeLines", []):
        number = line_row.get("line")
        if type(number) is not int or number < 1 or number in remove:
            raise AdoptionError(f"malformed cleanup line selection in {row['path']}")
        if sha256_bytes(_line_bytes(lines, number)) != line_row.get("sha256"):
            raise AdoptionError(f"stale cleanup plan: changed line {row['path']}:{number}")
        remove.add(number)
    desired = b"".join(line for number, line in enumerate(lines, 1) if number not in remove)
    if sha256_bytes(desired) != row.get("desiredSha256"):
        raise AdoptionError(f"cleanup plan desired hash mismatch for {row['path']}")
    return desired


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.adopt-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, stat.S_IMODE(mode))
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _plan_brain_sha256(plan: dict[str, Any]) -> str:
    matches = [row for row in plan["dependencies"] if row.get("path") == BRAIN_REL]
    if len(matches) != 1 or not isinstance(matches[0].get("sha256"), str):
        raise AdoptionError(f"cleanup plan must bind exactly one {BRAIN_REL} dependency")
    return matches[0]["sha256"]


def _trusted_index_bytes(repo: Path, expected_brain_sha256: str | None = None) -> bytes:
    loaded = _load_brain(repo, expected_sha256=expected_brain_sha256)
    notes, assets = loaded.index_corpus(repo)
    return loaded.serialize(loaded.reduce_restricted(loaded.build_index(repo, notes, assets)))


def _post_apply_validate(repo: Path, marker: str, plan: dict[str, Any]) -> None:
    brain_sha256 = _plan_brain_sha256(plan)
    _verify_plan_dependencies(repo, plan)
    expected_index = _trusted_index_bytes(repo, brain_sha256)
    regenerate = [row for row in plan["regenerate"] if row.get("path") == VAULT_INDEX_REL]
    if len(regenerate) != 1 or type(regenerate[0].get("mode")) is not int:
        raise AdoptionError(f"cleanup plan must bind exactly one {VAULT_INDEX_REL} output")
    _atomic_write(repo / VAULT_INDEX_REL, expected_index, regenerate[0]["mode"])

    _verify_plan_dependencies(repo, plan)
    actual_index = _read_bound_file(repo, VAULT_INDEX_REL)
    if actual_index != expected_index:
        raise AdoptionError(
            "post-apply vault index differs from an independent trusted computation"
        )

    # A surviving marker line that still carries a link means cleanup was partial.
    loaded = _load_brain(repo, expected_sha256=brain_sha256)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        validation_code = loaded.main(["validate", "--vault", str(repo)])
    if validation_code not in {0, 2}:
        raise AdoptionError(
            f"post-apply brain validate failed:\n{stdout.getvalue()}{stderr.getvalue()}"
        )
    _verify_plan_dependencies(repo, plan)
    notes, assets = loaded.walk_corpus(repo)
    for rel in notes:
        safe_existing(repo, rel, expected_kind="file")
    index = loaded.build_index(repo, notes, assets)
    offenders: list[str] = []
    for rel, record in index["notes"].items():
        if not record["links"]:
            continue
        lines = (repo / rel).read_text(encoding="utf-8").splitlines()
        for link in record["links"]:
            number = int(link["line"])
            if marker.casefold() in lines[number - 1].casefold():
                offenders.append(f"{rel}:{number}")
    if offenders:
        raise AdoptionError("post-apply cleanup markers still carry links: " + ", ".join(offenders))


def _target_matches(path: Path, row: dict[str, Any]) -> bool:
    if not os.path.lexists(path) or path.is_symlink():
        return False
    if row.get("kind") == "directory":
        contents = inventory_target(path)
        return contents == row.get("contents") and sha256_bytes(canonical_json(contents)) == row.get("sha256")
    contents = inventory_target(path)
    return len(contents) == 1 and contents[0]["sha256"] == row.get("sha256")


def _write_journal(transaction: Path, journal: dict[str, Any]) -> None:
    journal["updatedAt"] = int(time.time())
    _atomic_write(transaction / "journal.json", canonical_json(journal), 0o600)


def _transaction_path(repo: Path, name: Any) -> Path:
    if (
        not isinstance(name, str)
        or not name.startswith(TRANSACTION_PREFIX)
        or "/" in name
        or "\\" in name
        or name in {TRANSACTION_PREFIX, ".", ".."}
    ):
        raise AdoptionError("cleanup lock names an unsafe transaction")
    path = repo / name
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise AdoptionError("cleanup transaction path is unsafe")
    return path


def _read_journal(transaction: Path) -> dict[str, Any]:
    path = transaction / "journal.json"
    if path.is_symlink() or not path.is_file():
        raise AdoptionError("cleanup recovery journal is missing or unsafe")
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdoptionError(f"cannot read cleanup recovery journal: {exc}") from exc
    if (
        not isinstance(journal, dict)
        or journal.get("schemaVersion") != 1
        or not isinstance(journal.get("operations"), list)
    ):
        raise AdoptionError("cleanup recovery journal is malformed")
    return journal


def _read_lock(repo: Path) -> dict[str, Any]:
    path = repo / LOCK_REL
    if path.is_symlink() or not path.is_file():
        raise AdoptionError("cleanup lock is missing or unsafe")
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdoptionError(f"cannot read cleanup lock: {exc}") from exc
    if not isinstance(lock, dict) or lock.get("schemaVersion") != 1:
        raise AdoptionError("cleanup lock is malformed")
    _transaction_path(repo, lock.get("transaction"))
    return lock


def _acquire_lock(repo: Path, plan: dict[str, Any], transaction: Path) -> None:
    lock_path = repo / LOCK_REL
    payload = canonical_json(
        {
            "schemaVersion": 1,
            "planId": plan["planId"],
            "transaction": transaction.name,
            "createdAt": int(time.time()),
            "status": "active",
        }
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock_path, flags, 0o600)
    except FileExistsError as exc:
        raise AdoptionError(
            f"cleanup lock exists at {LOCK_REL}; run adopt_check.py recover before applying"
        ) from exc
    except OSError as exc:
        raise AdoptionError(f"cannot acquire cleanup lock: {exc}") from exc
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_lock(repo: Path, transaction: Path) -> None:
    lock = _read_lock(repo)
    if lock.get("transaction") != transaction.name:
        raise AdoptionError("cleanup lock changed during transaction; refusing to remove it")
    (repo / LOCK_REL).unlink()


def _set_lock_status(repo: Path, transaction: Path, status_value: str) -> None:
    lock = _read_lock(repo)
    if lock.get("transaction") != transaction.name:
        raise AdoptionError("cleanup lock changed during transaction")
    lock["status"] = status_value
    _atomic_write(repo / LOCK_REL, canonical_json(lock), 0o600)


def _cleanup_safe_orphans(repo: Path) -> None:
    """Remove only provably non-mutating or completed lockless journals."""
    if os.path.lexists(repo / LOCK_REL):
        return
    for candidate in sorted(repo.glob(f"{TRANSACTION_PREFIX}*")):
        transaction = _transaction_path(repo, candidate.name)
        journal = _read_journal(transaction)
        states = {operation.get("state") for operation in journal["operations"]}
        backups = transaction / "backups"
        has_backups = backups.is_dir() and any(backups.iterdir())
        if journal.get("status") in {"committed", "rolled-back"} or (
            journal.get("status") == "preparing"
            and states <= {"pending"}
            and not has_backups
        ):
            shutil.rmtree(transaction)
            continue
        raise AdoptionError(
            f"orphaned cleanup transaction {candidate.name} is not provably safe; manual recovery required"
        )


def _verify_plan_dependencies(repo: Path, plan: dict[str, Any]) -> None:
    if sha256_bytes(_read_bound_file(repo, plan["manifest"])) != plan.get("manifestSha256"):
        raise AdoptionError("stale cleanup plan: manifest changed during apply")
    for row in plan["dependencies"]:
        if sha256_bytes(_read_bound_file(repo, row["path"])) != row.get("sha256"):
            raise AdoptionError(f"stale cleanup plan: dependency changed during apply: {row['path']}")


def _operation_backup(transaction: Path, index: int) -> Path:
    return transaction / "backups" / str(index)


def _operation_stage(transaction: Path, index: int) -> Path:
    return transaction / "staged" / str(index)


def _verify_backup(transaction: Path, index: int, operation: dict[str, Any]) -> None:
    backup = _operation_backup(transaction, index)
    row = operation["row"]
    if not _target_matches(backup, row):
        raise AdoptionError(f"moved source failed authentication: {operation['path']}")


def _verify_moved_state(
    repo: Path,
    plan: dict[str, Any],
    transaction: Path,
    journal: dict[str, Any],
    *,
    require_index: bool,
) -> None:
    _verify_plan_dependencies(repo, plan)
    for index, operation in enumerate(journal["operations"]):
        _verify_backup(transaction, index, operation)
        original = repo / operation["path"]
        kind = operation["operation"]
        if kind == "edit":
            if (
                original.is_symlink()
                or not original.is_file()
                or sha256_bytes(original.read_bytes()) != operation["desiredSha256"]
            ):
                raise AdoptionError(f"changed or missing installed edit: {operation['path']}")
        elif kind == "delete":
            if os.path.lexists(original):
                raise AdoptionError(f"deletion target was recreated during apply: {operation['path']}")
        elif kind == "regenerate" and require_index:
            expected = _trusted_index_bytes(repo, _plan_brain_sha256(plan))
            if (
                original.is_symlink()
                or not original.is_file()
                or original.read_bytes() != expected
            ):
                raise AdoptionError(f"generated output failed independent verification: {operation['path']}")


def _preserve_collision(repo: Path, path: Path, recovery: Path | None, index: int) -> tuple[Path, Path]:
    if recovery is None:
        recovery = Path(tempfile.mkdtemp(prefix=".adopt-recovery-", dir=repo))
    destination = recovery / str(index)
    os.replace(path, destination)
    return recovery, destination


def _rollback_transaction(
    repo: Path, transaction: Path, journal: dict[str, Any]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    preserved: list[str] = []
    recovery: Path | None = None
    for index in reversed(range(len(journal["operations"]))):
        operation = journal["operations"][index]
        try:
            rel = safe_rel(operation["path"])
            original = repo / rel
            backup = _operation_backup(transaction, index)
            if not os.path.lexists(backup):
                # Pending operations never moved. A restored operation also
                # has no backup; authenticate it before accepting idempotence.
                if operation.get("state") in {"pending", "staged"}:
                    continue
                if _target_matches(original, operation["row"]):
                    operation["state"] = "restored"
                    _write_journal(transaction, journal)
                    continue
                raise AdoptionError(f"missing recovery backup for {rel}")
            if os.path.lexists(original):
                discard = False
                if operation["operation"] == "edit" and original.is_file() and not original.is_symlink():
                    discard = sha256_bytes(original.read_bytes()) == operation.get("desiredSha256")
                elif operation["operation"] == "regenerate" and original.is_file() and not original.is_symlink():
                    try:
                        discard = original.read_bytes() == _trusted_index_bytes(repo)
                    except AdoptionError:
                        discard = False
                if discard:
                    original.unlink()
                else:
                    recovery, destination = _preserve_collision(repo, original, recovery, index)
                    preserved.append(destination.relative_to(repo).as_posix())
            original.parent.mkdir(parents=True, exist_ok=True)
            os.replace(backup, original)
            operation["state"] = "restored"
            _write_journal(transaction, journal)
        except BaseException as exc:
            errors.append(f"{operation.get('path', index)}: {exc}")
    return errors, preserved


def recover_cleanup(repo: Path) -> list[str]:
    """Roll back the transaction named by the durable repository lock."""
    repo = repo.resolve()
    lock = _read_lock(repo)
    transaction = _transaction_path(repo, lock["transaction"])
    if not transaction.is_dir():
        if lock.get("status") in {"committed", "rolled-back"}:
            (repo / LOCK_REL).unlink()
            return []
        raise AdoptionError("cleanup lock names a missing transaction; manual recovery required")
    journal = _read_journal(transaction)
    if journal.get("planId") != lock.get("planId"):
        raise AdoptionError("cleanup lock and recovery journal do not match")
    if journal.get("status") == "committed":
        shutil.rmtree(transaction)
        _remove_lock(repo, transaction)
        return []
    errors, preserved = _rollback_transaction(repo, transaction, journal)
    if errors:
        raise AdoptionError("cleanup recovery incomplete; lock retained: " + "; ".join(errors))
    journal["status"] = "rolled-back"
    _write_journal(transaction, journal)
    _set_lock_status(repo, transaction, "rolled-back")
    shutil.rmtree(transaction)
    _remove_lock(repo, transaction)
    return preserved


def apply_plan(repo: Path, plan: dict[str, Any]) -> None:
    repo = repo.resolve()
    plan = _validate_plan_shape(plan)
    _cleanup_safe_orphans(repo)
    if os.path.lexists(repo / LOCK_REL):
        raise AdoptionError(
            f"cleanup lock exists at {LOCK_REL}; run adopt_check.py recover before applying"
        )
    dirty = dirty_planned_paths(repo, plan)
    if dirty:
        raise AdoptionError("planned cleanup paths are dirty; refusing mutation:\n  " + "\n  ".join(dirty))
    if build_plan(repo) != plan:
        raise AdoptionError("stale cleanup plan: repository state or manifest changed; generate a new preview")

    operations: list[dict[str, Any]] = []
    desired: dict[int, tuple[bytes, int]] = {}
    for row in plan["edits"]:
        path = safe_existing(repo, row["path"], expected_kind="file")
        operations.append(
            {
                "operation": "edit",
                "path": row["path"],
                "row": {"kind": "file", "sha256": row["sha256"]},
                "desiredSha256": row["desiredSha256"],
                "state": "pending",
            }
        )
        desired[len(operations) - 1] = (_desired_edit(repo, row), path.stat().st_mode)
    for row in plan["delete"]:
        operations.append(
            {"operation": "delete", "path": row["path"], "row": row, "state": "pending"}
        )
    for row in plan["regenerate"]:
        path = safe_existing(repo, row["path"], expected_kind="file")
        operations.append(
            {
                "operation": "regenerate",
                "path": row["path"],
                "row": {"kind": "file", "sha256": row["sha256"]},
                "state": "pending",
            }
        )
        # Preserve the checked-in mode for the brain command's replacement.
        desired[len(operations) - 1] = (b"", path.stat().st_mode)

    transaction = Path(tempfile.mkdtemp(prefix=TRANSACTION_PREFIX, dir=repo))
    (transaction / "backups").mkdir()
    (transaction / "staged").mkdir()
    journal: dict[str, Any] = {
        "schemaVersion": 1,
        "planId": plan["planId"],
        "status": "preparing",
        "operations": operations,
    }
    _write_journal(transaction, journal)
    try:
        _acquire_lock(repo, plan, transaction)
    except BaseException:
        shutil.rmtree(transaction, ignore_errors=True)
        raise

    try:
        for index, (body, mode) in desired.items():
            if operations[index]["operation"] == "edit":
                _atomic_write(_operation_stage(transaction, index), body, mode)
            operations[index]["state"] = "staged"
        journal["status"] = "staged"
        _write_journal(transaction, journal)

        # Final read-only gate after the lock and staging. Sources are then
        # moved to private backups and authenticated, closing the usual
        # preflight-to-write race without ever overwriting the late bytes.
        dirty = dirty_planned_paths(repo, plan)
        if dirty:
            raise AdoptionError("planned cleanup paths became dirty during apply")
        if build_plan(repo) != plan:
            raise AdoptionError("stale cleanup plan: repository changed during final preflight")

        for index, operation in enumerate(operations):
            kind = operation["row"]["kind"]
            raw = operation["path"] + ("/" if kind == "directory" else "")
            original = safe_existing(repo, raw, expected_kind=kind)
            backup = _operation_backup(transaction, index)
            operation["state"] = "moving"
            _write_journal(transaction, journal)
            os.replace(original, backup)
            operation["state"] = "backed-up"
            _write_journal(transaction, journal)
            _verify_backup(transaction, index, operation)
            if operation["operation"] == "edit":
                os.replace(_operation_stage(transaction, index), original)
                operation["state"] = "installed"
                _write_journal(transaction, journal)

        _verify_moved_state(repo, plan, transaction, journal, require_index=False)
        manifest, _ = load_manifest(repo)
        _post_apply_validate(repo, manifest["cleanup_marker"], plan)
        _verify_moved_state(repo, plan, transaction, journal, require_index=True)
        journal["status"] = "committed"
        _write_journal(transaction, journal)
    except BaseException as exc:
        rollback_errors, preserved = _rollback_transaction(repo, transaction, journal)
        if not rollback_errors:
            journal["status"] = "rolled-back"
            _write_journal(transaction, journal)
            try:
                _set_lock_status(repo, transaction, "rolled-back")
                shutil.rmtree(transaction)
                _remove_lock(repo, transaction)
            except BaseException as cleanup_exc:
                rollback_errors.append(f"transaction cleanup: {cleanup_exc}")
        recovery = f"; preserved late paths: {preserved}" if preserved else ""
        detail = f"; rollback failures: {rollback_errors}" if rollback_errors else ""
        if isinstance(exc, AdoptionError):
            raise AdoptionError(f"atomic cleanup rolled back: {exc}{recovery}{detail}") from exc
        raise AdoptionError(
            f"atomic cleanup rolled back after unexpected failure: {exc}{recovery}{detail}"
        ) from exc
    else:
        _set_lock_status(repo, transaction, "committed")
        shutil.rmtree(transaction)
        _remove_lock(repo, transaction)


def plan_human(plan: dict[str, Any]) -> str:
    lines = [f"Adoption cleanup plan {plan['planId']}", "Delete atomically:"]
    for row in plan["delete"]:
        suffix = "/" if row["kind"] == "directory" else ""
        lines.append(f"  - {row['path']}{suffix}")
        for item in row.get("contents", []):
            lines.append(f"      - {item['path']}")
    lines.append("Remove marked reference lines:")
    if not plan["edits"]:
        lines.append("  - (none)")
    for row in plan["edits"]:
        for line in row["removeLines"]:
            display = "<restricted line redacted>" if line.get("restricted") else line["text"]
            lines.append(f"  - {row['path']}:{line['line']}: {display}")
    lines.append("Regenerate after cleanup:")
    lines.extend(f"  - {row['path']}" for row in plan["regenerate"])
    lines.append("No files have been changed. Save the JSON plan, review it, then apply that exact plan.")
    return "\n".join(lines) + "\n"


def write_plan(path: Path, plan: dict[str, Any]) -> None:
    plan = _validate_plan_shape(plan)
    requested = path.expanduser().absolute()
    if requested.is_symlink():
        raise AdoptionError(f"refusing symlinked cleanup-plan output {requested}")
    path = requested.resolve()
    if not path.parent.is_dir():
        raise AdoptionError(f"cleanup-plan output directory does not exist: {path.parent}")
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdoptionError(f"refusing to overwrite foreign cleanup-plan output {path}: {exc}") from exc
        try:
            _validate_plan_shape(existing)
        except AdoptionError as exc:
            raise AdoptionError(f"refusing to overwrite foreign cleanup-plan output {path}: {exc}") from exc
    body = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
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


def read_plan(path: Path) -> dict[str, Any]:
    try:
        return _validate_plan_shape(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdoptionError(f"cannot read cleanup plan {path}: {exc}") from exc
