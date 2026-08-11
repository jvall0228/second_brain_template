#!/usr/bin/env python3
"""brain — vault index CLI.

Structured, queryable access to the vault for agents and humans.
Behavior is governed by spec.md in this directory (canonical); section
references below (§n) point there. Stdlib-only, Python 3.10+.

Usage: python 10_Agents/tools/brain/brain.py <command> [options]
Commands: index, list, search, links, tags, show, recent, validate
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 1
INDEX_RELPATH = "10_Agents/tools/brain/vault-index.json"
TESTS_RELPATH = "10_Agents/tools/brain/tests"
CONVENTIONS_RELPATH = "00_Meta/conventions.md"

# ---------------------------------------------------------------------------
# §2 Corpus


def default_vault_root() -> Path:
    return Path(__file__).resolve().parents[3]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def fold(s: str) -> str:
    # §6 folding rule: NFC then casefold.
    return nfc(s).casefold()


def walk_corpus(root: Path) -> tuple[list[str], list[str]]:
    """Working corpus: (note paths, asset paths), vault-relative NFC, sorted."""
    notes: list[str] = []
    assets: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d != "__pycache__"
            and not (
                nfc(f"{rel_dir}/{d}" if rel_dir != "." else d) == TESTS_RELPATH
            )
        ]
        dirnames.sort()
        for name in filenames:
            if name.startswith("."):
                continue
            rel = nfc(f"{rel_dir}/{name}" if rel_dir != "." else name)
            if rel == INDEX_RELPATH:
                continue
            if name.endswith(".md"):
                notes.append(rel)
            else:
                assets.append(rel)
    return sorted(notes), sorted(assets)


def git_tracked(root: Path) -> set[str] | None:
    """NFC paths of tracked/staged files, or None if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {nfc(p.decode("utf-8")) for p in out.split(b"\0") if p}


def index_corpus(root: Path) -> tuple[list[str], list[str]]:
    """Index corpus (§2): working corpus restricted to git-tracked files."""
    notes, assets = walk_corpus(root)
    tracked = git_tracked(root)
    if tracked is None:
        print(
            "warning: git unavailable — building index from the working tree",
            file=sys.stderr,
        )
        return notes, assets
    return [p for p in notes if p in tracked], [p for p in assets if p in tracked]


# ---------------------------------------------------------------------------
# §3 Text model


def load_text(root: Path, rel: str) -> tuple[str | None, int]:
    """(normalized text or None on decode failure, sizeBytes)."""
    raw = (root / rel).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        norm = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return None, len(norm)
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, len(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# §4 Frontmatter grammar

KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:$|\s+(.*)$|\s+$)")
LIST_ITEM_RE = re.compile(r"^\s*-\s(.*)$")


