---
name: triage-inbox
description: Process the 02_Inbox/ queue for human review — split multi-topic captures, extract action items, classify each note to a PARA destination, and propose updates to the existing notes each capture touches. Use when asked to triage, clean up, or process the Inbox — the skill proposes; the human approves.
title: "Skill: Triage Inbox"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-27
expires: 2027-08-11
---

# Triage Inbox

**CODE stage:** Organize — takes Capture's output and files it into PARA; hands `type/zettel` items to Distill.

Turn the raw Inbox into a reviewed set of filing proposals. **Proposing is the skill; moving is the human's call.**

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
6. **Propagate.** A new source rarely touches only its own note: for each capture, find the existing notes whose claims it extends, corrects, or contradicts (`brain search` on its key terms) and propose those edits alongside the filing. Filing without propagation is how a vault drifts into self-contradiction.
7. **Hand zettels to [distill-note](../distill-note/SKILL.md).** Anything classified `type/zettel` gets reshaped by that skill (atomic claim, summary layer, links) before filing — procedure detail lives there, not here.
8. **Write a triage report** as a new Inbox note (use `inbox-capture`; slug `triage-report`): one table row per note — path, one-line summary, proposed destination, proposed filename (kebab-case), tag changes (including `project/*` or `area/*` membership), action items, propagation edits, and open questions. A proposed active Project also shows proposed Areas, completion criteria, target, and whether the date is owner-confirmed or agent-estimated.
9. **Present the report** to the human. Apply moves and propagation edits only after explicit approval, updating each edited note's `updated:` date and re-checking its source-relative Markdown links (see `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md`). Propagation edits to `workflow/canonical` notes follow canonical change control even after triage approval.
10. After approved relationship or lifecycle changes, run `brain projects --write-rollups`; then `brain validate` and commit. Require zero new Project/Area membership or lifecycle warnings. When the approved application is committed, archive the report itself in the same commit — move it to `07_Archives/inbox/`, replacing `workflow/draft`/`workflow/review` with `status/done` — so a triage report never re-enters the queue; only a report with rows still awaiting approval stays in `02_Inbox/`.

## References

- `02_Inbox/README.md` — the triage contract
- `00_Meta/CONVENTIONS.md` — destinations and change control
- [distill-note](../distill-note/SKILL.md) — reshaping zettels at step 7
- [Project and Area Contract](../../docs/project-area-contract.md) — canonical entity, membership, lifecycle, and target rules
