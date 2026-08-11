---
title: "PRD"
tags:
  - type/meta
  - workflow/canonical
  - audience/human
  - audience/agent
updated: 2026-08-11
---

# PRD: Second Brain Knowledge Management System (Markdown + Git + Obsidian + Agents)

> **Revision 2.0 — 2026-08-11.** Aligned the spec with the shipped template: normalized all paths to kebab-case, recorded milestone status (M0–M4 done, M5–M6 not started), made [[00_Meta/conventions]] the authoritative tag taxonomy, documented the shipped surface (Journal subtree, solutions library, extra profile notes and templates), and added sections for the template phase, data sensitivity, concurrency, and validation. Revision 1.x (2026-02 through 2026-08) evolved in place without a revision log.

## 1. Summary
A Git-synced, Markdown-first repository that acts as the canonical "personal context layer" shared across multiple AI agents (via GitHub connector / MCP) and a human user (via Obsidian). It reduces per-agent context silos by defining a single source of truth for identity, preferences, current state, and structured knowledge. The repository is distributed as a fork-and-fill **template** (see §5).

## 2. Goals
- **Single shared context source of truth** for all agents and tools.
- **Obsidian-first usability** (vault-friendly, navigable, linkable).
- **Agent-safe structure** (predictable paths, stable contracts, low-risk write rules).
- **Git-native collaboration** (diffable changes, auditable history, PR/commit workflow).
- **Framework integration**
  - **PARA** for top-level organization (Projects/Areas/Resources/Archives)
  - **Bullet Journal** for capture + review cadence
  - **Zettelkasten** for evergreen, atomic notes + linking

## 3. Non-goals
- Building a custom application UI (Obsidian is the UI).
- Implementing an agent runtime/orchestrator in this phase.
- Enforcing strict schemas beyond lightweight frontmatter conventions.
- Solving cross-platform filesystem limitations beyond portable conventions.

## 4. Users / Personas
- **Human (Owner):** browses and edits in Obsidian; reviews agent changes via Git/PRs.
- **Agents (Multiple models/tools):** bootstrap from `AGENTS.md`, perform tasks, and write outputs following repo conventions.
- **Future contributor (optional):** another human consuming the same repo conventions.

## 5. Template phase
This repository ships as a reusable, context-neutral template. The shipped state intentionally contains:
- **Blank fill-in shells** for the profile notes (`01_Profile/now.md`, `preferences.md`, `defaults.md`, `identity.md`, `work.md`, `tooling-stack.md`, `long-running-themes.md`) with inline guidance.
- **One seeded example per section** (project, area, resource, person, idea, daily log, weekly review) — deleted by the adopter after seeing the pattern.

The §11.1 "real content" requirements and the M0 success criterion (§19) apply to the **adopter's fork after completing the getting-started checklist** in [[00_Meta/status]], not to the shipped template itself.

## 6. Key workflows
### 6.1 Universal agent bootstrap (must-read sequence)
This order is **contractual** and is listed first in `AGENTS.md`:

