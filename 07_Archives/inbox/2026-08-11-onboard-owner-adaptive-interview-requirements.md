---
title: "Requirements: onboard-owner adaptive interview (UI enrichment, defaults, research-before-ask)"
tags:
  - type/plan
  - audience/human
  - audience/agent
  - topic/onboarding
  - status/done
updated: 2026-08-11
---

# Requirements: onboard-owner adaptive interview

Triage of [the 2026-08-11 Cursor dry-run feedback](2026-08-11-onboard-owner-template-feedback.md) into settled requirements for [onboard-owner](../../10_Agents/skills/onboard-owner/SKILL.md). **Requirements only — nothing here is built yet.** Review, then direct execution via the paired [implementation plan](2026-08-11-onboard-owner-adaptive-interview-implementation-plan.md).

Three feedback items, all pointing at the same underlying gap: the skill's interview posture is inconsistent across its own stages — rich where it was designed carefully (people map, role interview), plain Q&A everywhere else.

## Feedback → gap → requirement

| # | Dry-run feedback | Current gap in SKILL.md | Requirement |
|---|---|---|---|
| 1 | Use in-thread UI/UX enrichment when the harness supports it | No capability check exists until agent-orientation's stage 8 inventory — every earlier stage (1–7) defaults to plain text even when richer tools are available | R1, R2 |
| 2 | Stronger non-technical defaults; "ask + offer recommendations" worked well and should be baked in | Only observed ad hoc during the dry run's preference interview; not written into the skill as a default pattern, and not applied to other owner-facing questions | R3 |
| 3 | Research before asking — extend inference-first beyond people/role | Stage 4 (people map) and stage 3's role interview already infer-then-confirm; stage 2 (profile: now/preferences/defaults) is pure Q&A with no inference step | R4, R5 |

## Requirements

- **R1 — Lightweight capability probe at stage 1.** Before the welcome beat asks its first question, the agent checks for in-thread UI affordances available in the current harness (a native structured-question tool, dialogs, rich prompts) — a cheap, session-scoped check, independent of and earlier than agent-orientation's stage-8 inventory. The result governs interaction style for the rest of the session: use the richer surface when available, plain text otherwise. Nothing is written to disk for this — it's a live interaction-mode decision, not a durable environment fact.
- **R2 — Defer to agent-orientation for the durable record.** R1's probe is transient and onboarding-scoped. When agent-orientation runs at stage 8, its fuller harness capability profile (already specified in its own SKILL.md — [agent-orientation](../../10_Agents/skills/agent-orientation/SKILL.md) §"Harness introspection") is the system of record; it confirms or expands what R1 assumed. No contradiction, no duplicate detection logic — R1 just can't wait until stage 8 to start behaving well.
- **R3 — "Ask + recommend" as the skill-wide default interaction pattern.** Every owner-facing question in onboard-owner defaults to pairing the question with a small set (2–4) of grounded, context-based recommended answers — using R1's UI surface when available (structured choices), plain-text numbered options otherwise. This is a *default*, not a mandate: a question that's genuinely open-ended (nothing to recommend without inventing an answer) stays open. Codify this once, in its own section, so stages 2–9 inherit it rather than each stage re-specifying it.
- **R4 — Research-before-ask extends to stage 2 (profile interview).** Before asking about `now`/`preferences`, infer from what's already surfaced in the conversation (the welcome-stage answer about what they're hoping this helps with) and from repo signals (git config, README, org names — the same sources stage 4's people map already uses). Before asking about `defaults` (timezone, locale, units), infer from system/environment signals (OS locale, system timezone) the same way the agent already grounds itself via machine-level context. Offer the inferred answer back for confirmation, in the same shape stage 3's role interview and stage 4's people map already use — extend the existing pattern, don't invent a new one.
- **R5 — No change needed for stage 3 (role) or stage 4 (people map).** Already research-first with consent; explicitly out of scope here. Stage 8 (agent-orientation) is also already research-first in its own skill (step 4: "Interview the owner for what can't be observed") — the "sources" leg of feedback item 3 is already satisfied by the existing skill boundary; no edit needed there either.

## Settled during triage (no longer open)

- Ask+recommend becomes a **skill-wide** default (R3), not scoped to the preferences stage alone — the pattern generalizes cleanly and the dry run's positive signal was about the *pattern*, not the specific stage.
- The UI-capability check is its **own lightweight stage-1 probe** (R1), not a wait-for-agent-orientation dependency — most of onboarding (stages 1–7) would otherwise never benefit from richer UI even when available.
- Research-before-ask sourcing for defaults/profile draws on **all available signals** — system/environment, repo/git, and prior conversation content — rather than restricting to one category.
- Stages 3, 4, and 8 need no changes (R5) — they already do what feedback item 3 is asking for; the gap is specifically stage 2.

## Related

- [Source feedback](2026-08-11-onboard-owner-template-feedback.md) — the dry-run notes this triages
- [Implementation plan](2026-08-11-onboard-owner-adaptive-interview-implementation-plan.md) — execution of R1–R5
- [SKILL](../../10_Agents/skills/onboard-owner/SKILL.md) — the skill amended (PR: see repo)
- [SKILL](../../10_Agents/skills/agent-orientation/SKILL.md) — harness capability profile this reuses/defers to (R2)
- [Original onboard-owner requirements](2026-08-11-onboard-owner-skill-requirements.md) — precedent this amends, not replaces
