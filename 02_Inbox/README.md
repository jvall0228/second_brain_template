---
title: "Inbox"
tags:
  - type/meta
  - audience/agent
  - audience/human
updated: 2026-09-04
---

# Inbox

This is the landing zone for untriaged content — raw capture, unsorted notes, and new content from autonomous agent sessions (the Inbox-first rule; interactive user-directed work files directly to its durable home per [AGENTS](../AGENTS.md#where-agents-write)). Everything placed here is considered **untriaged**. A human periodically reviews Inbox contents and moves them to the appropriate PARA directory (`04_Projects/`, `05_Areas/`, `06_Resources/`, or `07_Archives/`) or into `03_Journal/`, and the filing is traced in the periodic notes for the capture's event date (see [triage-inbox](../10_Agents/skills/triage-inbox/SKILL.md) — a capture triages to both PARA and the Journal). Evergreen atomic notes (`type/zettel`) are triaged to `06_Resources/`. Notes that don't belong anywhere may be deleted or merged.

When creating a new note here, include frontmatter with at least `title`, `tags` (including `audience/agent` if agent-generated), and `updated`. Use `workflow/draft` as the default workflow tag for Inbox items. Name notes `YYYY-MM-DD-descriptive-slug.md`; on a filename collision, append a numeric suffix rather than overwriting.
