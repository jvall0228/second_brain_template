---
title: "Changelog"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-12
---

# Changelog

## [2026-08-11] generate-artifacts | deterministic local graph and dashboard (#23)

- Added `brain artifacts` preview/JSON/check/write/open modes and a canonical [generate-artifacts](../10_Agents/skills/generate-artifacts/SKILL.md) workflow for the exact offline [artifact inventory](../08_Assets/artifacts/README.md).
- The link graph and health dashboard derive bounded metadata from authenticated Git-tracked shared snapshots only. Restricted and targeting notes, environment content, untracked or linked files, credentials, absolute host paths, raw bodies, and generated outputs are filtered before serialization.
- Both self-contained HTML files use hashed CSP sources, escaped canonical JSON, safe DOM text/attribute APIs, static and JavaScript-off summaries, keyboard/focus/reduced-motion/responsive states, and no CDN or runtime network. Hosting and real-provider notification transport remain unimplemented and disabled.
- Added exact-file ownership, rollback/concurrency refusal, controlled timestamps and manifest digests, VS Code preview/open tasks, freshness gates, and focused determinism, injection, privacy, accessibility, performance, browser-spy, and data-preservation tests.

## [2026-08-11] add-notifications | Push-only owner notification foundation (#21)

- Added `brain notify` with a strict versioned operational envelope, central privacy/link filtering, ignored selected-environment setup/state, category opt-ins, quiet hours, dedupe, hourly limits, and a bounded retry plan. Notification content rejects restricted data, credentials, absolute paths, tracking URLs, unsafe links, callbacks, and inbound actions.
- Shipped provider-neutral fake preview and explicit, create-only local file delivery with private-destination acknowledgment, remote-safety persistence preflight, mode-0600 files, compare-and-swap state, and rollback on state failure.
- Added the canonical [configure-notifications skill](../10_Agents/skills/configure-notifications/SKILL.md) and a narrow operating-policy exception for its ignored state/local test output. Slack, Google Chat, and Teams payload formatting is review-only: real transport and test send remain open pending the owner's provider and verified private-destination choice, so #21 is not yet resolved.

## [2026-08-11] add-home | deterministic local startup and navigation (#78)

- Added generated [Home](HOME.md) plus `brain home` preview/JSON/check/write modes. Home consumes structured AYMT data and one authenticated tracked safe corpus snapshot for tasks, Inbox, active work, reviews, current state, health, selected environment metadata, and navigation; it never parses AYMT Markdown or environment bodies.
- Added the canonical [refresh-home skill](../10_Agents/skills/refresh-home/SKILL.md), generated harness adapters, and a HOME-only descriptor-bound writer. Generic agents still cannot hand-edit Home, and clone-local Home remains outside hooks and the merge driver.
- Obsidian now opens Home through its native tracked `openBehavior` setting. VS Code best-effort opens the committed Home on folder open and exposes a separate read-only preview, with workspace-trust and automatic-task recovery documented.

## [2026-08-11] add-aymt | deterministic local next-action brief (#79)

- Added `brain aymt` preview/JSON/check/write modes, tracked-corpus privacy filtering, documented integer scoring and stable capped ranking, metadata-only environment freshness, and strict caller-sanitized GitHub input without connector or network execution.
- Added canonical [AYMT](AYMT.md), the [aymt skill](../10_Agents/skills/aymt/SKILL.md), generated harness adapters, and a dedicated exact-file writer that refuses foreign, linked, or concurrently replaced content. AYMT is deliberately outside hooks and the merge driver because date and selected-environment metadata are local inputs.
- Added the VS Code read-only preview task plus focused privacy, deterministic ranking, zero-write, and data-preservation tests.

