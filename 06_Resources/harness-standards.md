---
title: "Harness Primitives: Universal Standards & Protocols"
tags:
  - type/reference
  - topic/software
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Primitives: Universal Standards & Protocols

Part of the [[06_Resources/harness-primitives-research|harness primitives research]] (2026-08-11) — see it for the cross-harness overlap matrix and comparative findings. Surfaces move fast; re-verify against the sources below before relying on specifics.

The universal standards layer is not a harness but the portability substrate every harness adapter builds on. Three live standards matter as of 2026-08: **AGENTS.md** (project instruction entrypoint, contributed by OpenAI), **Agent Skills / SKILL.md** (packaged workflows, originated at Anthropic), and **MCP** (tool/context protocol, originated at Anthropic). All three are open and free; MCP and AGENTS.md are founding projects of the [Agentic AI Foundation (AAIF) under the Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) (formed Dec 2025; platinum members include AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI), while Agent Skills is developed openly at [github.com/agentskills/agentskills](https://github.com/agentskills/agentskills).

## AGENTS.md — the entrypoint/context standard
- ["A README for agents"](https://agents.md/): plain Markdown, **no required fields** — "AGENTS.md is just standard Markdown… any headings you like". 60,000+ open-source projects use it; now "stewarded by the Agentic AI Foundation under the Linux Foundation".
- Nesting/precedence: nested AGENTS.md files in monorepo subdirs are explicitly supported; "The closest AGENTS.md to the edited file wins; explicit user chat prompts override everything." Agents "automatically read the nearest file in the directory tree."
- Adoption (per [agents.md](https://agents.md/)): 25+ tools including OpenAI Codex, Google Jules, Aider, Cursor, GitHub Copilot, VS Code, Devin, JetBrains Junie, Warp; Gemini CLI supports it via `.gemini/settings.json` config.
- Notable holdout: **Claude Code does not read AGENTS.md natively** — its docs state ["Claude Code reads `CLAUDE.md`, not `AGENTS.md`"](https://code.claude.com/docs/en/memory) and recommend a `CLAUDE.md` containing `@AGENTS.md` (import, loaded at session start) or a symlink. This vault already ships exactly that shim.

## Agent Skills (SKILL.md) — the workflow-packaging standard
- A skill is a folder with a `SKILL.md` (YAML frontmatter + Markdown body). [Spec fields](https://agentskills.io/specification): `name` (required, 1–64 chars, lowercase alphanumerics + hyphens, no leading/trailing/consecutive hyphens, **must match directory name**), `description` (required, 1–1024 chars), optional `license`, `compatibility` (≤500 chars), `metadata` (string→string map), `allowed-tools` (space-separated pre-approved tools, **experimental**).
- Optional bundled dirs by convention: `scripts/` (executable code), `references/` (on-demand docs), `assets/` (templates/data). References use relative paths, kept one level deep.
- [Progressive disclosure](https://agentskills.io/): (1) metadata ~100 tokens loaded at startup for all skills, (2) full `SKILL.md` body on activation (<5k tokens recommended, keep under 500 lines), (3) bundled resources only as needed. Validate with `skills-ref validate` from the reference library.
- Discovery paths are **not standardized by the spec** — each harness defines its own. An `.agents/skills/` convention is emerging: [Cursor scans](https://cursor.com/docs/context/skills) `.agents/skills/` and `.cursor/skills/` (project), `~/.agents/skills/` and `~/.cursor/skills/` (user), plus legacy `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, `~/.codex/skills/`. Codex CLI uses `$CODEX_HOME/skills` (default `~/.codex/skills`) per community docs — official page returned 503, unverified as of 2026-08-11.
- Adoption: "originally developed by Anthropic, released as an open standard"; the [client showcase](https://agentskills.io/) lists 45+ adopters including Claude Code, Claude (claude.ai), ChatGPT & Codex, GitHub Copilot, VS Code, Cursor, Gemini CLI, JetBrains Junie, Goose, OpenCode, Amp, Roo Code, Factory, Kiro, Trae, Tabnine, Snowflake Cortex Code, Databricks Genie Code.

## MCP (Model Context Protocol) — the tool/context protocol
- [Open-source standard](https://modelcontextprotocol.io/) for connecting AI apps to external systems; joined the AAIF in Dec 2025. Date-based versioning; **current revision is `2026-07-28`** per the [versioning page](https://modelcontextprotocol.io/specification/versioning). The 2026-07-28 revision is stateless: every request carries `io.modelcontextprotocol/protocolVersion` in `_meta`, with a mandatory `server/discover` RPC replacing the old initialize handshake (compat path documented for `2025-11-25` and earlier).
- Primitives ([architecture](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)): server-side **tools**, **resources**, **prompts** (+ opt-in change notifications via `subscriptions/listen`); client-side **elicitation**. **Deprecated as of `2026-07-28`** per the [deprecated-features registry](https://modelcontextprotocol.io/specification/2026-07-28/deprecated): **roots**, **sampling**, **logging** (earliest removal on/after 2027-07-28), plus Dynamic Client Registration; the HTTP+SSE transport has been deprecated since `2025-03-26`.
- Transports: **stdio** (local) and **Streamable HTTP** (remote; OAuth recommended). Optional extensions build on core: Tasks (durable handles for long-running requests) and MCP Apps.
- Client adoption (per MCP homepage): Claude, ChatGPT, VS Code, Cursor, "and many others". **Config file locations/scopes are not standardized** — each harness defines its own MCP registration files.

## Other live cross-harness conventions
- **ACP (Agent Client Protocol)** — [agentclientprotocol.com](https://agentclientprotocol.com/): standardizes editor↔agent communication (LSP analog), created and maintained by Zed, Apache-licensed; editor adopters include Zed, JetBrains IDEs, Neovim and Emacs plugins, with Gemini CLI first among agents per [Zed's blog](https://zed.dev/blog/bring-your-own-agent-to-zed) and [progress report](https://zed.dev/blog/acp-progress-report). Harness-plumbing relevance only; no vault file format depends on it.
- **`.agents/` directory** — emerging neutral home for agent assets (skills today, per Cursor's docs above); not yet a written standard beyond skills discovery.
- **No cross-harness standard exists** for: glob-scoped rule files, command files, subagent definitions, lifecycle hooks, plugins/marketplaces, output styles, settings files, permission configuration, scheduling, or agent ignore files. These all remain per-harness. Git's own hooks (pre-commit) are the de facto portable enforcement layer since every harness commits through git.

## Vault wiring implications
- **Entrypoint is solved by AGENTS.md alone**: the vault-root `AGENTS.md` bootstrap doc is read natively by essentially every harness except Claude Code, which the existing one-line `CLAUDE.md` → `@AGENTS.md` shim covers using Anthropic's own documented bridge. Nested `AGENTS.md` files (e.g. in `02_Inbox/`, `10_Agents/`) are the only portable way to ship directory-scoped rules ("closest wins").
- **Canonical skills live at `.agents/skills/<name>/SKILL.md`**: spec-strict (dir name == `name`, ≤64/≤1024 limits, body <500 lines, `references/`+`scripts/` layout) makes them load anywhere; Cursor reads that path natively, other harness adapters only need a symlink/copy into `.claude/skills/`, `~/.codex/skills/`, etc.
- **The pre-commit hook is the only hook that travels**: no agent-hook standard exists, so all hard enforcement (frontmatter lint, tag taxonomy, `updated:` bump) belongs in the git pre-commit hook, with `skills-ref validate` added for skill folders; harness-native hooks are per-adapter conveniences only.
- **The `brain` CLI ports via MCP stdio**: exposing it as an MCP server (tools + a resource for `00_Meta/index`) makes it reachable from GUI/web harnesses that can't shell out — but registration config is per-harness, so each adapter carries its own MCP stanza. Target spec `2026-07-28` semantics and do not build on roots/sampling/logging (all deprecated).
- **What the standards track alone carries**: entrypoint + prose rules (AGENTS.md), workflows (Agent Skills), tool/context access (MCP). Commands, subagents, output styles, permissions, scheduling, and ignore rules must be regenerated per harness by the adapter layer.

## Sources
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

**Research gaps (2026-08-11):** OpenAI's official Codex skills page (developers.openai.com/codex/skills) returned HTTP 503 on two attempts, so Codex's exact skill discovery paths ($CODEX_HOME/skills, default ~/.codex/skills) rest on Cursor's compatibility list and community docs, not first-party docs. The agents.md adoption list was summarized ("25+ tools") rather than enumerated in full. The Agent Skills spec has no published versioning/governance document beyond the GitHub repo, so spec-version pinning is not possible. ACP's maintainer (Zed) and adopter list came from Zed blog posts surfaced via search, not a direct fetch of the protocol site (whose landing page names no adopters). MCP client adoption was verified only for the clients named on modelcontextprotocol.io (Claude, ChatGPT, VS Code, Cursor); per-harness MCP support for the other harnesses in the support matrix in [[06_Resources/harness-primitives-research]] was not re-verified here. Whether .gitignore is honored as an agent-ignore convention across harnesses was not verified.
