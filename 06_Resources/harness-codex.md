---
title: "Harness Primitives: Codex"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: Codex

Part of the [harness primitives research](harness-primitives-research.md) (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

Codex is OpenAI's coding/general agent, maintained by OpenAI, spanning a terminal CLI (open-source, [Apache-2.0, Rust](https://github.com/openai/codex), `npm install -g @openai/codex` / `brew install --cask codex`), an IDE extension (VS Code + Cursor/Windsurf, with separate Xcode and JetBrains integrations), Codex cloud/web tasks, and the ChatGPT desktop app; usage is bundled with ChatGPT Plus/Pro/Business/Edu/Enterprise plans or paid via API key. As of 2026 the official docs live at [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs) (developers.openai.com/codex 308-redirects there).

## Context & memory files
Codex reads **AGENTS.md natively** — it is the primary instruction mechanism. [Discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md): global `~/.codex/AGENTS.override.md` or `~/.codex/AGENTS.md` first, then from the Git root walking down to the cwd, checking each directory for `AGENTS.override.md`, then `AGENTS.md`, then configured fallbacks. Files are concatenated root-downward; "files closer to your current directory override earlier guidance because they appear later in the combined prompt." Combined size is capped by `project_doc_max_bytes` (32 KiB default); `project_doc_fallback_filenames` in `~/.codex/config.toml` adds alternate names (e.g. `["TEAM_GUIDE.md", ".agents.md"]`). Empty files are skipped; `CODEX_HOME` relocates the profile dir. No documented `@file` import syntax inside AGENTS.md (unverified as of 2026-08-11). A separate opt-in [`features.memories`](https://learn.chatgpt.com/docs/config-file/config-reference) toggle (default off) carries learned context forward locally.

## Rules
Codex "[rules](https://learn.chatgpt.com/docs/agent-configuration/rules)" are **command-execution policy**, not prose instruction files: `.rules` files written in **Starlark** using `prefix_rule(pattern=..., decision="allow"|"prompt"|"forbidden", justification=..., match/not_match=...)`, living in `rules/` folders under each config layer — `~/.codex/rules/default.rules` (user) and `<repo>/.codex/rules/` (loaded only when the project is trusted). Most restrictive decision wins (`forbidden` > `prompt` > `allow`). Glob-scoped prose rules à la Cursor do not exist; directory-scoped instructions are done with nested AGENTS.md files.

## Skills
Codex implements the **open Agent Skills standard** ([SKILL.md folders](https://learn.chatgpt.com/docs/build-skills), per agentskills.io): a directory with `SKILL.md` (YAML frontmatter `name` + `description`), optional `scripts/`, `references/`, and Codex-specific `agents/openai.yaml` metadata. Discovery paths: repo-scope `.agents/skills` (cwd and parents up to repo root), user-scope `$HOME/.agents/skills`, admin `/etc/codex/skills`, plus bundled system skills. Invocation is explicit (`$skillname` in the CLI, skill picker) or implicit by description matching. Per-skill disable via `[[skills.config]]` (`path`, `enabled = false`) in config.toml. Whether the older `~/.codex/skills` path is still scanned is unverified as of 2026-08-11.

## Commands
[Custom prompts](https://learn.chatgpt.com/docs/custom-prompts) — Markdown files in `~/.codex/prompts/` with `description`/`argument-hint` frontmatter, invoked as `/prompts:name`, supporting `$1`–`$9`, named `$UPPERCASE` params, `$ARGUMENTS`, and `$$` literal — still work but are **explicitly deprecated**: "Custom prompts are deprecated. Use skills for reusable instructions that Codex can invoke explicitly or implicitly." They are user-local only (no repo-scoped prompt dir).

## Subagents / custom agents
[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) are standalone **TOML files** in `~/.codex/agents/` (personal) or `.codex/agents/` (project): required `name`, `description`, `developer_instructions`; optional `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`. Defaults come from `agents.default_subagent_model` / `agents.default_subagent_reasoning_effort`; multi-agent tools are gated by `features.multi_agent`; `/agent` switches threads in the CLI.

## Hooks
[Lifecycle hooks](https://learn.chatgpt.com/docs/hooks) (enabled by default; `[features] hooks = false` disables): events `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Configured in `~/.codex/hooks.json`, `<repo>/.codex/hooks.json`, or inline `[hooks]` tables in config.toml, as event → matcher → handler (`type: "command"`) groups. Hooks can block actions (`"permissionDecision": "deny"` or exit code 2), inject `additionalContext`, rewrite tool input via `updatedInput`, and log. Project-local hooks load only for **trusted** projects; enterprise `requirements.toml` can enforce or restrict hooks (`allow_managed_hooks_only`).

## Plugins
[Plugins](https://learn.chatgpt.com/docs/plugins) are the installable distribution unit ("skills remain the authoring format"): a plugin can bundle skills, connectors/MCP servers, hooks, browser extensions, and scheduled-task templates. Installed via the `/plugins` browser in the CLI from marketplaces (OpenAI-built, workspace, personal "Created by me"/"Shared with me"); workspace admins can force-install.

## Output styles / personas
Config-level [`personality = "friendly" | "pragmatic" | "none"`](https://learn.chatgpt.com/docs/personalize) plus a `/personality` in-session command; ChatGPT Settings > Personalization custom instructions apply on ChatGPT surfaces. No arbitrary output-style file format exists; deeper persona shaping is done through the global `~/.codex/AGENTS.md`.

## MCP
Full [MCP client](https://learn.chatgpt.com/docs/extend/mcp): `[mcp_servers.<id>]` tables in `~/.codex/config.toml` or trusted-project `.codex/config.toml`. Transports: **stdio** (`command`, `args`, `env`, `cwd`) and **streamable HTTP** (`url`, `bearer_token_env_var`, OAuth by default, static/env headers). CLI management: `codex mcp add`, `codex mcp list`, `codex mcp login <server>`. Per-server/per-tool approvals: `default_tools_approval_mode` (`auto` | `prompt` | `writes` | `approve`) and `tools.<tool>.approval_mode`. Whether Codex still exposes itself as an MCP server is not documented (unverified as of 2026-08-11).

## Config & settings
[Layered TOML config](https://learn.chatgpt.com/docs/config-file/config-basic), highest to lowest: CLI flags / `--config` overrides → project `.codex/config.toml` files (root-to-cwd, closest wins, **trusted projects only**; provider/auth keys are skipped) → profile (`--profile name`, `~/.codex/<name>.config.toml`) → user `~/.codex/config.toml` → system `/etc/codex/config.toml` → built-in defaults, with enterprise `requirements.toml` imposing managed constraints. [Key options](https://learn.chatgpt.com/docs/config-file/config-reference): `model`, `model_provider`, `model_reasoning_effort` (`minimal`–`xhigh`), `approval_policy`, `sandbox_mode`, `features.*` (multi_agent, network_proxy, memories, hooks), `notify` command array, `project_doc_*`.

## Permissions & sandboxing
[Sandboxing](https://learn.chatgpt.com/docs/sandboxing): `sandbox_mode` = `read-only` | `workspace-write` (default) | `danger-full-access`; `approval_policy` = `untrusted` | `on-request` | `never`; `writable_roots` extends write scope. Enforcement: macOS Seatbelt, Linux/WSL2 bubblewrap, Windows native sandbox or WSL2. `approvals_reviewer` routes approvals to `user` or an `auto_review` agent; Starlark rules files (above) provide command allow/prompt/forbid lists; ChatGPT Work adds an "Allow public internet access" toggle with managed allowlists.

## Automation & scheduling
[`codex exec`](https://learn.chatgpt.com/docs/non-interactive-mode) is headless mode: final message to stdout, progress to stderr; `--json` (JSON Lines events), `--output-schema <path>`, `-o/--output-last-message`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, stdin piping (`codex exec -`), resume (`codex exec resume --last`), `CODEX_API_KEY` for CI. The [`codex cloud`](https://learn.chatgpt.com/docs/cli) command family submits work to configured cloud environments; [cloud tasks](https://learn.chatgpt.com/docs/cloud) run in isolated environments with per-repo setup steps and open PRs, dispatchable from GitHub, Linear, or Slack, with `@codex review` on PRs. [Scheduled tasks](https://learn.chatgpt.com/docs/automations) use RFC 5545 RRULEs, running locally via the desktop app (Git-worktree isolated) or in the cloud with "connected tools, skills, and plugins." The [openai/codex-action](https://github.com/openai/codex-action) GitHub Action wraps `codex exec` with `prompt`/`prompt-file`, `output-schema`, `safety-strategy` (`drop-sudo` default | `unprivileged-user` | `read-only` | `unsafe`), `permission-profile`, and `codex-args`.

## Ignore files
None found. No native `.codexignore`: request [#2847](https://github.com/openai/codex/issues/2847) was closed without shipping, [#6530](https://github.com/openai/codex/issues/6530) closed as duplicate, and [#24993](https://github.com/openai/codex/issues/24993) (May 2026) remains open with the creator noting the feature "was not actually implemented" despite an erroneous closure. Sandbox modes and rules, not ignore files, are the supported exclusion mechanism.

## Vault wiring implications
- **Zero-cost entrypoint**: the vault's root `AGENTS.md` is read natively by CLI, IDE, and cloud. But Codex does not expand `CLAUDE.md`-style `@AGENTS.md` imports or Obsidian `[[wikilinks]]` — the bootstrap sequence must list plain relative paths, and the combined doc must stay under the 32 KiB `project_doc_max_bytes` default (or the adapter ships a raised value).
- **Skills drop in as-is**: our SKILL.md folders install to `<vault>/.agents/skills/<name>/` (repo-shared, same folders Claude Code consumes) — one authoring format, no translation; per-skill toggles via `[[skills.config]]`.
- **Pre-commit guardrails get a second enforcement point**: mirror frontmatter/Inbox-first checks as `.codex/hooks.json` `PreToolUse`/`PostToolUse` hooks (deny writes outside `02_Inbox/`, lint frontmatter on edit) — but they only load once the user **trusts** the project, so the git pre-commit hook stays the backstop.
- **`brain` CLI**: allowlist it with a Starlark `prefix_rule` in `.codex/rules/` so it runs un-prompted inside `workspace-write`; vault maintenance jobs run headless via `codex exec --json "brain triage"` in cron/CI or as RRULE scheduled tasks.
- **Adapter must carry**: `.codex/config.toml` (project MCP servers, `project_doc_max_bytes`, features), `.codex/hooks.json`, `.codex/rules/*.rules` — and must NOT rely on custom prompts (deprecated; recast any slash commands as skills). No ignore file exists, so private-note exclusion must be handled by sandbox scope or repo layout, not a `.codexignore`.

## Sources
- https://learn.chatgpt.com/docs (redirect target of developers.openai.com/codex)
- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://learn.chatgpt.com/docs/config-file/config-basic
- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/custom-prompts
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/agent-configuration/rules
- https://learn.chatgpt.com/docs/hooks
- https://learn.chatgpt.com/docs/plugins
- https://learn.chatgpt.com/docs/extend/mcp
- https://learn.chatgpt.com/docs/sandboxing
- https://learn.chatgpt.com/docs/non-interactive-mode
- https://learn.chatgpt.com/docs/automations
- https://learn.chatgpt.com/docs/customization/overview
- https://learn.chatgpt.com/docs/personalize
- https://learn.chatgpt.com/docs/ide
- https://learn.chatgpt.com/docs/cloud
- https://learn.chatgpt.com/docs/cli
- https://github.com/openai/codex
- https://github.com/openai/codex-action
- https://github.com/openai/codex/issues/2847 | /issues/6530 | /issues/24993

**Research gaps (2026-08-11):** Could not verify: (1) whether the legacy ~/.codex/skills path is still scanned after the move to ~/.agents/skills — official docs only list .agents/skills, $HOME/.agents/skills, /etc/codex/skills; (2) whether Codex still exposes an MCP-server mode of its own — current MCP docs are silent; (3) explicit confirmation that AGENTS.md is loaded in cloud tasks (the cloud page doesn't state it directly; inferred from the cross-surface customization overview and repo checkout behavior); (4) the exact `codex cloud exec --env/--attempts` flag set came from search snippets — the `codex cloud` family itself is confirmed on the official CLI page but per-flag details were not fetched from an official page; (5) `--full-auto` flag current status — the non-interactive page now documents `--sandbox` instead; (6) any AGENTS.md import/include syntax — none documented, reported as absent. All learn.chatgpt.com pages were summarized by WebFetch's extraction model, so exact wording beyond direct quotes may be paraphrased.
