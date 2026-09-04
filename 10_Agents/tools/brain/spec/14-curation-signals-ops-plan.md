---
title: "brain Spec §14 — Curation signals (ops plan Phase 4)"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# 14. Curation signals (ops plan Phase 4)

*Section 14 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

Detection lives in `brain`; the judgment lives in the `curate` skill; findings needing owner decisions land as Inbox proposals. Every tunable is a module constant in one block at the top of `brain.py` — `CURATE_MAX_LINES`/`CURATE_MAX_BYTES` (oversized), `CURATE_STALE_DAYS`, `EXPIRES_CAP_DAYS`, the exemption sets, and the `BOOTSTRAP_BUDGETS` map with `BOOTSTRAP_TOTAL_BUDGET`. Policy prose (TTL defaults, what's exempt and why) lives in [CONVENTIONS](../../../../00_Meta/CONVENTIONS.md) § Expiration; the constants are authoritative for values.

- **`expires:`** — optional frontmatter date (`YYYY-MM-DD`). Malformed → `invalid-expires` error (§10.2). Present and past → **expired** (curate report only). More than `EXPIRES_CAP_DAYS` after `updated:` → **expires-beyond-cap**. Absent on a note that should carry one → **missing-expires**; exempt by path: `02_Inbox/` (zero-friction capture; assigned at triage), `02_Outbox/` (ephemeral packets; lifecycle is the archive path), `03_Journal/`, `07_Archives/`, `09_Templates/`, `10_Agents/solutions/`, the changelog, `00_Meta/STATUS.md`, and `CLAUDE.md`; exempt by type tag: `type/decision` (event records, via `EXPIRES_EXEMPT_TYPE_TAGS`). The orphan check uses the path exemptions only — a decision record still wants inbound links.
- **oversized** — normalized size or line count over the constants; exempt `07_Archives/` and the changelog (frozen/append-only content is never a split candidate).
- **stale** — `updated:` older than `CURATE_STALE_DAYS`; score = days-old × (1 + backlink count), sorted worst-first, so heavily-referenced stale notes surface first. Exempt by prefix (`CURATE_STALE_EXEMPT_PREFIXES`): `03_Journal/periodic/` and `07_Archives/` — dated event records and archived content are frozen by design, so age there is a fact, not a re-review signal, and exempting them keeps the stale list to notes a review can act on.
- **orphans** — zero backlinks; exempt the expires-exempt set plus `AGENTS.md`, `CLAUDE.md`, and the root `README.md`.
- **unreferenced assets** — `08_Assets/` files no resolved generic link or embed points at.
- **distill candidates** — notes under `CURATE_DISTILL_PREFIXES` (`03_Journal/`, `10_Agents/solutions/`), outside `CURATE_DISTILL_EXEMPT_PREFIXES` (`03_Journal/periodic/`, `03_Journal/people/`, `03_Journal/plans/` — dated records, entity hubs, and time-bound plans are linked because they are hubs or commitments, not because they hold a claim) and not a `README.md`, with at least `CURATE_DISTILL_MIN_BACKLINKS` (2) backlinks and no `type/zettel` tag. Rows `{backlinks, path, title}`, sorted by backlinks descending then path. Report-only: the curate skill hands each to distill-note as a proposal — a Journal idea or solution other notes keep citing is a claim that has outgrown its lane.
- **dead URLs** — `--check-urls` only: HEAD each distinct `http(s)` URL (10s timeout); 403/405 responses are HEAD-hostile hosts, not dead links. Network access makes this opt-in forever: never run by `validate`, the pre-commit hook, or CI.

`validate` surfaces only the free, offline, low-noise subset as warnings — `missing-expires`, `expires-beyond-cap`, `oversized`, `bootstrap-budget[-total]` — gated behind `VALIDATE_CURATION_WARNINGS` (flipped on with the one-time backfill). Warnings never block commits (§10.4); expired/stale/orphan findings stay report-only because they demand judgment, not mechanical fixes.
