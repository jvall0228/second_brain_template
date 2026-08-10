---
title: "PRD"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-10
---

# PRD: Second Brain Knowledge Management System (Markdown + Git + Obsidian + Agents)

## 1. Summary
A Git-synced, Markdown-first repository that acts as the canonical “personal context layer” shared across multiple AI agents (via GitHub connector / MCP) and a human user (via Obsidian). It reduces per-agent context silos by defining a single source of truth for identity, preferences, current state, and structured knowledge.

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
- Solving cross-platform filesystem limitations beyond portable conventions (e.g., prefer stub alias files over symlinks).

## 4. Users / Personas
- **Human (Owner):** browses and edits in Obsidian; reviews agent changes via Git/PRs.
- **Agents (Multiple models/tools):** bootstrap from `CONTEXT.md`, perform tasks, and write outputs following repo conventions.
- **Future contributor (optional):** another human consuming the same repo conventions.

## 5. Key workflows
### 5.1 Universal agent bootstrap (must-read sequence)
This order is **contractual** and must be listed verbatim in `CONTEXT.md`:

1. `CONTEXT.md` (entrypoint / scope / how to use this repo)
2. `01_Profile/now.md` (what’s happening right now)
3. `01_Profile/preferences.md` (how to behave / format outputs)
4. `00_Meta/conventions.md` (how to write and where to write)

> **Tip:** Agents with CLI access can also use the `brain` tool (see §16, M5) to query the vault index and discover relevant notes beyond the must-read sequence.

### 5.2 Agent write pattern (default rules)
**M0–M1 default: agents write only to Inbox.**
- New agent-generated notes go to `02_Inbox/`.
- Agents should not directly modify canonical profile files unless explicitly instructed.

**Expanded write permissions (later milestones):**
- Agents may write directly to `06_Resources/` for research summaries *only if* they conform to required frontmatter and include provenance.
- Agents may write to `04_Projects/` only when a project explicitly opts in (e.g., `workflow/agent-writable` tag on that project’s status note).

### 5.3 Change control
- Prefer PRs for changes to **canonical** notes and conventions.
- Direct commits allowed for:
  - adding new notes into `02_Inbox/`
  - adding new resource notes when permitted
- Canonical notes are marked with `workflow/canonical` and treated as **read-only for agents** unless explicitly allowed.

### 5.4 Human usage
- Open repo as Obsidian vault.
- Capture into Inbox/Journal.
- Review and migrate notes into PARA or Zettelkasten.
- Review agent PRs/commits and merge.

## 6. Information architecture (top-level, number-prefixed)
Top-level directories (must exist; number prefixes required for ordering):

- `00_Meta/` — global conventions, indices/MoCs, schemas, operating rules
- `01_Profile/` — canonical personal context (identity/preferences/current state/defaults)
- `02_Inbox/` — raw capture / triage queue
- `03_Journal/` — daily/weekly/monthly logs + reviews (Bullet Journal)
- `04_Projects/` — PARA Projects
- `05_Areas/` — PARA Areas
- `06_Resources/` — PARA Resources
- `07_Archives/` — PARA Archives
- `08_Assets/` — non-Markdown assets (images, PDFs, exports)
- `09_Templates/` — note templates (introduced when consistency pressure appears)
- `10_Agents/` — agent plugin library: universal skills, tools, harness adapters, and operating docs

**Filename convention:** kebab-case (Git-friendly, agent-predictable).

## 7. Universal agent entrypoint and aliases
### 7.1 Required root file
- `CONTEXT.md` at repository root.

Required content sections:
- What this repo is and why it exists
- The must-read order (see §5.1)
- Where agents write output (Inbox-first at M0/M1)
- Minimal tagging rules
- Links to canonical Profile notes and `10_Agents/` (when it exists)
- Links to navigation (PARA roots, Inbox, Templates)
- Conventions summary (frontmatter + tag syntax, numbered dirs)

Recommended frontmatter:
```yaml
---
title: "Agent Context"
tags:
  - audience/agent
  - type/meta
  - workflow/canonical
updated: 2026-02-12
---
```

### 7.2 Required alias files (portable primary approach)
At repo root, create **stub alias files** (portable across platforms and Git tooling):
- `AGENTS.md` — one line linking to `CONTEXT.md`
- `CLAUDE.md` — one line linking to `CONTEXT.md`

**Optional optimization:** use symlinks instead of stubs only if your environment supports them reliably.

## 8. Agent plugin library directory
### 8.1 Directory
- `10_Agents/`

