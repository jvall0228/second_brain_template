---
name: link-repair
description: Find and fix broken or fragile wikilinks using the brain index's resolution data and repair hints. Use when validate reports unresolved links, after files move or rename, or on request.
title: "Skill: Link Repair"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
---

# Link Repair

Drive unresolved wikilinks to zero without guessing.

## Steps

1. **Find breakage:** `python3 10_Agents/tools/brain/brain.py validate --json` — collect `unresolved-link` errors (each carries the note, line, raw link, and any `title matches:` hint) plus `ambiguous-link` / `case-mismatch` warnings.
2. **Diagnose each link** with `brain links <note>` and `brain search`:
   - **Title-match hint present** → the link text is a note's *title*, not its filename; retarget to the hinted path.
   - **File was moved/renamed** → `git log --follow` or `brain search` for the content; retarget.
   - **Partial filename** (e.g. `[[2024-01]]` for `2024-01-review.md`) → use the full filename.
   - **Target genuinely gone** → don't invent a target; list it for the human (or convert to plain text if clearly dead).
3. **Rewrite using safe patterns** (from `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md`):
   - Same directory → bare filename: `[[2026-08-10]]`
   - Across directories → full path with display text: `[[03_Journal/insights/lessons-learned|Lessons Learned]]`
   - Ambiguous bare names (`ambiguous-link` warnings) → replace with the full path of the intended target
4. **Preserve display text** (`[[target|Display]]`) when retargeting; bump each edited note's `updated:`.
5. **Verify:** re-run `validate` — zero unresolved links, and no new warnings introduced. Commit with a message listing what was retargeted.

## Rules

- Never "fix" a link by deleting it silently.
- Links inside code spans/fences are exempt by design — leave them alone.

## References

- `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md` — resolution rules and safe patterns
- `10_Agents/tools/brain/spec.md` §6 — exactly how links resolve
