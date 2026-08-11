---
title: "Task Patterns"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Task Patterns

Rules for agent-created output in this vault. For general conventions, see [[00_Meta/CONVENTIONS]].

## Default Write Location

Agent output goes to `02_Inbox/` by default unless the human explicitly names a different destination or a documented standing exception below applies. This is the **Inbox-first rule**.

## Destination Policy

- Current active policy: write to `02_Inbox/` by default
- Other non-Inbox destinations require the human to name them in the current request
- Standing exception: solution notes may be added to `10_Agents/solutions/` (include `type/solution` in tags; see [[10_Agents/README]])
- Standing exception: a live, user-invoked `agent-orientation` session may write its environment inventory and paired draft bundle to `10_Agents/environments/<env-slug>/`, `10_Agents/tools/<source>/`, and `10_Agents/skills/<source>-capture/`; note files stay `workflow/draft`, and non-note tool files inherit that state
- Standing exception: a live `onboard-owner` session may write only the profile, people, project, area, template-specialization, and config outputs documented in that skill
- Standing exception: `self-improve` may append rejection rows to `10_Agents/docs/rejected-proposals.md`
- Roadmap items in planning docs do not override this active policy

Template-shipped skills/tools, `00_Meta/config.yaml`, and named tagless entrypoint/editor/harness adapters are canonical-by-policy and use canonical change control. An orientation bundle is not canonical merely because it lives under `10_Agents/`; owner promotion changes that state.

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

Use kebab-case by default: `research-rust-async-patterns.md`. Follow documented exceptions in [[00_Meta/CONVENTIONS#Filename Convention]].

For Inbox notes, prefix with the date: `YYYY-MM-DD-descriptive-slug.md`. Check whether the file already exists before writing; on collision, append a numeric suffix (`-2`) rather than overwriting.
