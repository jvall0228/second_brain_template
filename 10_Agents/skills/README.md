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

## The CODE Loop in This Vault

The catalog is organized by the CODE method — **C**apture → **O**rganize → **D**istill → **E**xpress — the loop knowledge travels through this vault:

- **Capture** lands raw material in `02_Inbox/` with zero friction.
- **Organize** triages it into PARA (`04_Projects/` … `07_Archives/`).
- **Distill** sharpens filed notes into atomic, evergreen claims (`type/zettel` in `06_Resources/`).
- **Express** turns vault knowledge into answers and outbound packets (`02_Outbox/`) — and what shipping teaches gets recaptured, closing the loop.

System skills keep the machine itself healthy; onboarding skills set it up. Skill names stay imperative verbs — the stages are categories, not prefixes. Cadence lives in [[#The Rhythm (cadence table)]].

## Shipped skills

### Capture

| Skill | Does |
|-------|------|
| [[10_Agents/skills/inbox-capture/SKILL\|inbox-capture]] | Write a new `02_Inbox/` note with correct frontmatter, filename, and collision handling |
| [[10_Agents/skills/daily-log/SKILL\|daily-log]] | Create or update today's daily log from the template |
| [[10_Agents/skills/solution-capture/SKILL\|solution-capture]] | Record a solved problem in `10_Agents/solutions/` |
| [[10_Agents/skills/research-to-resource/SKILL\|research-to-resource]] | Turn research into a `06_Resources/` note or zettel with provenance — *spans Capture + Distill: it captures and distills in one pass* |

### Organize

| Skill | Does |
|-------|------|
| [[10_Agents/skills/triage-inbox/SKILL\|triage-inbox]] | Process the Inbox for review: atomize, extract action items, classify, propose propagation edits |
| [[10_Agents/skills/periodic-review/SKILL\|periodic-review]] | Weekly/monthly/quarterly/yearly reviews — cadence is a parameter; *the weekly review is the vault's Organize heartbeat* |

### Distill

| Skill | Does |
|-------|------|
| [[10_Agents/skills/distill-note/SKILL\|distill-note]] | Reshape a note into an atomic zettel: core claim, summary layer, links, supersede by replacement |

### Express

| Skill | Does |
|-------|------|
| [[10_Agents/skills/vault-answer/SKILL\|vault-answer]] | Answer "what do I know about X?" from vault notes, with wikilink citations and capture offers for substantive answers |
| [[10_Agents/skills/express-packet/SKILL\|express-packet]] | Assemble an outbound packet (brief, outline, draft post/email) from vault notes into `02_Outbox/` with provenance; the owner ships |

### System

| Skill | Does |
|-------|------|
| [[10_Agents/skills/vault-maintenance/SKILL\|vault-maintenance]] | Run `brain validate`, fix findings, keep status/changelog current (mechanical integrity) |
| [[10_Agents/skills/curate/SKILL\|curate]] | Work the `brain curate` report: refresh, re-verify, propose archives/splits, semantic lint (epistemic integrity) |
| [[10_Agents/skills/link-repair/SKILL\|link-repair]] | Find and fix broken wikilinks using the index's repair hints |
| [[10_Agents/skills/merge-notes/SKILL\|merge-notes]] | Execute approved merges, splits, and renames: rewrite, retarget backlinks, archive, validate |
| [[10_Agents/skills/recommended-automations/SKILL\|recommended-automations]] | Wire inbound capture flows and rhythm jobs via the harness's scheduler |
| [[10_Agents/skills/self-maintenance/SKILL\|self-maintenance]] | Audit generated tooling: validate, prune, update, propose promotions |
| [[10_Agents/skills/sync-upstream/SKILL\|sync-upstream]] | Pull upstream template releases into the fork: detect via `template_version` + release tags, classify (machinery / owner content / canonical docs), apply per lane, backfill, report — pull-only, dry-run first |
| [[10_Agents/skills/self-improve/SKILL\|self-improve]] | The self-improving loop: observe friction (`brain report` trends, git history, triage outcomes, solution notes), propose single-topic spec changes (canonical docs by PR, else Inbox notes), record rejections, recur monthly — propose-only, never push upstream |

### Onboarding & environment

| Skill | Does |
|-------|------|
| [[10_Agents/skills/onboard-owner/SKILL\|onboard-owner]] | Guided first-run for a new (possibly non-technical) vault owner: teach by doing, fill the profile, orchestrate the other onboarding skills |
| [[10_Agents/skills/onboard-harness/SKILL\|onboard-harness]] | Symlink-first user-scope install into a harness + memory-file wiring + hook |
| [[10_Agents/skills/agent-orientation/SKILL\|agent-orientation]] | Discover reachable context sources and generate access tooling + capture skills |

## Recommended community skills

Vault-canonical skills live above. A separate, curated **links-only** catalog of recommended third-party/community skill and memory-file content — branch-tracked upstreams (installs the latest), license and trust notes, per-item owner sign-off against the fetched content — lives at [[06_Resources/recommended-skills]], backed by the machine-readable registry [[10_Agents/components/README|10_Agents/components/manifest.json]] (which also carries first-party overlays and vault-config presets). Community content installs to the harness's user scope via [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] and is never vendored into this directory.

## The Rhythm (cadence table)

**This table is the single source of truth for the vault's operating cadence.** [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] wires it into the harness's scheduler; [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] teaches it as "the rhythm"; [[00_Meta/conventions]] points here.

| Cadence | Skills | Trigger |
|---------|--------|---------|
| Daily | [[10_Agents/skills/daily-log/SKILL\|daily-log]] (+ any wired inbound capture flows) | First session of the day |
| Weekly | [[10_Agents/skills/triage-inbox/SKILL\|triage-inbox]] → [[10_Agents/skills/periodic-review/SKILL\|periodic-review]] (weekly) → Outbox sweep (flag lingering `02_Outbox/` packets) | End of week |
| Monthly | [[10_Agents/skills/periodic-review/SKILL\|periodic-review]] (monthly) + [[10_Agents/skills/vault-maintenance/SKILL\|vault-maintenance]] + [[10_Agents/skills/curate/SKILL\|curate]] + [[10_Agents/skills/self-improve/SKILL\|self-improve]] (spec retrospective) | Month end |
| Quarterly | [[10_Agents/skills/periodic-review/SKILL\|periodic-review]] (quarterly, updates the Now page) + [[10_Agents/skills/curate/SKILL\|curate]] + [[10_Agents/skills/self-maintenance/SKILL\|self-maintenance]] audit | Quarter end |
| Yearly | [[10_Agents/skills/periodic-review/SKILL\|periodic-review]] (yearly) | Year end |

Ad hoc, not scheduled: capture and retrieval ([[10_Agents/skills/inbox-capture/SKILL|inbox-capture]], [[10_Agents/skills/vault-answer/SKILL|vault-answer]], [[10_Agents/skills/express-packet/SKILL|express-packet]]) run when needed; surgery ([[10_Agents/skills/merge-notes/SKILL|merge-notes]]) runs on approval only; upstream syncing ([[10_Agents/skills/sync-upstream/SKILL|sync-upstream]]) runs when the owner asks to check for or adopt template releases.

## Rules

- Template-shipped skills are canonical ([[00_Meta/prd]] §9.3): changes need human approval.
- Agent-generated skills may be added here directly, tagged `workflow/draft` until the human promotes them; they must pass `brain validate` (which checks `name` = folder name and a non-empty `description`).
- Skills reference vault files by path and invoke `brain …`. A clean checkout uses `./brain` (POSIX) or `brain.cmd` (Windows); the universal fallback is `python3 10_Agents/tools/brain/brain.py …`. Managed installation is optional and preview-first (`brain install`).
