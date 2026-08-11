---
name: triage-inbox
description: Classify the notes sitting in 02_Inbox/ and propose a PARA destination for each, for human review. Use when asked to triage, clean up, or process the Inbox — the skill proposes moves but never performs them.
title: "Skill: Triage Inbox"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
---

# Triage Inbox

Turn the raw Inbox into a reviewed set of filing proposals. **Proposing is the skill; moving is the human's call.**

## Steps

1. **List the queue:** `python3 10_Agents/tools/brain/brain.py list --dir 02_Inbox --json` (skip `02_Inbox/README.md`).
2. **Read each note** and classify it:
   - Actionable with a defined outcome → `04_Projects/<project>/`
   - Ongoing responsibility → `05_Areas/<area>/`
   - Reference material or evergreen idea → `06_Resources/` (atomic evergreen → `type/zettel`)
   - Personal experience, log, or reflection → the right `03_Journal/` subtree
   - Done or dead → `07_Archives/inbox/`
   - Solved-problem knowledge → `10_Agents/solutions/<category>/`
3. **Write a triage report** as a new Inbox note (use `inbox-capture`; slug `triage-report`): one table row per note — path, one-line summary, proposed destination, proposed filename (kebab-case), any tag changes (e.g. drop `workflow/draft` on filing), and open questions.
4. **Present the report** to the human. Apply moves only after explicit approval, updating each moved note's `updated:` date and re-checking its wikilinks (cross-directory links need full paths — see `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md`).
5. After any approved moves: `python3 10_Agents/tools/brain/brain.py validate` and commit.

## References

- `02_Inbox/README.md` — the triage contract
- `00_Meta/conventions.md` — destinations and change control
