#!/usr/bin/env python3
"""brain — vault index CLI.

Structured, queryable access to the vault for agents and humans.
Behavior is governed by spec.md in this directory (canonical); section
references below (§n) point there. Stdlib-only, Python 3.10+.

Usage: python 10_Agents/tools/brain/brain.py <command> [options]
Commands: index, list, search, links, tags, show, recent, validate,
          curate, context, config, report, tasks, embed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 1
INDEX_RELPATH = "10_Agents/tools/brain/vault-index.json"
# §18.1 embeddings sidecar: gitignored, machine-local, pruned from the corpus
# exactly like the index file (constants for the rest of §17 sit with its code).
EMBED_RELPATH = "10_Agents/tools/brain/vault-embeddings.json"
# Any tool's test tree (fixture mini-vaults, secret-shaped test data) stays
# out of the corpus — mirrors run_tests.py's */tests/ discovery rule.
TOOL_TESTS_RE = re.compile(r"^10_Agents/tools/[^/]+/tests$")
CONVENTIONS_RELPATH = "00_Meta/conventions.md"

# ---------------------------------------------------------------------------
# §14 Curation tunables — the single place these numbers live.
# Policy prose: 00_Meta/conventions.md § Expiration / § Bootstrap Context.

CURATE_MAX_LINES = 400
CURATE_MAX_BYTES = 20_000
CURATE_STALE_DAYS = 180
EXPIRES_CAP_DAYS = 366

# Events, not claims — never asked for an expires: date. 02_Inbox/ is exempt
# because capture is zero-friction (expires assigned at triage); 02_Outbox/
# because packets are ephemeral — their lifecycle is the archive path.
EXPIRES_EXEMPT_PREFIXES = (
    "02_Inbox/",
    "02_Outbox/",
    "03_Journal/",
    "07_Archives/",
    "09_Templates/",
    "10_Agents/solutions/",
)
EXPIRES_EXEMPT_PATHS = frozenset(
    {"00_Meta/changelog.md", "00_Meta/status.md", "CLAUDE.md"}
)
# type/* tag values whose notes are event records (a decision made on a date),
# not living claims — exempt from expires: wherever they live (e.g. a decision
# record under 04_Projects/). Journal/log types already sit in exempt dirs.
EXPIRES_EXEMPT_TYPE_TAGS = frozenset({"decision"})
ORPHAN_EXEMPT_PATHS = frozenset({"AGENTS.md", "CLAUDE.md", "README.md"})
OVERSIZED_EXEMPT_PATHS = frozenset({"00_Meta/changelog.md"})

# Gate for the validate-side curation warnings (missing-expires,
# expires-beyond-cap, oversized, bootstrap-budget). On since the one-time
# expires: backfill (2026-08-11); `brain curate` always reports regardless.
VALIDATE_CURATION_WARNINGS = True

# R20 bootstrap context budgets (bytes): measured 2026-08-11 sizes + ~50%
# headroom, rounded up. Total ties to the smallest harness project-doc cap.
# conventions.md raised 10240 -> 11264 with the issue-#28 Tasks section: the
# accepted design registers the emoji table there, the file sat 3 bytes under
# budget, and other sections could not be cut — the total budget still holds.
BOOTSTRAP_BUDGETS = {
    "00_Meta/conventions.md": 11264,
    "00_Meta/index.md": 4096,
    "01_Profile/defaults.md": 2048,
    "01_Profile/now.md": 2048,
    "01_Profile/preferences.md": 3072,
    "AGENTS.md": 8192,
}
BOOTSTRAP_TOTAL_BUDGET = 32768

# §16 Health-report defaults — overridable per fork via the `report` config
# key (spec §15.3 / §16.4): report: → stale_days / inbox_days.
REPORT_STALE_ACTIVE_DAYS = 30
REPORT_INBOX_TRIAGE_DAYS = 14

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
            and not TOOL_TESTS_RE.match(
                nfc(f"{rel_dir}/{d}" if rel_dir != "." else d)
            )
        ]
        dirnames.sort()
        for name in filenames:
            if name.startswith("."):
                continue
            rel = nfc(f"{rel_dir}/{name}" if rel_dir != "." else name)
            if rel in (INDEX_RELPATH, EMBED_RELPATH):
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


def iso_date(s: str | None) -> date | None:
    if not isinstance(s, str) or not UPDATED_RE.match(s):
        return None
    y, mo, d = (int(x) for x in s.split("-"))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def check_expires(fm: dict, errors: list[str]) -> None:
    """§14: expires: must be a real YYYY-MM-DD when present (templates may
    hold a placeholder — exempted in run_validate like invalid-updated)."""
    if "expires" not in fm:
        return
    raw = fm.get("expires")
    if not isinstance(raw, str) or iso_date(raw) is None:
        errors.append("invalid-expires")


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

# §17 checkbox tasks (issue #28). Detection runs on the MASKED line (so
# checkboxes inside fenced code or inline code spans never index); the task
# text is taken from the raw line at the same offset (masking preserves
# length), so inline code inside a real task's text survives.
TASK_RE = re.compile(r"^\s*[-*+] \[(.)\] ")
# Obsidian Tasks emoji grammar (accepted design, issue #28). Date-bearing
# emoji take a YYYY-MM-DD token; only 📅 (due) is indexed as a field, but a
# bad date after ANY of them flags `malformed` (§17.2).
TASK_DATE_EMOJI = {
    "\U0001f4c5": "due",  # 📅
    "⏳": "scheduled",  # ⏳
    "\U0001f6eb": "start",  # 🛫
    "✅": "done",  # ✅
    "➕": "created",  # ➕
}
TASK_PRIORITY_EMOJI = {
    "⏫": "high",  # ⏫
    "\U0001f53c": "medium",  # 🔼
    "\U0001f53d": "low",  # 🔽
}
TASK_RECURRENCE_EMOJI = "\U0001f501"  # 🔁 — free-text value, stripped only
TASK_EMOJI_RE = re.compile(
    "("
    + "|".join(
        sorted(TASK_DATE_EMOJI) + sorted(TASK_PRIORITY_EMOJI) + [TASK_RECURRENCE_EMOJI]
    )
    + ")\ufe0f?"  # tolerate an emoji variation selector
)
# ASCII digits only: unicode \d would accept e.g. Arabic-Indic digits that
# int() then mis-parses into a "valid" date the owner never wrote.
TASK_DATE_TOKEN_RE = re.compile(r"\s*([0-9]{4}-[0-9]{2}-[0-9]{2})(?![0-9])")


def parse_task_text(text: str) -> tuple[str, str | None, str | None, list[str]]:
    """§17.2: split a task's raw text into (clean description, due, priority,
    malformed field names). Emoji tokens (emoji + value) are stripped from the
    description; the last occurrence wins for a repeated field. A date-shaped
    token that is not a real calendar date is consumed and flags the field;
    a missing/non-date-shaped value flags the field and leaves the text."""
    due: str | None = None
    priority: str | None = None
    malformed: set[str] = set()
    pieces: list[str] = []
    pos = 0
    matches = list(TASK_EMOJI_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.start() < pos:
            continue  # inside a value a previous token consumed
        pieces.append(text[pos : m.start()])
        emoji = m.group(1)
        if emoji == TASK_RECURRENCE_EMOJI:
            # Recurrence is free text: runs to the next emoji or end of text.
            pos = next(
                (n.start() for n in matches[i + 1 :] if n.start() >= m.end()),
                len(text),
            )
            continue
        if emoji in TASK_PRIORITY_EMOJI:
            priority = TASK_PRIORITY_EMOJI[emoji]
            pos = m.end()
            continue
        field = TASK_DATE_EMOJI[emoji]
        dm = TASK_DATE_TOKEN_RE.match(text, m.end())
        if dm and iso_date(dm.group(1)) is not None:
            if field == "due":
                due = dm.group(1)
            pos = dm.end()
        else:
            malformed.add(field)
            pos = dm.end() if dm else m.end()
    pieces.append(text[pos:])
    clean = " ".join(" ".join(pieces).split())
    return clean, due, priority, sorted(malformed)


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


def extract_body(
    lines: list[str], body_start: int
) -> tuple[list[dict], list[dict], list[str], list[dict]]:
    """Returns (links, headings, bodyTags, tasks) per §5, §7, and §17."""
    links: list[dict] = []
    headings: list[dict] = []
    body_tags: set[str] = set()
    tasks: list[dict] = []
    for lineno, raw, masked in body_lines_masked(lines, body_start):
        tm = TASK_RE.match(masked)
        if tm:
            raw_text = raw[tm.end() :].strip()
            if raw_text:
                text, due, priority, malformed = parse_task_text(raw_text)
                tasks.append(
                    {
                        "due": due,
                        "line": lineno,
                        "malformed": malformed,
                        "priority": priority,
                        "status": "open" if tm.group(1) == " " else "done",
                        "text": text,
                    }
                )
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
    return links, headings, sorted(body_tags), tasks


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
        try:
            text, size = load_text(root, rel)
            read_error = "not-utf8" if text is None else None
        except OSError:
            # §3 read failure: broken symlink, permission denied, … — never fatal.
            text, size, read_error = None, 0, "not-readable"
        if text is None:
            records[rel] = {
                "backlinks": [],
                "bodyTags": [],
                "frontmatter": {},
                "frontmatterErrors": [read_error],
                "headings": [],
                "links": [],
                "sizeBytes": size,
                "tasks": [],
                "title": None,
                "updated": None,
            }
            continue
        lines = text.split("\n")
        fm, errors, body_start, _has_fm = parse_frontmatter(lines)
        title, _tags, updated = typed_fields(fm, errors)
        check_expires(fm, errors)
        links, headings, body_tags, tasks = extract_body(lines, body_start)
        records[rel] = {
            "backlinks": [],
            "bodyTags": body_tags,
            "frontmatter": fm,
            "frontmatterErrors": errors,
            "headings": headings,
            "links": links,
            "sizeBytes": size,
            "tasks": tasks,
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


# §8.3 restricted-note reduction (issue #17). Frontmatter tags only —
# bodyTags are informal (§10.2 posture) and never trigger restriction.
RESTRICTED_TAG = "restricted/private"


def note_frontmatter_tags(rec: dict) -> list[str]:
    tags = rec["frontmatter"].get("tags")
    return tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])


def is_restricted(rec: dict) -> bool:
    return RESTRICTED_TAG in note_frontmatter_tags(rec)


def reduce_restricted(index: dict) -> dict:
    """§8.3: reduce restricted notes for the COMMITTED index — keep
    path/title/frontmatter(tags)/updated/sizeBytes/frontmatterErrors/links/
    backlinks, empty the body-derived fields (headings, bodyTags) the index
    would otherwise re-leak, and strip body prose from link records
    (display alias text, fragments, verbatim raw markup) — only the
    structural target/resolution survives. Emptied/nulled, never omitted:
    the §8.1 shape holds, so no schemaVersion bump. In-memory query indexes
    stay unreduced (§8.3)."""
    for rec in index["notes"].values():
        if is_restricted(rec):
            rec["headings"] = []
            rec["bodyTags"] = []
            rec["tasks"] = []  # §17: task text/metadata is body content
            for link in rec.get("links", []):
                link["display"] = None
                link["fragment"] = None
                target = link.get("target") or ""
                link["raw"] = ("![[%s]]" if link.get("embed") else "[[%s]]") % target
    return index


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
# §15 Vault config (00_Meta/config.yaml) — issue #2.
#
# Module-internal section, deliberately self-contained: the planned `shared`
# module (#31) seeds from here. Public surface for later consumers
# (M9.2–M9.5: #16 report, #15 environments, #26 sync, …):
#
#   load_config(root)              -> (config map, findings)   — never raises
#   parse_config(text)             -> (config map, findings)
#   check_config(root, config, findings) -> (errors, warnings) — validate rows
#   write_exception_prefixes(config) -> tuple of dir prefixes agents may write
#   agent_write_allowed(rel, config) -> bool  (Inbox-first + exceptions)
#   extension_trust(config)        -> policy string (default "first-party")
#   vault_context(config)          -> context string (default "personal")
#   template_version(config)       -> recorded upstream version or None
#
# The config is OPTIONAL: an absent file (or empty/all-comment file) yields
# ({}, []) and every behavior stays at its built-in default. Malformed
# content becomes per-file validate findings on CONFIG_RELPATH — never a
# crash, and never a behavior change beyond ignoring the malformed part.

CONFIG_RELPATH = "00_Meta/config.yaml"
CONFIG_IMPLEMENTED_KEYS = frozenset(
    {
        "context",
        "extension_trust",
        "report",
        "tasks",
        "template_version",
        "write_exceptions",
    }
)
# Named-but-unimplemented keys reserved for the issues that claimed them
# (#15 environments, #32 modules, #18 provenance, #26 sync). Parsed and
# tolerated with no finding, so a forward-looking config never fails an
# older brain.
CONFIG_RESERVED_KEYS = frozenset(
    {
        "environments",
        "modules",
        "provenance",
        "sync",
    }
)
# §16.4: known subkeys of the `report` mapping (values: digits-only scalars).
REPORT_CONFIG_KEYS = frozenset({"inbox_days", "stale_days"})
# §17.4: known subkeys of the `tasks` mapping (issue #28).
TASKS_CONFIG_KEYS = frozenset({"carry_over"})
TASKS_CARRY_OVER_VALUES = frozenset({"off", "on"})
DEFAULT_TASKS_CARRY_OVER = True  # carry_over: on
# Inbox-first defaults (PRD §6.2 / AGENTS.md): always writable, config only
# ever ADDS to this set. Session-scoped carve-outs (onboard-owner interviews,
# agent-generated skills/tools) are policy prose, not path constants.
AGENT_WRITE_DEFAULT_PREFIXES = ("02_Inbox/", "02_Outbox/", "10_Agents/solutions/")
DEFAULT_EXTENSION_TRUST = "first-party"
EXTENSION_TRUST_VALUES = frozenset({"first-party", "relaxed"})
DEFAULT_CONTEXT = "personal"
CONTEXT_VALUES = frozenset({"personal", "work"})

CONFIG_KEY_RE = re.compile(r"^( *)([A-Za-z0-9_-]+):(?:$|\s+(.*)$|\s+$)")


def _cfg_finding(line: int | None, rule: str, message: str) -> dict:
    return {"line": line, "message": message, "rule": rule}


def parse_config(text: str) -> tuple[dict, list[dict]]:
    """Parse the bounded YAML subset (§15.2): scalars, flat lists, one level
    of nested mapping. Best-effort — malformed lines become findings and are
    skipped; parsing never raises."""
    config: dict = {}
    findings: list[dict] = []
    open_key: str | None = None  # top-level key that may still take a block
    open_kind: str | None = None  # None (undecided) | "list" | "map"
    nested_indent = 0
    for lineno, raw in enumerate(text.split("\n"), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        km = CONFIG_KEY_RE.match(raw)
        if km:
            indent, key, value = len(km.group(1)), km.group(2), (km.group(3) or "").strip()
            if indent == 0:
                open_key, open_kind = None, None
                if key in config:
                    findings.append(
                        _cfg_finding(
                            lineno, "config-duplicate-key", f"duplicate key {key!r} (last wins)"
                        )
                    )
                if not value:
                    config[key] = None
                    open_key = key
                elif value.startswith("["):
                    if value.endswith("]") and "[" not in value[1:-1] and "]" not in value[1:-1]:
                        config[key] = split_flow(value[1:-1])
                    else:
                        findings.append(
                            _cfg_finding(
                                lineno,
                                "config-unsupported",
                                f"unparseable flow list for key {key!r}",
                            )
                        )
                else:
                    config[key] = scalar(value)
                continue
            # Indented key line: one nested mapping level under open_key.
            if open_key is None or open_kind == "list":
                findings.append(
                    _cfg_finding(
                        lineno, "config-unsupported", "indented key with no open mapping"
                    )
                )
                continue
            if open_kind is None:
                open_kind = "map"
                nested_indent = indent
                config[open_key] = {}
            elif indent > nested_indent:
                findings.append(
                    _cfg_finding(
                        lineno,
                        "config-nesting-too-deep",
                        "mappings nest at most one level (§15.2)",
                    )
                )
                continue
            mapping = config[open_key]
            if key in mapping:
                findings.append(
                    _cfg_finding(
                        lineno,
                        "config-duplicate-key",
                        f"duplicate nested key {open_key}.{key} (last wins)",
                    )
                )
            if not value:
                mapping[key] = None
            elif value.startswith("["):
                if value.endswith("]") and "[" not in value[1:-1] and "]" not in value[1:-1]:
                    mapping[key] = split_flow(value[1:-1])
                else:
                    findings.append(
                        _cfg_finding(
                            lineno,
                            "config-unsupported",
                            f"unparseable flow list for key {open_key}.{key}",
                        )
                    )
            else:
                mapping[key] = scalar(value)
            continue
        lm = LIST_ITEM_RE.match(raw)
        if lm:
            if open_key is None or open_kind == "map":
                findings.append(
                    _cfg_finding(
                        lineno, "config-list-item-without-key", "list item with no open list"
                    )
                )
                continue
            if open_kind is None:
                open_kind = "list"
                config[open_key] = []
            config[open_key].append(scalar(lm.group(1)))
            continue
        findings.append(
            _cfg_finding(
                lineno, "config-unsupported", "line outside the bounded YAML subset (§15.2)"
            )
        )
    return config, findings


def load_config(root: Path) -> tuple[dict, list[dict]]:
    """Effective raw config for a vault. Absent file -> ({}, []) — the
    defaults; unreadable/undecodable file -> ({}, [finding]). Never raises."""
    path = root / CONFIG_RELPATH
    if not path.exists():
        return {}, []
    try:
        text, _ = load_text(root, CONFIG_RELPATH)
    except OSError:
        return {}, [_cfg_finding(None, "config-not-readable", "config file cannot be read")]
    if text is None:
        return {}, [_cfg_finding(None, "config-not-utf8", "config file is not UTF-8")]
    return parse_config(text)


def write_exception_prefixes(config: dict) -> tuple[str, ...]:
    """Directory prefixes agents may write to: the Inbox-first defaults plus
    any well-formed `write_exceptions` entries (normalized to a trailing /).
    Malformed entries are ignored here — check_config reports them."""
    prefixes = list(AGENT_WRITE_DEFAULT_PREFIXES)
    extras = config.get("write_exceptions")
    for entry in extras if isinstance(extras, list) else []:
        if not isinstance(entry, str):
            continue
        p = nfc(entry.strip()).replace("\\", "/")
        if not p or p.startswith("/") or ".." in p.split("/") or ":" in p:
            continue
        p = p.removeprefix("./").rstrip("/")
        if p in ("", "."):
            # Effectively-empty entry ('.', './') — dropped here, reported
            # by check_config as config-bad-write-exception (same rule).
            continue
        p += "/"
        if p not in prefixes:
            prefixes.append(p)
    return tuple(prefixes)


def agent_write_allowed(rel: str, config: dict) -> bool:
    """Whether an agent may write vault-relative path `rel` under the
    Inbox-first rule plus configured exceptions. The enforcement point for
    harness write-gates; with no config it is exactly current policy."""
    rel = nfc(rel.strip()).replace("\\", "/").removeprefix("./")
    # Fail closed on traversal and non-vault-relative shapes: a prefix match
    # means nothing if the path can climb back out of the allowed directory.
    if rel.startswith("/") or ":" in rel.split("/", 1)[0]:
        return False
    if any(part in ("..", ".") for part in rel.split("/")):
        return False
    return rel.startswith(write_exception_prefixes(config))


def extension_trust(config: dict) -> str:
    """Effective VS Code extension trust policy (PRD §6.5): the configured
    scalar, or the strict template default when absent/malformed."""
    value = config.get("extension_trust")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_EXTENSION_TRUST


def report_thresholds(config: dict) -> dict:
    """Effective §16 health-report thresholds: the `report` config mapping
    (spec §15.3) merged over the built-in defaults. Malformed values fall
    back to the default here — check_config reports them (§15.4)."""
    thresholds = {
        "inboxDays": REPORT_INBOX_TRIAGE_DAYS,
        "staleDays": REPORT_STALE_ACTIVE_DAYS,
    }
    section = config.get("report")
    if isinstance(section, dict):
        for subkey, out in (("inbox_days", "inboxDays"), ("stale_days", "staleDays")):
            value = section.get(subkey)
            v = value.strip() if isinstance(value, str) else ""
            if v.isascii() and v.isdigit():
                thresholds[out] = int(v)
    return thresholds


def tasks_carry_over(config: dict) -> bool:
    """Effective §17.4 daily-note carry-over toggle: `tasks: carry_over:`
    (spec §15.3), default on. Malformed values fall back to the default
    here — check_config reports them (§15.4)."""
    section = config.get("tasks")
    if isinstance(section, dict):
        value = section.get("carry_over")
        if isinstance(value, str) and value.strip() in TASKS_CARRY_OVER_VALUES:
            return value.strip() == "on"
    return DEFAULT_TASKS_CARRY_OVER


def vault_context(config: dict) -> str:
    """Effective vault context (issue #12): the scalar recorded by
    onboard-owner's fork-time specialization step, or the personal default
    when absent/malformed. Parse-and-report only — brain drives no behavior
    from it; templates are specialized at onboarding time, in place."""
    value = config.get("context")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_CONTEXT


def template_version(config: dict) -> str | None:
    """Recorded upstream template version (issue #6, spec §15.3): the
    free-form scalar the sync-upstream skill writes after a completed sync
    and compares against upstream release tags, or None when the fork has
    never recorded one. A record, not a switch — brain drives no behavior
    from it."""
    value = config.get("template_version")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def check_config(
    root: Path, config: dict, findings: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Semantic checks over a parsed config (§15.4). Returns (errors,
    warnings) as validate-shaped findings minus the path (the caller stamps
    CONFIG_RELPATH). Parse findings are errors except duplicate-key."""
    errors: list[dict] = []
    warnings: list[dict] = []
    for f in findings:
        (warnings if f["rule"] == "config-duplicate-key" else errors).append(f)
    for key in sorted(config):
        if key in CONFIG_IMPLEMENTED_KEYS or key in CONFIG_RESERVED_KEYS:
            continue
        warnings.append(
            _cfg_finding(
                None,
                "config-unknown-key",
                f"unknown key {key!r} is ignored (forward compatibility)",
            )
        )
    if "write_exceptions" in config:
        raw = config["write_exceptions"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, list):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "write_exceptions must be a list of directory paths",
                )
            )
        else:
            for entry in raw:
                p = nfc(entry.strip()).replace("\\", "/") if isinstance(entry, str) else ""
                # Normalize BEFORE judging, mirroring write_exception_prefixes,
                # so an entry that normalizes to nothing ('.', './') is
                # reported instead of silently granting nothing (§15.4).
                bad = not p or p.startswith("/") or ".." in p.split("/") or ":" in p
                p = p.removeprefix("./").rstrip("/")
                if bad or p in ("", "."):
                    errors.append(
                        _cfg_finding(
                            None,
                            "config-bad-write-exception",
                            f"write_exceptions entry {entry!r} is not a "
                            "vault-relative directory path (the vault root "
                            "itself cannot be granted)",
                        )
                    )
                    continue
                if not (root / p).is_dir():
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-missing-directory",
                            f"write_exceptions entry {entry!r} names no existing directory",
                        )
                    )
    if "report" in config:
        raw = config["report"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, dict):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "report must be a nested mapping of thresholds (§16.4)",
                )
            )
        else:
            for subkey in sorted(raw):
                value = raw[subkey]
                if subkey not in REPORT_CONFIG_KEYS:
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-unknown-key",
                            f"unknown key 'report.{subkey}' is ignored "
                            "(forward compatibility)",
                        )
                    )
                    continue
                if value is None:
                    continue  # explicit empty — same as absent
                if not (
                    isinstance(value, str)
                    and value.strip().isascii()
                    and value.strip().isdigit()
                ):
                    errors.append(
                        _cfg_finding(
                            None,
                            "config-invalid-value",
                            f"report.{subkey} must be a non-negative integer "
                            "number of days",
                        )
                    )
    if "tasks" in config:
        raw = config["tasks"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, dict):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "tasks must be a nested mapping of task-module settings (§17.4)",
                )
            )
        else:
            for subkey in sorted(raw):
                value = raw[subkey]
                if subkey not in TASKS_CONFIG_KEYS:
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-unknown-key",
                            f"unknown key 'tasks.{subkey}' is ignored "
                            "(forward compatibility)",
                        )
                    )
                    continue
                if value is None:
                    continue  # explicit empty — same as absent
                if not isinstance(value, str):
                    errors.append(
                        _cfg_finding(
                            None,
                            "config-invalid-value",
                            f"tasks.{subkey} must be a scalar string",
                        )
                    )
                elif value.strip() not in TASKS_CARRY_OVER_VALUES:
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-unknown-value",
                            f"tasks.{subkey} {value!r} is not a documented "
                            "value (on | off)",
                        )
                    )
    if "extension_trust" in config:
        raw = config["extension_trust"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, str):
            errors.append(
                _cfg_finding(
                    None, "config-invalid-value", "extension_trust must be a scalar string"
                )
            )
        elif raw.strip() not in EXTENSION_TRUST_VALUES:
            warnings.append(
                _cfg_finding(
                    None,
                    "config-unknown-value",
                    f"extension_trust {raw!r} is not a documented policy "
                    "(first-party | relaxed)",
                )
            )
    if "template_version" in config:
        raw = config["template_version"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, str):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "template_version must be a scalar version string",
                )
            )
        # Free-form by design (§15.3): any scalar is a documented value,
        # so there is no config-unknown-value warning for this key.
    if "context" in config:
        raw = config["context"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, str):
            errors.append(
                _cfg_finding(
                    None, "config-invalid-value", "context must be a scalar string"
                )
            )
        elif raw.strip() not in CONTEXT_VALUES:
            warnings.append(
                _cfg_finding(
                    None,
                    "config-unknown-value",
                    f"context {raw!r} is not a documented context "
                    "(personal | work)",
                )
            )
    return errors, warnings


