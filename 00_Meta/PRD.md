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

# Second Brain Product Requirements

## 1. Definition and audience

Second Brain is a reusable Markdown knowledge vault. Git supplies history; Obsidian and VS Code are supported human surfaces; `AGENTS.md`, portable skills, and `brain` define agent behavior. The context-neutral template becomes an owner vault through onboarding. It serves:

- the **owner**, who captures, reviews, organizes, and approves changes;
- **agents**, which bootstrap from repository instructions and work within explicit write and privacy rules;
- the **maintainer**, who evolves machinery without overwriting owner content.

## 2. Goals

- Keep one portable, auditable context and knowledge source.
- Support capture, retrieval, review, and maintenance in Obsidian and VS Code.
- Give agents predictable paths, bounded contracts, and safe write lanes.
- Combine PARA organization, Bullet Journal cadence, and evergreen Zettelkasten notes.
- Keep tooling deterministic and local-first while supporting safe template updates.

## 3. Non-goals

- An always-on hosted app, general web UI, or agent orchestrator.
- A replacement for Git, editors, or external systems of record.
- Full YAML/Markdown interpretation beyond the bounded `brain` contract.
- Repository access control; `restricted/private` is leak resistance.
- Automatic publication, upstream pushes, or unapproved outbound delivery.
- Identical editor features; integrity and core workflows require parity, enhancements may differ.

## 4. Template and adoption state

