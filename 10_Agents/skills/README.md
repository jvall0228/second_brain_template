---
title: "Agent Skills"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Agent Skills

Harness-agnostic skills in the [Agent Skills format](https://agentskills.io): one folder per skill containing a `SKILL.md` whose frontmatter carries the standard `name` + `description` **plus** the vault contract (`title`, `tags`, `updated`) — a superset; harnesses ignore the extra keys, and `brain validate` enforces both contracts.

Harnesses that scan the shared `.agents/skills/` path (or `.claude/skills/` for Claude Code) consume these unchanged — the [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] skill symlinks them into a harness's user config.

## Shipped skills

| Skill | Family | Does |
|-------|--------|------|
| [[10_Agents/skills/inbox-capture/SKILL\|inbox-capture]] | Capture & triage | Write a new `02_Inbox/` note with correct frontmatter, filename, and collision handling |
| [[10_Agents/skills/triage-inbox/SKILL\|triage-inbox]] | Capture & triage | Process the Inbox for review: atomize, extract action items, classify, propose propagation edits |
| [[10_Agents/skills/distill-note/SKILL\|distill-note]] | Capture & triage | Reshape a note into an atomic zettel: core claim, summary layer, links, supersede by replacement |
| [[10_Agents/skills/daily-log/SKILL\|daily-log]] | Periodic reviews | Create or update today's daily log from the template |
| [[10_Agents/skills/periodic-review/SKILL\|periodic-review]] | Periodic reviews | Weekly/monthly/quarterly/yearly reviews — cadence is a parameter |
| [[10_Agents/skills/vault-maintenance/SKILL\|vault-maintenance]] | Vault maintenance | Run `brain validate`, fix findings, keep status/changelog current |
| [[10_Agents/skills/link-repair/SKILL\|link-repair]] | Vault maintenance | Find and fix broken wikilinks using the index's repair hints |
| [[10_Agents/skills/merge-notes/SKILL\|merge-notes]] | Vault maintenance | Execute approved merges, splits, and renames: rewrite, retarget backlinks, archive, validate |
| [[10_Agents/skills/curate/SKILL\|curate]] | Vault maintenance | Work the `brain curate` report: refresh, re-verify, propose archives/splits, semantic lint |
| [[10_Agents/skills/solution-capture/SKILL\|solution-capture]] | Vault maintenance | Record a solved problem in `10_Agents/solutions/` |
| [[10_Agents/skills/research-to-resource/SKILL\|research-to-resource]] | Research → resource | Turn research into a `06_Resources/` note or zettel with provenance |
| [[10_Agents/skills/vault-answer/SKILL\|vault-answer]] | Retrieval | Answer "what do I know about X?" from vault notes, with wikilink citations and capture offers for substantive answers |
| [[10_Agents/skills/express-packet/SKILL\|express-packet]] | Express | Assemble an outbound packet (brief, outline, draft post/email) from vault notes into `02_Outbox/` with provenance; the owner ships |
| [[10_Agents/skills/onboard-harness/SKILL\|onboard-harness]] | Onboarding | Symlink-first user-scope install into a harness + memory-file wiring + hook |
| [[10_Agents/skills/onboard-owner/SKILL\|onboard-owner]] | Onboarding | Guided first-run for a new (possibly non-technical) vault owner: teach by doing, fill the profile, orchestrate the other onboarding skills |
| [[10_Agents/skills/agent-orientation/SKILL\|agent-orientation]] | Environment integration | Discover reachable context sources and generate access tooling + capture skills |
| [[10_Agents/skills/recommended-automations/SKILL\|recommended-automations]] | Environment integration | Wire recurring email/calendar/chat ingestion via the harness's scheduler |
| [[10_Agents/skills/self-maintenance/SKILL\|self-maintenance]] | Environment integration | Audit generated tooling: validate, prune, update, propose promotions |

## Rules

- Template-shipped skills are canonical ([[00_Meta/prd]] §9.3): changes need human approval.
- Agent-generated skills may be added here directly, tagged `workflow/draft` until the human promotes them; they must pass `brain validate` (which checks `name` = folder name and a non-empty `description`).
- Skills reference vault files by path and invoke `brain` via `python3 10_Agents/tools/brain/brain.py …` so they work in any harness.
