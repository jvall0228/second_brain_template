---
name: triage-inbox
description: Process the 02_Inbox/ queue for human review — split multi-topic captures, extract action items, classify each note to a PARA destination, and propose updates to the existing notes each capture touches. Use when asked to triage, clean up, or process the Inbox — the skill proposes; the human approves.
title: "Skill: Triage Inbox"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# Triage Inbox

**CODE stage:** Organize — takes Capture's output and files it into PARA; hands `type/zettel` items to Distill.

Turn the raw Inbox into a reviewed set of filing proposals. **Proposing is the skill; moving is the human's call.**

Every capture triages to **both PARA and the Journal**: PARA is its topical home (step 4), and the periodic notes are its dated trace (step 6). A capture filed to a Project without a dated trace loses when it happened; a capture logged only to a daily note loses what it concerns.

## Steps

1. **List the queue:** `brain list --dir 02_Inbox --json` (skip `02_Inbox/README.md`).
2. **Atomize first.** A capture holding several unrelated topics gets split into one-topic notes *before* classification — each with its own frontmatter, the original emptied into its pieces. Split pieces keep the original's provenance fields (`00_Meta/CONVENTIONS.md` § Provenance): `author:` (harness identifier) and `session:` (session URL / PR / task reference) tell the reviewer at a glance which agent produced a capture and from what task — use them to judge trust and filter the queue; absence means human-authored or pre-convention. Splitting notes still inside the Inbox is within triage's write authority. (Capture stays zero-friction; the split belongs here, never at capture time.)
3. **Extract action items.** An actionable commitment found inside a capture → propose adding it to the matching Project entrypoint or supporting note, or propose a new Project if none fits. The capture still files normally — the action item is copied out, not a reclassification.
4. **Classify each note:**
   - Established work with a bounded outcome, completion criteria, one or more Areas, and a defensible target → `04_Projects/<project>/` as `status/active`
   - Established work intentionally paused by priority, dependency, or resources → `status/deprioritized` Project with no active target fields
   - Uncommitted possibility → `status/someday`, not an active Project
   - Ongoing responsibility → `05_Areas/<area>/`. Apply this test before the Project branches: work whose context has no completion date — a property, account, practice, or system being kept healthy — belongs to an Area even when the capture arrives as tasks and outcomes; carve the bounded piece out as a Project mapped to that Area rather than filing the whole context as one
   - Reference material or evergreen idea → `06_Resources/` (atomic evergreen → `type/zettel`)
   - Personal experience, log, or reflection → the right `03_Journal/` subtree
   - Done or dead → `07_Archives/inbox/`
   - Solved-problem knowledge → `10_Agents/solutions/<category>/`
