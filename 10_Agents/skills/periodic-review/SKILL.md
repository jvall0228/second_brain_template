---
name: periodic-review
description: Run a weekly, monthly, quarterly, or yearly review from the matching vault template, pre-filled from what actually happened. Use when asked for any cadence of review; the cadence is a parameter, not a separate skill.
title: "Skill: Periodic Review"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Periodic Review

Produce the review note for a period in `03_Journal/periodic/<cadence>/`, grounded in the period's real activity.

## Cadence map

| Cadence | Template | Destination filename |
|---------|----------|----------------------|
| weekly | `09_Templates/template-weekly-review.md` | `YYYY-W##-review.md` |
| monthly | `09_Templates/template-monthly-review.md` | `YYYY-MM-review.md` |
| quarterly | `09_Templates/template-quarterly-review.md` | `YYYY-Q#-review.md` |
| yearly | `09_Templates/template-yearly-review.md` | `YYYY-review.md` |

## Steps

1. **Gather the period's activity** before writing:
   - `python3 10_Agents/tools/brain/brain.py recent 25 --json` — what changed
   - `git log --since=<period start> --oneline` — file-level history
   - The period's daily logs (weekly) or the child-cadence reviews (monthly reads weeklies, quarterly reads monthlies, yearly reads quarterlies)
   - `01_Profile/now.md` — current focus to review against
2. **Instantiate the template**: replace all `{{...}}` placeholders, set real frontmatter (`updated:` today, keep `workflow/draft`), link the period's source notes (full paths across directories; sibling reviews by bare filename).
3. **Fill every section from evidence**, not memory: wins and misses against the stated focus, what changed in projects/areas, what to carry forward. Leave explicitly-marked open questions for the human rather than inventing answers.
4. **Validate and commit:** `python3 10_Agents/tools/brain/brain.py validate`, then commit. Invocation directs the write to `03_Journal/periodic/<cadence>/`.

## References

- `09_Templates/README.md` — template selection guide
- `03_Journal/README.md` — periodic naming conventions
