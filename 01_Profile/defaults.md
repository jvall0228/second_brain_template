---
title: "Defaults"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-10
---

# Defaults

Machine-readable defaults for agent output. Agents apply these unless you override per-conversation.

> **Template note:** Update the locale and units to your own, then delete this callout.

## Locale

| Setting     | Value                           |
| ----------- | ------------------------------- |
| Timezone    | <!-- e.g. America/New_York -->  |
| Date format | ISO `YYYY-MM-DD`                |
| Time format | <!-- 12h or 24h -->             |
| Language    | <!-- e.g. en-US -->             |

## Units

| Setting     | Value                       |
|-------------|-----------------------------|
| Measurement | <!-- Metric or Imperial --> |
| Currency    | <!-- e.g. USD -->           |

## Agent Output Defaults

| Setting | Value |
|---------|-------|
| Default write location | `02_Inbox/` |
| Default tags for new notes | `audience/agent`, `workflow/draft` |
| Filename format | `kebab-case.md` |
| Frontmatter fields required | `title`, `tags`, `updated` |
