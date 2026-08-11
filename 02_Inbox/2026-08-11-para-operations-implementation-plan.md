---
title: "Implementation Plan: CODE Operations & Vault Operations (R1–R25)"
tags:
  - type/plan
  - audience/human
  - audience/agent
  - topic/second-brain
  - workflow/needs-review
  - status/active
updated: 2026-08-11
---

# Implementation Plan: CODE Operations & Vault Operations

Executes [[02_Inbox/2026-08-11-para-operations-skills-requirements|the R1–R25 requirements]]. Phases are grouped by **artifact cluster**, not by requirement number, so each canonical file gets rewritten once instead of repeatedly. **Owner approval of this plan authorizes the canonical edits listed per phase**; anything beyond a phase's listed files still goes through the normal needs-review path.

## Ground rules (every phase)

- Each phase is independently shippable and ends the same way: `brain index` + `brain validate --check-index` at zero errors, skills-README/index rows current, a changelog entry, commit + push.
- Detection logic lands in `brain` (tested); judgment lands in skills; anything needing owner judgment lands as an Inbox proposal — R17b's split, applied everywhere.
- Mid-build discoveries outside the phase's listed scope become Inbox notes (R14 discipline), never scope creep.
- New skills follow existing conventions: folder name = skill name, imperative verb, `SKILL.md` with both frontmatter contracts, brain invoked as `python3 10_Agents/tools/brain/brain.py …`.

## Assumed answers to open questions

Overridable before Phase 1; silence = assumption stands.

| Open question | Assumption |
|---|---|
| Entity notes (Q2) | Out of scope; revisit after this plan completes |
| Size threshold (Q3) | ~400 lines / ~20 KB starting point, as one tunable constant in brain |
| Missing-`expires:` timing (Q4) | Warnings stay off until Phase 4's backfill lands, then flip on |
| `import-notes` scope (Q5) | Deferred to Phase 8; owner call before building |
| R20 budgets (Q6) | Empirical: measure current bootstrap docs, set budget ≈ current + 50% headroom |

## Phase overview

| # | Phase | Requirements | Size | Status |
|---|-------|--------------|------|--------|
| 1 | Rules & retrieval | R11, R14, R22 | S | Done |
| 2 | Triage & distill upgrade | R2, R6, R13, R19 | M | Done |
| 3 | Note surgery | R7 | S | Pending |
| 4 | Curation & signals | R17, R17b, R20, R24, R8 | L | Pending |
| 5 | Express & Outbox | R10, R3, R12 | M | Pending |
| 6 | Rhythm & reviews | R15, R18, R9, R16 | M | Pending |
| 7 | Recategorize & polish | R1, R4, R5, R21 | S | Pending |
| 8 | Deferred | R25 (+R23 if approved) | M | Blocked on owner go |

## Phase detail

### Phase 1 — Rules & retrieval (R11, R14, R22)

- New skill `vault-answer`: search order (brain search → index → grep), wikilink citations in every answer, vault-vs-model knowledge separation, answers-are-assets capture offer, unanswerable → offer research-to-resource.
- `10_Agents/docs/operating-rules.md` gains two sections: **Stuck/Escalation Protocol** (R14) and **Session-End Flush** (R22).
- Canonical edits: operating-rules, skills README (+1 row).
- Exit: operating-rules still reads as one coherent document; new skill passes validate.

### Phase 2 — Triage & distill upgrade (R2, R6, R13, R19)

- New skill `distill-note` first (so triage has something to hand off to): atomic-claim extraction, template-zettel structure, summary layer, link wiring, supersede-by-replacement; callers are triage-inbox and the Journal/ideas graduation path.
- **One** rewrite of triage-inbox adding, in step order: atomize multi-topic captures (R6) → extract action items (R13) → classify → propagate to affected notes and index (R19) → hand `type/zettel` items to distill-note (R2).
- research-to-resource gains its propagation line (R19).
- Canonical edits: triage-inbox, research-to-resource, skills README.
- Risk watch: triage-inbox must stay readable — steps stay terse and link out to distill-note/merge-notes for procedure detail.

### Phase 3 — Note surgery (R7)

- New skill `merge-notes`: approved-merge procedure (survivor → replacement rewrite → retarget inbound links → archive loser → validate), split procedure, safe rename/move procedure.
- vault-maintenance step 4 gains one line: detection proposes, `merge-notes` executes.
- Canonical edits: vault-maintenance (one line), skills README.

### Phase 4 — Curation & signals (R17, R17b, R20, R24, R8)

The only code-heavy phase and the only frontmatter-schema change. Internal order matters:

