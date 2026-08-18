---
name: periodic-review
description: Run a weekly, monthly, quarterly, or yearly review from the matching vault template, pre-filled from what actually happened. Use when asked for any cadence of review; the cadence is a parameter, not a separate skill.
title: "Skill: Periodic Review"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-18
expires: 2027-08-11
---

# Periodic Review

**CODE stage:** Organize — the weekly review is the vault's Organize heartbeat; longer cadences add reflection and goal alignment.

Produce the review note for a period in `03_Journal/periodic/<cadence>/`, grounded in the period's real activity.

## Cadence map

| Cadence | Template | Destination filename |
|---------|----------|----------------------|
| weekly | `09_Templates/template-weekly-review.md` | `YYYY-W##-review.md` |
| monthly | `09_Templates/template-monthly-review.md` | `YYYY-MM-review.md` |
| quarterly | `09_Templates/template-quarterly-review.md` | `YYYY-Q#-review.md` |
| yearly | `09_Templates/template-yearly-review.md` | `YYYY-review.md` |

## Steps

1. **Open with the health report:** `brain report --since <period start>` — the review starts from "here's what needs attention" (stale-active notes, orphans, Inbox triage debt, tag drift, unresolved links), not a blank page. `--since` scopes tag drift and unresolved links to the period's changes; the debt sections always cover the whole vault. Carry the findings into the review's sections below.
2. **Gather the period's activity** before writing:
   - `brain projects --json` — the canonical active Project inventory, all Area mappings, target state, criteria presence, overdue state, and contract findings
   - `brain list --dir 04_Projects --tag status/deprioritized --json`, then repeat with `status/someday` and `status/done` — established inactive and archive-pending Project entrypoints that the active inventory intentionally excludes
   - `brain recent 25 --json` — what changed
   - `git log --since=<period start> --oneline` — file-level history
   - The period's daily logs (weekly) or the child-cadence reviews (monthly reads weeklies, quarterly reads monthlies, yearly reads quarterlies)
   - `01_Profile/NOW.md` — current focus to review against
3. **Instantiate the template**: replace all `{{...}}` placeholders, set real frontmatter (`updated:` today, keep `workflow/draft`), and replace each link token with a complete source-relative destination including `.md` (sibling reviews use their filename; cross-directory links use `../` segments).
4. **Fill every section from evidence**, not memory: wins and misses against the stated focus, what changed in projects/areas, what to carry forward. Leave explicitly-marked open questions for the human rather than inventing answers.
5. **Project and Area review:** treat `brain projects` plus the lifecycle-filtered `brain list` results as authoritative and [NOW](../../../01_Profile/NOW.md) as a curated priority view. Review every active Project's Areas, completion criteria, next action, and target; explicitly confirm or recalibrate estimated and overdue dates. Open each inactive entrypoint and review deprioritized Projects for reactivation, continued pause, or closeout; distinguish someday ideas from established-but-deprioritized work, and process done Projects as archive-pending. Surface NOW mismatches rather than treating its prose as a second registry.
6. **Closeout and archive are separate:** when a Project is completed, cancelled, or superseded, propose the immediate closeout: leave exactly `status/done`, remove active target fields, set `closed: YYYY-MM-DD`, write `## Final Outcome`, and run `brain projects --write-rollups`. A done Project under `04_Projects/` is valid archive-pending. Moving it requires separate owner approval: preview `brain archive-project <slug>`, then use `--write --approve-archive` only after that approval. Never use a generic note move. Areas no longer maintained get their own explicit archive proposal.
7. **Quarterly only — refresh the Now page:** with the owner, rewrite [NOW](../../../01_Profile/NOW.md) to match current reality (their in-review answers are the approval). A quarterly review that leaves a stale Now page isn't finished.
8. **Validate and commit:** `brain validate`, require zero Project/Area membership or lifecycle warnings introduced by the review, then commit. Invocation directs the write to `03_Journal/periodic/<cadence>/`.

## References

- `09_Templates/README.md` — template selection guide
- `03_Journal/README.md` — periodic naming conventions
- [Project and Area Contract](../../docs/project-area-contract.md) — lifecycle, target, rollup, and closeout rules
