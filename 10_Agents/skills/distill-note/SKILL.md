---
name: distill-note
description: Reshape an existing vault note into an atomic evergreen zettel — extract the core claim, add a summary layer, wire links, supersede the original by replacement. Use when triage classifies a note type/zettel, or when graduating a Journal idea into Resources.
title: "Skill: Distill Note"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Distill Note

**CODE stage:** Distill.

Distillation here is structural, not decorative: a captured note becomes an atomic, evergreen claim that a future reader — human or agent — can build on without the original context.

## Steps

1. **Read the source note and find the atomic claim** — the one idea the note exists to carry. If it carries several independent claims, it needs atomizing first (one claim per note; at triage that's [[10_Agents/skills/triage-inbox/SKILL|triage-inbox]]'s job), then distill each piece.
2. **Check for an existing home:** `python3 10_Agents/tools/brain/brain.py search "<claim terms>"` — if a zettel or resource note already covers this claim, merge into it (update by replacement) instead of minting a duplicate. One topic, one note. If that existing note is `workflow/canonical`, propose the merge via Inbox rather than editing it directly (canonical change control still applies, even on the owner-direct path).
3. **Reshape onto [[09_Templates/template-zettel|template-zettel]]:**
   - Title = the claim itself, stated declaratively ("Index-first retrieval beats embeddings at personal scale"), never a topic label ("Retrieval notes").
   - The body opens with a **summary layer**: 1–3 sentences stating the claim and why it matters, readable entirely on its own.
   - Below it, supporting detail — evidence, examples, caveats — distilled from the source, not pasted wholesale.
   - `## Source`: where the claim came from — a wikilink if the originating note survives, external sources with retrieval dates otherwise.
4. **Wire links:** `## Related` wikilinks to notes this claim supports, contradicts, or depends on; add the reverse links in those notes where they're non-canonical.
5. **Supersede by replacement** — never leave two notes claiming authority over the same idea:
   - An Inbox capture fully absorbed by the zettel is done: propose archiving it in the triage report.
   - A graduating Journal entry stays (logs are events, not claims) but gains a wikilink to the zettel; the zettel now owns the claim.
6. **Frontmatter and destination:** `type/zettel`, `workflow/draft` until reviewed, filed to `06_Resources/` (the zettel home) through normal triage approval. Then `python3 10_Agents/tools/brain/brain.py validate`.

## Rules

- Distilled means shorter and sharper — if the zettel is as long as its source, it isn't distilled yet.
- The summary layer asserts; the body supports. Keep the claim separable from its evidence.
- Invoked at triage, filing follows the triage report's approval gate; invoked directly by the owner, their direction is the review.

## References

- [[09_Templates/template-zettel]] — the target shape
- [[10_Agents/skills/triage-inbox/SKILL|triage-inbox]] — the main caller
- [[10_Agents/skills/research-to-resource/SKILL|research-to-resource]] — distills at research time; this skill distills after capture
- [[10_Agents/docs/operating-rules]] — update by replacement
