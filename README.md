---
title: "Second Brain Template"
tags:
  - type/meta
  - audience/human
updated: 2026-08-11
---

# Second Brain

A Git-synced, Markdown-first **personal knowledge vault** that doubles as a shared context layer for AI agents — readable in [Obsidian](https://obsidian.md) by you and by any agent with repo access.

This repository is a **template**. It ships the structure, conventions, note templates, and agent rules with all prior owner content removed and one worked example in each section. Fork it, delete the examples, and fill it with your own context.

## Why

Every AI conversation starts from scratch. This vault fixes that: a single source of truth for who you are, how you want output formatted, what you're working on, and what you know — so any agent can bootstrap itself without prior chat history.

## How it works

- **You** open this repo as an Obsidian vault (or edit the Markdown directly) to capture, organize, and review notes.
- **Agents** read a [bootstrap sequence](CONTEXT.md) to learn who you are, what you're working on, and how to behave — then write output to `02_Inbox/` for you to triage.
- **Git** tracks every change, making agent contributions auditable and reversible.

## Adopt this template

1. **Fork or clone** this repo (see *Personal vs work* below — you'll likely want one fork per context).
2. Open the folder as an **Obsidian vault**, or just edit the Markdown.
3. Work through `01_Profile/` — fill in `now`, `preferences`, `defaults`, `identity`, and `work`. These are what agents read first.
4. Skim [`00_Meta/conventions.md`](00_Meta/conventions.md) to learn the naming and tagging rules.
5. **Delete the seeded examples** once you've seen the pattern:
   - `04_Projects/example-project/`
   - `05_Areas/example-area/`
   - `06_Resources/example-resource.md`
   - `03_Journal/people/example-person.md`
   - `03_Journal/ideas/example-idea.md`
   - `03_Journal/periodic/daily/2025-01-15.md`
   - `03_Journal/periodic/weekly/2025-W03-review.md`
6. Start capturing into `02_Inbox/` and triage from there.

## Personal vs work

This template is **context-neutral** — nothing in it assumes personal or professional use. The recommended pattern is **one fork per context**:

- **Personal fork** (e.g. `second_brain`) — life, hobbies, health, side projects.
- **Work fork** (e.g. `second_brain-work`) — role, team context, work projects. Keep this fork private and mind your employer's confidentiality rules for anything you store in it.

Each fork is self-contained: same structure, different content. Keeping them separate prevents cross-contaminating personal and professional context when you point an agent at one.

## Structure

```
00_Meta/          Conventions, index, operating rules, changelog
01_Profile/       Identity, preferences, current focus (Now page)
02_Inbox/         Raw capture + agent output (triage queue)
03_Journal/       Daily/weekly logs, reviews, ideas, insights, people, plans
04_Projects/      Active projects with clear outcomes
05_Areas/         Ongoing areas of responsibility
06_Resources/     Reference material and topic notes
07_Archives/      Completed or inactive items
08_Assets/        Images, attachments, non-Markdown files
09_Templates/     Note templates
10_Agents/        Agent-facing docs and behavior rules
```

## Entrypoints

| Audience | Start here |
|----------|------------|
| Agents   | [CONTEXT.md](CONTEXT.md) (also aliased as `AGENTS.md` and `CLAUDE.md`) |
| Humans   | This file, then open as an Obsidian vault |

## Frameworks

- **[PARA](https://fortelabs.com/blog/para/)** for top-level organization (Projects / Areas / Resources / Archives)
- **Bullet Journal** for capture and review cadence
- **Zettelkasten** for atomic, linked evergreen notes

## Agent rules (summary)

- All agent output goes to `02_Inbox/` unless explicitly directed elsewhere.
- Every note must have YAML frontmatter with `title`, `tags`, and `updated`.
- Tags use slash-delimited namespaces (e.g. `type/meta`, `audience/agent`).
- Files marked `workflow/canonical` require a PR or explicit human approval to change — agents propose edits via an Inbox note (see [operating rules](10_Agents/docs/operating-rules.md)).

See [Conventions](00_Meta/conventions.md) for full details.
