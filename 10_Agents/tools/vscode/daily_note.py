#!/usr/bin/env python3
"""Create (if needed) and open today's daily note.

VS Code counterpart to Obsidian's daily-notes core plugin, wired to the
"Daily Note: Open Today" task in .vscode/tasks.json. Instantiates
09_Templates/template-daily-log.md into 03_Journal/periodic/daily/ with every
placeholder resolved (frontmatter contract, PRD §10.1): {{date}} becomes
today, the related-links tokens become yesterday's note and this ISO week's
review. Existing notes are never overwritten. Prints the note path; opens it
in the current VS Code window when the `code` CLI is on PATH.

Stdlib-only, Python 3.10+.
"""

import datetime
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def render_note(root: Path, today: datetime.date) -> str:
    """Instantiate the daily template for `today` with placeholders resolved."""
    template = root / "09_Templates" / "template-daily-log.md"
    daily_dir = root / "03_Journal" / "periodic" / "daily"
    iso_year, iso_week, _ = today.isocalendar()
    yesterday = today - datetime.timedelta(days=1)
    weekly = f"03_Journal/periodic/weekly/{iso_year}-W{iso_week:02d}-review"
    return (
        template.read_text(encoding="utf-8")
        .replace("{{date}}", today.isoformat())
        # Unresolved wikilinks are brain-validate errors, so link related
        # notes only once they exist; plain text otherwise.
        .replace(
            "[[{{RELATED_WEEKLY_REVIEW}}]]",
            f"[[{weekly}]]" if (root / f"{weekly}.md").exists() else "not yet created",
        )
        .replace(
            "[[{{PREVIOUS_DAILY_NOTE}}]]",
            f"[[{yesterday.isoformat()}]]"
            if (daily_dir / f"{yesterday.isoformat()}.md").exists()
            else "none",
        )
    )


def ensure_note(root: Path, today: datetime.date) -> tuple[Path, bool]:
    """Create today's note if absent; return (path, created). Never overwrites."""
    daily_dir = root / "03_Journal" / "periodic" / "daily"
    target = daily_dir / f"{today.isoformat()}.md"
    if target.exists():
        return target, False
    content = render_note(root, today)
    daily_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target, True


def main() -> int:
    target, created = ensure_note(ROOT, datetime.date.today())
    print(f"{'created' if created else 'exists '} {target.relative_to(ROOT)}")

    code_cli = shutil.which("code")
    if code_cli:
        subprocess.run([code_cli, "-r", str(target)], check=False)
    else:
        print("(`code` CLI not on PATH — open the note manually)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
