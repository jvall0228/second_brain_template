---
name: onboard-owner
description: Welcome a new vault owner — teach what the second brain does for them, interview them to fill in their profile, and orchestrate the other onboarding skills (harness wiring, environment orientation). Use on the first run of a freshly adopted vault, or to resume an unfinished onboarding.
title: "Skill: Onboard Owner"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Onboard Owner

Turn a fresh copy of this template into *someone's* second brain. This is the human counterpart to [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]]: that skill wires up the software; this one welcomes the owner. Requirements history: `07_Archives/inbox/2026-08-11-onboard-owner-skill-requirements.md`.

## The ruling constraint: the owner may be non-technical

Assume the owner has never used Obsidian, markdown, git, or a terminal — and never needs to. Everything follows:

- **You perform every mechanical step** — creating files, moving notes, validating, installing, committing. The owner only converses and approves.
- **Never** tell the owner to run a command, edit a file, or read a vault doc. The only interface you offer is "I can do X for you — want that?"
- **Plain language only.** No unexplained jargon: not PARA, Zettelkasten, frontmatter, YAML, CLI, repo, or markdown. When a concept must surface, name it by what it does for them: `04_Projects/` is "a folder for things you're actively working on", the Inbox is "where new stuff lands before we file it".
- **Errors are yours.** If validation or an install fails, fix it silently or explain the consequence in one plain sentence. Never show tool output.
- Vault docs ([[00_Meta/conventions]], [[00_Meta/index]], [[AGENTS]]) ground *you*; they are never reading assignments for the owner.

## Teaching: tone and best practices

The SKILL sets tone, not a script — improvise the words, hold the principles:

- **Lead with the payoff, never the system.** First beat: "this is a place where everything you tell me gets remembered and organized, so any AI assistant you talk to already knows your world — you never start from zero." Structure is explained only as it earns its keep.
- **Progressive disclosure.** Introduce each piece at the moment it's used — the Inbox when the first capture happens, reviews when routines come up. No upfront tour, no glossary, no wall of concepts.
- **Teach by doing together.** The guided first capture → triage cycle *is* the lesson in how the vault works day to day. Prefer "let's try it with something real from your life" over explanation.
- **One question at a time**, in their vocabulary, echoing their own words back in what you write.
- **Check understanding by use, not quiz.** "So if something comes up mid-conversation, you can just say 'remember this' — want to try?" beats "does that make sense?"
- **Normalize imperfection.** Nothing they say is locked in; everything can be refiled, reworded, or deleted later. Filing decisions are yours to propose so the owner never faces a taxonomy.

## Write policy during onboarding

Everything written **during the live onboarding conversation** goes directly to its real home — `01_Profile/`, `04_Projects/`, `05_Areas/` — not through the Inbox. The owner approving each answer in the moment *is* the human review the Inbox-first rule exists to provide. This exception is scoped to this skill's live session only; outside it, normal Inbox-first rules apply. Every note you write must carry valid frontmatter and pass `python3 10_Agents/tools/brain/brain.py validate`.

## State: the onboarding checklist

First step, always: look for an onboarding checklist note (`02_Inbox/*-onboarding.md`, or already archived in `07_Archives/inbox/`).

- **None exists** → this is a fresh start. Create `02_Inbox/YYYY-MM-DD-onboarding.md` (`type/log`, `workflow/draft`, `status/active`) listing the stages below, each marked pending.
- **One exists in the Inbox** → resume. Greet, recap what's already done in a sentence, and continue from the first pending stage. Never re-interview for answers already captured.
- **One is archived with `status/done`** → onboarding is complete; tell the owner and ask what they actually need.

Update the checklist as each stage completes or is skipped (skipping is a valid, recorded outcome). On completion, mark it `status/done`, drop `workflow/draft`, move it to `07_Archives/inbox/` (keep the dated filename), regenerate the index, and validate — it is the permanent record of the onboarding.

## Stages

1. **Welcome.** The payoff pitch (above). Ask what they're hoping this helps with; let their answer steer emphasis. Gauge familiarity — if they already know Obsidian or PKM, compress the teaching accordingly.
2. **Profile interview.** Conversationally fill the three profile notes from their answers — [[01_Profile/now]] (current focus, active projects, key dates), [[01_Profile/preferences]] (how they like to be talked to and what output should look like), [[01_Profile/defaults]] (timezone, locale, units). Write real notes; replace the fill-in guidance stubs. Read each back in summary for their OK.
3. **Seed real content.** Projects and responsibilities that surfaced in the interview become notes in `04_Projects/` and `05_Areas/` (1–2 each is plenty), built from [[09_Templates/template-project]] / [[09_Templates/template-area]].
4. **First capture → triage, together.** Ask for something real on their mind; capture it via [[10_Agents/skills/inbox-capture/SKILL|inbox-capture]], then triage it together via [[10_Agents/skills/triage-inbox/SKILL|triage-inbox]] — this teaches the daily loop: say "remember this" anytime; the Inbox catches it; filing happens later, together.
5. **Wire up the harness.** Offer to run [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] for whatever assistant they're using right now, framed as "let me make sure I remember all this next time we talk."
6. **Connect their world.** Offer [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]], translating its interview into plain offers ("should I be able to see your calendar?"). If sources are adopted, offer [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] as "I can check that regularly and file what matters."
7. **Clean up the training wheels.** The template ships one worked example per section, meant to be deleted once real content exists. Offer to remove them wherever stage 3 put something real.
8. **Close.** Run a full `brain validate`; fix anything it raises. Recap in three sentences what exists now and the one habit that matters ("just tell me things — I'll remember"). Archive the checklist per the state rules above.

Stages 5–7 are **offered, never forced** — stopping early is fine; the checklist makes resuming cheap.

## Orchestration rules

When a stage hands off to another skill, **follow that skill's SKILL.md contract** — never reimplement it. Each sub-skill keeps its own approval gates. Where a sub-skill speaks to a technical reader, you translate its owner-facing moments into plain language; its mechanics stay unchanged.

## Exit criteria ("onboarded")

- The three profile notes hold real answers.
- At least one real project or area note exists.
- The owner has done one capture → triage cycle and knows they can say "remember this" / "what's waiting to be filed?"
- At least one harness is wired (or the owner explicitly deferred it).
- Seed examples are dealt with (or deliberately kept).
- The checklist is archived with `status/done`.
