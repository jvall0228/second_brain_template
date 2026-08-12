---
name: express-packet
description: Assemble an outbound deliverable — brief, outline, decision doc, comparison, draft post or email — from vault notes into 02_Outbox/ with provenance links, for the owner to review and ship. Use when asked to draft something for an audience outside the vault.
title: "Skill: Express Packet"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Express Packet

**CODE stage:** Express — the outbound packet lane; shipping learnings recapture to the Inbox.

The Express stage: knowledge only pays off when it leaves the vault. This skill turns vault notes into an intermediate packet the owner can ship — and never ships anything itself.

## Steps

1. **Scope the packet with the owner's ask:** audience, purpose, and shape —
   - **Brief** — one-page synthesis of what the vault knows for a decision or meeting
   - **Outline** — structured skeleton for something the owner will write
   - **Decision doc** — options, criteria, recommendation (build on [template-decision-record](../../../09_Templates/template-decision-record.md) / [template-comparison](../../../09_Templates/template-comparison.md))
   - **Comparison** — side-by-side evaluation
   - **Draft post / email** — ready-to-edit prose in the owner's voice (see [PREFERENCES](../../../01_Profile/PREFERENCES.md))
2. **Gather sources vault-first** ([vault-answer](../vault-answer/SKILL.md) discipline): brain search → index → grep, read the actual notes, note gaps. Missing knowledge → offer [research-to-resource](../research-to-resource/SKILL.md) first, or flag the gap in the packet.
3. **Privacy gate — before writing a word:** packets never include `01_Profile/` or `03_Journal/` content unless the owner directed it *for this packet*. When personal-context notes do feed a packet (with per-packet direction), open the draft with a flag line such as `> Personal-context source: [Owner preferences](../01_Profile/PREFERENCES.md) — review before shipping.` Blanket permissions don't exist; the gate resets every packet.
4. **Write to `02_Outbox/`** (`YYYY-MM-DD-slug.md`, suffix on collision): frontmatter with `title`, `tags` (`audience/human`, `workflow/draft`, `type/*` fitting the shape), `updated:`; a one-line header stating audience and purpose; then the deliverable itself — polished enough to ship after one owner pass, not a dump of source notes.
5. **Provenance:** end with a `## Sources` section linking every vault note the packet draws on with source-relative Markdown (and external sources with retrieval dates). The owner must be able to check any claim in one hop.
6. **Hand off, don't ship:** tell the owner the packet is ready for review. Shipping — sending, posting, delivering — is theirs alone (see [README](../../../02_Outbox/README.md)).
7. **Close the loop:** after the owner ships, offer to recapture what shipping taught (feedback, corrections, reusable fragments) to the Inbox, and move the packet to `07_Archives/outbox/` with `status/done`.

## Rules

- **Agents never ship.** No send, no post, no publish — absent an explicit per-item owner instruction.
- The packet cites; the notes stay authoritative. A correction discovered while drafting goes into the *source note* (per its change control), then into the packet.
- Substantive synthesis created for a packet is also vault knowledge — offer to capture it to the Inbox so it outlives the deliverable.

## References

- [README](../../../02_Outbox/README.md) — the lane this writes to, and its lifecycle
- [vault-answer](../vault-answer/SKILL.md) — the retrieval discipline for step 2
- [CONVENTIONS](../../../00_Meta/CONVENTIONS.md) § Agent Write Rules — the two-lane write rule
