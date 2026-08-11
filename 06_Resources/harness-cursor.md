---
title: "Harness Primitives: Cursor"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: Cursor

Part of the [[06_Resources/harness-primitives-research|harness primitives research]] (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

Cursor (Anysphere) is a proprietary AI-first code editor (VS Code fork) with a terminal CLI (`agent`, installed via `curl https://cursor.com/install`), a web/mobile surface for [Cloud Agents](https://cursor.com/docs/cloud-agent) (cursor.com/agents, iOS app), and dashboard-managed [Automations](https://cursor.com/docs/automations); subscription-based, with Cloud Agents billed at API pricing for the selected model.

## Context & memory files
Cursor reads **AGENTS.md natively**: [project root and nested subdirectories](https://cursor.com/docs/context/rules) (`project/AGENTS.md`, `frontend/AGENTS.md`, …) — "instructions from nested AGENTS.md files are combined with parent directories, with more specific instructions taking precedence." The [CLI additionally reads `CLAUDE.md` at project root](https://cursor.com/docs/cli/using) "and applies them as rules alongside `.cursor/rules`" (CLAUDE.md fallback documented for CLI; not stated for the IDE). No `~/.cursor/AGENTS.md` user-level path is documented. The old auto-generated **Memories** feature was pulled from the editor around v2.1 ([forum reports, Nov 2025](https://forum.cursor.com/t/custom-modes-and-memories-gone-in-2-1/143744)); a new **Memories tool** now exists for Automations — named entries stored outside the agent filesystem, persistent across runs, deletable in the UI ([June 2026 changelog](https://cursor.com/changelog/06-18-26)).

## Rules
[Project Rules](https://cursor.com/docs/context/rules): `.cursor/rules/*.mdc` (Markdown + YAML frontmatter; plain `.md` ignored unless named `AGENTS.md`; nested subdirs OK). Frontmatter: `description`, `globs` (comma-separated patterns), `alwaysApply`. Four behaviors: `alwaysApply: true` = always included; `globs` set = auto-attached when matching files are in context; `description` only = agent decides ("Apply Intelligently"); none = manual `@rule-name`. **User Rules** are global, set in Customize → Rules, chat-only. **Team Rules** (Team/Enterprise, dashboard-managed, optional globs, can be enforced) take highest precedence: Team → Project → User. Rules can be imported from GitHub repos into `.cursor/rules/imported/<repoName>/`. Legacy `.cursorrules` is no longer documented on the current rules page; deprecated (still-read status unverified as of 2026-08-11). Rules don't apply to Tab or Inline Edit.

## Skills
First-class [Agent Skills](https://cursor.com/docs/skills) (since Cursor 2.4, [Jan 22 2026](https://cursor.com/changelog/2-4)), aligned with the agentskills.io open standard. Discovery: project `.cursor/skills/` and `.agents/skills/`; user `~/.cursor/skills/` and `~/.agents/skills/`; compatibility reads of `.claude/skills/` and `.codex/skills/`. Cursor "walks the skills root recursively and picks up any `SKILL.md`"; a `.cursor/skills/` folder anywhere in a monorepo is picked up and auto-scoped to that directory. `SKILL.md` frontmatter: `name` (must match folder), `description` (required), `paths` (glob scoping), `disable-model-invocation` (explicit-only), `metadata`. Folders may bundle `scripts/`, `references/`, `assets/`, loaded progressively. Invoked automatically by description relevance or explicitly via `/skill-name`. ~21 built-in skills; `/migrate-to-skills` converts old dynamic rules and slash commands.

## Commands
Deprecated. Standalone custom slash commands were silently removed from the docs (~Cursor 2.4); the sanctioned replacement is a skill with `disable-model-invocation: true`, which "behave[s] like a traditional slash command" ([skills doc](https://cursor.com/docs/skills)); `/migrate-to-skills` converts "both user-level and workspace-level commands." Historic `.cursor/commands/` paths are no longer documented ([forum](https://forum.cursor.com/t/what-happened-to-commands-best-practice-moving-forward/154238)).

## Subagents / custom agents
[Subagents](https://cursor.com/docs/agent/subagents) (since 2.4): Markdown + YAML frontmatter. Project: `.cursor/agents/` (plus `.claude/agents/`, `.codex/agents/` compatibility); user: `~/.cursor/agents/` (+ same compat variants); project overrides user on name conflict. Fields: `name`, `description` (drives auto-delegation), `model` (default `inherit`), `readonly`, `is_background`. Invoked explicitly (`/subagent-name`), automatically, or resumed by ID. Built-ins: Explore, Bash, Browser; cloud variants exist.

## Hooks
GA. JSON config at four levels (precedence high→low): Enterprise MDM (`/etc/cursor/hooks.json` Linux, `/Library/Application Support/Cursor/hooks.json` macOS, `C:\ProgramData\Cursor\hooks.json` Windows), Team (dashboard-synced), project `<root>/.cursor/hooks.json`, user `~/.cursor/hooks.json` ([hooks doc](https://cursor.com/docs/agent/hooks)). Rich event set: `sessionStart/End`, `preToolUse`/`postToolUse`/`postToolUseFailure`, `beforeShellExecution`/`afterShellExecution`, `beforeMCPExecution`/`afterMCPExecution`, `beforeReadFile`/`afterFileEdit`, `beforeSubmitPrompt`, `subagentStart/Stop`, `preCompact`, `stop`, `afterAgentResponse/Thought`, Tab hooks, `workspaceOpen`. Hooks are spawned processes speaking JSON over stdio; they can observe/audit, block (`permission: "deny"` / exit 2), rewrite tool input/output (`updated_input`), and inject context. Command-based and prompt-based (LLM-evaluated) variants; cloud agents run command-based hooks only, minus session/MCP/Tab/workspace events.

## Plugins
The [Cursor Marketplace](https://cursor.com/marketplace) packages "plugins" (e.g. Stripe, GitHub, Slack, Notion) that bundle MCP servers + skills + rules + automation templates, installed one-click ("Add to Cursor"; also cursor.directory). No local plugin packaging format for authoring your own bundles is documented as of 2026-08-11 — distribution of first-party config is via checked-in `.cursor/` files or GitHub rule/skill imports.

## Output styles / personas
None found as a dedicated primitive. Tone/format lives in global User Rules (chat-only). The earlier "custom modes" feature was removed around v2.1 ([forum](https://forum.cursor.com/t/custom-modes-and-memories-gone-in-2-1/143744)); current modes are fixed (Agent/Plan/Ask).

## MCP
Full client. Project `.cursor/mcp.json`, global `~/.cursor/mcp.json` (project takes precedence) ([MCP doc](https://cursor.com/docs/context/mcp)). `mcpServers` map; transports: stdio, SSE, streamable HTTP. Supports `env`, `envFile`, `headers`, OAuth (`auth` block, registered redirect URLs), and interpolation (`${env:VAR}`, `${workspaceFolder}`, `${userHome}`). Tools require approval by default, subject to run-mode automation settings. One-click installs via Marketplace/cursor.directory.

## Config & settings
IDE settings via the Cursor Settings UI (VS Code-fork settings underneath). CLI: global `~/.cursor/cli-config.json`, project `.cursor/cli.json` (project overrides global) ([CLI permissions doc](https://cursor.com/docs/cli/reference/permissions)). Other project-scoped config files: `.cursor/mcp.json`, `.cursor/hooks.json`, `.cursor/environment.json`, `.cursor/rules/`, `.cursor/skills/`, `.cursor/agents/`.

## Permissions & sandboxing
CLI/agent permissions in `cli.json`/`cli-config.json` under `permissions.allow`/`permissions.deny` (deny wins): `Shell(cmd)` incl. `Shell(npm:*)` arg matching, `Read(glob)`, `Write(glob)`, `WebFetch(domain)`, `Mcp(server:tool)` with wildcards. Sandbox toggle via `/sandbox` or `--sandbox enabled|disabled`, persisted ([CLI overview](https://cursor.com/docs/cli/overview)). MCP tool calls prompt for approval by default; hooks add org-enforceable deny/rewrite policy; Enterprise can push hooks and Team Rules non-disableable.

## Automation & scheduling
Headless CLI: `agent -p "…" --output-format text|json`, `--mode=plan|ask`, session resume — usable in CI. [Cloud Agents](https://cursor.com/docs/cloud-agent) launch from web/mobile (cursor.com/agents), editor, Slack/Linear (`@cursor`), GitHub/Bitbucket PR comments, or API; they clone the repo, work on a branch, and open merge-ready PRs; `&`-prefix hands a local CLI conversation off to cloud. Environments configured in [`.cursor/environment.json`](https://cursor.com/docs/cloud-agent/setup): `install`, `start`, `terminals[]`, `snapshot`, `build.dockerfile`/`context`; secrets via dashboard as env vars. [Automations](https://cursor.com/docs/automations): dashboard- or `/automate`-defined cloud-agent workflows on cron schedules or event triggers (GitHub/GitLab/Bitbucket, Slack messages/emoji, Linear, Sentry, PagerDuty, custom webhooks), with a persistent Memories tool.

## Vault wiring implications
- Zero-adapter entrypoint: our root `AGENTS.md` (which `CLAUDE.md` already imports) is read natively by the IDE at root + nested levels, and the CLI reads both `AGENTS.md` and `CLAUDE.md` — bootstrap order, Inbox-first rule, and tagging summary load automatically.
- Skills drop in unchanged: Cursor reads `.claude/skills/` for compatibility and prefers `.cursor/skills/`/`.agents/skills/`, so shipping our SKILL.md folders once under `.agents/skills/` (or symlinking) covers Cursor, with `paths:` globs to scope e.g. a journaling skill to `03_Journal/**`.
- The frontmatter/`updated:`-bumping pre-commit hook stays git-native and untouched; a Cursor adapter can add `.cursor/hooks.json` with `afterFileEdit` (auto-bump `updated:`) and `beforeShellExecution`/`preToolUse` guards enforcing Inbox-first writes at edit time.
- The stdlib `brain` CLI gets allowlisted in `.cursor/cli.json` (`"allow": ["Shell(brain)"]`, plus `Write(02_Inbox/**)` / `deny: Write(07_Archives/**)` style path permissions) and invoked from skill `scripts/`.
- Cursor-only adapter payload: `.cursor/rules/*.mdc` glob-scoped rules per PARA directory, `.cursor/hooks.json`, `.cursorignore` for `08_Assets/`, and optionally `.cursor/environment.json` (`install: pip install ./brain`) so Cloud Automations can run scheduled weekly-review drafts into `02_Inbox/` via cron.
- Deprecated surfaces to avoid: no `.cursorrules`, no `.cursor/commands/` — explicit-invocation workflows ship as skills with `disable-model-invocation: true`.

## Sources
- https://cursor.com/docs/context/rules — rules, .mdc frontmatter, AGENTS.md, User/Team Rules
- https://cursor.com/docs/skills — Agent Skills, SKILL.md, discovery paths
- https://cursor.com/docs/agent/subagents — subagent format and paths
- https://cursor.com/docs/agent/hooks — hook events, hooks.json levels
- https://cursor.com/docs/context/mcp — mcp.json scopes, transports, OAuth
- https://cursor.com/docs/context/ignore-files — .cursorignore / .cursorindexingignore
- https://cursor.com/docs/cli/overview and https://cursor.com/docs/cli/using — CLI, print mode, AGENTS.md/CLAUDE.md
- https://cursor.com/docs/cli/reference/permissions — allow/deny syntax, cli.json paths
- https://cursor.com/docs/cloud-agent and https://cursor.com/docs/cloud-agent/setup — cloud agents, environment.json
- https://cursor.com/docs/automations — schedules, triggers, Memories tool
- https://cursor.com/changelog/2-4 and https://cursor.com/changelog/06-18-26 — skills/subagents launch; automations updates
- https://cursor.com/marketplace — plugin bundles
- https://forum.cursor.com/t/custom-modes-and-memories-gone-in-2-1/143744 ; https://forum.cursor.com/t/what-happened-to-commands-best-practice-moving-forward/154238 — removals

**Research gaps (2026-08-11):** Whether legacy .cursorrules is still parsed today could not be confirmed from current official docs (the rules page no longer mentions it; third-party sources say deprecated-but-read). CLAUDE.md fallback is documented only for the CLI, not confirmed for the IDE. Exact historic .cursor/commands paths and the formal deprecation announcement for commands were never in current docs (forum evidence only). IDE desktop settings file paths (VS Code-fork settings.json location) were not verified from official docs, so the settings section sticks to documented CLI/config files. Cloud Agents API specifics (endpoints, webhooks) are mentioned but not detailed in the fetched docs. The claim that Automations launched March 2026 comes from a search summary, not a fetched changelog page, so the spec avoids asserting that date.
