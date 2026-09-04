---
name: vault-answer
description: Answer "what do I know about X?" from the vault, with relative Markdown citations and a clear line between vault knowledge and model knowledge. Use when the user asks what the vault says or knows about a topic, project, person, or decision.
title: "Skill: Vault Answer"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# Vault Answer

**CODE stage:** Express — vault knowledge leaves as cited answers; substantive ones are recaptured (Express → Capture).

Retrieval discipline for questions the vault should answer. The vault is the source of truth; the model's own knowledge is a clearly labeled supplement, never a silent substitute.

## Steps

1. **Search the vault, in order** — stop as soon as you have enough to answer:
   1. For Project status, portfolio, target, or Area-ownership questions, start with `brain projects --json`, then read the cited `PROJECT.md` and `AREA.md` entrypoints. It is the canonical entity inventory; NOW is only a priority view.
   2. Otherwise, `brain search --semantic "<question>"` — ranks whole notes by meaning, hybrid with keyword hits; with no embeddings sidecar (`brain embed --status`) it degrades to plain keyword search by itself, so it is always safe to run first.
   3. `brain search "<term>"` — exact title and full-text hits for the key terms, synonyms, and abbreviations; the substring pass catches what ranking buried.
   4. [INDEX](../../../00_Meta/INDEX.md) and the relevant directory READMEs — where a topic *should* live, even if search missed it.
   5. `grep` across the vault — phrasings neither search caught.
2. **Read the notes you found.** Answer from note content, never from search snippets or filenames alone. Query results carry each note's privacy classification — a `restricted` boolean on JSON rows, a `[restricted]` label in human-readable output; restricted notes are fully usable here, but keep the classification attached to what you take from them.
3. **Cite every vault claim with a source-relative Markdown link** to the note it came from, e.g. the [harness research](../../../06_Resources/harness-primitives-research.md) says… when writing from a skill directory. An answer without citations is an answer the human can't verify or follow.
4. **Keep vault knowledge and model knowledge separate.** If you supplement with general knowledge, label it explicitly ("the vault doesn't cover this, but generally…"). Check freshness while reading: if a note looks stale (`updated:` long ago for a volatile topic), say so alongside the answer.
5. **Offer to capture substantive answers** — answers are assets. If answering took real synthesis (a comparison, a cross-note summary, a decision input), offer to save it to `02_Inbox/` via [inbox-capture](../inbox-capture/SKILL.md) so the exploration compounds instead of evaporating in chat. Skip the offer for simple lookups.
6. **Treat unanswerable as a capture opportunity.** If the vault has nothing (or only stale material), say so plainly, offer to fill the gap via [research-to-resource](../research-to-resource/SKILL.md), and **log the gap** with `brain gap --question "<as asked>" --term <t>… --nearest <path>… --write` (spec §29.3), never by editing the queue by hand: the command forces the question onto one escaped line so it cannot alter the queue's structure, names a restricted nearest note by path only (never its title), and routes a **sensitive** gap — any nearest note carrying `restricted/private`, or `--sensitive` when the question itself is private (health, finances, people, identifiers) — to a `restricted/private` Inbox capture instead of the public [vault-answer-gaps](../../docs/vault-answer-gaps.md) queue, so private substance never lands in a non-restricted log. Interactive sessions append directly; an autonomous run adds `--inbox` and the row lands as an Inbox capture (Inbox-first rule) for triage to move.

## Rules

- Never present model knowledge as vault knowledge — the separation in step 4 is mandatory, not stylistic.
- Preserve privacy provenance: an answer that quotes or summarizes substance from a restricted note is itself private material — note it alongside the citations, and a captured version of that answer carries `restricted/private` ([CONVENTIONS](../../../00_Meta/CONVENTIONS.md#restrictedprivate)). Citing a restricted note by bare link propagates nothing.
- If two vault notes conflict, don't silently pick one: present both with the conflict flagged, and follow the Stuck/Escalation Protocol in [OPERATING-RULES](../../docs/OPERATING-RULES.md) so the conflict gets resolved in the notes, not just in chat.
- Captured answers land through [inbox-capture](../inbox-capture/SKILL.md)'s default lane and normal triage; filing an answer directly to its durable home is the execution-class contract's call ([AGENTS](../../../AGENTS.md#where-agents-write)), not this skill's.

## References

- `10_Agents/tools/brain/README.md` — the search/index CLI
- [INDEX](../../../00_Meta/INDEX.md) — the vault map, for step 1
- [inbox-capture](../inbox-capture/SKILL.md) — capturing offered answers
- [research-to-resource](../research-to-resource/SKILL.md) — filling gaps
- [vault-answer-gaps](../../docs/vault-answer-gaps.md) — the gap queue step 6 appends to
- [OPERATING-RULES](../../docs/OPERATING-RULES.md) — escalation on conflicting sources
