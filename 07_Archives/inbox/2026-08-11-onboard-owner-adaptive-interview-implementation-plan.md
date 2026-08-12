---
title: "Implementation Plan: onboard-owner adaptive interview (R1–R5)"
tags:
  - type/plan
  - audience/human
  - audience/agent
  - topic/onboarding
  - status/done
updated: 2026-08-11
---

# Implementation Plan: onboard-owner adaptive interview

Executes [the R1–R5 requirements](2026-08-11-onboard-owner-adaptive-interview-requirements.md). Single artifact, single phase — everything lands in one edit of `10_Agents/skills/onboard-owner/SKILL.md`. **Owner approval of this plan authorizes that edit.**

**Status: executed 2026-08-11**, on branch `onboard-owner/adaptive-interview`, pending PR review/merge.

## Ground rules

- One coherent rewrite pass, not a patchwork of inserted sentences — read the whole file before editing so the new material sits naturally in the existing voice (SKILL.md "sets tone, not a script").
- No new files, no new skills, no frontmatter/schema changes. This plan is scoped to prose edits in one SKILL.md.
- Ends the same way every canonical edit does: `python3 10_Agents/tools/brain/brain.py index` + `validate`, a changelog entry, this plan and its requirements archived to `07_Archives/inbox/` with `status/done`.

## Edit plan

1. **Done.** New "Interaction defaults" section, placed right after "The ruling constraint" (R1, R3).
   - Capability probe (R1): before the welcome beat's first question, check for in-thread UI affordances the current harness exposes; use the richer surface for the rest of the session if present, plain text otherwise. Noted as transient/session-scoped, not written anywhere.
   - Ask+recommend default (R3): every owner-facing question defaults to pairing the ask with 2–4 grounded, context-based recommended answers, via the UI surface from the probe or plain-text numbered options; open-ended questions are the explicit exception, not the default.
   - *Deviation from plan wording:* the requirements doc's R3 said "codify... in the Teaching section" — landed instead as its own section immediately after the ruling constraint, which reads better as a peer cross-cutting rule rather than a teaching-tone bullet. Same effect: stages 2–9 inherit it without re-specifying.

2. **Done.** Stage 2 (Profile interview) gained the inference-first sub-step (R4): infer `now`/`preferences` from the welcome-stage answer and repo signals; infer `defaults` from system/environment signals; offer each back for confirmation, matching stage 3's existing phrasing pattern.

3. **Done.** One-line pointer added inside stage 8 reconciling with R1/R2: agent-orientation's harness capability profile is the durable record that confirms/expands the Interaction-defaults probe.

4. **Done — no-op as planned.** Stages 3, 4, and the "People map: worked example" left unchanged (R5).

5. **N/A.** SKILL.md's `updated:` was already `2026-08-11` (same-day edit); no bump needed.

## Exit criteria

- [x] SKILL.md reads as one coherent document — reviewed end-to-end post-edit.
- [x] Stages 2–9 no longer need to individually justify plain-text-only or cold-ask behavior; the interaction defaults section covers it once.
- [x] `brain validate` clean (0 errors, 4 pre-existing unrelated warnings); index regenerated; changelog entry added.
- [x] This plan and its requirements doc archived to `07_Archives/inbox/` with `status/done`, mirroring [the original onboard-owner requirements](2026-08-11-onboard-owner-skill-requirements.md)'s lifecycle.
- [ ] PR opened and merged — tracked outside this note; this note's `status/done` reflects the plan's own execution, not the PR merge.

## Related

- [Requirements (R1–R5)](2026-08-11-onboard-owner-adaptive-interview-requirements.md) — what this plan executes
- [SKILL](../../10_Agents/skills/onboard-owner/SKILL.md) — the file edited
- [SKILL](../../10_Agents/skills/agent-orientation/SKILL.md) — referenced in step 3
