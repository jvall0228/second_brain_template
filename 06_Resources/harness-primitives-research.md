---
title: "Harness Primitives Research"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives Research

Grounded research (2026-08-11) on the extension surface of every harness in the [[00_Meta/PRD]] §8.3 support table, plus the universal standards layer they build on. Produced for M6/M7 planning (see [[07_Archives/inbox/2026-08-11-m5-m7-implementation-plan|M5–M7 Implementation Plan]]) by nine parallel research agents working from official documentation; the load-bearing claims are sourced in the per-harness notes linked below. Harness surfaces move fast — treat this as accurate as of the date above and re-verify before each adapter ships (per §8.3, wiring specifics are settled at build time). Unverifiable details are marked as gaps, not guessed. This note holds the cross-harness comparison (headline findings, overlap matrix, implications); the per-harness surface specs and their sources live in the separate notes linked under [[#Per-harness specs]] below.

## Headline Findings

- Exactly two primitives have true cross-harness standards — and they are the two this vault bet on. **AGENTS.md** is native in 6 of 7 harnesses (Claude Code is the only one needing the `CLAUDE.md` adapter — §8.3's table is confirmed row by row). **Agent Skills / SKILL.md** is supported by all 7.
- `.agents/skills/` is the shared skills discovery path (6 of 7 scan it; user scope `~/.agents/skills/`). Claude Code scans only `.claude/skills/` — so onboarding links the shared path once, plus one Claude Code–specific link.
- Custom slash-command files are converging **into** skills — already deprecated in Codex and Cursor. Ship skills, never command files.
- Rules, subagents, hooks, plugins, settings, and permissions are proprietary per harness. Git pre-commit remains the only portable hook layer, which validates the M5 enforcement design.
- Output styles are effectively Claude Code–only (the `/output-style` command was removed but the primitive lives on via settings). Portable voice/tone belongs in [[01_Profile/PREFERENCES]], loaded through the entrypoint.
- MCP is a standard protocol with non-standard per-harness config. Pi has no built-in MCP at all (extensions instead — which suits the integration preference ladder's custom-tooling rung), and Muse Code takes user-scope servers only.
- **No portable privacy/ignore mechanism exists.** Only Cursor honors a repo ignore file; Codex, Pi, and Muse Code have no reliable content-exclusion mechanism. This is an open policy question for the owner — flagged in the implementation plan.
- Codex and opencode read `AGENTS.md` natively but do **not** expand wikilinks or `@`-imports (Codex also caps project docs at 32 KiB) — adapters make the bootstrap deterministic with plain paths (e.g. opencode's `instructions[]`).


## Primitive Overlap Matrix

`~` prefix = partial support; ✗ = none; ? = unknown.

| Primitive | Claude Code | Codex | opencode | Pi | Cursor | Copilot | Muse Code |
|---|---|---|---|---|---|---|---|
| entrypoint-memory | CLAUDE.md +@import | AGENTS.md | AGENTS.md (+CLAUDE.md) | AGENTS.md/CLAUDE.md | AGENTS.md (+CLAUDE.md CLI) | AGENTS.md + copilot-instructions.md | AGENTS.md + .agents/memory |
| rules | .claude/rules/*.md | ~.codex/rules (exec Starlark) | ~instructions[] | ✗ | .cursor/rules/*.mdc | .github/instructions/*.instructions.md | ~nested AGENTS.md |
| skills | SKILL.md (.claude/skills) | SKILL.md (.agents/skills) | SKILL.md (.opencode+.claude+.agents) | SKILL.md (.pi+.agents) | SKILL.md (.cursor+.agents+compat) | SKILL.md (.github+.claude+.agents) | SKILL.md (.agents+compat) |
| commands | .claude/commands/*.md | ~prompts (deprecated) | .opencode/commands/*.md | .pi/prompts/*.md | ~deprecated→skills | .github/prompts/*.prompt.md | ~skills-as-slash only |
| subagents | .claude/agents/*.md | .codex/agents (TOML) | .opencode/agents/*.md | ~ext API only | .cursor/agents/*.md | .github/agents/*.agent.md | ~runtime spawn only |
| hooks | settings.json hooks | hooks.json | ~JS plugin hooks | TS extension events | hooks.json | .github/hooks (CLI+cloud+VS Code) | .muse/hooks.json |
| plugins | plugin.json + marketplaces | /plugins marketplaces | npm plugin[] | pi packages | ~marketplace only | Agent Plugins 1.0 | ✗ |
| output-styles | .claude/output-styles | ~personality toggle | ✗ | ✗ | ✗ | ~custom agents | ✗ |
| mcp | .mcp.json | config.toml [mcp_servers] | opencode.json mcp | ✗ (extension only) | .cursor/mcp.json | per-surface mcp.json | ~user settings only |
| settings | settings.json layers | config.toml layers | opencode.json | .pi/settings.json | UI + cli.json | config.json + chat.* | ~user-only settings.json |
| permissions-sandbox | allow/ask/deny + OS sandbox | sandbox_mode + approvals | ~permission map, no sandbox | ~trust gate only | permissions + --sandbox | allow/deny + Actions sandbox | approvals + sandbox |
| automation-scheduling | -p, SDK, Routines | exec, cloud, RRULE | ~run/serve, no scheduler | -p, RPC, no scheduler | -p, Automations cron | -p, tasks API, gh-aw | ~exec, no scheduler |
| ignore-files | ~deny rules only | ✗ | ~watcher.ignore | ✗ | .cursorignore | ~org settings only | ? |

## Where the Overlaps Are

- **entrypoint-memory — true standard.** AGENTS.md is native in 6/7 harnesses; Claude Code is the sole holdout (reads only CLAUDE.md). Sweet spot: root AGENTS.md + a one-line CLAUDE.md `@AGENTS.md` shim.
- rules — proprietary. Cursor (.mdc) and Copilot (.instructions.md) both do glob-scoped prose rules but in incompatible formats; Codex's ".rules" are exec-policy Starlark, not prose; Pi has nothing. Portable fallback: nested AGENTS.md files (closest-file-wins).
- **skills — true standard.** SKILL.md (agentskills.io) is supported by all 7. Six of seven discover `.agents/skills/`; Claude Code scans only `.claude/skills/` per today's data. Sweet spot: `.agents/skills/` + a symlink/copy for Claude Code.
- commands — converging into skills, not into a standard. Codex prompts and Cursor commands are both officially deprecated in favor of skill invocation. Sweet spot: ship no command files; ship skills.
- subagents — proprietary. Markdown formats (Claude/opencode/Cursor/Copilot) vs TOML (Codex) vs none (Pi, Muse). Cursor and Copilot read `.claude/agents` compat, making Claude's format the closest to portable, but coverage is 4-5/7 at best.
- hooks — proprietary, two camps: JSON shell-hook configs (Claude, Codex, Cursor, Copilot, Muse) vs code APIs (opencode JS, Pi TS). Only portable layer is git pre-commit.
- plugins — proprietary marketplaces everywhere; Copilot auto-detects the Claude plugin format, making plugin.json a weak de-facto seed, not a standard.
- output-styles — effectively Claude Code-only; Codex has a fixed personality toggle, everyone else has nothing. Tone must live in instruction files to be portable.
- **mcp — standard protocol, non-standard config.** The MCP spec is shared, but config locations differ per harness, Pi omits MCP entirely, and Muse supports user-scope only. Portable unit: the server list, not the config file.
- settings — fully proprietary; no overlap at all beyond "there is a project + user layer" in most.
- permissions-sandbox — fully proprietary, with a huge capability spread (OS sandboxes in Claude/Codex/Muse vs Pi's trust-gate-only).
- automation-scheduling — proprietary, but a headless `-p`/`exec` mode exists in all 7; built-in schedulers only in Claude Code, Codex, Cursor (+Copilot via gh-aw).
- ignore-files — the weakest category: only Cursor has a real repo ignore file; Codex explicitly declined one; Copilot's is org-managed and ignored by its own CLI/agent. No portable exclusion mechanism exists.

## Implications for the Standards-First Plan

- The standards track (root AGENTS.md + `10_Agents/skills/` exposed at `.agents/skills/` + plain scripts callable from skills) genuinely carries all 7 harnesses for the two primitives that matter most: bootstrap context and skills. That validates the plan's core bet.
- **Contradiction to flag:** any "reads AGENTS.md natively" claim for Claude Code in the vault's support table is wrong — Claude Code requires the CLAUDE.md `@AGENTS.md` import (which this vault already has, so the mechanism is right even if the table isn't).
- **Contradiction to flag:** Claude Code does not scan `.agents/skills/` per today's data. The Claude Code adapter must ship `.claude/skills/` symlinks (or copies) of the shared skills, or a plugin wrapping them — the standards dir alone won't reach it.
- Adapter file manifests: **Claude Code** = CLAUDE.md, `.claude/skills/` links, `.claude/settings.json` (permission denies), `.mcp.json`; **Codex** = `.codex/config.toml` (trusted) incl. `[mcp_servers]`, optional `.codex/agents/*.toml`; **opencode** = `opencode.json` (instructions[], mcp, permission map); **Pi** = `.pi/settings.json`, `.pi/prompts/*.md`; **Cursor** = `.cursor/rules/*.mdc`, `.cursor/mcp.json`, `.cursorignore`; **Copilot** = `.github/copilot-instructions.md` pointer, `.github/instructions/*.instructions.md`, `.vscode/mcp.json`; **Muse Code** = `.muse/hooks.json` only (no project settings or project MCP exist — Muse config is user-scope, so its adapter is thin by necessity).
- Do not build per-harness command/prompt files: commands are deprecated in Codex and Cursor and absent from the standards layer. Model every invocable workflow as a skill; harnesses that want `/name` invocation get it via skill mechanisms (e.g. Cursor's `disable-model-invocation: true`, Codex `$skillname`).
- Drop any plan use of output styles outside Claude Code — 5/7 harnesses have none. Voice/tone belongs in `01_Profile/PREFERENCES` referenced from AGENTS.md; a `.claude/output-styles/` file is an optional Claude-only nicety.
- Privacy exclusions cannot be a single ignore file. Only Cursor honors one; Codex has none at all (feature requests closed unimplemented). If the vault plans to fence off directories (e.g. private journal), each adapter needs its own deny mechanism (Claude/opencode/Cursor/Copilot permission denies), and Codex/Pi/Muse have **no reliable exclusion at all** — surface this gap to the owner as a policy decision, not a config task.
- Keep one canonical MCP server manifest in `10_Agents/` and generate per-harness configs from it; accept that Pi gets no MCP (skills there must degrade to plain scripts) and Muse can't receive project-scoped servers.
- Hook-driven vault automation (e.g. auto-bumping `updated:`, Inbox-first enforcement) cannot ride the standards track — hook formats are 100% proprietary and two harnesses need code, not config. Implement once as a git pre-commit hook (portable), with per-harness hooks as optional enhancements.
- Treat the Muse Code adapter as draft/volatile: the product is 6 days old, its SKILL.md frontmatter spec is unpublished, and its ignore/instruction-path story is undocumented. Re-verify before hardening that adapter.

## Per-harness specs

The full per-harness surface specs — each self-contained with its own sources and research gaps — live in dedicated notes (split out from this note on 2026-08-11 so each harness is one topic, one note):

- [[06_Resources/harness-standards|Universal standards & protocols]] — AGENTS.md, Agent Skills, MCP: the portability substrate every adapter builds on
- [[06_Resources/harness-claude-code|Claude Code]] (P0)
- [[06_Resources/harness-codex|Codex]] (P0)
- [[06_Resources/harness-opencode|opencode]] (P0)
- [[06_Resources/harness-pi|Pi]] (P0)
- [[06_Resources/harness-copilot|GitHub Copilot]] (P0)
- [[06_Resources/harness-cursor|Cursor]] (P1)
- [[06_Resources/harness-muse-code|Muse Code]] (P1)

## Related

- [[00_Meta/PRD]] — §8.3 support tiers this research grounds; §9.3 plugin-library design
- [[07_Archives/inbox/2026-08-11-m5-m7-implementation-plan|M5–M7 Implementation Plan]] — consumes these findings (adapter manifests, install map)
- [[01_Profile/PREFERENCES]] — portable home for voice/tone (in lieu of output styles)
