---
title: "Codex Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
---

# Codex Wiring

Facts verified 2026-08-11 against [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs) (see [[06_Resources/harness-primitives-research#Codex|research]]); re-verify before relying on paths.

## Entrypoint loading

Codex reads **`AGENTS.md` natively** — global `~/.codex/AGENTS.md` first, then from the git root down to the cwd, concatenated. Two caveats the adapter addresses:

- **No import expansion:** Codex does not expand `@file` imports or `[[wikilinks]]` — the bootstrap works because `AGENTS.md` lists plain paths agents read themselves; do not rely on link-following.
- **32 KiB cap:** combined project docs are capped by `project_doc_max_bytes` (default 32 KiB). The vault's `AGENTS.md` is well under it; if an adopter's grows past the cap, raise the value in config (see `config-example.toml`).

User scope: `onboard-harness` puts the vault import block in `~/.codex/AGENTS.md` (plain-path pointer plus a "read these first" line — Codex has no import syntax to expand).

## Skills

Codex implements the Agent Skills standard and scans repo-scope `.agents/skills/` and user-scope `~/.agents/skills/` — the shared standard path. `onboard-harness`'s `~/.agents/skills/<name>` symlinks cover Codex with no extra work. Invocation: `$skill-name` or implicit description matching. Project-scope resources load only for **trusted** projects.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone; the git hook runs unchanged. Codex-native lifecycle hooks (`.codex/hooks.json`, trusted projects only) can add edit-time validation, but the git hook is the portable enforcement layer.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

Approval for the command falls under Codex's `approval_policy`/sandbox settings; a prefix allow rule can be added in `.codex/rules/` (Starlark `prefix_rule`) for trusted projects.

## Harness-specific notes

- **Trust gate:** `.codex/config.toml`, rules, and hooks in the repo load only after the adopter trusts the project — the wiring doc's user-scope paths work regardless.
- **MCP:** `[mcp_servers.<id>]` tables in `config.toml`. The vault ships none (vault MCP is out of scope); M7 external-source servers register here.
- **No ignore file exists** (feature requests closed unimplemented) — Codex cannot exclude private vault directories; this feeds the open privacy-policy decision (PRD §21).
- **Prompts are deprecated** in favor of skills — ship no `.codex/prompts/`.

## Reference config

`config-example.toml` — copy into `.codex/config.toml` (project, needs trust) or merge into `~/.codex/config.toml` (user).
