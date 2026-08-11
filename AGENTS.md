---
title: "Agents"
tags:
  - audience/agent
  - type/meta
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Second Brain

A personal knowledge management vault designed for both human and AI agent use. It serves as a single source of truth for context, preferences, projects, and reference material — structured so that any agent can bootstrap itself and produce useful output without prior conversation history.

## Bootstrap Sequence (Must-Read Order)

**Minimum bootstrap** (required for all agents):

1. **[[AGENTS]]** — You are here. Repo purpose, structure, and rules.
2. **[[01_Profile/now]]** — Current focus, active projects, key dates.
3. **[[01_Profile/preferences]]** — Communication style, output format, and constraints.
4. **[[00_Meta/conventions]]** — Naming, tagging, directory layout, and change-control rules.

After reading all four, the agent has enough context to begin work.

**Complete bootstrap** (required when creating structured notes or navigating beyond Inbox):

5. **[[00_Meta/index]]** — Global map of content.
6. **[[01_Profile/defaults]]** — Timezone, locale, units, default tags.

## Where Agents Write

Agent writes are **two-lane**, both review-gated:

- Output **for the vault** (captures, research, reports, proposals) goes to **`02_Inbox/`** unless explicitly directed elsewhere. This is the **Inbox-first rule** — a human reviews and triages Inbox contents into the appropriate PARA directory.
- Deliverables **for the world** (briefs, outlines, draft posts/emails) go to **`02_Outbox/`** via [[10_Agents/skills/express-packet/SKILL|express-packet]] — the owner reviews and ships; **agents never ship**. See [[02_Outbox/README]].

Standing exceptions:

- Agents may append solution notes to `10_Agents/solutions/` — see [[10_Agents/README]] — and rejection rows to the append-only log `10_Agents/docs/rejected-proposals.md` (the self-improve loop's memory).
- A live, user-invoked [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] session may write draft outputs to `10_Agents/environments/<env-slug>/`, `10_Agents/tools/<source>/`, and `10_Agents/skills/<source>-capture/`. Markdown uses `workflow/draft`; other bundle files inherit it until owner promotion.
- During a live [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] session, agents write interview results directly to `01_Profile/`, `03_Journal/people/` (owner-confirmed people notes), `04_Projects/`, and `05_Areas/` — and, in its context-specialization stage, rewrite the periodic templates in `09_Templates/` from `09_Templates/variants/` and record `context:` in `00_Meta/config.yaml`. The owner's in-the-moment approval is the review. Outside that session, Inbox-first applies as usual.

Template-shipped skills/tools, `00_Meta/config.yaml`, and named tagless entrypoint/editor/harness adapters are **canonical-by-policy** and use canonical change control. Location alone does not confer that state; orientation bundles stay draft until owner promotion.

See [[02_Inbox/README]] for triage instructions.

**Before your first commit, arm the pre-commit hook:** `git config core.hooksPath .githooks` (once per clone). The committed vault index (`10_Agents/tools/brain/vault-index.json`) regenerates through that hook; committing without it ships a stale index. Claude Code sessions arm it automatically (`.claude/settings.json`); every other environment runs it manually — or run `python3 10_Agents/tools/brain/brain.py index` before each commit. CI self-heals stragglers, but don't rely on it. In the same setup, install the generated-file merge driver: `git config merge.regenerate.driver true` (once per clone). It resolves merge conflicts in the two committed generated files (the vault index and `.vscode/second-brain.code-snippets`) by keeping ours; the post-merge hook then regenerates both, so generated content is never hand-merged. Without the driver, conflicts fall back to the recipe in [[10_Agents/solutions/vault-tooling/index-merge-conflicts]].

## Tagging Rules (Summary)

Tags live in YAML frontmatter under `tags:` as a list. Use **slash-delimited namespaces**:

| Namespace | Purpose | Examples |
|-----------|---------|----------|
| `audience/*` | Who the note is for | `audience/agent`, `audience/human` |
| `type/*` | What kind of note | `type/meta`, `type/reference`, `type/log` |
| `topic/*` | Subject matter (free-form) | `topic/software`, `topic/health` |
| `workflow/*` | Lifecycle stage | `workflow/canonical`, `workflow/draft` |
| `status/*` | Actionability | `status/active`, `status/someday` |

The authoritative taxonomy (full value lists) is [[00_Meta/conventions#Tag Namespaces]].

Every note **must** have frontmatter with at least `title`, `tags`, and `updated`. When you edit an existing note, bump `updated:` to the current date.

## Vault Structure

Directories use numbered prefixes for sort stability. Each directory has a README explaining what belongs there.

| Directory | Purpose |
|-----------|---------|
| `00_Meta/` | Vault-level conventions and meta docs |
| `01_Profile/` | Owner context: Now page, preferences |
| `02_Inbox/` | Raw capture, agent output, unsorted notes |
| `02_Outbox/` | Outbound deliverables awaiting owner review and shipping |
| `03_Journal/` | Personal knowledge and experience |
| `04_Projects/` | Active projects with clear outcomes |
| `05_Areas/` | Ongoing areas of responsibility |
| `06_Resources/` | Reference material and topic notes |
| `07_Archives/` | Completed or inactive items |
| `08_Assets/` | Images, attachments, non-markdown files |
| `09_Templates/` | Note templates |
| `10_Agents/` | Agent-facing documentation and behavior rules |

## Templates

When creating structured notes, use templates from `09_Templates/`:
- [[09_Templates/template-project]] — Projects with outcomes
- [[09_Templates/template-area]] — Ongoing responsibilities
- [[09_Templates/template-resource]] — Reference material
- [[09_Templates/template-zettel]] — Atomic evergreen notes
- [[09_Templates/template-daily-log]] — Daily journal entries
- [[09_Templates/template-weekly-review]] — Weekly reviews
- [[09_Templates/template-monthly-review]] — Monthly reviews
- [[09_Templates/template-quarterly-review]] — Quarterly reviews
- [[09_Templates/template-yearly-review]] — Yearly reviews
- [[09_Templates/template-media]] — Media tracking
- [[09_Templates/template-decision-record]] — Decision logs
- [[09_Templates/template-comparison]] — Option comparisons

See [[09_Templates/README]] for the full selection guide.

## Editor Surfaces

The vault supports two editors, and both are part of its contract: **Obsidian** (primary; config in `.obsidian/`) and **VS Code** (config in `.vscode/`; see [[00_Meta/prd]] §6.5). If your change touches vault structure, navigation, templates, or link semantics, it must account for **both** surfaces — see the editor-surface parity item in the [[10_Agents/docs/operating-rules]] checklist. VS Code snippets are generated from `09_Templates/` by the pre-commit hook; never edit `.vscode/second-brain.code-snippets` by hand.

## Recency

To detect recent changes: check `updated:` fields, read [[00_Meta/changelog]], or use `git log`.

## Key Links

- Navigation: [[00_Meta/index]] — Full vault map
- Profile: [[01_Profile/now]] | [[01_Profile/preferences]] | [[01_Profile/defaults]]
- Conventions: [[00_Meta/conventions]]
- Inbox: [[02_Inbox/README]]
- PARA roots: [[04_Projects/README|Projects]] | [[05_Areas/README|Areas]] | [[06_Resources/README|Resources]] | [[07_Archives/README|Archives]]
- Agent docs: [[10_Agents/README]]
- The CODE loop: [[10_Agents/skills/README]] — stage → skill → directory map, and the cadence table
- Templates: [[09_Templates/README]]
