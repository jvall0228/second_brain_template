---
title: "VS Code Tools"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - topic/software
  - workflow/draft
updated: 2026-08-11
expires: 2027-08-11
---

# VS Code Tools

Scripts backing the VS Code alternative-editor surface ([PRD](../../../00_Meta/PRD.md) §6.5). Stdlib-only Python 3.10+, per the tools rules in [README](../README.md). Both are invoked from `.vscode/tasks.json` and the pre-commit hook — no editor extension involved (strict first-party trust policy).

The hand-maintained task surface also exposes **Brain: Actions You May Take**, a read-only `brain aymt` preview. Writing the generated [AYMT](../../../00_Meta/AYMT.md) remains an explicit CLI/skill action and is deliberately not a folder-open task or hook.

## Contents

- `gen_snippets.py` — generates `.vscode/second-brain.code-snippets` from `09_Templates/`, mapping `{{date}}` to VS Code's auto-filling date variables and other `{{...}}` tokens to tabstops. **The generated file is never edited by hand**; the pre-commit hook regenerates and re-stages it, so the snippet surface cannot drift from the canonical templates (editor-surface parity, §6.5). `--check` exits 1 if the committed file is stale.
- `daily_note.py` — creates today's note in `03_Journal/periodic/daily/` from `template-daily-log.md` (all placeholders resolved to source-relative Markdown destinations; related notes linked only if they exist, since unresolved links are validate errors) and opens it via the `code` CLI when available. The VS Code stand-in for Obsidian's daily-notes plugin; the [daily-log](../../skills/daily-log/SKILL.md) skill remains the agent-side path.

## Sync contract

Template changes flow to the snippet surface automatically at the next commit (hook) — agents and humans never update `second-brain.code-snippets` directly. Everything else under `.vscode/` (settings, extensions, tasks) is hand-maintained under the parity duty in [OPERATING-RULES](../../docs/OPERATING-RULES.md).