# ---------------------------------------------------------------------------
# §10.5 Secret scanning

# Inline allowlist: an HTML comment containing this token on the SAME line
# suppresses every secret finding on that line — the committed marker is the
# audit trail for an intentional example.
SECRET_ALLOW_MARKER = "brain:allow-secret-pattern"
SECRET_ALLOW_RE = re.compile(r"<!--[^\n]*" + re.escape(SECRET_ALLOW_MARKER) + r"[^\n]*-->")

# Data-driven rule table (§10.5): (name, compiled pattern). Every finding is
# an ERROR with rule `secret-<name>`. Extending detection is a table edit —
# add a row here and a row to the spec.md §10.5 table in the same commit.
# Patterns are written so they never match their own source text, keeping the
# repo self-scan clean by construction.
SECRET_RULES: tuple[tuple[str, re.Pattern], ...] = (
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[a-z]-[A-Za-z0-9-]{10,}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "generic-credential",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|secret|token|passwd|password)"""
            r"""\s*[:=]\s*["'](?=[^"']*\d)[A-Za-z0-9_\-+/=]{12,}["']"""
        ),
    ),
    (
        "high-entropy-string",
        re.compile(
            r"""[:=]\s*["'](?=[^"']*[a-z])(?=[^"']*[A-Z])(?=[^"']*\d)"""
            r"""[A-Za-z0-9+/]{40,}={0,2}["']"""
        ),
    ),
)


