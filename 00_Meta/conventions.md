---
title: "Conventions"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-11
---

# Conventions

Rules governing how notes are created, named, tagged, and organized in this vault.

## Directory Structure

Top-level directories use **numeric prefixes** for deterministic sort order. Each serves a distinct purpose:

- `00_Meta/` — Vault-level meta docs (this file lives here).
- `01_Profile/` — Owner identity and context (Now, Preferences).
- `02_Inbox/` — Landing zone for all new and unsorted content.
- `03_Journal/` — Personal knowledge and experience (periodic notes + ideas, insights, memories, people, plans).
- `04_Projects/` — Active projects with defined outcomes (PARA: Projects).
- `05_Areas/` — Ongoing responsibilities (PARA: Areas).
- `06_Resources/` — Reference material and topic notes (PARA: Resources).
- `07_Archives/` — Inactive or completed items (PARA: Archives).
- `08_Assets/` — Non-markdown files (images, PDFs, attachments).
- `09_Templates/` — Reusable note templates.
- `10_Agents/` — Agent-facing documentation and behavior rules.

## Filename Convention

Use **kebab-case** by default for filenames: `my-note-title.md`.

Allowed exceptions:
- Entrypoints: `AGENTS.md`, `CLAUDE.md`, `README.md` (uppercase by convention). These may appear at the vault root or at any directory level (e.g., `04_Projects/example-project/README.md`).
- Periodic review filenames may use ISO week/quarter tokens:
  - `YYYY-W##-review.md` (weekly)
  - `YYYY-Q#-review.md` (quarterly)

## Locale & Output Defaults

For timezone, date format, units, and other machine-readable defaults, see [[01_Profile/defaults]].

## Frontmatter Requirements

Every markdown note **must** include YAML frontmatter with at minimum:

```yaml
---
title: "Note Title"
tags:
  - namespace/value
updated: YYYY-MM-DD
---
```

### Template Placeholder Exception

Files in `09_Templates/` may use placeholder tokens such as `{{date}}`, `{{title}}`, and `{{...}}` in frontmatter and body. Any instantiated note created from a template must replace placeholders and set `updated` to a real ISO date.

### Adapter File Exception

`CLAUDE.md` at the vault root carries no frontmatter: it is a one-line adapter (`@AGENTS.md`) that Claude Code expands into the [[AGENTS]] entrypoint, not a note. It follows canonical change control despite having no tags.

## Tag Namespaces

Tags use **slash-delimited namespaces**. **This table is the authoritative tag taxonomy** — other documents (including [[00_Meta/prd]] and [[AGENTS]]) summarize it. Current namespaces:

| Namespace | Purpose | Values |
|-----------|---------|--------|
| `audience/*` | Who the note is for | `agent`, `human` |
| `type/*` | Kind of content | `meta`, `reference`, `log`, `note`, `idea`, `plan`, `project`, `area`, `resource`, `zettel`, `journal`, `decision`, `solution` |
| `topic/*` | Subject matter | Free-form (e.g., `software`, `physics`, `health`, `ttrpg`, `finance`, `identity`) |
| `workflow/*` | Lifecycle stage | `canonical`, `draft`, `review`, `needs-review` |
| `status/*` | Actionability | `active`, `someday`, `done` |

Notes tagged `workflow/canonical` are foundational vault docs. They require a PR or explicit human approval to modify.

## Agent Write Rules

Agents write to `02_Inbox/` by default. Agents may write elsewhere only when the human explicitly directs the destination. Every agent-created note must include valid frontmatter with `title`, `tags` (including `audience/agent`), and `updated`.

**Standing exception:** agents may append solution notes to `10_Agents/solutions/` (see [[10_Agents/README]]) with required frontmatter including `type/solution`.

**Filename collisions:** name Inbox notes `YYYY-MM-DD-descriptive-slug.md`. Before writing, check whether the file already exists; on collision, append a numeric suffix (`-2`). Never overwrite another agent's note.

See [[02_Inbox/README]] for Inbox-specific guidance.

## Change Control

| Scope | Method |
|-------|--------|
| `workflow/canonical` notes | PR or explicit human approval required |
| `02_Inbox/` content | Direct commits allowed |
| All other notes | Direct commits allowed |

Canonical notes form the vault's structural foundation — changes to them affect agent behavior across all sessions.

For expanded agent guidance, see [[10_Agents/README]].

## Recency

Agents detecting what changed:
1. Check `updated:` field in frontmatter (primary signal)
2. Read [[00_Meta/changelog]] for structural changes
3. Use `git log -n 10` for detailed file-level history

**Duty to bump:** any edit to a note — creation or modification — must set `updated:` to the current date. The recency signal decays without this.

Agents should **not** re-read files whose `updated:` date hasn't changed since last read. `updated:` has day granularity: for same-day changes, `git log` is authoritative.
