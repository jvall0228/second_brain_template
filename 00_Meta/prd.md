---
title: "PRD"
tags:
  - type/meta
  - workflow/canonical
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2027-08-11
---

# PRD: Second Brain Knowledge Management System (Markdown + Git + Obsidian + Agents)

> **Revision 2.2 — 2026-08-11.** Added §6.5: VS Code supported as an alternative editor via shipped `.vscode/` workspace config, under an owner-set strict first-party extension trust policy.
> **Revision 2.1 — 2026-08-11.** `AGENTS.md` became the entrypoint with `CLAUDE.md` as a one-line adapter (§8.2); harness support tiers recorded, standards-first (§8.3); M5–M7 requirements settled — M6 rescoped to the plugin-library core, M7 (environment integration) added (§19).
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
- Agent writes are **two-lane**, both review-gated: content *for the vault* goes to `02_Inbox/` by default (the **Inbox-first rule**); outbound deliverables *for the world* go to `02_Outbox/` via the `express-packet` skill — the owner reviews and ships, and **agents never ship** absent an explicit per-item instruction.
- Other (non-Inbox, non-Outbox) destinations are allowed only when the human explicitly names the destination in the current request.
- **Standing exceptions:** agents may append solution notes to `10_Agents/solutions/` (see §9.2); once M6 ships the plugin library, agents may also add or update **agent-generated** skills and tools under `10_Agents/skills/` and `10_Agents/tools/` (see §9.3 — generated items carry `workflow/draft` until promoted; template-shipped plugins are canonical).
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

### 6.5 Alternative editor: VS Code (decision 2026-08-11)
Obsidian remains the primary human UI (§2), but the vault must stay usable when Obsidian is unavailable. The repo ships root-scope `.vscode/` workspace config (`settings.json` + `extensions.json`) as the VS Code counterpart to `.obsidian/` — a dot-path outside the note corpus, per the §9.3 precedent (`.github/`, `CLAUDE.md`):

- **Extension trust policy (template default, owner-overridable):** only extensions published by **first-party organization accounts** (Microsoft, Anthropic, GitHub, and similar) are recommended; built-in VS Code capability is preferred over any extension. Community and personal-publisher extensions are never recommended by the template, regardless of reputation — notably **Foam**, the standard Obsidian-parity extension, was evaluated and declined under this policy. An adopter may relax the policy in their fork (Foam is documented as the single upgrade that restores wikilink/backlink/graph parity); a structured vault config file for such overrides is an open consideration (§21), out of scope for now.
- **Extension recommendations:** Microsoft's **Live Preview** for rendering HTML files, plus the two P0-harness companions with VS Code surfaces (§8.3): **Claude Code** (Anthropic) and **Copilot** (GitHub). Prettier is explicitly unwanted (it reformats markdown against §14 diffability).
- **Workspace settings** use built-ins to honor vault contracts: pasted images land in `08_Assets/` (§16.1), standard-markdown links are validated and path-completed, no tooling rewrites notes on save, and the generated `vault-index.json` is excluded from search.
- **Second-brain tooling in-editor** (all built-in mechanisms, no extensions): `.vscode/tasks.json` surfaces the `brain` CLI (validate, index, search, recent, per-note links — the backlinks-panel substitute), a daily-note task backed by `10_Agents/tools/vscode/daily_note.py` (the daily-notes plugin stand-in), and a homepage task that opens [[00_Meta/index]] on folder open (auto-tasks require one-time user consent; needs the `code` CLI). `.vscode/second-brain.code-snippets` offers every `09_Templates/` template plus a frontmatter block as markdown snippets, with `{{date}}` mapped to auto-filling date variables.
- **Editor-surface parity duty:** the snippet file is **generated** from `09_Templates/` by `10_Agents/tools/vscode/gen_snippets.py` and regenerated by the pre-commit hook (§18) — never hand-edited, so templates and snippets cannot drift. All other surface changes (structure, navigation, new note contracts — e.g. a future homepage note) must update both `.obsidian/` and `.vscode/` plus the §6.5 mapping; this duty is a checklist item in [[10_Agents/docs/operating-rules]].
- **Accepted gaps** (no first-party equivalent): wikilink click-through, backlinks panel, graph view, tag pane, mermaid in preview, `.canvas`. Mitigations run through the `brain` tasks above and harness skills; `brain validate` remains the authoritative convention check.
- **Acceptance criteria:** a fresh clone opened in VS Code prompts exactly the three recommended extensions; pasting an image into a note files it under `08_Assets/`; `Run Task` lists the brain, daily-note, and homepage tasks and they succeed with only `python3` on PATH (homepage additionally needs the `code` CLI); typing `sb-` in a markdown file offers the frontmatter and template snippets; a template edit followed by a commit updates the snippet file automatically; an editing session produces no unintended diffs; `brain validate` passes throughout.