Purpose: a unified library of reusable agent primitives (skills, tools) and harness-specific adapters, plus operating docs. Supersedes the earlier `00_Meta/Agents/` plan.

### 8.2 Structure
```
10_Agents/
  README.md              # directory index + "start here"
  skills/                # universal skill definitions (prompt templates)
  tools/                 # executable tools (e.g., brain CLI)
  harnesses/
    claude/              # Claude Code hooks, CLAUDE.md overrides
    cursor/              # .cursorrules, etc.
    ...                  # other harness adapters as needed
  docs/                  # operating rules, task patterns, model-specific guidance
```

### 8.3 Design principles
- **Two layers:** universal primitives (skills, tools) that work across any agent harness, and harness-specific adapters that wire them into a particular runtime.
- **Skills** are prompt templates — reusable, model-agnostic instruction sets for common tasks.
- **Tools** are executable code (CLIs, scripts) agents invoke directly.
- **Harness adapters** ship both reference config files (ready to symlink/copy) and documentation explaining the wiring. Frameworks like MCP and skills are universal; hooks and rules are harness-specific.
- Agents discover available skills and tools via the `brain` index (M5) or by reading `10_Agents/README.md`.

## 9. Frontmatter and tags
### 9.1 Requirement: YAML frontmatter
Markdown notes support YAML frontmatter.

### 9.2 Requirement: tags with subtags
Tags are slash-delimited strings in a YAML list:

```yaml
---
tags:
  - audience/agent
  - audience/human
---
```

### 9.3 Minimal required fields (baseline)
- `title` (string)
- `tags` (list of strings)
- `updated` (ISO `YYYY-MM-DD`)

Example:
```yaml
---
title: "Now"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-02-12
---
```

### 9.4 Tag intent default
Agents should assume **all notes are readable** unless explicitly restricted. Use tags to signal intent and handling rather than access control.

Recommended namespaces:
- `audience/*` — intended primary audience (`audience/agent`, `audience/human`)
- `type/*` — note type (`type/project`, `type/resource`, `type/zettel`, `type/journal`, `type/meta`)
- `workflow/*` — handling (`workflow/canonical`, `workflow/draft`, `workflow/needs-review`, `workflow/inbox`)
- `status/*` — lifecycle (`status/active`, `status/on-hold`, `status/done`, `status/archived`)

## 10. Canonical notes (phased: content vs stub)
The repo becomes usable with a small set of real-content files (M0). Everything else can start as stubs and evolve.

### 10.1 M0 “real content” files (must exist and be meaningful)
- `CONTEXT.md`
- `01_Profile/Now.md`
- `01_Profile/Preferences.md`
- `00_Meta/Conventions.md`

### 10.2 M0 structural stubs (must exist; minimal content acceptable)
- `AGENTS.md` (stub link to `CONTEXT.md`)
- `CLAUDE.md` (stub link to `CONTEXT.md`)
- `02_Inbox/README.md` (one-paragraph triage instructions)
- Remaining numbered directories exist (empty or `.gitkeep`)

### 10.3 Post-M0 canonical notes (can start as stubs, then filled)
- `00_Meta/Index.md` — global MoC
- `00_Meta/Agent-Operating-Rules.md` — expanded rules once multiple agents are in play
- `01_Profile/Defaults.md` — timezone/units/naming defaults
- Section READMEs:
  - `03_Journal/README.md`, `04_Projects/README.md`, `05_Areas/README.md`, `06_Resources/README.md`, `07_Archives/README.md`

## 11. Templates (introduced when needed)
Templates are valuable once note volume increases. Treat template paths as **stable contracts** to reduce rename churn.

When introduced in `09_Templates/`, required templates:
- `template-project.md`
- `template-area.md`
- `template-resource.md`
- `template-zettel.md`
- `template-daily-log.md`
- `template-weekly-review.md`
- `template-decision-record.md`

Template requirements:
- Must include YAML frontmatter (title, tags, updated)
- Must include placeholders for links to related notes
- Must include suggested tag sets (including `type/*` and relevant `workflow/*`)

## 12. Functional requirements
- Scaffold the full directory structure with number prefixes.
- Create M0 real-content files (see §10.1).
- Create root alias stub files (`AGENTS.md`, `CLAUDE.md`) pointing to `CONTEXT.md`.
- Create `02_Inbox/README.md` with minimal triage guidance.
- Ensure the repo is usable as an Obsidian vault from day one.
- Define minimum contents for `10_Agents/docs/Task-Patterns.md` when introduced:
  - “Write to Inbox” default
  - Required frontmatter for agent-created notes
  - Allowed destinations by milestone (Inbox-only → Resources → Projects opt-in)

