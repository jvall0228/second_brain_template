---
title: "Onboard-owner template feedback — 2026-08-11 dry run"
tags:
  - audience/agent
  - audience/human
  - type/note
  - workflow/draft
  - topic/onboarding
  - topic/template
updated: 2026-08-11
author: cursor
session: onboarding-2026-08-11
---

# Onboard-owner template feedback — 2026-08-11 dry run

Owner feedback from a live [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] dry run (Cursor, vault `second_brain_test`). Capture for template / skill updates — not owner profile content.

## Feedback

1. **Use in-thread UI/UX enrichment.** The agent should attempt whatever in-thread UI affordances the current harness exposes (richer prompts, structured choices, native dialogs, etc.) instead of plain text Q&A only when better surfaces exist.

2. **Stronger sensible defaults; assume non-technical.** Lean harder into defaults so the owner is not doing setup work. In particular, the preferences interview should default to: ask a question **and** offer several context-based recommendations (this pattern worked well in the dry run and should be the skill's baked-in default, not something discovered mid-session).

3. **Research before asking.** For each question, do more environment / prior-context research and **suggest** answers grounded in what can already be observed — rather than expecting the owner to supply everything from scratch. Inference-first already exists for people/role; extend that posture across profile, defaults, sources, and similar stages.

## Context from the run (for triage)

- Goal stated: organize life + compound user context
- Owner new to notes apps / Obsidian
- Preferences settled on explanatory tone + CTAs + recommend-options-when-asking
- Automations / heavy wiring deferred (dry run)
- Related skill: [[10_Agents/skills/onboard-owner/SKILL]]
- Requirements history pointer in skill: `07_Archives/inbox/2026-08-11-onboard-owner-skill-requirements.md`

## Suggested triage

- Update `onboard-owner` SKILL teaching + interview stages to mandate research→suggest→confirm
- Codify "question + recommendations" as the default preference / interview pattern (and as the shipped Preferences stub guidance)
- Add a harness-capability beat: detect in-thread UI enrichment and use it when available (Cursor user rules / dialogs / etc.)
