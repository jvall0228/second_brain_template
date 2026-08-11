---
name: self-maintenance
description: Audit the agent-generated skills, tools, and automations over time — validate, prune dead sources, update for upstream changes, and propose promotions or archival to the owner. Use on a recurring cadence (monthly fits the review rhythm) or after any environment change.
title: "Skill: Self Maintenance"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Self Maintenance

**CODE stage:** System (outside the loop).

Generated tooling rots as environments drift. This skill keeps the generated layer honest.

## Scope

Everything agent-generated under `10_Agents/` — `workflow/draft` skills and tools from `agent-orientation`, plus wired automations — and the dated facts in `10_Agents/harnesses/*/wiring.md`. Template-shipped (canonical) content is out of scope except for flagging staleness to the owner.

## Steps

1. **Resolve and read only the current environment:** run `brain env detect --json`; fail closed if it does not select exactly one slug. Read that slug's `orientation-inventory.md` only. Its solution inventory and recorded interface rungs are the source list this audit probes, and its capability/policy section bounds what the audit may do here. `brain env list` may diagnose metadata, but never use it to read another environment's contents.
2. **Enumerate the generated layer:** `brain list --dir 10_Agents --tag workflow/draft --json`, plus automations documented in orientation/automation notes.
3. **Validate:** `brain validate` must stay clean; fix generated-content errors directly (bump `updated:`).
4. **Probe each source** a generated tool or flow depends on: does the CLI still exist and authenticate, is the MCP server still registered, does a dry-run still return data? Auth stays environmental — **credentials never enter the repo** (PRD §16.2), so a probe failure is often just an expired local session: report it, don't work around it by embedding secrets.
5. **Repair or prune:** update tooling for upstream changes (re-verify against current vendor docs), keeping each tool on the best rung of the **interface ranking ladder** (see `agent-orientation`: custom tooling → first-party CLI → first-party MCP/connector → wrapped vendor API → browser → none) — and propose pruning tools whose source is gone.
6. **Propose lifecycle changes** to the owner via an Inbox report (`YYYY-MM-DD-self-maintenance-report.md`): drafts that earned promotion (stable, used, validated) — **only the owner assigns `workflow/canonical`** (PRD §11) — drafts to archive, wiring-doc facts that need re-verification (check each doc's `updated:` date), and automation flows that produced noise instead of signal.
7. **Apply what the owner approves**, commit, push.

## References

- `00_Meta/prd.md` §6.2 (write policy), §11 (promotion), §8.4 (environment integrations)
- `10_Agents/skills/vault-maintenance/SKILL.md` — the vault-side sibling of this skill
