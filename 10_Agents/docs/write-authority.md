---
title: "Write Authority Contract"
tags:
  - type/meta
  - audience/agent
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# Write Authority Contract

Write authority follows **execution class**. This note is the single full statement; [AGENTS § Where Agents Write](../../AGENTS.md#where-agents-write) carries the summary table and every other document points here. Moved out of AGENTS on 2026-09-04 (bootstrap budget); the contract text is unchanged.

**Execution class.** Every run is **interactive** or **autonomous**. The class comes from execution mode, not owner presence: an interactive session is a foreground, user-directed conversation; scheduled, headless, recurring, and automation-driven runs are autonomous. Missing trusted execution metadata defaults to **autonomous**. The owner temporarily stepping away does not change an established class. Subagents inherit the parent session's class but act only within the scope the parent delegated.

## Execution Classes

**Interactive sessions** may directly create or edit any appropriate non-generated vault location — including `workflow/canonical` notes — when the change is reasonably required by the current user-directed task. This removes file-by-file approval, not task scope. Canonical changes still receive a scoped diff, required validation, and a [CHANGELOG](../../00_Meta/CHANGELOG.md) entry when the canonical contract calls for one.

**Autonomous sessions** are review-gated: new vault content goes to **`02_Inbox/`** (the **Inbox-first rule** — a human triages it into the appropriate PARA directory), and existing notes change only through the named standing exceptions below.

**Either class:** deliverables **for the world** (briefs, outlines, draft posts/emails) go to **`02_Outbox/`** via [express-packet](../skills/express-packet/SKILL.md) — the owner reviews and ships; **agents never ship** (see [README](../../02_Outbox/README.md)). Generated files remain owned by their generators regardless of class: edit the source of truth and run the owning regeneration command, never hand-edit generated output. The append-only skill-run log `10_Agents/docs/skill-runs.log` is generated output in this sense: only the harness hooks (`10_Agents/harnesses/<harness>/skill-run-log.*`, wired by the harness's settings) append to it, as a mechanical record of tool use; no agent writes it by hand in either class.

## Standing Exceptions

Standing exceptions (the edits autonomous sessions may make to existing content):

- Agents may append solution notes to `10_Agents/solutions/` — see [README](../README.md) — and rejection rows to the append-only log `10_Agents/docs/rejected-proposals.md` (the self-improve loop's memory).
- `brain {aymt,home} --write` owns its generated `00_Meta/` file; `brain projects --write-rollups` owns each Area's `## Active Projects`; generic/hand edits remain forbidden.
- `brain artifacts --write` alone owns the three generated files in `08_Assets/artifacts/README.md`; generic writes and hand edits are forbidden.
- Notify: [contract](../skills/configure-notifications/SKILL.md).
- A live, user-invoked [agent-orientation](../skills/setup/agent-orientation/SKILL.md) session may write draft outputs to `10_Agents/environments/<env-slug>/`, `10_Agents/tools/<source>/`, and `10_Agents/skills/<source>-capture/`. Markdown uses `workflow/draft`; other bundle files inherit it until owner promotion.
- During a live [onboard-owner](../skills/setup/onboard-owner/SKILL.md) session, agents write interview results directly to `01_Profile/`, `03_Journal/people/` (owner-confirmed people notes), `04_Projects/`, and `05_Areas/` — and, in its context-specialization stage, rewrite the periodic templates in `09_Templates/` from `09_Templates/variants/` and record `context:` in `00_Meta/config.yaml`. The owner's in-the-moment approval is the review. Outside that session, the execution-class contract above applies as usual.

## Append-only agent logs

Three append-only logs under `10_Agents/docs/` hold agent memory, and only one of them is an autonomous exception:

| Log | Interactive | Autonomous |
|-----|-------------|------------|
| `rejected-proposals.md` | append | append (standing exception above) |
| `accepted-proposals.md` | append | rows go in the run's retrospective report in `02_Inbox/` under `## Accepted proposals`; triage runs `brain accepted --ingest <report> --write` |
| `vault-answer-gaps.md` | `brain gap --write` appends | `brain gap --inbox --write` writes an Inbox capture; triage runs `brain gap --ingest <capture> --write` |

A gap whose question or nearest notes are `restricted/private` never enters the public queue in either class: `brain gap` writes a `restricted/private` Inbox capture, and only an explicit `--ingest --declassify` at triage moves the row into the public queue. Both ingestion commands are idempotent (identity markers for gap rows, exact-row identity for acceptance rows), so a re-triaged capture adds nothing (spec §29.3–§29.4). The `research-to-resource` tick that closes a gap row follows the same table (interactive: tick; autonomous: note the fill in the Inbox capture). Autonomous mutation of existing notes is otherwise unchanged: everything else goes through the Inbox.

## Canonical-by-policy

Template-shipped skills/tools, `00_Meta/config.yaml`, and named tagless entrypoint/editor/harness adapters are **canonical-by-policy** and use canonical change control. Location alone does not confer that state; orientation bundles stay draft until owner promotion.

## Related

- [AGENTS](../../AGENTS.md#where-agents-write) — the bootstrap summary
- [Inbox README](../../02_Inbox/README.md) — triage instructions
