---
title: "Requirements: CODE Operations Reorg & Missing Vault Operations (R1–R18)"
tags:
  - type/plan
  - audience/human
  - audience/agent
  - topic/second-brain
  - workflow/needs-review
  - status/active
updated: 2026-08-11
---

# Requirements: CODE Operations Reorg & Missing Vault Operations

Owner-directed brainstorm (2026-08-11 session) on aligning the skills library with the canonical second-brain operations (CODE: Capture → Organize → Distill → Express) and codifying the mechanical operations an agent-operated vault needs beyond CODE. **Requirements only — nothing here is built yet.** Review, then direct execution.

Grounding: Forte Labs' BASB spec (CODE, PARA, progressive summarization, intermediate packets) and a survey of 7 second-brain agent implementations (see [[#Research basis]]).

## Current coverage verdict

| CODE stage | Our skills | Verdict |
|---|---|---|
| Capture | inbox-capture, daily-log, solution-capture | Strong |
| Organize | triage-inbox, periodic-review | Strong |
| Distill | research-to-resource (external research only) | Weak |
| Express | — | Missing |

Plus two agent-native layers CODE doesn't name, both partially built: system health (vault-maintenance, link-repair, self-maintenance) and onboarding (onboard-owner, onboard-harness, agent-orientation, recommended-automations).

## Requirements

### CODE alignment

- **R1 — Categorize, don't mass-rename.** Skill names stay imperative verbs (field-standard; renames churn folders, wikilinks, and harness docs for no functional gain). Restructure `10_Agents/skills/README.md` into CODE-staged sections (Capture / Organize / Distill / Express / System / Onboarding); add a one-line "CODE stage:" note to each SKILL.md.
- **R2 — New skill `distill-note`.** Reshape an existing vault note: extract the atomic claim, apply template-zettel structure, add a summary layer, wire links, supersede the original by replacement. Invoked by triage-inbox when classifying something `type/zettel` (closes the "tagged but never reshaped" hole) and by the Journal/ideas → Resources graduation path.
- **R3 — New skill `express-packet`.** Assemble an intermediate packet (brief, outline, decision doc, comparison, draft post/email) *from* vault notes, with provenance wikilinks. Writes to `02_Outbox/` (R10) as `workflow/draft`. Shipped packets may recapture learnings into Inbox (Express → Capture loop).
- **R4 — Boundary notes, not renames.** README entries state that research-to-resource spans Capture+Distill; periodic-review docs name the weekly review's Organize role; daily-log is Capture.
- **R5 — Teach the loop.** One "the CODE loop in this vault" section (skills README intro or 10_Agents/README) mapping stage → skills → directories; onboard-owner teaches it; AGENTS.md points at it in one line.

### System operations (non-CODE mechanics)

- **R6 — Atomize at triage.** New triage-inbox step: multi-topic capture → split into one-topic notes *before* classifying. Never at capture (capture stays zero-friction).
- **R7 — New skill `merge-notes`.** Executes an *approved* merge: pick survivor → rewrite overlapping sections into one coherent whole (replacement, never concatenation) → retarget inbound wikilinks → archive the loser → validate. Split (the inverse, for over-grown notes) documented in the same skill. vault-maintenance keeps detection/proposal; this skill is execution.
- **R8 — Promote & refresh ride on existing docs.** Draft→canonical promotion checklist in conventions/vault-maintenance. Staleness detection is superseded by R17.
- **R9 — Archive completion path.** periodic-review defines the project/area → `07_Archives/` move (status/done, index update, changelog entry).

### Outbox

- **R10 — New structure `02_Outbox/`.** Shared `02_` prefix keeps it adjacent to Inbox with **zero renumbering**. Holds outbound deliverables awaiting the owner's action (the vault's "loading dock"). Lifecycle mirrors Inbox: express-packet writes drafts → owner reviews and ships → archive to `07_Archives/outbox/` with status/done. Ephemeral: trends toward empty; staleness flagged by maintenance/reviews. Write rule becomes two-lane: agent output for the vault → Inbox; for the world → Outbox. Both review-gated. **Agents never ship directly** absent an explicit per-item owner instruction.

### Remaining operational gaps

