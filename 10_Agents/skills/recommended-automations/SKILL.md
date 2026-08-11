---
name: recommended-automations
description: Propose and wire any recurring vault operation via this harness's scheduler — inbound capture flows (email, calendar, chat) and rhythm jobs (scheduled triage, reviews, maintenance, curation). Use after agent-orientation has established sources, or when the owner asks for recurring capture or a scheduled rhythm.
title: "Skill: Recommended Automations"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Recommended Automations

**CODE stage:** System (outside the loop) — schedules the loop.

Turn recurring vault operations into scheduled flows the owner doesn't have to remember. Two families:

1. **Inbound flows** — external sources captured into the vault (email, calendar, chat, transcripts).
2. **Rhythm jobs** — headless invocations of the vault's own skills on cadence. **Source of truth: the cadence table in [[10_Agents/skills/README]] § The Rhythm** — this skill wires that table, never a private copy of it.

## Ground rules

- **Interface ranking ladder** for each flow's source access (PRD §8.4; full six-rung ladder in `agent-orientation`): (1) environment-specific custom tooling (CLI or MCP) → (2) first-party CLI → (3) first-party MCP server/connector → (4) vendor API wrapped in a generated tool → (5) browser automation, last resort → (6) none, recorded explicitly.
- **Credentials never enter the repo** (PRD §16.2): schedules and scripts are committed; auth stays in the environment (CLI sessions, env vars, the harness's connector store).
- **Every scheduled inbound run is persistence-gated immediately before access.** At a process boundary run `python3 10_Agents/tools/brain/brain.py remote-safety --persist --json` and proceed only when it exits `0` **and** returns `operationAllowed: true`; generated Python calls `require_remote_safety(..., persist=True)` at the same point. `block`, `unknown`, and local-only states make **zero connector calls and open zero output files**. Unattended jobs never use `--acknowledge-unknown`; they stop and report only the stable, redacted reason through the scheduler.
- Every inbound flow **writes through the `inbox-capture` rules** — dated kebab filenames, full frontmatter, `workflow/draft` — so triage stays uniform. **Inbound flows** never write outside `02_Inbox/` except `daily-log` context flows, which follow that skill's rules. Rhythm jobs instead write to each invoked skill's own home (reviews to `03_Journal/`, maintenance to `00_Meta/status.md`) — they inherit that skill's write posture, not the Inbox-only rule.
- **The unattended contract:** a scheduled run has nobody to ask. It executes only self-contained outcomes; anything needing judgment becomes a report note in the Inbox; its final output is the **deliverable** (the log entry, the report, the review draft) — never a plan, a question, or a request for input. Scheduled runs inherit the strictest write posture of the skills they invoke.
- **No automation ever ships from `02_Outbox/`** — the weekly sweep *flags* lingering packets; shipping stays the owner's act, always.

## Inbound flows (adapt per owner)

| Flow | Cadence | Output |
|------|---------|--------|
| Email digest — flagged/starred + unanswered threads | daily | one Inbox note per digest |
| Calendar context — today's meetings, attendees, linked docs | each morning | section in today's daily log |
| Chat capture — saved/starred messages, action items from team chat | daily or weekly | Inbox notes per item |
| Meeting transcripts — new transcripts summarized with decisions/actions | per meeting or daily | one Inbox note per meeting |

## Rhythm jobs (from the cadence table)

| Job | Cadence | Deliverable |
|-----|---------|-------------|
| Daily-log scaffold | daily | today's log created/updated per `daily-log` |
| Triage prep — triage-inbox through its report step | weekly | triage report in the Inbox (moves still wait for the owner) |
| Review draft — periodic-review for the closing period | weekly/monthly/quarterly/yearly | pre-filled review note, `workflow/draft` |
| Outbox sweep — list `02_Outbox/` packets older than a week | weekly | flag list in the triage report |
| Maintenance — vault-maintenance | monthly | fixes committed, findings reported |
| Curation — curate (no `--check-urls` unattended by default) | monthly/quarterly | curate report in the Inbox |
| Tooling audit — self-maintenance | quarterly | audit report |
| Spec retrospective — self-improve (Observe + drafted proposals only; owner review always waits for a human) | monthly | retrospective report + proposal notes in the Inbox, `workflow/needs-review` |

## Scheduling mechanism per harness

Use the harness's own scheduler; fall back to system cron running the harness headless:

- **Claude Code** — Routines/scheduled tasks, or `claude -p "<skill prompt>"` from cron
- **Codex** — cloud scheduled tasks (RRULE), or `codex exec` from cron
- **Cursor** — Cloud Automations (cron)
- **Copilot** — [gh-aw](https://github.github.com/gh-aw/reference/copilot-cloud-agent/) scheduled workflows or `gh agent-task` for cloud-agent flows; system cron + `copilot -p` locally
- **opencode / Pi / Muse Code** — no built-in scheduler: system cron + the harness's headless mode (`opencode run`, `pi -p`, `muse exec`)

Document each wired flow in the harness's context (what runs, when, writing what, where auth lives) as an Inbox note for owner review; the flow itself starts disabled/dry-run until the owner approves it.

## Steps

1. Read the **current environment's** orientation inventory note (`10_Agents/environments/<env-slug>/orientation-inventory.md` — see [[10_Agents/environments/README]]) for adopted sources, interface rungs, priorities, and the environment's permission envelope (never propose a flow the environment forbids); read the cadence table for the rhythm side.
2. Propose flows from both families (tables above, pruned to real sources and the owner's actual rhythm) with cadence and cost/noise notes — owner picks.
3. Wire each approved flow via the harness scheduler. For inbound flows, make the persistence preflight the first executable step before the connector or output path is opened, and test block, unknown, and local-only with connector/output spies. First runs in **dry-run mode** — inbound flows produce a sample Inbox note only after that gate passes; rhythm jobs produce their deliverable tagged `workflow/draft` — before anything is enabled.
4. Owner reviews samples → enable; register the flows with `self-maintenance` (it audits `10_Agents/` drafts and the documented flows).

## References

- [[10_Agents/skills/README]] § The Rhythm — the cadence table rhythm jobs implement
- `10_Agents/skills/inbox-capture/SKILL.md` — the write rules every inbound flow obeys
- `10_Agents/harnesses/<name>/wiring.md` — per-harness invocation detail
