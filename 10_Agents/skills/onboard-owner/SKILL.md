---
name: onboard-owner
description: Welcome a new vault owner — teach what the second brain does for them, interview them to fill in their profile, and orchestrate the other onboarding skills (harness wiring, environment orientation). Use on the first run of a freshly adopted vault, or to resume an unfinished onboarding.
title: "Skill: Onboard Owner"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-18
expires: 2027-08-11
---

# Onboard Owner

**CODE stage:** Onboarding.

Turn a fresh copy of this template into *someone's* second brain. This is the human counterpart to [onboard-harness](../onboard-harness/SKILL.md): that skill wires up the software; this one welcomes the owner. Requirements history: `07_Archives/inbox/2026-08-11-onboard-owner-skill-requirements.md`.

## The ruling constraint: the owner may be non-technical

Assume the owner has never used Obsidian, markdown, git, or a terminal — and never needs to. Everything follows:

- **You perform every mechanical step** — creating files, moving notes, validating, installing, committing. The owner only converses and approves.
- **Never** tell the owner to run a command, edit a file, or read a vault doc. The only interface you offer is "I can do X for you — want that?"
- **Plain language only.** No unexplained jargon: not PARA, Zettelkasten, frontmatter, YAML, CLI, repo, or markdown. When a concept must surface, name it by what it does for them: `04_Projects/` is "a folder for things you're actively working on", the Inbox is "where new stuff lands before we file it".
- **Errors are yours.** If validation or an install fails, fix it silently or explain the consequence in one plain sentence. Never show tool output.
- Vault docs ([CONVENTIONS](../../../00_Meta/CONVENTIONS.md), [INDEX](../../../00_Meta/INDEX.md), [AGENTS](../../../AGENTS.md)) ground *you*; they are never reading assignments for the owner.

## Interaction defaults

Two defaults apply across every stage below, so individual stages don't need to re-specify them:

- **Capability probe, once, at the start.** Before stage 1's first question, check for in-thread UI affordances the current harness exposes — a native structured-question tool, dialogs, richer prompts. This is a cheap, session-scoped check, independent of and earlier than [agent-orientation](../agent-orientation/SKILL.md)'s fuller stage-9 capability profile (see stage 9 below). Use the richer surface for the rest of the session when one exists; fall back to plain text otherwise. Nothing is written to disk for this — it's a live interaction-mode decision, not a durable environment fact.
- **Ask + recommend, by default.** Every owner-facing question defaults to pairing the ask with 2–4 grounded, context-based recommended answers — via the UI surface above when available, plain-text numbered options otherwise. Ground the recommendations in whatever can already be inferred (see each stage's research-before-ask guidance); never invent options with nothing behind them. This is a default, not a mandate — a genuinely open-ended question, with nothing plausible to recommend, stays open.

## Teaching: tone and best practices

The SKILL sets tone, not a script — improvise the words, hold the principles:

- **Lead with the payoff, never the system.** First beat: "this is a place where everything you tell me gets remembered and organized, so any AI assistant you talk to already knows your world — you never start from zero." Structure is explained only as it earns its keep.
- **Progressive disclosure.** Introduce each piece at the moment it's used — the Inbox when the first capture happens, reviews when routines come up. No upfront tour, no glossary, no wall of concepts.
- **Teach by doing together.** The guided first capture → triage cycle *is* the lesson in how the vault works day to day. Prefer "let's try it with something real from your life" over explanation.
- **One question at a time**, in their vocabulary, echoing their own words back in what you write.
- **Check understanding by use, not quiz.** "So if something comes up mid-conversation, you can just say 'remember this' — want to try?" beats "does that make sense?"
- **Normalize imperfection.** Nothing they say is locked in; everything can be refiled, reworded, or deleted later. Filing decisions are yours to propose so the owner never faces a taxonomy.

## Write policy during onboarding

Everything written **during the live onboarding conversation** goes directly to its real home — `01_Profile/`, `03_Journal/people/` (confirmed people notes, stage 4), `04_Projects/`, `05_Areas/` — not through the Inbox. The owner approving each answer in the moment *is* the human review the Inbox-first rule exists to provide. This exception is scoped to this skill's live session only; outside it, normal Inbox-first rules apply. Every note you write must carry valid frontmatter and pass `brain validate`.

## Remote-safety boundary

Repository, OS, and capability signals are safe to inspect without account-data
access. Before any onboarding step reads email, calendar, contacts, chat, drive,
tasks, transcripts, or equivalent personal data, run `brain remote-safety --persist --json`
(long-form fallback: `python3 10_Agents/tools/brain/brain.py remote-safety --persist --json`).
Run the shared guard with `persist=True` before the connector because onboarding
turns findings into notes.

`block` and `unknown` stop before the connector; owner consent to inspect a source
does not replace the gate. The owner may acknowledge `unknown` for this invocation
only, while a verified public/non-private or template push target is never
overrideable. A no-push vault is local-only and therefore cannot use connector
results in onboarding writes; rely on the conversation, git, and other local
non-personal signals instead. Capability inventory can still proceed.

## State: the onboarding checklist

First step, always: look for an onboarding checklist note (`02_Inbox/*-onboarding.md`, or already archived in `07_Archives/inbox/`).

- **None exists** → this is a fresh start. Create `02_Inbox/YYYY-MM-DD-onboarding.md` (`type/log`, `workflow/draft`, `status/active`) listing the stages below, each marked pending.
- **One exists in the Inbox** → resume. Greet, recap what's already done in a sentence, and continue from the first pending stage. Never re-interview for answers already captured.
- **One is archived with `status/done`** → onboarding is complete; tell the owner and ask what they actually need.

Update the checklist as each stage completes or is skipped (skipping is a valid, recorded outcome). On completion, mark it `status/done`, drop `workflow/draft`, move it to `07_Archives/inbox/` (keep the dated filename), regenerate the index, and validate — it is the permanent record of the onboarding.

## Stages

1. **Welcome & starter intent.** Give the payoff pitch, then offer four plain-language starting points: **work**, **personal life**, **exploring both**, and **not sure yet**. Always accept a free-form answer too; these are starting points, not a forced menu. If existing conversation or repository context materially supports one choice, recommend exactly one and explain why in one sentence. Otherwise present all four neutrally. Say that the owner can change direction later, then let the answer steer emphasis. Gauge familiarity — if they already know Obsidian or personal knowledge systems, compress the teaching accordingly.
2. **Profile interview.** Conversationally fill the three profile notes from their answers — [NOW](../../../01_Profile/NOW.md) (current focus, active projects, key dates), [PREFERENCES](../../../01_Profile/PREFERENCES.md) (how they like to be talked to and what output should look like), [DEFAULTS](../../../01_Profile/DEFAULTS.md) (timezone, locale, units). **Research before asking** — the same posture stage 3's role interview and stage 4's people map already use: before `now`/`preferences`, infer from what's already surfaced this session (the welcome-stage answer about what they're hoping this helps with) and from repo signals (git config, README, org names); before `defaults`, infer from system/environment signals (OS locale, system timezone). Offer each inferred value back for confirmation rather than asking cold. Write real notes; replace the fill-in guidance stubs. Read each back in summary for their OK.
3. **Vault intent & role.** Turn stage 1's starter intent into the privacy boundary: ask, in plain words, whether this particular vault is a personal home or a work notebook an employer might see (one fork per context — PRD §16.2). "Exploring both" means explaining the separate-fork boundary and helping the owner choose which fork this is first; "not sure yet" may stay undecided until enough context exists. The owner can change this later by re-running specialization. Once confirmed, the answer **triggers the context specialization**:
   - **Work** → rewrite the periodic templates in `09_Templates/` **in place** from the matching sources in [09_Templates/variants/](../../../09_Templates/variants/README.md) (`work-daily-log.md` → `template-daily-log.md`, `work-weekly-review.md` → `template-weekly-review.md`). Template paths never change, so every tool that resolves templates by stable name keeps working; the pre-commit hook's snippet regeneration (`10_Agents/tools/vscode/gen_snippets.py`) then carries the specialized templates to the VS Code surface automatically (PRD §6.5 parity) — the variant source files themselves never become snippets. Frame it by the payoff: "your daily page gets standup, blockers, and decisions instead of mood and health — nothing personal ends up where work can see it."
   - **Personal** → the shipped templates already fit; change nothing.
   - Either way, record the answer in `00_Meta/config.yaml` as `context: work` or `context: personal` (grammar: spec §15.3 — one scalar). This is a record for tooling and future skills, not a switch: the templates were already specialized above.
   - **Then the role interview.** Before asking, infer what you can from the environment — org names in git remotes, repo READMEs, installed tooling — and offer it back for confirmation rather than quizzing from zero. If the vault is a **work** brain (or work is a real part of a personal one): their role/title and company, the team they're on, and what they're responsible for — this materially changes what agents should capture and how they should write. Write confirmed answers into [WORK](../../../01_Profile/WORK.md) (the existing shell — replace its fill-in stubs; it exists in every fork). Who-they-are material that surfaces along the way — how they think, values, interests — goes into [IDENTITY](../../../01_Profile/IDENTITY.md). Read each back in summary for their OK.