Notable structural changes to the vault. For individual file history, use `git log`. Entry headers follow `## [YYYY-MM-DD] <operation> | <summary>` ([conventions § Recency](CONVENTIONS.md#recency)) — forward-only since 2026-08-11; older entries below keep their original headers.

## [2026-08-11] migrate-links | Portable relative Markdown links (#74, #75)

- Migrated every maintained internal link to source-relative inline Markdown after the exact-case framework rename, preserving human labels, heading fragments, self-links, and path identity; template placeholders now carry complete relative destinations rather than editor-specific targets.
- Relative paths with explicit extensions and GitHub-compatible heading slugs are the sole maintained-content contract across Obsidian, VS Code, GitHub, and `brain`. Obsidian now authors Markdown/relative links by default; VS Code uses its built-in navigation, completion, and validation.
- `brain migrate-links` remains a preview-first, crash-safe legacy import tool. Repository contracts require zero maintained legacy and unresolved records, a no-op migration preview, fresh generated artifacts, and exact three-surface regression coverage.

## [2026-08-11] safety | Fail-closed remote gate before personal-data access (#83)

- Added the stdlib-only `brain remote-safety` evaluator and shared guard (spec
  §19): it inspects every push URL, redacts repository identity and subprocess
  errors, and verifies GitHub privacy/template metadata through an injectable
  provider boundary.
- Public/non-private and template targets block without override; unverifiable
  targets block unless acknowledged for one invocation; no-push repositories are
  local-only and cannot persist connector results. Orientation and owner
  onboarding now apply the same boundary before personal-data reads.
- Temporary-repository, fake-provider, connector-spy, URL-variant, redaction,
  auth/timeout/subprocess, and contract tests cover the fail-closed paths without
  making a real connector or metadata call.

## [2026-08-11] rewrite-prd | Current-state dual-editor product contract (issues #71, #72, #73)

- Rewrote [PRD](PRD.md) in place as the current product contract: owner/agent audiences, both supported editors, architecture and write lanes, canonical/config/privacy contracts, tooling, journeys, acceptance, shipped M0–M12, the approved Ready roadmap, and only genuine unresolved gates.
- Removed revision banners, addenda, resolved consideration logs, M0-only acceptance framing, and shipped-as-planned language. Historical release detail remains here and in Git rather than being duplicated in the PRD.
- Updated [STATUS](STATUS.md) through M12, reconciled canonical-by-policy and generated-draft write lanes across the active agent rules, and added a PRD-specific edit-in-place rule to [OPERATING-RULES](../10_Agents/docs/OPERATING-RULES.md).

## [2026-08-11] improve-onboarding | Starter intent and atomic adoption (#81, #84)

- Owner onboarding starts with work, personal life, exploring both, or not sure yet; free-form answers remain valid, one grounded recommendation is conditional, and the owner can change direction later.
- `adopt_examples.json` is now the sole seeded-example authority. Deterministic plan/apply inventories every deletion occupant and marked line edit, refuses unsafe/missing/ignored/untracked/unmarked/dirty/stale state, binds the validator hash, applies under a durable recovery lock, independently checks the regenerated vault index, and rolls back on failure.
- Contract and adversarial tests cover the reported cross-links, aliases, manifest drift, path traversal, case/symlink hazards, dirty/stale plans, late-file and late-manifest races, recreated paths, interrupted recovery, post-apply validation, and idempotent all-or-nothing behavior.

## [2026-08-11] add-skill-adapters | Clean-clone project discovery (#82)

- Canonical skill `name`/`description` now generate versioned text adapters in `.agents/skills/` and `.claude/skills/`; adapters point back to the sole workflow body under `10_Agents/skills/` and never use symlinks.
- The deterministic stdlib generator checks missing, extra, metadata drift, collisions, strict YAML string typing, and unsafe symlinked paths. Pre-commit snapshots and transactionally restores both generated working files and the exact Git index on any later failure/interruption; post-merge regenerates, while CI and fake-home tests enforce freshness and zero external writes in project/preview mode.
- [onboard-harness](../10_Agents/skills/onboard-harness/SKILL.md) now verifies project scope by default. User-global setup is optional and split into an exact read-only preview followed by separately approved apply; the harness matrix records per-host discovery and Pi's trust caveat.

## [2026-08-11] feature | Recommended components: agent-library registry + onboarder install (follow-up to #7)

- **New registry `10_Agents/components/manifest.json`** (schema v1) is the machine-readable source of truth for installable **recommended components**, making third-party components a first-class part of the agent library without vendoring: six components across four kinds — `skill` (i-have-adhd, karpathy), `memory-block` (karpathy `CLAUDE.md` guidance), `overlay` (the Cursor/Copilot harness primitives surfaced as components), and `vault-config-preset` (a `work-fork` starting config applied via a new `merge-config` install). Documented in [README](../10_Agents/components/README.md).
- **Onboarder installs them:** [onboard-owner](../10_Agents/skills/onboard-owner/SKILL.md) gained a first-class "install recommended skills & configs" stage; [onboard-harness](../10_Agents/skills/onboard-harness/SKILL.md)'s optional step is now manifest-driven, grouped by kind, under the same reversible M6 install contract. Community content installs only to the harness's **user scope**, never the vault (separation invariant preserved).
- **Pin → track-latest reversal (owner decision, 2026-08-11):** the community submodule components now **track their upstream `main` and install the latest** commit (`source.track`, `.gitmodules` `branch = main`) rather than freezing a SHA — reversing issue #7's pinned-ref choice. The supply-chain safeguard is the **per-item owner sign-off against the content fetched at install time**; never-vendor still holds (3p content lives only under dot-pruned `.extern/`).
- **Gaps closed:** [sync-upstream](../10_Agents/skills/sync-upstream/SKILL.md) gained classify rows for `.gitmodules` / `.extern/` (owner-content — re-tracking is a curated decision) and `10_Agents/components/` (machinery); mechanical `test_components.py` enforces the manifest shape and branch-tracking. The catalog [recommended-skills](../06_Resources/recommended-skills.md) is reframed as the human-facing view naming the manifest as source of truth.
- **Also:** the root README gained one-click "Open with an AI agent" entrypoints (committed badge buttons + copyable desktop-scheme links); the five tool entrypoints are executable (`./brain.py`); the two recommended skills materialize as branch-tracking `.extern/` submodules.

## [2026-08-11] skill-update | onboard-owner adaptive interview (UI probe, ask+recommend default, research-before-ask)

- Triaged [Cursor dry-run feedback](../07_Archives/inbox/2026-08-11-onboard-owner-template-feedback.md) into [requirements R1–R5](../07_Archives/inbox/2026-08-11-onboard-owner-adaptive-interview-requirements.md) and an [implementation plan](../07_Archives/inbox/2026-08-11-onboard-owner-adaptive-interview-implementation-plan.md), then executed against [onboard-owner](../10_Agents/skills/onboard-owner/SKILL.md) on branch `onboard-owner/adaptive-interview` (PR pending).
- New "Interaction defaults" section: a lightweight, session-scoped in-thread-UI capability probe at stage 1 (independent of and earlier than agent-orientation's stage-8 profile), and "ask + recommend" (2–4 grounded options per question) as the skill-wide default interaction pattern.
- Stage 2 (profile interview) gained a research-before-ask sub-step — infer `now`/`preferences` from conversation and repo signals, `defaults` from system/environment signals — extending the inference-first posture already used by stage 3's role interview and stage 4's people map.
- The agent-orientation "Connect their world" stage gained a one-line pointer reconciling the stage-1 probe with agent-orientation's fuller harness capability profile.
- Source feedback note and both plan docs archived to `07_Archives/inbox/` with `status/done`.

## [2026-08-11] milestone | M12 Sync & self-improvement shipped (issues #6, #22) — M8–M12 plan complete

- **sync-upstream (#6, PR #61):** new canonical skill — detect (`template_version` config key, now implemented, vs upstream `template-v*` release tags), classify (a test-enforced path map covering every top-level path, with overrides for owner content incl. #12-specialized templates and the rejection log), apply (machinery direct · canonical docs via PR per §6.3 · owner content never), backfill (regenerate + `brain validate` proof), report to the Inbox; dry-run first, idempotent, **pull-only**. Upstream tagging documented as a release duty.
- **self-improve (#22, PR #62):** new canonical skill closing the template's loop — observe (`brain report` trends, git churn, triage outcomes, solution-note friction) → propose (single-topic, evidence + rollback + provenance; canonical docs by PR only, max 3 open) → owner review (never self-merged) → record rejections in the append-only [rejected-proposals](../10_Agents/docs/rejected-proposals.md) log (never re-proposed without materially new evidence) → recur monthly. Never-push-upstream is now an operating-rules "Upstream Boundary".
- **Final phase-gate review (PR #63):** the rejection log's append lane granted end-to-end (AGENTS/conventions standing exception, brain write-gate single-file allowance, sync-upstream override); both skills promoted to `workflow/canonical`; the 09_Templates sync override scoped to templates onboard-owner actually rewrote; the classify coverage test made fork-tolerant.
- **This closes the M8–M12 implementation plan:** 20 issues shipped across five phases (M8 hardening, M9 config & conventions, M10 orientation & onboarding, M11 search & tasks, M12 sync & self-improvement), each phase ending in a verification-and-review gate (full suites, live acceptance checks, and an adversarial multi-agent review sweep with independently verified findings, all fixed in-phase).

## [2026-08-11] milestone | M11 Search & tasks shipped (issues #8, #28)

- **Task tracking (#28, PR #57):** the Obsidian Tasks emoji grammar is the canonical inline task metadata (registered in [CONVENTIONS](CONVENTIONS.md) § Tasks); the index carries a per-note `tasks` field (spec §17; restricted notes reduced); new `brain tasks --open|--due|--overdue|--project|--json`; `tasks.carry_over` config key (default on) pulls yesterday's unchecked tasks into the daily note's Backlog; weekly-review prompt line + "Brain: Tasks (open)" VS Code task. Task *views* and digests stay deferred (#27/#21). The conventions bootstrap-budget tunable rose 10240→11264 with rationale.
- **QMD semantic search (#8, PR #58):** `brain search --semantic` with hybrid semantic+keyword ranking over a **gitignored** per-note embeddings sidecar (spec §18); three embedding backends — optional `sentence-transformers` local model (the one sanctioned non-stdlib dependency, lazily imported), harness-piped vectors via `brain embed --stdin-json` (+ `--query-vector`), documented external-API adapters; graceful keyword degradation when vectorless; `restricted/private` notes never enter the sidecar; invocation documented in all 7 harness wiring docs; "Brain: Semantic Search" VS Code task.
- **Phase-gate review (PR #59):** four-lens adversarial sweep; six distinct verified defects fixed — committed conflict markers in the brain README (plus a new repo-hygiene test banning them forever), the completed §17→§18 semantic renumber across nine surfaces, restricted carry-over containment, `--project` path normalization, ASCII-only task dates, and an `embed --local` empty-store guard.

## [2026-08-11] milestone | M10 Orientation & onboarding shipped (issues #3, #7, #13, #14)

- **agent-orientation output contract (#13, PR #51):** four required inventory sections (solution inventory across nine categories, harness introspection with PRD §8.3 tiers, ecosystem identification, environment capabilities & policy) and a six-rung interface ladder (custom tooling → first-party CLI → MCP/connector → wrapped vendor API → browser → none); inventory notes land per-environment under the new `10_Agents/environments/` convention (the minimal #15 slice — never bootstrap-linked, self-guarding preambles); recommended-automations and self-maintenance read the current environment's inventory.
- **Per-harness overlays (#3, PR #52):** `10_Agents/harnesses/<name>/overlay/` with `manifest.json` v1 extending PR #33's marker-managed/reversible install contract; Cursor and Copilot proto-overlays migrated; onboard-harness installs/uninstalls overlays; standards-first guard (an overlay carries only what a cross-harness standard can't express).
- **Recommended community skills (#7, PR #53):** links-only pinned-ref catalog at [recommended-skills](../06_Resources/recommended-skills.md) with per-item license/trust/sign-off contract; onboard-harness optional install to user scope under owner sign-off. The two seeded items await owner-verified pins.
- **onboard-owner people map + intent/role (#14, PR #54):** infer-first people map seeded from the environment inventory with verbatim PRD §16.2 sensitivity rules and confirm-before-landing consent flow into `03_Journal/people/`; vault-intent question drives the M9.4 specialization; role/team interview fills the `01_Profile/` shells.
- **Phase-gate review (PR #55):** four-lens adversarial sweep, 16 verified findings fixed — managed-block `.cursorignore` sync (idempotent, handles tag removal), truthful seed template, overlay artifacts gitignored, inventory `expires:`, environments write exception granted in the write rules, `restricted/private` offered as the person-note default, test scoping + a bootstrap-link guard.

## [2026-08-11] milestone | M9 Config & core conventions shipped (issues #2, #12, #16, #17, #18)

- **Vault config (#2, PR #44):** optional `00_Meta/config.yaml` in a bounded YAML subset parsed by brain's own stdlib reader (spec §15); `write_exceptions` (Inbox-first widening, enforced fail-closed via `agent_write_allowed`) and `extension_trust` implemented, plus `context` (#12) and `report` (#16) later in the phase; malformed config is per-file validate findings, never a crash; new `brain config` command.
- **Provenance (#18, PR #45):** optional `author:` (harness identifier) / `session:` frontmatter registered in [CONVENTIONS](CONVENTIONS.md); `missing-author` validate warning for agent-tagged Inbox drafts; note-writing skills updated.
- **restricted/* (#17, PR #46):** tag-only `restricted/private` in the closed taxonomy; the committed index reduces restricted notes (body-derived fields and link prose emptied — spec §8.3); `restricted-link` containment warning; `.cursorignore` generation documented; never-quote rule in operating-rules.
- **Context-aware templates (#12, PR #47):** `09_Templates/variants/` work-variant sources (outside the template contract and snippet generation, pinned by test); onboard-owner gained the fork-time specialization stage recording `context:` in config.
- **brain report (#16, PR #48):** five-section vault-health synthesis (stale-active, disconnected orphans, Inbox aging + triage debt, tag drift vs taxonomy, unresolved links) with `--json`/`--since`, config thresholds, a VS Code task, and periodic-review/vault-maintenance skills opening from it.
- **Phase-gate review (PR #49):** four-lens adversarial sweep, 13 verified findings fixed — write-gate path-traversal fail-closed, restricted link-prose stripped from the committed index, the shipped config template made grammar-safe, empty write-exception entries reported, Inbox date-prefix boundary, onboard-owner exception scope extended, fork-safe shipped-config test.

## [2026-08-11] milestone | M8 Hardening & test foundation shipped (issues #5, #9, #10, #11, #20, #24, #25)

- **Test foundation (#5, PR #36):** `10_Agents/tools/run_tests.py` runs every `10_Agents/tools/*/tests/` suite in one command, locally and in CI; the vscode tools gained their first suites; the TDD convention (tests land with the change) is documented in [README](../10_Agents/tools/README.md).
- **Validate bug fixes (#9, #10, PR #37):** unreadable notes (broken symlink, permission denied) yield a per-note `not-readable` finding instead of crashing every command; `tags: []` now fails the missing-tags check. Spec §3/§10.2 updated.
- **Hook exit codes (#11, PR #39):** the Claude Code example hook no longer swallows validation — `10_Agents/harnesses/claude-code/validate-hook.sh` maps brain errors to the PostToolUse blocking contract (stderr + exit 2); contract documented in the wiring doc.
- **Secret scanning (#24, PR #38):** `brain validate` now scans the whole working corpus (notes + assets) against a data-driven rule table (AWS/GitHub/Slack tokens, PEM keys, generic credentials, one conservative entropy heuristic) — findings are errors, enforced by hook/CI/agent chain with no new wiring; per-line escape via a `brain:allow-secret-pattern` HTML comment. Spec §10.5. GitHub-side scanning + push protection remains an owner setting.
- **Merge drivers (#25, PR #40):** `vault-index.json` and the VS Code snippets carry `merge=regenerate` (keep-ours driver, correctness from regeneration); new `.githooks/post-merge` refreshes both after any merge; spec §8.2.
- **Adopter smoke test (#20, PR #41):** `10_Agents/tools/adopt_check.py` replays the README's adoption steps in a scratch copy and requires zero validation errors; seeded-example list is data-driven and drift-checked against the README; runs in CI.
- **Phase-gate review (PR #42):** four-lens adversarial sweep over the merged diff; ten verified findings fixed — single-finding rule for unreadable notes, tool-test-tree pruning generalized, Windows-safe tests, SessionStart also arms the merge driver, adopt_check fails gracefully on unreadable trees.

## [2026-08-11] config | Claude Code sessions auto-install the pre-commit hook

- Shipped repo-scoped `.claude/settings.json` (root dot-path per [PRD](PRD.md) §9.3) with a `SessionStart` hook running `git config core.hooksPath .githooks` — every Claude Code session (local, web, cloud container) arms the pre-commit hook automatically, closing the hook-less-session stale-index failure mode at the source for the Claude fleet. Other harnesses get a new explicit bootstrap step in [OPERATING-RULES](../10_Agents/docs/OPERATING-RULES.md) (arm the hook before first commit); the reworked self-healing CI (entry below) remains the universal backstop. Claude Code wiring doc updated.

## [2026-08-11] rework | CI validate workflow is now self-healing

- `.github/workflows/validate.yml` reworked (owner-directed, after eight consecutive stale-index failures from a hook-less external agent session): instead of failing on a stale committed index, CI regenerates the generated files (`vault-index.json`, `.vscode/second-brain.code-snippets`), runs the full `brain validate` suite (content errors still fail), and on push events auto-commits the regenerated files back to the branch as `github-actions[bot]`. Loop-safe and race-safe; PR runs from forks validate without pushing (their head branch heals via its own push events). [PRD](PRD.md) §18 records the decision. Freshness remains locally enforced by the pre-commit hook; CI now repairs instead of rejecting.

## [2026-08-11] triage | VS Code support note filed to Resources

- Triaged `02_Inbox/2026-08-11-vscode-editor-support.md` → [vscode-editor-support](../06_Resources/vscode-editor-support.md) (VS Code alternative-editor requirements, trust policy, candidate research, and the `.obsidian` → `.vscode` mapping). Dropped `workflow/draft` and added `expires: 2026-11-11` (software-surface research TTL, matching the sibling harness notes); retargeted the inbound references in [PRD](PRD.md) §6.5, this changelog, and the two `.vscode/` config comments. Recorded the §6.5 acceptance-pass waiver and the note's now-merged status.

## 2026-08-11 — VS Code Alternative-Editor Support (strict first-party)

- Owner-directed: the vault is now usable in VS Code when Obsidian is unavailable, under an owner-set **strict first-party extension trust policy** (org publishers only — Microsoft, Anthropic, GitHub; built-ins preferred over extensions). Shipped root-scope `.vscode/` workspace config (the `.obsidian/` counterpart, dot-path outside the note corpus per [PRD](PRD.md) §9.3): `extensions.json` recommends only Live Preview (HTML rendering, Microsoft) plus the P0-harness companions Claude Code (Anthropic) and Copilot (GitHub), with Prettier explicitly unwanted; `settings.json` covers the rest via built-ins — image paste into `08_Assets/`, markdown link validation and path completion, no write-on-save behavior, `vault-index.json` excluded from search.
- Community extensions (Foam, Markdown All in One, markdownlint, mermaid preview) were evaluated and **declined** under the policy — recorded as the template default, overridable per fork; wikilink navigation, backlinks, graph, tag pane, and daily-note gaps are mitigated via the `brain` CLI and harness skills. [PRD](PRD.md) revision 2.2 records the decision as new §6.5 (Obsidian stays primary). Requirements, trust policy, candidate evaluations, and the `.obsidian` → `.vscode` mapping: [vscode-editor-support](../06_Resources/vscode-editor-support.md).
- **Second round (owner decisions):** shipped in-editor tooling via built-in mechanisms only — `.vscode/tasks.json` (brain validate/index/search/recent/links, daily note, homepage-on-folder-open) and `.vscode/second-brain.code-snippets` **generated** from `09_Templates/` by the new [vscode tools](../10_Agents/tools/vscode/README.md) (`gen_snippets.py`, `daily_note.py`); the pre-commit hook now regenerates snippets alongside the index so templates and snippets cannot drift. New **editor-surface parity duty** added to the [OPERATING-RULES](../10_Agents/docs/OPERATING-RULES.md) checklist (structural/navigation changes must update `.obsidian/`, `.vscode/`, and the §6.5 mapping). Cursor wiring notes the `.vscode/` config applies to Cursor as-is (VS Code fork). §6.5 gained acceptance criteria; README's adopt steps mention VS Code.

## [2026-08-11] review-fixes | Adversarial review: doc-consistency + brain hygiene

A multi-agent adversarial review of the CODE-operations branch returned no blocking defects; its 12 confirmed findings (doc drift + code hygiene) are fixed here:

- **brain:** `collect_urls` now excludes fenced/inline code and frontmatter (example URLs in code are no longer probed as dead source links); the oversized line count uses `splitlines()` (was off-by-one on newline-terminated notes). Tests added for the dead-URL classifier (403/405 skip, 404/URLError → dead), the total-bootstrap-budget warning, and code-fence URL exclusion — suite now 33.
- **Contradictions removed:** [PRD](PRD.md) §6.2/§7 updated to the two-lane write rule and the `02_Outbox/` directory (they had lagged the shipped reality); recommended-automations' "never write outside `02_Inbox/`" scoped to *inbound flows* only (rhythm jobs write to each skill's own home); [CONVENTIONS](CONVENTIONS.md) § Expiration exempt list now names `09_Templates/`+`CLAUDE.md`, and the changelog-format claim no longer overstates grep coverage.
- **Consistency:** cadence table gained a Yearly row (periodic-review already supports it); distill-note's merge-into-existing step gained the canonical carve-out its sibling skills carry; curate's link to conventions § Expiration dropped a fragile backtick heading anchor; the three onboarding skills share one CODE-stage label.

## [2026-08-11] restructure | Split harness research per-harness; resolve expires backfill review

Owner approved the four action items in the (now archived) [`expires:` backfill review](../07_Archives/inbox/2026-08-11-expires-backfill-report.md):

- **Harness research split.** The 114 KB [harness-primitives-research](../06_Resources/harness-primitives-research.md) became 8 self-contained notes — [standards & protocols](../06_Resources/harness-standards.md) plus one per harness ([Claude Code](../06_Resources/harness-claude-code.md), [Codex](../06_Resources/harness-codex.md), [opencode](../06_Resources/harness-opencode.md), [Pi](../06_Resources/harness-pi.md), [Cursor](../06_Resources/harness-cursor.md), [GitHub Copilot](../06_Resources/harness-copilot.md), [Muse Code](../06_Resources/harness-muse-code.md)) — satisfying one-topic-one-note. The hub keeps the headline findings, overlap matrix, overlaps, implications, and a per-harness index. Content moved **verbatim** (line-multiset verified); the 7 wiring docs' and the changelog's fragment links retargeted to the new notes; archived-note links left frozen. Hub: 114 KB → 12 KB.
- **Decision records exempt from `expires:`.** `type/decision` added to brain's `EXPIRES_EXEMPT_TYPE_TAGS` (+ [CONVENTIONS](CONVENTIONS.md) § Expiration, spec §14); the example decision record's `expires:` dropped and `updated:` restored to its event date (event records freeze). The orphan check stays path-only — a decision record still wants inbound links.
- **Orphan READMEs linked** from [INDEX](INDEX.md) (Profile, Meta, Agent docs, Harness adapters); the orphan signal is clean without a blanket README exemption.
- **Accepted as coherent single-topic notes** (oversized-but-fine; their warnings are expected, reviewed): [PRD](PRD.md), `10_Agents/tools/brain/spec.md`, [harness-copilot](../06_Resources/harness-copilot.md). The Now-page TTL stays 12 months (the quarterly review refreshes it; a shorter TTL would double-signal).

## [2026-08-11] recategorize | CODE-staged catalog, stage notes, changelog format (Ops Plan Phase 7)

- [README](../10_Agents/skills/README.md) restructured into CODE-staged sections (Capture / Organize / Distill / Express / System / Onboarding) with "The CODE Loop in This Vault" intro mapping stage → skills → directories (R5); skill names stay imperative verbs — categorization, no renames (R1). [AGENTS](../AGENTS.md) points at the loop in one Key Links line.
- Every SKILL.md now opens with a one-line **CODE stage:** note (R1), with boundary notes where a skill spans stages (R4): research-to-resource is Capture + Distill; periodic-review's weekly cadence is the Organize heartbeat; vault-answer and express-packet close the Express → Capture loop.
- Changelog entry headers standardized to the grep-parseable form above (R21), documented in [CONVENTIONS](CONVENTIONS.md) § Recency — this entry is the first compliant one; history is untouched.

## 2026-08-11 — Rhythm & Reviews (Ops Plan Phase 6)

- **One canonical cadence table** now lives in [README](../10_Agents/skills/README.md) § The Rhythm (daily log → weekly triage/review/Outbox sweep → monthly maintenance/curation → quarterly refresh incl. self-maintenance audit); [CONVENTIONS](CONVENTIONS.md) § Operating Rhythm points there and nothing duplicates it.
- [recommended-automations](../10_Agents/skills/recommended-automations/SKILL.md) charter widened to two flow families: inbound capture flows (unchanged) plus **rhythm jobs** — headless skill runs wired from the cadence table under the **unattended contract** (self-contained outcomes only; judgment → Inbox report; the run's output is the deliverable, never a plan or a question). Guardrails: no automation ships from `02_Outbox/`; everything dry-runs first.
- [periodic-review](../10_Agents/skills/periodic-review/SKILL.md) gained the **goal-alignment check** (each active project vs [NOW](../01_Profile/NOW.md), and vice versa), the **archive completion path** (done/dead projects and areas → proposed move to `07_Archives/` via merge-notes' safe-move, with changelog entry), and the quarterly duty to **refresh the Now page** with the owner. Weekly/monthly/quarterly review templates gained the matching Alignment section.
- [onboard-owner](../10_Agents/skills/onboard-owner/SKILL.md) now teaches the rhythm in stage 4 and pitches rhythm jobs in stage 6.

## 2026-08-11 — Express & Outbox (Ops Plan Phase 5)

- **New structure `02_Outbox/`** — the vault's loading dock: outbound deliverables awaiting the owner's review and shipping. Lifecycle mirrors the Inbox (draft → owner ships → `07_Archives/outbox/` with `status/done`); trends toward empty; **agents never ship**. Shares the `02_` prefix — both are review gates, no renumbering.
- New canonical skill [express-packet](../10_Agents/skills/express-packet/SKILL.md): assembles briefs, outlines, decision docs, comparisons, and draft posts/emails *from* vault notes with provenance wikilinks, behind a per-packet **privacy gate** — no `01_Profile/` or `03_Journal/` content without per-packet owner direction, and personal-context sources are flagged in the draft. Recapture loop returns shipping learnings to the Inbox.
- **Two-lane write rule** landed everywhere it governs: [AGENTS](../AGENTS.md) § Where Agents Write, [CONVENTIONS](CONVENTIONS.md) § Agent Write Rules, the operating-rules self-validation checklist, and [INDEX](INDEX.md). Vault content → Inbox; world-bound deliverables → Outbox; both review-gated.
- Wiring deviation (noted in the plan): `02_Outbox/` joined brain's expires/orphan exemption set — packets are ephemeral snapshots whose lifecycle is the archive path, not a TTL.

## 2026-08-11 — Curation & Signals (Ops Plan Phase 4)

- **`brain` grew its curation engine** (spec §14; all tunables in one constants block): new `curate` command reporting expired / missing / over-cap `expires:`, oversized notes, staleness weighted by backlink count, orphans, unreferenced `08_Assets/` files, and opt-in `--check-urls` dead-link probes; new `context` command reporting bootstrap-doc sizes against byte budgets (~150% of measured size, 32 KiB total). Nine new tests; suite at 30.
- **`expires:` schema shipped**: [CONVENTIONS](CONVENTIONS.md) gained the Expiration section (TTL defaults 3/6/12 months by volatility, hard one-year cap, exemption list for events-not-claims), the Bootstrap Context Budgets section, and the draft→canonical promotion checklist; five knowledge templates carry an `expires:` placeholder.
- **One-time backfill** added `expires:` to all 56 in-scope notes (3-month for harness wiring facts, 12-month evergreen default); judgment calls batched into `02_Inbox/2026-08-11-expires-backfill-report.md` for owner review. Validate-side curation warnings then flipped on — warn-only, never blocking; the three standing oversized warnings (prd, harness research, brain spec) are the queued split candidates.
- New canonical skill [curate](../10_Agents/skills/curate/SKILL.md) (epistemic integrity, vs vault-maintenance's mechanical): four outcomes per flagged note (refresh / re-verify / propose-archive / propose-split), semantic-lint pass (contradictions, superseded claims, concept-with-no-note, missing cross-links — proposals only), run summary to the Inbox.

## 2026-08-11 — Note Surgery (Ops Plan Phase 3)

- New canonical skill [merge-notes](../10_Agents/skills/merge-notes/SKILL.md): executes **approved** note surgery only — merge (survivor rewritten by replacement, backlinks retargeted via `brain links`, losers archived), split (one note per subject, backlinks re-pointed by citing intent), and the safe rename/move procedure (backlinks captured first, `git mv`, retarget, reindex).
- [vault-maintenance](../10_Agents/skills/vault-maintenance/SKILL.md)'s duplication scan now hands approved proposals to merge-notes: detection proposes there; this skill executes.

## 2026-08-11 — Triage & Distill Upgrade (Ops Plan Phase 2)

- New canonical skill [distill-note](../10_Agents/skills/distill-note/SKILL.md): reshape an existing note into an atomic evergreen zettel — declarative-claim title, standalone summary layer, wired links, supersede-by-replacement — invoked by triage for `type/zettel` items and by the Journal→Resources graduation path.
- [triage-inbox](../10_Agents/skills/triage-inbox/SKILL.md) rewritten once with the full pipeline, in order: **atomize** multi-topic captures before classifying (capture stays zero-friction), **extract action items** into project tasks, classify, **propagate** — propose edits to the existing notes each capture extends/corrects/contradicts, alongside the filing — and hand zettels to distill-note. The report gains action-item and propagation columns; everything still gates on human approval.
- [research-to-resource](../10_Agents/skills/research-to-resource/SKILL.md) gains the matching propagation step: a source is fully ingested only when every note it touches reflects it.

## 2026-08-11 — Rules & Retrieval (Ops Plan Phase 1)

- Fourteenth library skill, [vault-answer](../10_Agents/skills/vault-answer/SKILL.md) (canonical, owner-authorized via the ops implementation plan): retrieval discipline for "what do I know about X?" — brain search → index → grep, wikilink citations on every vault claim, explicit separation of vault knowledge from model knowledge, capture offers for substantive synthesized answers, and research-to-resource offers when the vault comes up empty.
- `10_Agents/docs/OPERATING-RULES.md` gained two sections: **Stuck/Escalation Protocol** (blocked or conflicting sources → `workflow/needs-review` Inbox note and stop; never guess-and-commit) and **Session-End Flush** (before session end or context compaction, write durable learnings to the daily log, an Inbox capture, or solution-capture — the vault only knows what reaches disk).
- Plan of record: `02_Inbox/2026-08-11-para-operations-implementation-plan.md` (executes the R1–R25 requirements note beside it).

## 2026-08-11 — Copilot Research Deduped

- Owner-directed policy, folded into two canonical skills: notes are **atomic — one topic, one note**. [research-to-resource](../10_Agents/skills/research-to-resource/SKILL.md) now requires corrective research to merge into the existing note (git keeps history; no parallel "supersedes X" notes left under banners), and [vault-maintenance](../10_Agents/skills/vault-maintenance/SKILL.md) gained a duplication-scan step that proposes merges to the human. Companion rule in the same pass: **update by replacement, not accumulation** — merges and updates rewrite or delete conflicting sections instead of appending beside them (git history is the archive; appending is for logs/journals only). General form in `10_Agents/docs/OPERATING-RULES.md`, reinforced in both skills.
- Merged `06_Resources/copilot-harness-deep-dive.md` into [the harness research's Copilot section](../06_Resources/harness-copilot.md), which it had superseded — one note now holds all seven harnesses again. The stale M6 Copilot pass was replaced wholesale by the deep-dive's verified content (corrections, per-surface facts, wiring implications, unverified list, sources); the section header moves to P0 and the overlap matrix's Copilot hooks cell drops its "Preview/VS Code-only" qualifier. Inbound links retargeted (harnesses README, Copilot wiring doc, changelog, archived P0 plan).

## 2026-08-11 — onboard-owner Skill Shipped

- Thirteenth library skill, [onboard-owner](../10_Agents/skills/onboard-owner/SKILL.md) (canonical, owner-promoted): a guided first-run for a new vault owner — plain-language teaching by doing (non-technical adopters are the ruling design constraint), a conversational interview that fills `01_Profile/`, and orchestration of [onboard-harness](../10_Agents/skills/onboard-harness/SKILL.md) / [agent-orientation](../10_Agents/skills/agent-orientation/SKILL.md) / [recommended-automations](../10_Agents/skills/recommended-automations/SKILL.md) via their own contracts. Resumable via an onboarding checklist note that archives on completion.
- New standing write-policy exception recorded in [AGENTS](../AGENTS.md) and [CONVENTIONS](CONVENTIONS.md): during a live onboard-owner session, interview results write directly to `01_Profile/`, `04_Projects/`, and `05_Areas/` — in-the-moment owner approval is the review. Root README now points first-run adopters at the skill as the guided path.
- Requirements note archived to `07_Archives/inbox/2026-08-11-onboard-owner-skill-requirements.md`; the 2026-08-11 triage report archived alongside it.

## 2026-08-11 — Copilot Promoted to P0

- Owner-directed ("add copilot support"): re-verified the whole Copilot surface against live docs — deep-dive research superseding the M6 note's Copilot section (since merged into [that section](../06_Resources/harness-copilot.md)). Key corrections: agent hooks run on the Copilot CLI **and** cloud agent (not just VS Code); symlinked skills fail in the CLI, so the `~/.agents/skills/` install path doesn't reach Copilot; `.github/copilot-instructions.md` is the only repo instruction channel for github.com Chat/Eclipse/Visual Studio; cloud-agent PRs run no CI until a human clicks "Approve and run workflows" (default).
- Shipped **working config in-repo** (dot-paths sit outside the note corpus, so `brain` never validates or indexes them): a thin `.github/copilot-instructions.md` bootstrap shim, and an `agentStop` agent hook (`.github/hooks/vault-validate.json` + `.github/scripts/agent-stop-validate.sh`) that blocks the cloud agent from finishing while `brain validate --check-index` reports errors — cloud-only, repeat-block-guarded, `SECOND_BRAIN_HOOK_DISABLE=1` escape hatch. [PRD](PRD.md) §18 records the new enforcement layer.
- Rewrote [the wiring doc](../10_Agents/harnesses/copilot/wiring.md) to P0 depth (per-surface entrypoints, skills, enforcement chain, permissions, MCP, secrets, automation; the example `.txt` shim was deleted — the real file ships now). Corrected two canonical skills: [onboard-harness](../10_Agents/skills/onboard-harness/SKILL.md) (Copilot gets `copilot skill add`/copies, never symlinks) and [recommended-automations](../10_Agents/skills/recommended-automations/SKILL.md) (Copilot schedules via gh-aw/`gh agent-task`, not cron-only).
- [PRD](PRD.md) §8.3 moves Copilot to P0 and §9.3 sanctions root-scope shipped adapter config (`CLAUDE.md` precedent). The tier placement awaits owner confirmation; plan + adversarial-review log in `07_Archives/inbox/2026-08-11-copilot-p0-plan.md`.

## 2026-08-11 — M7: Environment Integration Shipped (template scope)

- Three environment-integration skills joined `10_Agents/skills/` (canonical): `agent-orientation` (inventory the environment, interview the owner, generate per-source access tooling + draft capture skills), `recommended-automations` (recurring email/calendar/chat/transcript ingestion via each harness's scheduler, dry-run first), and `self-maintenance` (recurring audit of generated tooling: validate, probe sources, prune, propose draft → promotion). Each states the integration preference ladder (custom env tooling → first-party CLI → first-party MCP/connector) and the no-credentials rule (PRD §16.2) inline.
- Acceptance verified by dry run in a test vault: orientation produced an inventory note and a generated calendar source tool + paired draft skill, all passing `brain validate`.
- Also: new solutions category `vault-tooling/` with the index-merge-conflict recipe (regenerate, never hand-merge) — the M5 risk-mitigation note that had been deferred.
- With M5–M7 complete, the [PRD](PRD.md) §19 roadmap is fully shipped at template scope; M7's orientation/automation cycle recurs in each adopter's environment by design.

## 2026-08-11 — M6: Agent Plugin Library Shipped

- **Nine skills** at `10_Agents/skills/` in the Agent Skills format (folder-per-skill `SKILL.md`, superset frontmatter — standard `name`/`description` plus the vault contract): `inbox-capture`, `triage-inbox`, `daily-log`, `periodic-review`, `vault-maintenance`, `link-repair`, `solution-capture`, `research-to-resource`, `onboard-harness`. Skill list confirmed by the owner; shipped skills are canonical. `brain validate` now enforces the Agent Skills contract for `skills/` dirs, and `SKILL.md` joined the filename-convention exceptions ([CONVENTIONS](CONVENTIONS.md), spec §10.2).
- **Seven harness adapters** at `10_Agents/harnesses/` (P0: Claude Code, Codex, opencode, Pi; P1: Cursor, Copilot, Muse Code — the last kept `workflow/draft` as a six-day-old volatile surface). Each ships a wiring doc (entrypoint loading, skills paths, hook install, `brain` invocation, caveats) plus reference configs, grounded in the 2026-08-11 harness research; adapters carry only what the standards track cannot.
- **Onboarding verified end-to-end** into Claude Code's user config: symlinks into `~/.agents/skills/` + `~/.claude/skills/`, marker-delimited import block in `~/.claude/CLAUDE.md`, idempotent re-run, exact-manifest uninstall with foreign content untouched.

## 2026-08-11 — M5: `brain` Vault Index CLI Shipped

- Landed `10_Agents/tools/brain/`: `spec.md` (the parsing/link-resolution/index contract, owner-reviewed and promoted to canonical), stdlib-only `brain.py` (Python 3.10+) with `index`, `list`, `search`, `links`, `tags`, `show`, `recent`, and `validate` (all supporting `--json`), the committed deterministic `vault-index.json` (built from git-tracked files; byte-identical on rebuild), and a 21-test `unittest` suite with a fixture mini-vault under `tests/`.
- Enforcement is live per [PRD](PRD.md) §18: `.githooks/pre-commit` regenerates the index and blocks commits on validation errors (install once per clone with `git config core.hooksPath .githooks` — documented in the root README), with `.github/workflows/validate.yml` re-checking validation and index freshness on every push; `.gitattributes` shields the byte-compared index from newline conversion.
- `validate` reads the tag taxonomy from [CONVENTIONS](CONVENTIONS.md#tag-namespaces) at runtime, and the operating-rules self-validation checklist now ends with running it. New READMEs: `10_Agents/tools/` and `10_Agents/tools/brain/`; the agents README gained a Tools section.

## 2026-08-11 — M5–M7 Requirements Settled

Requirements for the remaining roadmap were gathered from the owner and recorded in [PRD](PRD.md); the build detail lives in the implementation plan at `07_Archives/inbox/2026-08-11-m5-m7-implementation-plan.md`.

- **M5 (`brain` CLI):** stdlib-only Python; built directly at `10_Agents/tools/brain/` (dropped the `.tools/` staging step and its M6 migration); the JSON index is **committed** and regenerated by a pre-commit hook; `brain validate` is enforced by that hook plus a CI backstop — resolving the §21 automated-enforcement consideration.
- **M6 rescoped to the plugin-library core:** skills adopt the Agent Skills format (folder-per-skill with `SKILL.md`); initial families are capture & triage, periodic reviews, vault maintenance, research → resource, and an onboarding installer (symlink-first into each harness's user-level config — e.g. `~/.claude` — for the primitives it supports, updating the harness's `CLAUDE.md`-equivalent memory file to import the vault entrypoint; merge/copy fallbacks; manifest-driven and reversible); P0 adapters then P1, per §8.3.
- **New M7 (environment integration):** agent orientation (discover context sources like Teams, transcripts, calendars and generate access tooling), ingestion automations (email/calendar/chat → Inbox), and self-maintenance of generated plugins. Integration preference ladder: environment-specific custom tooling → first-party CLI → first-party MCP/connector. A vault MCP server was ruled permanently out of scope.
- **Write policy:** the Inbox-first carve-out extends to agent-generated skills/tools under `10_Agents/` (`workflow/draft` until promoted); template-shipped plugins will be canonical.
- **Harness research:** grounded per-harness primitive specs and the overlap matrix captured in `06_Resources/harness-primitives-research.md`. Key confirmations: `AGENTS.md` native in 6 of 7 harnesses (Claude Code needs the §8.2 adapter — the §8.3 table holds), SKILL.md supported by all 7 via the shared `.agents/skills/` path (Claude Code scans `.claude/skills/` only), command files deprecated in favor of skills, hooks/settings fully proprietary (git pre-commit stays the portable enforcement layer). One gap flagged to the owner: no portable privacy/ignore mechanism exists across harnesses.

## 2026-08-11 — Harness Support Tiers

- Recorded the target harness support list in [PRD](PRD.md) §8.3, standards-first: **P0** — universal standards + protocols as the foundation (the `AGENTS.md` convention, MCP, portable skills — unlisted harnesses bootstrap with no bespoke adapter), then Claude Code (CLI, web, desktop app), Codex (CLI, web, desktop app), Opencode, Pi; **P1** — Cursor, Copilot, Muse Code.
- Rescoped milestone M6 into a standards-first build order: harness-agnostic skills/tools first, then adapters for the four P0 harnesses (was "at least one harness (Claude Code)"), P1 as a second wave. Adapters carry only what a standard cannot.

## 2026-08-11 — AGENTS.md Becomes the Entrypoint

- Retired `CONTEXT.md`: its content now lives in `AGENTS.md`, the standard cross-harness agent entrypoint (git history preserved via rename).
- Replaced the symlink aliases with a thin one-line `CLAUDE.md` containing only the `@AGENTS.md` memory-import line — Claude Code auto-loads it and injects the entrypoint's contents; other harnesses read `AGENTS.md` directly. As a one-line adapter, `CLAUDE.md` is exempt from the frontmatter requirement (see [CONVENTIONS](CONVENTIONS.md)) but follows canonical change control.
- Updated every reference across the vault (PRD §8 rewritten as "Universal agent entrypoint" with the decision history; bootstrap sequences, index, conventions' entrypoint exceptions, READMEs, operating rules, status).

## 2026-08-11 — PRD v2 + Spec Alignment

Resolved the findings of the spec review in `2026-08-11-prd-review.md` (then in the Inbox, since archived to `07_Archives/inbox/`; applied with explicit human approval):

- Rewrote [PRD](PRD.md) as revision 2.0: kebab-case paths throughout, milestone status recorded (M0–M4 done, M5–M6 not started), `brain` CLI marked as planned, shipped surface documented (Journal subtree, `10_Agents/solutions/`, extra profile notes and templates), template phase described, and new sections for data sensitivity, concurrency, and validation. Tagged the PRD `workflow/canonical`.
- Declared the tag table in [CONVENTIONS](CONVENTIONS.md) the authoritative taxonomy; synced the PRD and the entrypoint (then `CONTEXT.md`, now [AGENTS](../AGENTS.md)) to it (added `topic/*` to its summary).
- Recorded decisions: Zettelkasten home is `06_Resources/` (`type/zettel`); the milestone write-permission ladder is unadopted roadmap (Inbox-first plus the `10_Agents/solutions/` carve-out is the active policy); root aliases ship as symlinks; `00_Meta/STATUS.md` is deliberately non-canonical and agent-updatable.
- Added the `updated:`-bump-on-edit duty (conventions, operating-rules checklist) and Inbox filename-collision rules (conventions, task-patterns, Inbox README).
- Templates: added `workflow/draft` to every suggested tag set; added related-link placeholders to the daily/weekly (and placeholder links to monthly/quarterly/yearly) review templates; normalized `template-comparison.md` frontmatter (`type/reference`, placeholder title/date).
- Navigation/docs: the entrypoint gained PARA-root links and the comparison template listing; the index now maps `08_Assets/`; asset lifecycle guidance added to `08_Assets/README`; milestone table added to [STATUS](STATUS.md); removed the unshipped community-theme pin from `.obsidian/appearance.json`.

## 2026-08-10 — Template Initialized

- Forked from a personal knowledge vault into a reusable, context-neutral template.
- Removed all owner-specific content (profile data, projects, journal entries, people, resources, archives).
- Reset profile notes (`01_Profile/`) to blank templates with fill-in guidance.
- Seeded one worked example per section (project, area, resource, person, idea, daily log, weekly review) — delete these once you've learned the pattern.
- Preserved structure, conventions, note templates, and agent operating docs.

<!-- Add an entry at the top for each structural change: ## [YYYY-MM-DD] <operation> | <summary> -->
