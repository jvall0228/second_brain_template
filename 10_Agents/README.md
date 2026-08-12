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

Agent-facing documentation for working within this vault. Start with the bootstrap sequence in [AGENTS](../AGENTS.md), then return here for expanded guidance.

## Docs

- [Task Patterns](docs/TASK-PATTERNS.md) — Write rules, allowed destinations, example output
- [Operating Rules](docs/OPERATING-RULES.md) — Behavior expectations and self-modification protocol

## Skills

Twelve harness-agnostic skills in the Agent Skills format (folder-per-skill `SKILL.md`), covering capture & triage, periodic reviews, vault maintenance, research → resource, harness onboarding, and environment integration (orientation, ingestion automations, self-maintenance). See [Skills](skills/README.md) for the full table and the format contract.

## Components

The recommended-component registry — the agent library's home for installable **components** an onboarder can add: third-party skills, user-scope memory blocks, harness overlays, and vault-config presets. `10_Agents/components/manifest.json` is the machine-readable source of truth; third-party content is never vendored here (community items track their upstream branch and materialize only into the harness user scope at install time). [onboard-harness](skills/onboard-harness/SKILL.md) is the installer. See [Components](components/README.md), with the human-facing community catalog at [recommended-skills](../06_Resources/recommended-skills.md).

## Tools

- [brain](tools/brain/README.md) — the vault index CLI: structured queries (`list`, `search`, `links`, `tags`, `show`, `recent`) plus `validate`; the committed `vault-index.json` it maintains is readable without running anything. See [Tools](tools/README.md) for the directory rules.

## Environments

Environment-scoped notes (one directory per machine/execution environment), starting with the orientation inventory that [agent-orientation](skills/agent-orientation/SKILL.md) produces. Never bootstrap-linked; each note self-guards with an applicability preamble. See [Environments](environments/README.md) for the convention (full scoping machinery deferred to #15).

## Solutions

A running knowledge base of solutions to recurring problems agents hit while working in the vault, organized by category. Add a note whenever you solve something worth not re-deriving later. See [Solutions](solutions/README.md) for the category index.

One example is included to show the format:

- [Relative Markdown Link Rules](solutions/obsidian-issues/wikilink-resolution-rules.md) — Portable source-relative links across Obsidian, VS Code, GitHub, and `brain`

## Related

- [AGENTS](../AGENTS.md) — Vault entrypoint and bootstrap sequence
- [CONVENTIONS](../00_Meta/CONVENTIONS.md) — Naming, tagging, and change control
- [PREFERENCES](../01_Profile/PREFERENCES.md) — Communication style and constraints
- [DEFAULTS](../01_Profile/DEFAULTS.md) — Timezone, locale, output defaults
