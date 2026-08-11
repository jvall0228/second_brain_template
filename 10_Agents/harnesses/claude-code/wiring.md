---
title: "Claude Code Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# Claude Code Wiring

Facts verified 2026-08-11 against [code.claude.com/docs](https://code.claude.com/docs) (see [[06_Resources/harness-claude-code|research]]); re-verify before relying on paths.

## Entrypoint loading

Claude Code does **not** read `AGENTS.md` natively — it loads `CLAUDE.md`, and the vault's root `CLAUDE.md` (`@AGENTS.md`) is exactly the documented memory-import pattern, so **project scope needs no setup**. User scope: `onboard-harness` first creates the stable shared registration at `~/.agents/second-brain/AGENTS.md`, then appends a marker-delimited `@~/.agents/second-brain/AGENTS.md` import to `~/.claude/CLAUDE.md`. Claude therefore loads only the thin registration globally; that registration points at the adopter's actual vault and tells Claude to read the vault's `AGENTS.md` when owner-specific context materially helps with the task. The adopter-specific vault path never appears in this template or in the Claude adapter block.

## Skills

Claude Code scans `.claude/skills/` (project) and `~/.claude/skills/` (user) — it does **not** scan the shared `.agents/skills/` path. `onboard-harness` therefore symlinks each `10_Agents/skills/<name>/` folder into `~/.claude/skills/<name>`. Skills' extra vault frontmatter keys are ignored by the loader; `name`/`description` drive discovery.

## Hook installation

**Automatic since 2026-08-11:** the repo ships `.claude/settings.json` with a `SessionStart` hook that runs `git config core.hooksPath .githooks` in every Claude Code session (local, web, cloud containers) — fresh clones arm the pre-commit hook with zero manual setup, closing the stale-index CI failure mode that hook-less agent sessions produce. The pre-commit hook itself runs unchanged (Claude Code commits via Bash). Optional native enhancement: a `PostToolUse` hook on `Write|Edit` in settings can run `brain validate` at edit time instead of commit time; see `settings-example.json` (and issue #11 — the example's current `|| true` form never surfaces findings).

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

Pre-approve it with a permission allow rule (see `settings-example.json`) so queries never prompt.

## Harness-specific notes

- **Permission denies** can hard-enforce change control (deny `Edit` on `00_Meta/**`, `01_Profile/**`) — stricter than the vault's approval-based policy, so the reference config includes them for adopters who want belt-and-suspenders; note an approved canonical edit then requires loosening the rule. There is **no `.claudeignore`** — privacy exclusion is deny `Read()` rules, and the vault-wide privacy policy is still an open owner decision (PRD §21).
- **MCP:** `.mcp.json` at the repo root registers project-scope servers. The vault ships none (the vault MCP server is permanently out of scope; PRD §19 M7) — M7 integrations may add external-source servers here.
- **Output styles** are Claude-Code-only; the vault keeps voice/tone in `01_Profile/preferences.md` instead. An adopter may add a personal output style; the template ships none.

## Reference config

`settings-example.json` — copy into `.claude/settings.json` (project) or merge into `~/.claude/settings.json` (user), adjusting paths.
