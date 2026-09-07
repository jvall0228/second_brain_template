---
title: "Claude Code Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-07
expires: 2026-11-11
---

# Claude Code Wiring

Facts verified 2026-08-11 against [code.claude.com/docs](https://code.claude.com/docs) (see [research](../../../06_Resources/harness-claude-code.md)); re-verify before relying on paths.

[onboard-harness](../../skills/setup/onboard-harness/SKILL.md) currently supports project verification and read-only global preview. User-global installation, reconciliation, and uninstall are deferred; the user-global designs below are not executable setup instructions.

## Entrypoint loading

Claude Code does **not** read `AGENTS.md` natively — it loads `CLAUDE.md`, and the vault's root `CLAUDE.md` (`@AGENTS.md`) is exactly the documented memory-import pattern, so **project scope needs no setup**. Deferred user-scope design: a future `onboard-harness` backend would create the stable shared registration at `~/.agents/second-brain/AGENTS.md`, then append a marker-delimited `@~/.agents/second-brain/AGENTS.md` import to `~/.claude/CLAUDE.md`. Claude therefore loads only the thin registration globally; that registration points at the adopter's actual vault and tells Claude to read the vault's `AGENTS.md` when owner-specific context materially helps with the task. The adopter-specific vault path never appears in this template or in the Claude adapter block.

## Skills

Claude Code scans `.claude/skills/` (project) and `~/.claude/skills/` (user) — it does **not** scan the shared `.agents/skills/` path. A clean clone includes generated text adapters in `.claude/skills/`; each mirrors the canonical `name`/`description` and points, via its `canonical-source` field, to the real `SKILL.md` — `10_Agents/skills/<name>/SKILL.md` for a flat skill, `10_Agents/skills/<group>/<name>/SKILL.md` for a grouped one such as the setup skills. No project symlinks or onboarding writes are needed. User-global links/copies remain deferred; current onboarding only previews proposed targets.

## Skill-run log

`.claude/settings.json` also ships a `PostToolUse` hook matched to the `Skill` tool that runs `skill-run-log.sh` (a thin wrapper around `skill-run-log.py`, which parses the payload). It appends one tab-separated line — UTC timestamp, `claude-code`, skill name, `ok` or `error` — to the append-only [skill-runs log](../../docs/skill-runs.log) and always exits 0, so it never blocks a session. Before writing it authenticates the log path below the vault root component by component with no-follow opens and verifies the opened object is a regular file, so a log or parent directory replaced by a symlink (or a missing log) is silently skipped rather than followed outside the vault. The log is tracked and merges by union (`.gitattributes`), and the [self-improve](../../skills/self-improve/SKILL.md) loop reads it as usage evidence: which skills run, how often, and which fail. Other harnesses that expose a post-tool hook can write the same line shape with their own harness name.

**Coverage:** this repository wires only the Claude Code `Skill` hook. Direct skill-file reads (including Codex use), other harnesses, disabled hooks, and silently skipped writes are unobserved. For each retrospective, report the harness and first/last timestamp actually observed in its chosen window; an empty window has no observed coverage. Those timestamps do not establish continuous instrumentation. Missing rows mean unknown, never proof of non-use; a disuse-based pruning proposal needs independent evidence.

## Hook installation

**Automatic since 2026-08-11:** the repo ships `.claude/settings.json` with a `SessionStart` hook that runs `git config core.hooksPath .githooks` in every Claude Code session (local, web, cloud containers) — fresh clones arm the pre-commit hook with zero manual setup, closing the stale-index CI failure mode that hook-less agent sessions produce. The pre-commit hook itself runs unchanged (Claude Code commits via Bash). Optional native enhancement: a `PostToolUse` hook on `Write|Edit` in settings can run `brain validate` at edit time instead of commit time; see `settings-example.json`, which calls the `validate-hook.sh` shim so findings actually reach the agent (see the exit-code contract below; fixed under issue #11).

## Edit-time validation exit codes

Claude Code's `PostToolUse` hook contract and `brain validate`'s exit-code contract ([spec](../../tools/brain/SPEC.md) §10.4) do **not** line up, and wiring one directly to the other silently breaks edit-time validation:

- **Claude Code hooks:** exit `0` = success; exit `2` = *blocking error* — STDERR is fed back to the agent; any **other** exit code is non-blocking and the output never reaches the agent.
- **`brain validate`:** exit `0` = clean; exit `1` = errors; exit `2` = warnings only.

So a raw `brain validate` in a hook inverts the semantics: errors (exit 1) vanish, and warnings (exit 2) would block. The historical `|| true` form (issue #11) was worse still — it forced exit 0 unconditionally, making the hook a no-op. The shim `validate-hook.sh` translates between the contracts: brain exit 0 or 2 → hook exit 0 (warnings never block, matching the pre-commit hook's policy); brain exit 1 (or any unexpected failure) → findings re-emitted on STDERR and hook exit 2, so the agent sees them and fixes the note immediately. **Future harness adapters that wire `brain validate` into an edit-time hook must map exit codes to that harness's own hook contract the same way — never call it bare, and never append `|| true`.**

## Invoking brain

```
brain <command> --json
```

Pre-approve it with a permission allow rule (see `settings-example.json`) so queries never prompt.

**Semantic search** ([spec](../../tools/brain/SPEC.md) §18): `brain search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `brain embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **Permission denies** can hard-enforce change control (deny `Edit` on `00_Meta/**`, `01_Profile/**`) — stricter than the vault's approval-based policy, so the reference config includes them for adopters who want belt-and-suspenders; note an approved canonical edit then requires loosening the rule. There is **no `.claudeignore`** — privacy exclusion is deny `Read()` rules, and the vault-wide privacy policy is still an open owner decision (PRD §21).
- **MCP:** `.mcp.json` at the repo root registers project-scope servers. The vault ships none (the vault MCP server is permanently out of scope; PRD §19.1) — environment integrations may add external-source servers here under PRD §8.4.
- **Output styles** are Claude-Code-only; the vault keeps voice/tone in `01_Profile/PREFERENCES.md` instead. An adopter may add a personal output style; the template ships none.

## Reference config

`settings-example.json` — copy into `.claude/settings.json` (project) or merge into `~/.claude/settings.json` (user), adjusting paths.
