---
title: "Outbox"
tags:
  - type/meta
  - audience/agent
  - audience/human
updated: 2026-08-11
---

# Outbox

The vault's **loading dock**: outbound deliverables — briefs, outlines, decision docs, comparisons, draft posts and emails — assembled *from* vault notes and awaiting the owner's action. Where [the Inbox](../02_Inbox/README.md) is the review gate for content entering the vault, the Outbox is the review gate for content leaving it.

## Lifecycle (mirrors the Inbox)

1. The [express-packet](../10_Agents/skills/express-packet/SKILL.md) skill writes a packet here, tagged `workflow/draft`, with source-relative Markdown provenance links back to its source notes.
2. The owner reviews, edits, and **ships it themselves** (sends the email, posts the post, delivers the doc).
3. Shipped or abandoned packets move to `07_Archives/outbox/` with `status/done`. Learnings from shipping (feedback, corrections) are worth recapturing to the Inbox.

**Agents never ship.** No agent sends, posts, or publishes Outbox content anywhere absent an explicit per-item owner instruction — drafting is the skill; shipping is the owner's call.

## Expectations

- This directory trends toward **empty**. A packet sitting here for weeks is stale — reviews and maintenance flag lingering packets rather than letting them rot.
- Packets are snapshots, not knowledge: they cite their sources but the sources stay authoritative. Never update a packet in place of the note it came from.
- Naming follows the Inbox convention: `YYYY-MM-DD-descriptive-slug.md`, numeric suffix on collision.
- `expires:` is not used here (packets are ephemeral by design; the archive path is the lifecycle).
