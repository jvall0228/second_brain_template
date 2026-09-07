---
name: daily-log
description: Create or update today's daily journal log from the vault template. Use when asked to start the day, log something to today, or append to the daily note — invocation itself directs the write to 03_Journal/periodic/daily/.
title: "Skill: Daily Log"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# Daily Log

**CODE stage:** Capture.

Maintain `03_Journal/periodic/daily/YYYY-MM-DD.md` for today (owner's timezone — check `01_Profile/DEFAULTS.md`).

**Historical dates (backfill).** This skill writes today's note. An entry for an earlier event date — a triaged capture, a dated record filed late — goes through `brain trace --date YYYY-MM-DD --destination <note> --summary "..." --id <capture identity> --write` (spec §29.2), which instantiates that date's daily note from the same template when it is missing (the previous-day link only when that note exists), appends one line under `### Activity Log`, mirrors it into the ISO-week weekly note, and dedupes on the capture identity so a rerun adds nothing. Never hand-create a past daily note.

## Steps

1. **Check for today's file.** If it exists, append to it rather than recreating; bump `updated:` if the date rolled over an edit.
2. **If missing, instantiate** `09_Templates/template-daily-log.md` for the vault-local date: replace every `{{...}}` placeholder, set `title`, `updated`, and real tags (keep the template's suggested set including `workflow/draft`). Omit unfilled context and goal scaffold lines; never turn them into open tasks. Link yesterday's sibling filename and `../weekly/YYYY-W##-review.md` only when those notes exist; otherwise use plain text. Follow the shared creator's configured carry-over behavior: `ensure_note` in [daily_note.py](../../tools/vscode/daily_note.py) applies these rules without opening an editor, admits yesterday's tasks from a classified snapshot, and records the source dependency.
3. **Add the content** under the appropriate section (log entries, tasks, notes). Search for established people, pets, Projects, Areas, and other recurring entities; link the first meaningful mention to the existing note, entrypoint, or anchor and do not create duplicates. A bare link to a `restricted/private` entity keeps the log non-restricted; copying or summarizing private substance makes the whole day's log `restricted/private` — apply the tag, say so, and prefer the link. Private logs remain eligible for the complete internal Home and AYMT views; public-only outputs and daily task carry-over exclude private or unknown sources ([CONVENTIONS](../../../00_Meta/CONVENTIONS.md#restrictedprivate)). Keep entries terse and timestamped where useful.
4. **Validate and commit:** `brain validate`, then commit.

## Rules

- Being asked for a daily log **is** the explicit direction required to write outside the Inbox; anything that isn't daily-log content still goes through `inbox-capture`.
- Today only by hand; any other date only through `brain trace` (above).
- Same-directory links use sibling destinations such as `[2026-08-10](2026-08-10.md)`; cross-directory links remain source-relative, such as `[weekly review](../weekly/2026-W33-review.md)`.

## References

- `09_Templates/template-daily-log.md` — the template
- `03_Journal/README.md` — periodic note naming
- `01_Profile/DEFAULTS.md` — timezone and date format
- `00_Meta/CONVENTIONS.md` — established entity-link contract
