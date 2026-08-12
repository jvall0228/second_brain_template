---
title: "Templates"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-11
---

# Templates

Reusable note templates for creating structured content. Use these when creating new notes to ensure consistent frontmatter, tags, and section headings.

## Template Selection Guide

| Note Type | Template | Required Tags | Destination |
|-----------|----------|---------------|-------------|
| New project | `template-project.md` | `type/project`, `status/active` | `04_Projects/` |
| Area of responsibility | `template-area.md` | `type/area` | `05_Areas/` |
| Reference note | `template-resource.md` | `type/resource` | `06_Resources/` |
| Atomic evergreen note | `template-zettel.md` | `type/zettel` | `06_Resources/` |
| Daily log | `template-daily-log.md` | `type/journal` | `03_Journal/periodic/daily/` |
| Weekly review | `template-weekly-review.md` | `type/journal` | `03_Journal/periodic/weekly/` |
| Monthly review | `template-monthly-review.md` | `type/journal` | `03_Journal/periodic/monthly/` |
| Quarterly review | `template-quarterly-review.md` | `type/journal` | `03_Journal/periodic/quarterly/` |
| Yearly review | `template-yearly-review.md` | `type/journal` | `03_Journal/periodic/yearly/` |
| Media tracking | `template-media.md` | `type/resource` | `06_Resources/` |
| Decision record | `template-decision-record.md` | `type/decision` | `04_Projects/` or `06_Resources/` |
| Comparison | `template-comparison.md` | `type/reference` | `06_Resources/` |

All templates also carry `workflow/draft` in their suggested tags — an instantiated note keeps it until triage (see [CONVENTIONS](../00_Meta/CONVENTIONS.md#tag-namespaces)).

## Variants (`variants/`)

`variants/` holds context-specific **source material** — currently work-context versions of the daily log and weekly review — used by [onboard-owner](../10_Agents/skills/onboard-owner/SKILL.md)'s context-specialization step to rewrite the shipped periodic templates in place for a work fork. Variant files are **not** templates: nothing resolves them by name, and snippet generation ignores them. See [README](variants/README.md).

## Placeholder Syntax

- **Custom placeholders**: `{{UPPER_SNAKE_CASE}}` — literal text, fill in manually
- **Obsidian auto-fill**: `{{date}}`, `{{time}}`, `{{title}}` — replaced by Obsidian's core Templates plugin
- **Link placeholders**: `[human label]({{TOKEN}})` — replace each destination token with a complete source-relative, percent-encoded path including `.md` (or the asset extension); the token is never the label

## Related

- [INDEX](../00_Meta/INDEX.md) — Full vault map
- [CONVENTIONS](../00_Meta/CONVENTIONS.md) — Frontmatter and tagging rules
