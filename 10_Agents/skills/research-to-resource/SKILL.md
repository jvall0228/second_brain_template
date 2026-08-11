---
name: research-to-resource
description: Turn a research task into a durable reference note in 06_Resources/ (or an atomic zettel) with explicit provenance. Use when asked to research a topic for the vault — invocation directs the write to 06_Resources/.
title: "Skill: Research to Resource"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Research to Resource

**CODE stage:** Capture + Distill (boundary skill) — research is captured and distilled in one pass: provenance is the capture, the note shape is the distillation.

Convert research output into reference material that stays useful after the session ends.

## Steps

1. **Check for an existing home:** `python3 10_Agents/tools/brain/brain.py search <topic>` — extend an existing resource note (bump `updated:`) rather than fragmenting the topic across duplicates. This includes research that **corrects** an existing note: merge into the existing note's section, replacing what's now wrong (git keeps the history) and noting the re-verification date — do **not** publish a parallel "supersedes X" note and leave the stale original under a banner. A separate note is right only when the topic is genuinely distinct; a shared subject means a shared note.
2. **Pick the shape:**
   - Broad reference on a topic → `06_Resources/<kebab-topic>.md` from `09_Templates/template-resource.md`, tagged `type/resource`
   - One atomic, evergreen claim → `06_Resources/<kebab-claim>.md` from `09_Templates/template-zettel.md`, tagged `type/zettel`
   - Option comparison → `09_Templates/template-comparison.md`
3. **Write with provenance.** Every non-obvious claim carries its source; end the note with a `## Sources` section listing URLs/titles **with retrieval dates** — research decays, and the date tells future readers how stale it might be. Distinguish verified facts from your inference.
4. **Frontmatter:** real `title`, `updated:` today, `topic/*` tags for the subject, and `workflow/draft` — research stays draft until the human reviews it.
5. **Link it in:** wikilink related notes both ways where the related note is non-canonical (full paths across directories).
6. **Propagate:** research that extends, corrects, or contradicts *other* existing notes gets merged into those notes now, per step 1's merge rules (canonical targets → propose via Inbox instead). A source is fully ingested only when every note it touches reflects it — one source at a time, supervised.
7. **Validate and commit:** `python3 10_Agents/tools/brain/brain.py validate`, then commit.

## Rules

- Invoked research writes to `06_Resources/`; incidental findings mid-task still go through `inbox-capture`.
- Long raw dumps don't belong in the vault — distill; attach oversized source material under `08_Assets/` only if genuinely needed.
- **Respect `restricted/*`:** when research touches a note tagged `restricted/private`, link it — never quote or summarize its content into the resource note ([[00_Meta/conventions#Tag Namespaces]]; the operating-rules containment duty). Research output that is itself sensitive gets the tag on creation.
- **Merging is replacement, not accumulation.** Rewrite or delete the passages the new research conflicts with or obsoletes — never append a fresh section beside a stale one. The note must read as one coherent current state; its size should track knowledge, not edit count. Git history is the archive.
- **One topic, one note.** Notes are atomic: each covers exactly one subject, and each subject lives in exactly one note (sections for facets, wikilinks for relationships). Never let two notes share authority over the same facts — every reader and agent should find one place to look and one place to update.
- If session constraints force a temporary parallel note (e.g. the target is awaiting review), merging it back is unfinished work — flag it, don't normalize it.

## References

- `09_Templates/README.md` — template selection
- `06_Resources/README.md` — what belongs in Resources
