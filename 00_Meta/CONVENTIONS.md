---
title: "Conventions"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-12
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
- Entrypoints: exact uppercase `AGENTS.md`, `CLAUDE.md`, and `README.md`, at the root or any directory level.
- Framework core: `00_Meta/{CONVENTIONS,INDEX,CHANGELOG,PRD,STATUS}.md`, `01_Profile/{NOW,PREFERENCES,DEFAULTS,IDENTITY,WORK,TOOLING-STACK,LONG-RUNNING-THEMES}.md`, and `10_Agents/docs/{OPERATING-RULES,TASK-PATTERNS}.md`. These 14 paths require this exact case; the exception does not extend to other notes with the same basename.
- Generated: exact `00_Meta/{AYMT,HOME}.md` via matching `brain {aymt,home} --write`.
- Generated assets: the exact lowercase inventory under `08_Assets/artifacts/` (`brain artifacts --write`).
- Skill manifests: `SKILL.md` inside `10_Agents/skills/<skill-name>/` (the Agent Skills format requires this exact name).
- Periodic review filenames may use ISO week/quarter tokens:
  - `YYYY-W##-review.md` (weekly)
  - `YYYY-Q#-review.md` (quarterly)

## Locale & Output Defaults

For timezone, date format, units, and other machine-readable defaults, see [DEFAULTS](../01_Profile/DEFAULTS.md).

## Internal Link Contract

Maintained content uses **source-relative inline Markdown only**: `[label](relative/path.md)`, `[label](#heading-slug)`, or `![alt](relative/path.png)`. Destinations use POSIX `/`, exact case, explicit extensions, and UTF-8 percent encoding for spaces and Unicode; heading fragments are GitHub-compatible.

Obsidian is configured to author this portable form; GitHub, VS Code, and `brain` resolve it. Legacy parsing and `migrate-links` are import-only: never author new `[[…]]` links.

Template links use `[human label]({{TOKEN}})`. Replace each token with the complete encoded relative destination including its extension; instantiated notes retain no placeholders.

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

### Provenance

Optional fields marking agent-written notes (`audience/agent` says who a note is *for*): `author:` — the **harness identifier** (`claude-code`, `copilot`, …; not a model id or person); `session:` — a session URL, PR, or task ref (may expose workspace identifiers; work forks can use opaque ids). **Expected for agent notes, absent for human notes**; no migration of old notes. `brain validate` warns (`missing-author`, spec §10.2) on an agent-tagged `02_Inbox/` draft with no `author:`; templates exempt.

### Expiration (`expires:`)

Knowledge notes carry an optional-but-expected `expires: YYYY-MM-DD` — a best-effort "re-verify by" date set at write time, **hard-capped at one year** after `updated:`. It drives the curation loop (`brain curate` + the curate skill): claims decay, and the date says how fast.

Default TTLs by volatility:

| Content | TTL | Examples |
|---------|-----|----------|
| Wiring / product facts | 3 months | harness wiring docs, tool-surface research |
| Retrieval-dated research | 6 months | resource notes built from web sources |
| Evergreen / canonical | 12 months | conventions, zettels, project and area notes |

**Exempt** (events, not claims — never need `expires:`): `03_Journal/`, `07_Archives/`, `10_Agents/solutions/`, the changelog, `00_Meta/STATUS.md`, and any note tagged `type/decision` (a decision record is an event dated at the point it was made, wherever it lives). `02_Inbox/` is exempt because capture is zero-friction — `expires:` is assigned at triage when the note files. `02_Outbox/` is exempt because packets are ephemeral snapshots — their lifecycle is the archive path, not a TTL. (`09_Templates/` and the root `CLAUDE.md` are exempt too, via their own frontmatter exception sections above.) Enforcement is warn-only: `brain validate` flags missing or over-cap dates but never blocks a commit; the authoritative thresholds live in the constants block of `brain.py` (spec §14).

### Template Placeholder Exception

Files in `09_Templates/` may use placeholder tokens such as `{{date}}`, `{{title}}`, and `{{...}}` in frontmatter and body. Any instantiated note created from a template must replace placeholders and set `updated` to a real ISO date.

### Adapter File Exception

`CLAUDE.md` at the vault root carries no frontmatter: it is a one-line adapter (`@AGENTS.md`) that Claude Code expands into the [AGENTS](../AGENTS.md) entrypoint, not a note. It follows canonical change control despite having no tags.

## Tag Namespaces

Tags use **slash-delimited namespaces**. **This table is the authoritative tag taxonomy** — other documents (including [PRD](PRD.md) and [AGENTS](../AGENTS.md)) summarize it. Current namespaces:

| Namespace | Purpose | Values |
|-----------|---------|--------|
| `audience/*` | Who the note is for | `agent`, `human` |
| `type/*` | Kind of content | `meta`, `reference`, `log`, `note`, `idea`, `plan`, `project`, `area`, `resource`, `zettel`, `journal`, `decision`, `solution` |
| `topic/*` | Subject matter | Free-form (e.g., `software`, `physics`, `health`, `ttrpg`, `finance`, `identity`) |
| `workflow/*` | Lifecycle stage | `canonical`, `draft`, `review`, `needs-review` |
| `status/*` | Actionability | `active`, `someday`, `done` |
| `restricted/*` | Privacy marking | `private` |

Notes tagged `workflow/canonical` require a PR or explicit human approval to modify.

### restricted/private

`restricted/private` marks content that must not spread beyond its note. **Not access control** ([PRD](PRD.md) §10.3); leak resistance only, **advisory except on mechanically-enforced surfaces** — index reduction (spec §8.3: body content and link prose emptied; path/title/frontmatter/link targets stay published), the `restricted-link` warning, Cursor `.cursorignore` exclusion. Agents never quote or summarize restricted content into non-restricted notes (see PRD §16.2).

