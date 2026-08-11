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

Cursor reads **`AGENTS.md` natively** (IDE: root and nested levels; CLI also reads `CLAUDE.md`) — the vault bootstrap loads unmodified. User scope: `onboard-harness` creates `~/.agents/second-brain/AGENTS.md` and registers a marker-delimited reference to it through Cursor's documented user-rules surface. If the current Cursor surface documents a user-level instruction file or native include mechanism at install time, prefer that; otherwise use a plain user rule telling Cursor to read the shared registration when owner-specific context materially helps. Do not assume `~/.agents/second-brain/AGENTS.md` is automatically discovered, and never embed the adopter's vault path in the Cursor-specific adapter.

## Skills

Cursor supports Agent Skills and scans `.cursor/skills/`, the shared `.agents/skills/`, and Claude-compat paths — the `~/.agents/skills/<name>` symlinks cover it. Commands are deprecated in favor of skills; ship none.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone. Native polish: `.cursor/hooks.json` can add `afterFileEdit` (auto-bump `updated:`) and `beforeShellExecution` guards — optional; the git hook is the enforcement layer.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

## Harness-specific notes

- **`.vscode/` applies as-is:** Cursor is a VS Code fork and honors the vault's shipped workspace config ([[00_Meta/prd]] §6.5) unchanged — settings, the first-party extension recommendations, the brain/daily-note/homepage tasks, and the template-generated snippets all work in Cursor with zero extra wiring.
- **The only harness with a real repo ignore file:** `.cursorignore` gives genuine access exclusion — the one place the vault's privacy marking (`restricted/private`, issue #17 closing PRD §21's open question) can be enforced natively today — see the Restricted content section below. `overlay/cursorignore-template.txt` shows the shape.
- **Glob-scoped rules:** `.cursor/rules/*.mdc` can scope guidance per PARA directory (`overlay/rules/inbox-conventions.mdc`); use sparingly — `AGENTS.md` remains the portable rule layer.
- **MCP:** `.cursor/mcp.json`; the vault ships none (M7 registers external sources here).
- **Cloud Automations** can cron scheduled runs (e.g. weekly-review drafts into `02_Inbox/`) — an M7 concern.

## Restricted content → `.cursorignore`

The vault's privacy marking is the `restricted/private` tag ([[00_Meta/conventions#Tag Namespaces]], issue #17) — advisory everywhere except mechanically-enforced surfaces, and Cursor is the one harness where real enforcement exists. Generate `.cursorignore` entries from the restricted-tagged paths:

```
python3 10_Agents/tools/brain/brain.py list --tag restricted/private
```

Rewrite the managed block between the `# BEGIN second-brain restricted/private (generated)` and `# END` markers in the vault-root `.cursorignore` wholesale with one line per printed path (create the file from `overlay/cursorignore-template.txt` if absent; owner lines outside the markers are never touched). Rewriting the whole block is what makes the sync idempotent and lets a note that *loses* the tag drop back out. This is a documented manual step — run it during `onboard-harness` and re-run it whenever notes gain or lose the tag; nothing regenerates the file for you, so a stale `.cursorignore` silently under-excludes. Only path-listed notes are excluded: Cursor knows nothing about tags, so the tag alone protects nothing here until its path lands in the file.

## Reference configs

The Cursor-native primitives now ship as an installable **overlay** — `overlay/manifest.json` describes what installs where and how each artifact reverses (see the Overlays section of [[10_Agents/harnesses/README]]; [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] performs the install): `overlay/rules/inbox-conventions.mdc` (copy into `.cursor/rules/`), `overlay/cursorignore-template.txt` (seed for `.cursorignore` — the `restricted/private` generation step above is the shipping privacy policy since 2026-08-11).
