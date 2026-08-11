---
title: "Harness Adapters"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - workflow/canonical
updated: 2026-08-11
---

# Harness Adapters

Per-harness adapters for the support tiers in [[00_Meta/prd]] §8.3. **Standards-first:** the entrypoint (`AGENTS.md`), the skills library (`10_Agents/skills/`, Agent Skills format), and the `brain` CLI work in any harness with no adapter — each directory here carries **only what a cross-harness standard cannot**: exact config paths, import syntax, caps, and trust gates.

Every adapter ships a `wiring.md` (entrypoint loading, skills install paths, hook installation, how the harness invokes `brain`, harness-specific caveats) and reference config files to copy or merge. The [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] skill consumes these wiring docs for user-scope installs.

| Adapter | Tier | Wiring |
|---------|------|--------|
| [[10_Agents/harnesses/claude-code/wiring\|Claude Code]] | P0 | needs the `CLAUDE.md` import; scans `.claude/skills/` only |
| [[10_Agents/harnesses/codex/wiring\|Codex]] | P0 | native `AGENTS.md`; 32 KiB project-doc cap; trusted-project config |
| [[10_Agents/harnesses/opencode/wiring\|opencode]] | P0 | native `AGENTS.md`; `instructions[]` makes bootstrap deterministic |
| [[10_Agents/harnesses/pi/wiring\|Pi]] | P0 | native `AGENTS.md`; trust gate; no MCP (extensions instead) |
| [[10_Agents/harnesses/copilot/wiring\|Copilot]] | P0 | native `AGENTS.md` on agent surfaces; shipped `.github/` shim + cloud-agent validate hook |
| [[10_Agents/harnesses/cursor/wiring\|Cursor]] | P1 | native `AGENTS.md`; `.mdc` rules; only harness with a real ignore file |
| [[10_Agents/harnesses/muse-code/wiring\|Muse Code]] | P1 | volatile (launched 2026-08-05); user-scope config only |

Facts are grounded in [[06_Resources/harness-primitives-research|the 2026-08-11 harness research]] (sources linked there); Copilot facts live in [[06_Resources/copilot-harness-deep-dive|the same-day Copilot deep-dive]], which supersedes that note's Copilot section. Harness surfaces move fast — **re-verify a wiring doc against its sources before relying on it**, and bump `updated:` when you do.