def scan_secrets(root: Path, paths: list[str]) -> list[dict]:
    """§10.5: secret findings over every text file in the working corpus.

    Binary files (NUL byte in the first 8 KiB) are skipped; text is decoded
    UTF-8 with replacement and newline-normalized per §3, so line numbers
    match the rest of validate. One finding per (line, rule); the matched
    text is never echoed into the message."""
    findings: list[dict] = []
    for rel in sorted(paths):
        try:
            raw = (root / rel).read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue
        text = raw.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        for lineno, line in enumerate(text.split("\n"), start=1):
            if SECRET_ALLOW_RE.search(line):
                continue
            for name, pattern in SECRET_RULES:
                if pattern.search(line):
                    findings.append(
                        {
                            "line": lineno,
                            "message": (
                                f"matches secret rule {name!r} — remove the "
                                "credential, or mark an intentional example "
                                "with an HTML comment containing "
                                f"{SECRET_ALLOW_MARKER} on this line"
                            ),
                            "path": rel,
                            "rule": f"secret-{name}",
                        }
                    )
    return findings


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

    # §15 vault config: parse + semantic findings land on the config file
    # itself (per-file, never a crash); write_exception_prefixes(config) is
    # where the Inbox-first write-destination policy is materialized for
    # enforcement (harness write-gates call agent_write_allowed).
    config, cfg_findings = load_config(root)
    cfg_errors, cfg_warnings = check_config(root, config, cfg_findings)
    for f in cfg_errors:
        err(CONFIG_RELPATH, f["rule"], f["message"], f["line"])
    for f in cfg_warnings:
        warn(CONFIG_RELPATH, f["rule"], f["message"], f["line"])

    errors.extend(scan_secrets(root, notes + assets))

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

    # §8.3/§10.2 restricted containment: notes tagged restricted/private
    # (frontmatter tags only — bodyTags never trigger restriction).
    restricted_paths = {p for p, r in index["notes"].items() if is_restricted(r)}

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
                elif rule == "invalid-expires" and template and has_placeholder(
                    fm.get("expires")
                ):
                    continue
                else:
                    err(rel, rule, fe)
            if {"not-utf8", "not-readable"} & set(rec["frontmatterErrors"]):
                # §10.2: the read/decode failure is the note's only finding —
                # frontmatter was never read, so derived missing-* checks
                # would be false claims that bury the actual cause.
                pass
            elif not fm:
                if "unterminated-frontmatter" not in rec["frontmatterErrors"]:
                    err(rel, "missing-frontmatter", "note has no frontmatter block")
            else:
                if rec["title"] is None and not (
                    template and has_placeholder(fm.get("title"))
                ):
                    err(rel, "missing-title", "frontmatter lacks a title string")
                raw_tags = fm.get("tags")
                if raw_tags is None or raw_tags == []:
                    # §10.2: an explicitly empty list declares no tags — same
                    # missing-tags error as an absent/null key. The per-value
                    # template exemption cannot apply: no values to exempt.
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
                # §10.2 missing-author (issue #18 provenance): an Inbox note
                # tagged as agent-authored draft should say which harness wrote
                # it. Warning only — absence elsewhere means pre-convention or
                # human-authored. Template placeholders satisfy per §10.3, and
                # `09_Templates/` never sits under `02_Inbox/` anyway.
                if (
                    rel.startswith("02_Inbox/")
                    and not template
                    and "audience/agent" in tags
                    and "workflow/draft" in tags
                    and not fm.get("author")
                ):
                    warn(
                        rel,
                        "missing-author",
                        "agent-authored Inbox note has no author: field "
                        "(see conventions § Provenance)",
                    )

        # §17.2 task-invalid-date: a date-bearing task emoji whose value is
        # not a real YYYY-MM-DD. Warning only — tasks are informal body
        # content (same posture as bodyTags); template placeholders exempt.
        for task in rec["tasks"]:
            if template and "{{" in task["text"]:
                continue
            for field in task["malformed"]:
                warn(
                    rel,
                    "task-invalid-date",
                    f"task {field} metadata is not a real YYYY-MM-DD date",
                    task["line"],
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
                if link["resolved"] in restricted_paths and rel not in restricted_paths:
                    # §10.2 restricted-link (issue #17): context bleed —
                    # restricted -> restricted links stay clean.
                    warn(
                        rel,
                        "restricted-link",
                        f"{link['raw']} links a restricted/private note "
                        f"({link['resolved']}) from a non-restricted one — "
                        "never quote or summarize its content here",
                        link["line"],
                    )
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

    if VALIDATE_CURATION_WARNINGS:
        cur = compute_curation(root, index, today())
        for rel in cur["missingExpires"]:
            warn(rel, "missing-expires", "no expires: date (see conventions § Expiration)")
        for row in cur["beyondCap"]:
            warn(
                row["path"],
                "expires-beyond-cap",
                f"expires {row['expires']} is more than a year after updated {row['updated']}",
            )
        for row in cur["oversized"]:
            warn(
                row["path"],
                "oversized",
                f"{row['sizeBytes']} bytes / {row['lines']} lines exceeds "
                f"{CURATE_MAX_BYTES} bytes / {CURATE_MAX_LINES} lines — split candidate",
            )
        ctx = context_report(root)
        for row in ctx["docs"]:
            if row["sizeBytes"] is not None and row["sizeBytes"] > row["budget"]:
                warn(
                    row["path"],
                    "bootstrap-budget",
                    f"{row['sizeBytes']} bytes exceeds its {row['budget']}-byte bootstrap budget",
                )
        if ctx["totalBytes"] > ctx["totalBudget"]:
            warn(
                "AGENTS.md",
                "bootstrap-budget-total",
                f"bootstrap docs total {ctx['totalBytes']} bytes, budget {ctx['totalBudget']}",
            )

    if check_index:
        tnotes, tassets = index_corpus(root)
        fresh = serialize(reduce_restricted(build_index(root, tnotes, tassets)))
        index_path = root / INDEX_RELPATH
        if not index_path.exists() or index_path.read_bytes() != fresh:
            err(INDEX_RELPATH, "stale-index", "stale index — run `brain index`")

    def key(f: dict):
        return (f["path"], 0 if f["line"] is None else 1, f["line"] or 0, f["rule"])

    return sorted(errors, key=key), sorted(warnings, key=key)


# ---------------------------------------------------------------------------
# §14 Curation signals


def today() -> date:
    return date.today()


def path_exempt_from_expires(rel: str) -> bool:
    """Directory/path-based exemption: notes reached by convention, not by
    inbound links (Inbox, Journal, Archives, Templates, solutions, Outbox)."""
    return rel in EXPIRES_EXEMPT_PATHS or rel.startswith(EXPIRES_EXEMPT_PREFIXES)


def note_type_tags(fm: dict) -> set[str]:
    tags = fm.get("tags")
    tags = tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])
    return {t.split("/", 1)[1] for t in tags if isinstance(t, str) and t.startswith("type/")}


