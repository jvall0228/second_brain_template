---
title: "Ready backlog implementation plan"
tags:
  - audience/agent
  - audience/human
  - type/reference
  - topic/software
  - workflow/needs-review
  - status/active
updated: 2026-08-11
author: codex
---

# Ready Backlog Implementation Plan

## Objective and authority

Resolve issues #4, #15, #21, #23, #71, #72, #73, #74, #75, #78, #79, #81, #82, #83, and #84 from the approved contract in [[02_Inbox/2026-08-11-ready-backlog-requirements-brainstorm]]. Ready PR #80 and non-Ready items are excluded.

This plan is review-gated because it proposes protected canonical changes, core renames, and a link-format migration. Approval authorizes only the repository work listed here. Real credentials/destinations, repository visibility, PATH/shell choices, and user-global installation retain explicit owner gates.

## Delivery rules

1. Safety (#83/#82) lands before connectors or new connected skills.
2. Brain behavior is spec-first; tooling stays stdlib-only.
3. Preview/apply protects bulk, global, adoption, and external writes.
4. #75 lands before #74; the dual-format link engine lands before the corpus rewrite.
5. Local artifacts precede hosting/notifications; AYMT precedes Home.
6. One reviewable PR per work package; #74 is split into engine and corpus PRs.
7. Close issues only after their requirements pass on merged `main`.
8. Every phase ends with full tests, validation, generated-file freshness, adoption smoke, and a focused adversarial review.

## Work packages and critical path

| WP | Issues | Package |
|---:|---|---|
| 1 | #83 | Remote safety gate |
| 2 | #82 | Project-local skill adapters |
| 3 | #81, #84 | Onboarding entry and atomic cleanup |
| 4 | #71, #72, #73 | Current-state dual-editor PRD |
| 5 | #15 | Environment identity/selection |
| 6 | #4 | Portable `brain` resolver/installer |
| 7 | #75 | Uppercase core filenames |
| 8 | #74 | Markdown link engine/migrator |
| 9 | #74 | Markdown corpus migration |
| 10 | #79 | AYMT |
| 11 | #78 | Home/editor startup |
| 12 | #23 | Local artifact pipeline |
| 13 | #21 | Push-only owner notifications |
| 14 | all | Final contract/closure |

```mermaid
flowchart LR
  W1["WP1 Safety"] --> W13["WP13 Notify"]
  W2["WP2 Repo skills"] --> W5["WP5 Environments"]
  W5 --> W6["WP6 brain"]
  W5 --> W12["WP12 Artifacts"]
  W7["WP7 Names"] --> W8["WP8 Link engine"] --> W9["WP9 Link corpus"]
  W9 --> W10["WP10 AYMT"] --> W11["WP11 Home"]
  W12 --> W13 --> W14["WP14 Close"]
  W11 --> W14
```

Critical path: WP2 → WP5 → WP7 → WP8 → WP9 → WP10 → WP11 → WP12 → WP13 → WP14. WP1, WP3, and WP4 merge early before their dependents.

## Phase 0 — Baseline and approval

### Tasks

- [ ] Refresh Project 3 and record any Ready-set change instead of silently changing scope.
- [ ] Record `main` SHA, Python/Git versions, filesystem case behavior, and editor versions used for smoke tests.
- [ ] Preserve unrelated work, including untracked `02_Inbox/2026-08-11-triage-report-2.md`.
- [ ] Ensure hooks/merge driver are armed: `core.hooksPath=.githooks`, `merge.regenerate.driver=true`.
- [ ] Baseline all Python tests, `brain validate`, index/snippet freshness, `adopt_check.py`, link metrics, repo-skill count, and long-form brain invocations.
- [ ] Map every `R…` and `X…` requirement to a WP and verification check.
- [ ] Add planning/dependency links to the 15 issues after approval.

Exit: baseline is green or pre-existing failures are documented; plan approval is recorded; no unrelated file is staged.

## Phase 1 — Safety and onboarding

### WP1 — Remote safety (#83, P0)

Files: `brain.py`, brain spec/tests, `agent-orientation`, `onboard-owner`, operating rules, changelog.

- [ ] Specify `brain remote-safety` states/reason codes and injectable provider boundary.
- [ ] Enumerate push URLs; normalize/redact GitHub URL forms; query repository privacy/template metadata.
- [ ] Fail closed on public/template/unknown before personal-data connector calls. Keep capability inventory separate.
- [ ] Support local-only/no-push behavior and one-session unknown acknowledgment; verified public/template remains unoverrideable.
- [ ] Integrate the shared guard into orientation, onboarding, and future personal-data adapters.
- [ ] Test all URL/state/auth/provider/no-push cases in temporary repos; spy connectors must receive zero blocked calls.

Evidence: human/JSON examples for pass/block/unknown, redaction snapshots, full green suite, merged reference on #83.

### WP2 — Repo-local skills (#82)

Files: new deterministic adapter generator/tests; generated `.agents/skills` and `.claude/skills`; hooks/CI; `onboard-harness`; harness docs.

- [ ] Derive adapter catalog from canonical skill frontmatter; mirror name/description and point to canonical SKILL.md.
- [ ] Generate text adapters (no symlinks), version markers, `--check`, and missing/extra/collision/parity checks.
- [ ] Enforce freshness in pre-commit/CI.
- [ ] Make project verification the onboarding default. Global mode previews exact paths and writes only after consent.
- [ ] Add fake-home canary; project/dry-run modes must make zero external writes.
- [ ] Publish tested compatibility/trust table; leave Copilot on its current user-copy route until proven.

Evidence: clean clone exposes Codex repo skills, generator is byte-stable, CI detects drift.

### WP3 — Onboarding/adoption (#81/#84)

Files: `onboard-owner`, `adopt_examples.json`, `adopt_check.py`, fixtures/tests.

- [ ] Add four starter intents, conditional recommendation, free-form answer, and change-later wording.
- [ ] Remove selective example deletion; manifest becomes the sole bundle authority.
- [ ] Add atomic plan/apply with exact deletions/reference edits, stale/dirty/unmarked-reference refusal, and post-apply validation.
- [ ] Test the four reported dangling links, aliases, unmarked references, dirty files, and skill-contract wording.

Phase gate: WP1–WP3 requirements pass on merged `main`; no live connector/user-home write occurred; full privacy/destructive-action review passes.

## Phase 2 — Product contract

### WP4 — PRD rewrite (#71/#72/#73)

Files: `00_Meta/PRD.md`, status, changelog, operating rules; index only if navigation changes.

Target outline: definition/audience; goals/non-goals; cross-editor experience; architecture/write lanes; canonical/config/data contracts; agent model; privacy/restriction/sync; tooling/generated files; user journeys; current acceptance; shipped M0–M12; Ready roadmap; unresolved decisions.

- [ ] Inventory PRD/status/conventions/rules/config/spec claims as current, stale, historical, duplicate, or unresolved.
- [ ] Rewrite current claims in place; move meaningful history to one changelog entry; remove revision banners/addenda/resolved narrative.
- [ ] Replace M0–M7-only and shipped-as-planned language.
- [ ] Make Obsidian and VS Code contract-level throughout; separate editor-neutral integrity from enhancements.
- [ ] Add the edit-in-place PRD maintenance rule and reconcile all current contracts.
- [ ] Search for stale phrases and run a cross-document consistency/adversarial omission review.

Exit: #71/#72/#73 close together; PRD reads as current state; canonical docs agree and validation is green.

## Phase 3 — Environment and CLI

### WP5 — Environment model (#15)

Files: brain spec/code/tests; environments README; orientation/onboarding; config/conventions; `.gitignore`; report/sync/restriction tests.

- [ ] Specify versioned `environment.json`, privacy-safe fingerprinting, ignored selector/overlay, and selection precedence.
- [ ] Implement `brain env detect|list` and `--env current|slug`; ambiguity/no match fails closed.
- [ ] Apply current-only filtering to bootstrap, search/report, maintenance, sync, and generated integrations.
- [ ] Keep all-environment diagnostic metadata-only; never emit raw identity/path/secret.
- [ ] Update orientation to generate/maintain the selected slug safely; preview migration of existing notes.
- [ ] Test zero/one/two environments, all selection routes, conflicting infrastructure, sync classification, and privacy snapshots.

### WP6 — Portable `brain` (#4)

Files: POSIX/Windows launchers, installer or subcommand, tests, brain spec, active docs/tasks/skills.

- [ ] Implement resolver precedence: `--vault`, `BRAIN_VAULT`, upward CWD walk for AGENTS + brain.py.
- [ ] Preserve arguments/output/exit code; reject invalid/ambiguous roots.
- [ ] Add install preview/apply, doctor, uninstall, recognized-overwrite protection, and reversible external manifest.
- [ ] Prefer existing writable PATH directory; never edit shell rc automatically.
- [ ] Test root/subdir, spaces/Unicode, nested/sibling forks, overrides, missing Python/tool, POSIX/Windows behavior.
- [ ] Prefer `brain` in active docs after support lands, retaining long Python fallback.
- [ ] Record current plugin-bin capability as unavailable; do not add a nonstandard manifest field.

Phase gate: two environments and two sibling forks cannot cross-select; install/dry-run tests touch no real home/shell config; #15/#4 acceptance passes.

## Phase 4 — Final core filenames

### WP7 — Uppercase core files (#75)

This PR is mechanical: no semantic content edits beyond path/reference updates.

- [ ] Freeze the 14-file manifest from the requirements note and enumerate all references/constants/allowlists/tests.
- [ ] Use two-step `git mv` for every case-only rename.
- [ ] Update links, bootstrap budgets, code constants, settings/permissions, tests, tasks, and docs from one manifest where possible.
- [ ] Regenerate index/snippets/adapters; add exact-case and filename-validation tests.
- [ ] Require `git ls-files` exact final casing and no active old-case paths outside fixtures.
- [ ] Smoke test bootstrap and navigation on case-sensitive and case-insensitive environments where CI permits.

Exit: #75 closes before #74; diff remains mechanical; all gates green.

## Phase 5 — Portable links

### WP8 — Dual-format engine/migrator (#74 part 1)

Files: brain spec/code/tests and migration fixtures; no maintained corpus rewrite yet.

- [ ] Specify generic link records, source ranges, resolution/encoding/fragments/images/placeholders/block refs.
- [ ] Parse Markdown while excluding YAML, fenced/inline code, escapes, and external URLs; retain legacy wikilinks with counts.
- [ ] Resolve source-relative paths and tested heading slugs; report ambiguity instead of guessing.
- [ ] Implement `brain migrate-links`: preview default, `--check`, `--json`, explicit `--write`, source hashes, deterministic atomic writes.
- [ ] Preserve labels, fragments, self-links, images, encoding, and line endings; refuse stale/dirty/ambiguous/unsupported plans.
- [ ] Test syntax/false positives, legacy import, idempotence, rollback, and a ≥ current-corpus performance fixture.

### WP9 — Corpus migration (#74 part 2)

- [ ] Generate a complete categorized plan on merged WP8; manually sample each link class before apply.
- [ ] Convert maintained content once; update conventions/templates/skills/examples/spec/solutions/tests to make relative Markdown canonical.
- [ ] Regenerate snippets/index/adapters; configure/document Obsidian relative Markdown new links.
- [ ] Retain only named legacy fixtures and run a second no-op migration.
- [ ] Verify same/parent/child, spaces/Unicode, display label, heading, self-link, image, and placeholder in GitHub, VS Code, Obsidian, and brain.

Rollback: if the post-apply gate fails, revert the corpus PR as a unit while retaining WP8. Do not repair a partial migration on `main`.

Phase gate: zero maintained legacy/unresolved links; idempotence and three-surface matrix pass; full repository checks green; then close #74.

## Phase 6 — AYMT and Home

### WP10 — AYMT (#79)

Files: new AYMT skill + generated adapters; brain/helper spec/tests; proposed generated `00_Meta/AYMT.md`; config only if needed.

- [ ] Define deterministic candidate schema and local collectors; GitHub is optional/authenticated.
- [ ] Score urgency/leverage/effort/confidence/dependency/staleness, dedupe outcomes, cap at 5–7.
- [ ] Render Do next / Unblock or decide / Keep warm with sources, why-now, next step, and caveat.
- [ ] Apply restriction/current-environment filtering before candidate creation.
- [ ] Add local-only, JSON explanation, preview/write/`--check`, stable-output tests.
- [ ] Add a narrow generated-write exception only after canonical approval.

### WP11 — Home (#78)

Files: generator/spec/tests; proposed `00_Meta/HOME.md`; VS Code task/docs; Obsidian setting/onboarding.

- [ ] Disposable-vault spike: toggle Obsidian 1.11 native default file and diff settings. Commit only a stable repository key; otherwise document setup + CLI fallback.
- [ ] Generate Home separately from canonical INDEX using AYMT, tasks, Inbox, projects/areas, reviews, Now/status/changelog, expiry/health, and environment.
- [ ] Keep maintainer GitHub backlog optional; omit missed-automation claims until a run-log contract exists.
- [ ] Preserve VS Code's folder-open task; document trust/automatic-task recovery.
- [ ] Test empty/adopted/stale/overdue/environment states, restriction filtering, deterministic check, startup, and navigation.

Phase gate: AYMT/Home are stable portable Markdown, INDEX is untouched by dynamic updates, and VS Code/Obsidian/GitHub behavior passes.

## Phase 7 — Local artifacts

### WP12 — Artifact pipeline (#23)

Files: new artifact skill/adapters; stdlib generator/tests; `08_Assets/artifacts/README.md`; templates/assets.

- [ ] Define deterministic manifest/naming/scope and implement link-graph + health-dashboard data.
- [ ] Filter restricted/non-current/secrets/absolute paths/raw bodies before serialization.
- [ ] Generate offline HTML with escaped JSON, safe DOM text APIs, hashed CSP or local bundle, and zero CDN/runtime network.
- [ ] Add static/JS-off summary, keyboard/accessibility/reduced-motion/empty states.
- [ ] Document local browser/VS Code opening; define but disable hosting until environment configuration + owner consent.
- [ ] Test golden bytes, injection, CSP/offline, privacy, accessibility, large-vault budget, and browser opening.

Exit: #23 local-first requirements pass without credentials/network; shared hosting remains explicitly optional.

## Phase 8 — Owner notifications

### WP13 — Push-only v1 (#21)

Provider gate: ask which existing private surface to use. If none is selected, merge envelope + fake/file transport but keep #21 open with one explicit owner action. Do not install a connector plugin merely to implement repository runtime behavior.

Files: new notification library/tests/fixtures and setup skill/adapters; environment overlay schema; non-secret config; operating-rule exception.

- [ ] Define versioned provider-neutral envelope and privacy class; implement fake/file transport first.
- [ ] Implement exactly one selected real provider with text fallback and provider limits.
- [ ] Keep credentials in ignored current-environment overlay/external manager; redact all boundaries.
- [ ] Verify/acknowledge private destination before one redacted test send.
- [ ] Implement category opt-ins, owner-timezone quiet hours, rate limit, dedupe, bounded transient retry, and ignored delivery state.
- [ ] Route producers through the envelope; buttons are safe links only—no inbound mutation endpoint.
- [ ] Add narrow owner-authorized operational-notification exception to “agents never ship.”
- [ ] Test categories, redaction, payload/fallback, DST/quiet hours, dedupe/rate/retry/corrupt state, and approved real-provider smoke.

Exit: no secret in git/logs/artifacts; fake contract passes; selected private channel receives one approved test; close #21 only then.

## Phase 9 — Consolidation and closure

### WP14 tasks

- [ ] Update PRD/status once with final current behavior; add concise changelog entries, not implementation diaries.
- [ ] Reconcile conventions, config, operating rules, task patterns, brain spec, environment/artifact/editor docs.
- [ ] Regenerate index, snippets, and project skill adapters.
- [ ] Search for old-case paths, maintained wikilinks, hardcoded deprecated invocations, secrets, hostnames, usernames, and absolute paths.
- [ ] Re-run every requirement against merged `main`; record honest final test/link/skill metrics.
- [ ] For each issue, comment with merged PR/commit, acceptance evidence, adopted decisions, and limitations; then update project status and close.

### Final gate

| Check | Required result |
|---|---|
| All Python tests | 0 failures |
| `brain validate` | 0 errors |
| Index/snippets/skill adapters | all freshness checks clean |
| `adopt_check.py` | atomic cleanup green |
| Maintained links | 0 legacy, 0 unresolved |
| Secret/path privacy scans | 0 findings |
| Working tree | only explicitly preserved owner files |
| GitHub/VS Code/Obsidian | required link/home matrix passes |
| POSIX/Windows | launcher/path cases pass |
| Artifacts | offline/CSP/injection/accessibility pass |
| Notifications | fake + selected real smoke, no secrets |

Adversarial review lenses: privacy, wrong environment/fork, partial/destructive writes, parser correctness, case/path portability, spec drift, artifact injection/accessibility, notification leakage/spam.

## Risk and rollback register

| Risk | Mitigation / rollback |
|---|---|
| Personal data reaches public vault | WP1 first; fail closed; connector spy tests |
| Link corruption | dual-read engine, plan hashes, split corpus PR, unit revert |
| Case rename lost | two-step moves, exact-case CI |
| Skill drift/global writes | generated adapters, CI parity, fake-home canary |
| Wrong environment/fork | explicit precedence, ambiguity failure, two-env/two-fork tests |
| Artifact injection | escaped data/text APIs/CSP/offline and malicious fixtures |
| Webhook secret/spam | ignored overlay, redaction, opt-in categories, quiet/rate/dedupe |
| PRD loses valid behavior | claim inventory, consistency matrix, omission review |
| Editor startup mismatch | disposable-vault spike, versioned fallback |

## Owner action queue

- [ ] Approve protected canonical changes and narrow generated HOME/AYMT exceptions.
- [ ] Select a private notification provider/destination or accept that #21 remains open after fake/file infrastructure.
- [ ] Store the selected credential outside git for the smoke test.
- [ ] Opt into user-global harness discovery only if skills are needed outside this repo; default no.
- [ ] Choose/add a PATH directory manually if no existing writable PATH directory exists; installer will not edit shell rc.
- [ ] Resolve any unknown remote state before real personal-data access; public/template cannot be bypassed.

## Progress ledger

| WP | Status | PR/commit | Gate |
|---:|---|---|---|
| 1–3 Safety/onboarding | Not started | — | — |
| 4 Product contract | Not started | — | — |
| 5–6 Environment/CLI | Not started | — | — |
| 7 Names | Not started | — | — |
| 8–9 Links | Not started | — | — |
| 10–11 AYMT/Home | Not started | — | — |
| 12 Artifacts | Not started | — | — |
| 13 Notifications | Not started | — | — |
| 14 Consolidation | Not started | — | — |

## Immediate next action

Approve the requirements decisions and this plan, then start WP1 (#83). No real-data connector or notification work begins until the Phase 1 gate passes.
