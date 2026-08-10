---
title: "Operating Rules"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-02-21
---

# Operating Rules

Behavior expectations for agents working in this vault. These supplement — not duplicate — the rules in [[CONTEXT]] and [[00_Meta/conventions]].

## Bootstrap Before Working

Always read the bootstrap sequence before producing output. See [[CONTEXT#Bootstrap Sequence (Must-Read Order)]].

## Read Before Write

Before creating or modifying a note, read:

1. The target directory's README (e.g., `04_Projects/README.md`)
2. Any existing note you're about to update
3. Relevant templates from `09_Templates/`

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
- [ ] Tags use defined namespaces (see [[00_Meta/conventions#Tag Namespaces]])
- [ ] Filename follows [[00_Meta/conventions#Filename Convention]]
- [ ] Destination is `02_Inbox/` (unless explicitly directed elsewhere)

## Related

- [[CONTEXT]] — Vault entrypoint
- [[00_Meta/conventions]] — Full convention reference
- [[10_Agents/docs/task-patterns]] — Write rules and examples
