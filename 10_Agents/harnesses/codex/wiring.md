---
title: "Codex Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# Codex Wiring

Facts verified 2026-08-11 against [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs) (see [[06_Resources/harness-codex|research]]); re-verify before relying on paths.

## Entrypoint loading

Codex reads **`AGENTS.md` natively** — global `~/.codex/AGENTS.md` first, then from the git root down to the cwd, concatenated. Two caveats the adapter addresses:

- **No import expansion:** Codex does not expand `@file` imports or `[[wikilinks]]` — the bootstrap works because `AGENTS.md` lists plain paths agents read themselves; do not rely on link-following.
- **32 KiB cap:** combined project docs are capped by `project_doc_max_bytes` (default 32 KiB). The vault's `AGENTS.md` is well under it; if an adopter's grows past the cap, raise the value in config (see `config-example.toml`).

User scope: `onboard-harness` creates `~/.agents/second-brain/AGENTS.md`, then puts a marker-delimited plain-text instruction in `~/.codex/AGENTS.md` telling Codex that personal second-brain context is registered there and to read it when owner-specific context materially helps with the task. Codex has no import syntax to expand, so the adapter does not use `@`; it also does not embed the adopter's vault path. The shared registration owns that runtime-specific path and routes onward to the vault's `AGENTS.md`.

## Skills

Codex implements the Agent Skills standard and scans repo-scope `.agents/skills/` and user-scope `~/.agents/skills/` — the shared standard path. `onboard-harness`'s `~/.agents/skills/<name>` symlinks cover Codex with no extra work. Invocation: `$skill-name` or implicit description matching. Project-scope resources load only for **trusted** projects.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone; the git hook runs unchanged. Codex-native lifecycle hooks (`.codex/hooks.json`, trusted projects only) can add edit-time validation, but the git hook is the portable enforcement layer.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

Approval for the command falls under Codex's `approval_policy`/sandbox settings; a prefix allow rule can be added in `.codex/rules/` (Starlark `prefix_rule`) for trusted projects.

**Semantic search** ([[10_Agents/tools/brain/spec|spec]] §18): `python3 10_Agents/tools/brain/brain.py search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `python3 10_Agents/tools/brain/brain.py embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **Trust gate:** `.codex/config.toml`, rules, and hooks in the repo load only after the adopter trusts the project — the wiring doc's user-scope paths work regardless.
- **MCP:** `[mcp_servers.<id>]` tables in `config.toml`. The vault ships none (vault MCP is out of scope); M7 external-source servers register here.
- **No ignore file exists** (feature requests closed unimplemented) — Codex cannot exclude private vault directories; this feeds the open privacy-policy decision (PRD §21).
- **Prompts are deprecated** in favor of skills — ship no `.codex/prompts/`.

## Reference config

`config-example.toml` — copy into `.codex/config.toml` (project, needs trust) or merge into `~/.codex/config.toml` (user).