Requirements, trust policy detail, candidate evaluations, and the full `.obsidian` → `.vscode` mapping: `02_Inbox/2026-08-11-vscode-editor-support.md` (path updates on triage).

## 7. Information architecture (top-level, number-prefixed)
Top-level directories (must exist; number prefixes required for ordering):

- `00_Meta/` — conventions, index (MoC), changelog, status snapshot, this PRD
- `01_Profile/` — canonical personal context: `now`, `preferences`, `defaults`, plus `identity`, `work`, `tooling-stack`, `long-running-themes`
- `02_Inbox/` — raw capture / triage queue
- `02_Outbox/` — outbound deliverables awaiting owner review and shipping (shares the `02_` prefix — both are review gates, no renumbering)
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

### 8.3 Supported harnesses (decision 2026-08-11)
Support is **standards-first** and tiered by priority. The foundation is the P0 standards track: cross-harness standards and protocols (the `AGENTS.md` convention itself, MCP, portable skill definitions) that make the vault work in any harness with no bespoke adapter. Named harnesses build on that floor — "supported" means the entrypoint loads in that harness (natively via `AGENTS.md`, or through a thin adapter like §8.2) and, at M6, the harness gets a `10_Agents/harnesses/<name>/` directory with a reference config and wiring doc (§9.3). Per-harness wiring specifics are settled when that harness's M6 adapter ships.

| Tier | Harness | Entrypoint today |
|------|---------|------------------|
| P0 | Universal standards + protocols | The `AGENTS.md` convention (§8.1) is already the entrypoint's foundation |
| P0 | Claude Code (CLI, web, and desktop app) | `CLAUDE.md` adapter (§8.2) |
| P0 | Codex (CLI, web, and desktop app) | Reads `AGENTS.md` natively |
| P0 | Opencode | Reads `AGENTS.md` natively |
| P0 | Pi | Reads `AGENTS.md` natively |
| P0 | Copilot | Reads `AGENTS.md` natively on agent surfaces; shipped `.github/copilot-instructions.md` shim for the rest |
| P1 | Cursor | To specify at M6 |
| P1 | Muse Code | To specify at M6 |

