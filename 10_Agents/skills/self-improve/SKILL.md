---
name: self-improve
description: Run the vault's self-improving loop - observe friction in real usage (brain report trends, git history, triage outcomes, solution notes), propose single-topic spec/convention/skill changes as PRs or Inbox proposal notes with evidence and rollback, record owner rejections so they are never re-proposed, and recur as the monthly spec retrospective. Use when asked to run a spec retrospective or to propose improvements from observed usage. Propose-only - the owner decides; never push upstream.
title: "Skill: Self-Improve"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Self-Improve

**CODE stage:** System (outside the loop) — evolves the loop's own spec toward the owner.

Make the fork **self-improving** (issue #22): agents observe how the owner actually works and propose spec/convention/skill/template changes that personalize the fork — instead of the spec only changing when the owner thinks to ask. The loop is observe → propose → owner review → record → recur. Every cycle produces *proposals*, never applied changes: change control is the safety mechanism, so drift without review is impossible by construction.

## Ground rules (guardrails)

- **Propose-only.** The loop never edits canonical content directly and never merges its own proposals. Canonical-doc changes ([[00_Meta/prd]] §6.3 — `workflow/canonical` notes, `00_Meta/`, `10_Agents/docs/`) go **by PR only**, with one carved exception: `10_Agents/docs/rejected-proposals.md` is an **append-only agent log** (`type/log`, non-canonical) that the loop appends to directly — the standing exception is granted in [[AGENTS]] / [[00_Meta/conventions]] § Agent Write Rules and enforced in brain's write gate. Everything else goes as an `02_Inbox/` proposal note tagged `workflow/needs-review`. The owner's merge/close (or triage accept/reject) **is** the decision.
- **Rate limit: max 3 proposals open at once** (open PRs + untriaged Inbox proposal notes from this loop, counted together). Issue #22 requires a rate limit ("max N open at once") without fixing N; this skill sets N = 3 so the owner is never spammed into rubber-stamping. At the limit, hold further proposals for the next cycle — rank and keep the best three.
- **Owner content is out of bounds** except as read-only evidence. The loop maintains the fork's *spec* (conventions, skills, templates, agent docs, tooling); journal/profile/PARA notes are never proposal targets — they are only observed.
- **Never push upstream.** The fork pulls from the public upstream template ([[10_Agents/skills/sync-upstream/SKILL|sync-upstream]] is pull-only); this loop personalizes the fork in the opposite direction and inherits the same hard rule: agents never push, open PRs, or write in any form to the upstream public repo unless operating as its owner. A fork improvement worth generalizing is flagged to the owner as "worth upstreaming?" — the owner carries it upstream by hand if they choose. (Also stated in [[10_Agents/docs/operating-rules]].)
- **Consult the rejection log first.** Before proposing anything, read [[10_Agents/docs/rejected-proposals]] — a rejected idea is never re-proposed. Re-raising requires **materially new evidence**, and the proposal must state explicitly what changed since the rejection.
- **Single-topic proposals.** One observed friction → one proposal (the atomic-notes rule applies to spec changes too). A cycle that finds five frictions produces up to the rate limit of separate proposals, not one omnibus.

## Observe

Gather evidence of friction from real usage — the loop proposes only what the vault's own history supports:

1. **`brain report` trends:** run `brain report` (spec §16) and compare against the previous cycle's report if one is archived (prior spec-retrospective notes in `02_Inbox/` or `07_Archives/`; or re-run with `--since <last cycle>` to scope tag drift and unresolved links to the period). Rising Inbox aging, recurring tag drift (unknown/single-use/near-duplicate tags), or persistent stale-active notes are convention-change candidates.
2. **Git history:** `git log --stat` since the last cycle. Look for churn — the same file fixed repeatedly (candidate structural fix), recurring fix patterns across commits (candidate validate rule or convention), repeated manual edits that a template or skill step should absorb.
3. **Triage outcomes:** what the owner rejects, rewrites, or re-files during Inbox triage. A capture pattern the owner always renames, a frontmatter shape they always correct, a section they always delete — each is a candidate change to the capture skill or template that produced it.
4. **Friction notes:** `10_Agents/solutions/` — solution notes record problems agents already hit; recurring ones point at the spec gap that caused them. Also: templates whose sections stay empty or always get renamed (issue #12 targets), tags invented ad hoc (taxonomy candidates), skills whose steps get overridden every run, preferences stated in conversation but recorded nowhere.

Evidence is collected read-only. Owner content read here is quoted into proposals only as far as the restricted-containment rule allows (never quote `restricted/*` content — link it).

## Propose

For each observed friction (best three first, per the rate limit), after checking [[10_Agents/docs/rejected-proposals]]:

- **Canonical docs** (`workflow/canonical` notes, `00_Meta/`, `10_Agents/docs/`, template-shipped skills): open a **PR** on a proposal branch containing the change. Change control is the safety mechanism — the PR *is* the proposal.
- **Everything else** (new draft skills, template tweaks pending §6.3 review, taxonomy suggestions, automation ideas): write an **Inbox proposal note** per the `inbox-capture` rules — `02_Inbox/YYYY-MM-DD-proposal-<slug>.md`, tagged `workflow/needs-review`.

Every proposal — PR description or Inbox note — must state:

1. **Evidence:** the observed friction, cited concretely (report lines, commit hashes, note paths, triage events).
2. **The change:** exactly what would be edited, single-topic.
3. **Expected effect:** what improves, and how the next cycle would verify it.
4. **Rollback plan:** how to undo (usually `git revert <merge>`; for conventions, the note also names what downstream content would need re-checking).
5. **Provenance:** `author:` (harness identifier) + `session:` (session URL / PR / task ref) per [[00_Meta/conventions]] § Provenance — on the Inbox note's frontmatter, and in the PR description for PR-lane proposals.

## Owner review

Proposals are **never self-merged** and never applied by the loop in any form. The owner's action is the decision:

- **PR merged / Inbox proposal accepted at triage** → the change is in; the next cycle's Observe step verifies the expected effect.
- **PR closed unmerged / proposal rejected at triage** → record it (next section) and drop the idea.
- **No action** → the proposal stays open and counts against the rate limit; a proposal lingering more than two cycles is mentioned (once) in the next retrospective report, then left alone — nagging is spam.

## Record rejections

Rejections are memory, not failure. Append every rejected proposal to [[10_Agents/docs/rejected-proposals]] — one table row: date, proposal (with a link to the PR or note), the evidence it cited, and why it was rejected **if the owner stated a reason** (never invent one; leave the cell as `—` otherwise). The log is **append-only**: rows are never edited or removed, so the loop's memory of "we tried that" survives every session.

The loop consults this log **first**, before proposing (ground rules above). A rejected item may be re-raised only with materially new evidence, and the new proposal must say so explicitly: "previously rejected on `<date>` (see rejected-proposals); re-raising because `<what is new>`."

## Recur

The loop runs as a **monthly spec retrospective**, registered in the cadence table ([[10_Agents/skills/README]] § The Rhythm) alongside the monthly review and maintenance pass, and wireable as a scheduled rhythm job via [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]]. Under the unattended contract, a scheduled run carries the loop through Observe and drafts proposals — Inbox notes directly; PR-lane proposals as a prepared branch + Inbox summary — and its deliverable is the retrospective report; the owner review step always waits for a human.

Each cycle ends with a short retrospective report in `02_Inbox/` (`YYYY-MM-DD-spec-retrospective.md`, `inbox-capture` rules, provenance fields): evidence reviewed, proposals opened (with links), proposals held back by the rate limit, verification of the previous cycle's merged changes, and any "worth upstreaming?" flags for the owner.

## Worked example (dry-run cycle)

A seeded friction, walked observe → propose:

**Observe.** This cycle's `brain report` shows tag drift: `topic/sw` (3 uses) and `topic/software` (14 uses) as a near-duplicate pair. The previous cycle's report showed the same pair at 1 vs 12 — the drift is recurring, not a one-off typo. `git log` shows two triage commits that manually retagged `topic/sw` → `topic/software`, so the owner has already voted twice. [[10_Agents/docs/rejected-proposals]] has no row for this idea.

**Propose.** The fix is a convention nudge, not a canonical-doc edit (the `topic/*` namespace is free-form, so no taxonomy table changes) — Inbox lane. One single-topic proposal note, written to `02_Inbox/2026-08-11-proposal-topic-sw-alias.md`:

```markdown
---
title: "Proposal: retag topic/sw to topic/software"
tags:
  - audience/agent
  - audience/human
  - type/note
  - workflow/needs-review
  - topic/software
updated: 2026-08-11
author: claude-code
session: https://claude.ai/code/session_0194H8b6W4qpn7DQVKEc7y73
---

# Proposal: retag topic/sw to topic/software

**Evidence:** `brain report` (2026-08-11) flags `topic/sw` / `topic/software` as a
near-duplicate pair (3 vs 14 uses); last cycle showed the same pair growing (1 vs 12).
Two triage commits already retagged `sw` → `software` by hand.

**Change:** retag the 3 remaining `topic/sw` notes to `topic/software` (list attached
below), and add `sw → software` to the capture guidance in the inbox-capture skill's
tag-picking step so new captures stop reintroducing it.

**Expected effect:** next cycle's report shows zero `topic/sw` uses and no new
near-duplicate pair; triage stops spending edits on retagging.

**Rollback:** `git revert` the retag commit; remove the alias line from inbox-capture.

**Notes affected:** `02_Inbox/2026-08-03-sw-estimation-links.md`, …
```

**Owner review.** The note waits in the Inbox; triage accepts (retag proceeds as a normal non-canonical edit) or rejects (a row is appended to [[10_Agents/docs/rejected-proposals]] and the pair is never proposed again without new evidence). The loop itself touches nothing.

The example proposal conforms: frontmatter carries `title`, `tags`, `updated`; every tag is namespaced and each namespaced value is in the conventions taxonomy (`topic/*` is free-form); provenance `author:` is a harness identifier and `session:` a session URL per § Provenance; the filename follows the Inbox `YYYY-MM-DD-slug.md` convention; the body states evidence, change, expected effect, and rollback.

## Steps

1. Read [[10_Agents/docs/rejected-proposals]] — load the do-not-repropose list.
2. Observe (above): `brain report` vs previous cycle, git history, triage outcomes, `10_Agents/solutions/`.
3. Count proposals already open from this loop (PRs + untriaged Inbox proposal notes); available slots = 3 minus that.
4. For each friction, best-ranked first, up to the available slots: propose via the right lane (canonical → PR; else Inbox note), with evidence, expected effect, rollback, provenance.
5. Verify the previous cycle's merged changes had their expected effect; note the outcome in the retrospective report.
6. Append any newly-rejected proposals to [[10_Agents/docs/rejected-proposals]].
7. Write the retrospective report to `02_Inbox/`; the owner takes it from there.

## References

- Issue #22 — the loop's design: observe/propose/review/recur, rate limit, upstream boundary
- [[00_Meta/prd]] §6.3 — change control the propose lanes implement
- [[10_Agents/docs/rejected-proposals]] — the loop's rejection memory
- [[10_Agents/docs/operating-rules]] — never-push-upstream rule, canonical note handling
- [[10_Agents/skills/sync-upstream/SKILL|sync-upstream]] — the pull direction this loop coexists with (issue #6)
- `10_Agents/tools/brain/spec.md` §16 — `brain report`, the Observe step's primary instrument (issue #16)
- `10_Agents/skills/inbox-capture/SKILL.md` — write rules for proposal notes and the retrospective report
- [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] — scheduling the monthly retrospective
