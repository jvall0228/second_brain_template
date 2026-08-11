---
name: recommended-automations
description: Propose and wire recurring ingestion flows — email digests, calendar context, chat capture — into 02_Inbox/ using this harness's own scheduling mechanism. Use after agent-orientation has established which sources exist, or when the owner asks for recurring capture.
title: "Skill: Recommended Automations"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
---

# Recommended Automations

Turn one-off capture into recurring flows the owner doesn't have to remember.

## Ground rules

- **Preference ladder** for each flow's source access (PRD §19 M7): (1) environment-specific custom tooling (CLI or MCP) → (2) first-party CLI → (3) first-party MCP server/connector.
- **Credentials never enter the repo** (PRD §16.2): schedules and scripts are committed; auth stays in the environment (CLI sessions, env vars, the harness's connector store).
- Every flow **writes through the `inbox-capture` rules** — dated kebab filenames, full frontmatter, `workflow/draft` — so triage stays uniform. Automations never write outside `02_Inbox/` except `daily-log` context flows, which follow that skill's rules.

## Recommended flows (adapt per owner)

| Flow | Cadence | Output |
|------|---------|--------|
| Email digest — flagged/starred + unanswered threads | daily | one Inbox note per digest |
| Calendar context — today's meetings, attendees, linked docs | each morning | section in today's daily log |
| Chat capture — saved/starred messages, action items from team chat | daily or weekly | Inbox notes per item |
| Meeting transcripts — new transcripts summarized with decisions/actions | per meeting or daily | one Inbox note per meeting |

## Scheduling mechanism per harness

Use the harness's own scheduler; fall back to system cron running the harness headless:

- **Claude Code** — Routines/scheduled tasks, or `claude -p "<skill prompt>"` from cron
- **Codex** — cloud scheduled tasks (RRULE), or `codex exec` from cron
- **Cursor** — Cloud Automations (cron)
- **opencode / Pi / Copilot / Muse Code** — no built-in scheduler: system cron + the harness's headless mode (`opencode run`, `pi -p`, `copilot -p`, `muse exec`)

Document each wired flow in the harness's context (what runs, when, writing what, where auth lives) as an Inbox note for owner review; the flow itself starts disabled/dry-run until the owner approves it.

## Steps

1. Read the orientation inventory note for adopted sources and priorities.
2. Propose flows (table above, pruned to real sources) with cadence and cost/noise notes — owner picks.
3. Wire each approved flow via the harness scheduler; first runs in dry-run mode producing a sample Inbox note.
4. Owner reviews samples → enable; register the flows with `self-maintenance` (it audits `10_Agents/` drafts and the documented flows).

## References

- `10_Agents/skills/inbox-capture/SKILL.md` — the write rules every flow obeys
- `10_Agents/harnesses/<name>/wiring.md` — per-harness invocation detail