def expires_exempt(rel: str, fm: dict) -> bool:
    """Whether a note is exempt from carrying an expires: date — by path, or
    by an event-record type tag (e.g. type/decision)."""
    return path_exempt_from_expires(rel) or bool(
        note_type_tags(fm) & EXPIRES_EXEMPT_TYPE_TAGS
    )


def compute_curation(root: Path, index: dict, today_d: date) -> dict:
    """All re-review signals, deterministic given the tree and today's date.
    Detection lives here; the judgment lives in the curate skill."""
    notes = index["notes"]
    expired: list[dict] = []
    missing: list[str] = []
    beyond_cap: list[dict] = []
    oversized: list[dict] = []
    stale: list[dict] = []
    orphans: list[str] = []
    for rel in sorted(notes):
        rec = notes[rel]
        fm = rec["frontmatter"]
        if rel == "CLAUDE.md":
            continue
        exp_d = iso_date(fm.get("expires"))
        upd_d = iso_date(rec["updated"])
        if exp_d:
            if exp_d < today_d:
                expired.append(
                    {"expires": fm["expires"], "path": rel, "title": rec["title"]}
                )
            if upd_d and (exp_d - upd_d).days > EXPIRES_CAP_DAYS:
                beyond_cap.append(
                    {"expires": fm["expires"], "path": rel, "updated": rec["updated"]}
                )
        elif "expires" not in fm and fm and not expires_exempt(rel, fm) and not is_template(rel):
            missing.append(rel)
        if not (rel in OVERSIZED_EXEMPT_PATHS or rel.startswith("07_Archives/")):
            try:
                text, _ = load_text(root, rel)
            except OSError:  # §3 read failure: skip, best-effort
                text = None
            lines = len(text.splitlines()) if text else 0
            if rec["sizeBytes"] > CURATE_MAX_BYTES or lines > CURATE_MAX_LINES:
                oversized.append(
                    {"lines": lines, "path": rel, "sizeBytes": rec["sizeBytes"]}
                )
        if upd_d:
            days = (today_d - upd_d).days
            if days > CURATE_STALE_DAYS:
                stale.append(
                    {
                        "backlinks": len(rec["backlinks"]),
                        "daysOld": days,
                        "path": rel,
                        "score": days * (1 + len(rec["backlinks"])),
                        "updated": rec["updated"],
                    }
                )
        if (
            not rec["backlinks"]
            and not path_exempt_from_expires(rel)
            and rel not in ORPHAN_EXEMPT_PATHS
        ):
            orphans.append(rel)
    stale.sort(key=lambda r: (-r["score"], r["path"]))
    referenced = {
        link["resolved"]
        for rec in notes.values()
        for link in rec["links"]
        if link["resolved"]
    }
    unreferenced_assets = [
        a
        for a in index["assets"]
        if a.startswith("08_Assets/") and a not in referenced
    ]
    return {
        "beyondCap": beyond_cap,
        "expired": expired,
        "missingExpires": missing,
        "orphans": orphans,
        "oversized": oversized,
        "stale": stale,
        "unreferencedAssets": unreferenced_assets,
    }


