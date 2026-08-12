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

1. **[AGENTS](AGENTS.md)** — You are here. Repo purpose, structure, and rules.
2. **[NOW](01_Profile/NOW.md)** — Current focus, active projects, key dates.
3. **[PREFERENCES](01_Profile/PREFERENCES.md)** — Communication style, output format, and constraints.
4. **[CONVENTIONS](00_Meta/CONVENTIONS.md)** — Naming, tagging, directory layout, and change-control rules.

After reading all four, the agent has enough context to begin work.

**Complete bootstrap** (required when creating structured notes or navigating beyond Inbox):

5. **[INDEX](00_Meta/INDEX.md)** — Global map of content.
6. **[DEFAULTS](01_Profile/DEFAULTS.md)** — Timezone, locale, units, default tags.

## Where Agents Write

Agent writes are **two-lane**, both review-gated:

- Output **for the vault** (captures, research, reports, proposals) goes to **`02_Inbox/`** unless explicitly directed elsewhere. This is the **Inbox-first rule** — a human reviews and triages Inbox contents into the appropriate PARA directory.
- Deliverables **for the world** (briefs, outlines, draft posts/emails) go to **`02_Outbox/`** via [express-packet](10_Agents/skills/express-packet/SKILL.md) — the owner reviews and ships; **agents never ship**. See [README](02_Outbox/README.md).

Standing exceptions:

- Agents may append solution notes to `10_Agents/solutions/` — see [README](10_Agents/README.md) — and rejection rows to the append-only log `10_Agents/docs/rejected-proposals.md` (the self-improve loop's memory).
- Only `brain {aymt,home} --write` may replace its exact generated file in `00_Meta/`; generic writes and hand edits remain forbidden.
- A live, user-invoked [agent-orientation](10_Agents/skills/agent-orientation/SKILL.md) session may write draft outputs to `10_Agents/environments/<env-slug>/`, `10_Agents/tools/<source>/`, and `10_Agents/skills/<source>-capture/`. Markdown uses `workflow/draft`; other bundle files inherit it until owner promotion.
- During a live [onboard-owner](10_Agents/skills/onboard-owner/SKILL.md) session, agents write interview results directly to `01_Profile/`, `03_Journal/people/` (owner-confirmed people notes), `04_Projects/`, and `05_Areas/` — and, in its context-specialization stage, rewrite the periodic templates in `09_Templates/` from `09_Templates/variants/` and record `context:` in `00_Meta/config.yaml`. The owner's in-the-moment approval is the review. Outside that session, Inbox-first applies as usual.

Template-shipped skills/tools, `00_Meta/config.yaml`, and named tagless entrypoint/editor/harness adapters are **canonical-by-policy** and use canonical change control. Location alone does not confer that state; orientation bundles stay draft until owner promotion.

See [README](02_Inbox/README.md) for triage instructions.

**Before your first commit, arm the pre-commit hook:** `git config core.hooksPath .githooks` (once per clone). The committed vault index (`10_Agents/tools/brain/vault-index.json`) regenerates through that hook; committing without it ships a stale index. Claude Code sessions arm it automatically (`.claude/settings.json`); every other environment runs it manually — or run `./brain index` (`brain index` after managed installation) before each commit. CI self-heals stragglers, but don't rely on it. In the same setup, install the generated-file merge driver: `git config merge.regenerate.driver true` (once per clone). It resolves merge conflicts in the two committed generated files (the vault index and `.vscode/second-brain.code-snippets`) by keeping ours; the post-merge hook then regenerates both, so generated content is never hand-merged. Without the driver, conflicts fall back to the recipe in [index-merge-conflicts](10_Agents/solutions/vault-tooling/index-merge-conflicts.md).

## Tagging Rules (Summary)

Tags live in YAML frontmatter under `tags:` as a list. Use **slash-delimited namespaces**:

| Namespace | Purpose | Examples |
|-----------|---------|----------|
| `audience/*` | Who the note is for | `audience/agent`, `audience/human` |
| `type/*` | What kind of note | `type/meta`, `type/reference`, `type/log` |
| `topic/*` | Subject matter (free-form) | `topic/software`, `topic/health` |
| `workflow/*` | Lifecycle stage | `workflow/canonical`, `workflow/draft` |
| `status/*` | Actionability | `status/active`, `status/someday` |

The authoritative taxonomy (full value lists) is [CONVENTIONS](00_Meta/CONVENTIONS.md#tag-namespaces).

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
- [template-project](09_Templates/template-project.md) — Projects with outcomes
- [template-area](09_Templates/template-area.md) — Ongoing responsibilities
- [template-resource](09_Templates/template-resource.md) — Reference material
- [template-zettel](09_Templates/template-zettel.md) — Atomic evergreen notes
- [template-daily-log](09_Templates/template-daily-log.md) — Daily journal entries
- [template-weekly-review](09_Templates/template-weekly-review.md) — Weekly reviews
- [template-monthly-review](09_Templates/template-monthly-review.md) — Monthly reviews
- [template-quarterly-review](09_Templates/template-quarterly-review.md) — Quarterly reviews
- [template-yearly-review](09_Templates/template-yearly-review.md) — Yearly reviews
- [template-media](09_Templates/template-media.md) — Media tracking
- [template-decision-record](09_Templates/template-decision-record.md) — Decision logs
- [template-comparison](09_Templates/template-comparison.md) — Option comparisons

See [README](09_Templates/README.md) for the full selection guide.

## Editor Surfaces

The vault supports two editors, and both are part of its contract: **Obsidian** (primary; config in `.obsidian/`) and **VS Code** (config in `.vscode/`; see [PRD](00_Meta/PRD.md) §6.5). Maintained internal links are source-relative inline Markdown with explicit extensions; Obsidian is configured to author that same portable form. If your change touches vault structure, navigation, templates, or link semantics, it must account for **both** surfaces — see the editor-surface parity item in the [OPERATING-RULES](10_Agents/docs/OPERATING-RULES.md) checklist. VS Code snippets are generated from `09_Templates/` by the pre-commit hook; never edit `.vscode/second-brain.code-snippets` by hand.

## Recency

To detect recent changes: check `updated:` fields, read [CHANGELOG](00_Meta/CHANGELOG.md), or use `git log`.

## Key Links

- Navigation: [INDEX](00_Meta/INDEX.md) — Full vault map
- Profile: [NOW](01_Profile/NOW.md) | [PREFERENCES](01_Profile/PREFERENCES.md) | [DEFAULTS](01_Profile/DEFAULTS.md)
- Conventions: [CONVENTIONS](00_Meta/CONVENTIONS.md)
- Inbox: [README](02_Inbox/README.md)
- PARA roots: [Projects](04_Projects/README.md) | [Areas](05_Areas/README.md) | [Resources](06_Resources/README.md) | [Archives](07_Archives/README.md)
- Agent docs: [README](10_Agents/README.md)
- The CODE loop: [README](10_Agents/skills/README.md) — stage → skill → directory map, and the cadence table
- Templates: [README](09_Templates/README.md)
