---
title: "Agent Skills"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - workflow/canonical
updated: 2026-08-12
expires: 2027-08-11
---

# Agent Skills

Harness-agnostic skills in the [Agent Skills format](https://agentskills.io): one folder per skill containing a `SKILL.md` whose frontmatter carries the standard `name` + `description` **plus** the vault contract (`title`, `tags`, `updated`) — a superset; harnesses ignore the extra keys, and `brain validate` enforces both contracts.

Harnesses that scan the shared `.agents/skills/` path (or `.claude/skills/` for Claude Code) consume these unchanged — the [onboard-harness](onboard-harness/SKILL.md) skill symlinks them into a harness's user config.

## The CODE Loop in This Vault

The catalog is organized by the CODE method — **C**apture → **O**rganize → **D**istill → **E**xpress — the loop knowledge travels through this vault:

- **Capture** lands raw material in `02_Inbox/` with zero friction.
- **Organize** triages it into PARA (`04_Projects/` … `07_Archives/`).
- **Distill** sharpens filed notes into atomic, evergreen claims (`type/zettel` in `06_Resources/`).
- **Express** turns vault knowledge into answers and outbound packets (`02_Outbox/`) — and what shipping teaches gets recaptured, closing the loop.

System skills keep the machine itself healthy; onboarding skills set it up. Skill names stay imperative verbs — the stages are categories, not prefixes. Cadence lives in [The Rhythm (cadence table)](#the-rhythm-cadence-table).

## Shipped skills

### Capture

| Skill | Does |
|-------|------|
| [inbox-capture](inbox-capture/SKILL.md) | Write a new `02_Inbox/` note with correct frontmatter, filename, and collision handling |
| [daily-log](daily-log/SKILL.md) | Create or update today's daily log from the template |
| [solution-capture](solution-capture/SKILL.md) | Record a solved problem in `10_Agents/solutions/` |
| [research-to-resource](research-to-resource/SKILL.md) | Turn research into a `06_Resources/` note or zettel with provenance — *spans Capture + Distill: it captures and distills in one pass* |

### Organize

| Skill | Does |
|-------|------|
| [triage-inbox](triage-inbox/SKILL.md) | Process the Inbox for review: atomize, extract action items, classify, propose propagation edits |
| [periodic-review](periodic-review/SKILL.md) | Weekly/monthly/quarterly/yearly reviews — cadence is a parameter; *the weekly review is the vault's Organize heartbeat* |

### Distill

| Skill | Does |
|-------|------|
| [distill-note](distill-note/SKILL.md) | Reshape a note into an atomic zettel: core claim, summary layer, links, supersede by replacement |

### Express

| Skill | Does |
|-------|------|
| [vault-answer](vault-answer/SKILL.md) | Answer "what do I know about X?" from vault notes, with relative Markdown citations and capture offers for substantive answers |
| [express-packet](express-packet/SKILL.md) | Assemble an outbound packet (brief, outline, draft post/email) from vault notes into `02_Outbox/` with provenance; the owner ships |

### System

| Skill | Does |
|-------|------|
| [vault-maintenance](vault-maintenance/SKILL.md) | Run `brain validate`, fix findings, keep status/changelog current (mechanical integrity) |
| [aymt](aymt/SKILL.md) | Rank tracked local signals into a reviewable 5–7-action brief; preview by default, dedicated exact-file write only on request |
| [refresh-home](refresh-home/SKILL.md) | Preview or explicitly refresh the generated local Home from structured AYMT and safe tracked navigation/health data |
| [generate-artifacts](generate-artifacts/SKILL.md) | Generate, check, and locally open the offline link graph and health dashboard from privacy-filtered tracked metadata |
| [configure-notifications](configure-notifications/SKILL.md) | Configure, preview, inspect, and locally file-test push-only private owner notifications; real-provider sends remain owner-gated and unimplemented |
| [curate](curate/SKILL.md) | Work the `brain curate` report: refresh, re-verify, propose archives/splits, semantic lint (epistemic integrity) |
| [link-repair](link-repair/SKILL.md) | Find and fix broken relative Markdown links using the index's repair hints |
| [merge-notes](merge-notes/SKILL.md) | Execute approved merges, splits, and renames: rewrite, retarget backlinks, archive, validate |
| [recommended-automations](recommended-automations/SKILL.md) | Wire inbound capture flows and rhythm jobs via the harness's scheduler |
| [self-maintenance](self-maintenance/SKILL.md) | Audit generated tooling: validate, prune, update, propose promotions |
| [sync-upstream](sync-upstream/SKILL.md) | Pull upstream template releases into the fork: detect via `template_version` + release tags, classify (machinery / owner content / canonical docs), apply per lane, backfill, report — pull-only, dry-run first |
| [self-improve](self-improve/SKILL.md) | The self-improving loop: observe friction (`brain report` trends, git history, triage outcomes, solution notes), propose single-topic spec changes (canonical docs by PR, else Inbox notes), record rejections, recur monthly — propose-only, never push upstream |

### Onboarding & environment

| Skill | Does |
|-------|------|
| [onboard-owner](onboard-owner/SKILL.md) | Guided first-run for a new (possibly non-technical) vault owner: teach by doing, fill the profile, orchestrate the other onboarding skills |
| [onboard-harness](onboard-harness/SKILL.md) | Symlink-first user-scope install into a harness + memory-file wiring + hook |
| [agent-orientation](agent-orientation/SKILL.md) | Discover reachable context sources and generate access tooling + capture skills |

## Recommended community skills

Vault-canonical skills live above. A separate, curated **links-only** catalog of recommended third-party/community skill and memory-file content — branch-tracked upstreams (installs the latest), license and trust notes, per-item owner sign-off against the fetched content — lives at [recommended-skills](../../06_Resources/recommended-skills.md), backed by the machine-readable registry [10_Agents/components/manifest.json](../components/README.md) (which also carries first-party overlays and vault-config presets). Community content installs to the harness's user scope via [onboard-harness](onboard-harness/SKILL.md) and is never vendored into this directory.

## The Rhythm (cadence table)

**This table is the single source of truth for the vault's operating cadence.** [recommended-automations](recommended-automations/SKILL.md) wires it into the harness's scheduler; [onboard-owner](onboard-owner/SKILL.md) teaches it as "the rhythm"; [CONVENTIONS](../../00_Meta/CONVENTIONS.md) points here.

| Cadence | Skills | Trigger |
|---------|--------|---------|
| Daily | [daily-log](daily-log/SKILL.md) (+ any wired inbound capture flows) | First session of the day |
| Weekly | [triage-inbox](triage-inbox/SKILL.md) → [periodic-review](periodic-review/SKILL.md) (weekly) → Outbox sweep (flag lingering `02_Outbox/` packets) | End of week |
| Monthly | [periodic-review](periodic-review/SKILL.md) (monthly) + [vault-maintenance](vault-maintenance/SKILL.md) + [curate](curate/SKILL.md) + [self-improve](self-improve/SKILL.md) (spec retrospective) | Month end |
| Quarterly | [periodic-review](periodic-review/SKILL.md) (quarterly, updates the Now page) + [curate](curate/SKILL.md) + [self-maintenance](self-maintenance/SKILL.md) audit | Quarter end |
| Yearly | [periodic-review](periodic-review/SKILL.md) (yearly) | Year end |

Ad hoc, not scheduled: capture and retrieval ([inbox-capture](inbox-capture/SKILL.md), [vault-answer](vault-answer/SKILL.md), [express-packet](express-packet/SKILL.md)) run when needed; notification setup/testing ([configure-notifications](configure-notifications/SKILL.md)) is owner-invoked; surgery ([merge-notes](merge-notes/SKILL.md)) runs on approval only; upstream syncing ([sync-upstream](sync-upstream/SKILL.md)) runs when the owner asks to check for or adopt template releases.

## Rules

- Template-shipped skills are canonical ([PRD](../../00_Meta/PRD.md) §9.3): changes need human approval.
- Agent-generated skills may be added here directly, tagged `workflow/draft` until the human promotes them; they must pass `brain validate` (which checks `name` = folder name and a non-empty `description`).
- Skills reference vault files by path and invoke `brain …`. A clean checkout uses `./brain` (POSIX) or `brain.cmd` (Windows); the universal fallback is `python3 10_Agents/tools/brain/brain.py …`. Managed installation is optional and preview-first (`brain install`).
