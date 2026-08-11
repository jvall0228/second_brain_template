---
title: "M5–M7 Implementation Plan"
tags:
  - type/plan
  - audience/human
  - audience/agent
  - topic/software
  - status/done
updated: 2026-08-11
---

# M5–M7 Implementation Plan

Execution plan for the remaining [[00_Meta/PRD]] milestones, based on requirements gathered from the owner on 2026-08-11. Every spec-affecting decision below is already recorded in the PRD (the owner's answers authorized those amendments); this note holds the build detail.

## Decision Log (owner, 2026-08-11)

| # | Decision | Recorded in PRD |
|---|----------|-----------------|
| 1 | `brain` is stdlib-only Python — no third-party dependencies | §19 M5 |
| 2 | The JSON index is committed; a pre-commit hook regenerates it before commit | §19 M5, §18 |
| 3 | `brain` is built directly at `10_Agents/tools/brain/` (no `.tools/` staging, no M6 migration) | §19 M5 |
| 4 | Validation is enforced: the hook runs `brain validate` (blocking) with a CI backstop | §18, §21 resolved |
| 5 | Skills use the Agent Skills format (folder-per-skill with `SKILL.md`) | §9.3, §19 M6 |
| 6 | Initial skill families: capture & triage, periodic reviews, vault maintenance, research → resource, onboarding installer | §19 M6 |
| 7 | Inbox-first carve-out extends to agent-generated skills/tools (draft until promoted; shipped = canonical) | §6.2, §9.3, §11 |
| 8 | Environment-dependent work becomes a new milestone M7: orientation, ingestion automations, self-maintenance | §19 M7 |
| 9 | External-source access preference ladder: (1) environment-specific custom tooling (CLI or MCP) → (2) first-party CLI → (3) first-party MCP/connector | §19 M7 |
| 10 | Vault MCP server: permanently out of scope — the CLI is the vault's programmatic interface | §19 M7, §21 |
| 11 | Onboarding installs **symlink-first at user scope**: each harness's user-config discovery paths (e.g. `~/.claude`) symlink back to the canonical `10_Agents/` primitives it supports; merge for shared config files; copy fallback where symlinks are unavailable; the harness's user-level memory file (its `CLAUDE.md` equivalent) is updated to import the vault entrypoint | §19 M6 |

## M5 — Vault Index CLI (`brain`)

Goal: a zero-dependency CLI that gives agents structured, queryable access to the vault, plus enforced validation.

### Phase M5.0 — Parsing and link-resolution spec (prerequisite)

Deliverable: `10_Agents/tools/brain/spec.md` — reviewed by the owner and promoted to canonical **before** implementation starts. Starting point is [[10_Agents/solutions/obsidian-issues/wikilink-resolution-rules]]. It must pin down:

- **Frontmatter grammar:** a YAML subset matching the §10.1 contract — string scalars (bare or quoted), lists of strings, ISO dates. Notes with unparseable frontmatter are still indexed, with a recorded frontmatter error for `validate` to surface.
- **Wikilink grammar:** `[[target]]`, `[[target|display]]`, `[[target#heading]]`, and `![[embeds]]`; links inside inline code spans and fenced code blocks are ignored (the known false-positive source from the M4 link check).
- **Resolution algorithm (mirrors Obsidian):** exact filename match anywhere in the vault → shortest unique path on ambiguity → exact full-path match. **No title-based resolution** — the solutions note marks it unreliable, so `brain` treats title-only matches as unresolved and `validate` flags them.
- **Extraction scope:** headings, inline `#tags` in body text, backlinks, and file stats (path, size, mtime).
- **Index schema:** versioned (`schemaVersion`), with deterministic serialization — sorted paths and keys, LF line endings, trailing newline — so the committed index produces minimal, reviewable diffs.

### Phase M5.1 — Indexer

- Single file `10_Agents/tools/brain/brain.py` (Python 3.10+, stdlib only). Invocation: `python 10_Agents/tools/brain/brain.py <command>`; the tool README documents a shell alias for convenience.
- `brain index` walks every `.md` file (excluding `.git/`, `.obsidian/`) and writes `10_Agents/tools/brain/vault-index.json` per the spec schema.

### Phase M5.2 — Query commands

Proposed semantics (finalized in `spec.md`); every command supports `--json`, human output is plain text:

- `list` — note paths with `--dir`, `--tag`, `--type` filters.
- `search <query>` — case-insensitive substring over title, headings, and body; combinable with `--tag`.
- `links <note>` — outgoing links, backlinks, and unresolved targets for one note.
- `tags` — tag usage counts grouped by namespace.
- `show <note>` — one note's full index record.
- `recent [n]` — notes by `updated:` descending (mtime as tiebreak), per §15.

### Phase M5.3 — `validate`

Checks: frontmatter presence and required fields; tag namespace membership **read from the authoritative table in [[00_Meta/CONVENTIONS]]** so conventions remains the single source; filename conventions including the documented exceptions; wikilink resolution (template placeholders and code spans exempt); `updated:` format; `--check-index` for index freshness. Exit codes: 0 clean, 1 errors, 2 warnings only.

### Phase M5.4 — Hook and CI

- `.githooks/pre-commit`: regenerate the index, re-stage it, run `brain validate`; abort the commit on errors.
- Install via `git config core.hooksPath .githooks` — documented in the root README now, automated by the M6 onboarding skill later.
- `.github/workflows/validate.yml`: on push/PR, rebuild the index and fail if it differs from the committed copy, then run `validate` — the backstop for clones without the hook.

### Phase M5.5 — Tests, docs, closeout

- Stdlib `unittest` suite with a fixture mini-vault under `10_Agents/tools/brain/tests/`.
- `10_Agents/tools/brain/README.md` (usage; carries vault frontmatter).
- Closeout updates: PRD §19 status, [[00_Meta/STATUS]] table, [[00_Meta/CHANGELOG]], §9.4 discovery pointer, and the operating-rules checklist gains "run `brain validate`".

### M5 acceptance criteria

- All six query commands plus `validate` work in both output modes, stdlib-only.
- The committed index matches a fresh rebuild (CI-verified).
- `validate` passes on the shipped template with zero errors.
- The hook demonstrably blocks a commit that introduces a frontmatter violation.

## M6 — Agent Plugin Library (core)

Goal: the standards track made real — a skills/tools library any harness can consume — then P0/P1 adapters. Repo-only; nothing here depends on an adopter's environment.

### Phase M6.1 — Skills library (standards track)

Layout: `10_Agents/skills/<name>/SKILL.md`, Agent Skills frontmatter (`name`, `description`) **plus** the vault's `title`/`tags`/`updated` — a superset; harnesses ignore the extra keys, and `brain validate` checks both contracts for `skills/` dirs. Shipped skills are tagged `workflow/canonical` (pre-authorized).

Proposed initial set (nine — family scope is decided; the exact list is confirmed at M6 kickoff):

| Skill | Family | Does |
|-------|--------|------|
| `inbox-capture` | Capture & triage | Write a new note to `02_Inbox/` with correct frontmatter, filename, and collision handling |
| `triage-inbox` | Capture & triage | Classify Inbox notes and propose PARA destinations for human review |
| `daily-log` | Periodic reviews | Create/update today's daily log from the template |
| `periodic-review` | Periodic reviews | Run weekly/monthly/quarterly/yearly reviews (one skill, cadence parameter) |
| `vault-maintenance` | Vault maintenance | Run `brain validate`, fix findings, keep changelog/status current |
| `link-repair` | Vault maintenance | Find and fix broken wikilinks per the solutions note |
| `solution-capture` | Vault maintenance | Record a solved problem in `10_Agents/solutions/` in the standard format |
| `research-to-resource` | Research → resource | Turn a research task into a `06_Resources/` note or zettel with provenance |
| `onboard-harness` | Onboarding | Install the vault's primitives into a supported harness's config, symlink-first (see install strategy below); install the pre-commit hook |

**Install strategy (decision 2026-08-11) — symlink-first, user scope.** For every primitive the target harness supports (per its adapter's primitive map), `onboard-harness` creates **symlinks** from the harness's **user-level** config discovery paths — e.g. `~/.claude/skills/` for Claude Code, and each harness's equivalents for commands/agents; project scope is used only where a harness has no user-level home for a primitive — back to the canonical folders under `10_Agents/`. One source of truth, edits propagate instantly, no copy drift, and the vault's primitives are available in **every** session of that harness, not just when working inside the vault repo. Two deliberate exceptions:

- **Merge, don't link,** where a primitive lives inside a shared config file the user also owns (settings JSON/TOML, hook registrations, MCP entries) — symlinking whole files would clobber user config, so the skill edits those files additively and idempotently.
- **Copy as fallback** where symlinks aren't available (e.g. Windows without Developer Mode), recording a manifest so later runs detect drift and offer re-sync.

**Entrypoint wiring.** The install also updates the harness's **user-level memory file** — its `CLAUDE.md` equivalent, e.g. `~/.claude/CLAUDE.md` for Claude Code — to import or point at the vault's `AGENTS.md`, inside a marker-delimited block generated with the adopter's absolute vault path. Additive and idempotent, so the adopter's own memory content is untouched, and the block is removed cleanly on uninstall. The exact memory file and import syntax per harness is settled in each adapter's wiring doc.

Installs are manifest-driven, idempotent (re-running is a no-op), and reversible (`uninstall` removes exactly what was installed). Symlinks are created **at install time on the adopter's machine, never committed to the repo** — the in-repo symlink approach was retired (PRD §8.2). Each harness adapter's wiring doc carries the primitive map: which categories that harness supports and the exact user-config discovery paths.

Per [[06_Resources/harness-primitives-research|the harness research]], the skills map collapses nicely: one `~/.agents/skills/` link covers the six harnesses that scan the shared standard path, plus one `~/.claude/skills/` link for Claude Code — and the memory-file update targets `~/.claude/CLAUDE.md` for Claude Code while the six AGENTS.md-native harnesses need only their user-scope instruction file (or nothing, where user memory is config-driven; per-harness detail in the wiring docs).

### Phase M6.2 — P0 harness adapters

`10_Agents/harnesses/{claude-code,codex,opencode,pi}/`, each shipping a reference config and a wiring doc. Per §8.3, wiring specifics are settled at build time; every wiring doc must cover: entrypoint loading, the skills install path (user config), hook installation, and how the harness invokes `brain`. Adapters carry only what a standard cannot.

**Grounding:** [[06_Resources/harness-primitives-research|Harness Primitives Research (2026-08-11)]] holds the full per-harness surface specs and the overlap matrix. Research-informed adapter manifests (re-verify at build time):

- **Claude Code** — `CLAUDE.md` import (does not read `AGENTS.md` natively); `~/.claude/skills/` links (it does not scan the shared `.agents/skills/`); settings permission denies; `.mcp.json`. Optional nicety: an output style.
- **Codex** — `config.toml` incl. `[mcp_servers]`; reads `AGENTS.md` natively but expands no imports/wikilinks and caps project docs at 32 KiB — the wiring doc addresses both.
- **opencode** — `opencode.json` with `instructions[]` (deterministic bootstrap sequence as plain paths), MCP, and the permission map.
- **Pi** — `.pi/settings.json` + prompts; **no MCP** (TypeScript extensions instead — the preference ladder's custom-tooling rung applies).
- **P1: Cursor** — `.cursor/rules/*.mdc`, `.cursor/mcp.json`, `.cursorignore`; **Copilot** — `.github/copilot-instructions.md` pointer + `instructions/*.instructions.md`, per-surface MCP config; **Muse Code** — thin by necessity (user-scope config only; launched 2026-08-05, treat the adapter as volatile and re-verify before hardening).

Cross-cutting from the research: ship **no command files** (commands are deprecated into skills in Codex and Cursor — skills are the invocable unit everywhere); keep **one canonical MCP server manifest** in `10_Agents/` and generate per-harness configs from it; portable voice/tone lives in [[01_Profile/PREFERENCES]], not output styles (Claude Code–only).

### Phase M6.3 — P1 second wave

`cursor`, `copilot`, `muse-code` — same shape as M6.2.

### M6 acceptance criteria

- Every shipped skill passes `brain validate` and conforms to the Agent Skills format.
- `onboard-harness` installs the library end-to-end into at least Claude Code's user config (`~/.claude`) via symlinks, including the memory-file import block; re-running is a no-op, and uninstall removes exactly what was installed.
- All four P0 adapter directories ship a reference config plus wiring doc.
- A harness outside the support list can still use the vault with no adapter (the standards floor holds).

## M7 — Environment Integration

Goal: the vault reaches outward. The template ships the skills; completion happens in each adopter's environment.

### Phase M7.1 — `agent-orientation` skill

Procedure the skill encodes: inventory the harness's available tools, MCP servers, and CLIs; interview the owner about high-value sources (Teams chats, meeting transcripts, calendars, email, …); write an inventory note; for each adopted source, generate access tooling under `10_Agents/tools/<source>/` plus a paired skill, tagged `workflow/draft`. Apply the preference ladder (decision #9) at every step. Credentials never enter the repo — local auth only (CLI sessions, env vars), per §16.2.

### Phase M7.2 — `recommended-automations` skill

Proposes and wires recurring ingestion flows — email → Inbox digest, calendar → daily-log context, chat → Inbox capture — using the harness's own scheduling mechanism, documented per adapter.

### Phase M7.3 — `self-maintenance` skill

Periodically audits generated skills and tools: runs `validate`, prunes dead sources, updates for upstream changes, and proposes draft → promotion (or archival) to the owner.

### M7 acceptance criteria

- The three skills ship and validate clean.
- Dry run: orientation produces an inventory note and at least one generated source tool in a test environment.
- The preference ladder and the no-credentials rule are stated inside each shipped skill.

## Sequencing and dependencies

M5 → M6 → M7, strictly: M6's maintenance and onboarding skills call `brain` and install its hook; M7's generated content must pass `validate`, and its automations write through M6's capture skills. Within each milestone, phases land as small commit series (§17) in the order listed; M5.0 and the M6.1 skill-list confirmation are the two owner checkpoints.

## Risks and mitigations

- **Subset-YAML parser meets exotic frontmatter** → the spec defines the contract narrowly; `validate` flags anything outside it instead of guessing.
- **Committed-index merge conflicts** → deterministic serialization minimizes them; on conflict, regenerate rather than hand-merge (to be documented as a solutions note at M5).
- **SKILL.md dual-frontmatter drift** (Agent Skills fields vs vault fields) → the superset is validated by `brain validate`, which special-cases `skills/` directories.
- **Harness config formats drift** → adapters carry only what a standard cannot; wiring docs are dated and revisited each wave.
- **Hook not installed in fresh clones or agent sandboxes** → CI backstop fails the push; `onboard-harness` automates installation.

## Open items for the owner

- Review and promote `10_Agents/tools/brain/spec.md` when it lands (pre-authorized as canonical, but it will be flagged for your review before implementation proceeds).
- Confirm the nine-skill list at M6 kickoff.
- M7 source priorities (Teams vs email vs calendar vs transcripts first) — decided at orientation time, per environment.
- **Privacy-exclusion policy (from the harness research):** no portable ignore mechanism exists — only Cursor honors a repo ignore file; Codex, Pi, and Muse Code have no reliable content exclusion at all. If parts of the vault should be fenced off from some harnesses, that needs a per-harness deny strategy (and stays impossible on three of seven) — or the existing §16.2 rule ("exclusion from the repo is the only reliable protection") remains the whole policy. Owner call; relates to the §21 `restricted/*` consideration.

## Related

- [[00_Meta/PRD]] — the spec, amended 2026-08-11 with the decision log above
- [[00_Meta/STATUS]] — milestone table
- [[00_Meta/CHANGELOG]] — decision record
- [[10_Agents/solutions/obsidian-issues/wikilink-resolution-rules]] — M5.0 starting point
- [[06_Resources/harness-primitives-research|Harness Primitives Research]] — grounded per-harness specs, overlap matrix, adapter manifests