Blank guided profiles and one example per documented section teach the structure; they are not owner facts. README and `adopt_examples.json` define the complete seed set, while atomic onboarder cleanup remains unshipped (#84). An adopted fork has meaningful profile context. Personal and employer-visible contexts use separate forks.

## 5. Product architecture

### 5.1 Information architecture

| Path | Contract |
|---|---|
| `00_Meta/` | Product policy, navigation, status, config, and structural history |
| `01_Profile/` | Owner context loaded or consulted by agents |
| `02_Inbox/` | Untriaged vault captures and agent output |
| `02_Outbox/` | Outbound drafts awaiting owner review and shipping |
| `03_Journal/` | Subjective experience, people, ideas, plans, and periodic notes |
| `04_Projects/` | Active outcomes with an end state |
| `05_Areas/` | Ongoing responsibilities |
| `06_Resources/` | Objective references and evergreen zettels |
| `07_Archives/` | Inactive or superseded material |
| `08_Assets/` | Images, documents, exports, and other non-note files |
| `09_Templates/` | Stable note-template contracts |
| `10_Agents/` | Skills, tools, harness wiring, environments, and reusable solutions |

Numeric prefixes stabilize ordering. Journal material is subjective; Resources are objective. Ideas may graduate from Journal to atomic Resource zettels.

### 5.2 Portability boundary

Tracked paths are vault-relative and case-sensitive. Markdown/Git are durable; `.obsidian/`, `.vscode/`, `.github/`, and `.claude/` are adapters outside the note corpus. Credentials, absolute paths, embeddings, and user-scope machine-state install manifests stay untracked or external.

## 6. Core workflows and write lanes

### 6.1 Universal agent bootstrap

The contractual minimum order is:

1. `AGENTS.md`
2. `01_Profile/NOW.md`
3. `01_Profile/PREFERENCES.md`
4. `00_Meta/CONVENTIONS.md`

Structured writes or navigation beyond Inbox also require `00_Meta/INDEX.md` and `01_Profile/DEFAULTS.md`. READMEs and the committed index provide deeper discovery.

### 6.2 Agent write pattern

Agent captures, research, reports, and proposals default to `02_Inbox/`; outside deliverables go to `02_Outbox/` via `express-packet`, then the owner ships. Standing exceptions cover solution notes, the append-only rejection log, `onboard-owner` session outputs, and `agent-orientation` inventories plus paired draft capture skill/tool bundles. A user-invoked canonical skill may direct only its documented session writes. Generated orientation bundles are not canonical-by-policy until owner promotion; `write_exceptions` may add directories but cannot weaken canonical or privacy rules. Other destinations require current owner direction.

### 6.3 Change control

Canonical notes and canonical-by-policy artifacts require a PR or explicit approval. The latter include template-shipped skills/tools, `00_Meta/config.yaml`, and named tagless entrypoint and harness/editor adapters. Agent-generated orientation bundles remain drafts until owner promotion. Otherwise agents propose via Inbox with `workflow/needs-review`. Status remains a non-canonical snapshot.

Edit superseded PRD claims in place; record the event once in the changelog and leave detail to Git. Do not add revision banners, addenda, or resolved decision logs.

### 6.4 Owner journeys

1. **Adopt:** fill the profile, choose context, remove the README seed set, validate, capture.
2. **Capture/organize:** use Inbox when uncertain, then triage into PARA or Journal.
3. **Find/act:** use INDEX, READMEs, editor search, `brain`, backlinks, tasks, and reports.
4. **Review/express:** use cadence templates and owner-reviewed Outbox packets.
5. **Maintain:** validate, regenerate, pull template releases, and propose improvements.

### 6.5 Cross-editor experience

Obsidian and VS Code are contract surfaces. Obsidian is primary; VS Code is a supported alternative, not a raw-file fallback.

**Editor-neutral integrity:** Markdown, Git, stable paths, frontmatter, templates, and `brain` preserve bytes, validate links, and prevent unintended rewrites.

**Obsidian:** tracked config provides navigation, properties, backlinks, graph, tags, templates, daily notes, and relative Markdown links (`useMarkdownLinks: true`, `newLinkFormat: relative`).

**VS Code:** tracked config provides Markdown link/path checks, image paste into Assets, `brain`/task/daily-note commands, folder-open navigation, and generated snippets. Extension recommendations default to first-party publishers; `extension_trust: relaxed` records an override. Automatic tasks need workspace trust and consent.

Gaps need an editor-neutral route or documentation. Navigation, template, link, homepage, and command changes evaluate both configs; snippets are never hand-edited. See [vscode-editor-support](../06_Resources/vscode-editor-support.md).

## 7. Content and navigation contracts

- Kebab-case filenames use only the exceptions in conventions.
- Notes require `title`, list-form `tags`, and ISO `updated`; templates and `CLAUDE.md` are explicit exceptions.
- `updated` drives recency; Git, changelog, and status carry finer history, structural events, and state.
- Contextual Markdown tasks use Obsidian Tasks emoji grammar; `brain tasks` is editor-neutral.
- Template paths are stable; work specialization rewrites only documented periodic templates.
- Maintained content uses source-relative inline Markdown links with explicit extensions and GitHub-compatible heading slugs; `brain` reports resolution, ambiguity, encoding, fragment, and case findings. Legacy wikilinks are import-only and must be migrated before acceptance.
- INDEX is the human map and is not overwritten by dynamic summaries.

## 8. Agent model

### 8.1 Standards-first behavior

`AGENTS.md`, portable skills, and `brain` are the common layer. Harness adapters contain only discovery, trust, hook, or config details standards cannot express.

### 8.2 Entrypoint adapters

`CLAUDE.md` contains only `@AGENTS.md`. It has no frontmatter but is canonical-by-policy. Other harnesses load `AGENTS.md` natively or by documented shim; no committed symlink is required.

### 8.3 Supported harnesses

| Tier | Surfaces |
|---|---|
| P0 | Standards layer, Claude Code, Codex, opencode, Pi, Copilot |
| P1 | Cursor, Muse Code |

Each harness has a wiring contract. P0 is required support; P1 is maintained second-wave support. Wiring records discovery, hooks, connectors, privacy, scheduling, and gaps and requires periodic re-verification.

### 8.4 Environment integrations

Orientation inventories capabilities and policy before generating draft tools. Access preference is local tooling, first-party CLI, first-party connector/MCP, wrapped API, browser, then “none.” Auth stays environmental; automations are proposed and generated integrations audited. Automatic environment selection remains roadmap work.

## 9. Agent library, tooling, and generated files

### 9.1 Library structure

`10_Agents/` contains skills, adapters, tools, environment notes, components, docs, and solutions. Shipped primitives are canonical; generated primitives start as drafts.

### 9.2 Solutions knowledge base

Agents may append `type/solution` notes; restructuring or deletion is owner-directed.

### 9.3 Skills, components, and harness installation

Canonical skills use folder-per-skill Agent Skills format. `onboard-harness` installs primitives and overlays to user scope through a reversible user-scope machine-state manifest while preserving foreign content. Community components remain sign-off-gated external pointers, never vendored. Overlays cover only standards gaps; root adapters remain tracked.

### 9.4 `brain` and generated data

`brain` is Python 3.10+ and normed by [spec](../10_Agents/tools/brain/spec.md). It is stdlib-only except optional local embeddings, which degrade to keyword search. Commands cover indexing/query, validation, curation, context, config, reports, tasks, and embeddings.

The committed index and VS Code snippets are deterministic tracked outputs. Hooks regenerate them, `merge=regenerate` avoids hand-merges, and CI checks/self-heals freshness. Embeddings and user-scope machine-state install manifests are untracked.

## 10. Frontmatter, tags, and restriction data

### 10.1 Frontmatter

Notes require `title`, non-empty list `tags`, and ISO `updated`. Templates may use placeholders. Agent Inbox drafts record `author` and, when available, `session`. `expires` is expected outside documented exemptions.

### 10.2 Tags

[CONVENTIONS](CONVENTIONS.md#tag-namespaces) is the single authoritative taxonomy. The current namespaces cover audience, type, topic, workflow, status, and `restricted/private`; other documents summarize rather than redefine that table.

### 10.3 Restriction semantics

`restricted/private` forbids spreading content beyond its note but is not access control. Agents do not quote it into unrestricted notes. Mechanical protections reduce index data, exclude embeddings/task carry-over, warn on links, and support Cursor ignore. Paths, titles, frontmatter, and targets may remain visible; most harnesses lack repository ignore.

## 11. Canonical and config contracts

A canonical artifact defines structure, policy, navigation, or behavior. Only the owner assigns/removes the tag. Shipped skills/tools and named adapters are canonical-by-policy when they cannot carry tags. Promotion requires approval, current validated content, discoverability, and changelog entry.

`00_Meta/config.yaml` is optional bounded-YAML fork policy, canonical-by-policy and secret-free:

| Key | Current effect |
|---|---|
| `write_exceptions` | Adds approved agent-write directory prefixes |
| `extension_trust` | Records first-party or relaxed VS Code extension policy |
| `context` | Records personal/work specialization already applied at onboarding |
| `report` | Sets health-report aging thresholds |
| `tasks` | Controls daily-note task carry-over |
| `template_version` | Records the upstream template release adopted by the fork |

Reserved keys have no behavior until implemented. Config never changes committed-index semantics.

## 12. Templates

Stable templates cover project, area, resource, zettel, five review cadences, decision, media, and comparison. Top-level templates generate VS Code snippets; `variants/` are onboarding inputs only.

## 13. Current functional requirements

- Clean clones include structure, bootstrap, both editor configs, templates, skills, harness wiring, and validation.
- Adoption completes without manual link or generated-file repair.
- Capture, query, links, tasks, reviews, curation, and expression work locally.
- Validation reports content, secret, restriction, and curation findings without crashing on unreadable files.
- Template sync previews classified changes, preserves owner content, and never pushes upstream.
- Generated integrations are draft, environment-scoped, and credential-free in tracked content.

## 14. Non-functional requirements

- **Portability:** UTF-8 Markdown, vault-relative paths, documented Python floor, no platform-specific tracked state.
- **Determinism:** committed generators are byte-stable and exclude ambient machine state; time-dependent queries document their inputs.
- **Diffability:** no save-time rewrites; generated files are regenerated, not hand-merged.
- **Safety:** preview destructive/external actions; review canonical changes; owner content wins ambiguity.
- **Privacy:** filter before derived/external output where supported; never commit credentials.
- **Parity:** Obsidian and VS Code impact checks for structure, navigation, links, templates, commands.
- **Low overhead:** lightweight capture; stronger maintenance and commit checks.

## 15. Recency and maintenance

Every edit bumps `updated`. Changelog records structural events once; Git owns history. Reports, curation, context budgets, reviews, and self-improvement surface work without silently rewriting owner knowledge.

## 16. Privacy, assets, and sync

### 16.1 Assets

New assets land under `08_Assets/`, append-only by default, and are secret-scanned. Archive or remove obsolete/reproducible assets only with owner direction.

### 16.2 Data sensitivity

Connected agents and Git collaborators may read the vault. Never commit credentials or material that must not reach them. `03_Journal/people/` notes concern **third parties** — keep them factual and respectful, and write nothing you would not stand behind if read back. For health, financial, or otherwise sensitive content, remember that anything committed is visible to every agent and service with repo access; keep out material that must not reach them. Legal and relationship-conflict detail also requires owner judgment. Separate work/personal forks.

Restrictions cannot replace permissions or separate forks. External authentication stays in CLI sessions, keychains, connector stores, or environment variables.

### 16.3 Sync boundaries

Git is owner-controlled sync. `sync-upstream` previews and pulls: machinery may update, canonical changes are proposed, owner content is untouched, and agents never write upstream unless explicitly its owner. Editor sync services are outside this contract.

## 17. Multi-agent concurrency

Agents check overlaps, use collision-safe Inbox names, preserve unrelated edits, scope commits, and never force-push. Rebuild generated artifacts after integration; reconcile shared-source semantics and revalidate.

## 18. Validation and enforcement

`brain validate` is authoritative: `0` clean, `1` errors, `2` warnings. The test runner discovers tool suites. Hooks regenerate and block errors; CI runs tests, adoption smoke, validation, and freshness. Copilot adds a cloud-agent stop gate. Warnings are debt, not blockers.

`brain` changes are spec-first and tested; editor changes check both surfaces. Completion requires targeted tests, full validation, freshness, and adversarial review for contradictions, privacy, destructive behavior, portability, and false shipped claims.

## 19. Shipped milestones and Ready roadmap

### 19.1 Shipped M0–M12

| Milestone | Shipped capability |
|---|---|
| M0–M4 | Bootstrap, full structure, navigation, templates, agent docs, and link integrity |
| M5 | Canonical `brain` spec, deterministic index/queries, validation, hooks, and CI |
| M6 | Canonical skills, adapters, and reversible user-scope onboarding (§9.3) |
| M7 | Environment integration and the source-access ladder (§8.4) |
| M8 | Test foundation, validation hardening, secret scanning, merge regeneration, and adopter smoke |
| M9 | Fork config, provenance, `restricted/private`, context variants, and health reporting |
| M10 | Structured orientation, harness overlays, recommended components, and owner onboarding |
| M11 | Markdown task tracking and optional semantic search |
| M12 | Pull-only template sync and the propose/review/record self-improvement loop |

Release detail belongs in [CHANGELOG](CHANGELOG.md), not in this current-state specification.

`brain` remains the vault's programmatic interface; a vault MCP server is out of scope.

### 19.2 Approved Ready roadmap

The active contract is [2026-08-11-ready-backlog-implementation-plan](../02_Inbox/2026-08-11-ready-backlog-implementation-plan.md), grounded by [2026-08-11-ready-backlog-requirements-brainstorm](../02_Inbox/2026-08-11-ready-backlog-requirements-brainstorm.md). This maintained dual-editor contract implements #71, #72, and #73. The remaining approved packages stay roadmap work until accepted on merged `main`:

1. remote safety and project-local skill discovery (#83, #82);
2. onboarding entry and atomic example cleanup (#81, #84);
3. environment selection and a portable `brain` command (#15, #4);
4. uppercase core filenames and portable Markdown links (#75, #74);
5. Actions You May Take and generated Home (#79, #78);
6. local offline artifacts and push-only owner notifications (#23, #21).

## 20. Current acceptance criteria

- Bootstrap is ordered, budgeted, and path-correct; maintained notes pass frontmatter, taxonomy, filename, and link checks.
- Tool tests, validation, freshness checks, and scratch adoption finish with zero errors; generated outputs are byte-stable.
- Obsidian and VS Code perform documented navigation, edit, template, task, and validation flows without unintended rewrites.
- Restriction reduction, secret scan, and credential-free config fixtures pass and never claim access control.
- Write lanes agree across entrypoint, conventions, config, rules, skills, and `brain`.
- Upstream sync previews, pulls only, preserves owner content, and is change-set reversible.
- Status distinguishes fresh template, shipped framework, adopted fork, roadmap, and unresolved decisions.

## 21. Unresolved decisions

Only owner choices or evidence gates remain:

- **#15:** owner-chosen environment slugs; implementation proves private matching and ambiguity behavior.
- **#4:** owner-approved existing writable PATH target; never edit shell startup files automatically.
- **#78:** commit Obsidian's default-file key only after a disposable-vault proof; otherwise document UI/CLI setup.
- **#21:** owner selects a private destination before any real send; otherwise fake/file transport only and the issue stays open.
- **Cross-harness privacy:** no portable repository ignore exists; stronger access exclusion would need a separate product decision.
