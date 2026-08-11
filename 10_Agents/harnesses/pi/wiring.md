---
title: "Pi Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# Pi Wiring

Facts verified 2026-08-11 against the [pi-mono docs](https://github.com/badlogic/pi-mono) (see [[06_Resources/harness-pi|research]]); re-verify before relying on paths.

## Entrypoint loading

Pi reads **`AGENTS.md` natively** (with `CLAUDE.md` fallback), walking parent directories to the cwd — the vault bootstrap works unmodified. User scope: `onboard-harness` creates `~/.agents/second-brain/AGENTS.md`, then writes a marker-delimited plain-text instruction into `~/.pi/agent/AGENTS.md` telling Pi to read that shared registration when owner-specific context materially helps. The adapter does not embed the adopter's vault path or assume the shared file is automatically discovered; the shared registration owns the runtime-specific path and routes onward to the vault's `AGENTS.md`.

## Skills

Pi supports Agent Skills and scans `.pi/skills/`, the shared `.agents/skills/`, and user-scope equivalents — the `~/.agents/skills/<name>` symlinks cover it. **Trust gate:** project-scope `.pi/` and `.agents/skills/` resources load only after the adopter runs `/trust` on the vault once (or sets `defaultProjectTrust` globally); headless runs silently ignore them otherwise — the single most common Pi setup miss.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone. Pi's native event surface is TypeScript extensions (`.pi/extensions/`), not config hooks — the git hook is the enforcement layer; an extension hooking `tool_call` for edit-time validation is optional adopter polish and the main Pi-only artifact worth building later.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

Pi shells out normally; no approval config needed beyond project trust.

**Semantic search** ([[10_Agents/tools/brain/spec|spec]] §18): `python3 10_Agents/tools/brain/brain.py search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `python3 10_Agents/tools/brain/brain.py embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **No MCP support** — Pi extends via TypeScript extensions instead. This is exactly the preference ladder's first rung (PRD §8.4): external-source access for Pi is a custom extension or CLI, never an MCP server.
- **No ignore mechanism** of any kind — feeds the open privacy-policy decision (PRD §21).
- Prompt templates (`.pi/prompts/*.md`) exist, but skills are the portable unit — ship none.

## Reference config

`settings-example.json` — merge into `~/.pi/agent/settings.json` (**user scope**: `defaultProjectTrust` is a global-only key and has no effect in a project `.pi/settings.json`). Prefer running `/trust` on the vault instead if you don't want every project trusted by default.
