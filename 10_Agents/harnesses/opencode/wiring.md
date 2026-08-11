---
title: "opencode Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# opencode Wiring

Facts verified 2026-08-11 against [opencode.ai/docs](https://opencode.ai/docs) (see [[06_Resources/harness-opencode|research]]); re-verify before relying on paths.

## Entrypoint loading

opencode reads **`AGENTS.md` natively** (when both exist, `AGENTS.md` wins over `CLAUDE.md`). It does **not** follow `@file` references or wikilinks, so the adapter makes the bootstrap sequence deterministic: the `instructions[]` array in `opencode.json` loads the must-read files as plain paths alongside `AGENTS.md` (see `opencode-example.json`). User scope: `onboard-harness` writes the import block into `~/.config/opencode/AGENTS.md` (global instructions file).

## Skills

opencode scans `.opencode/skills/`, `.claude/skills/`, and the shared `.agents/skills/` — the `~/.agents/skills/<name>` symlinks from `onboard-harness` cover it with no extra work.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone. opencode's native hooks are JS plugin code, not config — the git hook remains the enforcement layer; a plugin is optional adopter polish.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

Shell access falls under the `permission` map in `opencode.json`; the reference config leaves bash on defaults — tighten per taste.

## Harness-specific notes

- **Config precedence** deep-merges global `~/.config/opencode/opencode.json` under the project-root `opencode.json`, so the reference file can live at either scope.
- **MCP:** the `mcp` key in `opencode.json`. The vault ships none; M7 external-source servers go here.
- **Ignore:** only `watcher.ignore` exists (file-watcher scope, not access control) — no reliable content exclusion; feeds the open privacy-policy decision (PRD §21).
- Commands exist (`.opencode/commands/`) but skills are the portable unit — ship none.

## Reference config

`opencode-example.json` — copy to the vault root as `opencode.json` (or merge into the global config, converting paths to absolute).
