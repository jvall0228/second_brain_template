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

Facts verified 2026-08-11 against [code.claude.com/docs](https://code.claude.com/docs) (see [research](../../../06_Resources/harness-claude-code.md)); re-verify before relying on paths.

## Entrypoint loading

Claude Code does **not** read `AGENTS.md` natively — it loads `CLAUDE.md`, and the vault's root `CLAUDE.md` (`@AGENTS.md`) is exactly the documented memory-import pattern, so **project scope needs no setup**. User scope: `onboard-harness` first creates the stable shared registration at `~/.agents/second-brain/AGENTS.md`, then appends a marker-delimited `@~/.agents/second-brain/AGENTS.md` import to `~/.claude/CLAUDE.md`. Claude therefore loads only the thin registration globally; that registration points at the adopter's actual vault and tells Claude to read the vault's `AGENTS.md` when owner-specific context materially helps with the task. The adopter-specific vault path never appears in this template or in the Claude adapter block.

## Skills

Claude Code scans `.claude/skills/` (project) and `~/.claude/skills/` (user) — it does **not** scan the shared `.agents/skills/` path. A clean clone includes generated text adapters in `.claude/skills/`; each mirrors the canonical `name`/`description` and points to `10_Agents/skills/<name>/SKILL.md`. No project symlinks or onboarding writes are needed. Optional user-global mode retains the manifest-owned `~/.claude/skills/<name>` link/copy route after exact preview and approval.

## Hook installation

**Automatic since 2026-08-11:** the repo ships `.claude/settings.json` with a `SessionStart` hook that runs `git config core.hooksPath .githooks` in every Claude Code session (local, web, cloud containers) — fresh clones arm the pre-commit hook with zero manual setup, closing the stale-index CI failure mode that hook-less agent sessions produce. The pre-commit hook itself runs unchanged (Claude Code commits via Bash). Optional native enhancement: a `PostToolUse` hook on `Write|Edit` in settings can run `brain validate` at edit time instead of commit time; see `settings-example.json`, which calls the `validate-hook.sh` shim so findings actually reach the agent (see the exit-code contract below; fixed under issue #11).

## Edit-time validation exit codes

Claude Code's `PostToolUse` hook contract and `brain validate`'s exit-code contract ([spec](../../tools/brain/spec.md) §10.4) do **not** line up, and wiring one directly to the other silently breaks edit-time validation:

- **Claude Code hooks:** exit `0` = success; exit `2` = *blocking error* — STDERR is fed back to the agent; any **other** exit code is non-blocking and the output never reaches the agent.
- **`brain validate`:** exit `0` = clean; exit `1` = errors; exit `2` = warnings only.

So a raw `brain validate` in a hook inverts the semantics: errors (exit 1) vanish, and warnings (exit 2) would block. The historical `|| true` form (issue #11) was worse still — it forced exit 0 unconditionally, making the hook a no-op. The shim `validate-hook.sh` translates between the contracts: brain exit 0 or 2 → hook exit 0 (warnings never block, matching the pre-commit hook's policy); brain exit 1 (or any unexpected failure) → findings re-emitted on STDERR and hook exit 2, so the agent sees them and fixes the note immediately. **Future harness adapters that wire `brain validate` into an edit-time hook must map exit codes to that harness's own hook contract the same way — never call it bare, and never append `|| true`.**

## Invoking brain

```
brain <command> --json
```

Pre-approve it with a permission allow rule (see `settings-example.json`) so queries never prompt.

**Semantic search** ([spec](../../tools/brain/spec.md) §18): `brain search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `brain embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **Permission denies** can hard-enforce change control (deny `Edit` on `00_Meta/**`, `01_Profile/**`) — stricter than the vault's approval-based policy, so the reference config includes them for adopters who want belt-and-suspenders; note an approved canonical edit then requires loosening the rule. There is **no `.claudeignore`** — privacy exclusion is deny `Read()` rules, and the vault-wide privacy policy is still an open owner decision (PRD §21).
- **MCP:** `.mcp.json` at the repo root registers project-scope servers. The vault ships none (the vault MCP server is permanently out of scope; PRD §19.1) — environment integrations may add external-source servers here under PRD §8.4.
- **Output styles** are Claude-Code-only; the vault keeps voice/tone in `01_Profile/PREFERENCES.md` instead. An adopter may add a personal output style; the template ships none.

## Reference config

`settings-example.json` — copy into `.claude/settings.json` (project) or merge into `~/.claude/settings.json` (user), adjusting paths.
