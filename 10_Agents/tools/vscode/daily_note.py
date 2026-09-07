#!/usr/bin/env python3
"""Create (if needed) and open today's daily note.

VS Code counterpart to Obsidian's daily-notes core plugin, wired to the
"Daily Note: Open Today" task in .vscode/tasks.json. Instantiates
09_Templates/template-daily-log.md into 03_Journal/periodic/daily/ with every
placeholder resolved (frontmatter contract, PRD §10.1): {{date}} becomes
the vault-local date, the related-links tokens become yesterday's note and this
ISO week's review, and unfilled goal scaffold lines are omitted. Existing notes
are never overwritten. Prints the note path; opens it
in the current VS Code window when the `code` CLI is on PATH.

Task carry-over (brain spec §17.5, issue #28): when the vault config's
`tasks: carry_over:` toggle is on (the default), yesterday's unchecked
checkbox tasks are copied verbatim into the new note's `### Backlog`
section. Checkboxes inside fenced code blocks or inline code spans never
carry (brain's §5.2 exclusion zones apply — detection is shared with
`brain tasks`). Private or unknown source classification also means no carry-over;
carried tasks retain yesterday as a privacy-sources dependency.

Stdlib-only, Python 3.10+.
"""

import datetime
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "10_Agents" / "tools" / "brain"))
import brain  # noqa: E402

DAILY_DIR = "03_Journal/periodic/daily"
BACKLOG_HEADING = "### Backlog"


def render_note(root: Path, today: datetime.date) -> str:
    """Instantiate the daily template for `today` with placeholders resolved."""
    iso_year, iso_week, _ = today.isocalendar()
    yesterday = today - datetime.timedelta(days=1)
    weekly = f"03_Journal/periodic/weekly/{iso_year}-W{iso_week:02d}-review.md"
    weekly_link = f"../weekly/{iso_year}-W{iso_week:02d}-review.md"
    previous_link = f"{yesterday.isoformat()}.md"
    content = brain._instantiate_periodic(
        root, "09_Templates/template-daily-log.md", f"{DAILY_DIR}/{today.isoformat()}.md",
        {
            "date": today.isoformat(),
            "CONTEXT": None,
            "GOAL": None,
            "RELATED_WEEKLY_REVIEW": weekly_link,
            "PREVIOUS_DAILY_NOTE": previous_link,
        },
        today,
    )
    return (
        # Unresolved links are brain-validate errors, so link related
        # notes only once they exist; preserve their established labels.
        content.replace(
            f"[Current weekly review]({weekly_link})",
            f"[{iso_year}-W{iso_week:02d} review]({weekly_link})"
            if (root / weekly).exists()
            else "not yet created",
        )
        .replace(
            f"[Previous daily note]({previous_link})",
            f"[{yesterday.isoformat()}]({previous_link})"
            if (root / DAILY_DIR / previous_link).exists()
            else "none",
        )
    )


def carry_over_tasks(root: Path, today: datetime.date) -> list[str]:
    """Yesterday's unchecked task lines, verbatim (indentation preserved so
    nested subtasks keep their structure). Empty when the config toggle is
    off, yesterday's note is absent/unreadable, private/unknown, or task-free."""
    config, _findings = brain.load_config(root)
    if not brain.tasks_carry_over(config):
        return []
    yesterday = today - datetime.timedelta(days=1)
    rel = f"{DAILY_DIR}/{yesterday.isoformat()}.md"
    if not (root / rel).exists():
        return []
    try:
        rows = brain.read_note_context(root, [rel], public_only=True)
    except (OSError, brain.NoteContextError):
        return []
    # Parse exactly the bytes admitted by the source classification snapshot.
    lines = rows[0]["content"].split("\n")
    _fm, _errs, body_start, _has = brain.parse_frontmatter(lines)
    carried: list[str] = []
    for _lineno, raw, masked in brain.body_lines_masked(lines, body_start):
        m = brain.TASK_RE.match(masked)
        if m and m.group(1) == " " and raw[m.end() :].strip():
            carried.append(raw.rstrip())
    return carried


def insert_backlog(content: str, tasks: list[str]) -> str:
    """Insert carried task lines at the end of the `### Backlog` section
    (before its trailing blank lines); append the section if the template
    yields none. No tasks -> content unchanged."""
    if not tasks:
        return content
    lines = content.split("\n")
    try:
        i = lines.index(BACKLOG_HEADING)
    except ValueError:
        return (
            content.rstrip("\n")
            + "\n\n"
            + "\n".join([BACKLOG_HEADING, ""] + tasks)
            + "\n"
        )
    j = i + 1
    while j < len(lines) and not lines[j].startswith("#"):
        j += 1
    while j > i + 1 and lines[j - 1].strip() == "":
        j -= 1
    return "\n".join(lines[:j] + tasks + lines[j:])


def ensure_note(root: Path, today: datetime.date) -> tuple[Path, bool]:
    """Create today's note if absent; return (path, created). Never overwrites."""
    daily_dir = root / "03_Journal" / "periodic" / "daily"
    target = daily_dir / f"{today.isoformat()}.md"
    if target.exists():
        return target, False
    content = render_note(root, today)
    tasks = carry_over_tasks(root, today)
    if tasks:
        content = insert_backlog(content, tasks)
        yesterday = today - datetime.timedelta(days=1)
        content = brain.record_privacy_sources(content, [f"{DAILY_DIR}/{yesterday.isoformat()}.md"])
    daily_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target, True


def main() -> int:
    config, _findings = brain.load_config(ROOT)
    target, created = ensure_note(ROOT, brain.vault_today(config))
    print(f"{'created' if created else 'exists '} {target.relative_to(ROOT)}")

    code_cli = shutil.which("code")
    if code_cli:
        subprocess.run([code_cli, "-r", str(target)], check=False)
    else:
        print("(`code` CLI not on PATH — open the note manually)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
