---
title: "Harness Primitives: Pi"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: Pi

Part of the [harness primitives research](harness-primitives-research.md) (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

Pi is a deliberately minimal, "aggressively extensible" open-source terminal coding agent by Mario Zechner (badlogic, of libGDX fame), now maintained under [Earendil Inc.](https://pi.dev) with contributors (npm maintainers include Armin Ronacher); it lives in the [pi-mono monorepo](https://github.com/badlogic/pi-mono) (canonical org now `earendil-works`), ships as the CLI/TUI `@earendil-works/pi-coding-agent` (v0.84.1, 2026-08-07) plus an SDK and RPC mode — MIT-licensed and free, bring-your-own API keys. Its philosophy: four default tools, a tiny system prompt, and everything else (sub-agents, plan mode, permissions, MCP) pushed out to user-installable extensions.

## Context & memory files
Pi reads **AGENTS.md natively** — and accepts `CLAUDE.md` as an equivalent project context file. Load order per the [README](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md): `~/.pi/agent/AGENTS.md` (global), then `AGENTS.md`/`CLAUDE.md` in each parent directory walking down to cwd, concatenated. An `AGENTS.override.md` in a directory replaces that directory's context file (others still load). System prompt itself is replaceable via `.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md`, or extended via `APPEND_SYSTEM.md` in the same locations. Disable with `pi --no-context-files` / `-nc`. No `@import` mechanism found in docs (unverified as of 2026-08-11).

## Rules
No dedicated rule-file system (no glob-scoped, auto-attached rules). Always-on instructions are exactly the context-file chain above plus `APPEND_SYSTEM.md`; conditional behavior is instead delegated to skills (model-invoked) or extensions (programmatic). "None found" beyond that.

## Skills
First-class, following the [Agent Skills standard](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md) (agentskills.io): folders with `SKILL.md`, YAML frontmatter `name` (required, ≤64 chars, lowercase/hyphens) and `description` (required, ≤1024 chars; skills missing it are not loaded), optional `license`, `compatibility`, `metadata`, `allowed-tools`, `disable-model-invocation`. Progressive disclosure: names+descriptions go in the system prompt; full body loads on demand. Discovery: `~/.pi/agent/skills/`, `~/.agents/skills/`, and (after project trust) `.pi/skills/` and **`.agents/skills/`** searched from cwd upward; also Pi packages, settings arrays, and `--skill <path>`. Invoke manually with `/skill:name`; disable discovery with `--no-skills`. First-discovered wins on name collisions.

## Commands
"Prompt templates": markdown files whose filename becomes a slash command (`review.md` → `/review`), per [prompt-templates.md](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/prompt-templates.md). Optional YAML frontmatter `description` and `argument-hint`; bash-style args `$1`, `$@`/`$ARGUMENTS`, `${1:-default}`, `${@:N:L}`. Locations: `~/.pi/agent/prompts/*.md`, `.pi/prompts/*.md` (trust-gated), package `prompts/` dirs, settings, `--prompt-template <path>`; non-recursive discovery. Extensions can also register programmatic `/commands` via `pi.registerCommand()`.

## Subagents / custom agents
Deliberately **not built-in** — the README lists "No sub-agents" as a design choice: spawn pi in tmux, or build them with the extension API (example extensions demonstrate sub-agent/plan-mode patterns; `ctx.newSession()`, `ctx.fork()`, `ctx.switchSession()` exist in command context). No agent-definition file format exists.

## Hooks
No shell-command hook config; the equivalent is the [TypeScript extension event system](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md): `pi.on(event, handler)` with events including `session_start`, `session_shutdown`, `before_agent_start` (inject messages / modify system prompt), `input`, `tool_call` (can **block** via `{ block: true, reason }` or mutate args), `tool_result` (patch output), `turn_start/end`, `message_start/update/end`, `model_select`, `project_trust`. Handlers get UI primitives (`ctx.ui.confirm()` etc.) and session access.

## Plugins
Two layers. (1) **Extensions**: TypeScript modules loaded via jiti (no compile step), default-export factory receiving `ExtensionAPI` — register tools (`pi.registerTool` with TypeBox schema + custom TUI renderers), commands, providers, event handlers. Locations: `~/.pi/agent/extensions/*.ts` (+`*/index.ts`), `.pi/extensions/` (trust-gated), settings, `-e ./ext.ts`. (2) **Pi packages**: npm or git repos installed with `pi install npm:@foo/pi-tools` / `pi install git:github.com/user/repo[@tag]` (user-scope under `~/.pi/agent/{npm,git}/`, or project-local with `-l` into `.pi/`), bundling extensions, skills, prompts, and themes via a `package.json` `"pi"` manifest (keyword `pi-package`); managed with `pi list/update/remove/config`. No central marketplace; npm/git are the registry.

## Output styles / personas
No output-styles feature (nothing deprecated — never existed). Closest analog: full system-prompt replacement (`SYSTEM.md`) or append (`APPEND_SYSTEM.md`), plus TUI **themes** (JSON, hot-reloading, built-in `dark`/`light`, in `~/.pi/agent/themes/`, `.pi/themes/`, packages, `--theme <path>`), which style the UI, not the model's voice.

## MCP
**Intentionally not built in.** The README's stated stance: "Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support." MCP clients can be added as a third-party Pi package/extension; no config file, scopes, or transports exist in core.

## Config & settings
`~/.pi/agent/settings.json` (global) and `.pi/settings.json` (project; trust-gated), deep-merged with project winning, per [settings.md](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md). Keys cover model defaults (`defaultProvider`, `defaultModel`, `defaultThinkingLevel`), `theme`, `compaction.*`, `retry.*`, resource arrays (`packages`, `extensions`, `skills`, `prompts`, `themes`, `enableSkillCommands`), `defaultProjectTrust` (global-only), telemetry toggles. Env vars: `PI_CODING_AGENT_DIR` (relocate config), `PI_CODING_AGENT_SESSION_DIR`, `PI_OFFLINE`, `PI_TELEMETRY`, plus session metadata exported to bash tools (`PI_SESSION_ID`, `PI_MODEL`, ...). Custom providers/models via `models.json` ([docs](https://pi.dev)).

## Permissions & sandboxing
No permission popups or allowlists by design — "Pi does not include a built-in permission system"; the docs direct users to containerize (three documented patterns: Gondolin extension, plain Docker, OpenShell, in `packages/coding-agent/docs/containerization.md`) or build extension-based permission gates (examples provided). What does exist is **project trust**: interactive pi prompts before loading `.pi/` resources or `.agents/skills/`; decisions saved via `/trust` to `~/.pi/agent/trust.json`; overridable per-run with `--approve`/`--no-approve`; headless modes fall back to `defaultProjectTrust` (`ask`→ignore / `never` / `always`). Tools can be pruned with `--exclude-tools`.

## Automation & scheduling
Strong headless story, no built-in scheduler. `pi -p "prompt"` one-shot (reads piped stdin), `--mode json` (JSONL event stream), `--mode rpc` (strict LF-delimited JSONL over stdio for non-Node hosts, [rpc.md](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/rpc.md)), and an [SDK](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/sdk.md) (`createAgentSession()`, `AgentSession.prompt()/steer()/subscribe()`, `runPrintMode()`, `runRpcMode()`, in-memory sessions) for CI/pipelines. Sessions are branchable JSONL trees (`-c`, `-r`, `--fork`, `/tree`, `/compact`) exportable to HTML via `--export`. Scheduling is external (cron/CI).

## Vault wiring implications
- **Zero-adapter entrypoint**: pi natively reads our root `AGENTS.md` (and would fall back to `CLAUDE.md`), walking parents → cwd, so the bootstrap sequence works unmodified; a user-global `~/.pi/agent/AGENTS.md` could add owner-level defaults without touching the vault.
- **Skills land in the shared path**: pi discovers `.agents/skills/` natively (trust-gated), so the vault's SKILL.md folders need no copying — the same tree serves pi, Claude Code, and other agentskills.io consumers. `10_Agents/` docs can point at `/skill:name` invocation.
- **The stdlib `brain` CLI is pi's preferred integration**: pi's explicit anti-MCP stance ("CLI tools with READMEs") means our CLI + a thin SKILL.md wrapper is the *native* pattern here, not a fallback.
- **Pre-commit hook is unaffected** (git runs it), but in-session frontmatter/Inbox-first enforcement needs a small TypeScript extension in `.pi/extensions/` hooking `tool_call` on write/edit to block or warn — this extension is the main pi-only artifact the adapter must carry.
- **Adapter also ships**: `.pi/prompts/*.md` mirroring our slash commands (bash-style `$1`/`$@` args differ from other harnesses), optional `.pi/settings.json`, and a note that users must `/trust` the vault once (or set `defaultProjectTrust`) before any `.pi/` or `.agents/skills/` resources load — headless runs silently ignore them otherwise.
- **Optional**: publish the whole toolkit as a Pi package (`pi install git:...`) bundling extension + skills + prompts + a vault theme in one manifest.

## Sources
- https://pi.dev (official site/docs portal)
- https://github.com/badlogic/pi-mono (redirects to earendil-works/pi-mono; root README, AGENTS.md)
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/README.md
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/skills.md
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/extensions.md
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/settings.md
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/prompt-templates.md
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/sdk.md
- https://registry.npmjs.org/@earendil-works/pi-coding-agent (version/license/maintainers)

**Research gaps (2026-08-11):** Import/@-mention mechanism for context files: none documented, but absence not explicitly stated — marked unverified. Whether the skills `allowed-tools` frontmatter is enforced or advisory in pi was not verified. Theme JSON schema internals not inspected (format/locations/hot-reload verified via README only). The full extension event list beyond those quoted in extensions.md was not exhaustively enumerated. npmjs.com web page returned 403 via proxy, so version/license/maintainers were verified via the registry API instead. Canonical repo org (badlogic vs earendil-works) inferred from npm homepage field plus working redirect; GitHub rename not independently confirmed. The claim that pi powers OpenClaw comes from search-result snippets (blogs), not official docs, and was left out of the spec's factual claims accordingly.
