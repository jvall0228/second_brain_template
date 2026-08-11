---
title: "Operating Rules"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
---

# Operating Rules

Behavior expectations for agents working in this vault. These supplement — not duplicate — the rules in [[AGENTS]] and [[00_Meta/conventions]].

## Bootstrap Before Working

Always read the bootstrap sequence before producing output. See [[AGENTS#Bootstrap Sequence (Must-Read Order)]].

## Read Before Write

Before creating or modifying a note, read:

1. The target directory's README (e.g., `04_Projects/README.md`)
2. Any existing note you're about to update
3. Relevant templates from `09_Templates/`

## Update by Replacement, Not Accumulation

When updating an existing note, **replace** the sections the new content conflicts with or obsoletes — never append a new section alongside a stale one. Append-only editing bloats notes into contradictory context dumps that mislead every future reader, human or agent. A note must always read as the current state of knowledge; git history preserves every prior version for posterity, so deleting outdated content loses nothing. Appending is right only for genuinely additive structures — logs, journals, changelog-style records — where entries are events, not claims.

## Canonical Note Handling

Notes tagged `workflow/canonical` are vault infrastructure. Agents must **not** modify them directly.

To propose a change to a canonical note:

1. Write a note to `02_Inbox/` explaining the proposed change
2. Tag it `workflow/needs-review`
3. Reference the canonical note with a wikilink

The human reviews and applies (or rejects) the change.

## Self-Validation

Before writing any note, verify:

- [ ] Frontmatter includes `title`, `tags`, `updated`
- [ ] `updated:` is set to today's date — on every edit, not just creation
- [ ] Tags use defined namespaces (see [[00_Meta/conventions#Tag Namespaces]])
- [ ] Filename follows [[00_Meta/conventions#Filename Convention]] and does not collide with an existing note
- [ ] Destination is `02_Inbox/` (unless explicitly directed elsewhere, or a `10_Agents/solutions/` note)
- [ ] Run `python3 10_Agents/tools/brain/brain.py validate` after writing — fix any errors it reports before committing (the pre-commit hook enforces this; see [[10_Agents/tools/brain/README|brain]])
- [ ] **Editor-surface parity** ([[00_Meta/prd]] §6.5): if the change alters vault structure, navigation, or templates, update both editor surfaces — `.obsidian/` and `.vscode/` (settings/tasks by hand; snippets regenerate automatically via the pre-commit hook) — and the §6.5 feature mapping

## Concurrency

Multiple agents may work in this vault. Sync (pull) before writing when the environment allows, keep commits small, and never force-push. Merge conflicts are resolved by the human.

## Related

- [[AGENTS]] — Vault entrypoint
- [[00_Meta/conventions]] — Full convention reference
- [[10_Agents/docs/task-patterns]] — Write rules and examples
