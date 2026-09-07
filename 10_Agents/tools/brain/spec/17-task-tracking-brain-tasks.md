---
title: "brain Spec §17 — Task tracking (`brain tasks`) — issue #28"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# 17. Task tracking (`brain tasks`) — issue #28

*Section 17 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

Markdown-native checkbox tasks, adopted 2026-08-11 per the accepted triage recommendation on issue #28: **Obsidian Tasks emoji grammar is the canonical inline metadata**, so Obsidian users get the native plugin experience with zero vault changes while `brain` answers the same queries on every other surface. The conventions entry ([CONVENTIONS](../../../../00_Meta/CONVENTIONS.md) § Tasks) carries the human-facing emoji ↔ meaning table and the location rule: tasks live where their context lives (any note); there is no central task file.

## 17.1 Recognition

A task is a list-item checkbox line in the note body: optional leading whitespace (nested subtasks index like any other), a bullet (`-`, `*`, or `+`), one space, `[c]` where `c` is exactly one character, one space, then non-empty text. `c` = space → `status: "open"`; any other character (`x`, `X`, Obsidian custom statuses like `-` or `/`) → `status: "done"`. A bracket pair with no text after it is not a task. The §5.2 exclusion zones apply: detection runs on the **masked** line, so checkboxes inside fenced code blocks or inline code spans never index; the task text is then taken from the **raw** line at the matched offset (masking preserves length), so inline code *within* a real task's text survives verbatim. Blockquoted checkboxes (`> - [ ]`) and ordered-list checkboxes (`1. [ ]`) are not recognized (out of grammar, mirroring Obsidian Tasks' default).

Extraction happens in the same `extract_body` line walk as links, headings, and body tags — **no additional parsing pass** — and each note record carries the results as the `tasks` array (document order). The field addition is purely additive to §8.1 (every field still always present), so `schemaVersion` stays 1.

## 17.2 Task record and emoji metadata

Each task record: `{due, line, malformed, priority, status, text}` — every field always present.

- `line` — 1-based source line (§3). `status` — `"open"` | `"done"` (§17.1).
- **Emoji tokens** are parsed out of the checkbox text and stripped from `text` (whitespace then collapsed to single spaces). Date-bearing emoji — 📅 due, ⏳ scheduled, 🛫 start, ✅ done, ➕ created — take an optionally-space-separated `YYYY-MM-DD` token (ASCII digits only — non-ASCII digit forms are not date-shaped); ⏫/🔼/🔽 set `priority` `high`/`medium`/`low`; 🔁 takes free text running to the next recognized emoji or end of line. A trailing emoji variation selector (U+FE0F) is tolerated. For a repeated field the **last** occurrence wins (mirroring §4.2's duplicate-key posture).
- **Indexed fields:** only `due` (`"YYYY-MM-DD"` or `null`) and `priority` (`"high"` | `"medium"` | `"low"` | `null`) — the queryable subset. Scheduled/start/done/created dates and recurrence rules are recognized and stripped from `text` but not stored (future consumers re-read the source line, which `line` pins).
- **Malformed metadata:** a date-bearing emoji whose value is date-*shaped* but not a real calendar date has the token consumed; a missing or non-date-shaped value leaves the text in place. Either way the task **still indexes** with the affected field at its null/default and the field's name appended to `malformed` (sorted, de-duplicated) — and `validate` surfaces each entry as the `task-invalid-date` **warning** (§10.2). Parsing is best-effort, never fatal (§4's posture); 🔁 takes free text and can never be malformed.

Restricted notes (§8.3): `tasks` is emptied to `[]` in the committed index — task text and metadata are body prose.

## 17.3 `tasks` command

`brain tasks` (§9 conventions: in-memory index, `--json`, exit 0; `1` for a malformed `--due` value) lists every task in the working corpus. Filters, ANDed:

- `--open` — `status == "open"` only.
- `--due <YYYY-MM-DD|today>` — tasks **with** a due date on or **before** the given date (`today` resolves to the current date); a task with no due date never matches.
- `--overdue` — open tasks whose due date is **strictly before** today (due today is not overdue).
- `--project PREFIX` — note-path prefix match (e.g. `04_Projects/example-project/`).

**Ordering (deterministic):** due date ascending with `null` due dates last, then path (code-point order), then line. JSON: an array of task records each extended with `path` and the §9 provenance fields `restricted`, `privacy`, and `explicitRestricted` (effective private/unknown admission flag, classification enum, and explicit tag respectively). Human output: `path:line  [ ]|[x] text` plus a parenthesized suffix listing due date, priority, and malformed fields when present; rows from restricted notes get a trailing `  [restricted]` marker. The VS Code surface runs `tasks --open` via the "Brain: Tasks (open)" task (§6.5 parity).

## 17.4 Config: `tasks.carry_over`

The `tasks` config key (§15.3) holds the module's settings; its sole subkey `carry_over` (`on` | `off`, default **on**) gates §17.5's daily-note carry-over. `tasks_carry_over(config)` is the reader (malformed → default; `check_config` reports per §15.4), and `brain config` prints the effective value. Per §15.1 the config never influences `index` output.

## 17.5 Surfacing: daily-note carry-over

`daily_note.py` (the VS Code daily-note task), when **creating** today's note and the §17.4 toggle is on, copies **yesterday's unchecked task lines** — open checkboxes per §17.1, including nested ones, indentation preserved, fenced-code/inline-code exclusions applied via the shared `brain` parser — verbatim into the end of the new note's `### Backlog` section (before the section's trailing blank lines; if the instantiated template has no such heading, the section is appended). "Yesterday" is calendar yesterday (`today − 1 day`), so month, ISO-week, and year boundaries need no special casing; a missing, unreadable, or task-free yesterday note simply carries nothing, and a private or unknown derivative carries nothing either. Admission and carried text come from one `read_note_context(..., public_only=True)` snapshot; a new note with carried tasks merges yesterday into `privacy-sources`, retaining existing dependencies and refusing malformed provenance. The actual shipped template is instantiated through the periodic renderer; absent CONTEXT/GOAL rows are dropped rather than becoming tasks. The editor entrypoint uses the configured vault-local date. Existing notes are never rewritten — carry-over runs only at instantiation. The weekly-review template instead carries a prompt line pointing at `brain tasks --open` / `--overdue` (live query beats a stale snapshot at week granularity).

**Deferred surfacing (explicitly out of scope here):** VS Code task *views* and web-UI views (#27), notification/overdue digests (#21), external-tracker mirroring (#26 directionality).
