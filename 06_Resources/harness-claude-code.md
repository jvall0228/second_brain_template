---
title: "Harness Primitives: Claude Code"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: Claude Code

Part of the [harness primitives research](harness-primitives-research.md) (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

Claude Code is Anthropic's agentic coding harness: a terminal CLI plus [VS Code and JetBrains extensions, a desktop app, and a web/cloud surface at claude.ai/code (with mobile apps)](https://code.claude.com/docs/en/overview), all sharing one engine so "your CLAUDE.md files, settings, and MCP servers work across all of them"; proprietary, requiring a paid Claude subscription or Anthropic Console/API billing. It has an exceptionally rich extension surface (see the [research overview](harness-primitives-research.md) for the cross-harness comparison) and is the reference implementation of the Agent Skills standard.

## Context & memory files
- **Does NOT read AGENTS.md natively.** The docs state flatly: ["Claude Code reads `CLAUDE.md`, not `AGENTS.md`"](https://code.claude.com/docs/en/memory#agents-md) and recommend a `CLAUDE.md` containing `@AGENTS.md` (or a symlink) — exactly what this vault already ships. `/init` with `CLAUDE_CODE_NEW_INIT=1` will read AGENTS.md and other tools' rules; `/import` (v2.1.213+) does a one-time copy.
- Load order (broad→specific): managed policy CLAUDE.md (`/Library/Application Support/ClaudeCode/CLAUDE.md` macOS, `/etc/claude-code/CLAUDE.md` Linux/WSL, `C:\Program Files\ClaudeCode\CLAUDE.md` Windows, or the `claudeMd` key in managed settings) → `~/.claude/CLAUDE.md` → `./CLAUDE.md` or `./.claude/CLAUDE.md` → `./CLAUDE.local.md` (gitignored personal). Files in ancestor dirs load at launch; subdirectory CLAUDE.md files load on demand when Claude reads files there. All are concatenated, not overridden.
- [`@path/to/import` syntax](https://code.claude.com/docs/en/memory#import-additional-files), relative or absolute, recursive to 4 hops; imports resolving outside the working dir trigger a one-time approval dialog. Block-level HTML comments are stripped before injection.
- Separate **auto memory** system: Claude self-writes `~/.claude/projects/<project>/memory/MEMORY.md` (+topic files); first 200 lines/25KB of the index load each session; toggle via `autoMemoryEnabled`.

## Rules
[`.claude/rules/*.md`](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/) (project, discovered recursively, symlink-friendly) and `~/.claude/rules/` (user, loads before project). Plain markdown; optional YAML frontmatter `paths:` with glob patterns (brace expansion supported) makes a rule load only when Claude works with matching files; rules without `paths` load at launch with same priority as `.claude/CLAUDE.md`. `claudeMdExcludes` setting skips unwanted memory files by glob.

## Skills
First-class; Claude Code [follows the Agent Skills open standard (agentskills.io)](https://code.claude.com/docs/en/skills) and extends it. Discovery: enterprise managed dir → `~/.claude/skills/<name>/SKILL.md` (personal) → `.claude/skills/<name>/SKILL.md` (project, plus nested/parent-dir discovery up to repo root and inside `--add-dir` dirs) → plugin `skills/` (namespaced `/plugin:skill`). Format: `SKILL.md` with YAML frontmatter — spec fields `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`, plus Claude-Code-only fields `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`, `shell`. Supporting files/scripts live beside SKILL.md (`${CLAUDE_SKILL_DIR}` substitution); `` !`cmd` `` injects live command output pre-prompt; `$ARGUMENTS`/`$0..$N` substitution; live change detection without restart. Cloud/Cowork sessions load project `.claude/skills/` from the cloned repo, but not local `~/.claude/skills/`.

## Commands
["Custom commands have been merged into skills"](https://code.claude.com/docs/en/skills): a file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy`; `.claude/commands/` files keep working and accept the same frontmatter, but skills are the recommended format. Bundled skills (`/code-review`, `/debug`, `/loop`, …) ship with the product; `disableBundledSkills` and per-skill `skillOverrides` settings control visibility.

## Subagents / custom agents
Markdown + YAML frontmatter files in [`.claude/agents/` (project, recursive, walk-up discovery) and `~/.claude/agents/` (user)](https://code.claude.com/docs/en/sub-agents), plugin `agents/`, managed-settings dir, or inline JSON via the `--agents` CLI flag. Fields: `name` and `description` required; optional `tools`, `disallowedTools`, `model`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills` (preload), `memory` (own auto-memory), `effort`, `background`, `isolation: worktree`, `color`. Built-ins: `Explore`, `Plan`, `general-purpose`. `--agent <name>` runs the whole session as that agent. Plugin subagents can't carry `hooks`/`mcpServers`/`permissionMode`.

## Hooks
Configured in `hooks` blocks of `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, managed policy, plugin `hooks/hooks.json`, or skill/agent frontmatter. [Events](https://code.claude.com/docs/en/hooks) include `SessionStart`, `Setup`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart/Stop`, `PreCompact`/`PostCompact`, `Notification`, `FileChanged`, `ConfigChange`, `InstructionsLoaded`, worktree/task/teammate events. Five hook types: `command` (JSON on stdin; exit 2 blocks), `http`, `mcp_tool`, `prompt`, `agent`. Hooks can block/allow tool calls, rewrite tool input (`updatedInput`), transform output, inject `additionalContext`, or stop the session — deterministic enforcement where CLAUDE.md is only guidance. `disableAllHooks` and workspace-trust gating apply.

## Plugins
A plugin is a directory with optional [`.claude-plugin/plugin.json` manifest](https://code.claude.com/docs/en/plugins) bundling `skills/`, `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json` (language servers), `monitors/` (background watchers), `bin/` (PATH executables), `output-styles/`, and default `settings.json`. Distribution via git-hosted marketplaces (`marketplace.json`); Anthropic runs two: `claude-plugins-official` (auto-registered) and `anthropics/claude-plugins-community`. Local dev via `--plugin-dir` / `--plugin-url`; a skill folder with a manifest auto-loads as a `<name>@skills-dir` plugin. Skills are namespaced `/plugin-name:skill-name`.

## Output styles / personas
**The feature is alive — only the `/output-style` command was deprecated (v2.1.73) and removed (v2.1.91)**; selection now lives in `/config` or the [`outputStyle` setting](https://code.claude.com/docs/en/output-styles). Markdown files with frontmatter (`name`, `description`, `keep-coding-instructions`, plugin-only `force-for-plugin`) at `~/.claude/output-styles`, `.claude/output-styles`, managed dir, or plugin `output-styles/`. Built-ins: Default, Proactive, Explanatory, Learning. Styles modify the system prompt; subagents are unaffected.

## MCP
Full client. [Three scopes](https://code.claude.com/docs/en/mcp#mcp-installation-scopes): **local** (`~/.claude.json`, this project only), **project** (`.mcp.json` at repo root, version-controlled, approval-gated via `enabledMcpjsonServers`/`disabledMcpjsonServers`), **user** (`~/.claude.json`, all projects); plus managed/enterprise config and plugin-bundled servers (`plugin:<plugin>:<server>`). Transports: `stdio`, `http` (accepts `streamable-http` alias; OAuth supported), `sse` (deprecated), `ws`. `claude mcp add --transport ... --scope ...`; `--strict-mcp-config` and managed allowlists restrict servers; `CLAUDE_PROJECT_DIR` exported to stdio servers.

## Config & settings
Precedence: managed policy (`managed-settings.json` at the OS paths above, plus `managed-settings.d/` drop-ins, plist/registry) → CLI args → `.claude/settings.local.json` (gitignored) → `.claude/settings.json` (committed) → [`~/.claude/settings.json`](https://code.claude.com/docs/en/settings). `~/.claude.json` holds user/local MCP and misc state. Settings cover model, permissions, hooks, `env` vars, `outputStyle`, `skillOverrides`, `claudeMdExcludes`, plugin/marketplace controls, sandbox; most hot-reload on change.

## Permissions & sandboxing
[Rules](https://code.claude.com/docs/en/permissions) `permissions.allow`/`ask`/`deny` with `Tool(specifier)` syntax (evaluated deny→ask→allow); `Bash(git commit *)` prefix matching; `Read`/`Edit` rules use gitignore-style patterns with `//` (absolute), `~/`, `/` (settings-root-relative), and relative anchors — a `Read` deny also blocks `Edit` on the path (v2.1.208+). Modes: `default`, `plan`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `auto` (set via `defaultMode` or `--permission-mode`). OS-level Bash sandbox (`/sandbox`; macOS Seatbelt, Linux/WSL2 packages; `sandbox.enabled`, `allowUnsandboxedCommands` settings) enforces filesystem/network isolation on all child processes. **No `.claudeignore` exists** — file-access exclusion is done with deny `Read()` rules.

## Automation & scheduling
[`claude -p`](https://code.claude.com/docs/en/headless) headless mode with `--allowedTools`, `--permission-mode`, `--output-format json|stream-json`, `--json-schema`, `--continue`/`--resume`, and `--bare` (skip all config discovery, recommended for CI); Agent SDK (Python/TypeScript); official [GitHub Actions and GitLab CI/CD](https://code.claude.com/docs/en/overview) integrations; **Routines** (cloud-scheduled runs, `/schedule`, can trigger on GitHub events), **Desktop scheduled tasks** (local machine), `/loop` (in-session recurrence); cloud sessions at claude.ai/code with `claude --cloud` / `--teleport` handoff, background agents, Remote Control, Slack, and Channels.

## Vault wiring implications
- **Entrypoint is already native**: the vault's `CLAUDE.md` containing `@AGENTS.md` is verbatim the documented pattern; no adapter transform needed. Claude-specific additions (e.g. "write to 02_Inbox/") can sit below the import.
- **Vault skills install as-is**: commit each skill to `.claude/skills/<name>/SKILL.md`; they load locally, follow the Agent Skills standard, and — critically — project skills also load in claude.ai/code cloud sessions from the cloned repo, unlike `~/.claude/skills/`. Keep frontmatter to the six spec fields if the same folders must upload to claude.ai.
- **Tagging/frontmatter conventions as path-scoped rules**: put note-format rules in `.claude/rules/` with `paths: ["0*_*/**/*.md"]`-style globs so they load only when editing vault notes, keeping the AGENTS.md bootstrap lean.
- **Pre-commit hook + `brain` CLI**: the git pre-commit hook runs unchanged (Claude commits via Bash); additionally wire a `PostToolUse` hook on `Write|Edit` in `.claude/settings.json` to run the vault linter (frontmatter/`updated:` check) at edit time, and a `PreToolUse` hook to enforce the Inbox-first rule deterministically. Pre-approve the CLI with `permissions.allow: ["Bash(brain *)"]` in committed project settings.
- **Protect canonical notes**: deny `Edit()` rules on `00_Meta/**` and `01_Profile/**` in `.claude/settings.json` give hard enforcement of the vault's change-control rules, independent of what the model decides.
- **This adapter carries almost nothing extra**: `.claude/` (settings + rules + skills) is the native format other harnesses' adapters will be generated from; the only Claude-specific shims are the one-line `CLAUDE.md` import and the settings/hooks JSON.

## Sources
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/output-styles
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/sandboxing
- https://code.claude.com/docs/en/headless
- https://code.claude.com/docs/en/overview

**Research gaps (2026-08-11):** All claims verified against live official docs at code.claude.com/docs on 2026-08-11 (memory, skills, sub-agents, hooks, plugins, output-styles, mcp, settings, permissions, sandboxing, headless, overview pages fetched directly). Minor caveats: (1) the hooks, settings, and sandboxing pages were summarized by a fetch-assist model rather than read verbatim in full, so exact phrasing of individual hook-event descriptions and some settings-key lists is second-hand, though event names and file paths were cross-corroborated across multiple pages; (2) the absence of a .claudeignore file is asserted by the settings-page summary and by no ignore-file appearing anywhere in the fetched docs — a dedicated ignore-file feature shipping under another name is unlikely but not exhaustively ruled out; (3) enterprise/managed skill and output-style directory exact paths ("managed settings directory") were referenced but not expanded per-OS in the fetched content; (4) Routines/desktop-scheduled-tasks details come from mentions in the overview and skills pages, not from fetching those dedicated pages; (5) whether the CLI source is open-source vs source-available was not stated in fetched docs, so the overview says only "proprietary, requires subscription or API billing."
