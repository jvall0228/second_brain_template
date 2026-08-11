---
title: "Agents"
tags:
  - type/meta
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Agents

Agent-facing documentation for working within this vault. Start with the bootstrap sequence in [[AGENTS]], then return here for expanded guidance.

## Docs

- [[10_Agents/docs/TASK-PATTERNS|Task Patterns]] — Write rules, allowed destinations, example output
- [[10_Agents/docs/OPERATING-RULES|Operating Rules]] — Behavior expectations and self-modification protocol

## Skills

Twelve harness-agnostic skills in the Agent Skills format (folder-per-skill `SKILL.md`), covering capture & triage, periodic reviews, vault maintenance, research → resource, harness onboarding, and environment integration (orientation, ingestion automations, self-maintenance). See [[10_Agents/skills/README|Skills]] for the full table and the format contract.

## Components

The recommended-component registry — the agent library's home for installable **components** an onboarder can add: third-party skills, user-scope memory blocks, harness overlays, and vault-config presets. `10_Agents/components/manifest.json` is the machine-readable source of truth; third-party content is never vendored here (community items track their upstream branch and materialize only into the harness user scope at install time). [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] is the installer. See [[10_Agents/components/README|Components]], with the human-facing community catalog at [[06_Resources/recommended-skills]].

## Tools

- [[10_Agents/tools/brain/README|brain]] — the vault index CLI: structured queries (`list`, `search`, `links`, `tags`, `show`, `recent`) plus `validate`; the committed `vault-index.json` it maintains is readable without running anything. See [[10_Agents/tools/README|Tools]] for the directory rules.

## Environments

Environment-scoped notes (one directory per machine/execution environment), starting with the orientation inventory that [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] produces. Never bootstrap-linked; each note self-guards with an applicability preamble. See [[10_Agents/environments/README|Environments]] for the convention (full scoping machinery deferred to #15).

## Solutions

A running knowledge base of solutions to recurring problems agents hit while working in the vault, organized by category. Add a note whenever you solve something worth not re-deriving later. See [[10_Agents/solutions/README|Solutions]] for the category index.

One example is included to show the format:

- [[10_Agents/solutions/obsidian-issues/wikilink-resolution-rules|Wikilink Resolution Rules]] — How Obsidian resolves `[[wikilinks]]`

## Related

- [[AGENTS]] — Vault entrypoint and bootstrap sequence
- [[00_Meta/CONVENTIONS]] — Naming, tagging, and change control
- [[01_Profile/PREFERENCES]] — Communication style and constraints
- [[01_Profile/DEFAULTS]] — Timezone, locale, output defaults
