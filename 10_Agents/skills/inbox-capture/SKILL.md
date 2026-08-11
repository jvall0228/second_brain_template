---
name: inbox-capture
description: Capture new content into the vault's Inbox as a correctly formatted note. Use whenever you produce output for the vault and no explicit destination was given — the Inbox-first rule makes 02_Inbox/ the default landing zone.
title: "Skill: Inbox Capture"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
---

# Inbox Capture

Write a new note to `02_Inbox/` that passes validation on the first try.

## Steps

1. **Name the file** `YYYY-MM-DD-descriptive-slug.md` (today's date, kebab-case slug). Check for an existing file with that name first; on collision append a numeric suffix (`-2`, `-3`). Never overwrite another note.
2. **Write frontmatter** — required on every note:
   ```yaml
   ---
   title: "Human-Readable Title"
   tags:
     - audience/agent
     - type/note
     - workflow/draft
   updated: YYYY-MM-DD
   ---
   ```
   Pick the `type/*` that fits (see the authoritative table in `00_Meta/conventions.md` § Tag Namespaces); add free-form `topic/*` tags as useful. Agent-created notes always carry `audience/agent` and start `workflow/draft`.
3. **Write the body.** Wikilink related notes — bare filename within the same directory, full path (`[[06_Resources/example-resource|Display]]`) across directories.
4. **Validate:** `python3 10_Agents/tools/brain/brain.py validate` — fix any error it reports before committing.
5. **Commit** with a short descriptive message (the pre-commit hook re-validates and refreshes the index).

## Rules

- `02_Inbox/` is the only default destination; write elsewhere only when the human explicitly directs it (or use the `solution-capture` skill for `10_Agents/solutions/`).
- A human triages the Inbox later (`triage-inbox` skill) — don't move your own notes out.

## References

- `00_Meta/conventions.md` — frontmatter, tags, filenames
- `02_Inbox/README.md` — Inbox rules and triage flow
- `10_Agents/docs/task-patterns.md` — worked examples
