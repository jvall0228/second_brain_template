#!/usr/bin/env python3
"""Generate .vscode/second-brain.code-snippets from 09_Templates/.

Keeps the VS Code snippet surface automatically in sync with the canonical
templates (PRD §6.5 editor-surface parity): run by the pre-commit hook after
any template change; never edit the generated file by hand.

Stdlib-only, deterministic output (sorted keys, stable ordering) so the
committed file diffs cleanly. Usage:

    python3 10_Agents/tools/vscode/gen_snippets.py            # write
    python3 10_Agents/tools/vscode/gen_snippets.py --check    # exit 1 if stale

Placeholder mapping (template token -> VS Code snippet syntax):
    {{date}}   -> ${CURRENT_YEAR}-${CURRENT_MONTH}-${CURRENT_DATE}  (auto-fills)
    {{title}}  -> ${1:title}                                        (tabstop)
    {{OTHER}}  -> ${n:OTHER}   (tabstops numbered by first appearance)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = ROOT / "09_Templates"
OUT_PATH = ROOT / ".vscode" / "second-brain.code-snippets"

DATE_VAR = "${CURRENT_YEAR}-${CURRENT_MONTH}-${CURRENT_DATE}"
TOKEN_RE = re.compile(r"\{\{([^}]+)\}\}")

HEADER = (
    "// GENERATED FILE — do not edit. Built from 09_Templates/ by\n"
    "// 10_Agents/tools/vscode/gen_snippets.py (run by the pre-commit hook).\n"
)


def escape_snippet_text(text: str) -> str:
    """Escape characters VS Code snippet grammar treats specially."""
    return text.replace("\\", "\\\\").replace("$", "\\$")


def template_to_body(text: str) -> list[str]:
    tabstops: dict[str, int] = {}

    def replace(match: re.Match) -> str:
        token = match.group(1)
        if token == "date":
            return DATE_VAR
        if token not in tabstops:
            tabstops[token] = len(tabstops) + 1
        return "${%d:%s}" % (tabstops[token], token)

    escaped = escape_snippet_text(text)
    # Tokens survive escaping untouched ({{...}} contains no \ or $).
    return TOKEN_RE.sub(replace, escaped).rstrip("\n").split("\n")


def build_snippets() -> dict:
    snippets = {
        "Second Brain: frontmatter": {
            "prefix": "sb-frontmatter",
            "scope": "markdown",
            "description": "Required note frontmatter (00_Meta/conventions)",
            "body": [
                "---",
                "title: \"${1:Title}\"",
                "tags:",
                "  - ${2:type/note}",
                "  - workflow/draft",
                "updated: " + DATE_VAR,
                "---",
                "",
                "# ${1:Title}",
                "$0",
            ],
        }
    }
    for path in sorted(TEMPLATES_DIR.glob("template-*.md")):
        short = path.stem.removeprefix("template-")
        snippets[f"Second Brain: {short} template"] = {
            "prefix": f"sb-{short}",
            "scope": "markdown",
            "description": f"Instantiate 09_Templates/{path.name}",
            "body": template_to_body(path.read_text(encoding="utf-8")),
        }
    return snippets


def render() -> str:
    body = json.dumps(build_snippets(), indent=2, ensure_ascii=False, sort_keys=True)
    return HEADER + body + "\n"


def main() -> int:
    content = render()
    if "--check" in sys.argv[1:]:
        current = OUT_PATH.read_text(encoding="utf-8") if OUT_PATH.exists() else ""
        if current != content:
            print(f"stale: {OUT_PATH.relative_to(ROOT)} — rerun gen_snippets.py", file=sys.stderr)
            return 1
        return 0
    OUT_PATH.write_text(content, encoding="utf-8")
    print(OUT_PATH.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
