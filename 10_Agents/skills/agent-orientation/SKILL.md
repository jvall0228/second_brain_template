---
name: agent-orientation
description: Discover the high-value context sources available in this adopter's environment (chat, email, calendar, transcripts, task trackers) and generate the vault tooling to access them. Use once per new environment, or when the owner's toolchain changes.
title: "Skill: Agent Orientation"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Agent Orientation

**CODE stage:** Onboarding.

Map what this environment can reach, agree on what's worth ingesting, and generate the access layer — the vault reaches outward from here.

## Integration preference ladder (apply at every step)

When a source needs access tooling, prefer in this order (PRD §19 M7, decision #9):

1. **Environment-specific custom tooling** — a CLI script or MCP integration built for this environment
2. **The vendor's first-party CLI** (e.g. `gh`, `gcloud`, mail/calendar CLIs)
3. **A first-party MCP server / connector**

**Credentials never enter the repo** (PRD §16.2): auth lives in local CLI sessions, keychains, or environment variables — a generated tool reads `$SOURCE_TOKEN`, it never contains one. Refuse to write any secret into a committed file.

## Steps

1. **Inventory the environment.** What is actually reachable from here: harness-provided tools and MCP servers/connectors (list them), CLIs on PATH (`git`, `gh`, vendor CLIs), schedulers (see `recommended-automations`), and the harness adapter in `10_Agents/harnesses/<name>/wiring.md`.
2. **Interview the owner.** Which sources carry real context — team chat (Teams/Slack), meeting transcripts, calendars, email, task trackers, docs? For each: value, sensitivity (some sources shouldn't enter the vault at all — PRD §16.2), and desired freshness. Source priorities are the owner's call, decided here.
3. **Write the inventory note** to `02_Inbox/` (`YYYY-MM-DD-orientation-inventory.md`, `workflow/draft`): reachable sources, chosen ladder rung per source, owner decisions, and what was deliberately excluded.
4. **Generate the access layer for each adopted source:**
   - **Tooling** under `10_Agents/tools/<source>/` — a script (stdlib-first, config via env vars) where the rung is a CLI; an access doc naming the exact harness tools where the rung is MCP/connector.
   - **A paired skill** at `10_Agents/skills/<source>-capture/SKILL.md` describing when and how to pull from the source and capture into the vault **via the `inbox-capture` rules**.
   - Both tagged `workflow/draft` (agent-generated; the owner promotes — PRD §9.3). Everything must pass `python3 10_Agents/tools/brain/brain.py validate`.
5. **Hand off:** propose recurring flows to `recommended-automations`; register everything generated for `self-maintenance` audits (both list draft tooling by walking `10_Agents/`).

## References

- `10_Agents/harnesses/<name>/wiring.md` — what this harness can reach and how
- `00_Meta/prd.md` §19 M7, §16.2 — the ladder and the credentials rule
