---
title: "Second Brain Template"
tags:
  - type/meta
  - audience/human
updated: 2026-08-11
expires: 2027-08-11
---

# Second Brain

A Git-synced, Markdown-first **personal knowledge vault** that doubles as a shared context layer for AI agents — readable in [Obsidian](https://obsidian.md) by you and by any agent with repo access.

This repository is a **template**. It ships the structure, conventions, note templates, and agent rules with all prior owner content removed and one worked example in each section. Fork it, delete the examples, and fill it with your own context.

## Open with an AI agent

New here? Hand this repo to an assistant with one click — it reads [AGENTS.md](AGENTS.md), bootstraps itself, and walks you through setup conversationally (no technical background needed):

[![Open in Claude Code](.github/badges/claude-code.svg)](https://claude.ai/code/new?q=Help%20me%20setup%20https%3A%2F%2Fgithub.com%2Fjvall0228%2Fsecond_brain_template&repo=jvall0228%2Fsecond_brain_template)
[![Open in Claude Web](.github/badges/claude-web.svg)](https://claude.ai/new?q=Help%20me%20setup%20https%3A%2F%2Fgithub.com%2Fjvall0228%2Fsecond_brain_template)
[![Open in ChatGPT](.github/badges/chatgpt-web.svg)](https://chatgpt.com/?surface=tpp&skip_instant_query=1&q=Help%20me%20get%20started%20with%20https%3A%2F%2Fgithub.com%2Fjvall0228%2Fsecond_brain_template)

**Claude Code** drops you straight into the repo. Prefer the **desktop app**? GitHub can't make `claude://` / `codex://` links clickable, so copy one into your browser's address bar:

```
# Claude desktop — Cowork
claude://cowork/new?q=Help%20me%20setup%20https%3A%2F%2Fgithub.com%2Fjvall0228%2Fsecond_brain_template

# Claude desktop — chat instead of Cowork
claude://claude.ai/new?q=Help%20me%20setup%20https%3A%2F%2Fgithub.com%2Fjvall0228%2Fsecond_brain_template

# ChatGPT desktop (Codex)
codex://threads/new?prompt=Help%20me%20get%20started%20with%20https%3A%2F%2Fgithub.com%2Fjvall0228%2Fsecond_brain_template
```

Rather set it up yourself? The manual steps are in [Adopt this template](#adopt-this-template) below.

## Why

Every AI conversation starts from scratch. This vault fixes that: a single source of truth for who you are, how you want output formatted, what you're working on, and what you know — so any agent can bootstrap itself without prior chat history.

## How it works

- **You** open this repo as an Obsidian vault (or edit the Markdown directly) to capture, organize, and review notes.
- **Agents** read a [bootstrap sequence](AGENTS.md) to learn who you are, what you're working on, and how to behave — then write output to `02_Inbox/` for you to triage.
- **Git** tracks every change, making agent contributions auditable and reversible.

## Adopt this template

> **Prefer a guided setup?** Point an AI assistant (Claude Code, Codex, etc.) at your fork and ask it to *onboard me* — the [onboard-owner](10_Agents/skills/onboard-owner/SKILL.md) skill walks you through everything below conversationally, does the mechanical steps for you, and assumes no technical background.

1. **Fork or clone** this repo (see *Personal vs work* below — you'll likely want one fork per context).
2. Open the folder as an **Obsidian vault**, in **VS Code** (shipped `.vscode/` config recommends a small first-party extension set and adds brain/daily-note tasks and template snippets — see `00_Meta/prd.md` §6.5), or just edit the Markdown.
3. Work through `01_Profile/` — fill in `now`, `preferences`, `defaults`, `identity`, and `work`. These are what agents read first.
4. Skim [`00_Meta/conventions.md`](00_Meta/conventions.md) to learn the naming and tagging rules.
5. **Install the pre-commit hook** so every commit keeps the vault index, VS Code snippets, and repository skill adapters fresh and the conventions enforced, and **the merge driver** so committed generated files never need hand-merging:
   ```
   git config core.hooksPath .githooks
   git config merge.regenerate.driver true
   ```
   The driver keeps "ours" on conflict (`true` exits 0 leaving the file as-is); correctness comes from regeneration — the post-merge and pre-commit hooks rebuild the index, snippets, and adapters, and CI checks freshness. Clones without the driver just get a normal conflict (see the [fallback recipe](10_Agents/solutions/vault-tooling/index-merge-conflicts.md)).
6. **Remove the seeded examples as one bundle** once you've seen the pattern.
   `10_Agents/tools/adopt_examples.json` is the sole bundle authority; never
   delete an example selectively. Preview every deletion and marked reference
   edit, save that machine-readable plan outside the vault, then apply the
   exact approved plan:

   ```sh
   # macOS/Linux: keep the plan outside the vault
   python3 10_Agents/tools/adopt_check.py plan --output "${TMPDIR:-/tmp}/second-brain-adopt-plan.json"
   python3 10_Agents/tools/adopt_check.py apply "${TMPDIR:-/tmp}/second-brain-adopt-plan.json"
   ```

   On Windows PowerShell, use
   `$env:TEMP\second-brain-adopt-plan.json` for the same external plan path.

   Apply refuses missing examples, ignored or untracked occupants, unmarked
   surviving links, dirty or changed inputs (including the validator), unsafe
   paths, and stale plans. It rolls back the whole bundle if index regeneration
   or independent post-apply verification fails. If an interruption leaves the
   durable cleanup lock in place, run `python3 10_Agents/tools/adopt_check.py recover`
   rather than deleting recovery state by hand. CI's no-argument adopter smoke test replays the
   atomic cleanup, fills `01_Profile/`, makes a first capture, and requires zero
   validation errors.
7. Start capturing into `02_Inbox/` and triage from there.

## Validation and the vault index

The vault ships a zero-dependency CLI, [`brain`](10_Agents/tools/brain/spec.md), that indexes every note and enforces the conventions (Python 3.10+, stdlib only):

```
./brain validate   # frontmatter, tags, filenames, wikilinks
./brain search <q> # plus: list, links, tags, show, recent
```

The committed index at `10_Agents/tools/brain/vault-index.json` gives agents structured vault access without running anything. The pre-commit hook (step 5 above) regenerates it on every commit and blocks commits that break the conventions; a GitHub Actions workflow re-checks both on push as a backstop.

## Personal vs work

This template is **context-neutral** — nothing in it assumes personal or professional use. The recommended pattern is **one fork per context**:

- **Personal fork** (e.g. `second_brain`) — life, hobbies, health, side projects.
- **Work fork** (e.g. `second_brain-work`) — role, team context, work projects. Keep this fork private and mind your employer's confidentiality rules for anything you store in it.

Each fork is self-contained: same structure, different content. Keeping them separate prevents cross-contaminating personal and professional context when you point an agent at one.

## Structure

```
00_Meta/          Conventions, index, changelog, PRD, status
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
| Agents   | [AGENTS.md](AGENTS.md) (Claude Code loads `CLAUDE.md`, which imports it via `@AGENTS.md`) |
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