5. **Respect `restricted/*`.** A capture tagged `restricted/private` (or splitting out of one) keeps the tag through triage. A bare link to it propagates nothing, but any report row, split piece, or propagation edit that copies, summarizes, or transforms its private substance carries `restricted/private` too — keep the report non-restricted by holding its rows to path, proposed destination, and tag changes, and call out every tag flip a proposed edit would cause. See [CONVENTIONS](../../../00_Meta/CONVENTIONS.md#restrictedprivate).
6. **Propagate.** A new source rarely touches only its own note: for each capture, find the existing notes whose claims it extends, corrects, or contradicts (`brain search` on its key terms) and propose those edits alongside the filing. Filing without propagation is how a vault drifts into self-contradiction. Propagation has two kinds of target:
   - **Topical:** the notes the search finds.
   - **Temporal:** the daily note for the capture's **event date** (`03_Journal/periodic/daily/YYYY-MM-DD.md`) and the weekly note for its ISO week and ISO week-year (`03_Journal/periodic/weekly/YYYY-W##-review.md` — `brain trace` computes it, so 2027-01-01 lands in `2026-W53`). The event date is the date in the capture's filename unless the capture states the date it describes; never the triage date — triage is batched, and logging on the triage day piles every capture onto one entry. The daily entry is one line under `### Activity Log` linking the filed destination; the weekly entry is a line under `## Get Clear` from the capture's summary and, for Project or Area filings, a line under the matching `## Get Current` section. Each entry carries the capture's identity (its original Inbox path) as an HTML comment, which is what makes re-application a no-op. Daily and weekly only — monthly and quarterly roll up from weeklies through [periodic-review](../periodic-review/SKILL.md).
7. **Hand zettels to [distill-note](../distill-note/SKILL.md).** Anything classified `type/zettel` gets reshaped by that skill (atomic claim, summary layer, links) before filing — procedure detail lives there, not here.
8. **Write a triage report** as a new Inbox note (use `inbox-capture`; slug `triage-report`): one table row per note — path, one-line summary, proposed destination, proposed filename (kebab-case), tag changes (including `project/*` or `area/*` membership), action items, propagation edits, periodic entries (the daily and weekly targets from step 6, so an empty Journal trace is visible to the reviewer), and open questions. A proposed active Project also shows proposed Areas, completion criteria, target, and whether the date is owner-confirmed or agent-estimated.
9. **Present the report** to the human. Apply moves and propagation edits only after explicit approval, updating each edited note's `updated:` date and re-checking its source-relative Markdown links (see `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md`). Propagation edits to `workflow/canonical` notes follow canonical change control even after triage approval.
10. **Apply.** After approved relationship or lifecycle changes, run `brain projects --write-rollups`. Write the approved periodic entries in the same application with `brain trace --date <event date> --destination <filed path> --summary "<row summary>" --id <original Inbox path> [--kind project|area] --write`, once per approved row (spec §29.2): it creates the daily and weekly notes from their templates when the event date has none (historical dates included — this is the backfill interface [daily-log](../daily-log/SKILL.md) delegates to, so triage never writes a periodic note by hand), appends the entries under the right sections, dedupes on the capture identity (two captures filed to one destination on one day both land; re-running the same row adds nothing), and traces a `restricted/private` destination by bare title link only. Proposed filings never touch periodic notes; only approved ones do. Require zero new Project/Area membership or lifecycle warnings. When every approved row is applied, roll the report into the month's triage log **before** the final validation: `brain triage-archive 02_Inbox/<report>.md --write` (spec §29.1) appends the report body under a `## YYYY-MM-DD — <report title>` heading with a `*Run: <author>, <session>*` provenance line and an identity marker to `07_Archives/inbox/YYYY-MM-triage-log.md` (creating the month's log with `type/log`, `status/done`, `audience/agent`, `audience/human` when there is none), with the document H1 dropped, every other heading demoted one level, and every relative link rebased to the log's directory — then deletes the Inbox report. The append and the delete are retry-safe: an interrupted run finishes on the next invocation without a second copy, and re-running an archived report changes nothing. A report tagged `restricted/private` is moved as its own note under `07_Archives/inbox/` (`workflow/draft`/`workflow/review` replaced by `status/done`, links rebased) so the month's log stays non-restricted. The command ends by validating the resulting corpus; then run `brain validate` yourself and commit application, rollup, and deletion together. Either way a triage report never re-enters the queue; only a report with rows still awaiting approval stays in `02_Inbox/`. Reports archived before this rule stay as they are.

## References

- `02_Inbox/README.md` — the triage contract
- `00_Meta/CONVENTIONS.md` — destinations and change control
- [distill-note](../distill-note/SKILL.md) — reshaping zettels at step 7
- [Project and Area Contract](../../docs/project-area-contract.md) — canonical entity, membership, lifecycle, and target rules
- [daily-log](../daily-log/SKILL.md) — today's daily note; historical event dates go through `brain trace` (step 10)
- `10_Agents/tools/brain/README.md` — `brain trace` and `brain triage-archive` (spec §29)
- `03_Journal/periodic/README.md` — periodic note naming
