---
title: "Agents"
tags:
  - audience/agent
  - type/meta
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# Second Brain

A personal knowledge vault for humans and AI agents. It is the source of truth for context, preferences, projects, and reference material, structured so agents can bootstrap without prior conversation history.

## Bootstrap Sequence (Must-Read Order)

**Public-only synthesis branches here, before loading personal context:** use the [policy-only route](00_Meta/restricted-private.md#public-only-synthesis) in a fresh context containing only policy instructions and admitted sources. Do not load the normal bootstrap below. If the harness cannot establish that isolation, report unsupported isolation without synthesizing; retrieval flags cannot cleanse earlier context.

**Minimum bootstrap** (normal internal tasks):

1. **[AGENTS](AGENTS.md)** — You are here. Repo purpose, structure, and rules.
2. **[NOW](01_Profile/NOW.md)** — Current focus, active projects, key dates.
3. **[PREFERENCES](01_Profile/PREFERENCES.md)** — Communication style, output format, and constraints.
4. **[CONVENTIONS](00_Meta/CONVENTIONS.md)** — Naming, tagging, directory layout, and change-control rules.

**Fast path:** `00_Meta/BOOTSTRAP.md` is all six docs compiled in this order, regenerated on every commit (`brain bootstrap --write`); read it as one file when your harness loads files one at a time. It is generated and pruned from the index — never edit or link it.

**Complete bootstrap** (required when creating structured notes or navigating beyond Inbox):

5. **[INDEX](00_Meta/INDEX.md)** — Global map of content.
6. **[DEFAULTS](01_Profile/DEFAULTS.md)** — Timezone, locale, units, default tags.

## Entity Continuity

Before writing, search for established people, pets, Projects, Areas, and recurring entities. Link the first meaningful mention to its existing home; do not create duplicates. Prefer linking `restricted/private` entities; a note that carries their private substance inherits the tag. See [CONVENTIONS](00_Meta/CONVENTIONS.md#established-entity-links).

## Where Agents Write

Write authority follows **execution class**: every run is **interactive** (a foreground, user-directed conversation) or **autonomous** (scheduled, headless, recurring, or automation-driven; missing trusted execution metadata defaults here). Subagents inherit the parent's class within the delegated scope. The single full statement is the [Write Authority Contract](10_Agents/docs/write-authority.md); this table is the summary.

| Class | May write | Review |
|-------|-----------|--------|
| Interactive | Any appropriate non-generated location, `workflow/canonical` notes included, when the user-directed task reasonably requires it | Scoped diff, validation, and a [CHANGELOG](00_Meta/CHANGELOG.md) entry when the canonical contract calls for one |
| Autonomous | New content to `02_Inbox/` only (the **Inbox-first rule**); existing notes only through the contract's standing exceptions | Human triage |
| Either | Deliverables for the world to `02_Outbox/` via [express-packet](10_Agents/skills/express-packet/SKILL.md); generated files only through their owning command | Owner reviews and ships — **agents never ship** |

Template-shipped skills/tools, `00_Meta/config.yaml`, and named tagless entrypoint, editor, and harness adapters are [canonical-by-policy](10_Agents/docs/write-authority.md#canonical-by-policy). See [README](02_Inbox/README.md) for triage instructions.

**Before your first commit, configure the hooks:** `git config core.hooksPath .githooks` and `git config merge.regenerate.driver true` (once per clone). Commit and merge hooks generate and validate from the staged snapshot, preserving unstaged source edits. The merge driver keeps ours for generated conflicts; a merge needing regeneration pauses for `git commit` to record the fresh staged output. Automatic read-only CI checks committed consistency; manual repair is separate. Post-merge checks report stale committed content without changing history. Generated content is never hand-merged; see [index-merge-conflicts](10_Agents/solutions/vault-tooling/index-merge-conflicts.md). Use separate worktrees for concurrent agents; a shared checkout requires conflict-detecting publication and rollback.

## Tagging Rules (Summary)

Tags live in YAML frontmatter under `tags:` as a list. Use **slash-delimited namespaces**:

| Namespace | Purpose | Examples |
|-----------|---------|----------|
| `audience/*` | Who the note is for | `audience/agent`, `audience/human` |
| `type/*` | What kind of note | `type/meta`, `type/reference`, `type/log` |
| `topic/*` | Subject matter (free-form) | `topic/software`, `topic/health` |
| `workflow/*` | Lifecycle stage | `workflow/canonical`, `workflow/draft` |
| `status/*` | Actionability | `status/active`, `status/deprioritized` |

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
| `04_Projects/` | Projects with bounded outcomes |
| `05_Areas/` | Ongoing areas of responsibility |
| `06_Resources/` | Reference material and topic notes |
| `07_Archives/` | Completed or inactive items |
| `08_Assets/` | Images, attachments, non-markdown files |
| `09_Templates/` | Note templates |
| `10_Agents/` | Agent-facing documentation and behavior rules |

## Templates

When creating structured notes, use templates from `09_Templates/`. The [README](09_Templates/README.md) is the selection guide — every template, what it is for, and when to use it.

## Editor Surfaces

**Obsidian** and **VS Code** are both supported (see [PRD](00_Meta/PRD.md) §6.5). Maintained links use source-relative Markdown with explicit extensions. Changes to structure, navigation, templates, or links must preserve both surfaces; see [OPERATING-RULES](10_Agents/docs/OPERATING-RULES.md). VS Code snippets regenerate from templates; never hand-edit them.

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
