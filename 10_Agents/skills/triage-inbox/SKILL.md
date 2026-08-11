---
name: triage-inbox
description: Process the 02_Inbox/ queue for human review — split multi-topic captures, extract action items, classify each note to a PARA destination, and propose updates to the existing notes each capture touches. Use when asked to triage, clean up, or process the Inbox — the skill proposes; the human approves.
title: "Skill: Triage Inbox"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Triage Inbox

**CODE stage:** Organize — takes Capture's output and files it into PARA; hands `type/zettel` items to Distill.

Turn the raw Inbox into a reviewed set of filing proposals. **Proposing is the skill; moving is the human's call.**

## Steps

1. **List the queue:** `python3 10_Agents/tools/brain/brain.py list --dir 02_Inbox --json` (skip `02_Inbox/README.md`).
2. **Atomize first.** A capture holding several unrelated topics gets split into one-topic notes *before* classification — each with its own frontmatter, the original emptied into its pieces. Splitting notes still inside the Inbox is within triage's write authority. (Capture stays zero-friction; the split belongs here, never at capture time.)
3. **Extract action items.** An actionable commitment found inside a capture → propose adding it to the matching project note's tasks, or propose a new project if none fits. The capture still files normally — the action item is copied out, not a reclassification.
4. **Classify each note:**
   - Actionable with a defined outcome → `04_Projects/<project>/`
   - Ongoing responsibility → `05_Areas/<area>/`
   - Reference material or evergreen idea → `06_Resources/` (atomic evergreen → `type/zettel`)
   - Personal experience, log, or reflection → the right `03_Journal/` subtree
   - Done or dead → `07_Archives/inbox/`
   - Solved-problem knowledge → `10_Agents/solutions/<category>/`
5. **Propagate.** A new source rarely touches only its own note: for each capture, find the existing notes whose claims it extends, corrects, or contradicts (`brain search` on its key terms) and propose those edits alongside the filing. Filing without propagation is how a vault drifts into self-contradiction.
6. **Hand zettels to [[10_Agents/skills/distill-note/SKILL|distill-note]].** Anything classified `type/zettel` gets reshaped by that skill (atomic claim, summary layer, links) before filing — procedure detail lives there, not here.
7. **Write a triage report** as a new Inbox note (use `inbox-capture`; slug `triage-report`): one table row per note — path, one-line summary, proposed destination, proposed filename (kebab-case), tag changes (e.g. drop `workflow/draft` on filing), action items found, propagation edits proposed, open questions.
8. **Present the report** to the human. Apply moves and propagation edits only after explicit approval, updating each edited note's `updated:` date and re-checking its wikilinks (cross-directory links need full paths — see `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md`). Propagation edits to `workflow/canonical` notes follow canonical change control even after triage approval.
9. After any approved changes: `python3 10_Agents/tools/brain/brain.py validate` and commit.

## References

- `02_Inbox/README.md` — the triage contract
- `00_Meta/conventions.md` — destinations and change control
- [[10_Agents/skills/distill-note/SKILL|distill-note]] — reshaping zettels at step 6