4. **People map.** Identify the key people around the owner — name, role, and **relationship to the owner** (manager, direct report, peer, partner, family, client…) — so future assistants know who's who. **Inference-first, with consent and remote safety:** ask the owner's permission in plain words ("mind if I peek at who you meet and message most, so you don't have to list everyone from scratch?"). Before reading any approved connector, apply the remote-safety boundary above with persistence requested. Then seed candidates only from **observable sources this environment's orientation inventory records a working interface for** (`10_Agents/environments/<env-slug>/orientation-inventory.md` — the [agent-orientation](../agent-orientation/SKILL.md) output contract is the source list: recent calendar attendees, frequent email/chat correspondents), plus what is directly observable without tooling (git history — commit authors, co-authors, reviewers). If no inventory note exists yet (orientation runs at stage 9), or the gate does not allow persisted connector results, seed from git history and the conversation so far; revisit connector-backed inference only after orientation and remote safety both allow it.
   - **Confirm everything before landing.** Every candidate — and every inferred fact about them — gets the owner's confirmation before a note is written. Escalate to the owner precisely what can't be observed or shouldn't be assumed: relationships, sensitivities, who actually matters. Unconfirmed candidates are dropped, not parked in notes.
   - **Write confirmed people** to `03_Journal/people/` (one note per person, first-name kebab-case filenames), following the permanent [people-note guidance](../../../03_Journal/people/README.md) (Relationship / Personality & Traits / Notes; include only sections with real content). This lands under this skill's live-session write exception. Each note carries full frontmatter plus `author:`/`session:` provenance. Offer the `restricted/private` tag for each person note (conventions § restricted/private): people notes are third-party data, and the tag keeps them out of the committed index's body fields and lets Cursor exclude them — recommend it as the default and record the owner's choice.
   - **Sensitivity (PRD §16.2, verbatim):** "`03_Journal/people/` notes concern **third parties** — keep them factual and respectful, and write nothing you would not stand behind if read back." And: "For health, financial, or otherwise sensitive content, remember that anything committed is visible to every agent and service with repo access; keep out material that must not reach them." Concretely: health, financial, legal, or relationship-conflict details about a third party — or anything the owner shares in confidence about someone — is **never recorded without the owner's explicit approval of the exact wording**.
   - A dry-run of this stage is worked through in [People map: worked example](#people-map-worked-example) below.
5. **Seed real content.** Responsibilities that surfaced become Areas first (1–2 is plenty), built from [template-area](../../../09_Templates/template-area.md). A bounded outcome may become an active Project only after confirming every related Area, substantive completion criteria, and a target. Mark an owner-supplied date `confirmed`; when scope supports a realistic working date but the owner has not supplied one, explain the estimate and mark it `estimated`. If no defensible finish line exists, keep it inactive or as an Area rather than fabricating a date. Build from [template-project](../../../09_Templates/template-project.md), then run `brain projects --write-rollups` and summarize the resulting active inventory back to the owner. [NOW](../../../01_Profile/NOW.md) remains a curated priority view, not a second registry.
6. **First capture → triage, together.** Ask for something real on their mind; capture it via [inbox-capture](../inbox-capture/SKILL.md), then triage it together via [triage-inbox](../triage-inbox/SKILL.md) — this teaches the daily loop: say "remember this" anytime; the Inbox catches it; filing happens later, together. Then sketch **the rhythm** in one breath — daily log, weekly tidy-up and review, monthly health check, quarterly refresh (the cadence table in [README](../README.md)) — as "the vault stays useful because we check in on it; I'll handle the mechanics."
7. **Verify the harness.** Run [onboard-harness](../onboard-harness/SKILL.md) in its read-only **project** mode for the assistant in use. A clean clone already carries repository-local skill adapters. Separately offer user-global availability only if the owner wants these skills in sessions outside this repository; show the exact external-path preview and ask again before applying it.
8. **Install recommended skills & configs.** Offer, in plain words, the owner-requested option to set up the recommended add-ons — "there are a few well-regarded community helper skills and a work-vs-personal settings starter I can install for you; want any of them?" This delegates to [onboard-harness](../onboard-harness/SKILL.md)'s **recommended components** install, driven by `10_Agents/components/manifest.json` ([README](../../components/README.md)): first-party overlays may go in without fuss, and each community skill or memory block (the ADHD output rules, the Karpathy coding rails) is a separate plain yes/no — "these come from the wider community and install the latest version; okay to add this one?" The **vault-config presets** (e.g. the work-fork starter) change *this vault's* settings, so you apply the chosen preset yourself — merging it into `00_Meta/config.yaml` under this skill's live-session write exception — rather than through onboard-harness's user-scope install. Everything is recorded in the machine manifest and reversible; skipping changes nothing.
9. **Connect their world.** Offer [agent-orientation](../agent-orientation/SKILL.md), translating its interview into plain offers ("should I be able to see your calendar?"). Its harness capability profile ("Harness introspection") is also the durable record that confirms or expands the Interaction defaults probe above — nothing further to do here. If sources are adopted, offer [recommended-automations](../recommended-automations/SKILL.md) as "I can check that regularly and file what matters" — and pitch its **rhythm jobs** the same plain way ("I can also run the weekly tidy-up and draft your reviews on schedule; you just read them"). If stage 4's people map ran before an orientation inventory existed, offer one more inference pass over the newly adopted sources.
10. **Clean up the training wheels atomically.** The seeded examples are one linked bundle whose sole authority is `10_Agents/tools/adopt_examples.json`; never offer selective deletion. Preview the exact all-or-nothing deletion inventories and marked reference edits with `python3 10_Agents/tools/adopt_check.py plan --output <path-outside-vault>/second-brain-adopt-plan.json`. Apply only after approval of that fresh plan. The tool refuses missing examples, ignored/untracked occupants, unmarked surviving links, changed/dirty inputs, unsafe paths, and stale plans; after apply it independently verifies the regenerated index before accepting the cleanup. If apply reports an interrupted lock, run `python3 10_Agents/tools/adopt_check.py recover`; do not remove its lock or transaction by hand. If the owner wants even one seeded example kept, keep the whole bundle and record that choice.
11. **Close.** Run a full `brain validate`; fix anything it raises. Recap in three sentences what exists now and the one habit that matters ("just tell me things — I'll remember"). Archive the checklist per the state rules above.

Stages 7–10 are **offered, never forced** — stopping early is fine; the checklist makes resuming cheap. The people map (stage 4) is also skippable on the owner's say-so; record the skip in the checklist like any other.

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
- The vault's intent is recorded (`context:` in `00_Meta/config.yaml`); for a work vault, [WORK](../../../01_Profile/WORK.md) holds the owner's role, team, and responsibilities.
- Confirmed people notes exist in `03_Journal/people/` — or the people map was explicitly skipped and the skip recorded.
- At least one real Area exists; every activated Project has all related Areas, explicit completion criteria, and a confirmed or visibly estimated target.
- The owner has done one capture → triage cycle and knows they can say "remember this" / "what's waiting to be filed?"
- Project-local harness discovery is verified; optional user-global wiring was applied from an approved exact preview or explicitly deferred.
- The seeded example bundle was atomically removed and validated, or deliberately kept intact.
- The checklist is archived with `status/done`.
