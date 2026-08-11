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

**CODE stage:** Onboarding.

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

Everything written **during the live onboarding conversation** goes directly to its real home — `01_Profile/`, `03_Journal/people/` (confirmed people notes, stage 4), `04_Projects/`, `05_Areas/` — not through the Inbox. The owner approving each answer in the moment *is* the human review the Inbox-first rule exists to provide. This exception is scoped to this skill's live session only; outside it, normal Inbox-first rules apply. Every note you write must carry valid frontmatter and pass `python3 10_Agents/tools/brain/brain.py validate`.

## State: the onboarding checklist

First step, always: look for an onboarding checklist note (`02_Inbox/*-onboarding.md`, or already archived in `07_Archives/inbox/`).

- **None exists** → this is a fresh start. Create `02_Inbox/YYYY-MM-DD-onboarding.md` (`type/log`, `workflow/draft`, `status/active`) listing the stages below, each marked pending.
- **One exists in the Inbox** → resume. Greet, recap what's already done in a sentence, and continue from the first pending stage. Never re-interview for answers already captured.
- **One is archived with `status/done`** → onboarding is complete; tell the owner and ask what they actually need.

Update the checklist as each stage completes or is skipped (skipping is a valid, recorded outcome). On completion, mark it `status/done`, drop `workflow/draft`, move it to `07_Archives/inbox/` (keep the dated filename), regenerate the index, and validate — it is the permanent record of the onboarding.

## Stages

1. **Welcome.** The payoff pitch (above). Ask what they're hoping this helps with; let their answer steer emphasis. Gauge familiarity — if they already know Obsidian or PKM, compress the teaching accordingly.
2. **Profile interview.** Conversationally fill the three profile notes from their answers — [[01_Profile/now]] (current focus, active projects, key dates), [[01_Profile/preferences]] (how they like to be talked to and what output should look like), [[01_Profile/defaults]] (timezone, locale, units). Write real notes; replace the fill-in guidance stubs. Read each back in summary for their OK.
3. **Vault intent & role.** Ask, in plain words, whether this vault is for their whole life or for work — "is this a personal home for everything, or a work notebook your employer might see?" (One fork per context — PRD §16.2.) The answer **triggers the context specialization**:
   - **Work** → rewrite the periodic templates in `09_Templates/` **in place** from the matching sources in [[09_Templates/variants/README|09_Templates/variants/]] (`work-daily-log.md` → `template-daily-log.md`, `work-weekly-review.md` → `template-weekly-review.md`). Template paths never change, so every tool that resolves templates by stable name keeps working; the pre-commit hook's snippet regeneration (`10_Agents/tools/vscode/gen_snippets.py`) then carries the specialized templates to the VS Code surface automatically (PRD §6.5 parity) — the variant source files themselves never become snippets. Frame it by the payoff: "your daily page gets standup, blockers, and decisions instead of mood and health — nothing personal ends up where work can see it."
   - **Personal** → the shipped templates already fit; change nothing.
   - Either way, record the answer in `00_Meta/config.yaml` as `context: work` or `context: personal` (grammar: spec §15.3 — one scalar). This is a record for tooling and future skills, not a switch: the templates were already specialized above.
   - **Then the role interview.** Before asking, infer what you can from the environment — org names in git remotes, repo READMEs, installed tooling — and offer it back for confirmation rather than quizzing from zero. If the vault is a **work** brain (or work is a real part of a personal one): their role/title and company, the team they're on, and what they're responsible for — this materially changes what agents should capture and how they should write. Write confirmed answers into [[01_Profile/work]] (the existing shell — replace its fill-in stubs; it exists in every fork). Who-they-are material that surfaces along the way — how they think, values, interests — goes into [[01_Profile/identity]]. Read each back in summary for their OK.
