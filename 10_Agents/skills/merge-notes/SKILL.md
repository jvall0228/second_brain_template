---
name: merge-notes
description: Execute an approved merge, split, or rename/move of vault notes — rewrite content into one coherent whole, retarget inbound wikilinks via the index, archive superseded notes, validate. Use only after the human has approved a specific proposal (e.g. from vault-maintenance's duplication scan).
title: "Skill: Merge Notes"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Merge Notes

**CODE stage:** System (outside the loop).

Note surgery. Detection and proposal live elsewhere ([[10_Agents/skills/vault-maintenance/SKILL|vault-maintenance]]'s duplication scan, reviews); this skill only **executes what the human has already approved**, naming the exact notes involved.

## Merge — two or more notes share a subject

1. **Confirm the approval** names the survivor and the loser(s). No approval, no merge.
2. **Read every involved note in full** before touching any of them.
3. **Rewrite the survivor:** fold the losers' content in by replacement — conflicting or overlapping sections are rewritten into one current claim, never concatenated side by side or left under "supersedes" banners. The result must read as a single coherent note; git history is the archive for what was dropped.
4. **Retarget inbound links:** `brain links <loser> --json` lists each loser's backlinks; point every one at the survivor (or its matching section anchor), preserving display text.
5. **Archive the losers** to the matching `07_Archives/` subdirectory with `status/done` — their content now lives in the survivor.
6. **Finish:** bump `updated:` on every edited note, reindex, `validate --check-index` to zero errors, commit stating what merged into what.

## Split — one note has outgrown one topic

1. The approval names the note and the intended pieces (one subject each).
2. **Create one note per subject** from the right template, each self-contained with its share of the content; wire the pieces together with wikilinks.
3. **The original either becomes one of the pieces** (keeping its path for the subject it's best known for) or is emptied and archived.
4. **Re-point inbound links by intent:** each backlink goes to the piece its citing context actually meant — check the surrounding sentence, don't bulk-replace.
5. Finish as in merge step 6.

## Rename / move — the safe procedure

1. **Before moving:** `brain links <path>` — capture the backlink list first.
2. `git mv` the file (preserves history); update its `title:` if the name changed; bump `updated:`.
3. **Retarget every backlink** to the new path — cross-directory links need full paths (`[[06_Resources/new-name|Display]]`).
4. Reindex and `validate --check-index` — the index catches any straggler links — then commit the move and retargets as one change.

## Rules

- This skill never decides. It executes explicit approvals only; canonical notes additionally follow canonical change control.
- Replacement, never concatenation — the survivor reads as the current state of knowledge.
- Never drop content silently: anything deliberately not carried over gets a line in the commit message saying so.
- Leave the vault at zero errors; a half-done surgery (moved note, stale links) is worse than none.

## References

- [[10_Agents/skills/vault-maintenance/SKILL|vault-maintenance]] — where merge proposals come from
- [[10_Agents/skills/link-repair/SKILL|link-repair]] — fixing links outside a surgery context
- `10_Agents/tools/brain/README.md` — the `links` command
- [[10_Agents/docs/OPERATING-RULES]] — update by replacement; canonical handling
