---
name: vault-answer
description: Answer "what do I know about X?" from the vault, with relative Markdown citations and a clear line between vault knowledge and model knowledge. Use when the user asks what the vault says or knows about a topic, project, person, or decision.
title: "Skill: Vault Answer"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Vault Answer

**CODE stage:** Express — vault knowledge leaves as cited answers; substantive ones are recaptured (Express → Capture).

Retrieval discipline for questions the vault should answer. The vault is the source of truth; the model's own knowledge is a clearly labeled supplement, never a silent substitute.

## Steps

1. **Search the vault, in order** — stop as soon as you have enough to answer:
   1. `brain search "<term>"` — title and full-text hits (try synonyms and abbreviations too).
   2. [INDEX](../../../00_Meta/INDEX.md) and the relevant directory READMEs — where a topic *should* live, even if search missed it.
   3. `grep` across the vault — phrasings the index search didn't catch.
2. **Read the notes you found.** Answer from note content, never from search snippets or filenames alone.
3. **Cite every vault claim with a source-relative Markdown link** to the note it came from, e.g. the [harness research](../../../06_Resources/harness-primitives-research.md) says… when writing from a skill directory. An answer without citations is an answer the human can't verify or follow.
4. **Keep vault knowledge and model knowledge separate.** If you supplement with general knowledge, label it explicitly ("the vault doesn't cover this, but generally…"). Check freshness while reading: if a note looks stale (`updated:` long ago for a volatile topic), say so alongside the answer.
5. **Offer to capture substantive answers** — answers are assets. If answering took real synthesis (a comparison, a cross-note summary, a decision input), offer to save it to `02_Inbox/` via [inbox-capture](../inbox-capture/SKILL.md) so the exploration compounds instead of evaporating in chat. Skip the offer for simple lookups.
6. **Treat unanswerable as a capture opportunity.** If the vault has nothing (or only stale material), say so plainly and offer to fill the gap via [research-to-resource](../research-to-resource/SKILL.md).

## Rules

- Never present model knowledge as vault knowledge — the separation in step 4 is mandatory, not stylistic.
- If two vault notes conflict, don't silently pick one: present both with the conflict flagged, and follow the Stuck/Escalation Protocol in [OPERATING-RULES](../../docs/OPERATING-RULES.md) so the conflict gets resolved in the notes, not just in chat.
- Captured answers follow the Inbox-first rule and normal triage — this skill never files directly to PARA directories.

## References

- `10_Agents/tools/brain/README.md` — the search/index CLI
- [INDEX](../../../00_Meta/INDEX.md) — the vault map, for step 1
- [inbox-capture](../inbox-capture/SKILL.md) — capturing offered answers
- [research-to-resource](../research-to-resource/SKILL.md) — filling gaps
- [OPERATING-RULES](../../docs/OPERATING-RULES.md) — escalation on conflicting sources
