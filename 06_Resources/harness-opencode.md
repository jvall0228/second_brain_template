---
title: "Harness Primitives: opencode"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: opencode

Part of the [harness primitives research](harness-primitives-research.md) (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

[opencode](https://github.com/sst/opencode) is "the open source coding agent" — MIT-licensed (~196k stars), built by the SST team and maintained under Anomaly Co. (repo `sst/opencode`, org now `anomalyco`). Surfaces: terminal TUI, CLI (`opencode run`), headless HTTP server (`opencode serve`), web UI (`opencode web`), desktop app (macOS/Windows/Linux), IDE/VS Code extension, and ACP support (stdio nd-JSON) for editors like Zed. The tool itself is free; you bring provider API keys (any provider via Models.dev) or use its paid Zen model gateway.

## Context & memory files
opencode reads **`AGENTS.md` natively** — confirmed: "You can provide custom instructions to opencode by creating an `AGENTS.md` file" ([rules doc](https://opencode.ai/docs/rules/)). Load order: (1) local files found by traversing up from cwd (`AGENTS.md`, with `CLAUDE.md` as Claude Code-compat fallback — "if you have both AGENTS.md and CLAUDE.md, only AGENTS.md is used"); (2) global `~/.config/opencode/AGENTS.md`; (3) fallback `~/.claude/CLAUDE.md`. Claude compat is disabled via `OPENCODE_DISABLE_CLAUDE_CODE=1` (or `_PROMPT`/`_SKILLS` variants). Additional files load via the `instructions` array in `opencode.json` — supports relative paths, globs (`.cursor/rules/*.md`, `packages/*/AGENTS.md`), and remote URLs (5s fetch timeout); all are combined with `AGENTS.md`. Important: opencode "doesn't automatically parse file references in AGENTS.md" — no `@file` auto-import; the docs recommend `instructions` globs or explicit lazy-read instructions instead.

## Rules
No separate rule-file format (no `.mdc`, no per-rule frontmatter or glob-triggered activation). "Rules" = `AGENTS.md` files plus the `instructions` config array ([rules doc](https://opencode.ai/docs/rules/)); everything listed is always loaded into context. Globs select *which files* load, not *when* they activate. On-demand/triggered loading is instead served by Skills (below).

## Skills
First-class [Agent Skills support](https://opencode.ai/docs/skills/), loaded on demand via a native `skill` tool. Discovery paths (project paths found by walking up to the git worktree root): `.opencode/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`, plus global `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/`. Frontmatter: `name` (required, `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 chars, must match dir name), `description` (required, 1–1024 chars), optional `license`, `compatibility`, `metadata` (string map); unknown fields ignored (so Claude's `allowed-tools` is tolerated but inert). Skills are gated by pattern-based `permission.skill` rules (`allow`/`ask`/`deny`, per-agent overridable) and the tool can be disabled per agent via `tools: { skill: false }`.

## Commands
Custom slash commands are markdown files — filename becomes `/name` — in `.opencode/commands/` (project) or `~/.config/opencode/commands/` (global), or inline under the `command` key in config ([commands doc](https://opencode.ai/docs/commands/)). Frontmatter: `description`, `agent`, `model`, `subtask` (force subagent invocation). Templates support `$ARGUMENTS` and positional `$1..$n`, `` !`cmd` `` shell-output injection, and `@file` file inclusion. Custom commands can override built-ins (`/init`, `/undo`, ...). No `.claude/commands/` compat path is documented. Runnable headless via `opencode run --command <name>`.

## Subagents / custom agents
Two kinds: **primary agents** (built-ins: `build`, `plan`) switched with Tab, and **subagents** (built-ins: `general`, `explore`, `scout`) invoked by `@mention` or the `task` tool ([agents doc](https://opencode.ai/docs/agents/)). Define as markdown in `.opencode/agents/` (project) or `~/.config/opencode/agents/` (global) — filename = agent name; body = system prompt. Frontmatter: `description` (required), `mode` (`primary`/`subagent`/`all`), `model`, `temperature`, `top_p`, `steps` (replaces deprecated `maxSteps`), `permission`, `tools`, `prompt` (supports `{file:./prompts/x.txt}`), `disable`, `color`. Same options available under the `agent` key in `opencode.json`. `subagent_depth` controls nesting. No `.claude/agents/` compat documented.

## Hooks
No declarative shell-hook config (nothing like Claude Code's `hooks` in settings). Lifecycle interception is done in **JS/TS plugins**: `tool.execute.before` / `tool.execute.after` (can mutate args or throw to block), `chat`/`message.*`, `session.*` (incl. `session.idle`, `session.compacted`), `permission.asked`/`permission.replied`, `file.edited`, `file.watcher.updated`, `command.executed`, `shell.env` (inject env into all shell executions), `tui.*`, and `experimental.session.compacting` (inject or replace the compaction prompt) ([plugins doc](https://opencode.ai/docs/plugins/)).

## Plugins
Plugins are JS/TS modules exporting async functions that receive `{ project, client, $, directory, worktree }` (Bun shell + SDK client) and return a hooks object. Load from `.opencode/plugins/` (project), `~/.config/opencode/plugins/` (global), or npm packages listed in the `plugin` config array (installed via Bun at startup, cached in `~/.cache/opencode/node_modules/`). Load order: global config → project config → global dir → project dir. Local plugin deps go in a `.opencode/package.json`. Plugins can also register **custom tools** (`tool` helper from `@opencode-ai/plugin`, Zod-schema args) that take precedence over same-named built-ins; standalone custom tools also live in `.opencode/tools/` / `~/.config/opencode/tools/` (filename = tool name) ([custom tools doc](https://opencode.ai/docs/custom-tools/)). Community registry is the docs [ecosystem page](https://opencode.ai/docs/ecosystem/); no marketplace/bundle format — a "plugin" is one npm package or file.

## Output styles / personas
No dedicated output-style/response-persona feature. Nearest equivalents: agent definitions with custom `prompt` (personas), and [TUI themes](https://opencode.ai/docs/themes/) — JSON color themes from `~/.config/opencode/themes/*.json` and `.opencode/themes/*.json` — which are visual only. No deprecated output-style feature exists to note.

## MCP
Full MCP client. Configured under the `mcp` key in `opencode.json` ([MCP doc](https://opencode.ai/docs/mcp-servers/)): `"type": "local"` (`command` array, `environment`, `cwd`, `timeout` default 5000ms) or `"type": "remote"` (`url`, `headers`, `oauth`, `timeout`); per-server `enabled` toggle. Remote servers get automatic OAuth (401 detection + Dynamic Client Registration RFC 7591, tokens stored). Orgs can ship default MCP servers via a `.well-known/opencode` remote config that local config overrides. Scopes follow config precedence (global vs project file).

## Config & settings
`opencode.json` / `opencode.jsonc` (schema `https://opencode.ai/config.json`) plus `tui.json` (`https://opencode.ai/tui.json`) for theme/keybinds ([config doc](https://opencode.ai/docs/config/)). Precedence (low→high): remote `.well-known/opencode` → global `~/.config/opencode/opencode.json` → `OPENCODE_CONFIG` → project-root `opencode.json` → `.opencode` dirs → `OPENCODE_CONFIG_CONTENT` → managed config (`/etc/opencode/`, macOS `/Library/Application Support/opencode/`, `%ProgramData%\opencode`) → macOS MDM `.mobileconfig`; configs deep-merge. Key keys: `model`, `small_model`, `provider`, `agent`, `default_agent`, `instructions`, `command`, `permission`, `mcp`, `plugin`, `formatter`, `lsp`, `share`, `snapshot`, `watcher.ignore`, `compaction`, `server.*`. Variable substitution: `{env:VAR}` and `{file:path}`.

## Permissions & sandboxing
Pattern-based `permission` map with `allow`/`ask`/`deny` per tool: `read`, `edit` (covers write/patch), `glob`, `grep`, `bash` (patterns match parsed commands, e.g. `"git *": "allow"`), `task` (subagent type), `skill`, `webfetch`, `websearch`, `question`, `lsp`, plus guards `external_directory` (paths outside the workspace; default `ask`) and `doom_loop` (identical call repeated 3×; default `ask`). Last matching rule wins; `~`/`$HOME` expansion supported. Defaults are permissive (`read` allows but `*.env` denied by default). Per-agent permission overrides merge over global. `--auto` flag / TUI toggle auto-approves anything not explicitly denied. As of v1.1.1 the legacy boolean `tools` config is deprecated into `permission` ([permissions doc](https://opencode.ai/docs/permissions/)). No OS-level sandbox (container/seccomp) is documented — enforcement is at the permission layer.

## Automation & scheduling
Headless one-shot: `opencode run "prompt"` with `--agent`, `--command`, `--session`/`--continue`/`--fork`, `--format json` (raw JSON events), `--auto`, and `--attach <url>` to reuse a warm server ([CLI doc](https://opencode.ai/docs/cli/)). Long-running: `opencode serve` (OpenAPI 3.1 HTTP server, SSE events, basic-auth via `OPENCODE_SERVER_PASSWORD`; JS SDK generated from it) and `opencode web`; `opencode attach` connects a TUI to a remote server. CI: [GitHub agent](https://opencode.ai/docs/github/) installed via `opencode github install` → `.github/workflows/opencode.yml`, triggered by `/oc` or `/opencode` comments on issues/PRs. Session export/import as JSON. No built-in cron/scheduler — pair `opencode run` with external schedulers.

## Vault wiring implications
- **Zero-cost entrypoint**: our root `AGENTS.md` loads natively (and `CLAUDE.md` is unnecessary here since `AGENTS.md` wins). But opencode does **not** follow `[[wikilinks]]` or `@file` references, so the opencode adapter should ship an `opencode.json` with `"instructions": ["01_Profile/NOW.md", "01_Profile/PREFERENCES.md", "00_Meta/CONVENTIONS.md"]` to make the bootstrap sequence deterministic rather than read-tool-dependent.
- **Skills are shared, not ported**: opencode reads `.claude/skills/*/SKILL.md` and `.agents/skills/*/SKILL.md` natively — one skills directory serves Claude Code and opencode; just keep frontmatter to `name`+`description` (opencode ignores unknown fields like `allowed-tools`) and names regex-clean.
- **Inbox-first rule enforceable, not just documented**: `permission.edit` patterns (e.g. `{"*": "ask", "02_Inbox/**": "allow", "10_Agents/solutions/**": "allow"}`) encode the write policy; a tiny `.opencode/plugins/inbox-guard.ts` using `tool.execute.before` can hard-block writes and auto-bump `updated:` frontmatter after `tool.execute.after` edits.
- **Pre-commit hook & `brain` CLI**: git hooks run unchanged under the `bash` tool; add `"bash": {"brain *": "allow", "git *": "allow"}` permissions, and optionally wrap `brain` as a typed custom tool in `.opencode/tools/brain.ts` so the model gets schema'd access instead of raw shell.
- **Vault workflows as commands/agents**: `/daily-log`, `/weekly-review`, `/triage-inbox` become `.opencode/commands/*.md` (with `` !`date` `` injection and `@09_Templates/...` template inclusion); a read-only `librarian` subagent in `.opencode/agents/` with `edit: deny` handles retrieval-only queries.
- **Adapter must carry**: `opencode.json` (instructions, permissions, commands), `.opencode/agents|commands|plugins|tools` translations — agent/command frontmatter dialects differ from Claude Code's and there is no `.claude/commands` or `.claude/agents` compat, only CLAUDE.md + skills.

## Sources
- https://opencode.ai/docs/rules/ · https://opencode.ai/docs/config/ · https://opencode.ai/docs/skills/
- https://opencode.ai/docs/agents/ · https://opencode.ai/docs/commands/ · https://opencode.ai/docs/plugins/ · https://opencode.ai/docs/custom-tools/
- https://opencode.ai/docs/permissions/ · https://opencode.ai/docs/mcp-servers/ · https://opencode.ai/docs/themes/
- https://opencode.ai/docs/server/ · https://opencode.ai/docs/cli/ · https://opencode.ai/docs/github/
- https://github.com/sst/opencode

**Research gaps (2026-08-11):** Could not verify: (1) whether legacy singular directories (.opencode/agent/, .opencode/command/, .opencode/plugin/) still work as aliases — current docs only document the plural forms, so singular support is unverified as of 2026-08-11; (2) whether glob/grep/read respect .gitignore internally (docs only document watcher.ignore and permission-based .env denial); (3) latest release version number (not visible on the GitHub page fetched); (4) desktop-app-specific config surface beyond the shared opencode.json/tui.json. Claude Code compatibility was verified to cover exactly CLAUDE.md and skills — no .claude/commands or .claude/agents compat appears anywhere in the docs fetched. All paths, frontmatter fields, hook names, and permission keys quoted were taken from raw markdown of opencode.ai/docs pages (rules, config, skills, agents, commands, plugins, custom-tools, permissions, mcp-servers, themes, server, cli) fetched 2026-08-11.