def context_report(root: Path) -> dict:
    """R20: bootstrap docs' actual sizes against their byte budgets."""
    docs: list[dict] = []
    total = 0
    for rel in sorted(BOOTSTRAP_BUDGETS):
        budget = BOOTSTRAP_BUDGETS[rel]
        try:
            _, size = load_text(root, rel)
        except OSError:
            size = None
        if size is not None:
            total += size
        docs.append({"budget": budget, "path": rel, "sizeBytes": size})
    return {"docs": docs, "totalBudget": BOOTSTRAP_TOTAL_BUDGET, "totalBytes": total}


# ---------------------------------------------------------------------------
# §16 Health report

INBOX_PREFIX = "02_Inbox/"
# Boundary lookahead: '2026-08-1234-note.md' must NOT parse as 2026-08-12.
INBOX_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?=[-.]|$)")
REPORT_BUCKET_LABELS = ("0-7d", "8-30d", "31-90d", "90+d", "unknown")
REPORT_ORPHAN_EXEMPT_BASENAMES = frozenset({"AGENTS.md", "CLAUDE.md", "README.md"})
REPORT_ORPHAN_EXEMPT_PREFIXES = ("07_Archives/", "09_Templates/")


def frontmatter_tags(rec: dict) -> list[str]:
    """§16.1: a note's frontmatter tags (bare scalar coerced per §4.5),
    template placeholders excluded. Body #tags are informal — never counted."""
    tags = rec["frontmatter"].get("tags")
    tags = tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])
    return [t for t in tags if isinstance(t, str) and "{{" not in t]


def is_abbreviation(short: str, long: str) -> bool:
    """§16.1 near-duplicate heuristic: `short` (folded, ≥ 2 chars, strictly
    shorter) shares its first character with `long` and is an in-order
    subsequence of it — catches both prefixes (`tool`/`tools`) and
    abbreviations (`sw`/`software`)."""
    if len(short) < 2 or len(short) >= len(long) or short[0] != long[0]:
        return False
    it = iter(long)
    return all(ch in it for ch in short)


def age_bucket(days: int) -> str:
    if days <= 7:
        return "0-7d"
    if days <= 30:
        return "8-30d"
    if days <= 90:
        return "31-90d"
    return "90+d"


def compute_report(
    index: dict,
    today_d: date,
    thresholds: dict,
    taxonomy: dict[str, list[str] | None] | None,
    since_d: date | None = None,
) -> dict:
    """§16: the five vault-health sections, synthesized from the in-memory
    index — no new parsing, deterministic given tree + config + date."""
    notes = index["notes"]

    def in_window(rec: dict) -> bool:
        # §16.3: --since scopes tag drift and unresolved links only.
        if since_d is None:
            return True
        upd = iso_date(rec["updated"])
        return upd is not None and upd >= since_d

    # 1. Stale-active + 2. Orphans (whole vault, never --since-scoped).
    stale_active: list[dict] = []
    orphans: list[str] = []
    for rel in sorted(notes):
        rec = notes[rel]
        upd_d = iso_date(rec["updated"])
        if "status/active" in frontmatter_tags(rec) and upd_d is not None:
            days = (today_d - upd_d).days
            if days > thresholds["staleDays"]:
                stale_active.append(
                    {
                        "daysOld": days,
                        "path": rel,
                        "title": rec["title"],
                        "updated": rec["updated"],
                    }
                )
        outgoing = any(not l["placeholder"] for l in rec["links"])
        if (
            not rec["backlinks"]
            and not outgoing
            and rel.rsplit("/", 1)[-1] not in REPORT_ORPHAN_EXEMPT_BASENAMES
            and not rel.startswith(REPORT_ORPHAN_EXEMPT_PREFIXES)
        ):
            orphans.append(rel)
    stale_active.sort(key=lambda r: (-r["daysOld"], r["path"]))

    # 3. Inbox aging (whole vault, never --since-scoped).
    buckets: dict[str, list[dict]] = {label: [] for label in REPORT_BUCKET_LABELS}
    triage_debt: list[str] = []
    for rel in sorted(notes):
        if not rel.startswith(INBOX_PREFIX):
            continue
        name = rel.rsplit("/", 1)[-1]
        if name == "README.md":
            continue
        rec = notes[rel]
        m = INBOX_DATE_PREFIX_RE.match(name)
        captured = iso_date(m.group(1)) if m else None
        if captured is not None:
            source = "filename"
        else:
            captured = iso_date(rec["updated"])
            source = "updated" if captured is not None else "unknown"
        if captured is None:
            buckets["unknown"].append({"ageDays": None, "path": rel, "source": source})
            continue
        days = max(0, (today_d - captured).days)
        buckets[age_bucket(days)].append(
            {"ageDays": days, "path": rel, "source": source}
        )
        if days > thresholds["inboxDays"]:
            triage_debt.append(rel)

    # 4. Tag drift (--since-scoped) — same taxonomy machinery as validate.
    counts: dict[str, int] = {}
    for rel in sorted(notes):
        rec = notes[rel]
        if not in_window(rec):
            continue
        for tag in sorted(set(frontmatter_tags(rec))):
            counts[tag] = counts.get(tag, 0) + 1
    unknown: list[dict] = []
    single_use: list[str] = []
    near_duplicates: list[dict] = []
    if taxonomy is not None:
        open_values: dict[str, set[str]] = {}
        for tag in sorted(counts):
            if "/" not in tag:
                unknown.append({"count": counts[tag], "reason": "not-namespaced", "tag": tag})
                continue
            namespace, value = tag.split("/", 1)
            if namespace not in taxonomy:
                unknown.append(
                    {"count": counts[tag], "reason": "unknown-namespace", "tag": tag}
                )
            elif taxonomy[namespace] is not None and value not in taxonomy[namespace]:
                unknown.append(
                    {"count": counts[tag], "reason": "unknown-value", "tag": tag}
                )
            else:
                if taxonomy[namespace] is None:
                    open_values.setdefault(namespace, set()).add(value)
                    if counts[tag] == 1:
                        single_use.append(tag)
        for namespace in sorted(open_values):
            values = sorted(open_values[namespace])
            for a in values:
                for b in values:
                    if a != b and is_abbreviation(fold(a), fold(b)):
                        near_duplicates.append({"namespace": namespace, "values": [a, b]})

    # 5. Unresolved links (--since-scoped) — same population validate errors on.
    unresolved: list[dict] = []
    for rel in sorted(notes):
        rec = notes[rel]
        if not in_window(rec):
            continue
        for link in rec["links"]:
            if not link["placeholder"] and link["resolved"] is None:
                unresolved.append(
                    {"line": link["line"], "path": rel, "target": link["target"]}
                )
    unresolved.sort(key=lambda r: (r["path"], r["line"], r["target"]))

    return {
        "inboxAging": {"buckets": buckets, "triageDebt": triage_debt},
        "orphans": orphans,
        "since": since_d.isoformat() if since_d else None,
        "staleActive": stale_active,
        "tagDrift": {
            "nearDuplicates": near_duplicates,
            "singleUse": single_use,
            "taxonomyReadable": taxonomy is not None,
            "unknown": unknown,
        },
        "thresholds": dict(sorted(thresholds.items())),
        "unresolvedLinks": {"count": len(unresolved), "links": unresolved},
    }


URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")


def collect_urls(root: Path, notes: list[str]) -> dict[str, str]:
    """url -> first note path mentioning it. Frontmatter and code (fenced
    blocks + inline spans) are excluded, matching the link/tag extractors —
    so example URLs in code samples are never probed as source URLs."""
    found: dict[str, str] = {}
    for rel in notes:
        try:
            text, _ = load_text(root, rel)
        except OSError:  # §3 read failure: skip, best-effort
            continue
        if text is None:
            continue
        lines = text.split("\n")
        _fm, _errs, body_start, _has = parse_frontmatter(lines)
        for _lineno, _raw, masked in body_lines_masked(lines, body_start):
            for m in URL_RE.finditer(masked):
                url = m.group(0).rstrip(".,;:!?")
                found.setdefault(url, rel)
    return found


def check_urls(root: Path, notes: list[str]) -> list[dict]:
    """Opt-in (network): dead source URLs. Never runs pre-commit."""
    import urllib.error
    import urllib.request

    dead: list[dict] = []
    urls = collect_urls(root, notes)
    for url in sorted(urls):
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "brain-curate/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.HTTPError as e:
            if e.code in (403, 405):  # HEAD-hostile hosts are not dead links
                continue
            dead.append({"error": f"HTTP {e.code}", "path": urls[url], "url": url})
        except (urllib.error.URLError, OSError, ValueError) as e:
            dead.append({"error": str(e), "path": urls[url], "url": url})
    return dead