def scalar(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s


def split_flow(inner: str) -> list[str]:
    if not inner.strip():
        return []
    items: list[str] = []
    buf = ""
    quote: str | None = None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
    items.append(buf)
    return [scalar(i) for i in items]


def parse_frontmatter(lines: list[str]) -> tuple[dict, list[str], int, bool]:
    """Returns (frontmatter map, errors, body start line index, has_frontmatter)."""
    if not lines or lines[0] != "---":
        return {}, [], 0, False
    errors: list[str] = []
    close = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            close = i
            break
    if close is None:
        errors.append("unterminated-frontmatter")
        body_start = 1
        block: list[str] = lines[1:]
    else:
        body_start = close + 1
        block = lines[1:close]

    fm: dict = {}
    open_list: str | None = None
    for offset, line in enumerate(block, start=2):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        m = KEY_RE.match(line)
        if m:
            key, value = m.group(1), (m.group(2) or "").strip()
            if key in fm:
                errors.append(f"duplicate-key:{key}")
            open_list = None
            if not value:
                fm[key] = None
                open_list = key
            elif value.startswith("["):
                if value.endswith("]"):
                    inner = value[1:-1]
                    if "[" in inner or "]" in inner:
                        errors.append(f"unsupported-yaml:{offset}")
                    else:
                        fm[key] = split_flow(inner)
                else:
                    errors.append(f"unsupported-yaml:{offset}")
            else:
                fm[key] = scalar(value)
            continue
        m = LIST_ITEM_RE.match(line)
        if m:
            if open_list is None:
                errors.append("list-item-without-key")
            else:
                if fm[open_list] is None:
                    fm[open_list] = []
                fm[open_list].append(scalar(m.group(1)))
            continue
        errors.append(f"unsupported-yaml:{offset}")
    return fm, errors, body_start, True


UPDATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def typed_fields(fm: dict, errors: list[str]) -> tuple[str | None, list[str] | None, str | None]:
    """§4.5: (title, tags, updated) with coercions recorded into errors."""
    title = fm.get("title") if isinstance(fm.get("title"), str) else None
    raw_tags = fm.get("tags")
    tags: list[str] | None
    if isinstance(raw_tags, list):
        tags = raw_tags
    elif isinstance(raw_tags, str):
        errors.append("tags-not-a-list")
        tags = [raw_tags]
    else:
        tags = None
    updated = None
    raw_updated = fm.get("updated")
    if isinstance(raw_updated, str):
        if UPDATED_RE.match(raw_updated):
            y, mo, d = (int(x) for x in raw_updated.split("-"))
            try:
                date(y, mo, d)
                updated = raw_updated
            except ValueError:
                errors.append("invalid-updated")
        else:
            errors.append("invalid-updated")
    elif "updated" in fm:
        errors.append("invalid-updated")
    return title, tags, updated


# ---------------------------------------------------------------------------
# §5.2 Exclusion zones

FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
TICK_RUN_RE = re.compile(r"`+")


def mask_code_spans(line: str) -> str:
    """Blank out line-scoped inline code spans (backticks included)."""
    runs = [(m.start(), m.end()) for m in TICK_RUN_RE.finditer(line)]
    if not runs:
        return line
    out = list(line)
    i = 0
    while i < len(runs):
        n = runs[i][1] - runs[i][0]
        j = i + 1
        while j < len(runs) and runs[j][1] - runs[j][0] != n:
            j += 1
        if j < len(runs):
            for k in range(runs[i][0], runs[j][1]):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def body_lines_masked(lines: list[str], body_start: int):
    """Yield (line number, raw line, masked line) outside fenced code blocks."""
    fence_char = ""
    fence_len = 0
    for i in range(body_start, len(lines)):
        raw = lines[i]
        if fence_char:
            stripped = raw.strip()
            if stripped and set(stripped) == {fence_char} and len(stripped) >= fence_len:
                fence_char = ""
            continue
        m = FENCE_OPEN_RE.match(raw)
        if m:
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            continue
        yield i + 1, raw, mask_code_spans(raw)


# ---------------------------------------------------------------------------
# §5 Wikilink grammar / §7 body extraction

LINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
HEADING_RE = re.compile(r"^( {0,3})(#{1,6}) (.*)$")
BODY_TAG_RE = re.compile(r"(?:^|(?<=\s))#([A-Za-z0-9_/-]+)")
EXT_RE = re.compile(r"\.[A-Za-z0-9]+$")


def parse_link(inner: str, embed: bool, raw: str, line: int) -> dict:
    i = inner.find("|")
    if i == -1:
        linkpath, display = inner, None
    elif i > 0 and inner[i - 1] == "\\":
        linkpath, display = inner[: i - 1], inner[i + 1 :]
    else:
        linkpath, display = inner[:i], inner[i + 1 :]
    if "#" in linkpath:
        target, fragment = linkpath.split("#", 1)
        fragment = fragment.strip()
    else:
        target, fragment = linkpath, None
    target = target.strip()
    display = display.strip() if display is not None else None
    placeholder = "{{" in target
    if target.endswith(".md"):
        target = target[:-3]
    return {
        "display": display,
        "embed": embed,
        "fragment": fragment,
        "line": line,
        "placeholder": placeholder,
        "raw": raw,
        "resolved": None,
        "target": target,
        "warnings": [],
    }


def extract_body(lines: list[str], body_start: int) -> tuple[list[dict], list[dict], list[str]]:
    """Returns (links, headings, bodyTags) per §5 and §7."""
    links: list[dict] = []
    headings: list[dict] = []
    body_tags: set[str] = set()
    for lineno, raw, masked in body_lines_masked(lines, body_start):
        hm = HEADING_RE.match(masked)
        if hm:
            text = raw[hm.start(3) :]
            text = re.sub(r"\s+#+\s*$", "", text).strip()
            headings.append({"level": len(hm.group(2)), "line": lineno, "text": text})
        for m in LINK_RE.finditer(masked):
            if m.start() > 0 and masked[m.start() - 1] == "\\":
                continue
            links.append(parse_link(m.group(2), m.group(1) == "!", m.group(0), lineno))
        for m in BODY_TAG_RE.finditer(masked):
            tag = m.group(1)
            if any(not c.isdigit() for c in tag):
                body_tags.add(tag)
    return links, headings, sorted(body_tags)


# ---------------------------------------------------------------------------
# §6 Link resolution


class Resolver:
    def __init__(self, notes: list[str], assets: list[str], titles: dict[str, str | None]):
        self.notes = set(notes)
        self.note_base: dict[str, list[str]] = {}
        for p in notes:
            self.note_base.setdefault(fold(p.rsplit("/", 1)[-1][:-3]), []).append(p)
        self.note_fold = {}
        for p in notes:
            self.note_fold.setdefault(fold(p), []).append(p)
        self.assets = set(assets)
        self.asset_base: dict[str, list[str]] = {}
        for p in assets:
            self.asset_base.setdefault(fold(p.rsplit("/", 1)[-1]), []).append(p)
        self.asset_fold = {}
        for p in assets:
            self.asset_fold.setdefault(fold(p), []).append(p)
        self.title_fold: dict[str, list[str]] = {}
        for p, t in titles.items():
            if t:
                self.title_fold.setdefault(fold(t), []).append(p)

    @staticmethod
    def _pick(cands: list[str]) -> str:
        return min(cands, key=lambda p: (p.count("/"), p))

    def _ladder(
        self, target: str, base: dict, full_set: set, full_fold: dict, suffix: str
    ) -> tuple[str | None, list[str]]:
        if "/" not in target:
            cands = base.get(fold(target))
            if cands:
                warnings = []
                r = cands[0] if len(cands) == 1 else self._pick(cands)
                if len(cands) > 1:
                    warnings.append("ambiguous")
                actual = r.rsplit("/", 1)[-1]
                if suffix:
                    actual = actual[: -len(suffix)]
                if actual != target:
                    warnings.append("case-mismatch")
                return r, warnings
            return None, []
        full = target + suffix
        if full in full_set:
            return full, []
        ci = full_fold.get(fold(full))
        if ci:
            warnings = ["case-mismatch"]
            r = ci[0] if len(ci) == 1 else self._pick(ci)
            if len(ci) > 1:
                warnings.insert(0, "ambiguous")
            return r, warnings
        return None, []

    def resolve(self, target: str, containing: str) -> tuple[str | None, list[str]]:
        if target == "":
            return containing, []
        r, warnings = self._ladder(target, self.note_base, self.notes, self.note_fold, ".md")
        if r:
            return r, warnings
        final = target.rsplit("/", 1)[-1]
        if EXT_RE.search(final) and not final.endswith(".md"):
            r, warnings = self._ladder(target, self.asset_base, self.assets, self.asset_fold, "")
            if r:
                return r, warnings
        hints = sorted(self.title_fold.get(fold(target), []))
        return None, [f"title-match:{p}" for p in hints]


# ---------------------------------------------------------------------------
# §8 Index build and serialization


def build_index(root: Path, notes: list[str], assets: list[str]) -> dict:
    records: dict[str, dict] = {}
    for rel in notes:
        text, size = load_text(root, rel)
        if text is None:
            records[rel] = {
                "backlinks": [],
                "bodyTags": [],
                "frontmatter": {},
                "frontmatterErrors": ["not-utf8"],
                "headings": [],
                "links": [],
                "sizeBytes": size,
                "title": None,
                "updated": None,
            }
            continue
        lines = text.split("\n")
        fm, errors, body_start, _has_fm = parse_frontmatter(lines)
        title, _tags, updated = typed_fields(fm, errors)
        links, headings, body_tags = extract_body(lines, body_start)
        records[rel] = {
            "backlinks": [],
            "bodyTags": body_tags,
            "frontmatter": fm,
            "frontmatterErrors": errors,
            "headings": headings,
            "links": links,
            "sizeBytes": size,
            "title": title,
            "updated": updated,
        }
    resolver = Resolver(notes, assets, {p: r["title"] for p, r in records.items()})
    backlinks: dict[str, set[str]] = {p: set() for p in notes}
    for rel, rec in records.items():
        for link in rec["links"]:
            if link["placeholder"]:
                continue
            resolved, warnings = resolver.resolve(link["target"], rel)
            link["resolved"] = resolved
            link["warnings"] = warnings
            if resolved in backlinks:
                backlinks[resolved].add(rel)
    for rel, rec in records.items():
        rec["backlinks"] = sorted(backlinks[rel])
    return {"assets": assets, "notes": records, "schemaVersion": SCHEMA_VERSION}


def serialize(index: dict) -> bytes:
    return (json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode(
        "utf-8"
    )


# ---------------------------------------------------------------------------
# §10.1 Conventions taxonomy

TICK_TOKEN_RE = re.compile(r"`([^`]+)`")


def load_taxonomy(root: Path) -> dict[str, list[str] | None] | None:
    """namespace -> closed value list, or None for open. None overall = unreadable."""
    try:
        text, _ = load_text(root, CONVENTIONS_RELPATH)
    except OSError:
        return None
    if text is None:
        return None
    lines = text.split("\n")
    try:
        start = lines.index("## Tag Namespaces")
    except ValueError:
        return None
    table: list[str] = []
    for line in lines[start + 1 :]:
        if line.lstrip().startswith("|"):
            table.append(line)
        elif table:
            break
    if len(table) < 3:
        return None
    taxonomy: dict[str, list[str] | None] = {}
    for row in table[2:]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 3:
            return None
        m = TICK_TOKEN_RE.search(cells[0])
        if not m:
            return None
        namespace = m.group(1)
        if namespace.endswith("/*"):
            namespace = namespace[:-2]
        if cells[2].lower().startswith("free-form"):
            taxonomy[namespace] = None
        else:
            taxonomy[namespace] = TICK_TOKEN_RE.findall(cells[2])
    return taxonomy or None


# ---------------------------------------------------------------------------
# §10 Validate

NOTE_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
PERIODIC_RE = re.compile(r"^\d{4}-(W\d{2}|Q\d)-review\.md$")
NAME_EXCEPTIONS = {"AGENTS.md", "CLAUDE.md", "README.md"}
FM_WARNING_RULES = {"tags-not-a-list"}
SKILLS_PREFIX = "10_Agents/skills/"


def is_template(rel: str) -> bool:
    return rel.startswith("09_Templates/")


def has_placeholder(value) -> bool:
    if isinstance(value, str):
        return "{{" in value
    if isinstance(value, list):
        return any(isinstance(v, str) and "{{" in v for v in value)
    return False


def run_validate(root: Path, check_index: bool) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []

    def err(path: str, rule: str, message: str, line: int | None = None):
        errors.append({"line": line, "message": message, "path": path, "rule": rule})

    def warn(path: str, rule: str, message: str, line: int | None = None):
        warnings.append({"line": line, "message": message, "path": path, "rule": rule})

    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    taxonomy = load_taxonomy(root)
    if taxonomy is None:
        err(
            CONVENTIONS_RELPATH,
            "conventions-table-unreadable",
            "cannot read the authoritative Tag Namespaces table",
        )

    folded: dict[str, list[str]] = {}
    for p in notes + assets:
        folded.setdefault(fold(p), []).append(p)
    for group in folded.values():
        if len(group) > 1:
            group = sorted(group)
            err(
                group[0],
                "path-collision",
                "collides case-insensitively with " + ", ".join(group[1:]),
            )

    for rel in notes:
        rec = index["notes"][rel]
        template = is_template(rel)
        exempt_frontmatter = rel == "CLAUDE.md"

        name = rel.rsplit("/", 1)[-1]
        if not (
            NOTE_NAME_RE.match(name)
            or name in NAME_EXCEPTIONS
            or PERIODIC_RE.match(name)
            or (name == "SKILL.md" and rel.startswith(SKILLS_PREFIX))
        ):
            err(rel, "filename-convention", f"filename {name!r} is not kebab-case")

        if not exempt_frontmatter:
            fm = rec["frontmatter"]
            for fe in rec["frontmatterErrors"]:
                rule = fe.split(":", 1)[0]
                if rule in FM_WARNING_RULES or rule == "duplicate-key":
                    warn(rel, rule, fe)
                elif rule == "invalid-updated" and template and has_placeholder(
                    fm.get("updated")
                ):
                    continue
                else:
                    err(rel, rule, fe)
            if not fm and "not-utf8" not in rec["frontmatterErrors"]:
                if "unterminated-frontmatter" not in rec["frontmatterErrors"]:
                    err(rel, "missing-frontmatter", "note has no frontmatter block")
            else:
                if rec["title"] is None and not (
                    template and has_placeholder(fm.get("title"))
                ):
                    err(rel, "missing-title", "frontmatter lacks a title string")
                raw_tags = fm.get("tags")
                if raw_tags is None and not (template and has_placeholder(raw_tags)):
                    err(rel, "missing-tags", "frontmatter lacks a tags list")
                if "updated" not in fm:
                    err(rel, "missing-updated", "frontmatter lacks an updated date")
                tags = raw_tags if isinstance(raw_tags, list) else (
                    [raw_tags] if isinstance(raw_tags, str) else []
                )
                for tag in tags:
                    if template and "{{" in tag:
                        continue
                    if "/" not in tag:
                        err(rel, "tag-not-namespaced", f"tag {tag!r} has no namespace")
                        continue
                    if taxonomy is None:
                        continue
                    namespace, value = tag.split("/", 1)
                    if namespace not in taxonomy:
                        err(rel, "unknown-namespace", f"tag namespace {namespace!r} is not in conventions")
                    elif taxonomy[namespace] is not None and value not in taxonomy[namespace]:
                        err(
                            rel,
                            "unknown-tag-value",
                            f"tag {tag!r} is not in the conventions value list",
                        )

        for link in rec["links"]:
            if link["placeholder"]:
                continue
            if link["resolved"] is None:
                hints = [w[len("title-match:") :] for w in link["warnings"]]
                message = f"unresolved link {link['raw']}"
                if hints:
                    message += " (title matches: " + ", ".join(hints) + ")"
                err(rel, "unresolved-link", message, link["line"])
            else:
                for w in link["warnings"]:
                    if w == "ambiguous":
                        warn(rel, "ambiguous-link", f"{link['raw']} is ambiguous; resolved to {link['resolved']}", link["line"])
                    elif w == "case-mismatch":
                        warn(rel, "case-mismatch", f"{link['raw']} differs in case from {link['resolved']}", link["line"])

    skill_dirs: dict[str, list[str]] = {}
    for rel in notes:
        if rel.startswith(SKILLS_PREFIX) and "/" in rel[len(SKILLS_PREFIX) :]:
            skill_dirs.setdefault(rel[len(SKILLS_PREFIX) :].split("/", 1)[0], []).append(rel)
    for dirname in sorted(skill_dirs):
        skill_md = f"{SKILLS_PREFIX}{dirname}/SKILL.md"
        if skill_md not in index["notes"]:
            err(f"{SKILLS_PREFIX}{dirname}/", "skill-missing", "skill directory has no SKILL.md")
            continue
        fm = index["notes"][skill_md]["frontmatter"]
        if fm.get("name") != dirname:
            err(
                skill_md,
                "skill-name-mismatch",
                f"frontmatter name {fm.get('name')!r} != directory name {dirname!r}",
            )
        description = fm.get("description")
        if not (isinstance(description, str) and description.strip()):
            err(skill_md, "skill-missing-description", "frontmatter lacks a description string")

    if check_index:
        tnotes, tassets = index_corpus(root)
        fresh = serialize(build_index(root, tnotes, tassets))
        index_path = root / INDEX_RELPATH
        if not index_path.exists() or index_path.read_bytes() != fresh:
            err(INDEX_RELPATH, "stale-index", "stale index — run `brain index`")

    def key(f: dict):
        return (f["path"], 0 if f["line"] is None else 1, f["line"] or 0, f["rule"])

    return sorted(errors, key=key), sorted(warnings, key=key)


# ---------------------------------------------------------------------------
# §9 CLI commands


def effective_tags(rec: dict) -> set[str]:
    tags = rec["frontmatter"].get("tags")
    fm_tags = tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])
    return set(fm_tags) | set(rec["bodyTags"])