1. **brain first:** `brain curate` command (human + `--json`) with all signals — expired, missing-expires, oversized, old-updated weighted by inbound links, orphan notes, unreferenced assets, opt-in `--check-urls`; `brain context` report (R20, budgets measured empirically); tunables in one constants block; tests extended.
2. **Schema:** conventions gains `expires:` (TTL defaults table, exemption list) and the draft→canonical promotion checklist (R8); templates gain `expires:`.
3. **Backfill:** one mechanical commit adding `expires:` across existing knowledge notes; judgment calls batched into a single Inbox report rather than decided silently.
4. **Flip warnings on** (missing-expires, size, budget breach) — only now, per Q4.
5. **New skill `curate`:** consumes the brain report; four outcomes (refresh / re-verify / propose-archive / propose-split); semantic-lint checks (R24) as proposals; run summary lands as an Inbox report note.
- Canonical edits: conventions, all templates, brain code + tests, vault-maintenance (staleness pointer → curate).
- Exit: brain test suite green; `brain curate --json` output stable; vault at zero errors *with warnings enabled*.

### Phase 5 — Express & Outbox (R10, R3, R12)

1. Structure: `02_Outbox/README.md` (lifecycle, staleness expectations, **never-ship rule**) and the `07_Archives/outbox/` landing path documented in the Archives README.
2. New skill `express-packet`: packet shapes (brief, outline, decision doc, comparison, draft post/email), provenance wikilinks, privacy gate (R12 — no `01_Profile/`/`03_Journal/` content without per-packet direction, personal-context sources flagged in the draft), `workflow/draft` frontmatter, recapture loop back to Inbox.
3. Two-lane write rule lands everywhere it must: AGENTS.md § Where Agents Write, conventions § Agent Write Rules, operating-rules self-validation checklist, index.
- Canonical edits: AGENTS.md, conventions, operating-rules, index, Archives README, skills README.

### Phase 6 — Rhythm & reviews (R15, R18, R9, R16)

1. Cadence table (R15) lives in the skills README (beside the catalog it schedules); conventions points to it.
2. recommended-automations rewrite: two flow families (inbound + rhythm jobs), unattended contract, guardrails (no shipping from Outbox, dry-run-first); source of truth = the R15 table.
3. periodic-review gains the archive completion path (R9) and goal-alignment questions (R16); weekly/monthly/quarterly review templates updated to match; quarterly updates now.md.
4. onboard-owner riders: teaches the rhythm, pitches rhythm jobs.
- Canonical edits: recommended-automations, periodic-review, review templates, onboard-owner, skills README.

### Phase 7 — Recategorize & polish (R1, R4, R5, R21)

Deliberately last, so the README describes what exists rather than what's planned.

1. skills README restructured into CODE-staged sections with "the CODE loop in this vault" intro (R5); AGENTS.md gains its one pointer line.
2. Every SKILL.md gains a one-line "CODE stage:" note (R1); boundary notes added where a skill spans stages (R4).
3. Changelog entry format standardized forward-only (R21): documented in conventions § Recency; all subsequent entries comply.
- Canonical edits: skills README, every SKILL.md, AGENTS.md, conventions, changelog.

### Phase 8 — Deferred (R25; R23 pending scope call)

- **R25 heartbeat** (owner-gated — build only on explicit go): `10_Agents/heartbeat.md` checklist (prose only; schedules stay in the scheduler), heartbeat skill (narrow prompt, `HEARTBEAT_OK` sentinel-quiet convention), recommended-automations wiring (skip-if-empty, quiet hours, cheap-model override where the harness allows).
- **R23 `import-notes`** if approved: batch capture with per-item provenance, supervised atomize-and-triage batches.

## Sequencing rationale

Phases 1–3 are pure skill/doc additions — immediate value, no schema risk. Phase 4 is the single code-and-schema milestone everything rhythm-related depends on. Phase 5 introduces the one new directory. Phase 6 wires cadence only once curate exists to schedule. Phase 7 recategorizes a finished catalog. Phase 8 stays behind an explicit owner gate.

## Risks

- **Canonical churn:** many phases touch conventions/AGENTS.md — mitigated by artifact clustering (each file rewritten in as few phases as possible) and per-phase approval scope.
- **Backfill judgment:** assigning TTLs to existing notes involves calls an agent shouldn't make silently — mitigated by batching all judgment items into one reviewable Inbox report (Phase 4.3).
- **Triage bloat:** Phase 2 quadruples triage-inbox's responsibilities — mitigated by keeping procedure detail in the callee skills.

## Tracking

This note is the plan of record. On each phase completion: flip its Status to Done here, add the changelog entry, and note deviations inline. Requirements stay authoritative for *what*; this plan is authoritative for *when and in what shape*.

## Related

- [[02_Inbox/2026-08-11-para-operations-skills-requirements|Requirements (R1–R25)]] — what this plan executes
- [[10_Agents/skills/README]] — the catalog being extended
- [[00_Meta/conventions]] — change control governing the canonical edits
- [[10_Agents/docs/operating-rules]] — write rules amended in Phases 1 and 5
