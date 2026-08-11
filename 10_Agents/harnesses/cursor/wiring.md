---
title: "Cursor Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# Cursor Wiring

Facts verified 2026-08-11 against [cursor.com/docs](https://cursor.com/docs) (see [[06_Resources/harness-cursor|research]]); re-verify before relying on paths.

## Entrypoint loading

Cursor reads **`AGENTS.md` natively** (IDE: root and nested levels; CLI also reads `CLAUDE.md`) — the vault bootstrap loads unmodified. User scope: `onboard-harness` writes the import block into Cursor's user rules (or a user-level `AGENTS.md` where supported; per-surface — check current docs at install time).

## Skills

Cursor supports Agent Skills and scans `.cursor/skills/`, the shared `.agents/skills/`, and Claude-compat paths — the `~/.agents/skills/<name>` symlinks cover it. Commands are deprecated in favor of skills; ship none.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone. Native polish: `.cursor/hooks.json` can add `afterFileEdit` (auto-bump `updated:`) and `beforeShellExecution` guards — optional; the git hook is the enforcement layer.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

## Harness-specific notes

- **The only harness with a real repo ignore file:** `.cursorignore` gives genuine access exclusion — the one place the vault's pending privacy policy (PRD §21) can be enforced natively today. `cursorignore-example.txt` shows the shape.
- **Glob-scoped rules:** `.cursor/rules/*.mdc` can scope guidance per PARA directory (`rule-example.mdc`); use sparingly — `AGENTS.md` remains the portable rule layer.
- **MCP:** `.cursor/mcp.json`; the vault ships none (M7 registers external sources here).
- **Cloud Automations** can cron scheduled runs (e.g. weekly-review drafts into `02_Inbox/`) — an M7 concern.

## Reference configs

`rule-example.mdc` (copy into `.cursor/rules/`), `cursorignore-example.txt` (copy to `.cursorignore` once a privacy policy is decided).