def tag_matches(tag_filter: str, tags: set[str]) -> bool:
    if tag_filter.endswith("/*"):
        prefix = tag_filter[:-1]
        return any(t.startswith(prefix) for t in tags)
    return tag_filter in tags


def resolve_note_arg(index: dict, arg: str) -> str | None:
    # Index paths are /-separated (spec §2); accept OS-native separators from
    # callers like the VS Code ${relativeFile} task on Windows.
    target = nfc(arg.strip()).replace("\\", "/")
    if target.endswith(".md"):
        target = target[:-3]
    notes = sorted(index["notes"])
    resolver = Resolver(notes, index["assets"], {p: index["notes"][p]["title"] for p in notes})
    resolved, _ = resolver.resolve(target, target)
    return resolved if resolved in index["notes"] else None


def emit(payload, as_json: bool, human_lines):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        for line in human_lines:
            print(line)


def cmd_index(root: Path, args) -> int:
    notes, assets = index_corpus(root)
    data = serialize(build_index(root, notes, assets))
    path = root / INDEX_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(INDEX_RELPATH)
    return 0


def cmd_list(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    filters = list(args.tag)
    if args.type:
        filters.append(f"type/{args.type}")
    rows = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if args.dir and not rel.startswith(args.dir):
            continue
        tags = effective_tags(rec)
        if not all(tag_matches(t, tags) for t in filters):
            continue
        rows.append({"path": rel, "title": rec["title"], "updated": rec["updated"]})
    emit(rows, args.json, (r["path"] for r in rows))
    return 0


def cmd_search(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    query = args.query.lower()
    hits = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if args.tag and not all(tag_matches(t, effective_tags(rec)) for t in args.tag):
            continue
        if rec["title"] and query in rec["title"].lower():
            hits.append({"field": "title", "line": None, "path": rel, "snippet": rec["title"]})
        heading_lines = set()
        for h in rec["headings"]:
            heading_lines.add(h["line"])
            if query in h["text"].lower():
                hits.append(
                    {"field": "heading", "line": h["line"], "path": rel, "snippet": h["text"]}
                )
        text, _ = load_text(root, rel)
        if text is None:
            continue
        for i, line in enumerate(text.split("\n"), start=1):
            if i in heading_lines:
                continue
            if query in line.lower():
                hits.append({"field": "body", "line": i, "path": rel, "snippet": line.strip()})
    emit(
        hits,
        args.json,
        (
            f"{h['path']}: title: {h['snippet']}"
            if h["line"] is None
            else f"{h['path']}:{h['line']}: {h['snippet']}"
            for h in hits
        ),
    )
    return 0


def cmd_links(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    rel = resolve_note_arg(index, args.note)
    if rel is None:
        print(f"error: note not found: {args.note}", file=sys.stderr)
        return 1
    rec = index["notes"][rel]
    unresolved = sorted(
        {l["target"] for l in rec["links"] if l["resolved"] is None and not l["placeholder"]}
    )
    payload = {
        "backlinks": rec["backlinks"],
        "outgoing": rec["links"],
        "path": rel,
        "unresolved": unresolved,
    }
    lines = [f"note: {rel}", "outgoing:"]
    for l in rec["links"]:
        state = l["resolved"] or ("placeholder" if l["placeholder"] else "UNRESOLVED")
        lines.append(f"  {l['raw']} -> {state}")
    lines.append("backlinks:")
    lines.extend(f"  {b}" for b in rec["backlinks"])
    if unresolved:
        lines.append("unresolved: " + ", ".join(unresolved))
    emit(payload, args.json, lines)
    return 0


def cmd_tags(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    counts: dict[str, dict[str, int]] = {}
    for rec in index["notes"].values():
        for tag in effective_tags(rec):
            namespace, _, value = tag.partition("/")
            if not value:
                namespace, value = "(none)", tag
            counts.setdefault(namespace, {})
            counts[namespace][value] = counts[namespace].get(value, 0) + 1
    lines = []
    for namespace in sorted(counts):
        lines.append(f"{namespace}/")
        for value in sorted(counts[namespace]):
            lines.append(f"  {value} {counts[namespace][value]}")
    emit(counts, args.json, lines)
    return 0


def cmd_show(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    rel = resolve_note_arg(index, args.note)
    if rel is None:
        print(f"error: note not found: {args.note}", file=sys.stderr)
        return 1
    rec = index["notes"][rel]
    lines = [
        f"path: {rel}",
        f"title: {rec['title']}",
        f"updated: {rec['updated']}",
        f"tags: {', '.join(sorted(effective_tags(rec))) or '(none)'}",
        f"headings: {len(rec['headings'])}  links: {len(rec['links'])}  backlinks: {len(rec['backlinks'])}",
        f"sizeBytes: {rec['sizeBytes']}",
    ]
    if rec["frontmatterErrors"]:
        lines.append("frontmatterErrors: " + ", ".join(rec["frontmatterErrors"]))
    emit(rec, args.json, lines)
    return 0


def cmd_recent(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    entries = list(index["notes"].items())
    entries.sort(key=lambda kv: kv[0])
    entries.sort(key=lambda kv: (root / kv[0]).stat().st_mtime, reverse=True)
    entries.sort(key=lambda kv: kv[1]["updated"] or "", reverse=True)
    entries = entries[: args.n]
    rows = [
        {"path": rel, "title": rec["title"], "updated": rec["updated"]}
        for rel, rec in entries
    ]
    emit(rows, args.json, (f"{r['updated'] or '----------'}  {r['path']}" for r in rows))
    return 0


def cmd_validate(root: Path, args) -> int:
    errors, warnings = run_validate(root, args.check_index)
    if args.json:
        print(
            json.dumps(
                {"errors": errors, "warnings": warnings},
                ensure_ascii=False,
                indent=1,
                sort_keys=True,
            )
        )
    else:
        for f in errors + warnings:
            severity = "ERROR" if f in errors else "WARN"
            location = f["path"] + (f":{f['line']}" if f["line"] is not None else "")
            print(f"{severity} {location} {f['rule']}: {f['message']}")
        print(f"{len(errors)} errors, {len(warnings)} warnings")
    if errors:
        return 1
    if warnings:
        return 2
    return 0


# ---------------------------------------------------------------------------
# Entry point


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brain", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, **kwargs):
        p = sub.add_parser(name, **kwargs)
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.add_argument("--vault", type=Path, default=None, help="vault root override")
        return p

    add("index", help="rebuild and write the committed vault index")
    p = add("list", help="list note paths")
    p.add_argument("--dir", default=None, help="path prefix filter")
    p.add_argument("--tag", action="append", default=[], help="effective-tag filter (repeatable; trailing /* matches a namespace)")
    p.add_argument("--type", default=None, help="shorthand for --tag type/X")
    p = add("search", help="substring search over title, headings, body")
    p.add_argument("query")
    p.add_argument("--tag", action="append", default=[], help="effective-tag filter")
    p = add("links", help="outgoing links, backlinks, unresolved targets")
    p.add_argument("note")
    add("tags", help="tag usage counts by namespace")
    p = add("show", help="full index record for one note")
    p.add_argument("note")
    p = add("recent", help="notes by updated date, newest first")
    p.add_argument("n", nargs="?", type=int, default=10)
    p = add("validate", help="check vault conventions; exit 0 clean / 1 errors / 2 warnings")
    p.add_argument("--check-index", action="store_true", help="also verify the committed index is fresh")

    args = parser.parse_args(argv)
    root = (args.vault or default_vault_root()).resolve()
    handlers = {
        "index": cmd_index,
        "list": cmd_list,
        "search": cmd_search,
        "links": cmd_links,
        "tags": cmd_tags,
        "show": cmd_show,
        "recent": cmd_recent,
        "validate": cmd_validate,
    }
    return handlers[args.command](root, args)


if __name__ == "__main__":
    sys.exit(main())
