---
title: "Changelog"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-11
---

# Changelog

Notable structural changes to the vault. For individual file history, use `git log`.

## 2026-08-11 — VS Code Alternative-Editor Support (strict first-party)

- Owner-directed: the vault is now usable in VS Code when Obsidian is unavailable, under an owner-set **strict first-party extension trust policy** (org publishers only — Microsoft, Anthropic, GitHub; built-ins preferred over extensions). Shipped root-scope `.vscode/` workspace config (the `.obsidian/` counterpart, dot-path outside the note corpus per [[00_Meta/prd]] §9.3): `extensions.json` recommends only Live Preview (HTML rendering, Microsoft) plus the P0-harness companions Claude Code (Anthropic) and Copilot (GitHub), with Prettier explicitly unwanted; `settings.json` covers the rest via built-ins — image paste into `08_Assets/`, markdown link validation and path completion, no write-on-save behavior, `vault-index.json` excluded from search.
- Community extensions (Foam, Markdown All in One, markdownlint, mermaid preview) were evaluated and **declined** under the policy — recorded as the template default, overridable per fork; wikilink navigation, backlinks, graph, tag pane, and daily-note gaps are mitigated via the `brain` CLI and harness skills. [[00_Meta/prd]] revision 2.2 records the decision as new §6.5 (Obsidian stays primary). Requirements, trust policy, candidate evaluations, and the `.obsidian` → `.vscode` mapping: `02_Inbox/2026-08-11-vscode-editor-support.md` (untriaged).
- **Second round (owner decisions):** shipped in-editor tooling via built-in mechanisms only — `.vscode/tasks.json` (brain validate/index/search/recent/links, daily note, homepage-on-folder-open) and `.vscode/second-brain.code-snippets` **generated** from `09_Templates/` by the new [[10_Agents/tools/vscode/README|vscode tools]] (`gen_snippets.py`, `daily_note.py`); the pre-commit hook now regenerates snippets alongside the index so templates and snippets cannot drift. New **editor-surface parity duty** added to the [[10_Agents/docs/operating-rules]] checklist (structural/navigation changes must update `.obsidian/`, `.vscode/`, and the §6.5 mapping). Cursor wiring notes the `.vscode/` config applies to Cursor as-is (VS Code fork). §6.5 gained acceptance criteria; README's adopt steps mention VS Code.

## 2026-08-11 — Copilot Research Deduped

