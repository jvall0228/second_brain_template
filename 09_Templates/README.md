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

All templates also carry `workflow/draft` in their suggested tags — an instantiated note keeps it until triage (see [[00_Meta/conventions#Tag Namespaces]]).

## Placeholder Syntax

- **Custom placeholders**: `{{UPPER_SNAKE_CASE}}` — literal text, fill in manually
- **Obsidian auto-fill**: `{{date}}`, `{{time}}`, `{{title}}` — replaced by Obsidian's core Templates plugin

## Related

- [[00_Meta/index]] — Full vault map
- [[00_Meta/conventions]] — Frontmatter and tagging rules
