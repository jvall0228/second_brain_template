---
name: link-repair
description: Find and fix broken or fragile relative Markdown links using the brain index's resolution data and repair hints. Use when validate reports unresolved links, after files move or rename, or on request.
title: "Skill: Link Repair"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Link Repair

**CODE stage:** System (outside the loop).

Drive unresolved internal links to zero without guessing.

## Steps

1. **Find breakage:** `brain validate --json` — collect `unresolved-link` errors (each carries the note, line, raw link, and any `title matches:` hint) plus `ambiguous-link` / `case-mismatch` warnings.
2. **Diagnose each link** with `brain links <note>` and `brain search`:
   - **Title-match hint present** → the link text is a note's *title*, not its filename; retarget to the hinted path.
   - **File was moved/renamed** → `git log --follow` or `brain search` for the content; retarget.
   - **Incomplete filename** (for example `2024-01.md` when the file is `2024-01-review.md`) → use the exact filename.
   - **Target genuinely gone** → don't invent a target; list it for the human (or convert to plain text if clearly dead).
3. **Rewrite using safe patterns** (from `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md`):
   - Same directory → sibling destination: `[2026-08-10](2026-08-10.md)`
   - Child directory → `[Decision](decision-records/example-decision.md)`
   - Parent/cross-tree → source-relative `../` path: `[Lessons Learned](../../06_Resources/lessons-learned.md)`
   - Heading/self link → GitHub slug: `[Tag namespaces](../../00_Meta/CONVENTIONS.md#tag-namespaces)` / `[Details](#details)`
   - Spaces or Unicode → UTF-8 percent-encoded destination: `[Café](caf%C3%A9%20notes.md)`
   - Ambiguity warnings → identify the intended target from context, then use its exact relative path; never choose the first candidate
4. **Preserve the human label, fragment, image/embed meaning, and target type** when retargeting; bump each edited note's `updated:`.
5. **Verify:** re-run `validate` — zero unresolved links, and no new warnings introduced. Commit with a message listing what was retargeted.

## Rules

- Never "fix" a link by deleting it silently.
- Links inside code spans/fences are exempt by design — leave them alone.

## References

- `10_Agents/solutions/obsidian-issues/wikilink-resolution-rules.md` — portable resolution rules and safe patterns
- `10_Agents/tools/brain/SPEC.md` §6 — exactly how links resolve