4. **People map.** Identify the key people around the owner — name, role, and **relationship to the owner** (manager, direct report, peer, partner, family, client…) — so future assistants know who's who. **Inference-first, with consent:** ask the owner's permission in plain words ("mind if I peek at who you meet and message most, so you don't have to list everyone from scratch?"), then seed candidates only from **observable sources this environment's orientation inventory records a working interface for** (`10_Agents/environments/<env-slug>/orientation-inventory.md` — the [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] output contract is the source list: recent calendar attendees, frequent email/chat correspondents), plus what is directly observable without tooling (git history — commit authors, co-authors, reviewers). If no inventory note exists yet (orientation runs at stage 8), seed from git history and the conversation so far, and revisit the people map after stage 8 connects more sources.
   - **Confirm everything before landing.** Every candidate — and every inferred fact about them — gets the owner's confirmation before a note is written. Escalate to the owner precisely what can't be observed or shouldn't be assumed: relationships, sensitivities, who actually matters. Unconfirmed candidates are dropped, not parked in notes.
   - **Write confirmed people** to `03_Journal/people/` (one note per person, first-name kebab-case filenames — see [[03_Journal/people/README]]), following the shipped `example-person` pattern (Relationship / Personality & Traits / Notes; include only sections with real content). This lands under this skill's live-session write exception. Each note carries full frontmatter plus `author:`/`session:` provenance.
   - **Sensitivity (PRD §16.2, verbatim):** "`03_Journal/people/` notes concern **third parties** — keep them factual and respectful, and write nothing you would not stand behind if read back." And: "For health, financial, or otherwise sensitive content, remember that anything committed is visible to every agent and service with repo access; keep out material that must not reach them." Concretely: health, financial, legal, or relationship-conflict details about a third party — or anything the owner shares in confidence about someone — is **never recorded without the owner's explicit approval of the exact wording**.
   - A dry-run of this stage is worked through in [[#People map: worked example]] below.
5. **Seed real content.** Projects and responsibilities that surfaced in the interview become notes in `04_Projects/` and `05_Areas/` (1–2 each is plenty), built from [[09_Templates/template-project]] / [[09_Templates/template-area]].
6. **First capture → triage, together.** Ask for something real on their mind; capture it via [[10_Agents/skills/inbox-capture/SKILL|inbox-capture]], then triage it together via [[10_Agents/skills/triage-inbox/SKILL|triage-inbox]] — this teaches the daily loop: say "remember this" anytime; the Inbox catches it; filing happens later, together. Then sketch **the rhythm** in one breath — daily log, weekly tidy-up and review, monthly health check, quarterly refresh (the cadence table in [[10_Agents/skills/README]]) — as "the vault stays useful because we check in on it; I'll handle the mechanics."
7. **Wire up the harness.** Offer to run [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] for whatever assistant they're using right now, framed as "let me make sure I remember all this next time we talk."
8. **Connect their world.** Offer [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]], translating its interview into plain offers ("should I be able to see your calendar?"). If sources are adopted, offer [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] as "I can check that regularly and file what matters" — and pitch its **rhythm jobs** the same plain way ("I can also run the weekly tidy-up and draft your reviews on schedule; you just read them"). If stage 4's people map ran before an orientation inventory existed, offer one more inference pass over the newly adopted sources.
9. **Clean up the training wheels.** The template ships one worked example per section, meant to be deleted once real content exists. Offer to remove them wherever stage 5 put something real — including `03_Journal/people/example-person.md` once a real person note exists.
10. **Close.** Run a full `brain validate`; fix anything it raises. Recap in three sentences what exists now and the one habit that matters ("just tell me things — I'll remember"). Archive the checklist per the state rules above.

Stages 7–9 are **offered, never forced** — stopping early is fine; the checklist makes resuming cheap. The people map (stage 4) is also skippable on the owner's say-so; record the skip in the checklist like any other.

## People map: worked example

A dry run of stage 4, showing the confirm-before-landing flow and the note it produces.

> **Agent:** While looking at your calendar and commit history (you said that was OK), one name keeps coming up — Dana. She's in most of your weekly meetings and reviews a lot of your changes. Who is Dana to you?
>
> **Owner:** She's my manager.
>
> **Agent:** Got it. I'd like to save a small note — "Dana: my manager, works with me closely" — so any assistant you talk to knows who she is when she comes up. Anything else worth remembering about working with her?
>
> **Owner:** She likes a short written update before our one-on-ones.
>
> **Agent:** I'll add that. Here's exactly what the note will say: *"Dana — owner's manager. Prefers a short written update ahead of 1:1s."* Sound right?
>
> **Owner:** Yes.

Only now does the note land, as `03_Journal/people/dana.md`:

```markdown
---
title: "Dana"
tags:
  - type/note
  - audience/human
  - audience/agent
  - topic/people
updated: 2026-08-11
author: claude-code
session: onboarding-2026-08-11
---

# Dana

## Relationship

- Owner's manager (confirmed by owner during onboarding, 2026-08-11; candidate inferred from calendar and review activity).

## Notes

- Prefers a short written update ahead of 1:1s.
```

Everything in the note was read back and approved verbatim; the inference (calendar/commits) produced only the *candidate* — the relationship and the note's contents came from the owner.

## Orchestration rules

When a stage hands off to another skill, **follow that skill's SKILL.md contract** — never reimplement it. Each sub-skill keeps its own approval gates. Where a sub-skill speaks to a technical reader, you translate its owner-facing moments into plain language; its mechanics stay unchanged.

## Exit criteria ("onboarded")

- The three profile notes hold real answers.
- The vault's intent is recorded (`context:` in `00_Meta/config.yaml`); for a work vault, [[01_Profile/work]] holds the owner's role, team, and responsibilities.
- Confirmed people notes exist in `03_Journal/people/` — or the people map was explicitly skipped and the skip recorded.
- At least one real project or area note exists.
- The owner has done one capture → triage cycle and knows they can say "remember this" / "what's waiting to be filed?"
- At least one harness is wired (or the owner explicitly deferred it).
- Seed examples are dealt with (or deliberately kept).
- The checklist is archived with `status/done`.