## 13. Non-functional requirements
- **Portability:** plain text-first; no proprietary formats required.
- **Diffability:** content structured to minimize noisy diffs.
- **Predictability:** stable file paths and naming conventions for agent automation.
- **Safety for edits:** canonical notes clearly marked; agents guided to propose changes carefully.
- **Low overhead:** conventions lightweight enough to preserve capture speed.

## 14. “What changed?” / recency convention
Agents should have a minimal way to detect recency without rereading everything:
- Canonical notes include `updated:` and should be inspected first.
- Optional (post-M0): add `00_Meta/Changelog.md` with short dated entries, or instruct agents to check recent commits via `git log -n <N>` when tool access supports it.

## 15. Asset lifecycle guidance
- `08_Assets/` is append-only by default.
- Large or obsolete assets should be moved to `07_Archives/Assets/` (or removed if reproducible).
- Resource notes should link to assets using relative paths.

## 16. Milestones
### M0: Bootstrap Minimum (prove the loop)
Goal: the smallest set that lets one agent bootstrap, understand context, and write useful output predictably.

**Files with real content (4):**
- `CONTEXT.md`
- `01_Profile/Now.md`
- `01_Profile/Preferences.md`
- `00_Meta/Conventions.md`

**Structural stubs:**
- `AGENTS.md` (stub link)
- `CLAUDE.md` (stub link)
- `02_Inbox/README.md`
- Other numbered directories (empty or `.gitkeep`)

Success criterion:
- An agent reads the must-read sequence and produces an Inbox note that matches conventions.

### M1: Repo skeleton expansion
- Ensure all top-level directories exist.
- Add basic section READMEs (Projects/Areas/Resources/Archives/Journal) as stubs.

### M2: Canonical navigation
- Create `00_Meta/Index.md` and link the core sections.
- Add `01_Profile/Defaults.md`.

### M3: Templates + agent docs bootstrap
- Add `09_Templates/` and reference stable paths.
- Create `10_Agents/` directory with `README.md` and `docs/` (operating rules, task patterns).
- Supersedes earlier plan for `00_Meta/Agents/`; all agent-targeted docs live under `10_Agents/docs/`.

### M4: Navigation integrity + scaling
- Reduce broken links; stabilize conventions.
- Add changelog/recency conventions if agents/tooling benefit.

### M5: Vault Index CLI (`brain`)
- Python CLI at `.tools/brain/` that indexes all `.md` files in the vault.
- Extracts frontmatter, wikilinks, headings, inline tags, backlinks, and file stats.
- Stores index as JSON (`.tools/brain/vault-index.json`).
- Query commands: `list`, `search` (by tag/title/folder), `links`, `tags`, `show`, `recent`.
- All commands support `--json` for agent-consumable output.
- Modeled after Obsidian's MetadataCache: same metadata types, similar resolution logic.
- Enables progressive disclosure — agents query the index instead of reading every file.

### M6: Agent Plugin Library
- Populate `10_Agents/skills/` with universal skill definitions (prompt templates for common tasks).
- Populate `10_Agents/tools/` with executable tools (migrate `brain` CLI here from `.tools/`).
- Add `10_Agents/harnesses/` with reference configs and wiring docs for at least one harness (Claude Code).
- Ship both real config files (ready to symlink/copy) and companion documentation.
- Universal primitives (skills, MCP tools) work across any agent harness; harness-specific adapters (hooks, rules) are isolated under `harnesses/<name>/`.

## 17. Acceptance criteria
- Number-prefixed directories exist.
- `CONTEXT.md` exists at root, includes must-read order, and defines default write location.
- `AGENTS.md` and `CLAUDE.md` exist as portable stubs linking to `CONTEXT.md` (or symlinks as an optional optimization).
- M0 canonical profile files exist with YAML frontmatter and slash-delimited subtags.
- Agents can reliably write a valid note into `02_Inbox/` with required frontmatter.
- Obsidian opens the repo cleanly with a clear entrypoint (`CONTEXT.md`).

## 18. Open considerations (document-only, not blockers)
- Whether to adopt a strict “agents never edit, only propose PRs” posture for canonical files.
- Whether to adopt an explicit “restricted/*” tag namespace in the future.
- When to formalize a weekly review cadence to keep `Now.md` fresh.