## Tasks

Checkbox tasks (`- [ ]` open, `- [x]` done) live **where their context lives** — any note; no central task file. Inline metadata is Obsidian Tasks emoji, queryable everywhere via `brain tasks` (spec §17):

| Emoji | Meaning |
|-------|---------|
| 📅 | due date (`📅 2026-08-15`) |
| ⏳ / 🛫 / ✅ | scheduled / start / done date |
| ⏫ / 🔼 / 🔽 | priority high / medium / low |
| 🔁 | recurrence (free text) |

## Agent Write Rules

Agent writes are **two-lane**: content *for the vault* goes to `02_Inbox/` by default; deliverables *for the outside world* go to `02_Outbox/` (via express-packet; the owner ships — agents never do). Agents may write elsewhere only when the human explicitly directs the destination. Every agent-created note needs `title`, `tags` (including `audience/agent`), and `updated`, plus `author:`/`session:` per § Provenance above.

**Exceptions:**

- Agents may append solution notes to `10_Agents/solutions/` (`type/solution`; see [README](../10_Agents/README.md)) and rejection rows to the append-only log `10_Agents/docs/rejected-proposals.md` (self-improve's memory; the file itself stays non-canonical `type/log`).
- Only matching `brain {aymt,home} --write` replaces exact `00_Meta/{AYMT,HOME}.md`; no hand edits.
- Only `brain artifacts --write` replaces the exact generated inventory under `08_Assets/artifacts/`; no hand edits or generic directory authority.
- Notifications: configure-notifications only.
- Live, user-invoked [agent-orientation](../10_Agents/skills/agent-orientation/SKILL.md) may write its documented draft inventory, access tool, and capture skill. Markdown uses `workflow/draft`; other files inherit it until promotion.
- A live [onboard-owner](../10_Agents/skills/onboard-owner/SKILL.md) session writes interview results to `01_Profile/`, `03_Journal/people/`, `04_Projects/`, `05_Areas/`; its specialization stage rewrites `09_Templates/` from `variants/` and sets `context:` in the config. In-the-moment owner approval is the review; live-session-scoped.

**Filename collisions:** name Inbox notes `YYYY-MM-DD-descriptive-slug.md`; check first, on collision append a numeric suffix (`-2`), never overwrite another agent's note.

See [README](../02_Inbox/README.md) for Inbox-specific guidance.

## Change Control

| Scope | Method |
|-------|--------|
| `workflow/canonical` notes | PR or explicit human approval required |
| Canonical-by-policy artifacts without note tags | PR or explicit human approval required |
| `02_Inbox/` content | Direct commits allowed |
| All other notes | Direct commits allowed |

Template-shipped skills/tools, `00_Meta/config.yaml`, and tagless adapters are canonical-by-policy. Orientation bundles stay draft until promotion; paths alone do not confer canonical status.

### Draft → Canonical Promotion

Promoting a `workflow/draft` note to `workflow/canonical` is an owner decision, checked off in order:

1. The owner has explicitly approved the promotion (in-session direction counts).
2. The note passes `brain validate` clean and its content is current (bump `updated:`, refresh `expires:` to the evergreen TTL).
3. Swap `workflow/draft` → `workflow/canonical`.
4. The note is reachable: linked from [INDEX](INDEX.md) and/or its directory README.
5. Structural promotions (new skills, new policies) get a [CHANGELOG](CHANGELOG.md) entry.

Promoting an access-tool/capture-skill bundle is one owner decision: promote its Markdown, after which non-note files become canonical-by-policy.

For expanded agent guidance, see [README](../10_Agents/README.md).

## Bootstrap Context Budgets

The bootstrap docs ([AGENTS](../AGENTS.md), [NOW](../01_Profile/NOW.md), [PREFERENCES](../01_Profile/PREFERENCES.md), [DEFAULTS](../01_Profile/DEFAULTS.md), this file, [INDEX](INDEX.md)) load into **every** agent session — their size is a per-session context tax. Each has a byte budget (~150% of its measured 2026-08-11 size; total capped at 32 KiB, the smallest harness project-doc cap). `brain context` reports actual sizes against budget; `brain validate` warns on breach but never blocks. Budget values are authoritative in the `brain.py` constants block (spec §14). When a bootstrap doc outgrows its budget, distill it — move detail into linked notes — rather than raising the budget by reflex.

## Operating Rhythm

The canonical cadence table — which skills run daily, weekly, monthly, and quarterly — lives in [README](../10_Agents/skills/README.md) § The Rhythm. Automations wire that table; documents don't duplicate it.

## Recency

Agents detecting what changed:
1. Check `updated:` field in frontmatter (primary signal)
2. Read [CHANGELOG](CHANGELOG.md) for structural changes
3. Use `git log -n 10` for detailed file-level history

**Changelog entry format** — new entries use `## [YYYY-MM-DD] <operation> | <summary>`, grep-parseable via `grep '^## \['`. Forward-only: entries before the 2026-08-11 `recategorize` entry keep their original `## YYYY-MM-DD — Title` headers, so the grep matches new-format entries, not the full history. `<operation>` is a short kebab-case verb phrase (`add-skill`, `restructure`, `backfill`); the bullets below the header carry the detail.

**Duty to bump:** any edit to a note — creation or modification — must set `updated:` to the current date. The recency signal decays without this.

Agents should **not** re-read files whose `updated:` date hasn't changed since last read. `updated:` has day granularity: for same-day changes, `git log` is authoritative.
