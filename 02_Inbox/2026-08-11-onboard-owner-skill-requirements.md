---
title: "Requirements: onboard-owner skill"
tags:
  - type/plan
  - audience/human
  - audience/agent
  - topic/software
  - workflow/draft
  - status/active
updated: 2026-08-11
---

# Requirements: `onboard-owner` skill

Owner-settled requirements (chat brainstorm, 2026-08-11) for a thirteenth library skill that onboards a **new vault owner** — the human counterpart to [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]]. Motivating case: the owner is forking the template for a family member who is not a software engineer.

## The one design constraint that rules the rest

**The adopter is non-technical.** They may never have used Obsidian, markdown, git, or a terminal. Everything follows from this:

- The **agent performs every mechanical step** — file creation, moves, validation, harness install, git. The owner only converses and approves.
- **Plain language throughout.** No unexplained jargon (PARA, Zettelkasten, frontmatter, YAML, CLI, repo). Where a concept must surface, explain it by what it does for the owner ("a folder for things you're actively working on"), not by its name.
- **Never instruct the owner to run a command or edit a file.** Offering "I can do X for you — want that?" is the only interface.
- Errors (validation failures, install problems) are the agent's to fix silently or explain in consequences, never in tool output dumps.

## Three jobs

### 1. Teach — what a second brain is and what's built in

- Open with the payoff, not the system: "a place where everything you tell me is remembered, organized, and usable by any AI assistant you talk to — so you never start from zero."
- **Progressive disclosure**: teach each piece at the moment it's used (Inbox when the first capture happens, reviews when scheduling comes up). No upfront lecture, no glossary.
- Teach by **doing together**: the guided first capture → triage cycle is the lesson on how the vault works day to day.
- The skill links to vault docs ([[00_Meta/conventions]], [[00_Meta/index]]) for the *agent's* grounding; it never sends the *owner* to read them.

### 2. Interview — populate the owner's context

- Conversationally fill the three profile notes — [[01_Profile/now]] (current focus, projects, key dates), [[01_Profile/preferences]] (how they like to communicate and receive output), [[01_Profile/defaults]] (timezone, locale, units) — writing valid, frontmatter-complete notes from their answers.
- **Writes directly to `01_Profile/`** (owner decision): the live interview is the approval; no Inbox staging. This is a standing write-policy exception scoped to this skill, mirroring the `solution-capture` carve-out — record it in [[AGENTS]] / conventions when the skill ships.
- Seed first real content where the conversation surfaces it: 1–2 projects into `04_Projects/`, responsibilities into `05_Areas/`, using the templates.
- Offer to delete the seeded worked examples once real content exists in a section (their documented purpose is "delete once you've learned the pattern").

### 3. Orchestrate — run the other onboarding skills

- Sequence (owner decision: orchestration **triggers** the sub-skills; they stay separate skills): profile interview → [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] for the harness in use → [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] → optionally [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]].
- Invoke each by **following its SKILL.md contract**, never reimplementing it; each sub-skill keeps its own approval gates.
- Sub-skills assume a technical reader in places — this skill **wraps their owner-facing moments in plain language** (e.g. orientation's source interview becomes "should I be able to see your calendar?").
- Every hand-off is offered, not forced; stopping early is a valid outcome.

## Cross-cutting requirements

- **Resumable state**: a checklist note at `02_Inbox/YYYY-MM-DD-onboarding.md` marks each stage done/skipped/pending; re-running the skill resumes rather than re-interviews.
- **Validation gate**: every written note passes `brain validate`; a full validate run closes the session. Failures are the agent's to fix, invisibly.
- **Discoverability**: root README and [[AGENTS]] point first-run adopters at this skill as step 0 of the adoption path.
- **Exit criteria** ("onboarded"): profile notes filled; at least one harness wired; seed examples decided on; owner has done one capture → triage cycle with the agent and knows they can just say "remember this" / "what's in my inbox?".

## Open questions (for build time)

1. Exact plain-language script/beats for the teaching moments — draft in the SKILL.md or leave to agent judgment with tone guidance?
2. Does the write-policy exception for `01_Profile/` extend to the seeded `04_Projects/`/`05_Areas/` notes, or do those stage through the Inbox as usual?
3. Should the resumable checklist note archive to `07_Archives/inbox/` on completion (like executed plans) as the record of onboarding?

## Related

- [[10_Agents/skills/README]] — library the skill joins (would be #13)
- [[00_Meta/prd]] §9.3 — write policy the profile exception amends
