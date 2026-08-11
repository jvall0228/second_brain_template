---
title: "Implementation plan: M8–M12 (all non-deferred issues)"
tags:
  - audience/agent
  - audience/human
  - type/reference
  - topic/software
  - workflow/draft
  - status/active
updated: 2026-08-11
author: claude-code
session: https://claude.ai/code/session_0194H8b6W4qpn7DQVKEc7y73
---

# Implementation Plan — M8–M12

Detailed work plan for the **20 non-deferred issues**, sequenced per [[02_Inbox/2026-08-11-feature-request-triage|the triage note]]. Deferred (M13, out of this plan): #4, #15, #19, #21, #23, #26, #27, #29, #31, #32.

**Baseline** (main @ PR #33 merged): `brain.py` stdlib-only CLI with spec (`10_Agents/tools/brain/spec.md` §1–14), 43-test suite wired into CI, self-healing CI (regenerate + auto-commit index/snippets), pre-commit hook, 18 skills, 7 harness wiring docs + shared registration (`~/.agents/second-brain/AGENTS.md`), VS Code tooling (`gen_snippets.py`, `daily_note.py`).

**Ground rules for every work package:**
1. **Spec-first (§6.3):** any behavior change to brain lands in `spec.md` before code; canonical doc changes go through PR review.
2. **Tests land with the change** (#5's TDD convention — applies from M8.1 onward).
3. **Stdlib-only** for all tooling; the single sanctioned exception is #8's optional embedding backend.
4. **Parity duty (PRD §6.5):** new brain commands get a VS Code task; template changes flow through snippet regeneration.
5. Every phase ends green: unit tests, `brain validate` 0 errors, index fresh, changelog entry.

**Effort scale:** S = small (single focused session), M = medium (1–2 sessions), L = large (several sessions / needs its own breakdown).

## Execution mode (owner-approved 2026-08-11)

This plan executes **autonomously** in a goal-driven session (Opus 4.8, ultracode effort — multi-agent orchestration per work package) until all M8–M12 packages are complete. Operating rules for that run:

- **Decision gates default to the posted recommendations.** The recommendation comments on #2, #6, #7, #12, #17, #28 and the #8 comment are the working decisions — implement them as written unless the owner overrides in the meantime. Record each adoption in the issue when closing it.
- **Delivery unit = one PR per work package** (small packages may cluster within a phase). Every PR: CI green, `brain validate` 0 errors, index/snippets fresh, adversarial self-review before merge. Canonical-doc changes ride these PRs, satisfying §6.3. Merge without waiting on the owner; the PR trail is the review record.
- **Never block on owner-only actions — queue them.** Maintain a running **Owner action queue** (this note's final section) for anything only the owner can do: enable GitHub secret scanning + push protection (M8.5), create the six milestone shells, gate overrides. Surface the queue in every progress report; proceed around it.
- **Progress tracking:** close each issue on completion with commit/PR refs; assign milestones once shells exist (labels + closures track progress meanwhile); changelog entry per phase.
- **Stop conditions:** genuine ambiguity where the plan and recommendations give no answer (ask, don't guess); anything destructive or history-rewriting on `main`; **never push to the upstream public repo** (#22's rule applies to the executing agent too).

### Phase gate (mandatory between milestones)

Each phase ends with a **verification & review gate that must pass before the next phase starts**. A gate failure is fixed inside the current phase — never carried forward.

1. **Mechanical verification on `main`:** full test suite (all tools), `brain validate` = 0 errors, index + snippets fresh, adopter smoke test green (once M8.7 exists), CI green on the last merge.
2. **Acceptance re-check:** every package's acceptance criteria in this plan re-verified against merged `main` (not against the feature branch it was developed on).
3. **Adversarial review sweep** (run as an ultracode workflow — see Orchestration): independent reviewer agents over the phase's cumulative merged diff, one per lens — correctness, spec-conformance (§6.3: does spec.md actually describe shipped behavior), portability/path-leak, cross-package regression. Each finding adversarially verified before it's accepted; confirmed findings are fixed and re-reviewed within the phase.
4. **Phase-exit criterion** from this plan's phase section confirmed true.
5. **Checkpoint report:** changelog entry for the phase, issue closures confirmed with refs, Owner action queue refreshed, one-paragraph gate verdict recorded in this note (a `### Gate log` appended per phase).

### Orchestration (ultracode)

- **Parallel packages run as dynamic workflows** (the Workflow tool): after a phase's serial head (M8.1, M9.1, M10.1), fan the remaining packages out as concurrent agents; phase gates run as find→verify workflows (reviewer fan-out, adversarial verification of findings).
- **Worktree isolation is required for parallel implementation** — each package agent works in its own git worktree on its own branch. The committed generated files (`vault-index.json`, snippets) make parallel edits to a shared checkout collide by construction; worktrees + regenerate-on-merge is the collision protocol (and after M8.6 lands, the merge driver automates the index side).
- **Merges are serialized:** parallel development, sequential integration — merge one package PR at a time, regenerating index/snippets at each merge, CI green between merges. Never merge two package branches into `main` simultaneously.
- Solo (no workflow) is fine for S-sized packages and gate fixes; the fan-out is for M/L packages and review sweeps.

### Owner action queue
- [ ] Enable GitHub secret scanning + push protection on the repo (M8.5 backstop): repo **Settings → Advanced Security → Secret Protection** — turn on *Secret scanning* and *Push protection*. `brain validate` secret scanning already enforces locally/CI; this is the GitHub-side layer only the owner can toggle.
- [ ] (Optional, bookkeeping) Create milestone shells: all 20 M8–M12 issues are already closed with PR refs, so retroactive milestones are cosmetic. The one useful shell is **"M13 — Deferred"** for the 10 open issues (#4, #15, #19, #21, #23, #26, #27, #29, #31, #32) — create it in **Issues → Milestones → New milestone** and say the word; an agent session can then assign all ten via the API.
- [ ] Review the seven decision-gate recommendations at leisure (implemented as posted on #2, #6, #7, #8, #12, #17, #28; each closing PR records the adoption). Silence = accepted stands.
- [x] ~~Verify and pin the two seeded recommended-skills items (#7)~~ — **done 2026-08-11 (PR #65):** i-have-adhd → `ayghri/i-have-adhd` @ `2ed0640` (MIT, ~19.6k★); karpathy → `multica-ai/andrej-karpathy-skills` @ `2c60614` (MIT, ~200k★, the former forrestchang viral repo). Both read and verified at the pin; per-item sign-off still applies at install time.

### Gate log

**M12 — PASSED (2026-08-11) — PLAN COMPLETE.** Both packages merged (PRs #61 sync-upstream, #62 self-improve), issues #6/#22 closed with refs; breakdown comments posted on both issues before code. Mechanical: 287→288 tests OK on merged main, `adopt_check` green, `brain validate` 0 errors, CI green; `brain config` reports all five implemented keys (`write_exceptions`, `extension_trust`, `context`, `report`, `tasks`, plus `template_version`). Adversarial sweep (4 lenses, 18 agents, widened whole-plan regression lens): 6 confirmed findings, 8 refuted; all fixed in-phase via PR #63 — headline: the rejection log's direct-append instruction contradicted the vault's write lanes, now a granted single-file standing exception wired through AGENTS.md/conventions/brain's write gate/spec §15.3/both skills; both new skills promoted to `workflow/canonical`; the 09_Templates sync override scoped to actually-rewritten templates; the classify coverage test made fork-tolerant. Phase-exit criterion confirmed: the fork tracks upstream (pull-only, classified, change-controlled) and improves itself under change control — the template's full loop is closed. Changelog entry merged (PR #64). **Whole-plan verdict: all 20 non-deferred issues closed (only the 10 deferred M13 issues remain open), all five phase gates passed with logged verdicts, main green.**

**M11 — PASSED (2026-08-11).** Both L packages merged (PRs #57 tasks, #58 semantic search), issues #8/#28 closed with refs; breakdown-duty comments posted on both issues before code. Mechanical: 260→264 tests OK on merged main, `adopt_check` green, `brain validate` 0 errors, CI green. Acceptance verified live: `brain tasks --overdue` finds a seeded overdue task, `embed --stdin-json` ingests vectors, `search --semantic --query-vector` ranks, vectorless vaults degrade to keyword with exit 0. Merge-train note: both packages claimed spec §17 — tasks kept §17 (more internal refs), semantic renumbered to §18 during the M11.1 merge. Adversarial sweep (4 lenses, 35 agents): 30 confirmed findings deduplicating to six distinct defects, 1 refuted; all fixed in-phase via PR #59 — headline: my merge had committed conflict markers into the brain README (now impossible — a repo-hygiene test bans committed markers), the §17→§18 renumber completed across nine surfaces, restricted carry-over containment closed, `--project` normalization, ASCII-only task dates, `embed --local` empty-store guard. Accepted deviation: the conventions bootstrap-budget tunable rose 10240→11264 (documented rationale — the doc had grown legitimately across M9/M10/M11 and repeated byte-shaving was degrading canonical prose). Phase-exit criterion confirmed: the vault answers questions (semantic + keyword search through the CLI in every harness) and tracks work natively (tasks indexed, queried, carried over). Changelog entry merged (PR #60).

**M10 — PASSED (2026-08-11).** All 4 packages merged (PRs #51–#54), issues #3/#7/#13/#14 closed with refs; the M10.3 breakdown-duty comment (5 sub-parts) posted on #3 before code. Mechanical: 198→199 tests OK on merged main, `adopt_check` green, `brain validate` 0 errors, CI green. Adversarial sweep (4 lenses, 23 agents, findings independently verified): 16 confirmed, 3 refuted; all fixed in-phase via PR #55 — headline fixes: `.cursorignore` generation became a marker-delimited managed block (append-only could never remove an un-restricted note and duplicated per re-run), the seed template no longer claims the privacy policy is undecided, machine-local overlay installs are gitignored, environments writes got the standing exception the README claimed, person notes default to `restricted/private`, inventory notes carry `expires:`. Phase-exit criterion confirmed: orientation and onboarding produce defined, homed artifacts (four-section inventory contract landing in `10_Agents/environments/`, people/profile notes under the consent flow) and harness-specific power is systematized (overlay manifests extending the PR #33 contract). Changelog entry merged (PR #56). Owner queue addition: verify commit-pinned URLs + licenses for the two seeded recommended-skills items (#7).

**M9 — PASSED (2026-08-11).** All 5 packages merged (PRs #44–#48), issues #2/#12/#16/#17/#18 closed with refs. Mechanical: 158→162 tests OK on merged main, `adopt_check` green, `brain validate` 0 errors (3 accepted oversize warnings), CI green. Acceptance verified live in a scratch vault: `missing-author` and `restricted-link` warnings fire, restricted index reduction holds, `brain report` emits all five sections, `brain config` reports the effective merge. Merge-train note: the provenance + restricted conventions additions jointly busted the 10240-byte bootstrap budget — distilled during the M9.3 merge and again in the gate PR (final 10239 bytes). Adversarial sweep (4 lenses, 18 agents, findings independently verified): 13 confirmed, 1 refuted; all fixed in-phase via PR #49 — including three highs (write-gate path traversal fails closed; restricted link prose stripped from the committed index; the shipped config template's inline comments would have broken under its own grammar). Phase-exit criterion confirmed: config exists and is enforced (fail-closed write gate, per-file findings), conventions cover provenance + privacy, and reviews start from data (`brain report` wired into periodic-review/vault-maintenance). Changelog entry merged (PR #50).

**M8 — PASSED (2026-08-11).** All 7 packages merged (PRs #36–#41), issues #5/#9/#10/#11/#20/#24/#25 closed with refs. Mechanical: 92→96 tests OK on merged main, `adopt_check` green, `brain validate` 0 errors (3 pre-existing oversize warnings), index/snippets fresh, CI green on the tip. Acceptance re-checked on main incl. live repros (broken symlink → `not-readable` finding, no traceback; seeded AWS key → `secret-aws-access-key-id`, exit 1). Adversarial sweep (4 lenses, 15 agents, every finding independently verified): 10 confirmed findings, 1 refuted; all 10 fixed in-phase via PR #42 (single-finding rule for unreadable notes; tool-test-tree pruning generalized + spec §2/§10.5 aligned; brain README refreshed; Windows-safe tests; SessionStart arms the merge driver; adopt_check graceful on unreadable trees). Phase-exit criterion confirmed: the enforcement chain (frontmatter + secrets + adoption contract) is fully mechanized through hook/CI/agent paths, and every tool is under test via one runner. Changelog entry merged (PR #43).

---

## Phase M8 — Hardening & test foundation

Goal: trustworthy enforcement chain and a test harness that the rest of the plan builds on. No open decisions — start immediately. Internal order matters: **M8.1 first** (everything after lands with tests), then bugs, then enforcement features.

### M8.1 — #5 Test runner & TDD convention (M)
- **Build:** `10_Agents/tools/run_tests.py` — stdlib unittest discovery across `10_Agents/tools/*/tests/`; exit non-zero on failure.
- **Wire:** replace CI's brain-only `unittest discover` step with the runner; optionally add to `.githooks/pre-commit` behind a fast-path check.
- **Backfill tests:** `10_Agents/tools/vscode/tests/` — `gen_snippets.py` (escaping, determinism, `--check`), `daily_note.py` (placeholder resolution, existing-note no-op, ISO-week year boundary).
- **Document:** TDD convention in `10_Agents/tools/README.md` (tests land with or before the change).
- **Accept:** one command runs every suite locally and in CI; vscode tools covered.

### M8.2 — #9 Unreadable note crashes brain (S)
- **Spec:** §10 gains a `not-readable` per-note error (OSError caught in `load_text`, best-effort posture per §2).
- **Code:** catch per file alongside existing `not-utf8`; `validate` reports it, other commands skip the file.
- **Tests:** broken-symlink fixture + permission-denied case (skip on platforms where root ignores modes).
- **Accept:** repro from the issue (broken symlink in `02_Inbox/`) yields a finding, not a traceback, for validate/index/list/search.

### M8.3 — #10 `tags: []` passes validation (S)
- **Spec:** §10 missing-tags fires on empty list as well as absent/null; template placeholder exemption unchanged.
- **Code:** fix the `raw_tags is None` guard (~brain.py:622); remove the dead `has_placeholder` branch.
- **Tests:** `tags: []` fixture (error) + template fixture (exempt).

### M8.4 — #11 Hook example swallows validation (S)
- **Build:** shim (inline in settings JSON or a small script under `10_Agents/harnesses/claude-code/`): run validate; on nonzero, re-emit findings to **stderr**, `exit 2` (Claude Code PostToolUse contract).
- **Docs:** fix `settings-example.json`; explain the exit-code contract in `wiring.md` so future adapters don't repeat it.
- **Tests:** contract test asserting the example no longer contains `|| true` (mechanical, not prose-lock).

### M8.5 — #24 Secret scanning (M)
- **Spec:** §10 secret rules, **data-driven** (rule table: name, regex, severity): AWS `AKIA…`, GitHub `ghp_`/`gho_`/`github_pat_`, Slack `xox…`, PEM headers, generic `api[_-]key` assignments, conservative high-entropy heuristic. Findings are errors → existing hook/CI/agent-stop chain enforces with no new wiring.
- **Allowlist:** inline HTML-comment marker `brain:allow-secret-pattern` on the flagged line; the marker is the audit trail.
- **Scope:** all text files in the working corpus, not just notes.
- **Tests:** fixture positives per rule, negatives (prose, hashes), allowlisted line, entropy false-positive guard.
- **Owner action:** enable GitHub secret scanning + push protection on the repo (settings UI — not agent-doable).

### M8.6 — #25 Merge drivers for generated files (S)
- **Build:** `.gitattributes` (`vault-index.json`, `second-brain.code-snippets` → `merge=regenerate`); driver = keep-ours, correctness from regeneration; `.githooks/post-merge` runs `brain index` + `gen_snippets.py` to close the stale window.
- **Install:** one `git config merge.regenerate.driver ...` line added to README step 5 and `onboard-harness`; unconfigured clones degrade to today's behavior.
- **Update:** `10_Agents/solutions/vault-tooling/index-merge-conflicts.md` becomes background + fallback.
- **Accept:** synthetic two-branch index conflict merges clean and post-merge hook refreshes.

### M8.7 — #20 Adopter-flow smoke test (M)
- **Build:** `10_Agents/tools/adopt_check.py` (stdlib): copy tree to scratch → delete the README's listed example files (list lives in **one data file** the README also renders, so they can't drift) → dumb-fill `01_Profile/` shells → write one conventions-conforming Inbox note → `brain index && brain validate` must be 0 errors → assert example list matched reality.
- **Wire:** CI job in `validate.yml`; runnable locally via M8.1's runner.
- **Accept:** deliberately adding a canonical wikilink to a seeded example turns CI red.

**M8 exit:** enforcement chain (frontmatter + secrets + adoption contract) fully mechanized; every tool under test.

---

## Phase M9 — Config & core conventions

Goal: land the #2 config (the backlog's most-depended-on decision) and the conventions-level features anchored to it. **M9.1 first**; M9.2–M9.5 can then proceed in parallel.

### M9.1 — #2 Vault config file (M) — DECISION GATE
- **Decide (recommendation posted on issue):** `00_Meta/config.yaml`; bounded YAML subset (scalars, flat lists, one nesting level); §6.3 change-controlled.
- **Spec:** new spec section: config location, grammar, unknown-key tolerance (forward compat), defaults when absent (current behavior — config is optional).
- **Code:** config reader in brain (candidate future `shared` seed — keep it a distinct module-internal section); implement `write_exceptions` (validate enforces Inbox-first destinations) and `extension_trust` (documented override consumed by editor docs); **reserve** `context`, `modules`, `sync`, `environments`, `report`, `provenance`, `template_version` as named-but-unimplemented.
- **Tests:** parse fixtures (valid, absent, unknown keys, malformed → per-file error not crash); write-exception enforcement cases.
- **Accept:** shipped template has a commented example config; absence changes nothing.

### M9.2 — #18 Provenance frontmatter (S)
- **Conventions:** register optional `author` (harness-level identifier: `claude-code`, `copilot`, …) and `session` (URL/PR/task ref) — required-for-agents, absent-for-humans.
- **Validate:** warn (not error) when `02_Inbox/` note has `audience/agent` + `workflow/draft` but no `author`; templates exempt (placeholders, §10.1).
- **Sweep:** operating-rules checklist +1 line; agent-facing skills that write notes (inbox-capture, research-to-resource, solution-capture, triage-inbox) mention the fields.
- **Tests:** warn fixture, exemption fixture.

### M9.3 — #17 restricted/* namespace (M)
- **Conventions:** register `restricted/private` (tag-only v1 — no directory rule, per issue recommendation), with the honest framing: advisory everywhere except Cursor.
- **Validate:** warn on non-restricted → restricted wikilink/embed (context bleed).
- **Index:** restricted notes keep path/title/tags, drop headings/excerpts (spec §8 amendment — prevents the committed index re-leaking).
- **Harness:** document `.cursorignore` generation from restricted-tagged paths in cursor wiring (generation itself can be a small script or an onboard-harness step).
- **Skills:** operating-rules gains "never quote/summarize restricted content into non-restricted notes"; triage-inbox + research-to-resource respect it.
- **Tests:** containment-warn fixture; index-reduction assertion.

### M9.4 — #12 Context-aware periodic templates (M)
- **Approach (recommendation posted):** option 2 — `onboard-owner` asks personal vs work and rewrites `09_Templates/` periodic templates in place; paths stay stable.
- **Build:** work-variant source content under `09_Templates/variants/` (excluded from resolve-by-name contract and snippet generation); onboard-owner SKILL.md gains the specialization step (mood/health sections removed for work, standup/blockers/decisions added); record answer as `context:` in config (M9.1).
- **Ripple:** snippet regeneration picks up specialized templates automatically (parity holds); note in #6's classify rules already exists (specialized templates = owner content).
- **Tests:** smoke assertion that variants stay out of snippet generation; M8.7's fill step remains green post-specialization scenarios.

### M9.5 — #16 brain report (M)
- **Spec:** new command section: five sections (stale-active 30d default, orphans excluding READMEs/templates/archives, Inbox aging, tag drift vs taxonomy, unresolved-link count), deterministic ordering, `--json`, `--since <date>`; thresholds read from config `report` key (defaults inline).
- **Code:** synthesis over the existing index — no new parsing.
- **Wire:** VS Code task "Brain: Health Report" (§6.5 parity); `periodic-review` + `vault-maintenance` SKILL.md embed the report as their opening step.
- **Tests:** fixture vault with known stale/orphan/aging/drift counts; determinism check.

**M9 exit:** config exists and is enforced; conventions cover provenance + privacy; reviews start from data.

---

## Phase M10 — Orientation & onboarding

Goal: the #13 inventory contract (second decision hub) and the onboarding surface built on it. **M10.1 first**; M10.2 depends on it; M10.3/M10.4 are independent of each other.

### M10.1 — #13 agent-orientation inventory contract (M)
- **SKILL.md restructure:** defined output contract — structured inventory note with required sections: (1) solution inventory per category (version control, email, chat, storage, calendar, other high-use) with access method ranked custom-tooling → first-party CLI → MCP/connector → **browser (add to ladder)** → none; "none identified" is a recorded outcome; (2) harness introspection (own harness + other CLIs detected, mapped to PRD §8.3 tiers); (3) ecosystem identification (agent products, productivity suite as prior).
- **Landing convention (deferral edge):** one inventory note per environment under `10_Agents/environments/<env>/`, never bootstrap-linked, self-guarding applicability preamble — the *minimal* slice of deferred #15, just enough that output isn't homeless.
- **Feeds:** `recommended-automations` and `self-maintenance` read the current env's inventory.
- **Tests:** mechanical contract checks only (required section headings present in SKILL.md template block — avoid prose-locks per the PR #33 lesson).

### M10.2 — #14 onboard-owner: people map + role/intent (M) — depends M10.1
- **SKILL.md additions:** (1) people map — infer candidates from observable sources per the #13 inventory, confirm with owner, write `03_Journal/people/` under the live-session exception; sensitivity rules verbatim (§16.2); (2) vault intent (work/personal → triggers M9.4 specialization; recorded in config `context`) and role/team/responsibilities → `01_Profile/work.md` / `identity.md`.
- **Escalation posture:** infer first, confirm everything before landing in Profile/people.
- **Accept:** dry-run interview transcript exercise produces conforming notes.

### M10.3 — #3 Per-harness overlays (L)
- **Shape:** `10_Agents/harnesses/<harness>/overlay/` — harness-native primitives (Cursor `.mdc` rules, Claude Code hooks/settings, Copilot agent hooks) + per-overlay manifest; `onboard-harness` installs/uninstalls them with the same provider/consumer, marker-managed, reversible contract PR #33 established (extend that manifest model, don't invent a second one).
- **Migrate proto-overlays:** existing Copilot config + Cursor examples become the first real overlays.
- **Guard:** standards-first rule (§8.3) — overlays carry only what a cross-harness standard can't express.
- **Tests:** manifest-shape checks; path-leak regexes extended to overlay files.

### M10.4 — #7 Recommended skills & user memory content (S)
- **Build (recommendation posted):** `06_Resources/recommended-skills.md` — links-only with pinned refs, per-item license + trust note; i-have-adhd and karpathy MDs seeded. `10_Agents/skills/README.md` links to it.
- **Install path:** `onboard-harness` optional step — fetch pinned ref to user scope, per-item owner sign-off, manifest-recorded; user-scope `CLAUDE.md` curated blocks extend the existing marker-managed import surface.

**M10 exit:** orientation and onboarding produce defined, homed artifacts; harness-specific power is systematized.

---

## Phase M11 — Search & tasks

Independent of each other; both need M9 (config for defaults, conventions registration).

### M11.1 — #8 QMD semantic search (L) — DECISION GATE
- **Decide (recommendation posted):** embedding-source interface accepting all three backends — (a) optional local model, (b) harness-side precomputed vectors via `brain embed --stdin-json`, (c) external API; degrade to keyword search when none available.
- **Spec first:** sidecar store schema (per-note/section vectors keyed by path + content hash), similarity semantics, hybrid ranking, staleness rules (incremental re-embed on hash change). Sidecar **gitignored** (model/environment-specific — unlike the committed index).
- **Code:** `brain search --semantic "<query>"` (+ `--json`); cosine similarity stdlib; store read/write; `brain embed` ingestion interface.
- **Harness delivery:** wiring docs document invocation per harness (CLI is the universal layer); where a harness can supply embeddings, its doc shows the `brain embed` pipe.
- **Tests:** store round-trip, hash-staleness, ranking determinism with fixture vectors, graceful degradation.
- **Breakdown duty:** first implementation session splits this into sub-issues (store, embed interface, query, harness docs).

### M11.2 — #28 Task module (L) — DECISION GATE
- **Decide (recommendation posted):** Obsidian Tasks emoji grammar as canonical inline metadata.
- **Conventions:** checkbox base syntax + emoji table + location rule (tasks live where context lives) registered in `00_Meta/conventions.md`.
- **Spec + code:** index checkbox tasks per note (status, due, priority, source line — spec §8 extension); `brain tasks --open|--due|--overdue|--project|--json`.
- **Surfacing (in-scope slice only):** `daily_note.py` pulls yesterday's unchecked tasks into Backlog (config toggle, default on); weekly-review template embeds open/overdue counts via #16's report. VS Code/web-UI views and notification digests are deferred edges (#27/#21).
- **Tests:** parse fixtures (all metadata forms, malformed), query filters, carry-over behavior incl. ISO-week boundary.

**M11 exit:** the vault answers questions and tracks work natively in every harness.

---

## Phase M12 — Sync & self-improvement

M12.1 before M12.2 (the loop proposes through sync's classify rules).

### M12.1 — #6 Upstream sync skill (L) — DECISION GATE
- **Decide (recommendation posted):** `template_version` in config + upstream release git tags; `00_Meta/VERSION` stopgap acceptable if sequenced before M9.1. Upstream tagging becomes a documented release duty.
- **SKILL.md:** detect (fork vs upstream tags) → classify (machinery / owner content / canonical docs — table drafted in the issue comment, including the #12/#22 owner-content rules) → apply (machinery direct, canonical via PR, owner content never) → backfill (mechanical fixes + validate proof) → report to Inbox; idempotent, dry-run first.
- **Tests:** classify-table coverage against a fixture file list (mechanical); backfill validate-proof convention.

### M12.2 — #22 Self-improving loop (L) — depends #16, #6
- **SKILL.md:** observe (report trends, git history, triage outcomes) → propose (single-topic PRs/Inbox proposals with evidence + rollback, provenance fields per M9.2) → owner review → record rejections (`10_Agents/docs/rejected-proposals.md` log so the loop never re-proposes) → recur (monthly spec-retrospective cadence via recommended-automations).
- **Guardrails in skill text:** proposal rate limit (max N open), canonical-docs-by-PR-only (change control is the safety mechanism), owner content out of bounds except as evidence, **never push upstream** (also lands in operating-rules.md).
- **Accept:** one full dry-run cycle produces a well-formed proposal from seeded friction fixtures.

**M12 exit:** the fork tracks upstream and improves itself under change control — the template's full loop is closed.

---

## Sequencing summary

```
M8.1 → {M8.2, M8.3, M8.4, M8.5, M8.6, M8.7}          (runner first, rest parallel)
M9.1 → {M9.2, M9.3, M9.4, M9.5}                       (config first, rest parallel)
M10.1 → M10.2 ; {M10.3, M10.4} independent
M11.1 ∥ M11.2                                          (both need M9)
M12.1 → M12.2                                          (both need M9; M12.2 needs M9.5/#16)
```

**Owner decision gates** (recommendations already posted on the issues — approving the comment unblocks): #2 location/grammar (gates M9), #12 option 2, #17 index handling, #8 embedding source (gates M11.1), #28 syntax (gates M11.2), #6 version marker (gates M12), #7 sign-off policy.
**Owner actions:** create the six GitHub milestones; enable secret scanning + push protection (M8.5); approve/adjust the gate recommendations.

**Effort totals** (S = single focused session, M = 1–2 sessions, L = multi-session): M8 = 4S + 3M · M9 = 1S + 4M · M10 = 1S + 2M + 1L · M11 = 2L · M12 = 2L. Every L item (M10.3, M11.1, M11.2, M12.1, M12.2) begins with its own breakdown step that splits it into sub-issues before code.

---

*Agent-generated (feature-request triage session). Inbox-first: pairs with [[02_Inbox/2026-08-11-feature-request-triage|the triage note]]; both promote together on review.*
