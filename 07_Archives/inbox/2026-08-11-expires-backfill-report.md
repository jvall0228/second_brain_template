---
title: "Report: expires: Backfill — Judgment Calls (Resolved)"
tags:
  - type/log
  - audience/human
  - audience/agent
  - status/done
updated: 2026-08-11
---

# `expires:` Backfill — Judgment Calls for Review

## Resolution (2026-08-11)

Owner approved all four action items. Applied:

1. **Decision records exempted by type.** `type/decision` added to brain's `EXPIRES_EXEMPT_TYPE_TAGS` (and documented in [CONVENTIONS](../../00_Meta/CONVENTIONS.md#expiration-expires) and the spec); `expires:` dropped from the example decision record, and its `updated:` restored to the event date `2025-01-10` (event records freeze, like Journal entries). The orphan check stays path-only, so a decision record still wants inbound links.
2. **Oversized notes:** [harness-primitives-research](../../06_Resources/harness-primitives-research.md) was **split** — 7 per-harness notes + a standards note ([harness-claude-code](../../06_Resources/harness-claude-code.md), [harness-codex](../../06_Resources/harness-codex.md), [harness-opencode](../../06_Resources/harness-opencode.md), [harness-pi](../../06_Resources/harness-pi.md), [harness-cursor](../../06_Resources/harness-cursor.md), [harness-copilot](../../06_Resources/harness-copilot.md), [harness-muse-code](../../06_Resources/harness-muse-code.md), [harness-standards](../../06_Resources/harness-standards.md)) with the hub keeping the overlap matrix and comparative findings. [PRD](../../00_Meta/PRD.md) and `10_Agents/tools/brain/SPEC.md` **accepted** as coherent single-topic notes (product memory / one spec). `harness-copilot` (20.4 KB) also accepted — one harness is one topic. These three are reviewed-coherent; their oversized warnings are expected.
3. **Orphan READMEs linked** from [INDEX](../../00_Meta/INDEX.md) (Profile, Meta, Agent docs, Harness adapters) — orphan signal now clean, no blanket README exemption.
4. **Now-page TTL kept at 12 months** — the quarterly review refreshes it (a shorter TTL would double-signal), per the recommendation below.

Original review request preserved below for the record.

---

The one-time backfill (ops plan Phase 4.3) added `expires:` to all 56 in-scope notes mechanically: 3-month TTL (2026-11-11) for the 8 harness wiring docs, the harnesses README, and [harness-primitives-research](../../06_Resources/harness-primitives-research.md); 6-month (2027-02-11) for `06_Resources/example-resource.md` (modeling the research TTL for adopters; plain path — the note is a seeded example adopters delete); 12-month (2027-08-11) for everything else. Every touched note's `updated:` was bumped per the duty-to-bump rule. The calls below were made mechanically but deserve an owner look:

## Decisions to confirm or override

1. **Decision records got a TTL they arguably shouldn't have.** `04_Projects/example-project/decision-records/2025-01-10-example-decision.md` is an event record (a decision log), conceptually exempt like Journal entries — but the exemption list in [CONVENTIONS](../../00_Meta/CONVENTIONS.md#expiration-expires) doesn't cover `decision-records/` directories. It received the 12-month default, and its example date `updated: 2025-01-10` was bumped to today (also required to keep it under the one-year cap). **Proposal:** add `decision-records/` (or `type/decision`) to the exempt set in brain's constants + conventions, then drop the field from that note.
2. **Oversized split candidates** (flagged by `brain curate`, all genuine):
   - [harness-primitives-research](../../06_Resources/harness-primitives-research.md) — 114 KB, 5.7× the threshold. Natural split: one note per harness, with the overlap matrix as the surviving hub.
   - [PRD](../../00_Meta/PRD.md) — 31 KB. Could split shipped-history sections into Archives; or accept (it's the product's memory).
   - `10_Agents/tools/brain/SPEC.md` — 29.5 KB. Dense but single-topic; suggest accepting oversize (a spec is one subject — splitting harms it).
3. **Orphan READMEs** (no inbound wikilinks): `00_Meta/README.md`, `01_Profile/README.md`, `10_Agents/docs/README.md`, `10_Agents/harnesses/README.md`. READMEs are reached by path convention, not links. **Proposal:** link the four from [INDEX](../../00_Meta/INDEX.md) rather than exempting all READMEs (keeps the orphan signal honest).
4. **Bootstrap TTLs:** [NOW](../../01_Profile/NOW.md) intentionally got the 12-month evergreen default even though a Now page goes stale in weeks — the quarterly review updates it (ops plan Phase 6), so a shorter TTL would double-signal. Flag if you'd rather have the 3-month TTL as a backstop.

## Related

- `02_Inbox/2026-08-11-para-operations-implementation-plan.md` — Implementation plan, Phase 4.3 (plain path — a shipped capture note adopters delete)
- [CONVENTIONS](../../00_Meta/CONVENTIONS.md) § Expiration — the schema this backfill instantiated
