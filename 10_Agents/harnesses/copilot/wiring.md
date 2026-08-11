---
title: "Copilot Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
---

# Copilot Wiring

Facts verified 2026-08-11 against [docs.github.com/copilot](https://docs.github.com/copilot) (see [[02_Inbox/2026-08-11-harness-primitives-research#Copilot|research]]); re-verify before relying on paths.

## Entrypoint loading

Copilot's **agent surfaces** (VS Code agent mode, Copilot CLI, github.com coding agent) read `AGENTS.md` natively — no setup. Two caveats:

- github.com treats a root `CLAUDE.md` as an *alternative* instruction file; the vault's is a one-line import Copilot cannot expand. `AGENTS.md` wins when both exist — keep it that way.
- **IDE-embedded surfaces** (JetBrains, Visual Studio, Xcode, Eclipse) ignore `AGENTS.md`; they read `.github/copilot-instructions.md`. Copy `copilot-instructions-example.txt` there if you use those IDEs — it's a thin pointer to the bootstrap sequence, not a duplicate.

## Skills

Copilot supports Agent Skills and scans `.github/skills/`, `.claude/skills/`, and the shared `.agents/skills/` — the `~/.agents/skills/<name>` symlinks cover it. Prompt files (`.github/prompts/`) are the legacy unit; ship none.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone. Copilot repo hooks (`.github/hooks/`, Preview) are optional polish; the git hook is the enforcement layer.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

The github.com coding agent runs in an Actions sandbox — the CI validate workflow already covers enforcement there.

## Harness-specific notes

- **MCP is per-surface:** `.vscode/mcp.json` for VS Code; the cloud coding agent's MCP config lives in repo settings (**cannot be committed as a file**) — document, don't automate. The vault ships no servers.
- Glob-scoped instruction files (`.github/instructions/*.instructions.md`) can mirror per-directory rules; use sparingly — `AGENTS.md` is the portable layer.
- Content-exclusion is org-managed (and ignored by the CLI/agent) — no repo-level privacy mechanism; feeds the open policy decision (PRD §21).

## Reference config

`copilot-instructions-example.txt` — copy to `.github/copilot-instructions.md` for IDE-embedded surfaces.
