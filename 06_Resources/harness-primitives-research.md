---
title: "Harness Primitives Research"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
---

# Harness Primitives Research

Grounded research (2026-08-11) on the extension surface of every harness in the [[00_Meta/prd]] §8.3 support table, plus the universal standards layer they build on. Produced for M6/M7 planning (see [[07_Archives/inbox/2026-08-11-m5-m7-implementation-plan|M5–M7 Implementation Plan]]) by nine parallel research agents working from official documentation; load-bearing claims link their sources. Harness surfaces move fast — treat this as accurate as of the date above and re-verify before each adapter ships (per §8.3, wiring specifics are settled at build time). Unverifiable details are marked as gaps, not guessed.

## Headline Findings

- Exactly two primitives have true cross-harness standards — and they are the two this vault bet on. **AGENTS.md** is native in 6 of 7 harnesses (Claude Code is the only one needing the `CLAUDE.md` adapter — §8.3's table is confirmed row by row). **Agent Skills / SKILL.md** is supported by all 7.
- `.agents/skills/` is the shared skills discovery path (6 of 7 scan it; user scope `~/.agents/skills/`). Claude Code scans only `.claude/skills/` — so onboarding links the shared path once, plus one Claude Code–specific link.
- Custom slash-command files are converging **into** skills — already deprecated in Codex and Cursor. Ship skills, never command files.
- Rules, subagents, hooks, plugins, settings, and permissions are proprietary per harness. Git pre-commit remains the only portable hook layer, which validates the M5 enforcement design.
- Output styles are effectively Claude Code–only (the `/output-style` command was removed but the primitive lives on via settings). Portable voice/tone belongs in [[01_Profile/preferences]], loaded through the entrypoint.
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
| hooks | settings.json hooks | hooks.json | ~JS plugin hooks | TS extension events | hooks.json | ~.github/hooks (Preview) | .muse/hooks.json |
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
- Drop any plan use of output styles outside Claude Code — 5/7 harnesses have none. Voice/tone belongs in `01_Profile/preferences` referenced from AGENTS.md; a `.claude/output-styles/` file is an optional Claude-only nicety.
- Privacy exclusions cannot be a single ignore file. Only Cursor honors one; Codex has none at all (feature requests closed unimplemented). If the vault plans to fence off directories (e.g. private journal), each adapter needs its own deny mechanism (Claude/opencode/Cursor/Copilot permission denies), and Codex/Pi/Muse have **no reliable exclusion at all** — surface this gap to the owner as a policy decision, not a config task.
- Keep one canonical MCP server manifest in `10_Agents/` and generate per-harness configs from it; accept that Pi gets no MCP (skills there must degrade to plain scripts) and Muse can't receive project-scoped servers.
- Hook-driven vault automation (e.g. auto-bumping `updated:`, Inbox-first enforcement) cannot ride the standards track — hook formats are 100% proprietary and two harnesses need code, not config. Implement once as a git pre-commit hook (portable), with per-harness hooks as optional enhancements.
- Treat the Muse Code adapter as draft/volatile: the product is 6 days old, its SKILL.md frontmatter spec is unpublished, and its ignore/instruction-path story is undocumented. Re-verify before hardening that adapter.

## Full Specs

P0 rows first (standards track, then harnesses), P1 second wave after. Each section ends with its sources and the research gaps the agent could not verify.

### Universal standards + protocols (P0)
This row is not a harness but the portability substrate every harness adapter builds on. Three live standards matter as of 2026-08: **AGENTS.md** (project instruction entrypoint, contributed by OpenAI), **Agent Skills / SKILL.md** (packaged workflows, originated at Anthropic), and **MCP** (tool/context protocol, originated at Anthropic). All three are open and free; MCP and AGENTS.md are founding projects of the [Agentic AI Foundation (AAIF) under the Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) (formed Dec 2025; platinum members include AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI), while Agent Skills is developed openly at [github.com/agentskills/agentskills](https://github.com/agentskills/agentskills).

#### AGENTS.md — the entrypoint/context standard
- ["A README for agents"](https://agents.md/): plain Markdown, **no required fields** — "AGENTS.md is just standard Markdown… any headings you like". 60,000+ open-source projects use it; now "stewarded by the Agentic AI Foundation under the Linux Foundation".
- Nesting/precedence: nested AGENTS.md files in monorepo subdirs are explicitly supported; "The closest AGENTS.md to the edited file wins; explicit user chat prompts override everything." Agents "automatically read the nearest file in the directory tree."
- Adoption (per [agents.md](https://agents.md/)): 25+ tools including OpenAI Codex, Google Jules, Aider, Cursor, GitHub Copilot, VS Code, Devin, JetBrains Junie, Warp; Gemini CLI supports it via `.gemini/settings.json` config.
- Notable holdout: **Claude Code does not read AGENTS.md natively** — its docs state ["Claude Code reads `CLAUDE.md`, not `AGENTS.md`"](https://code.claude.com/docs/en/memory) and recommend a `CLAUDE.md` containing `@AGENTS.md` (import, loaded at session start) or a symlink. This vault already ships exactly that shim.

#### Agent Skills (SKILL.md) — the workflow-packaging standard
- A skill is a folder with a `SKILL.md` (YAML frontmatter + Markdown body). [Spec fields](https://agentskills.io/specification): `name` (required, 1–64 chars, lowercase alphanumerics + hyphens, no leading/trailing/consecutive hyphens, **must match directory name**), `description` (required, 1–1024 chars), optional `license`, `compatibility` (≤500 chars), `metadata` (string→string map), `allowed-tools` (space-separated pre-approved tools, **experimental**).
- Optional bundled dirs by convention: `scripts/` (executable code), `references/` (on-demand docs), `assets/` (templates/data). References use relative paths, kept one level deep.
- [Progressive disclosure](https://agentskills.io/): (1) metadata ~100 tokens loaded at startup for all skills, (2) full `SKILL.md` body on activation (<5k tokens recommended, keep under 500 lines), (3) bundled resources only as needed. Validate with `skills-ref validate` from the reference library.
- Discovery paths are **not standardized by the spec** — each harness defines its own. An `.agents/skills/` convention is emerging: [Cursor scans](https://cursor.com/docs/context/skills) `.agents/skills/` and `.cursor/skills/` (project), `~/.agents/skills/` and `~/.cursor/skills/` (user), plus legacy `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, `~/.codex/skills/`. Codex CLI uses `$CODEX_HOME/skills` (default `~/.codex/skills`) per community docs — official page returned 503, unverified as of 2026-08-11.
- Adoption: "originally developed by Anthropic, released as an open standard"; the [client showcase](https://agentskills.io/) lists 45+ adopters including Claude Code, Claude (claude.ai), ChatGPT & Codex, GitHub Copilot, VS Code, Cursor, Gemini CLI, JetBrains Junie, Goose, OpenCode, Amp, Roo Code, Factory, Kiro, Trae, Tabnine, Snowflake Cortex Code, Databricks Genie Code.

#### MCP (Model Context Protocol) — the tool/context protocol
- [Open-source standard](https://modelcontextprotocol.io/) for connecting AI apps to external systems; joined the AAIF in Dec 2025. Date-based versioning; **current revision is `2026-07-28`** per the [versioning page](https://modelcontextprotocol.io/specification/versioning). The 2026-07-28 revision is stateless: every request carries `io.modelcontextprotocol/protocolVersion` in `_meta`, with a mandatory `server/discover` RPC replacing the old initialize handshake (compat path documented for `2025-11-25` and earlier).
- Primitives ([architecture](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)): server-side **tools**, **resources**, **prompts** (+ opt-in change notifications via `subscriptions/listen`); client-side **elicitation**. **Deprecated as of `2026-07-28`** per the [deprecated-features registry](https://modelcontextprotocol.io/specification/2026-07-28/deprecated): **roots**, **sampling**, **logging** (earliest removal on/after 2027-07-28), plus Dynamic Client Registration; the HTTP+SSE transport has been deprecated since `2025-03-26`.
- Transports: **stdio** (local) and **Streamable HTTP** (remote; OAuth recommended). Optional extensions build on core: Tasks (durable handles for long-running requests) and MCP Apps.
- Client adoption (per MCP homepage): Claude, ChatGPT, VS Code, Cursor, "and many others". **Config file locations/scopes are not standardized** — each harness defines its own MCP registration files.

#### Other live cross-harness conventions
- **ACP (Agent Client Protocol)** — [agentclientprotocol.com](https://agentclientprotocol.com/): standardizes editor↔agent communication (LSP analog), created and maintained by Zed, Apache-licensed; editor adopters include Zed, JetBrains IDEs, Neovim and Emacs plugins, with Gemini CLI first among agents per [Zed's blog](https://zed.dev/blog/bring-your-own-agent-to-zed) and [progress report](https://zed.dev/blog/acp-progress-report). Harness-plumbing relevance only; no vault file format depends on it.
- **`.agents/` directory** — emerging neutral home for agent assets (skills today, per Cursor's docs above); not yet a written standard beyond skills discovery.
- **No cross-harness standard exists** for: glob-scoped rule files, command files, subagent definitions, lifecycle hooks, plugins/marketplaces, output styles, settings files, permission configuration, scheduling, or agent ignore files. These all remain per-harness. Git's own hooks (pre-commit) are the de facto portable enforcement layer since every harness commits through git.

#### Vault wiring implications
- **Entrypoint is solved by AGENTS.md alone**: the vault-root `AGENTS.md` bootstrap doc is read natively by essentially every harness except Claude Code, which the existing one-line `CLAUDE.md` → `@AGENTS.md` shim covers using Anthropic's own documented bridge. Nested `AGENTS.md` files (e.g. in `02_Inbox/`, `10_Agents/`) are the only portable way to ship directory-scoped rules ("closest wins").
- **Canonical skills live at `.agents/skills/<name>/SKILL.md`**: spec-strict (dir name == `name`, ≤64/≤1024 limits, body <500 lines, `references/`+`scripts/` layout) makes them load anywhere; Cursor reads that path natively, other harness adapters only need a symlink/copy into `.claude/skills/`, `~/.codex/skills/`, etc.
- **The pre-commit hook is the only hook that travels**: no agent-hook standard exists, so all hard enforcement (frontmatter lint, tag taxonomy, `updated:` bump) belongs in the git pre-commit hook, with `skills-ref validate` added for skill folders; harness-native hooks are per-adapter conveniences only.
- **The `brain` CLI ports via MCP stdio**: exposing it as an MCP server (tools + a resource for `00_Meta/index`) makes it reachable from GUI/web harnesses that can't shell out — but registration config is per-harness, so each adapter carries its own MCP stanza. Target spec `2026-07-28` semantics and do not build on roots/sampling/logging (all deprecated).
- **What the standards track alone carries**: entrypoint + prose rules (AGENTS.md), workflows (Agent Skills), tool/context access (MCP). Commands, subagents, output styles, permissions, scheduling, and ignore rules must be regenerated per harness by the adapter layer.

#### Sources
- https://agents.md/
- https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation
- https://code.claude.com/docs/en/memory
- https://agentskills.io/
- https://agentskills.io/specification
- https://cursor.com/docs/context/skills
- https://modelcontextprotocol.io/
- https://modelcontextprotocol.io/specification/versioning
- https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture
- https://modelcontextprotocol.io/specification/2026-07-28/deprecated
- https://agentclientprotocol.com/
- https://zed.dev/blog/bring-your-own-agent-to-zed
- https://zed.dev/blog/acp-progress-report
- https://github.com/composiohq/awesome-codex-skills (Codex skill paths; official docs 503)

**Research gaps (2026-08-11):** OpenAI's official Codex skills page (developers.openai.com/codex/skills) returned HTTP 503 on two attempts, so Codex's exact skill discovery paths ($CODEX_HOME/skills, default ~/.codex/skills) rest on Cursor's compatibility list and community docs, not first-party docs. The agents.md adoption list was summarized ("25+ tools") rather than enumerated in full. The Agent Skills spec has no published versioning/governance document beyond the GitHub repo, so spec-version pinning is not possible. ACP's maintainer (Zed) and adopter list came from Zed blog posts surfaced via search, not a direct fetch of the protocol site (whose landing page names no adopters). MCP client adoption was verified only for the clients named on modelcontextprotocol.io (Claude, ChatGPT, VS Code, Cursor); per-harness MCP support for the other harnesses in the support table was not re-verified here. Whether .gitignore is honored as an agent-ignore convention across harnesses was not verified.

### Claude Code (P0)
Claude Code is Anthropic's agentic coding harness: a terminal CLI plus [VS Code and JetBrains extensions, a desktop app, and a web/cloud surface at claude.ai/code (with mobile apps)](https://code.claude.com/docs/en/overview), all sharing one engine so "your CLAUDE.md files, settings, and MCP servers work across all of them"; proprietary, requiring a paid Claude subscription or Anthropic Console/API billing. It has the richest extension surface of any harness covered here and is the reference implementation of the Agent Skills standard.

#### Context & memory files
- **Does NOT read AGENTS.md natively.** The docs state flatly: ["Claude Code reads `CLAUDE.md`, not `AGENTS.md`"](https://code.claude.com/docs/en/memory#agents-md) and recommend a `CLAUDE.md` containing `@AGENTS.md` (or a symlink) — exactly what this vault already ships. `/init` with `CLAUDE_CODE_NEW_INIT=1` will read AGENTS.md and other tools' rules; `/import` (v2.1.213+) does a one-time copy.
- Load order (broad→specific): managed policy CLAUDE.md (`/Library/Application Support/ClaudeCode/CLAUDE.md` macOS, `/etc/claude-code/CLAUDE.md` Linux/WSL, `C:\Program Files\ClaudeCode\CLAUDE.md` Windows, or the `claudeMd` key in managed settings) → `~/.claude/CLAUDE.md` → `./CLAUDE.md` or `./.claude/CLAUDE.md` → `./CLAUDE.local.md` (gitignored personal). Files in ancestor dirs load at launch; subdirectory CLAUDE.md files load on demand when Claude reads files there. All are concatenated, not overridden.
- [`@path/to/import` syntax](https://code.claude.com/docs/en/memory#import-additional-files), relative or absolute, recursive to 4 hops; imports resolving outside the working dir trigger a one-time approval dialog. Block-level HTML comments are stripped before injection.
- Separate **auto memory** system: Claude self-writes `~/.claude/projects/<project>/memory/MEMORY.md` (+topic files); first 200 lines/25KB of the index load each session; toggle via `autoMemoryEnabled`.

#### Rules
[`.claude/rules/*.md`](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/) (project, discovered recursively, symlink-friendly) and `~/.claude/rules/` (user, loads before project). Plain markdown; optional YAML frontmatter `paths:` with glob patterns (brace expansion supported) makes a rule load only when Claude works with matching files; rules without `paths` load at launch with same priority as `.claude/CLAUDE.md`. `claudeMdExcludes` setting skips unwanted memory files by glob.

#### Skills
First-class; Claude Code [follows the Agent Skills open standard (agentskills.io)](https://code.claude.com/docs/en/skills) and extends it. Discovery: enterprise managed dir → `~/.claude/skills/<name>/SKILL.md` (personal) → `.claude/skills/<name>/SKILL.md` (project, plus nested/parent-dir discovery up to repo root and inside `--add-dir` dirs) → plugin `skills/` (namespaced `/plugin:skill`). Format: `SKILL.md` with YAML frontmatter — spec fields `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`, plus Claude-Code-only fields `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`, `shell`. Supporting files/scripts live beside SKILL.md (`${CLAUDE_SKILL_DIR}` substitution); `` !`cmd` `` injects live command output pre-prompt; `$ARGUMENTS`/`$0..$N` substitution; live change detection without restart. Cloud/Cowork sessions load project `.claude/skills/` from the cloned repo, but not local `~/.claude/skills/`.

#### Commands
["Custom commands have been merged into skills"](https://code.claude.com/docs/en/skills): a file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy`; `.claude/commands/` files keep working and accept the same frontmatter, but skills are the recommended format. Bundled skills (`/code-review`, `/debug`, `/loop`, …) ship with the product; `disableBundledSkills` and per-skill `skillOverrides` settings control visibility.

#### Subagents / custom agents
Markdown + YAML frontmatter files in [`.claude/agents/` (project, recursive, walk-up discovery) and `~/.claude/agents/` (user)](https://code.claude.com/docs/en/sub-agents), plugin `agents/`, managed-settings dir, or inline JSON via the `--agents` CLI flag. Fields: `name` and `description` required; optional `tools`, `disallowedTools`, `model`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills` (preload), `memory` (own auto-memory), `effort`, `background`, `isolation: worktree`, `color`. Built-ins: `Explore`, `Plan`, `general-purpose`. `--agent <name>` runs the whole session as that agent. Plugin subagents can't carry `hooks`/`mcpServers`/`permissionMode`.

#### Hooks
Configured in `hooks` blocks of `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, managed policy, plugin `hooks/hooks.json`, or skill/agent frontmatter. [Events](https://code.claude.com/docs/en/hooks) include `SessionStart`, `Setup`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart/Stop`, `PreCompact`/`PostCompact`, `Notification`, `FileChanged`, `ConfigChange`, `InstructionsLoaded`, worktree/task/teammate events. Five hook types: `command` (JSON on stdin; exit 2 blocks), `http`, `mcp_tool`, `prompt`, `agent`. Hooks can block/allow tool calls, rewrite tool input (`updatedInput`), transform output, inject `additionalContext`, or stop the session — deterministic enforcement where CLAUDE.md is only guidance. `disableAllHooks` and workspace-trust gating apply.

#### Plugins
A plugin is a directory with optional [`.claude-plugin/plugin.json` manifest](https://code.claude.com/docs/en/plugins) bundling `skills/`, `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json` (language servers), `monitors/` (background watchers), `bin/` (PATH executables), `output-styles/`, and default `settings.json`. Distribution via git-hosted marketplaces (`marketplace.json`); Anthropic runs two: `claude-plugins-official` (auto-registered) and `anthropics/claude-plugins-community`. Local dev via `--plugin-dir` / `--plugin-url`; a skill folder with a manifest auto-loads as a `<name>@skills-dir` plugin. Skills are namespaced `/plugin-name:skill-name`.

#### Output styles / personas
**The feature is alive — only the `/output-style` command was deprecated (v2.1.73) and removed (v2.1.91)**; selection now lives in `/config` or the [`outputStyle` setting](https://code.claude.com/docs/en/output-styles). Markdown files with frontmatter (`name`, `description`, `keep-coding-instructions`, plugin-only `force-for-plugin`) at `~/.claude/output-styles`, `.claude/output-styles`, managed dir, or plugin `output-styles/`. Built-ins: Default, Proactive, Explanatory, Learning. Styles modify the system prompt; subagents are unaffected.

#### MCP
Full client. [Three scopes](https://code.claude.com/docs/en/mcp#mcp-installation-scopes): **local** (`~/.claude.json`, this project only), **project** (`.mcp.json` at repo root, version-controlled, approval-gated via `enabledMcpjsonServers`/`disabledMcpjsonServers`), **user** (`~/.claude.json`, all projects); plus managed/enterprise config and plugin-bundled servers (`plugin:<plugin>:<server>`). Transports: `stdio`, `http` (accepts `streamable-http` alias; OAuth supported), `sse` (deprecated), `ws`. `claude mcp add --transport ... --scope ...`; `--strict-mcp-config` and managed allowlists restrict servers; `CLAUDE_PROJECT_DIR` exported to stdio servers.

#### Config & settings
Precedence: managed policy (`managed-settings.json` at the OS paths above, plus `managed-settings.d/` drop-ins, plist/registry) → CLI args → `.claude/settings.local.json` (gitignored) → `.claude/settings.json` (committed) → [`~/.claude/settings.json`](https://code.claude.com/docs/en/settings). `~/.claude.json` holds user/local MCP and misc state. Settings cover model, permissions, hooks, `env` vars, `outputStyle`, `skillOverrides`, `claudeMdExcludes`, plugin/marketplace controls, sandbox; most hot-reload on change.

#### Permissions & sandboxing
[Rules](https://code.claude.com/docs/en/permissions) `permissions.allow`/`ask`/`deny` with `Tool(specifier)` syntax (evaluated deny→ask→allow); `Bash(git commit *)` prefix matching; `Read`/`Edit` rules use gitignore-style patterns with `//` (absolute), `~/`, `/` (settings-root-relative), and relative anchors — a `Read` deny also blocks `Edit` on the path (v2.1.208+). Modes: `default`, `plan`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `auto` (set via `defaultMode` or `--permission-mode`). OS-level Bash sandbox (`/sandbox`; macOS Seatbelt, Linux/WSL2 packages; `sandbox.enabled`, `allowUnsandboxedCommands` settings) enforces filesystem/network isolation on all child processes. **No `.claudeignore` exists** — file-access exclusion is done with deny `Read()` rules.

#### Automation & scheduling
[`claude -p`](https://code.claude.com/docs/en/headless) headless mode with `--allowedTools`, `--permission-mode`, `--output-format json|stream-json`, `--json-schema`, `--continue`/`--resume`, and `--bare` (skip all config discovery, recommended for CI); Agent SDK (Python/TypeScript); official [GitHub Actions and GitLab CI/CD](https://code.claude.com/docs/en/overview) integrations; **Routines** (cloud-scheduled runs, `/schedule`, can trigger on GitHub events), **Desktop scheduled tasks** (local machine), `/loop` (in-session recurrence); cloud sessions at claude.ai/code with `claude --cloud` / `--teleport` handoff, background agents, Remote Control, Slack, and Channels.

#### Vault wiring implications
- **Entrypoint is already native**: the vault's `CLAUDE.md` containing `@AGENTS.md` is verbatim the documented pattern; no adapter transform needed. Claude-specific additions (e.g. "write to 02_Inbox/") can sit below the import.
- **Vault skills install as-is**: commit each skill to `.claude/skills/<name>/SKILL.md`; they load locally, follow the Agent Skills standard, and — critically — project skills also load in claude.ai/code cloud sessions from the cloned repo, unlike `~/.claude/skills/`. Keep frontmatter to the six spec fields if the same folders must upload to claude.ai.
- **Tagging/frontmatter conventions as path-scoped rules**: put note-format rules in `.claude/rules/` with `paths: ["0*_*/**/*.md"]`-style globs so they load only when editing vault notes, keeping the AGENTS.md bootstrap lean.
- **Pre-commit hook + `brain` CLI**: the git pre-commit hook runs unchanged (Claude commits via Bash); additionally wire a `PostToolUse` hook on `Write|Edit` in `.claude/settings.json` to run the vault linter (frontmatter/`updated:` check) at edit time, and a `PreToolUse` hook to enforce the Inbox-first rule deterministically. Pre-approve the CLI with `permissions.allow: ["Bash(brain *)"]` in committed project settings.
- **Protect canonical notes**: deny `Edit()` rules on `00_Meta/**` and `01_Profile/**` in `.claude/settings.json` give hard enforcement of the vault's change-control rules, independent of what the model decides.
- **This adapter carries almost nothing extra**: `.claude/` (settings + rules + skills) is the native format other harnesses' adapters will be generated from; the only Claude-specific shims are the one-line `CLAUDE.md` import and the settings/hooks JSON.

#### Sources
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

### Codex (P0)
Codex is OpenAI's coding/general agent, maintained by OpenAI, spanning a terminal CLI (open-source, [Apache-2.0, Rust](https://github.com/openai/codex), `npm install -g @openai/codex` / `brew install --cask codex`), an IDE extension (VS Code + Cursor/Windsurf, with separate Xcode and JetBrains integrations), Codex cloud/web tasks, and the ChatGPT desktop app; usage is bundled with ChatGPT Plus/Pro/Business/Edu/Enterprise plans or paid via API key. As of 2026 the official docs live at [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs) (developers.openai.com/codex 308-redirects there).

#### Context & memory files
Codex reads **AGENTS.md natively** — it is the primary instruction mechanism. [Discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md): global `~/.codex/AGENTS.override.md` or `~/.codex/AGENTS.md` first, then from the Git root walking down to the cwd, checking each directory for `AGENTS.override.md`, then `AGENTS.md`, then configured fallbacks. Files are concatenated root-downward; "files closer to your current directory override earlier guidance because they appear later in the combined prompt." Combined size is capped by `project_doc_max_bytes` (32 KiB default); `project_doc_fallback_filenames` in `~/.codex/config.toml` adds alternate names (e.g. `["TEAM_GUIDE.md", ".agents.md"]`). Empty files are skipped; `CODEX_HOME` relocates the profile dir. No documented `@file` import syntax inside AGENTS.md (unverified as of 2026-08-11). A separate opt-in [`features.memories`](https://learn.chatgpt.com/docs/config-file/config-reference) toggle (default off) carries learned context forward locally.

#### Rules
Codex "[rules](https://learn.chatgpt.com/docs/agent-configuration/rules)" are **command-execution policy**, not prose instruction files: `.rules` files written in **Starlark** using `prefix_rule(pattern=..., decision="allow"|"prompt"|"forbidden", justification=..., match/not_match=...)`, living in `rules/` folders under each config layer — `~/.codex/rules/default.rules` (user) and `<repo>/.codex/rules/` (loaded only when the project is trusted). Most restrictive decision wins (`forbidden` > `prompt` > `allow`). Glob-scoped prose rules à la Cursor do not exist; directory-scoped instructions are done with nested AGENTS.md files.

#### Skills
Codex implements the **open Agent Skills standard** ([SKILL.md folders](https://learn.chatgpt.com/docs/build-skills), per agentskills.io): a directory with `SKILL.md` (YAML frontmatter `name` + `description`), optional `scripts/`, `references/`, and Codex-specific `agents/openai.yaml` metadata. Discovery paths: repo-scope `.agents/skills` (cwd and parents up to repo root), user-scope `$HOME/.agents/skills`, admin `/etc/codex/skills`, plus bundled system skills. Invocation is explicit (`$skillname` in the CLI, skill picker) or implicit by description matching. Per-skill disable via `[[skills.config]]` (`path`, `enabled = false`) in config.toml. Whether the older `~/.codex/skills` path is still scanned is unverified as of 2026-08-11.

#### Commands
[Custom prompts](https://learn.chatgpt.com/docs/custom-prompts) — Markdown files in `~/.codex/prompts/` with `description`/`argument-hint` frontmatter, invoked as `/prompts:name`, supporting `$1`–`$9`, named `$UPPERCASE` params, `$ARGUMENTS`, and `$$` literal — still work but are **explicitly deprecated**: "Custom prompts are deprecated. Use skills for reusable instructions that Codex can invoke explicitly or implicitly." They are user-local only (no repo-scoped prompt dir).

#### Subagents / custom agents
[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) are standalone **TOML files** in `~/.codex/agents/` (personal) or `.codex/agents/` (project): required `name`, `description`, `developer_instructions`; optional `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`. Defaults come from `agents.default_subagent_model` / `agents.default_subagent_reasoning_effort`; multi-agent tools are gated by `features.multi_agent`; `/agent` switches threads in the CLI.

#### Hooks
[Lifecycle hooks](https://learn.chatgpt.com/docs/hooks) (enabled by default; `[features] hooks = false` disables): events `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Configured in `~/.codex/hooks.json`, `<repo>/.codex/hooks.json`, or inline `[hooks]` tables in config.toml, as event → matcher → handler (`type: "command"`) groups. Hooks can block actions (`"permissionDecision": "deny"` or exit code 2), inject `additionalContext`, rewrite tool input via `updatedInput`, and log. Project-local hooks load only for **trusted** projects; enterprise `requirements.toml` can enforce or restrict hooks (`allow_managed_hooks_only`).

#### Plugins
[Plugins](https://learn.chatgpt.com/docs/plugins) are the installable distribution unit ("skills remain the authoring format"): a plugin can bundle skills, connectors/MCP servers, hooks, browser extensions, and scheduled-task templates. Installed via the `/plugins` browser in the CLI from marketplaces (OpenAI-built, workspace, personal "Created by me"/"Shared with me"); workspace admins can force-install.

#### Output styles / personas
Config-level [`personality = "friendly" | "pragmatic" | "none"`](https://learn.chatgpt.com/docs/personalize) plus a `/personality` in-session command; ChatGPT Settings > Personalization custom instructions apply on ChatGPT surfaces. No arbitrary output-style file format exists; deeper persona shaping is done through the global `~/.codex/AGENTS.md`.

#### MCP
Full [MCP client](https://learn.chatgpt.com/docs/extend/mcp): `[mcp_servers.<id>]` tables in `~/.codex/config.toml` or trusted-project `.codex/config.toml`. Transports: **stdio** (`command`, `args`, `env`, `cwd`) and **streamable HTTP** (`url`, `bearer_token_env_var`, OAuth by default, static/env headers). CLI management: `codex mcp add`, `codex mcp list`, `codex mcp login <server>`. Per-server/per-tool approvals: `default_tools_approval_mode` (`auto` | `prompt` | `writes` | `approve`) and `tools.<tool>.approval_mode`. Whether Codex still exposes itself as an MCP server is not documented (unverified as of 2026-08-11).

#### Config & settings
[Layered TOML config](https://learn.chatgpt.com/docs/config-file/config-basic), highest to lowest: CLI flags / `--config` overrides → project `.codex/config.toml` files (root-to-cwd, closest wins, **trusted projects only**; provider/auth keys are skipped) → profile (`--profile name`, `~/.codex/<name>.config.toml`) → user `~/.codex/config.toml` → system `/etc/codex/config.toml` → built-in defaults, with enterprise `requirements.toml` imposing managed constraints. [Key options](https://learn.chatgpt.com/docs/config-file/config-reference): `model`, `model_provider`, `model_reasoning_effort` (`minimal`–`xhigh`), `approval_policy`, `sandbox_mode`, `features.*` (multi_agent, network_proxy, memories, hooks), `notify` command array, `project_doc_*`.

#### Permissions & sandboxing
[Sandboxing](https://learn.chatgpt.com/docs/sandboxing): `sandbox_mode` = `read-only` | `workspace-write` (default) | `danger-full-access`; `approval_policy` = `untrusted` | `on-request` | `never`; `writable_roots` extends write scope. Enforcement: macOS Seatbelt, Linux/WSL2 bubblewrap, Windows native sandbox or WSL2. `approvals_reviewer` routes approvals to `user` or an `auto_review` agent; Starlark rules files (above) provide command allow/prompt/forbid lists; ChatGPT Work adds an "Allow public internet access" toggle with managed allowlists.

#### Automation & scheduling
[`codex exec`](https://learn.chatgpt.com/docs/non-interactive-mode) is headless mode: final message to stdout, progress to stderr; `--json` (JSON Lines events), `--output-schema <path>`, `-o/--output-last-message`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, stdin piping (`codex exec -`), resume (`codex exec resume --last`), `CODEX_API_KEY` for CI. The [`codex cloud`](https://learn.chatgpt.com/docs/cli) command family submits work to configured cloud environments; [cloud tasks](https://learn.chatgpt.com/docs/cloud) run in isolated environments with per-repo setup steps and open PRs, dispatchable from GitHub, Linear, or Slack, with `@codex review` on PRs. [Scheduled tasks](https://learn.chatgpt.com/docs/automations) use RFC 5545 RRULEs, running locally via the desktop app (Git-worktree isolated) or in the cloud with "connected tools, skills, and plugins." The [openai/codex-action](https://github.com/openai/codex-action) GitHub Action wraps `codex exec` with `prompt`/`prompt-file`, `output-schema`, `safety-strategy` (`drop-sudo` default | `unprivileged-user` | `read-only` | `unsafe`), `permission-profile`, and `codex-args`.

#### Ignore files
None found. No native `.codexignore`: request [#2847](https://github.com/openai/codex/issues/2847) was closed without shipping, [#6530](https://github.com/openai/codex/issues/6530) closed as duplicate, and [#24993](https://github.com/openai/codex/issues/24993) (May 2026) remains open with the creator noting the feature "was not actually implemented" despite an erroneous closure. Sandbox modes and rules, not ignore files, are the supported exclusion mechanism.

#### Vault wiring implications
- **Zero-cost entrypoint**: the vault's root `AGENTS.md` is read natively by CLI, IDE, and cloud. But Codex does not expand `CLAUDE.md`-style `@AGENTS.md` imports or Obsidian `[[wikilinks]]` — the bootstrap sequence must list plain relative paths, and the combined doc must stay under the 32 KiB `project_doc_max_bytes` default (or the adapter ships a raised value).
- **Skills drop in as-is**: our SKILL.md folders install to `<vault>/.agents/skills/<name>/` (repo-shared, same folders Claude Code consumes) — one authoring format, no translation; per-skill toggles via `[[skills.config]]`.
- **Pre-commit guardrails get a second enforcement point**: mirror frontmatter/Inbox-first checks as `.codex/hooks.json` `PreToolUse`/`PostToolUse` hooks (deny writes outside `02_Inbox/`, lint frontmatter on edit) — but they only load once the user **trusts** the project, so the git pre-commit hook stays the backstop.
- **`brain` CLI**: allowlist it with a Starlark `prefix_rule` in `.codex/rules/` so it runs un-prompted inside `workspace-write`; vault maintenance jobs run headless via `codex exec --json "brain triage"` in cron/CI or as RRULE scheduled tasks.
- **Adapter must carry**: `.codex/config.toml` (project MCP servers, `project_doc_max_bytes`, features), `.codex/hooks.json`, `.codex/rules/*.rules` — and must NOT rely on custom prompts (deprecated; recast any slash commands as skills). No ignore file exists, so private-note exclusion must be handled by sandbox scope or repo layout, not a `.codexignore`.

#### Sources
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

### opencode (P0)
[opencode](https://github.com/sst/opencode) is "the open source coding agent" — MIT-licensed (~196k stars), built by the SST team and maintained under Anomaly Co. (repo `sst/opencode`, org now `anomalyco`). Surfaces: terminal TUI, CLI (`opencode run`), headless HTTP server (`opencode serve`), web UI (`opencode web`), desktop app (macOS/Windows/Linux), IDE/VS Code extension, and ACP support (stdio nd-JSON) for editors like Zed. The tool itself is free; you bring provider API keys (any provider via Models.dev) or use its paid Zen model gateway.

#### Context & memory files
opencode reads **`AGENTS.md` natively** — confirmed: "You can provide custom instructions to opencode by creating an `AGENTS.md` file" ([rules doc](https://opencode.ai/docs/rules/)). Load order: (1) local files found by traversing up from cwd (`AGENTS.md`, with `CLAUDE.md` as Claude Code-compat fallback — "if you have both AGENTS.md and CLAUDE.md, only AGENTS.md is used"); (2) global `~/.config/opencode/AGENTS.md`; (3) fallback `~/.claude/CLAUDE.md`. Claude compat is disabled via `OPENCODE_DISABLE_CLAUDE_CODE=1` (or `_PROMPT`/`_SKILLS` variants). Additional files load via the `instructions` array in `opencode.json` — supports relative paths, globs (`.cursor/rules/*.md`, `packages/*/AGENTS.md`), and remote URLs (5s fetch timeout); all are combined with `AGENTS.md`. Important: opencode "doesn't automatically parse file references in AGENTS.md" — no `@file` auto-import; the docs recommend `instructions` globs or explicit lazy-read instructions instead.

#### Rules
No separate rule-file format (no `.mdc`, no per-rule frontmatter or glob-triggered activation). "Rules" = `AGENTS.md` files plus the `instructions` config array ([rules doc](https://opencode.ai/docs/rules/)); everything listed is always loaded into context. Globs select *which files* load, not *when* they activate. On-demand/triggered loading is instead served by Skills (below).

#### Skills
First-class [Agent Skills support](https://opencode.ai/docs/skills/), loaded on demand via a native `skill` tool. Discovery paths (project paths found by walking up to the git worktree root): `.opencode/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`, plus global `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/`. Frontmatter: `name` (required, `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 chars, must match dir name), `description` (required, 1–1024 chars), optional `license`, `compatibility`, `metadata` (string map); unknown fields ignored (so Claude's `allowed-tools` is tolerated but inert). Skills are gated by pattern-based `permission.skill` rules (`allow`/`ask`/`deny`, per-agent overridable) and the tool can be disabled per agent via `tools: { skill: false }`.

#### Commands
Custom slash commands are markdown files — filename becomes `/name` — in `.opencode/commands/` (project) or `~/.config/opencode/commands/` (global), or inline under the `command` key in config ([commands doc](https://opencode.ai/docs/commands/)). Frontmatter: `description`, `agent`, `model`, `subtask` (force subagent invocation). Templates support `$ARGUMENTS` and positional `$1..$n`, `` !`cmd` `` shell-output injection, and `@file` file inclusion. Custom commands can override built-ins (`/init`, `/undo`, ...). No `.claude/commands/` compat path is documented. Runnable headless via `opencode run --command <name>`.

#### Subagents / custom agents
Two kinds: **primary agents** (built-ins: `build`, `plan`) switched with Tab, and **subagents** (built-ins: `general`, `explore`, `scout`) invoked by `@mention` or the `task` tool ([agents doc](https://opencode.ai/docs/agents/)). Define as markdown in `.opencode/agents/` (project) or `~/.config/opencode/agents/` (global) — filename = agent name; body = system prompt. Frontmatter: `description` (required), `mode` (`primary`/`subagent`/`all`), `model`, `temperature`, `top_p`, `steps` (replaces deprecated `maxSteps`), `permission`, `tools`, `prompt` (supports `{file:./prompts/x.txt}`), `disable`, `color`. Same options available under the `agent` key in `opencode.json`. `subagent_depth` controls nesting. No `.claude/agents/` compat documented.

#### Hooks
No declarative shell-hook config (nothing like Claude Code's `hooks` in settings). Lifecycle interception is done in **JS/TS plugins**: `tool.execute.before` / `tool.execute.after` (can mutate args or throw to block), `chat`/`message.*`, `session.*` (incl. `session.idle`, `session.compacted`), `permission.asked`/`permission.replied`, `file.edited`, `file.watcher.updated`, `command.executed`, `shell.env` (inject env into all shell executions), `tui.*`, and `experimental.session.compacting` (inject or replace the compaction prompt) ([plugins doc](https://opencode.ai/docs/plugins/)).

#### Plugins
Plugins are JS/TS modules exporting async functions that receive `{ project, client, $, directory, worktree }` (Bun shell + SDK client) and return a hooks object. Load from `.opencode/plugins/` (project), `~/.config/opencode/plugins/` (global), or npm packages listed in the `plugin` config array (installed via Bun at startup, cached in `~/.cache/opencode/node_modules/`). Load order: global config → project config → global dir → project dir. Local plugin deps go in a `.opencode/package.json`. Plugins can also register **custom tools** (`tool` helper from `@opencode-ai/plugin`, Zod-schema args) that take precedence over same-named built-ins; standalone custom tools also live in `.opencode/tools/` / `~/.config/opencode/tools/` (filename = tool name) ([custom tools doc](https://opencode.ai/docs/custom-tools/)). Community registry is the docs [ecosystem page](https://opencode.ai/docs/ecosystem/); no marketplace/bundle format — a "plugin" is one npm package or file.

#### Output styles / personas
No dedicated output-style/response-persona feature. Nearest equivalents: agent definitions with custom `prompt` (personas), and [TUI themes](https://opencode.ai/docs/themes/) — JSON color themes from `~/.config/opencode/themes/*.json` and `.opencode/themes/*.json` — which are visual only. No deprecated output-style feature exists to note.

#### MCP
Full MCP client. Configured under the `mcp` key in `opencode.json` ([MCP doc](https://opencode.ai/docs/mcp-servers/)): `"type": "local"` (`command` array, `environment`, `cwd`, `timeout` default 5000ms) or `"type": "remote"` (`url`, `headers`, `oauth`, `timeout`); per-server `enabled` toggle. Remote servers get automatic OAuth (401 detection + Dynamic Client Registration RFC 7591, tokens stored). Orgs can ship default MCP servers via a `.well-known/opencode` remote config that local config overrides. Scopes follow config precedence (global vs project file).

#### Config & settings
`opencode.json` / `opencode.jsonc` (schema `https://opencode.ai/config.json`) plus `tui.json` (`https://opencode.ai/tui.json`) for theme/keybinds ([config doc](https://opencode.ai/docs/config/)). Precedence (low→high): remote `.well-known/opencode` → global `~/.config/opencode/opencode.json` → `OPENCODE_CONFIG` → project-root `opencode.json` → `.opencode` dirs → `OPENCODE_CONFIG_CONTENT` → managed config (`/etc/opencode/`, macOS `/Library/Application Support/opencode/`, `%ProgramData%\opencode`) → macOS MDM `.mobileconfig`; configs deep-merge. Key keys: `model`, `small_model`, `provider`, `agent`, `default_agent`, `instructions`, `command`, `permission`, `mcp`, `plugin`, `formatter`, `lsp`, `share`, `snapshot`, `watcher.ignore`, `compaction`, `server.*`. Variable substitution: `{env:VAR}` and `{file:path}`.

#### Permissions & sandboxing
Pattern-based `permission` map with `allow`/`ask`/`deny` per tool: `read`, `edit` (covers write/patch), `glob`, `grep`, `bash` (patterns match parsed commands, e.g. `"git *": "allow"`), `task` (subagent type), `skill`, `webfetch`, `websearch`, `question`, `lsp`, plus guards `external_directory` (paths outside the workspace; default `ask`) and `doom_loop` (identical call repeated 3×; default `ask`). Last matching rule wins; `~`/`$HOME` expansion supported. Defaults are permissive (`read` allows but `*.env` denied by default). Per-agent permission overrides merge over global. `--auto` flag / TUI toggle auto-approves anything not explicitly denied. As of v1.1.1 the legacy boolean `tools` config is deprecated into `permission` ([permissions doc](https://opencode.ai/docs/permissions/)). No OS-level sandbox (container/seccomp) is documented — enforcement is at the permission layer.

#### Automation & scheduling
Headless one-shot: `opencode run "prompt"` with `--agent`, `--command`, `--session`/`--continue`/`--fork`, `--format json` (raw JSON events), `--auto`, and `--attach <url>` to reuse a warm server ([CLI doc](https://opencode.ai/docs/cli/)). Long-running: `opencode serve` (OpenAPI 3.1 HTTP server, SSE events, basic-auth via `OPENCODE_SERVER_PASSWORD`; JS SDK generated from it) and `opencode web`; `opencode attach` connects a TUI to a remote server. CI: [GitHub agent](https://opencode.ai/docs/github/) installed via `opencode github install` → `.github/workflows/opencode.yml`, triggered by `/oc` or `/opencode` comments on issues/PRs. Session export/import as JSON. No built-in cron/scheduler — pair `opencode run` with external schedulers.

#### Vault wiring implications
- **Zero-cost entrypoint**: our root `AGENTS.md` loads natively (and `CLAUDE.md` is unnecessary here since `AGENTS.md` wins). But opencode does **not** follow `[[wikilinks]]` or `@file` references, so the opencode adapter should ship an `opencode.json` with `"instructions": ["01_Profile/now.md", "01_Profile/preferences.md", "00_Meta/conventions.md"]` to make the bootstrap sequence deterministic rather than read-tool-dependent.
- **Skills are shared, not ported**: opencode reads `.claude/skills/*/SKILL.md` and `.agents/skills/*/SKILL.md` natively — one skills directory serves Claude Code and opencode; just keep frontmatter to `name`+`description` (opencode ignores unknown fields like `allowed-tools`) and names regex-clean.
- **Inbox-first rule enforceable, not just documented**: `permission.edit` patterns (e.g. `{"*": "ask", "02_Inbox/**": "allow", "10_Agents/solutions/**": "allow"}`) encode the write policy; a tiny `.opencode/plugins/inbox-guard.ts` using `tool.execute.before` can hard-block writes and auto-bump `updated:` frontmatter after `tool.execute.after` edits.
- **Pre-commit hook & `brain` CLI**: git hooks run unchanged under the `bash` tool; add `"bash": {"brain *": "allow", "git *": "allow"}` permissions, and optionally wrap `brain` as a typed custom tool in `.opencode/tools/brain.ts` so the model gets schema'd access instead of raw shell.
- **Vault workflows as commands/agents**: `/daily-log`, `/weekly-review`, `/triage-inbox` become `.opencode/commands/*.md` (with `` !`date` `` injection and `@09_Templates/...` template inclusion); a read-only `librarian` subagent in `.opencode/agents/` with `edit: deny` handles retrieval-only queries.
- **Adapter must carry**: `opencode.json` (instructions, permissions, commands), `.opencode/agents|commands|plugins|tools` translations — agent/command frontmatter dialects differ from Claude Code's and there is no `.claude/commands` or `.claude/agents` compat, only CLAUDE.md + skills.

#### Sources
- https://opencode.ai/docs/rules/ · https://opencode.ai/docs/config/ · https://opencode.ai/docs/skills/
- https://opencode.ai/docs/agents/ · https://opencode.ai/docs/commands/ · https://opencode.ai/docs/plugins/ · https://opencode.ai/docs/custom-tools/
- https://opencode.ai/docs/permissions/ · https://opencode.ai/docs/mcp-servers/ · https://opencode.ai/docs/themes/
- https://opencode.ai/docs/server/ · https://opencode.ai/docs/cli/ · https://opencode.ai/docs/github/
- https://github.com/sst/opencode

**Research gaps (2026-08-11):** Could not verify: (1) whether legacy singular directories (.opencode/agent/, .opencode/command/, .opencode/plugin/) still work as aliases — current docs only document the plural forms, so singular support is unverified as of 2026-08-11; (2) whether glob/grep/read respect .gitignore internally (docs only document watcher.ignore and permission-based .env denial); (3) latest release version number (not visible on the GitHub page fetched); (4) desktop-app-specific config surface beyond the shared opencode.json/tui.json. Claude Code compatibility was verified to cover exactly CLAUDE.md and skills — no .claude/commands or .claude/agents compat appears anywhere in the docs fetched. All paths, frontmatter fields, hook names, and permission keys quoted were taken from raw markdown of opencode.ai/docs pages (rules, config, skills, agents, commands, plugins, custom-tools, permissions, mcp-servers, themes, server, cli) fetched 2026-08-11.

### Pi (P0)
Pi is a deliberately minimal, "aggressively extensible" open-source terminal coding agent by Mario Zechner (badlogic, of libGDX fame), now maintained under [Earendil Inc.](https://pi.dev) with contributors (npm maintainers include Armin Ronacher); it lives in the [pi-mono monorepo](https://github.com/badlogic/pi-mono) (canonical org now `earendil-works`), ships as the CLI/TUI `@earendil-works/pi-coding-agent` (v0.84.1, 2026-08-07) plus an SDK and RPC mode — MIT-licensed and free, bring-your-own API keys. Its philosophy: four default tools, a tiny system prompt, and everything else (sub-agents, plan mode, permissions, MCP) pushed out to user-installable extensions.

#### Context & memory files
Pi reads **AGENTS.md natively** — and accepts `CLAUDE.md` as an equivalent project context file. Load order per the [README](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md): `~/.pi/agent/AGENTS.md` (global), then `AGENTS.md`/`CLAUDE.md` in each parent directory walking down to cwd, concatenated. An `AGENTS.override.md` in a directory replaces that directory's context file (others still load). System prompt itself is replaceable via `.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md`, or extended via `APPEND_SYSTEM.md` in the same locations. Disable with `pi --no-context-files` / `-nc`. No `@import` mechanism found in docs (unverified as of 2026-08-11).

#### Rules
No dedicated rule-file system (no glob-scoped, auto-attached rules). Always-on instructions are exactly the context-file chain above plus `APPEND_SYSTEM.md`; conditional behavior is instead delegated to skills (model-invoked) or extensions (programmatic). "None found" beyond that.

#### Skills
First-class, following the [Agent Skills standard](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md) (agentskills.io): folders with `SKILL.md`, YAML frontmatter `name` (required, ≤64 chars, lowercase/hyphens) and `description` (required, ≤1024 chars; skills missing it are not loaded), optional `license`, `compatibility`, `metadata`, `allowed-tools`, `disable-model-invocation`. Progressive disclosure: names+descriptions go in the system prompt; full body loads on demand. Discovery: `~/.pi/agent/skills/`, `~/.agents/skills/`, and (after project trust) `.pi/skills/` and **`.agents/skills/`** searched from cwd upward; also Pi packages, settings arrays, and `--skill <path>`. Invoke manually with `/skill:name`; disable discovery with `--no-skills`. First-discovered wins on name collisions.

#### Commands
"Prompt templates": markdown files whose filename becomes a slash command (`review.md` → `/review`), per [prompt-templates.md](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/prompt-templates.md). Optional YAML frontmatter `description` and `argument-hint`; bash-style args `$1`, `$@`/`$ARGUMENTS`, `${1:-default}`, `${@:N:L}`. Locations: `~/.pi/agent/prompts/*.md`, `.pi/prompts/*.md` (trust-gated), package `prompts/` dirs, settings, `--prompt-template <path>`; non-recursive discovery. Extensions can also register programmatic `/commands` via `pi.registerCommand()`.

#### Subagents / custom agents
Deliberately **not built-in** — the README lists "No sub-agents" as a design choice: spawn pi in tmux, or build them with the extension API (example extensions demonstrate sub-agent/plan-mode patterns; `ctx.newSession()`, `ctx.fork()`, `ctx.switchSession()` exist in command context). No agent-definition file format exists.

#### Hooks
No shell-command hook config; the equivalent is the [TypeScript extension event system](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md): `pi.on(event, handler)` with events including `session_start`, `session_shutdown`, `before_agent_start` (inject messages / modify system prompt), `input`, `tool_call` (can **block** via `{ block: true, reason }` or mutate args), `tool_result` (patch output), `turn_start/end`, `message_start/update/end`, `model_select`, `project_trust`. Handlers get UI primitives (`ctx.ui.confirm()` etc.) and session access.

#### Plugins
Two layers. (1) **Extensions**: TypeScript modules loaded via jiti (no compile step), default-export factory receiving `ExtensionAPI` — register tools (`pi.registerTool` with TypeBox schema + custom TUI renderers), commands, providers, event handlers. Locations: `~/.pi/agent/extensions/*.ts` (+`*/index.ts`), `.pi/extensions/` (trust-gated), settings, `-e ./ext.ts`. (2) **Pi packages**: npm or git repos installed with `pi install npm:@foo/pi-tools` / `pi install git:github.com/user/repo[@tag]` (user-scope under `~/.pi/agent/{npm,git}/`, or project-local with `-l` into `.pi/`), bundling extensions, skills, prompts, and themes via a `package.json` `"pi"` manifest (keyword `pi-package`); managed with `pi list/update/remove/config`. No central marketplace; npm/git are the registry.

#### Output styles / personas
No output-styles feature (nothing deprecated — never existed). Closest analog: full system-prompt replacement (`SYSTEM.md`) or append (`APPEND_SYSTEM.md`), plus TUI **themes** (JSON, hot-reloading, built-in `dark`/`light`, in `~/.pi/agent/themes/`, `.pi/themes/`, packages, `--theme <path>`), which style the UI, not the model's voice.

#### MCP
**Intentionally not built in.** The README's stated stance: "Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support." MCP clients can be added as a third-party Pi package/extension; no config file, scopes, or transports exist in core.

#### Config & settings
`~/.pi/agent/settings.json` (global) and `.pi/settings.json` (project; trust-gated), deep-merged with project winning, per [settings.md](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md). Keys cover model defaults (`defaultProvider`, `defaultModel`, `defaultThinkingLevel`), `theme`, `compaction.*`, `retry.*`, resource arrays (`packages`, `extensions`, `skills`, `prompts`, `themes`, `enableSkillCommands`), `defaultProjectTrust` (global-only), telemetry toggles. Env vars: `PI_CODING_AGENT_DIR` (relocate config), `PI_CODING_AGENT_SESSION_DIR`, `PI_OFFLINE`, `PI_TELEMETRY`, plus session metadata exported to bash tools (`PI_SESSION_ID`, `PI_MODEL`, ...). Custom providers/models via `models.json` ([docs](https://pi.dev)).

#### Permissions & sandboxing
No permission popups or allowlists by design — "Pi does not include a built-in permission system"; the docs direct users to containerize (three documented patterns: Gondolin extension, plain Docker, OpenShell, in `packages/coding-agent/docs/containerization.md`) or build extension-based permission gates (examples provided). What does exist is **project trust**: interactive pi prompts before loading `.pi/` resources or `.agents/skills/`; decisions saved via `/trust` to `~/.pi/agent/trust.json`; overridable per-run with `--approve`/`--no-approve`; headless modes fall back to `defaultProjectTrust` (`ask`→ignore / `never` / `always`). Tools can be pruned with `--exclude-tools`.

#### Automation & scheduling
Strong headless story, no built-in scheduler. `pi -p "prompt"` one-shot (reads piped stdin), `--mode json` (JSONL event stream), `--mode rpc` (strict LF-delimited JSONL over stdio for non-Node hosts, [rpc.md](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/rpc.md)), and an [SDK](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/sdk.md) (`createAgentSession()`, `AgentSession.prompt()/steer()/subscribe()`, `runPrintMode()`, `runRpcMode()`, in-memory sessions) for CI/pipelines. Sessions are branchable JSONL trees (`-c`, `-r`, `--fork`, `/tree`, `/compact`) exportable to HTML via `--export`. Scheduling is external (cron/CI).

#### Vault wiring implications
- **Zero-adapter entrypoint**: pi natively reads our root `AGENTS.md` (and would fall back to `CLAUDE.md`), walking parents → cwd, so the bootstrap sequence works unmodified; a user-global `~/.pi/agent/AGENTS.md` could add owner-level defaults without touching the vault.
- **Skills land in the shared path**: pi discovers `.agents/skills/` natively (trust-gated), so the vault's SKILL.md folders need no copying — the same tree serves pi, Claude Code, and other agentskills.io consumers. `10_Agents/` docs can point at `/skill:name` invocation.
- **The stdlib `brain` CLI is pi's preferred integration**: pi's explicit anti-MCP stance ("CLI tools with READMEs") means our CLI + a thin SKILL.md wrapper is the *native* pattern here, not a fallback.
- **Pre-commit hook is unaffected** (git runs it), but in-session frontmatter/Inbox-first enforcement needs a small TypeScript extension in `.pi/extensions/` hooking `tool_call` on write/edit to block or warn — this extension is the main pi-only artifact the adapter must carry.
- **Adapter also ships**: `.pi/prompts/*.md` mirroring our slash commands (bash-style `$1`/`$@` args differ from other harnesses), optional `.pi/settings.json`, and a note that users must `/trust` the vault once (or set `defaultProjectTrust`) before any `.pi/` or `.agents/skills/` resources load — headless runs silently ignore them otherwise.
- **Optional**: publish the whole toolkit as a Pi package (`pi install git:...`) bundling extension + skills + prompts + a vault theme in one manifest.

#### Sources
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

### Cursor (P1)
Cursor (Anysphere) is a proprietary AI-first code editor (VS Code fork) with a terminal CLI (`agent`, installed via `curl https://cursor.com/install`), a web/mobile surface for [Cloud Agents](https://cursor.com/docs/cloud-agent) (cursor.com/agents, iOS app), and dashboard-managed [Automations](https://cursor.com/docs/automations); subscription-based, with Cloud Agents billed at API pricing for the selected model.

#### Context & memory files
Cursor reads **AGENTS.md natively**: [project root and nested subdirectories](https://cursor.com/docs/context/rules) (`project/AGENTS.md`, `frontend/AGENTS.md`, …) — "instructions from nested AGENTS.md files are combined with parent directories, with more specific instructions taking precedence." The [CLI additionally reads `CLAUDE.md` at project root](https://cursor.com/docs/cli/using) "and applies them as rules alongside `.cursor/rules`" (CLAUDE.md fallback documented for CLI; not stated for the IDE). No `~/.cursor/AGENTS.md` user-level path is documented. The old auto-generated **Memories** feature was pulled from the editor around v2.1 ([forum reports, Nov 2025](https://forum.cursor.com/t/custom-modes-and-memories-gone-in-2-1/143744)); a new **Memories tool** now exists for Automations — named entries stored outside the agent filesystem, persistent across runs, deletable in the UI ([June 2026 changelog](https://cursor.com/changelog/06-18-26)).

#### Rules
[Project Rules](https://cursor.com/docs/context/rules): `.cursor/rules/*.mdc` (Markdown + YAML frontmatter; plain `.md` ignored unless named `AGENTS.md`; nested subdirs OK). Frontmatter: `description`, `globs` (comma-separated patterns), `alwaysApply`. Four behaviors: `alwaysApply: true` = always included; `globs` set = auto-attached when matching files are in context; `description` only = agent decides ("Apply Intelligently"); none = manual `@rule-name`. **User Rules** are global, set in Customize → Rules, chat-only. **Team Rules** (Team/Enterprise, dashboard-managed, optional globs, can be enforced) take highest precedence: Team → Project → User. Rules can be imported from GitHub repos into `.cursor/rules/imported/<repoName>/`. Legacy `.cursorrules` is no longer documented on the current rules page; deprecated (still-read status unverified as of 2026-08-11). Rules don't apply to Tab or Inline Edit.

#### Skills
First-class [Agent Skills](https://cursor.com/docs/skills) (since Cursor 2.4, [Jan 22 2026](https://cursor.com/changelog/2-4)), aligned with the agentskills.io open standard. Discovery: project `.cursor/skills/` and `.agents/skills/`; user `~/.cursor/skills/` and `~/.agents/skills/`; compatibility reads of `.claude/skills/` and `.codex/skills/`. Cursor "walks the skills root recursively and picks up any `SKILL.md`"; a `.cursor/skills/` folder anywhere in a monorepo is picked up and auto-scoped to that directory. `SKILL.md` frontmatter: `name` (must match folder), `description` (required), `paths` (glob scoping), `disable-model-invocation` (explicit-only), `metadata`. Folders may bundle `scripts/`, `references/`, `assets/`, loaded progressively. Invoked automatically by description relevance or explicitly via `/skill-name`. ~21 built-in skills; `/migrate-to-skills` converts old dynamic rules and slash commands.

#### Commands
Deprecated. Standalone custom slash commands were silently removed from the docs (~Cursor 2.4); the sanctioned replacement is a skill with `disable-model-invocation: true`, which "behave[s] like a traditional slash command" ([skills doc](https://cursor.com/docs/skills)); `/migrate-to-skills` converts "both user-level and workspace-level commands." Historic `.cursor/commands/` paths are no longer documented ([forum](https://forum.cursor.com/t/what-happened-to-commands-best-practice-moving-forward/154238)).

#### Subagents / custom agents
[Subagents](https://cursor.com/docs/agent/subagents) (since 2.4): Markdown + YAML frontmatter. Project: `.cursor/agents/` (plus `.claude/agents/`, `.codex/agents/` compatibility); user: `~/.cursor/agents/` (+ same compat variants); project overrides user on name conflict. Fields: `name`, `description` (drives auto-delegation), `model` (default `inherit`), `readonly`, `is_background`. Invoked explicitly (`/subagent-name`), automatically, or resumed by ID. Built-ins: Explore, Bash, Browser; cloud variants exist.

#### Hooks
GA. JSON config at four levels (precedence high→low): Enterprise MDM (`/etc/cursor/hooks.json` Linux, `/Library/Application Support/Cursor/hooks.json` macOS, `C:\ProgramData\Cursor\hooks.json` Windows), Team (dashboard-synced), project `<root>/.cursor/hooks.json`, user `~/.cursor/hooks.json` ([hooks doc](https://cursor.com/docs/agent/hooks)). Rich event set: `sessionStart/End`, `preToolUse`/`postToolUse`/`postToolUseFailure`, `beforeShellExecution`/`afterShellExecution`, `beforeMCPExecution`/`afterMCPExecution`, `beforeReadFile`/`afterFileEdit`, `beforeSubmitPrompt`, `subagentStart/Stop`, `preCompact`, `stop`, `afterAgentResponse/Thought`, Tab hooks, `workspaceOpen`. Hooks are spawned processes speaking JSON over stdio; they can observe/audit, block (`permission: "deny"` / exit 2), rewrite tool input/output (`updated_input`), and inject context. Command-based and prompt-based (LLM-evaluated) variants; cloud agents run command-based hooks only, minus session/MCP/Tab/workspace events.

#### Plugins
The [Cursor Marketplace](https://cursor.com/marketplace) packages "plugins" (e.g. Stripe, GitHub, Slack, Notion) that bundle MCP servers + skills + rules + automation templates, installed one-click ("Add to Cursor"; also cursor.directory). No local plugin packaging format for authoring your own bundles is documented as of 2026-08-11 — distribution of first-party config is via checked-in `.cursor/` files or GitHub rule/skill imports.

#### Output styles / personas
None found as a dedicated primitive. Tone/format lives in global User Rules (chat-only). The earlier "custom modes" feature was removed around v2.1 ([forum](https://forum.cursor.com/t/custom-modes-and-memories-gone-in-2-1/143744)); current modes are fixed (Agent/Plan/Ask).

#### MCP
Full client. Project `.cursor/mcp.json`, global `~/.cursor/mcp.json` (project takes precedence) ([MCP doc](https://cursor.com/docs/context/mcp)). `mcpServers` map; transports: stdio, SSE, streamable HTTP. Supports `env`, `envFile`, `headers`, OAuth (`auth` block, registered redirect URLs), and interpolation (`${env:VAR}`, `${workspaceFolder}`, `${userHome}`). Tools require approval by default, subject to run-mode automation settings. One-click installs via Marketplace/cursor.directory.

#### Config & settings
IDE settings via the Cursor Settings UI (VS Code-fork settings underneath). CLI: global `~/.cursor/cli-config.json`, project `.cursor/cli.json` (project overrides global) ([CLI permissions doc](https://cursor.com/docs/cli/reference/permissions)). Other project-scoped config files: `.cursor/mcp.json`, `.cursor/hooks.json`, `.cursor/environment.json`, `.cursor/rules/`, `.cursor/skills/`, `.cursor/agents/`.

#### Permissions & sandboxing
CLI/agent permissions in `cli.json`/`cli-config.json` under `permissions.allow`/`permissions.deny` (deny wins): `Shell(cmd)` incl. `Shell(npm:*)` arg matching, `Read(glob)`, `Write(glob)`, `WebFetch(domain)`, `Mcp(server:tool)` with wildcards. Sandbox toggle via `/sandbox` or `--sandbox enabled|disabled`, persisted ([CLI overview](https://cursor.com/docs/cli/overview)). MCP tool calls prompt for approval by default; hooks add org-enforceable deny/rewrite policy; Enterprise can push hooks and Team Rules non-disableable.

#### Automation & scheduling
Headless CLI: `agent -p "…" --output-format text|json`, `--mode=plan|ask`, session resume — usable in CI. [Cloud Agents](https://cursor.com/docs/cloud-agent) launch from web/mobile (cursor.com/agents), editor, Slack/Linear (`@cursor`), GitHub/Bitbucket PR comments, or API; they clone the repo, work on a branch, and open merge-ready PRs; `&`-prefix hands a local CLI conversation off to cloud. Environments configured in [`.cursor/environment.json`](https://cursor.com/docs/cloud-agent/setup): `install`, `start`, `terminals[]`, `snapshot`, `build.dockerfile`/`context`; secrets via dashboard as env vars. [Automations](https://cursor.com/docs/automations): dashboard- or `/automate`-defined cloud-agent workflows on cron schedules or event triggers (GitHub/GitLab/Bitbucket, Slack messages/emoji, Linear, Sentry, PagerDuty, custom webhooks), with a persistent Memories tool.

#### Vault wiring implications
- Zero-adapter entrypoint: our root `AGENTS.md` (which `CLAUDE.md` already imports) is read natively by the IDE at root + nested levels, and the CLI reads both `AGENTS.md` and `CLAUDE.md` — bootstrap order, Inbox-first rule, and tagging summary load automatically.
- Skills drop in unchanged: Cursor reads `.claude/skills/` for compatibility and prefers `.cursor/skills/`/`.agents/skills/`, so shipping our SKILL.md folders once under `.agents/skills/` (or symlinking) covers Cursor, with `paths:` globs to scope e.g. a journaling skill to `03_Journal/**`.
- The frontmatter/`updated:`-bumping pre-commit hook stays git-native and untouched; a Cursor adapter can add `.cursor/hooks.json` with `afterFileEdit` (auto-bump `updated:`) and `beforeShellExecution`/`preToolUse` guards enforcing Inbox-first writes at edit time.
- The stdlib `brain` CLI gets allowlisted in `.cursor/cli.json` (`"allow": ["Shell(brain)"]`, plus `Write(02_Inbox/**)` / `deny: Write(07_Archives/**)` style path permissions) and invoked from skill `scripts/`.
- Cursor-only adapter payload: `.cursor/rules/*.mdc` glob-scoped rules per PARA directory, `.cursor/hooks.json`, `.cursorignore` for `08_Assets/`, and optionally `.cursor/environment.json` (`install: pip install ./brain`) so Cloud Automations can run scheduled weekly-review drafts into `02_Inbox/` via cron.
- Deprecated surfaces to avoid: no `.cursorrules`, no `.cursor/commands/` — explicit-invocation workflows ship as skills with `disable-model-invocation: true`.

#### Sources
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

### GitHub Copilot (P1)

> **Superseded 2026-08-11** by [[06_Resources/copilot-harness-deep-dive]] — several claims below were corrected there (hooks run on the CLI and cloud agent, not just VS Code; symlinked skills fail in the CLI; the CLI has a real `@`-include mechanism; the surface is now branded "Copilot cloud agent").
GitHub Copilot is GitHub/Microsoft's AI pair-programmer family: **Copilot Chat in VS Code** (agent mode in the editor), the **Copilot cloud agent** (the async agent formerly branded "coding agent," running in ephemeral [GitHub Actions environments](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent)), and the **[Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview)** terminal agent — plus code review, JetBrains/Visual Studio/Xcode/Eclipse IDE plugins, and github.com web chat; proprietary, subscription-based (Free/Pro/Pro+/Business/Enterprise).

#### Context & memory files
- **AGENTS.md is read natively** across the agent surfaces: GitHub's [repository custom instructions doc](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions) lists `AGENTS.md` (nearest file in the directory tree wins), with a single root `CLAUDE.md` or `GEMINI.md` accepted as alternatives. The [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview) auto-includes `AGENTS.md`, `.github/copilot-instructions.md`, and `.github/instructions/**/*.instructions.md`. In [VS Code](https://code.visualstudio.com/docs/copilot/customization/custom-instructions), root `AGENTS.md` is on via `chat.useAgentsMdFile`, nested per-subfolder AGENTS.md via experimental `chat.useNestedAgentsMdFiles`; `CLAUDE.md`/`CLAUDE.local.md` (root, `.claude/`, or `~/.claude/CLAUDE.md`) via `chat.useClaudeMdFile`.
- `.github/copilot-instructions.md` = classic always-on repo-wide file; the only kind honored by JetBrains/Xcode/Eclipse per the [support matrix](https://docs.github.com/en/copilot/concepts/prompting/response-customization); Visual Studio adds path-specific but not agent files.
- Personal instructions (github.com web) and organization instructions also exist; priority is personal → repository → organization. Files can reference other files via ordinary Markdown links; there is **no `@import` mechanism** like Claude Code's.

#### Rules
[Path-specific instruction files](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions): `.github/instructions/**/NAME.instructions.md` (subdirectories searched recursively) with YAML frontmatter — `applyTo:` glob (triggered when matching files are in context; `**` = always), optional `name`, `description`, and `excludeAgent` (`code-review` or `cloud-agent`). User-level rules live in `~/.copilot/instructions/` (VS Code also reads `~/.claude/rules/`); extra folders via `chat.instructionsFilesLocations`.

#### Skills
First-class **Agent Skills** following the open agentskills.io standard ([GitHub docs](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [VS Code docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills)): `SKILL.md` with `name` (lowercase-hyphen, ≤64 chars) + `description` (≤1024 chars) frontmatter, progressive disclosure. Project paths: `.github/skills/`, `.claude/skills/`, or `.agents/skills/`; personal: `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` (more via `chat.agentSkillsLocations`). Supported by cloud agent, code review, Copilot CLI, the Copilot app, and agent mode in VS Code and JetBrains. The CLI honors an [`allowed-tools` frontmatter field](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) for pre-approving tools per skill.

#### Commands
[Prompt files](https://code.visualstudio.com/docs/copilot/customization/prompt-files): `*.prompt.md` in `.github/prompts/` (workspace) or the VS Code user profile; frontmatter `name`, `description`, `argument-hint`, `agent`, `model`, `tools`; invoked as `/promptname` in chat; `${input:var}` variables. Not supported in github.com web chat per the [matrix](https://docs.github.com/en/copilot/concepts/prompting/response-customization). Copilot CLI has built-in slash commands (`/agent`, `/mcp add`, `/settings`, `/add-dir`); plugins can also contribute slash commands.

#### Subagents / custom agents
[Custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents): `*.agent.md` files in `.github/agents/` or `.claude/agents/` (repo), `~/.copilot/agents/` (user), or `/agents` in an org's `.github-private` repo (org/enterprise level, per the [custom agents reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration)). Frontmatter: `description` (required), `name`, `tools`, `model`, `target` (`vscode`|`github-copilot`), `mcp-servers`, `agents` (subagent allowlist — real subagent orchestration), `handoffs`, `user-invocable`, `hooks`, `disable-model-invocation`; 30,000-char body limit. Old `*.chatmode.md` chat modes are migrated by renaming to `.agent.md`. Work in VS Code, Eclipse, Xcode, Copilot CLI, and GitHub.com (cloud agent ignores `argument-hint`/`handoffs`).

#### Hooks
[Agent hooks (Preview)](https://code.visualstudio.com/docs/agent-customization/hooks) in VS Code: 8 events — `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Config in `.github/hooks/*.json` (workspace), `~/.copilot/hooks` (user), agent-scoped via `hooks` in `.agent.md` — and VS Code also reads Claude Code's `.claude/settings.json`/`settings.local.json` hook config. Hooks are shell commands receiving JSON on stdin; they can block (`"continue": false` / exit 2), return `permissionDecision: allow|deny|ask`, and inject `additionalContext`. Hook support in standalone Copilot CLI and cloud agent: unverified as of 2026-08-11.

#### Plugins
[Agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins): folder with `plugin.json` manifest (Agent Plugins 1.0 open schema, `agent-plugins.org`) bundling `skills/`, `agents/`, `hooks/`, `mcp.json`, and slash commands. Marketplaces are git repos (default: GitHub's `copilot-plugins` and `awesome-copilot`; add via `chat.plugins.marketplaces`). **Claude Code plugin format (`.claude-plugin/plugin.json`) is auto-detected and loadable.** Plugins installed via Copilot CLI auto-appear in VS Code.

#### Output styles / personas
No dedicated output-style primitive. Persona/tone customization is done via custom agents (above) or personal custom instructions on github.com. The former "chat modes" (`*.chatmode.md`) are effectively deprecated — renamed into custom agents ([VS Code docs](https://code.visualstudio.com/docs/copilot/customization/custom-agents)).

#### MCP
Full MCP client on all three surfaces, different config per surface: VS Code uses [`.vscode/mcp.json`](https://code.visualstudio.com/docs/copilot/customization/mcp-servers) (workspace) and a user-profile `mcp.json` (stdio + HTTP transports, `inputs` for secrets, devcontainer support, auto-discovery of Claude Desktop config, sandbox mode for local servers). Copilot CLI uses `~/.copilot/mcp-config.json` (`/mcp add`). The cloud agent takes a JSON MCP config entered in **repository settings on github.com** (shared with code review; GitHub MCP and Playwright MCP [enabled by default](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/extend-cloud-agent-with-mcp)) — not a committable file.

#### Config & settings
VS Code: standard settings (`chat.*` keys) plus the Agent Customizations editor. Copilot CLI: [`~/.copilot/config.json`](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/configure-copilot-cli) (relocatable via `COPILOT_HOME`), including `trustedFolders`. Cloud agent: repo settings on github.com plus `.github/workflows/copilot-setup-steps.yml` (a single `copilot-setup-steps` Actions job that pre-installs environment dependencies).

#### Permissions & sandboxing
Copilot CLI: per-tool approval prompts; [`--allow-tool` / `--deny-tool`](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools) with `Kind(argument)` patterns (e.g. `--deny-tool 'shell(rm)'`; deny always beats allow, even under `--allow-all`/`--yolo`); saved approvals in `permissions-config.json`; trusted-directory model. Cloud agent: sandboxed ephemeral Actions runner, single-repo write scope, 59-minute task cap, and an [egress firewall](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-firewall) (customizable/disableable in repo settings; applies to Bash-tool processes, not MCP servers or setup steps). VS Code: tool confirmation prompts, hook-driven `permissionDecision`, MCP server trust + sandbox mode.

#### Automation & scheduling
Copilot CLI has a [programmatic mode](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference) (`copilot -p "<prompt>"`) for scripts and CI/CD. Cloud agent tasks start from issue assignment, the agents panel, chat, integrations (Jira/Linear/Slack/Teams), or programmatically via the [Agent tasks REST API](https://docs.github.com/en/rest/agent-tasks/agent-tasks) (public preview since [May 2026](https://github.blog/changelog/2026-05-13-start-copilot-cloud-agent-tasks-via-the-rest-api/); Pro tiers added June 2026) and the GitHub CLI. Scheduled agentic runs come via [GitHub Agentic Workflows (gh-aw)](https://github.github.com/gh-aw/reference/copilot-cloud-agent/) — markdown workflows compiled to Actions with cron triggers, able to spawn cloud-agent sessions — or plain Actions cron jobs invoking `copilot -p`.

#### Vault wiring implications
- Our root `AGENTS.md` bootstrap is picked up **natively and unmodified** by VS Code, Copilot CLI, and github.com agents — no Copilot-specific entrypoint needed for agent surfaces. Caveat: our `CLAUDE.md` contains only `@AGENTS.md` (Claude import syntax Copilot does not expand), and github.com treats root `CLAUDE.md` as an *alternative* to AGENTS.md — the adapter should ensure AGENTS.md wins and optionally add a thin `.github/copilot-instructions.md` pointer so JetBrains/Visual Studio/Xcode/Eclipse (which ignore AGENTS.md) still get the bootstrap sequence.
- Our SKILL.md folders drop into `.github/skills/` (or stay in `.claude/skills/`, which Copilot also scans) with zero format changes — same agentskills.io standard; personal skills go to `~/.copilot/skills/`.
- Vault policies (Inbox-first rule, tagging/frontmatter rules) map cleanly to `.github/instructions/*.instructions.md` with `applyTo` globs (e.g. `applyTo: "02_Inbox/**"`), enforced across chat, cloud agent, and code review.
- The pre-commit frontmatter hook runs as-is in the cloud agent's Actions environment and under Copilot CLI; VS Code agent hooks (`.github/hooks/*.json`, PostToolUse/Stop) can additionally lint frontmatter mid-session — and VS Code even reuses our `.claude/settings.json` hook config.
- The stdlib `brain` CLI: pre-approve via `--allow-tool 'shell(brain)'` (CLI), install for the cloud agent via `.github/workflows/copilot-setup-steps.yml`, and expose per-skill via `allowed-tools` in SKILL.md frontmatter.
- Adapter-specific carry: the `.github/copilot-instructions.md` shim, `.github/instructions/` rule variants, `copilot-setup-steps.yml`, and documentation for the cloud agent's settings-page MCP config (it cannot be committed as a file).

#### Sources
- https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions
- https://docs.github.com/en/copilot/concepts/prompting/response-customization
- https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
- https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview
- https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools
- https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/configure-copilot-cli
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference
- https://docs.github.com/en/copilot/reference/custom-agents-configuration
- https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/extend-cloud-agent-with-mcp
- https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-firewall
- https://docs.github.com/en/copilot/how-tos/configure-content-exclusion/exclude-content-from-copilot
- https://docs.github.com/en/rest/agent-tasks/agent-tasks
- https://github.blog/changelog/2026-05-13-start-copilot-cloud-agent-tasks-via-the-rest-api/
- https://code.visualstudio.com/docs/copilot/customization/overview
- https://code.visualstudio.com/docs/copilot/customization/custom-instructions
- https://code.visualstudio.com/docs/copilot/customization/prompt-files
- https://code.visualstudio.com/docs/copilot/customization/custom-agents
- https://code.visualstudio.com/docs/copilot/customization/agent-skills
- https://code.visualstudio.com/docs/agent-customization/hooks
- https://code.visualstudio.com/docs/agent-customization/agent-plugins
- https://code.visualstudio.com/docs/copilot/customization/mcp-servers
- https://github.github.com/gh-aw/reference/copilot-cloud-agent/

**Research gaps (2026-08-11):** Hook support in standalone Copilot CLI and the cloud agent could not be confirmed (VS Code docs describe hooks as applying across agent harnesses inside VS Code only) — marked unverified. The exact VS Code user-profile paths for prompt files/user mcp.json are profile-folder-relative, not fixed paths, so not quoted. The `gh skill` discovery command was mentioned in docs summaries but not independently verified. Cloud-agent details known from training (draft-PR-only output, Actions-approval gate on CI) were not re-verified from fetched pages and were omitted. Content-exclusion plan/tier requirements not stated in the fetched doc. All docs were read via WebFetch summarization of live pages on 2026-08-11; per-surface support matrix rows for Copilot CLI/cloud agent in the response-customization table were partially reconstructed from multiple pages rather than one canonical table.

### Muse Code (P1)
Muse Code is [Meta's coding agent for the terminal and CI](https://dev.meta.ai/docs/muse-code.md), built by Meta Superintelligence Labs on the `muse-spark-1.2` model (co-trained with the harness) and [launched in beta on 2026-08-05](https://techcrunch.com/2026/08/05/meta-launches-muse-code-an-ai-agent-for-large-code-bases/) for macOS and Linux (`curl -fsSL https://dev.meta.ai/install.sh | sh`). Surfaces are an interactive TUI and a headless `muse exec` mode — no IDE/web/desktop surface is documented. Its runtime is an append-only local event log ([replay-exact, restart-safe](https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2)) with persistent async background agents. Closed-source, [usage-based token billing](https://dev.meta.ai/docs/muse-code/auth.md); press reports a discounted "contributor" tier (>10x cheaper) in exchange for training-data consent ([CNBC](https://www.cnbc.com/2026/08/05/meta-debuts-muse-code-to-take-on-anthropic-and-openai-.html)).

#### Context & memory files
Reads **AGENTS.md natively** — `muse init` creates it, and per the [configuration docs](https://dev.meta.ai/docs/muse-code/configuration.md) it "prefers `AGENTS.md` over `CLAUDE.md`" when both exist (CLAUDE.md is the fallback). Muse walks from workspace root to the nearest `.git` boundary loading one instruction file per directory level; "project rules win over user rules" and "the deeper file wins over a shallower one." Untrusted workspaces ignore both files. No `@import`/inclusion mechanism documented; no user-level global AGENTS.md path documented (unverified as of 2026-08-11). Separate **memory system**: project memory committed at `<repo>/.agents/memory/` with a `MEMORY.md` index plus per-topic `.md` files — the index loads at session start, files load on demand; personal (machine-wide) and personal-project scopes exist but their paths are undocumented. Docs warn project memory loads even in untrusted workspaces (prompt-injection surface).

#### Rules
No dedicated rule-file format (no glob scoping, no frontmatter-triggered rules). The rules story is the nested AGENTS.md hierarchy above, plus permission prefix rules (see Permissions). "None found" beyond that.

#### Skills
First-class, **SKILL.md-compatible**. Discovery per the [extending docs](https://dev.meta.ai/docs/muse-code/extending.md): built-in; user (`$XDG_CONFIG_HOME/muse/skills` and `~/.agents/skills`); project (`<repo>/.agents/skills/<skill-id>/SKILL.md`, committed). It **also scans `<repo>/.claude/skills` and `<repo>/.codex/skills`**, and `muse skills import --from claude` / `--from codex` converts existing skills. CLI: `muse skills list|inspect|enable|install|validate`, with `--scope project|user`. Invocation: "In an interactive session, invoke a skill with a slash command," and a background skill-recall observer auto-loads relevant skills. Exact SKILL.md frontmatter fields are not specified in the docs (unverified as of 2026-08-11).

#### Commands
Built-in slash commands only (`/plan`, `/goal`, `/loop`, `/compact`, `/resume`, `/fork`, `/side`, etc. — [interactive docs](https://dev.meta.ai/docs/muse-code/interactive.md)). No standalone custom-command file format; user-defined slash entries come from skills, which surface as slash commands.

#### Subagents / custom agents
Runtime feature, not a file format: the lead spawns children via native tools (`subagent_spawn`, `subagent_status`, `subagent_send_message`, `subagent_cancel`, `subagent_wait`, `subagent_read_result`), steered interactively via `/agent*` commands. Optional `--subagent-worktree-isolation` gives each child a detached-HEAD git worktree under `.muse/worktrees/`; default concurrency ≈ cores−2, clamped 2–16; children run one level deep. No user-authored agent definition files documented. Four background observer agents (memory recall, skill recall, goal tracking, verification — last off by default) toggle via `runtime_capabilities` in settings.

#### Hooks
Three sources: project `<project-root>/.muse/hooks.json`; user (in `~/.config/muse/settings.json` `hooks` block); managed (file at `managed_hooks_path`, pre-approved). Twelve events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreLLMCall`, `PostLLMCall`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Hooks "enforce a check, format code, or block an action"; they receive a JSON payload on stdin and run with a cleared environment plus a small allowlist. User/project hooks require explicit `muse hooks trust <key>`; tooling includes `muse hooks list|validate|run --fixture`. Exact exit-code semantics undocumented (unverified as of 2026-08-11).

#### Plugins
None found — no plugin packaging, marketplace, or registry documented; distribution is per-mechanism (skills install/import, hooks trust).

#### Output styles / personas
None found. Instruction files can set tone/standing rules, but no output-style/persona feature is documented ("voice" refers to a TUI `/voice` feature, not a persona system).

#### MCP
Supported, configured under `mcp_servers` in `~/.config/muse/settings.json`. Transports: `stdio` (`command`/`args`/`env`) and `streamable_http` (`url`/`headers`). Per-server mode `required` (default, aborts on failure) or `optional`. No project-scoped MCP config file documented. Docs warn "MCP tools are not sandboxed" — they run outside the filesystem/network sandbox.

#### Config & settings
Single user settings file `~/.config/muse/settings.json` (must contain `"schema_version": 1` or every command fails with `malformed settings file`); holds model defaults, TUI preferences, MCP servers, hooks, `managed_hooks_path`, `runtime_capabilities`, telemetry. No project-level settings file documented. Model via `--model` / `/models`; reasoning via `--reasoning-effort` (`minimal`→`ultra`, clamped to `xhigh`). Auth via browser sign-in or `META_API_KEY`.

#### Permissions & sandboxing
Per the [permissions docs](https://dev.meta.ai/docs/muse-code/permissions.md): approval modes `on-request` (default; only the dangerous set — `rm -f`, `rm -rf`, `sudo` — stops), `untrusted` (any stage without an allow rule stops), `never`. Compound commands are parsed into ordered stages reviewed individually. Allow decisions: once / always-in-this-workspace (saved prefix rule scoped to workspace root); deny overrides allow; interpreter prefixes (python, bash, node) cannot be broadly allowed. A built-in **approval judge** auto-reviews prompt-bound calls (`--approval-judge off` to disable). OS sandbox: Seatbelt on macOS, bundled bubblewrap on Linux; write access limited to workspace + temp, and **`.git`, `.muse`, `.agents` stay read-only inside the workspace**. Network: `--sandbox-network proxy-only` (default, per-destination approval) / `restricted` / `enabled`. Escape hatches: `--yolo`, `--disable-approval`, `--disable-sandbox`. Workspace trust is asked on first open and gates loading of project skills, rules, and hooks.

#### Automation & scheduling
Headless `muse exec "prompt"` (or `--prompt-file`) for scripts/CI, `--json` for JSONL events on stdout, `--max-model-steps`, `--session-id` resume, `--no-session-log`; exit codes 0/1/2/130/143. `muse export --session <uuid>` for audit. Linux CI needs working bubblewrap and a non-musl build. In-session automation via `/goal`, `/loop`, and persistent background agents; **no native scheduler** — recurring runs are external (cron/CI) as of 2026-08-11.

#### Vault wiring implications
- **Zero-adapter entrypoint**: our `AGENTS.md` is Muse Code's native, preferred instruction file — the `CLAUDE.md → @AGENTS.md` shim is unnecessary here (and Muse ignores it when AGENTS.md exists). Bootstrap-sequence links work as prose; no import mechanism to lean on.
- **Skills land natively**: ship vault skills at `.agents/skills/<skill-id>/SKILL.md`; Muse also scans `.claude/skills`, so a single Claude-format skill tree serves both harnesses, with `muse skills validate` / `import --from claude` as the migration check.
- **Memory bridge is the adapter's main job**: mirror the vault map into `.agents/memory/MEMORY.md` (index → `00_Meta/index`, topics → `01_Profile/now`, `01_Profile/preferences`) so Muse's memory-recall observer surfaces vault context automatically.
- **Sandbox caveat for git**: `.git` and `.agents` are read-only in the sandbox, so our pre-commit frontmatter hook still guards human commits, but agent-driven commits/`updated:` bumps need approval or an unsandboxed stage — replicate the lint as a `PostToolUse` hook in `.muse/hooks.json` (users must `muse hooks trust` it once).
- **`brain` CLI**: pre-seed workspace prefix allow-rules ("always allow in this workspace") for `brain …` invocations; under `untrusted` mode every unlisted stage prompts. `proxy-only` networking is fine for a local vault.
- **MCP is user-scope only**: the vault cannot ship project MCP config; the Muse adapter README must document adding any vault MCP server to `~/.config/muse/settings.json` manually.

#### Sources
- https://dev.meta.ai/docs/muse-code.md
- https://dev.meta.ai/docs/muse-code/configuration.md
- https://dev.meta.ai/docs/muse-code/extending.md
- https://dev.meta.ai/docs/muse-code/permissions.md
- https://dev.meta.ai/docs/muse-code/interactive.md
- https://dev.meta.ai/docs/muse-code/auth.md
- https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2
- https://developer.meta.com/ai/resources/blog/build-with-muse-code/
- https://techcrunch.com/2026/08/05/meta-launches-muse-code-an-ai-agent-for-large-code-bases/
- https://www.cnbc.com/2026/08/05/meta-debuts-muse-code-to-take-on-anthropic-and-openai-.html

**Research gaps (2026-08-11):** SKILL.md frontmatter field spec not published in fetched docs; user-level global instruction-file path and personal-memory filesystem path undocumented; hook exit-code semantics not detailed; exact slash-name binding for custom skills not shown verbatim; contributor-tier pricing (>10x cheaper, training-data consent) confirmed only via press (TechCrunch/CNBC), not the auth docs, which describe usage-based token billing; no ignore-file mechanism found anywhere (absence not explicitly confirmed by docs). Product is 6 days old (beta, launched 2026-08-05), so all details are volatile.

## Related

- [[00_Meta/prd]] — §8.3 support tiers this research grounds; §9.3 plugin-library design
- [[07_Archives/inbox/2026-08-11-m5-m7-implementation-plan|M5–M7 Implementation Plan]] — consumes these findings (adapter manifests, install map)
- [[01_Profile/preferences]] — portable home for voice/tone (in lieu of output styles)