- **R11 — New skill `vault-answer`.** Retrieval discipline for "what do I know about X?": search order (brain search → index → grep), cite vault notes by wikilink in every answer, separate vault knowledge from model knowledge, and treat unanswerable questions as capture opportunities (offer research-to-resource).
- **R12 — Privacy gate at egress.** Outbound packets never include `01_Profile/` or `03_Journal/` content unless the owner directs it per-packet; packets built from personal-context notes flag it in the draft. (Counterpart to agent-orientation's ingestion-side sensitivity judgment.)
- **R13 — Action-item extraction at triage.** Triage step: actionable commitment found in a capture → add to the relevant project's tasks (or propose a project); the note still files normally.
- **R14 — Stuck/escalation protocol.** operating-rules section: when blocked, or when two vault sources conflict, write a `workflow/needs-review` Inbox note stating the conflict and stop — never guess-and-commit or silently resolve rule conflicts.
- **R15 — One canonical cadence table.** Single table (conventions or skills README): cadence → skills → trigger (daily: log; weekly: triage + review + Outbox sweep; monthly: review + maintenance/curation; quarterly: review + curation + self-maintenance audit). recommended-automations wires *this table*; onboard-owner teaches it as "the rhythm".
- **R16 — Goal alignment in reviews.** Weekly/monthly review templates ask: does each active project serve something in [[01_Profile/now]]? Anything on the Now page with no project moving it? Quarterly review updates now.md.

### Expiration & curation

- **R17 — `expires:` property + curation job.** New frontmatter field on knowledge notes, best-effort at write time, hard cap one year. Default TTLs by volatility: wiring/product facts 3 mo; retrieval-dated research 6 mo; evergreen/canonical 12 mo. Exempt (events, not claims): Journal logs, changelog, solution notes, all of 07_Archives. Flagging is **report-driven, no tag churn**. New skill `curate` (distinct from vault-maintenance: *epistemic* vs *mechanical* integrity) runs ad hoc or scheduled; per flagged note: (1) still good → bump updated + fresh expires; (2) stale → re-verify via research-to-resource corrective mode; (3) dead → propose archive; (4) too big → propose split. 1–2 executable by agents; 3–4 are proposals. One-time backfill migration for existing notes.
- **R17b — `brain` is the single signal engine.** New `brain curate` command (human + `--json` output) computing all re-review signals: expired, missing-expires (per exemption rules), oversized (start ~400 lines / ~20 KB, tunable in one place), old-updated weighted by inbound-link count, and opt-in `--check-urls` for dead source URLs. `validate` gains the free/offline signals as *warnings* (never blocks commits; URL checks never run pre-commit). Skills consume the report; detection logic never lives in skill prose.

### Automations

- **R18 — recommended-automations gains a second flow family.** Charter widens from ingestion-only to "wire any recurring vault operation": (1) inbound flows (unchanged); (2) **rhythm jobs** — headless skill invocations on cadence (curate, vault-maintenance, weekly triage/review prompt, Outbox sweep, daily-log scaffold). Source of truth inverts to the R15 cadence table. Scheduled runs inherit the strictest write posture: execute only self-contained outcomes; everything needing judgment → report note to Inbox. Guardrails: no automation ever ships from Outbox; rhythm jobs are dry-run-first like inbound flows. onboard-owner's automation stage adds the rhythm-jobs pitch.

## Open questions (owner to decide)

1. **Build order.** Suggested: R11+R14 (cheap, high-leverage) → R2+R7 (policy debt already incurred) → R17+R17b+R18 (curation milestone) → R10+R3+R12 (Express milestone) → R1/R4/R5/R13/R15/R16 ride along with the recategorization pass. All at once is also viable.
2. **Entity notes** (tiered people/tool profiles, per COG-second-brain): in scope for the template, or explicitly out?
3. **Size threshold** for R17b: confirm ~400 lines / ~20 KB starting point.
4. **Missing-`expires:` warning timing**: immediately, or only after the backfill migration lands?

## Settled during brainstorm (no longer open)

- No mass renames (R1); merge execution is its own skill, not a vault-maintenance mode (R7); curation is its own skill (R17); Outbox shares the `02_` prefix — no directory renumbering (R10); agents never auto-ship (R10/R18); flagging is report-driven, not tag-driven (R17); brain owns all detection signals (R17b).

## Research basis

- CODE/BASB spec: [The Building a Second Brain overview](https://fortelabs.com/blog/basboverview/), [The 4 Levels of PKM](https://fortelabs.com/blog/the-4-levels-of-personal-knowledge-management/) (retrieved 2026-08-11).
- Implementation survey (2026-08-11), 7 repos: jamesmcroft/obsidian-ai-second-brain (only explicit CODE adopter — stages in docs/folders, skill names stay generic verbs), ballred/obsidian-claude-pkm (review-centric command family, goal cascade), eugeniughelbur/obsidian-second-brain (~46 commands; distill/graduate verbs; scheduled review agents), AgriciDaniel/claude-obsidian (PARA as pluggable mode; hash-approved change control), huytieu/COG-second-brain (fullest Express stage: content-factory, publish flows; verification agents), smixs/agent-second-brain (memory-decay tiers ≈ expiration), coleam00/second-brain-starter (proactive-heartbeat reviews).
- Key findings applied: explicit CODE naming is rare — the stages survive as verbs (→R1); Express is the field's weakest stage (→R3/R10); distillation appears as structural promotion, not highlighting (→R2); reviews everywhere drift into their own first-class family (→ keep periodic-review as-is); memory decay is the field's expiration analog (→R17).

## Related

- [[10_Agents/skills/README]] — current skill catalog
- [[00_Meta/conventions]] — change control, tag taxonomy
- [[10_Agents/docs/operating-rules]] — write rules this plan amends
- [[07_Archives/inbox/2026-08-11-onboard-owner-skill-requirements|onboard-owner requirements]] — precedent for this note's lifecycle
