---
title: "Cursor Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-07
expires: 2026-11-11
---

# Cursor Wiring

Facts verified 2026-08-11 against [cursor.com/docs](https://cursor.com/docs) (see [research](../../../06_Resources/harness-cursor.md)); re-verify before relying on paths.

[onboard-harness](../../skills/setup/onboard-harness/SKILL.md) currently supports project verification and read-only global preview. User-global installation, reconciliation, and uninstall are deferred; the user-global designs below are not executable setup instructions.

## Entrypoint loading

Cursor reads **`AGENTS.md` natively** (IDE: root and nested levels; CLI also reads `CLAUDE.md`) — the vault bootstrap loads unmodified. Deferred user-scope design: a future `onboard-harness` backend would create `~/.agents/second-brain/AGENTS.md` and register a marker-delimited reference to it through Cursor's documented user-rules surface. If the current Cursor surface documents a user-level instruction file or native include mechanism at install time, prefer that; otherwise use a plain user rule telling Cursor to read the shared registration when owner-specific context materially helps. Do not assume `~/.agents/second-brain/AGENTS.md` is automatically discovered, and never embed the adopter's vault path in the Cursor-specific adapter.

## Skills

Cursor supports Agent Skills and scans `.cursor/skills/`, `.agents/skills/`, and Claude-compat paths. A clean clone includes generated text adapters in `.agents/skills/` and `.claude/skills/`, each pointing to its canonical `SKILL.md` (`10_Agents/skills/<name>/SKILL.md` for a flat skill, `10_Agents/skills/<group>/<name>/SKILL.md` for a grouped one such as the setup skills); project use needs no link or user-scope write. User-global links/copies remain deferred; current onboarding only previews proposed targets. Commands are deprecated in favor of skills; ship none.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone. Native polish: `.cursor/hooks.json` can add `afterFileEdit` (auto-bump `updated:`) and `beforeShellExecution` guards — optional; the git hook is the enforcement layer.

## Invoking brain

```
brain <command> --json
```

**Semantic search** ([spec](../../tools/brain/SPEC.md) §18): `brain search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `brain embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **`.vscode/` applies as-is:** Cursor is a VS Code fork and honors the vault's shipped workspace config ([PRD](../../../00_Meta/PRD.md) §6.5) unchanged — settings, the first-party extension recommendations, the brain/daily-note/homepage tasks, and the template-generated snippets all work in Cursor with zero extra wiring.
- **The only harness with a real repo ignore file:** `.cursorignore` gives genuine path-based read exclusion — no other supported harness has an equivalent. That makes it available as an **owner-selected opt-in** read restriction, not the enforcement layer for the vault's privacy marking: `restricted/private` is publication classification, not agent access control ([CONVENTIONS](../../../00_Meta/CONVENTIONS.md#restrictedprivate)). See the Restricted content section below; `overlay/cursorignore-template.txt` shows the shape.
- **Glob-scoped rules:** `.cursor/rules/*.mdc` can scope guidance per PARA directory (`overlay/rules/inbox-conventions.mdc`); use sparingly — `AGENTS.md` remains the portable rule layer.
- **MCP:** `.cursor/mcp.json`; the vault ships none (M7 registers external sources here).
- **Cloud Automations** can cron scheduled runs (e.g. weekly-review drafts into `02_Inbox/`) — an M7 concern.

## Restricted content → `.cursorignore` (opt-in owner-selected read restriction)

The vault's privacy marking is the `restricted/private` tag — **publication classification, not agent access control** ([CONVENTIONS](../../../00_Meta/CONVENTIONS.md#restrictedprivate) owns the contract). Agents read and use private content locally by default. If — and only if — the owner additionally wants this harness blocked from reading restricted notes, `.cursorignore` is the recipe: the artifact is marked `owner_opt_in` in `overlay/manifest.json`. Automated installation is deferred; current onboarding only verifies or previews. The manual recipe below requires the owner's explicit selection.

When the owner chooses it, generate `.cursorignore` entries from the restricted-tagged paths:

```
brain list --tag restricted/private
```

Rewrite the managed block between the `# BEGIN second-brain restricted/private (generated)` and `# END` markers in the vault-root `.cursorignore` wholesale with one line per printed path (create the file from `overlay/cursorignore-template.txt` if absent; owner lines outside the markers are never touched). Rewriting the whole block is what makes the sync idempotent and lets a note that *loses* the tag drop back out.

Know what this does and does not give you — it is **path-based, Cursor-specific, and incomplete**:

- Only path-listed notes are excluded: Cursor knows nothing about tags, so the tag alone protects nothing here until its path lands in the file.
- The sync is a documented manual step — re-run it whenever notes gain or lose the tag; nothing regenerates the file for you, so a stale `.cursorignore` silently under-excludes.
- No other supported harness has an equivalent mechanism, so this restriction does not travel with the vault.

## Reference configs

The Cursor-native primitives now ship as an installable **overlay** — `overlay/manifest.json` describes what installs where and how each artifact reverses (see the Overlays section of [README](../README.md); installation through [onboard-harness](../../skills/setup/onboard-harness/SKILL.md) is deferred): `overlay/rules/inbox-conventions.mdc` (future default copy into `.cursor/rules/`) and `overlay/cursorignore-template.txt` (seed for `.cursorignore` — owner-opt-in only; the generation step above runs solely when the owner selects harness-level read restriction).
