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
TEMPLATE = ROOT / "09_Templates" / "template-daily-log.md"
DAILY_DIR = ROOT / "03_Journal" / "periodic" / "daily"


def main() -> int:
    today = datetime.date.today()
    target = DAILY_DIR / f"{today.isoformat()}.md"

    if not target.exists():
        iso_year, iso_week, _ = today.isocalendar()
        yesterday = today - datetime.timedelta(days=1)
        weekly = f"03_Journal/periodic/weekly/{iso_year}-W{iso_week:02d}-review"
        content = (
            TEMPLATE.read_text(encoding="utf-8")
            .replace("{{date}}", today.isoformat())
            # Unresolved wikilinks are brain-validate errors, so link related
            # notes only once they exist; plain text otherwise.
            .replace(
                "[[{{RELATED_WEEKLY_REVIEW}}]]",
                f"[[{weekly}]]" if (ROOT / f"{weekly}.md").exists() else "not yet created",
            )
            .replace(
                "[[{{PREVIOUS_DAILY_NOTE}}]]",
                f"[[{yesterday.isoformat()}]]"
                if (DAILY_DIR / f"{yesterday.isoformat()}.md").exists()
                else "none",
            )
        )
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"created {target.relative_to(ROOT)}")
    else:
        print(f"exists  {target.relative_to(ROOT)}")

    code_cli = shutil.which("code")
    if code_cli:
        subprocess.run([code_cli, "-r", str(target)], check=False)
    else:
        print("(`code` CLI not on PATH — open the note manually)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