# ---------------------------------------------------------------------------
# §18 Semantic search (QMD — issue #8)
#
# Module-internal store section: the sidecar (EMBED_RELPATH, gitignored) is
# read and written ONLY here, and only `embed` and `search --semantic` ever
# touch it — index/validate output is provably unaffected (§17.5). The one
# sanctioned optional non-stdlib dependency (sentence-transformers) is
# imported lazily inside local_embedder(); every other path is stdlib.

EMBED_SCHEMA_VERSION = 1
EMBED_LOCAL_MODEL_DEFAULT = "all-MiniLM-L6-v2"
# §18.4 hybrid ranking weights: score = 0.7·sem + 0.3·kw, rounded to 6 dp.
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3
SEMANTIC_TOP_DEFAULT = 10


def note_content_hash(text: str) -> str:
    """§17.1: SHA-256 hex over the note's full normalized text (§3)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _empty_store() -> dict:
    return {"dim": None, "model": None, "notes": {}, "schemaVersion": EMBED_SCHEMA_VERSION}


def _valid_vector(v, dim: int | None = None) -> bool:
    """A non-empty list of finite numbers (bools excluded), optionally of
    exactly `dim` components."""
    return (
        isinstance(v, list)
        and bool(v)
        and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
            for x in v
        )
        and (dim is None or len(v) == dim)
    )


def load_embeddings(root: Path) -> dict:
    """§18.2: best-effort sidecar load. Missing file -> empty store; any
    malformed content is treated as absent with a stderr notice. Never raises."""

    def ignored(reason: str) -> dict:
        print(
            f"warning: ignoring embeddings sidecar ({reason}) — "
            "regenerate it with `brain embed`",
            file=sys.stderr,
        )
        return _empty_store()

    path = root / EMBED_RELPATH
    if not path.exists():
        return _empty_store()
    try:
        raw = path.read_bytes()
    except OSError:
        return ignored("not readable")
    try:
        store = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ignored("not valid JSON")
    if not isinstance(store, dict) or store.get("schemaVersion") != EMBED_SCHEMA_VERSION:
        return ignored("unknown schemaVersion")
    dim, model, entries = store.get("dim"), store.get("model"), store.get("notes")
    if not (
        isinstance(dim, int)
        and not isinstance(dim, bool)
        and dim > 0
        and isinstance(model, str)
        and model
        and isinstance(entries, dict)
    ):
        return ignored("invalid shape")
    for rel, entry in entries.items():
        if not (
            isinstance(rel, str)
            and isinstance(entry, dict)
            and isinstance(entry.get("hash"), str)
            and _valid_vector(entry.get("vector"), dim)
        ):
            return ignored("invalid entry shape")
    return {"dim": dim, "model": model, "notes": entries, "schemaVersion": EMBED_SCHEMA_VERSION}


def save_embeddings(root: Path, store: dict) -> None:
    """§17.1 serialization: like the index (§8.2) but floats are allowed."""
    path = root / EMBED_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")
    )


def cosine(a: list[float], b: list[float]) -> float:
    """§18.4 cosine similarity; zero-magnitude vectors give 0.0."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def note_hashes(root: Path, index: dict) -> dict[str, str | None]:
    """path -> current content hash; None for notes that cannot be read or
    decoded (§3) — such notes are never embeddable."""
    hashes: dict[str, str | None] = {}
    for rel in index["notes"]:
        try:
            text, _ = load_text(root, rel)
        except OSError:
            text = None
        hashes[rel] = None if text is None else note_content_hash(text)
    return hashes


def fresh_entries(index: dict, store: dict, hashes: dict) -> dict[str, list[float]]:
    """§18.2 freshness ∩ §18.1 restricted containment: path -> vector for
    every sidecar entry that is current (note exists, hash matches, length
    == dim) and whose note is not currently restricted/private. Everything
    else is stale — excluded, never re-ranked."""
    fresh: dict[str, list[float]] = {}
    for rel, entry in store["notes"].items():
        rec = index["notes"].get(rel)
        if rec is None or is_restricted(rec):
            continue
        if (
            hashes.get(rel) is not None
            and entry["hash"] == hashes[rel]
            and len(entry["vector"]) == store["dim"]
        ):
            fresh[rel] = entry["vector"]
    return fresh


def embeddable_notes(index: dict, hashes: dict) -> list[str]:
    """§18.3: the embeddable universe — readable, non-restricted notes."""
    return sorted(
        rel
        for rel, rec in index["notes"].items()
        if hashes[rel] is not None and not is_restricted(rec)
    )


def local_embedder(model_name: str):
    """§17.3: the ONE sanctioned optional non-stdlib dependency
    (sentence-transformers), imported lazily and only here. Returns a
    texts -> vectors callable, or None when the import or model load fails —
    callers degrade cleanly, never crash."""
    try:
        from sentence_transformers import SentenceTransformer  # optional — §17.3
    except Exception:
        return None
    try:
        model = SentenceTransformer(model_name)
    except Exception:
        return None

    def encode(texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vec] for vec in model.encode(texts)]

    return encode


def cmd_embed(root: Path, args) -> int:
    """§18.3: maintain the embeddings sidecar (--stdin-json / --local /
    --status). Exit 0 success, 1 operational error; the sidecar is written
    only on a fully-validated update."""
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    store = load_embeddings(root)
    hashes = note_hashes(root, index)

    if args.status:
        fresh = fresh_entries(index, store, hashes)
        universe = embeddable_notes(index, hashes)
        payload = {
            "dim": store["dim"],
            "embedded": len(fresh),
            "missing": len([r for r in universe if r not in store["notes"]]),
            "model": store["model"],
            "notes": len(universe),
            "present": (root / EMBED_RELPATH).exists(),
            "stale": len([r for r in store["notes"] if r not in fresh]),
        }
        emit(
            payload,
            args.json,
            [
                f"sidecar: {EMBED_RELPATH} "
                f"({'present' if payload['present'] else 'absent'})",
                f"model: {payload['model']}  dim: {payload['dim']}",
                f"embeddable notes: {payload['notes']}  fresh: {payload['embedded']}  "
                f"stale: {payload['stale']}  missing: {payload['missing']}",
            ],
        )
        return 0

    if args.stdin_json:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"error: --stdin-json input is not valid JSON: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, dict) or set(data) != {"model", "vectors"}:
            print(
                'error: input must be an object with exactly the keys "model" and "vectors"',
                file=sys.stderr,
            )
            return 1
        if not (isinstance(data["model"], str) and data["model"].strip()):
            print("error: model must be a non-empty string", file=sys.stderr)
            return 1
        if not (isinstance(data["vectors"], dict) and data["vectors"]):
            print(
                "error: vectors must be a non-empty object of note path -> number array",
                file=sys.stderr,
            )
            return 1
        model = data["model"].strip()
        vectors: dict[str, list[float]] = {}
        dim: int | None = None
        unknown: list[str] = []
        for key in sorted(data["vectors"]):
            vec = data["vectors"][key]
            if not _valid_vector(vec):
                print(
                    f"error: vector for {key!r} must be a non-empty array of finite numbers",
                    file=sys.stderr,
                )
                return 1
            if dim is None:
                dim = len(vec)
            elif len(vec) != dim:
                print(
                    f"error: vector for {key!r} has length {len(vec)}, expected {dim} "
                    "— all vectors must share one dimension",
                    file=sys.stderr,
                )
                return 1
            rel = nfc(key.strip()).replace("\\", "/").removeprefix("./")
            if rel not in index["notes"]:
                unknown.append(key)
                continue
            vectors[rel] = [float(x) for x in vec]
        if unknown:
            print(
                "error: unknown note paths (nothing written): " + ", ".join(unknown),
                file=sys.stderr,
            )
            return 1
        skipped_restricted = sorted(
            rel for rel in vectors if is_restricted(index["notes"][rel])
        )
        for rel in skipped_restricted:
            del vectors[rel]
            print(
                f"notice: skipping restricted note {rel} — restricted/private "
                "content never enters the embeddings sidecar (spec §18.1)",
                file=sys.stderr,
            )
        skipped_unreadable = sorted(rel for rel in vectors if hashes[rel] is None)
        for rel in skipped_unreadable:
            del vectors[rel]
            print(
                f"notice: skipping unreadable note {rel} — no text to hash (spec §17.3)",
                file=sys.stderr,
            )
        if store["notes"] and (store["model"] != model or store["dim"] != dim):
            print(
                f"notice: model/dim changed ({store['model']}/{store['dim']} -> "
                f"{model}/{dim}) — replacing the sidecar wholesale (spec §18.3)",
                file=sys.stderr,
            )
            merged: dict[str, dict] = {}
        else:
            merged = dict(store["notes"])
        for rel, vec in vectors.items():
            merged[rel] = {"hash": hashes[rel], "vector": vec}
        save_embeddings(
            root,
            {"dim": dim, "model": model, "notes": merged, "schemaVersion": EMBED_SCHEMA_VERSION},
        )
        payload = {
            "dim": dim,
            "model": model,
            "path": EMBED_RELPATH,
            "skippedRestricted": skipped_restricted,
            "skippedUnreadable": skipped_unreadable,
            "stored": len(vectors),
        }
        emit(
            payload,
            args.json,
            [
                f"stored {len(vectors)} vectors (model {model}, dim {dim}) "
                f"-> {EMBED_RELPATH}"
            ]
            + [f"skipped restricted: {r}" for r in skipped_restricted]
            + [f"skipped unreadable: {r}" for r in skipped_unreadable],
        )
        return 0

    # --local (§17.3): the offline path via the optional dependency.
    model_name = args.model or store["model"] or EMBED_LOCAL_MODEL_DEFAULT
    encode = local_embedder(model_name)
    if encode is None:
        print(
            "error: local embedding model unavailable — install the optional "
            "`sentence-transformers` package, pipe precomputed vectors via "
            "`brain embed --stdin-json`, or use keyword `brain search` (spec §18.3)",
            file=sys.stderr,
        )
        return 1
    if store["notes"] and store["model"] != model_name:
        print(
            f"notice: model changed ({store['model']} -> {model_name}) — "
            "replacing the sidecar wholesale (spec §18.3)",
            file=sys.stderr,
        )
        store = _empty_store()
    fresh = fresh_entries(index, store, hashes)
    todo = [rel for rel in embeddable_notes(index, hashes) if rel not in fresh]
    texts: list[str] = []
    for rel in todo:
        text, _ = load_text(root, rel)  # readable by construction (hash present)
        texts.append(text)
    vecs = encode(texts) if todo else []
    dim = store["dim"]
    merged = {rel: store["notes"][rel] for rel in fresh}
    if not todo and not merged:
        # Nothing to embed and nothing retained: writing a {"dim": null}
        # store would be shape-invalid (§18.1) — report and leave it absent.
        print("nothing to embed — sidecar unchanged", file=sys.stderr)
        return 0
    for rel, vec in zip(todo, vecs):
        if dim is None:
            dim = len(vec)
        merged[rel] = {"hash": hashes[rel], "vector": vec}
    save_embeddings(
        root,
        {"dim": dim, "model": model_name, "notes": merged, "schemaVersion": EMBED_SCHEMA_VERSION},
    )
    payload = {
        "dim": dim,
        "embedded": len(todo),
        "model": model_name,
        "path": EMBED_RELPATH,
        "total": len(merged),
    }
    emit(
        payload,
        args.json,
        [
            f"embedded {len(todo)} notes (model {model_name}, dim {dim}), "
            f"{len(merged)} total -> {EMBED_RELPATH}"
        ],
    )
    return 0