- Owner-directed policy, folded into two canonical skills: notes are **atomic — one topic, one note**. [[10_Agents/skills/research-to-resource/SKILL|research-to-resource]] now requires corrective research to merge into the existing note (git keeps history; no parallel "supersedes X" notes left under banners), and [[10_Agents/skills/vault-maintenance/SKILL|vault-maintenance]] gained a duplication-scan step that proposes merges to the human. Companion rule in the same pass: **update by replacement, not accumulation** — merges and updates rewrite or delete conflicting sections instead of appending beside them (git history is the archive; appending is for logs/journals only). General form in `10_Agents/docs/operating-rules.md`, reinforced in both skills.
- Merged `06_Resources/copilot-harness-deep-dive.md` into [[06_Resources/harness-primitives-research#GitHub Copilot (P0)|the harness research's Copilot section]], which it had superseded — one note now holds all seven harnesses again. The stale M6 Copilot pass was replaced wholesale by the deep-dive's verified content (corrections, per-surface facts, wiring implications, unverified list, sources); the section header moves to P0 and the overlap matrix's Copilot hooks cell drops its "Preview/VS Code-only" qualifier. Inbound links retargeted (harnesses README, Copilot wiring doc, changelog, archived P0 plan).

## 2026-08-11 — onboard-owner Skill Shipped

- Thirteenth library skill, [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] (canonical, owner-promoted): a guided first-run for a new vault owner — plain-language teaching by doing (non-technical adopters are the ruling design constraint), a conversational interview that fills `01_Profile/`, and orchestration of [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] / [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] / [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] via their own contracts. Resumable via an onboarding checklist note that archives on completion.
- New standing write-policy exception recorded in [[AGENTS]] and [[00_Meta/conventions]]: during a live onboard-owner session, interview results write directly to `01_Profile/`, `04_Projects/`, and `05_Areas/` — in-the-moment owner approval is the review. Root README now points first-run adopters at the skill as the guided path.
- Requirements note archived to `07_Archives/inbox/2026-08-11-onboard-owner-skill-requirements.md`; the 2026-08-11 triage report archived alongside it.

## 2026-08-11 — Copilot Promoted to P0

- Owner-directed ("add copilot support"): re-verified the whole Copilot surface against live docs — deep-dive research superseding the M6 note's Copilot section (since merged into [[06_Resources/harness-primitives-research#GitHub Copilot (P0)|that section]]). Key corrections: agent hooks run on the Copilot CLI **and** cloud agent (not just VS Code); symlinked skills fail in the CLI, so the `~/.agents/skills/` install path doesn't reach Copilot; `.github/copilot-instructions.md` is the only repo instruction channel for github.com Chat/Eclipse/Visual Studio; cloud-agent PRs run no CI until a human clicks "Approve and run workflows" (default).
- Shipped **working config in-repo** (dot-paths sit outside the note corpus, so `brain` never validates or indexes them): a thin `.github/copilot-instructions.md` bootstrap shim, and an `agentStop` agent hook (`.github/hooks/vault-validate.json` + `.github/scripts/agent-stop-validate.sh`) that blocks the cloud agent from finishing while `brain validate --check-index` reports errors — cloud-only, repeat-block-guarded, `SECOND_BRAIN_HOOK_DISABLE=1` escape hatch. [[00_Meta/prd]] §18 records the new enforcement layer.
- Rewrote [[10_Agents/harnesses/copilot/wiring|the wiring doc]] to P0 depth (per-surface entrypoints, skills, enforcement chain, permissions, MCP, secrets, automation; the example `.txt` shim was deleted — the real file ships now). Corrected two canonical skills: [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] (Copilot gets `copilot skill add`/copies, never symlinks) and [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] (Copilot schedules via gh-aw/`gh agent-task`, not cron-only).
- [[00_Meta/prd]] §8.3 moves Copilot to P0 and §9.3 sanctions root-scope shipped adapter config (`CLAUDE.md` precedent). The tier placement awaits owner confirmation; plan + adversarial-review log in `07_Archives/inbox/2026-08-11-copilot-p0-plan.md`.

## 2026-08-11 — M7: Environment Integration Shipped (template scope)

- Three environment-integration skills joined `10_Agents/skills/` (canonical): `agent-orientation` (inventory the environment, interview the owner, generate per-source access tooling + draft capture skills), `recommended-automations` (recurring email/calendar/chat/transcript ingestion via each harness's scheduler, dry-run first), and `self-maintenance` (recurring audit of generated tooling: validate, probe sources, prune, propose draft → promotion). Each states the integration preference ladder (custom env tooling → first-party CLI → first-party MCP/connector) and the no-credentials rule (PRD §16.2) inline.
- Acceptance verified by dry run in a test vault: orientation produced an inventory note and a generated calendar source tool + paired draft skill, all passing `brain validate`.
- Also: new solutions category `vault-tooling/` with the index-merge-conflict recipe (regenerate, never hand-merge) — the M5 risk-mitigation note that had been deferred.
- With M5–M7 complete, the [[00_Meta/prd]] §19 roadmap is fully shipped at template scope; M7's orientation/automation cycle recurs in each adopter's environment by design.

## 2026-08-11 — M6: Agent Plugin Library Shipped

- **Nine skills** at `10_Agents/skills/` in the Agent Skills format (folder-per-skill `SKILL.md`, superset frontmatter — standard `name`/`description` plus the vault contract): `inbox-capture`, `triage-inbox`, `daily-log`, `periodic-review`, `vault-maintenance`, `link-repair`, `solution-capture`, `research-to-resource`, `onboard-harness`. Skill list confirmed by the owner; shipped skills are canonical. `brain validate` now enforces the Agent Skills contract for `skills/` dirs, and `SKILL.md` joined the filename-convention exceptions ([[00_Meta/conventions]], spec §10.2).
- **Seven harness adapters** at `10_Agents/harnesses/` (P0: Claude Code, Codex, opencode, Pi; P1: Cursor, Copilot, Muse Code — the last kept `workflow/draft` as a six-day-old volatile surface). Each ships a wiring doc (entrypoint loading, skills paths, hook install, `brain` invocation, caveats) plus reference configs, grounded in the 2026-08-11 harness research; adapters carry only what the standards track cannot.
- **Onboarding verified end-to-end** into Claude Code's user config: symlinks into `~/.agents/skills/` + `~/.claude/skills/`, marker-delimited import block in `~/.claude/CLAUDE.md`, idempotent re-run, exact-manifest uninstall with foreign content untouched.

## 2026-08-11 — M5: `brain` Vault Index CLI Shipped

- Landed `10_Agents/tools/brain/`: `spec.md` (the parsing/link-resolution/index contract, owner-reviewed and promoted to canonical), stdlib-only `brain.py` (Python 3.10+) with `index`, `list`, `search`, `links`, `tags`, `show`, `recent`, and `validate` (all supporting `--json`), the committed deterministic `vault-index.json` (built from git-tracked files; byte-identical on rebuild), and a 21-test `unittest` suite with a fixture mini-vault under `tests/`.
- Enforcement is live per [[00_Meta/prd]] §18: `.githooks/pre-commit` regenerates the index and blocks commits on validation errors (install once per clone with `git config core.hooksPath .githooks` — documented in the root README), with `.github/workflows/validate.yml` re-checking validation and index freshness on every push; `.gitattributes` shields the byte-compared index from newline conversion.
- `validate` reads the tag taxonomy from [[00_Meta/conventions#Tag Namespaces]] at runtime, and the operating-rules self-validation checklist now ends with running it. New READMEs: `10_Agents/tools/` and `10_Agents/tools/brain/`; the agents README gained a Tools section.

## 2026-08-11 — M5–M7 Requirements Settled

Requirements for the remaining roadmap were gathered from the owner and recorded in [[00_Meta/prd]]; the build detail lives in the implementation plan at `07_Archives/inbox/2026-08-11-m5-m7-implementation-plan.md`.

- **M5 (`brain` CLI):** stdlib-only Python; built directly at `10_Agents/tools/brain/` (dropped the `.tools/` staging step and its M6 migration); the JSON index is **committed** and regenerated by a pre-commit hook; `brain validate` is enforced by that hook plus a CI backstop — resolving the §21 automated-enforcement consideration.
- **M6 rescoped to the plugin-library core:** skills adopt the Agent Skills format (folder-per-skill with `SKILL.md`); initial families are capture & triage, periodic reviews, vault maintenance, research → resource, and an onboarding installer (symlink-first into each harness's user-level config — e.g. `~/.claude` — for the primitives it supports, updating the harness's `CLAUDE.md`-equivalent memory file to import the vault entrypoint; merge/copy fallbacks; manifest-driven and reversible); P0 adapters then P1, per §8.3.
- **New M7 (environment integration):** agent orientation (discover context sources like Teams, transcripts, calendars and generate access tooling), ingestion automations (email/calendar/chat → Inbox), and self-maintenance of generated plugins. Integration preference ladder: environment-specific custom tooling → first-party CLI → first-party MCP/connector. A vault MCP server was ruled permanently out of scope.
- **Write policy:** the Inbox-first carve-out extends to agent-generated skills/tools under `10_Agents/` (`workflow/draft` until promoted); template-shipped plugins will be canonical.
- **Harness research:** grounded per-harness primitive specs and the overlap matrix captured in `06_Resources/harness-primitives-research.md`. Key confirmations: `AGENTS.md` native in 6 of 7 harnesses (Claude Code needs the §8.2 adapter — the §8.3 table holds), SKILL.md supported by all 7 via the shared `.agents/skills/` path (Claude Code scans `.claude/skills/` only), command files deprecated in favor of skills, hooks/settings fully proprietary (git pre-commit stays the portable enforcement layer). One gap flagged to the owner: no portable privacy/ignore mechanism exists across harnesses.

## 2026-08-11 — Harness Support Tiers

- Recorded the target harness support list in [[00_Meta/prd]] §8.3, standards-first: **P0** — universal standards + protocols as the foundation (the `AGENTS.md` convention, MCP, portable skills — unlisted harnesses bootstrap with no bespoke adapter), then Claude Code (CLI, web, desktop app), Codex (CLI, web, desktop app), Opencode, Pi; **P1** — Cursor, Copilot, Muse Code.
- Rescoped milestone M6 into a standards-first build order: harness-agnostic skills/tools first, then adapters for the four P0 harnesses (was "at least one harness (Claude Code)"), P1 as a second wave. Adapters carry only what a standard cannot.

## 2026-08-11 — AGENTS.md Becomes the Entrypoint

- Retired `CONTEXT.md`: its content now lives in `AGENTS.md`, the standard cross-harness agent entrypoint (git history preserved via rename).
- Replaced the symlink aliases with a thin one-line `CLAUDE.md` containing only the `@AGENTS.md` memory-import line — Claude Code auto-loads it and injects the entrypoint's contents; other harnesses read `AGENTS.md` directly. As a one-line adapter, `CLAUDE.md` is exempt from the frontmatter requirement (see [[00_Meta/conventions]]) but follows canonical change control.
- Updated every reference across the vault (PRD §8 rewritten as "Universal agent entrypoint" with the decision history; bootstrap sequences, index, conventions' entrypoint exceptions, READMEs, operating rules, status).

## 2026-08-11 — PRD v2 + Spec Alignment

Resolved the findings of the spec review in `2026-08-11-prd-review.md` (then in the Inbox, since archived to `07_Archives/inbox/`; applied with explicit human approval):

- Rewrote [[00_Meta/prd]] as revision 2.0: kebab-case paths throughout, milestone status recorded (M0–M4 done, M5–M6 not started), `brain` CLI marked as planned, shipped surface documented (Journal subtree, `10_Agents/solutions/`, extra profile notes and templates), template phase described, and new sections for data sensitivity, concurrency, and validation. Tagged the PRD `workflow/canonical`.
- Declared the tag table in [[00_Meta/conventions]] the authoritative taxonomy; synced the PRD and the entrypoint (then `CONTEXT.md`, now [[AGENTS]]) to it (added `topic/*` to its summary).
- Recorded decisions: Zettelkasten home is `06_Resources/` (`type/zettel`); the milestone write-permission ladder is unadopted roadmap (Inbox-first plus the `10_Agents/solutions/` carve-out is the active policy); root aliases ship as symlinks; `00_Meta/status.md` is deliberately non-canonical and agent-updatable.
- Added the `updated:`-bump-on-edit duty (conventions, operating-rules checklist) and Inbox filename-collision rules (conventions, task-patterns, Inbox README).
- Templates: added `workflow/draft` to every suggested tag set; added related-link placeholders to the daily/weekly (and placeholder links to monthly/quarterly/yearly) review templates; normalized `template-comparison.md` frontmatter (`type/reference`, placeholder title/date).
- Navigation/docs: the entrypoint gained PARA-root links and the comparison template listing; the index now maps `08_Assets/`; asset lifecycle guidance added to `08_Assets/README`; milestone table added to [[00_Meta/status]]; removed the unshipped community-theme pin from `.obsidian/appearance.json`.

## 2026-08-10 — Template Initialized

- Forked from a personal knowledge vault into a reusable, context-neutral template.
- Removed all owner-specific content (profile data, projects, journal entries, people, resources, archives).
- Reset profile notes (`01_Profile/`) to blank templates with fill-in guidance.
- Seeded one worked example per section (project, area, resource, person, idea, daily log, weekly review) — delete these once you've learned the pattern.
- Preserved structure, conventions, note templates, and agent operating docs.

<!-- Add a dated entry here each time you make a structural change to the vault. -->
