---
title: "Task Patterns"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-02-21
---

# Task Patterns

Rules for agent-created output in this vault. For general conventions, see [[00_Meta/conventions]].

## Default Write Location

All agent output goes to `02_Inbox/` unless the human explicitly names a different destination. This is the **Inbox-first rule**.

## Destination Policy

- Current active policy: write to `02_Inbox/` by default
- Non-Inbox destinations are allowed only when the human explicitly names the destination in the current request
- Roadmap items in planning docs do not override this active policy

## Required Frontmatter

Every agent-created note must include:

```yaml
---
title: "Descriptive Title"
tags:
  - audience/agent
  - workflow/draft
  - type/<appropriate-type>
updated: YYYY-MM-DD
---
```

Use the actual date, not a placeholder. The `workflow/draft` tag signals the note needs human triage.

Exception: files inside `09_Templates/` may include placeholders such as `{{date}}` until a note is instantiated.

## Example Agent-Created Note

```markdown
---
title: "Research: Rust Async Patterns"
tags:
  - audience/agent
  - workflow/draft
  - type/reference
updated: 2026-02-21
---

# Research: Rust Async Patterns

## Summary

[Content here]

## Sources

- [Source 1]
- [Source 2]
```

## Filename Convention

Use kebab-case by default: `research-rust-async-patterns.md`. Follow documented exceptions in [[00_Meta/conventions#Filename Convention]].