def semantic_search(root: Path, index: dict, args) -> int:
    """§18.4: hybrid semantic+keyword note ranking, degrading to the plain
    keyword search (exit 0, identical output shape) whenever semantic
    ranking is impossible."""
    store = load_embeddings(root)
    hashes = note_hashes(root, index)
    fresh = fresh_entries(index, store, hashes)

    def degrade(reason: str) -> int:
        print(
            f"notice: semantic search unavailable ({reason}) — falling back to "
            "keyword search; populate the sidecar with `brain embed` (spec §18.4)",
            file=sys.stderr,
        )
        emit_keyword_hits(keyword_hits(root, index, args.query, args.tag), args.json)
        return 0

    if not fresh:
        return degrade("no fresh embeddings")

    qvec: list[float] | None = None
    if args.query_vector:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"error: --query-vector stdin is not valid JSON: {e}", file=sys.stderr)
            return 1
        if not _valid_vector(data):
            print(
                "error: --query-vector must be a non-empty JSON array of finite numbers",
                file=sys.stderr,
            )
            return 1
        if len(data) != store["dim"]:
            print(
                f"error: --query-vector has length {len(data)}, store dim is {store['dim']}",
                file=sys.stderr,
            )
            return 1
        qvec = [float(x) for x in data]
    else:
        encode = local_embedder(store["model"])
        if encode is not None:
            try:
                qvec = encode([args.query])[0]
            except Exception:
                qvec = None
            if qvec is not None and len(qvec) != store["dim"]:
                qvec = None
    if qvec is None:
        return degrade("no query embedding source")

    kw_counts: dict[str, int] = {}
    for h in keyword_hits(root, index, args.query, args.tag):
        kw_counts[h["path"]] = kw_counts.get(h["path"], 0) + 1
    rows: list[dict] = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if args.tag and not all(tag_matches(t, effective_tags(rec)) for t in args.tag):
            continue
        vec = fresh.get(rel)
        kw = kw_counts.get(rel, 0)
        if vec is None and kw == 0:
            continue
        sem_raw = 0.0 if vec is None else (cosine(qvec, vec) + 1) / 2
        rows.append(
            {
                "keywordHits": kw,
                "path": rel,
                "score": round(
                    SEMANTIC_WEIGHT * sem_raw + KEYWORD_WEIGHT * (1.0 if kw else 0.0), 6
                ),
                "semanticScore": None if vec is None else round(sem_raw, 6),
                "title": rec["title"],
            }
        )
    rows.sort(key=lambda r: (-r["score"], r["path"]))
    rows = rows[: args.top]
    emit(
        rows,
        args.json,
        (
            f"{r['score']:.6f}  {r['path']}" + (f"  ({r['title']})" if r["title"] else "")
            for r in rows
        ),
    )
    return 0


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
    data = serialize(reduce_restricted(build_index(root, notes, assets)))
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


def keyword_hits(root: Path, index: dict, query: str, tag_filters: list[str]) -> list[dict]:
    """§9 search: case-insensitive substring hits over title, headings, and
    body. Shared by plain search, semantic degradation, and the §18.4 keyword
    component."""
    query = query.lower()
    hits: list[dict] = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if tag_filters and not all(tag_matches(t, effective_tags(rec)) for t in tag_filters):
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
        try:
            text, _ = load_text(root, rel)
        except OSError:  # §3 read failure: skip, best-effort
            continue
        if text is None:
            continue
        for i, line in enumerate(text.split("\n"), start=1):
            if i in heading_lines:
                continue
            if query in line.lower():
                hits.append({"field": "body", "line": i, "path": rel, "snippet": line.strip()})
    return hits


def emit_keyword_hits(hits: list[dict], as_json: bool) -> None:
    emit(
        hits,
        as_json,
        (
            f"{h['path']}: title: {h['snippet']}"
            if h["line"] is None
            else f"{h['path']}:{h['line']}: {h['snippet']}"
            for h in hits
        ),
    )


