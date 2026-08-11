---
title: "Conventions"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-11
expires: 2027-08-11
---

# Conventions

Rules governing how notes are created, named, tagged, and organized in this vault.

## Directory Structure

Top-level directories use **numeric prefixes** for deterministic sort order. Each serves a distinct purpose:

- `00_Meta/` — Vault-level meta docs (this file lives here).
- `01_Profile/` — Owner identity and context (Now, Preferences).
- `02_Inbox/` — Landing zone for all new and unsorted content.
- `02_Outbox/` — Outbound deliverables awaiting owner review and shipping (shares the `02_` prefix: both are review gates, no renumbering).
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
- Skill manifests: `SKILL.md` inside `10_Agents/skills/<skill-name>/` (the Agent Skills format requires this exact name).
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

### Expiration (`expires:`)

Knowledge notes carry an optional-but-expected `expires: YYYY-MM-DD` — a best-effort "re-verify by" date set at write time, **hard-capped at one year** after `updated:`. It drives the curation loop (`brain curate` + the curate skill): claims decay, and the date says how fast.

Default TTLs by volatility:

| Content | TTL | Examples |
|---------|-----|----------|
| Wiring / product facts | 3 months | harness wiring docs, tool-surface research |
| Retrieval-dated research | 6 months | resource notes built from web sources |
| Evergreen / canonical | 12 months | conventions, zettels, project and area notes |

**Exempt** (events, not claims — never need `expires:`): `03_Journal/`, `07_Archives/`, `10_Agents/solutions/`, the changelog, `00_Meta/status.md`. `02_Inbox/` is exempt because capture is zero-friction — `expires:` is assigned at triage when the note files. `02_Outbox/` is exempt because packets are ephemeral snapshots — their lifecycle is the archive path, not a TTL. Enforcement is warn-only: `brain validate` flags missing or over-cap dates but never blocks a commit; the authoritative thresholds live in the constants block of `brain.py` (spec §14).

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

Agent writes are **two-lane**: content *for the vault* goes to `02_Inbox/` by default; deliverables *for the outside world* go to `02_Outbox/` (via the express-packet skill; the owner ships — agents never do). Agents may write elsewhere only when the human explicitly directs the destination. Every agent-created note must include valid frontmatter with `title`, `tags` (including `audience/agent`), and `updated`.

**Standing exceptions:**

- Agents may append solution notes to `10_Agents/solutions/` (see [[10_Agents/README]]) with required frontmatter including `type/solution`.
- During a live [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] session, agents write interview results directly to `01_Profile/`, `04_Projects/`, and `05_Areas/` — the owner approving each answer in the moment is the human review the Inbox-first rule exists to provide. The exception is scoped to that skill's live session only.

**Filename collisions:** name Inbox notes `YYYY-MM-DD-descriptive-slug.md`. Before writing, check whether the file already exists; on collision, append a numeric suffix (`-2`). Never overwrite another agent's note.

See [[02_Inbox/README]] for Inbox-specific guidance.

## Change Control

| Scope | Method |
|-------|--------|
| `workflow/canonical` notes | PR or explicit human approval required |
| `02_Inbox/` content | Direct commits allowed |
| All other notes | Direct commits allowed |

Canonical notes form the vault's structural foundation — changes to them affect agent behavior across all sessions.

### Draft → Canonical Promotion

Promoting a `workflow/draft` note to `workflow/canonical` is an owner decision, checked off in order:

1. The owner has explicitly approved the promotion (in-session direction counts).
2. The note passes `brain validate` clean and its content is current (bump `updated:`, refresh `expires:` to the evergreen TTL).
3. Swap `workflow/draft` → `workflow/canonical`.
4. The note is reachable: linked from [[00_Meta/index]] and/or its directory README.
5. Structural promotions (new skills, new policies) get a [[00_Meta/changelog]] entry.

For expanded agent guidance, see [[10_Agents/README]].

## Bootstrap Context Budgets

The bootstrap docs ([[AGENTS]], [[01_Profile/now]], [[01_Profile/preferences]], [[01_Profile/defaults]], this file, [[00_Meta/index]]) load into **every** agent session — their size is a per-session context tax. Each has a byte budget (~150% of its measured 2026-08-11 size; total capped at 32 KiB, the smallest harness project-doc cap). `python3 10_Agents/tools/brain/brain.py context` reports actual sizes against budget; `brain validate` warns on breach but never blocks. Budget values are authoritative in the `brain.py` constants block (spec §14). When a bootstrap doc outgrows its budget, distill it — move detail into linked notes — rather than raising the budget by reflex.

## Operating Rhythm

The canonical cadence table — which skills run daily, weekly, monthly, and quarterly — lives in [[10_Agents/skills/README]] § The Rhythm. Automations wire that table; documents don't duplicate it.

## Recency

Agents detecting what changed:
1. Check `updated:` field in frontmatter (primary signal)
2. Read [[00_Meta/changelog]] for structural changes
3. Use `git log -n 10` for detailed file-level history

**Duty to bump:** any edit to a note — creation or modification — must set `updated:` to the current date. The recency signal decays without this.

Agents should **not** re-read files whose `updated:` date hasn't changed since last read. `updated:` has day granularity: for same-day changes, `git log` is authoritative.