1. `AGENTS.md` (entrypoint / scope / how to use this repo)
2. `01_Profile/now.md` (what's happening right now)
3. `01_Profile/preferences.md` (how to behave / format outputs)
4. `00_Meta/conventions.md` (how to write and where to write)

`AGENTS.md` additionally defines a **complete bootstrap** tier — `00_Meta/index.md` and `01_Profile/defaults.md` — required before creating structured notes or navigating beyond the Inbox. The four-item sequence above is the contractual minimum; the second tier extends it and does not replace it.

> **Planned (M5 — not yet built):** a `brain` CLI for querying a vault index. Until it ships, agents navigate via [[00_Meta/index]] and directory READMEs.

### 6.2 Agent write pattern (active policy)
- Agents write new notes to `02_Inbox/` by default (the **Inbox-first rule**).
- Non-Inbox destinations are allowed only when the human explicitly names the destination in the current request.
- **Standing exception:** agents may append solution notes to `10_Agents/solutions/` (see §9.2).
- Agents should not modify canonical profile files unless explicitly instructed.

**Roadmap — not adopted:** a milestone-gated expansion (direct agent writes to `06_Resources/` for research summaries with provenance; `04_Projects/` opt-in via a `workflow/agent-writable` tag on the project's status note). If adopted, the tag must first be registered in [[00_Meta/conventions]] and this section plus [[10_Agents/docs/task-patterns]] updated. Until then the active policy above governs; roadmap language does not override it.

### 6.3 Change control
- Notes tagged `workflow/canonical` require a **PR or explicit human approval** to modify (see §11 for what canonical means). Agents propose changes via the Inbox protocol in [[10_Agents/docs/operating-rules]].
- Direct commits are allowed for `02_Inbox/` content, `10_Agents/solutions/` notes (per §9.2), and other non-canonical notes.

### 6.4 Human usage
- Open repo as Obsidian vault.
- Capture into Inbox/Journal.
- Review and migrate notes into PARA directories; evergreen atomic notes go to `06_Resources/` tagged `type/zettel` (see §7).
- Review agent PRs/commits and merge.

## 7. Information architecture (top-level, number-prefixed)
Top-level directories (must exist; number prefixes required for ordering):

- `00_Meta/` — conventions, index (MoC), changelog, status snapshot, this PRD
- `01_Profile/` — canonical personal context: `now`, `preferences`, `defaults`, plus `identity`, `work`, `tooling-stack`, `long-running-themes`
- `02_Inbox/` — raw capture / triage queue
- `03_Journal/` — **subjective** knowledge and experience: `periodic/{daily,weekly,monthly,quarterly,yearly}/` reviews (Bullet Journal) plus `ideas/`, `insights/`, `memories/`, `people/`, `plans/`
- `04_Projects/` — PARA Projects
- `05_Areas/` — PARA Areas
- `06_Resources/` — PARA Resources (**objective** reference material; also the home of Zettelkasten notes)
- `07_Archives/` — PARA Archives
- `08_Assets/` — non-Markdown assets (images, PDFs, exports)
- `09_Templates/` — note templates (stable-path contracts)
- `10_Agents/` — agent operating docs and solutions knowledge base; grows into a plugin library at M6 (see §9)

**Placement rule:** Journal is subjective (your perspective and experience); Resources are objective (shareable without personal context). **Zettelkasten home:** evergreen atomic notes live in `06_Resources/` with `type/zettel`; subjective sparks start in `03_Journal/ideas/` and graduate to Resources when refined.

**Filename convention:** kebab-case (Git-friendly, agent-predictable), with two exceptions defined in [[00_Meta/conventions]]:
- Uppercase entrypoints (`AGENTS.md`, `CLAUDE.md`, `README.md`) at any directory level.
- ISO periodic tokens for reviews (`YYYY-W##-review.md`, `YYYY-Q#-review.md`).

Paths are case-sensitive; this document uses the literal shipped paths throughout.

## 8. Universal agent entrypoint
### 8.1 Required root file
- `AGENTS.md` at repository root — the standard agent entrypoint, following the cross-harness `AGENTS.md` convention.

Required content sections:
- What this repo is and why it exists
- The must-read order (see §6.1)
- Where agents write output (Inbox-first)
- Minimal tagging rules
- Links to canonical Profile notes and `10_Agents/`
- Links to navigation (PARA roots, Inbox, Templates)
- Conventions summary (frontmatter + tag syntax, numbered dirs)

Recommended frontmatter:
```yaml
---
title: "Agents"
tags:
  - audience/agent
  - type/meta
  - workflow/canonical
updated: 2026-08-11
---
```

### 8.2 Claude Code adapter file
`CLAUDE.md` at repo root is a **thin adapter**: its entire content is the single memory-import line

```markdown
@AGENTS.md
```

Claude Code auto-loads `CLAUDE.md` and the `@AGENTS.md` line injects the entrypoint's contents; harnesses that read `AGENTS.md` natively never touch `CLAUDE.md`. As a one-line machine directive rather than a note, `CLAUDE.md` is **exempt from the §10.1 frontmatter requirement** and cannot carry the `workflow/canonical` tag — treat it as canonical for change-control purposes anyway (§6.3).

**Decision history:** the vault originally used `CONTEXT.md` as the entrypoint with `AGENTS.md`/`CLAUDE.md` as aliases (stub files, later symlinks). On 2026-08-11 `CONTEXT.md` was retired: its content moved to `AGENTS.md` (now the real file) and `CLAUDE.md` became the `@`-import adapter above — no symlinks remain, which also removes the old platform-portability caveat.

## 9. Agent library directory (`10_Agents/`)
### 9.1 Shipped structure
```
10_Agents/
  README.md              # directory index + "start here"
  docs/                  # operating-rules.md, task-patterns.md
  solutions/             # knowledge base of solved problems, by category
```

### 9.2 Solutions knowledge base
`10_Agents/solutions/` is a standing knowledge base of solutions to recurring problems, organized by category. Agents **may append** solution notes here whenever they solve something worth not re-deriving later — this is a deliberate, bounded carve-out from the Inbox-first rule. Solution notes must carry required frontmatter (including `audience/agent` and `type/solution`), use kebab-case filenames, and follow the note format in `10_Agents/solutions/README.md`. Agents add notes; restructuring or deleting within `solutions/` still requires human direction.

### 9.3 M6 target structure (not built)
At M6 the directory grows into a plugin library:
```
10_Agents/
  skills/                # universal skill definitions (prompt templates)
  tools/                 # executable tools (e.g., brain CLI)
  harnesses/<name>/      # harness-specific adapters (hooks, rules)
```
Design principles: universal primitives (skills, tools) work across any agent harness; harness-specific adapters are isolated under `harnesses/<name>/`; adapters ship both reference configs and wiring docs.

### 9.4 Discovery
Today, agents discover available docs and solutions by reading `10_Agents/README.md`. Once M5 ships, the `brain` index becomes the primary discovery mechanism.

## 10. Frontmatter and tags
### 10.1 Requirement: YAML frontmatter (all notes)
**Every markdown note in the vault must include YAML frontmatter** with at minimum:
- `title` (string)
- `tags` (list of slash-delimited strings)
- `updated` (ISO `YYYY-MM-DD`)

**Exceptions:** files in `09_Templates/` may use placeholder tokens (`{{date}}`, `{{title}}`, `{{...}}`); any note instantiated from a template must replace them and set `updated` to a real ISO date. `CLAUDE.md` carries no frontmatter at all — it is a one-line adapter, not a note (§8.2).

Example:
```yaml
---
title: "Now"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-11
---
```

### 10.2 Authoritative taxonomy
**[[00_Meta/conventions#Tag Namespaces]] owns the evolving tag vocabulary.** Other documents (including this one) summarize it. As of this revision:

- `audience/*` — intended primary audience: `agent`, `human`
- `type/*` — note type: `meta`, `reference`, `log`, `note`, `idea`, `plan`, `project`, `area`, `resource`, `zettel`, `journal`, `decision`, `solution`
- `topic/*` — subject matter, free-form (e.g. `software`, `health`, `finance`)
- `workflow/*` — handling: `canonical`, `draft`, `review`, `needs-review`
- `status/*` — actionability: `active`, `someday`, `done`

### 10.3 Tag intent default
Tags signal **intent and handling, not access control**. Agents should assume all notes are readable. No restriction mechanism exists today; a `restricted/*` namespace remains an open consideration (§21), and sensitive content is handled per §16.2 in the interim.

## 11. Canonical notes
**Definition:** a note is canonical when other notes and agent behavior depend on it — it defines vault structure, conventions, navigation, or agent rules. **Only the human assigns or removes the `workflow/canonical` tag.** Promotion path: a note starts as `workflow/draft`, may pass through `workflow/review`, and becomes canonical when the human adds the tag.

Canonical notes are read-only for agents except via the change-control process in §6.3.

**Current canonical set:** `AGENTS.md`, `00_Meta/conventions.md`, `00_Meta/index.md`, `00_Meta/changelog.md`, `00_Meta/prd.md` (this file), `01_Profile/now.md`, `01_Profile/preferences.md`, `01_Profile/defaults.md`, `10_Agents/README.md`, `10_Agents/docs/operating-rules.md`, `10_Agents/docs/task-patterns.md`. (`CLAUDE.md` cannot carry the tag — see §8.2 — but follows the same change control.)

**Deliberately not canonical:** `00_Meta/status.md` is a living snapshot that agents may update directly (e.g. milestone status); this is recorded in the note itself.

### 11.1 Real-content files (must exist and be meaningful in an adopter's fork — see §5)
- `AGENTS.md`
- `01_Profile/now.md`
- `01_Profile/preferences.md`
- `00_Meta/conventions.md`

### 11.2 Structural requirements
- `CLAUDE.md` (Claude Code adapter per §8.2)
- `02_Inbox/README.md` (triage instructions)
- Section READMEs for every top-level directory

> **Historical note:** an early plan placed agent operating rules under `00_Meta/`; that plan was superseded at M3. The operative file is `10_Agents/docs/operating-rules.md`.

## 12. Templates
Template paths in `09_Templates/` are **stable contracts**. The shipped set (12):

**Core seven:** `template-project.md`, `template-area.md`, `template-resource.md`, `template-zettel.md`, `template-daily-log.md`, `template-weekly-review.md`, `template-decision-record.md`

**Additional:** `template-monthly-review.md`, `template-quarterly-review.md`, `template-yearly-review.md`, `template-media.md`, `template-comparison.md`

Template requirements (all shipped templates comply):
- YAML frontmatter with `title`, `tags`, `updated` (placeholders allowed per §10.1)
- Placeholders for links to related notes
- Suggested tag sets including `type/*` and `workflow/draft` (instantiated notes keep `workflow/draft` until triaged)

See [[09_Templates/README]] for the selection guide.

## 13. Functional requirements
- Scaffold the full directory structure with number prefixes.
- Create the real-content files (§11.1) — shipped as fill-in shells per §5.
- Provide `CLAUDE.md` importing `AGENTS.md` via the `@AGENTS.md` memory-import line (§8.2).
- Create `02_Inbox/README.md` with triage guidance.
- Ensure the repo is usable as an Obsidian vault from day one.
- `10_Agents/docs/task-patterns.md` defines:
  - The Inbox-first default
  - Required frontmatter for agent-created notes
  - The destination policy: explicit human direction for non-Inbox writes, plus the `solutions/` carve-out (§9.2)

## 14. Non-functional requirements
- **Portability:** plain text-first; no proprietary formats required.
- **Diffability:** content structured to minimize noisy diffs.
- **Predictability:** stable file paths and naming conventions for agent automation.
- **Safety for edits:** canonical notes clearly marked; agents guided to propose changes carefully.
- **Low overhead:** conventions lightweight enough to preserve capture speed.

## 15. Recency ("what changed?")
- `updated:` in frontmatter is the **primary recency signal**. **Any edit to a note must bump `updated:` to the current date** — the recency contract fails without this duty.
- `updated:` has day granularity; for same-day or finer history, `git log` is authoritative.
- [[00_Meta/changelog]] records structural changes; [[00_Meta/status]] snapshots overall vault state.
- Agents may skip re-reading notes whose `updated:` hasn't changed since last read, accepting the day-granularity caveat.

## 16. Assets and data sensitivity
### 16.1 Asset lifecycle
- `08_Assets/` is append-only by default.
- Reference assets from notes using Obsidian embed syntax (`![[file.png]]`) or relative markdown links — embeds are the vault-internal default; relative links are the portable option.
- Large or obsolete assets move to `07_Archives/assets/` (or are removed if reproducible).

### 16.2 Data sensitivity
This vault is a personal context layer read in full by every connected agent service. Therefore:
- **Never commit** credentials, API keys, tokens, or other secrets.
- `03_Journal/people/` notes concern **third parties** — keep them factual and respectful, and write nothing you would not stand behind if read back.
- For health, financial, or otherwise sensitive content, remember that anything committed is visible to every agent and service with repo access; keep out material that must not reach them.
- Use **separate forks per context** (personal vs work — see the root README) to prevent cross-contamination.
- Until a `restricted/*` mechanism exists (§21), exclusion from the repo is the only reliable protection.

## 17. Multi-agent concurrency
- **Inbox filenames:** date-prefix plus descriptive slug (`YYYY-MM-DD-slug.md`). Before writing, check for an existing file with the same name; on collision, append a numeric suffix (`-2`). Never overwrite another agent's note.
- Pull/sync before writing when the environment allows; keep commits small and frequent.
- Merge conflicts are resolved by the human. Agents must never force-push.

## 18. Validation and enforcement
- **Current:** honor-system — the self-validation checklist in [[10_Agents/docs/operating-rules]] (frontmatter fields, tag namespaces, filename convention, destination, `updated:` bump).
- **Planned (M5):** a `brain validate` subcommand checking frontmatter fields, tag namespaces against conventions, filename conventions, and wikilink resolution.
- Automated enforcement (pre-commit hook / CI) remains an open consideration (§21).

## 19. Milestones (status as of 2026-08-11)
### M0: Bootstrap Minimum — **Done**
Real-content files (§11.1, shipped as fill-in shells per §5), aliases, Inbox README, all numbered directories.
Success criterion: an agent reads the must-read sequence and produces an Inbox note that matches conventions. *(Verified 2026-08-11: `2026-08-11-prd-review.md`, written to the Inbox and archived after triage to `07_Archives/inbox/`.)*

### M1: Repo skeleton expansion — **Done**
Section READMEs for every top-level directory (directories themselves exist from M0).

### M2: Canonical navigation — **Done**
`00_Meta/index.md` and `01_Profile/defaults.md`.

### M3: Templates + agent docs — **Done**
`09_Templates/` (twelve templates, §12) and `10_Agents/` with README, `docs/` (operating rules, task patterns), and — beyond the original scope — the `solutions/` knowledge base (§9.2).

### M4: Navigation integrity — **Done**
Zero broken wikilinks (verified 2026-08-11; template placeholders exempt).

### M5: Vault Index CLI (`brain`) — **Not started**
- Python CLI at `.tools/brain/` that indexes all `.md` files (frontmatter, wikilinks, headings, inline tags, backlinks, file stats).
- Index stored as JSON (`.tools/brain/vault-index.json`; moves to `10_Agents/tools/brain/vault-index.json` after the M6 migration).
- Query commands: `list`, `search`, `links`, `tags`, `show`, `recent`; all support `--json`.
- Also: `validate` (§18).
- Obsidian's MetadataCache is the design inspiration; concrete parsing and link-resolution rules must be specified before implementation (start from [[10_Agents/solutions/obsidian-issues/wikilink-resolution-rules]]).

### M6: Agent Plugin Library — **Not started**
- Populate `10_Agents/skills/` (universal skill definitions) and `10_Agents/tools/` (migrate `brain` here).
- Add `10_Agents/harnesses/` with reference configs and wiring docs for at least one harness (Claude Code).

## 20. Acceptance criteria (M0, objective)
- All eleven number-prefixed directories exist.
- `AGENTS.md` exists at root, lists the §6.1 four-item order first, and names `02_Inbox/` as the default write location.
- `CLAUDE.md` exists at root and its body contains the `@AGENTS.md` import line.
- Every markdown note passes the §10.1 frontmatter check (`title`, `tags`, `updated`; slash-delimited tags) — scriptable; template placeholders and the `CLAUDE.md` adapter exempt.
- An agent-authored note with required frontmatter exists in `02_Inbox/` (the M0 success criterion).
- Zero unresolved wikilinks from `AGENTS.md`, `00_Meta/index.md`, and section READMEs (template placeholders exempt).
- Canonical notes carry `workflow/canonical`, and the change-control table in [[00_Meta/conventions]] covers them (Git-native collaboration goal).
- Each framework has a concrete home: PARA (`04_`–`07_`), Bullet Journal (`03_Journal/periodic/` + review templates), Zettelkasten (`06_Resources/` + `template-zettel`).

## 21. Open considerations (document-only, not blockers)
- Whether to adopt a `restricted/*` tag namespace (interim handling: §16.2).
- Whether/when to activate the expanded write ladder (§6.2 roadmap) and register `workflow/agent-writable`.
- Whether to add automated enforcement (pre-commit/CI) beyond the planned `brain validate`.

**Resolved since revision 1.x (decisions recorded in the body):** strict canonical change control → adopted (§6.3, [[10_Agents/docs/operating-rules]]); review cadence → adopted (four periodic review templates plus the daily log); alias approach → symlinks shipped (§8.2); Zettelkasten home → `06_Resources/` (§7).