def cmd_search(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    if args.semantic:
        return semantic_search(root, index, args)
    emit_keyword_hits(keyword_hits(root, index, args.query, args.tag), args.json)
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

    def mtime(rel: str) -> float:
        try:
            return (root / rel).stat().st_mtime
        except OSError:  # §3 read failure (e.g. broken symlink): sort last
            return 0.0

    entries.sort(key=lambda kv: mtime(kv[0]), reverse=True)
    entries.sort(key=lambda kv: kv[1]["updated"] or "", reverse=True)
    entries = entries[: args.n]
    rows = [
        {"path": rel, "title": rec["title"], "updated": rec["updated"]}
        for rel, rec in entries
    ]
    emit(rows, args.json, (f"{r['updated'] or '----------'}  {r['path']}" for r in rows))
    return 0


def cmd_curate(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    cur = compute_curation(root, index, today())
    if args.check_urls:
        cur["deadUrls"] = check_urls(root, sorted(index["notes"]))
    lines: list[str] = []
    sections = [
        ("expired", "expired", lambda r: f"{r['path']}  (expired {r['expires']})"),
        ("missingExpires", "missing expires:", lambda r: r),
        ("beyondCap", "expires beyond the one-year cap", lambda r: f"{r['path']}  (updated {r['updated']}, expires {r['expires']})"),
        ("oversized", "oversized (split candidates)", lambda r: f"{r['path']}  ({r['sizeBytes']} bytes, {r['lines']} lines)"),
        ("stale", "stale (days old x inbound links)", lambda r: f"{r['path']}  (updated {r['updated']}, {r['daysOld']}d, {r['backlinks']} backlinks, score {r['score']})"),
        ("orphans", "orphans (no inbound links)", lambda r: r),
        ("unreferencedAssets", "unreferenced assets", lambda r: r),
        ("deadUrls", "dead source urls", lambda r: f"{r['url']}  ({r['error']}; first seen in {r['path']})"),
    ]
    flagged = 0
    for key_name, label, fmt in sections:
        rows = cur.get(key_name)
        if rows is None:
            continue
        lines.append(f"{label}: {len(rows)}")
        for row in rows:
            lines.append(f"  {fmt(row)}")
        flagged += len(rows)
    lines.append(f"total flagged: {flagged}")
    emit(cur, args.json, lines)
    return 0


def cmd_context(root: Path, args) -> int:
    ctx = context_report(root)
    lines = []
    for row in ctx["docs"]:
        if row["sizeBytes"] is None:
            lines.append(f"{row['path']}  missing  (budget {row['budget']})")
        else:
            pct = 100 * row["sizeBytes"] // row["budget"]
            over = "  OVER BUDGET" if row["sizeBytes"] > row["budget"] else ""
            lines.append(
                f"{row['path']}  {row['sizeBytes']} / {row['budget']} bytes ({pct}%){over}"
            )
    tpct = 100 * ctx["totalBytes"] // ctx["totalBudget"]
    over = "  OVER BUDGET" if ctx["totalBytes"] > ctx["totalBudget"] else ""
    lines.append(f"total  {ctx['totalBytes']} / {ctx['totalBudget']} bytes ({tpct}%){over}")
    emit(ctx, args.json, lines)
    return 0


def cmd_config(root: Path, args) -> int:
    """§15: effective vault config — defaults merged, findings included."""
    config, findings = load_config(root)
    cfg_errors, cfg_warnings = check_config(root, config, findings)
    payload = {
        "context": vault_context(config),
        "errors": cfg_errors,
        "extensionTrust": extension_trust(config),
        "path": CONFIG_RELPATH,
        "present": (root / CONFIG_RELPATH).exists(),
        "raw": config,
        "reservedKeys": sorted(CONFIG_RESERVED_KEYS),
        "tasksCarryOver": tasks_carry_over(config),
        "templateVersion": template_version(config),
        "warnings": cfg_warnings,
        "writeExceptions": list(write_exception_prefixes(config)),
    }
    lines = [
        f"config: {CONFIG_RELPATH} ({'present' if payload['present'] else 'absent — defaults'})",
        "write exceptions (agent-writable prefixes):",
        *(f"  {p}" for p in payload["writeExceptions"]),
        f"extension trust: {payload['extensionTrust']}",
        f"context: {payload['context']}",
        f"tasks carry-over: {'on' if payload['tasksCarryOver'] else 'off'}",
        f"template version: {payload['templateVersion'] or '(unset)'}",
    ]
    for f in cfg_errors:
        lines.append(f"ERROR {f['rule']}: {f['message']}")
    for f in cfg_warnings:
        lines.append(f"WARN {f['rule']}: {f['message']}")
    emit(payload, args.json, lines)
    return 0


def cmd_report(root: Path, args) -> int:
    """§16: the five-section vault-health report, most-actionable-first."""
    since_d = None
    if args.since is not None:
        since_d = iso_date(args.since)
        if since_d is None:
            print(
                f"error: --since must be a real YYYY-MM-DD date, got {args.since!r}",
                file=sys.stderr,
            )
            return 1
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    config, _findings = load_config(root)
    thresholds = report_thresholds(config)
    taxonomy = load_taxonomy(root)
    rep = compute_report(index, today(), thresholds, taxonomy, since_d)

    lines: list[str] = [
        "vault health report "
        f"(stale-active > {thresholds['staleDays']}d, "
        f"inbox triage > {thresholds['inboxDays']}d)"
    ]
    if rep["since"]:
        lines.append(
            f"since {rep['since']}: tag drift and unresolved links scoped to "
            "notes updated on/after this date"
        )
    lines.append(f"stale-active: {len(rep['staleActive'])}")
    for row in rep["staleActive"]:
        lines.append(f"  {row['path']}  (updated {row['updated']}, {row['daysOld']}d old)")
    lines.append(f"orphans (no links in or out): {len(rep['orphans'])}")
    for rel in rep["orphans"]:
        lines.append(f"  {rel}")
    inbox = rep["inboxAging"]
    total_inbox = sum(len(rows) for rows in inbox["buckets"].values())
    lines.append(
        f"inbox aging: {total_inbox} notes, {len(inbox['triageDebt'])} past "
        f"the {thresholds['inboxDays']}d triage threshold"
    )
    for label in REPORT_BUCKET_LABELS:
        rows = inbox["buckets"][label]
        if not rows:
            continue
        lines.append(f"  {label}: {len(rows)}")
        for row in rows:
            age = "?" if row["ageDays"] is None else f"{row['ageDays']}d"
            lines.append(f"    {row['path']}  ({age}, {row['source']})")
    drift = rep["tagDrift"]
    if not drift["taxonomyReadable"]:
        lines.append("tag drift: conventions taxonomy unreadable — not computed (see validate)")
    else:
        lines.append(
            "tag drift: "
            f"{len(drift['unknown'])} unknown, {len(drift['singleUse'])} single-use, "
            f"{len(drift['nearDuplicates'])} near-duplicate pairs"
        )
        for row in drift["unknown"]:
            lines.append(f"  {row['tag']}  ({row['reason']}, {row['count']} notes)")
        for tag in drift["singleUse"]:
            lines.append(f"  {tag}  (single-use)")
        for row in drift["nearDuplicates"]:
            lines.append(
                f"  {row['namespace']}/: {row['values'][0]} ~ {row['values'][1]}"
                "  (near-duplicate)"
            )
    lines.append(f"unresolved links: {rep['unresolvedLinks']['count']}")
    for row in rep["unresolvedLinks"]["links"]:
        lines.append(f"  {row['path']}:{row['line']}  -> [[{row['target']}]]")
    emit(rep, args.json, lines)
    return 0


def cmd_tasks(root: Path, args) -> int:
    """§17.3: query checkbox tasks from the in-memory index."""
    due_limit: date | None = None
    if args.due is not None:
        due_limit = today() if args.due == "today" else iso_date(args.due)
        if due_limit is None:
            print(
                f"error: --due must be 'today' or a real YYYY-MM-DD date, "
                f"got {args.due!r}",
                file=sys.stderr,
            )
            return 1
    today_iso = today().isoformat()
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    rows: list[dict] = []
    # Normalize like every other path input (§2): NFC, forward slashes,
    # no leading ./ — a macOS NFD prefix or backslash must still match.
    project = (
        nfc(args.project.strip()).replace("\\", "/").removeprefix("./")
        if args.project
        else None
    )
    for rel in sorted(index["notes"]):
        if project and not rel.startswith(project):
            continue
        for t in index["notes"][rel]["tasks"]:
            if args.open and t["status"] != "open":
                continue
            if due_limit is not None and (
                t["due"] is None or t["due"] > due_limit.isoformat()
            ):
                continue
            if args.overdue and not (
                t["status"] == "open" and t["due"] is not None and t["due"] < today_iso
            ):
                continue
            rows.append({**t, "path": rel})
    rows.sort(key=lambda r: (r["due"] is None, r["due"] or "", r["path"], r["line"]))
    lines = []
    for r in rows:
        box = "[ ]" if r["status"] == "open" else "[x]"
        extras = ", ".join(
            part
            for part in (
                f"due {r['due']}" if r["due"] else None,
                r["priority"],
                "malformed: " + ", ".join(r["malformed"]) if r["malformed"] else None,
            )
            if part
        )
        lines.append(
            f"{r['path']}:{r['line']}  {box} {r['text']}"
            + (f"  ({extras})" if extras else "")
        )
    emit(rows, args.json, lines)
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
    p.add_argument(
        "--semantic",
        action="store_true",
        help="rank notes by embedding similarity (spec §18.4), degrading to keyword search without vectors",
    )
    p.add_argument(
        "--top",
        type=int,
        default=SEMANTIC_TOP_DEFAULT,
        help="semantic mode: max ranked notes returned",
    )
    p.add_argument(
        "--query-vector",
        action="store_true",
        help="semantic mode: read the query embedding as a JSON array from stdin",
    )
    p = add("links", help="outgoing links, backlinks, unresolved targets")
    p.add_argument("note")
    add("tags", help="tag usage counts by namespace")
    p = add("show", help="full index record for one note")
    p.add_argument("note")
    p = add("recent", help="notes by updated date, newest first")
    p.add_argument("n", nargs="?", type=int, default=10)
    p = add("validate", help="check vault conventions; exit 0 clean / 1 errors / 2 warnings")
    p.add_argument("--check-index", action="store_true", help="also verify the committed index is fresh")
    p = add("curate", help="re-review signals: expired, missing/over-cap expires, oversized, stale, orphans, unreferenced assets")
    p.add_argument("--check-urls", action="store_true", help="also probe source URLs over the network (never pre-commit)")
    add("context", help="bootstrap docs' sizes against their context budgets")
    add("config", help="effective vault config (00_Meta/config.yaml merged over defaults)")
    p = add("tasks", help="checkbox tasks across the vault (spec §17)")
    p.add_argument("--open", action="store_true", help="open (unchecked) tasks only")
    p.add_argument(
        "--due",
        default=None,
        metavar="YYYY-MM-DD|today",
        help="tasks with a due date on or before this date",
    )
    p.add_argument(
        "--overdue", action="store_true", help="open tasks whose due date is past"
    )
    p.add_argument(
        "--project", default=None, metavar="PREFIX", help="note-path prefix filter"
    )
    p = add("report", help="vault health: stale-active, orphans, Inbox aging, tag drift, unresolved links")
    p.add_argument(
        "--since",
        default=None,
        metavar="YYYY-MM-DD",
        help="scope tag drift and unresolved links to notes updated on/after this date",
    )
    p = add("embed", help="maintain the semantic-search embeddings sidecar (spec §18.3)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--stdin-json",
        action="store_true",
        help="ingest precomputed vectors from stdin JSON ({model, vectors})",
    )
    mode.add_argument(
        "--local",
        action="store_true",
        help="embed changed notes with the optional local model (sentence-transformers)",
    )
    mode.add_argument("--status", action="store_true", help="report sidecar coverage; no writes")
    p.add_argument("--model", default=None, help="--local: embedding model name override")

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
        "curate": cmd_curate,
        "context": cmd_context,
        "config": cmd_config,
        "report": cmd_report,
        "tasks": cmd_tasks,
        "embed": cmd_embed,
    }
    return handlers[args.command](root, args)


if __name__ == "__main__":
    sys.exit(main())
