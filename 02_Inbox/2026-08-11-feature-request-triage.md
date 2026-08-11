---
title: "Feature-request triage: scan, classification, and qualification of open issues"
tags:
  - audience/agent
  - audience/human
  - type/log
  - topic/software
  - workflow/draft
  - status/active
updated: 2026-08-11
author: claude-code
session: https://claude.ai/code/session_0194H8b6W4qpn7DQVKEc7y73
---

# Feature-Request Triage — 2026-08-11

Scan of all **30 open issues** (#2–#29, #31, #32; #1 and #30 are PRs) in `jvall0228/second_brain_template`, classified by kind and module, and qualified for implementation readiness. Purpose: prepare feature requests for fleshing-out and implementation sequencing. *(Corrected 2026-08-11: an earlier revision miscounted 31 issues / 28 features.)*

## Headline findings

- **26 feature requests, 3 bugs (#9, #10, #11), and 1 scope/meta item (#31).** The bugs are not feature requests but are all small, fully repro'd, and worth fixing before feature work touches `brain.py`.
- **Issue quality is already high.** Every issue has a body with scope, design notes, and cross-references; none is a bare one-liner. "Fleshing out" mostly means **resolving named open decisions**, not writing missing specs.
- **No labels exist on any issue.** #31 (owner-accepted) already prescribes `module/*` labels as "the immediate, zero-refactor win" — applying them, plus `type/feature` / `type/bug`, is the cheapest next action.
- **Two dependency hubs gate most of the backlog:** **#2 (vault config)** — declared home for decisions in #6, #12, #15, #16, #17, #18, #21, #26, #28, #32 — and **#13 (orientation inventory contract)** — prerequisite for #14, #15, #19, #21, #23, #28, #29.

## Classification

Module assignments follow #31's owner-authored mapping. Readiness tiers:

- **T1 Ready** — spec'd well enough to implement now (change-controlled spec edit ≠ blocker).
- **T2 Decision-gated** — implementable once one or two named decisions are made.
- **T3 Dependency-gated** — blocked on another issue landing first.
- **T4 Scoping needed** — needs a survey, phasing decision, or PRD amendment before design.

### Bugs (fix first — all T1, all in `brain`/harness config)

| # | Title (short) | Qualification |
|---|---|---|
| #9 | Unreadable note crashes every brain command | Repro + fix direction given (catch `OSError` per file, per-note error). Small. Spec §10 edit per §6.3. |
| #10 | `tags: []` passes missing-tags check | Repro + fix direction given (treat empty list as missing; keep template exemption). Small; includes dead-code cleanup. |
| #11 | Example hook `brain validate \|\| true` is a no-op | Fix direction given (shim: re-emit to stderr, exit 2; document exit-code contract in wiring.md). Small. |

### Features — T1 Ready

| # | Title (short) | Module | Qualification |
|---|---|---|---|
| #5 | Test runner for TDD workflow | core | Scope enumerated (single entrypoint, CI wiring, coverage for `gen_snippets.py` / `daily_note.py`). Natural companion to the three bug fixes (fixtures named there). |
| #16 | `brain report` vault-health synthesis | core | All five report sections defined; inputs already in `vault-index.json`. Sequence: spec.md first (§6.3), then implement with tests (#5). |
| #20 | Adopter-flow smoke test | core | Four concrete steps + failure modes listed. Stdlib script + CI job. Note forward-compat: #32 later wants this as a module-combination matrix — keep the step list data-driven as the issue already says. |
| #24 | Secret scanning in enforcement chain | core | Rule list, allowlist marker (`brain:allow-secret-pattern` HTML comment), GitHub-scanning backstop all specified. |
| #25 | Git merge drivers for generated files | core | Mechanism fully specified incl. degrade path and post-merge hook. Small, additive. |
| #18 | Provenance frontmatter | core | Purely additive; recommendation already in-body (harness-level granularity). Only residual decision is field-name bikeshed. |

### Features — T2 Decision-gated

| # | Title (short) | Module | Open decision(s) blocking implementation |
|---|---|---|---|
| #2 | YAML vault config | core | File location + canonicality; YAML-subset grammar bounds. **Highest-leverage decision in the backlog** — ten other issues name it as their home. Decide first. |
| #12 | Context-aware periodic templates | core | Pick among 3 options; body leans option 2 (fork-time specialization via `onboard-owner`). Feeds #6's classify step. |
| #17 | `restricted/*` namespace | core | Spec decision: how the committed index treats restricted content (exclude vs reduce). Directory convention yes/no. |
| #28 | Task/todo module | core | Emoji vs text-token metadata syntax (body suggests stealing Obsidian Tasks grammar — that largely resolves it). External-bridge explicitly deferred. |
| #4 | `brain` on PATH / plugin bin | integrations | Per-vault resolution design for multi-fork setups; Windows shim approach. |
| #7 | Recommended skills + user memory-file content | agent-library | Vendored copies vs links-only (licensing/staleness); per-item owner sign-off policy. |
| #13 | agent-orientation inventory contract | agent-library | Essentially spec'd (categories, ranking ladder incl. new browser rung); "decision" is just adopting the contract into the canonical skill per §6.3. Closest of T2 to ready — and unblocks the most. |
| #14 | onboard-owner people map + role/intent | agent-library | Ready once #13's inventory shape exists (people-map inference reads it); consent/confirmation flow already defined. |
| #6 | Upstream sync skill | agent-library | Upstream version-marker mechanism (ties to #2). Classify-step rules accumulate inputs from #12, #15, #22, #32 — worth drafting the classification table during flesh-out. |

### Features — T3 Dependency-gated

| # | Title (short) | Module | Gated on |
|---|---|---|---|
| #15 | Environment-scoped infra docs | integrations | #13 (produces the content). Own open questions: env naming/fingerprint drift, local-overlay vs committed, index-or-flag. |
| #19 | Mobile capture (email-to-Inbox v1) | integrations | #13 (email interface), #15 (env scoping), #18 (provenance). v1 shape itself is well defined. |
| #21 | Brain notification channel | integrations | #13/#15 (platform + channel-id home). v1 push scope defined; v2 bidirectional explicitly later. |
| #23 | Artifact & visualization skill | integrations | #13 (hosting discovery) for shared render; local-render path (mermaid + self-contained HTML to `08_Assets/`) could start earlier. #16 is its main data source. |
| #26 | Cross-vault interop | agent-library | v0 (rules in operating-rules.md) is actually **T1 — cheap, ship first** as the body says. v1 gated on #2 (channel declarations) + #18 (provenance). |
| #29 | n8n/Zapier execution layer | integrations | #13 (new automation-platforms category), #15, #18. Shippable piece (example n8n JSON) gated on the email-to-Inbox flow (#19) existing. |
| #22 | Self-improving loop | agent-library | #16 (evidence), #6 (pull boundary + conflict handling). Guardrails well specified; needs the rejected-proposals log convention decided. |
| #32 | Selective module installation | core | #31 (manifest as source of truth), #2 (recorded module set), #6 (sync semantics), #20 (test matrix). Hardest named sub-problem: wikilink integrity across pruned modules. |

### Features — T4 Scoping needed

| # | Title (short) | Module | What's needed before design |
|---|---|---|---|
| #8 | QMD (Query Markdown): semantic vector search | core | *(Reclassified 2026-08-11 — QMD meant Query Markdown, not Quarto; owner correction.)* Semantic search over vault notes in all supported harnesses via `brain search --semantic`. Decision-gated on the embedding source (optional local model vs harness-side vectors vs external API) — the one place stdlib-only can't hold. Effectively T2 now. |
| #27 | Built-in web UI | services | Requires a deliberate **PRD §3 amendment** (currently a stated non-goal). Phase 1 (read-only `brain serve`) is small once amended; phases 2–3 pull in #16, #23, #28, #19. |

### Meta / scope

| # | Title (short) | Qualification |
|---|---|---|
| #31 | Modularize: 5 modules + mechanics | Owner-authored partition with full backlog mapping. Mechanic 1 (GitHub labels) is immediately actionable with zero refactor; mechanic 3 (PRD amendment for directory ownership) goes through §6.3. Shared-module extraction explicitly deferred until a second consumer appears. |

## Qualification summary — suggested order of attack

1. **Quick wins, no decisions:** fix bugs #9/#10/#11 → land #5 (runner) alongside → apply #31's labels across the backlog.
2. **Unblock the hubs:** decide #2 (config location + grammar) and adopt #13 (inventory contract). These two convert most of T3 to actionable.
3. **T1 features in any order:** #16, #20, #24, #25, #18 (+#26 v0 rules).
4. **Decision batch for T2:** #12 (recommend option 2), #17, #28, #4, #7, #14, #6.
5. **Then T3 in dependency order**, with #8 surveyed and #27's PRD amendment decided deliberately.

## Milestone plan

Six milestones continuing the PRD's M-numbering (M0–M7 shipped). Owner scope decision (2026-08-11): **implement everything except modularization (#31, #32), cross-vault (#26), the `module/integrations` set (#4, #15, #19, #21, #23, #29), and the web UI (#27)** — those ten issues park in a final deferred milestone for the next phase of work. (Owner explicitly confirmed deferring mobile capture #19 and web UI #27.) Ordering of the planned work follows the dependency analysis: hardening first, then the #2 and #13 decision hubs, then feature waves.

| Milestone | Theme | Issues |
|---|---|---|
| **M8 — Hardening & test foundation** | Bugs, tests, enforcement; zero open decisions | #5, #9, #10, #11, #20, #24, #25 |
| **M9 — Config & core conventions** | The #2 decision hub + conventions-level features it anchors | #2, #12, #16, #17, #18 |
| **M10 — Orientation & onboarding** | The #13 decision hub + skill/onboarding surface | #3, #7, #13, #14 |
| **M11 — Search & tasks** | Insight-out features on top of the M9 core | #8, #28 |
| **M12 — Sync & self-improvement** | Upstream flow and the improvement loop | #6, #22 |
| **M13 — Deferred: integrations, cross-vault, modularization, web UI** | Next phase of work, after M8–M12 | #4, #15, #19, #21, #23, #26, #27, #29, #31, #32 |

Notes on the deferral's edges:
- **#13 orientation writes environment-scoped results, whose home is #15 (deferred).** A minimal landing convention (even just "one inventory note per environment under `10_Agents/environments/`, never bootstrap-linked") should ship with #13 so its output isn't homeless; full #15 scoping machinery stays deferred.
- **#4 deferred** means all docs keep the `python3 .../brain.py` long form — the M11 web UI and `brain search --semantic` docs should not assume a PATH install.
- **#26's v0** (session-scoping rules in operating-rules.md, no machinery) is cheap and can still land out-of-band with #22's operating-rules edits; the deferred milestone holds v1 sync channels.
- **#28's VS Code/web-UI task views and #21 notification digests** are the deferred edges of planned issues — #28 in M11 ships conventions + `brain tasks` + daily-log carry-over only.
- #31's label mechanic already shipped; the rest of modularization is deferred with it. GitHub milestone shells must be created by the owner (no API path from agent sessions); issue assignment is then agent-doable.

## Flesh-out notes (defects found in issue bodies during scan)

Three body defects were found during the scan and **repaired 2026-08-11 ~12:29** (bodies now carry repair notes):

- **#24**: inline allowlist-marker example had been stripped by GitHub's markup sanitizer — restored as the `brain:allow-secret-pattern` HTML-comment marker, spelled out in words since raw HTML comments don't survive issue bodies.
- **#18**: `session:` frontmatter example value similarly stripped — restored (`session: SESSION_REF`).
- **#19**: two dangling "the provenance issue" references — now name #18 explicitly.

**Labels applied 2026-08-11:** #31 mechanic 1 is done — all 30 issues now carry `module/*` labels per the owner mapping (plus `module/core` for #32; #31 itself is `type/meta`) and `type/feature` / `type/bug` classification.

**Decision recommendations posted 2026-08-11** as comments on the seven decision-gated issues: #2 (config at `00_Meta/config.yaml`, bounded YAML subset, reserved keys), #12 (option 2 — fork-time specialization), #17 (tag-only v1, index reduces restricted notes), #28 (Obsidian Tasks emoji grammar), #4 (git-style walk-up vault resolution shim), #7 (links-only pinned refs, per-item sign-off), #6 (`template_version` + upstream tags, classify table draft). Owner approval of each recommendation converts the issue to ready.

---
*Agent-generated (feature-request triage session, branch `claude/feature-request-triage-azsvau`). Inbox-first: awaiting human triage.*
