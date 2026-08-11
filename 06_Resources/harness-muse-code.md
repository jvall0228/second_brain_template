---
title: "Harness Primitives: Muse Code"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: Muse Code

Part of the [[06_Resources/harness-primitives-research|harness primitives research]] (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

Muse Code is [Meta's coding agent for the terminal and CI](https://dev.meta.ai/docs/muse-code.md), built by Meta Superintelligence Labs on the `muse-spark-1.2` model (co-trained with the harness) and [launched in beta on 2026-08-05](https://techcrunch.com/2026/08/05/meta-launches-muse-code-an-ai-agent-for-large-code-bases/) for macOS and Linux (`curl -fsSL https://dev.meta.ai/install.sh | sh`). Surfaces are an interactive TUI and a headless `muse exec` mode — no IDE/web/desktop surface is documented. Its runtime is an append-only local event log ([replay-exact, restart-safe](https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2)) with persistent async background agents. Closed-source, [usage-based token billing](https://dev.meta.ai/docs/muse-code/auth.md); press reports a discounted "contributor" tier (>10x cheaper) in exchange for training-data consent ([CNBC](https://www.cnbc.com/2026/08/05/meta-debuts-muse-code-to-take-on-anthropic-and-openai-.html)).

## Context & memory files
Reads **AGENTS.md natively** — `muse init` creates it, and per the [configuration docs](https://dev.meta.ai/docs/muse-code/configuration.md) it "prefers `AGENTS.md` over `CLAUDE.md`" when both exist (CLAUDE.md is the fallback). Muse walks from workspace root to the nearest `.git` boundary loading one instruction file per directory level; "project rules win over user rules" and "the deeper file wins over a shallower one." Untrusted workspaces ignore both files. No `@import`/inclusion mechanism documented; no user-level global AGENTS.md path documented (unverified as of 2026-08-11). Separate **memory system**: project memory committed at `<repo>/.agents/memory/` with a `MEMORY.md` index plus per-topic `.md` files — the index loads at session start, files load on demand; personal (machine-wide) and personal-project scopes exist but their paths are undocumented. Docs warn project memory loads even in untrusted workspaces (prompt-injection surface).

## Rules
No dedicated rule-file format (no glob scoping, no frontmatter-triggered rules). The rules story is the nested AGENTS.md hierarchy above, plus permission prefix rules (see Permissions). "None found" beyond that.

## Skills
First-class, **SKILL.md-compatible**. Discovery per the [extending docs](https://dev.meta.ai/docs/muse-code/extending.md): built-in; user (`$XDG_CONFIG_HOME/muse/skills` and `~/.agents/skills`); project (`<repo>/.agents/skills/<skill-id>/SKILL.md`, committed). It **also scans `<repo>/.claude/skills` and `<repo>/.codex/skills`**, and `muse skills import --from claude` / `--from codex` converts existing skills. CLI: `muse skills list|inspect|enable|install|validate`, with `--scope project|user`. Invocation: "In an interactive session, invoke a skill with a slash command," and a background skill-recall observer auto-loads relevant skills. Exact SKILL.md frontmatter fields are not specified in the docs (unverified as of 2026-08-11).

## Commands
Built-in slash commands only (`/plan`, `/goal`, `/loop`, `/compact`, `/resume`, `/fork`, `/side`, etc. — [interactive docs](https://dev.meta.ai/docs/muse-code/interactive.md)). No standalone custom-command file format; user-defined slash entries come from skills, which surface as slash commands.

## Subagents / custom agents
Runtime feature, not a file format: the lead spawns children via native tools (`subagent_spawn`, `subagent_status`, `subagent_send_message`, `subagent_cancel`, `subagent_wait`, `subagent_read_result`), steered interactively via `/agent*` commands. Optional `--subagent-worktree-isolation` gives each child a detached-HEAD git worktree under `.muse/worktrees/`; default concurrency ≈ cores−2, clamped 2–16; children run one level deep. No user-authored agent definition files documented. Four background observer agents (memory recall, skill recall, goal tracking, verification — last off by default) toggle via `runtime_capabilities` in settings.

## Hooks
Three sources: project `<project-root>/.muse/hooks.json`; user (in `~/.config/muse/settings.json` `hooks` block); managed (file at `managed_hooks_path`, pre-approved). Twelve events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreLLMCall`, `PostLLMCall`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Hooks "enforce a check, format code, or block an action"; they receive a JSON payload on stdin and run with a cleared environment plus a small allowlist. User/project hooks require explicit `muse hooks trust <key>`; tooling includes `muse hooks list|validate|run --fixture`. Exact exit-code semantics undocumented (unverified as of 2026-08-11).

## Plugins
None found — no plugin packaging, marketplace, or registry documented; distribution is per-mechanism (skills install/import, hooks trust).

## Output styles / personas
None found. Instruction files can set tone/standing rules, but no output-style/persona feature is documented ("voice" refers to a TUI `/voice` feature, not a persona system).

## MCP
Supported, configured under `mcp_servers` in `~/.config/muse/settings.json`. Transports: `stdio` (`command`/`args`/`env`) and `streamable_http` (`url`/`headers`). Per-server mode `required` (default, aborts on failure) or `optional`. No project-scoped MCP config file documented. Docs warn "MCP tools are not sandboxed" — they run outside the filesystem/network sandbox.

## Config & settings
Single user settings file `~/.config/muse/settings.json` (must contain `"schema_version": 1` or every command fails with `malformed settings file`); holds model defaults, TUI preferences, MCP servers, hooks, `managed_hooks_path`, `runtime_capabilities`, telemetry. No project-level settings file documented. Model via `--model` / `/models`; reasoning via `--reasoning-effort` (`minimal`→`ultra`, clamped to `xhigh`). Auth via browser sign-in or `META_API_KEY`.

## Permissions & sandboxing
Per the [permissions docs](https://dev.meta.ai/docs/muse-code/permissions.md): approval modes `on-request` (default; only the dangerous set — `rm -f`, `rm -rf`, `sudo` — stops), `untrusted` (any stage without an allow rule stops), `never`. Compound commands are parsed into ordered stages reviewed individually. Allow decisions: once / always-in-this-workspace (saved prefix rule scoped to workspace root); deny overrides allow; interpreter prefixes (python, bash, node) cannot be broadly allowed. A built-in **approval judge** auto-reviews prompt-bound calls (`--approval-judge off` to disable). OS sandbox: Seatbelt on macOS, bundled bubblewrap on Linux; write access limited to workspace + temp, and **`.git`, `.muse`, `.agents` stay read-only inside the workspace**. Network: `--sandbox-network proxy-only` (default, per-destination approval) / `restricted` / `enabled`. Escape hatches: `--yolo`, `--disable-approval`, `--disable-sandbox`. Workspace trust is asked on first open and gates loading of project skills, rules, and hooks.

## Automation & scheduling
Headless `muse exec "prompt"` (or `--prompt-file`) for scripts/CI, `--json` for JSONL events on stdout, `--max-model-steps`, `--session-id` resume, `--no-session-log`; exit codes 0/1/2/130/143. `muse export --session <uuid>` for audit. Linux CI needs working bubblewrap and a non-musl build. In-session automation via `/goal`, `/loop`, and persistent background agents; **no native scheduler** — recurring runs are external (cron/CI) as of 2026-08-11.

## Vault wiring implications
- **Zero-adapter entrypoint**: our `AGENTS.md` is Muse Code's native, preferred instruction file — the `CLAUDE.md → @AGENTS.md` shim is unnecessary here (and Muse ignores it when AGENTS.md exists). Bootstrap-sequence links work as prose; no import mechanism to lean on.
- **Skills land natively**: ship vault skills at `.agents/skills/<skill-id>/SKILL.md`; Muse also scans `.claude/skills`, so a single Claude-format skill tree serves both harnesses, with `muse skills validate` / `import --from claude` as the migration check.
- **Memory bridge is the adapter's main job**: mirror the vault map into `.agents/memory/MEMORY.md` (index → `00_Meta/index`, topics → `01_Profile/now`, `01_Profile/preferences`) so Muse's memory-recall observer surfaces vault context automatically.
- **Sandbox caveat for git**: `.git` and `.agents` are read-only in the sandbox, so our pre-commit frontmatter hook still guards human commits, but agent-driven commits/`updated:` bumps need approval or an unsandboxed stage — replicate the lint as a `PostToolUse` hook in `.muse/hooks.json` (users must `muse hooks trust` it once).
- **`brain` CLI**: pre-seed workspace prefix allow-rules ("always allow in this workspace") for `brain …` invocations; under `untrusted` mode every unlisted stage prompts. `proxy-only` networking is fine for a local vault.
- **MCP is user-scope only**: the vault cannot ship project MCP config; the Muse adapter README must document adding any vault MCP server to `~/.config/muse/settings.json` manually.

## Sources
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
