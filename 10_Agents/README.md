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

- [[10_Agents/docs/task-patterns|Task Patterns]] — Write rules, allowed destinations, example output
- [[10_Agents/docs/operating-rules|Operating Rules]] — Behavior expectations and self-modification protocol

## Skills

Twelve harness-agnostic skills in the Agent Skills format (folder-per-skill `SKILL.md`), covering capture & triage, periodic reviews, vault maintenance, research → resource, harness onboarding, and environment integration (orientation, ingestion automations, self-maintenance). See [[10_Agents/skills/README|Skills]] for the full table and the format contract.

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
- [[00_Meta/conventions]] — Naming, tagging, and change control
- [[01_Profile/preferences]] — Communication style and constraints
- [[01_Profile/defaults]] — Timezone, locale, output defaults
