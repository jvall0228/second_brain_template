---
title: "Muse Code Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/draft
updated: 2026-08-11
expires: 2026-11-11
---

# Muse Code Wiring

**Volatile adapter.** Muse Code (Meta) launched 2026-08-05 — six days before this doc. Facts verified 2026-08-11 (see [[06_Resources/harness-muse-code|research]]); its SKILL.md frontmatter spec is unpublished and paths are undocumented in places. This doc stays `workflow/draft` (unlike the other adapters) until the surface stabilizes — **re-verify everything before relying on it.**

## Entrypoint loading

Muse Code reads **`AGENTS.md` natively and preferentially** (it ignores `CLAUDE.md` when `AGENTS.md` exists) — the vault bootstrap loads unmodified. Bootstrap links work as prose only; no import mechanism exists. User-scope onboarding still creates the shared registration at `~/.agents/second-brain/AGENTS.md`, but the current adapter does **not** invent an undocumented global instruction location or assume Muse discovers that file automatically. If a documented user-level instruction or memory-injection surface is available when onboarding runs, add a marker-managed plain-path reference to the shared registration there; otherwise report that persistent second-brain registration is not yet supported for Muse and leave the shared file ready for a future adapter update.

## Skills

Muse scans the shared `.agents/skills/` (plus compat paths) — the `~/.agents/skills/<name>` symlinks cover it. Skills surface as slash invocations; frontmatter details beyond `name`/`description` are unverified.

## Hook installation

`git config core.hooksPath .githooks` in the vault clone; `.muse/hooks.json` is the only project-scope Muse artifact and is optional polish.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

**Semantic search** ([[10_Agents/tools/brain/spec|spec]] §18): `python3 10_Agents/tools/brain/brain.py search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `python3 10_Agents/tools/brain/brain.py embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **Config is user-scope only** (`~/.config/muse/settings.json`) — no project settings, no project MCP. Anything per-vault must be documented for manual user-scope setup, not committed.
- **Memory bridge** is the adapter's distinctive job: once Muse's memory format is stable, use it to reference `~/.agents/second-brain/AGENTS.md` rather than duplicating vault context or embedding the vault path — deferred until the memory format is stable.
- No ignore/exclusion mechanism is documented — feeds the open privacy-policy decision (PRD §21).

## Reference config

None shipped — with user-scope-only config and an unstable surface, prose instructions are the honest deliverable today.
