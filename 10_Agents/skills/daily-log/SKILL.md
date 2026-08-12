---
name: daily-log
description: Create or update today's daily journal log from the vault template. Use when asked to start the day, log something to today, or append to the daily note — invocation itself directs the write to 03_Journal/periodic/daily/.
title: "Skill: Daily Log"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Daily Log

**CODE stage:** Capture.

Maintain `03_Journal/periodic/daily/YYYY-MM-DD.md` for today (owner's timezone — check `01_Profile/DEFAULTS.md`).

## Steps

1. **Check for today's file.** If it exists, append to it rather than recreating; bump `updated:` if the date rolled over an edit.
2. **If missing, instantiate** `09_Templates/template-daily-log.md`: replace every `{{...}}` placeholder, set `title`, `updated`, and real tags (keep the template's suggested set including `workflow/draft`), and fill each link-destination token with a source-relative path including `.md` — yesterday's sibling filename and `../weekly/YYYY-W##-review.md` for the current weekly review.
3. **Add the content** under the appropriate section (log entries, tasks, notes). Keep entries terse and timestamped where useful.
4. **Validate and commit:** `brain validate`, then commit.

## Rules

- Being asked for a daily log **is** the explicit direction required to write outside the Inbox; anything that isn't daily-log content still goes through `inbox-capture`.
- Same-directory links use sibling destinations such as `[2026-08-10](2026-08-10.md)`; cross-directory links remain source-relative, such as `[weekly review](../weekly/2026-W33-review.md)`.

## References

- `09_Templates/template-daily-log.md` — the template
- `03_Journal/README.md` — periodic note naming
- `01_Profile/DEFAULTS.md` — timezone and date format
