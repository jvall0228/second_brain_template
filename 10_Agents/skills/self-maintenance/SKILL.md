---
name: self-maintenance
description: Audit the agent-generated skills, tools, and automations over time — validate, prune dead sources, update for upstream changes, and propose promotions or archival to the owner. Use on a recurring cadence (monthly fits the review rhythm) or after any environment change.
title: "Skill: Self Maintenance"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
---

# Self Maintenance

Generated tooling rots as environments drift. This skill keeps the generated layer honest.

## Scope

Everything agent-generated under `10_Agents/` — `workflow/draft` skills and tools from `agent-orientation`, plus wired automations — and the dated facts in `10_Agents/harnesses/*/wiring.md`. Template-shipped (canonical) content is out of scope except for flagging staleness to the owner.

## Steps

1. **Enumerate the generated layer:** `python3 10_Agents/tools/brain/brain.py list --dir 10_Agents --tag workflow/draft --json`, plus automations documented in orientation/automation notes.
2. **Validate:** `brain validate` must stay clean; fix generated-content errors directly (bump `updated:`).
3. **Probe each source** a generated tool or flow depends on: does the CLI still exist and authenticate, is the MCP server still registered, does a dry-run still return data? Auth stays environmental — **credentials never enter the repo** (PRD §16.2), so a probe failure is often just an expired local session: report it, don't work around it by embedding secrets.
4. **Repair or prune:** update tooling for upstream changes (re-verify against current vendor docs), keeping each tool on the best rung of the **preference ladder** — (1) environment-specific custom tooling → (2) first-party CLI → (3) first-party MCP/connector — and propose pruning tools whose source is gone.
5. **Propose lifecycle changes** to the owner via an Inbox report (`YYYY-MM-DD-self-maintenance-report.md`): drafts that earned promotion (stable, used, validated) — **only the owner assigns `workflow/canonical`** (PRD §11) — drafts to archive, wiring-doc facts that need re-verification (check each doc's `updated:` date), and automation flows that produced noise instead of signal.
6. **Apply what the owner approves**, commit, push.

## References

- `00_Meta/prd.md` §9.3 (write policy), §11 (promotion), §19 M7
- `10_Agents/skills/vault-maintenance/SKILL.md` — the vault-side sibling of this skill