Tier meanings:
- **P0 — must support:** the standards track plus the M6 adapters (first wave: Claude Code, Codex, Opencode, Pi; **Copilot promoted from P1 on 2026-08-11** after the owner directed full Copilot support — hardened wiring, shipped `.github/` config, cloud-agent enforcement hook; the tier placement itself is this promotion's interpretation of that directive and awaits owner confirmation). The standards track is not a harness and comes first: anything achievable through a cross-harness standard is solved there, not in a harness-specific adapter — adapters carry only what a standard cannot. The vault is not harness-complete without all six rows.
- **P1 — should support:** second wave of adapters, after P0 ships.

## 9. Agent library directory (`10_Agents/`)
### 9.1 Shipped structure
```
10_Agents/
  README.md              # directory index + "start here"
  docs/                  # operating-rules.md, task-patterns.md
  solutions/             # knowledge base of solved problems, by category
  tools/brain/           # vault index CLI (M5): brain.py, spec.md, vault-index.json, tests/
```

### 9.2 Solutions knowledge base
`10_Agents/solutions/` is a standing knowledge base of solutions to recurring problems, organized by category. Agents **may append** solution notes here whenever they solve something worth not re-deriving later — this is a deliberate, bounded carve-out from the Inbox-first rule. Solution notes must carry required frontmatter (including `audience/agent` and `type/solution`), use kebab-case filenames, and follow the note format in `10_Agents/solutions/README.md`. Agents add notes; restructuring or deleting within `solutions/` still requires human direction.

### 9.3 Plugin library structure (shipped: `tools/brain/` at M5; `skills/` and `harnesses/` at M6)
The directory is a plugin library:
```
10_Agents/
  skills/<skill-name>/   # Agent Skills format: SKILL.md + optional bundled files
  tools/brain/           # executable tools; brain shipped here at M5 (§19)
  harnesses/<name>/      # harness-specific adapters (hooks, rules)
```
Design principles: universal primitives (skills, tools) work across any agent harness; skills use the **Agent Skills format** — folder-per-skill with a `SKILL.md` carrying YAML frontmatter (decision 2026-08-11) — so harnesses that understand the standard consume them unchanged; harness-specific adapters are isolated under `harnesses/<name>/` and carry only what a cross-harness standard cannot; adapters ship reference configs and wiring docs — or, where zero-setup requires it, working config committed at root scope (dot-paths like `.github/` sit outside the note corpus; `CLAUDE.md` (§8.2) is the precedent, and Copilot's instructions shim + agent hook ship this way, 2026-08-11). Which harnesses get adapters, and in what order, is defined by the support tiers in §8.3 (standards-first).

**Write policy (decision 2026-08-11):** the Inbox-first carve-out extends to this library — agents may add or update **agent-generated** skills and tools directly, tagging them `workflow/draft` until the human promotes them. Template-**shipped** skills and tools are canonical (§11) and follow §6.3 change control. Restructuring or deleting still requires human direction.

### 9.4 Discovery
Agents discover available docs and solutions by reading `10_Agents/README.md` and, since M5 (2026-08-11), the `brain` index: the committed `10_Agents/tools/brain/vault-index.json` is the primary discovery mechanism — per-note frontmatter, headings, links, and backlinks, readable directly even without running the CLI.

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

**Planned additions (M5–M6, decision 2026-08-11):** shipped plugin-library content joins the canonical set as it lands — the `brain` tool's parsing-rules spec note and each template-shipped skill. Agent-generated skills and tools instead start as `workflow/draft` (§9.3).

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
- **Editor compatibility:** Obsidian (primary) and VS Code (§6.5) are the supported editor surfaces. Any spec or structural change must consider both — new note contracts, navigation, templates, and link semantics land on `.obsidian/`, `.vscode/`, and the `brain` spec together (parity duty: §6.5 and the [[10_Agents/docs/operating-rules]] checklist).

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
- **Current (shipped at M5, 2026-08-11):** `brain validate` checks frontmatter fields, tag namespaces against the [[00_Meta/conventions]] table (read at runtime — conventions stays the single source), filename conventions, and wikilink resolution; exit codes 0 clean / 1 errors / 2 warnings.
- **Automated enforcement (shipped at M5):** the versioned pre-commit hook `.githooks/pre-commit` (installed via `git config core.hooksPath .githooks`) regenerates the committed vault index and runs `brain validate`, blocking commits on errors; `.github/workflows/validate.yml` re-runs validation and index freshness on push as the backstop for clones without the hook. This resolved the former §21 open consideration.
- **Copilot cloud agent (added 2026-08-11):** the agent hook `.github/hooks/vault-validate.json` blocks the Copilot cloud agent from finishing a session while `brain validate --check-index` reports errors (cloud-only, repeat-block-guarded, fail-open on timeout) — covering the one surface whose commits bypass git hooks and whose PR workflows are approval-gated by default. See [[10_Agents/harnesses/copilot/wiring]].
- The self-validation checklist in [[10_Agents/docs/operating-rules]] remains the agent-side first line of defense and now ends with running `brain validate`.

## 19. Milestones (status as of 2026-08-11)
### M0: Bootstrap Minimum — **Done**
Real-content files (§11.1, shipped as fill-in shells per §5), the entrypoint files per §8 (originally aliases, now the `CLAUDE.md` adapter), Inbox README, all numbered directories.
Success criterion: an agent reads the must-read sequence and produces an Inbox note that matches conventions. *(Verified 2026-08-11: `2026-08-11-prd-review.md`, written to the Inbox and archived after triage to `07_Archives/inbox/`.)*

### M1: Repo skeleton expansion — **Done**
Section READMEs for every top-level directory (directories themselves exist from M0).

### M2: Canonical navigation — **Done**
`00_Meta/index.md` and `01_Profile/defaults.md`.

### M3: Templates + agent docs — **Done**
`09_Templates/` (twelve templates, §12) and `10_Agents/` with README, `docs/` (operating rules, task patterns), and — beyond the original scope — the `solutions/` knowledge base (§9.2).

### M4: Navigation integrity — **Done**
Zero broken wikilinks (verified 2026-08-11; template placeholders exempt).

### M5: Vault Index CLI (`brain`) — **Done (2026-08-11)**
Shipped as specified below; the parsing/link-resolution contract lives in `10_Agents/tools/brain/spec.md` (owner-reviewed and promoted to canonical before implementation). Verified: all six query commands plus `validate` work with and without `--json`; the committed index is byte-reproducible and CI-checked; `validate` passes on the shipped template with zero errors; the hook demonstrably blocked a commit carrying frontmatter violations; 21-test stdlib suite with a fixture mini-vault. Requirements had been settled 2026-08-11 (see [[00_Meta/changelog]] and the implementation plan in the Inbox):
- Python CLI at `10_Agents/tools/brain/` — built directly in its final home; the earlier `.tools/` staging step and its M6 migration are dropped.
- **Stdlib-only:** no third-party dependencies; the frontmatter parser targets the vault's §10.1 contract rather than full YAML.
- Index stored as JSON at `10_Agents/tools/brain/vault-index.json`, **committed to the repo** and regenerated by the pre-commit hook (§18) so agents can read it without running Python. Serialization is deterministic (sorted, stable ordering) to keep diffs clean.
- Query commands: `list`, `search`, `links`, `tags`, `show`, `recent`; all support `--json`.
- Also: `validate` (§18) — enforced via the pre-commit hook and CI.
- Obsidian's MetadataCache is the design inspiration; concrete parsing and link-resolution rules must be specified before implementation in a spec note shipped alongside the tool (start from [[10_Agents/solutions/obsidian-issues/wikilink-resolution-rules]]).

### M6: Agent Plugin Library (core) — **Done (2026-08-11)**
Shipped as specified below (skill list confirmed by the owner at the M6 checkpoint). Verified: all nine skills pass `brain validate` including the Agent Skills contract checks (name = folder, non-empty description); the `onboard-harness` install was demonstrated end-to-end into Claude Code's user config — 18 symlinks across `~/.agents/skills/` and `~/.claude/skills/`, the marker-delimited memory-file import block in `~/.claude/CLAUDE.md` with user content preserved, re-run a byte-identical no-op, uninstall removing exactly the manifest entries while leaving pre-existing foreign skills untouched. Seven adapters shipped under `10_Agents/harnesses/` (P0: Claude Code, Codex, opencode, Pi; P1: Cursor, Copilot, Muse Code — the last `workflow/draft` as a volatile surface). Repo-only content; environment-dependent work lives in M7 (decision 2026-08-11). Standards-first build order (§8.3):
1. **Standards track (P0 foundation):** populate `10_Agents/skills/` and `10_Agents/tools/` (`brain` is already here from M5) as harness-agnostic primitives. Skills use the **Agent Skills format** (§9.3). Initial skill families: capture & triage, periodic reviews, vault maintenance, research → resource, and **onboarding** — a skill that installs the library into each supported harness's **user-level** config **symlink-first** (the harness's user-config discovery paths, e.g. `~/.claude`, symlink back to the canonical `10_Agents/` copies of every primitive that harness supports; merge for shared config files, copy where the platform lacks symlinks; manifest-driven, idempotent, reversible — links are created at install time, never committed, per the §8.2 symlink retirement), updates the harness's user-level memory file (its `CLAUDE.md` equivalent) to import the vault entrypoint, and installs the pre-commit hook. This step alone must leave harnesses outside the support list working with no bespoke adapter.
2. **P0 adapters:** add `10_Agents/harnesses/` with reference configs and wiring docs for Claude Code, Codex, Opencode, and Pi. Adapters carry only what a standard cannot.
3. **P1 second wave:** Cursor, Copilot, Muse Code.

### M7: Environment Integration — **Done (2026-08-11, template scope)**
Shipped as specified below. The template ships the three skills (`agent-orientation`, `recommended-automations`, `self-maintenance` — all canonical, all validating clean, each stating the preference ladder and the no-credentials rule inline); completion recurs in each adopter's environment by design. Verified by dry run in a test vault against a live environment: orientation produced an inventory note (six reachable sources, ladder rung per source) plus a generated source tool (`10_Agents/tools/calendar/access.md`) and paired draft capture skill, all passing `brain validate` including the skills contract. Depends on M6; ships as template content but completes in an adopter's environment (decision 2026-08-11):
- **Agent orientation:** a skill that discovers the high-value context sources available to the adopter (e.g. Teams chats, meeting transcripts, calendars, email) and generates skills and tools/scripts to access them.
- **Ingestion automations:** recommended recurring flows (email, calendar, chat) capturing into `02_Inbox/`.
- **Self-maintenance:** a skill that maintains the generated skills and tools over time (audit, prune, update), proposing draft → promotion to the human.
- **Integration preference ladder:** when a skill needs an external source, prefer (1) environment-specific custom tooling (CLI or MCP), then (2) the vendor's first-party CLI, then (3) a first-party MCP server/connector. Credentials never enter the repo (§16.2).
- A vault MCP server is **out of scope** permanently — the `brain` CLI is the vault's programmatic interface (§21).

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

**Resolved since revision 1.x (decisions recorded in the body):** strict canonical change control → adopted (§6.3, [[10_Agents/docs/operating-rules]]); review cadence → adopted (four periodic review templates plus the daily log); alias approach → symlinks shipped in 1.x, retired 2026-08-11 for the `@AGENTS.md` import adapter (§8.2); Zettelkasten home → `06_Resources/` (§7); automated enforcement → adopted as pre-commit hook + CI backstop (§18, 2026-08-11); vault MCP server → out of scope, the `brain` CLI is the vault's programmatic interface (§19 M7, 2026-08-11).
