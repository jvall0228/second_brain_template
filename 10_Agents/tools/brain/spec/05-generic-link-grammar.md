---
title: "brain Spec §5 — Generic link grammar"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 5. Generic link grammar

*Section 5 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 5.1 Recognized forms and records

The schema-v2 extractor reads the maintained format plus one import-only legacy format into one record shape:

- **Standard inline Markdown:** `[label](destination)`, `![alt](destination)`, angle-bracket destinations, balanced parentheses, escaped delimiters, one optional fully quoted/parenthesized ignored title, URL-encoded paths/fragments, and fragment-only self-links. Arbitrary text after a destination is invalid rather than silently discarded. Reference-style and multiline links are intentionally not recognized.
- **Legacy import format:** `[[target]]`, `[[target|label]]`, `[[target#fragment]]`, `[[target#fragment|label]]`, and the `!` embed forms. The first `|` (or table-safe `\|`) separates the label; the first `#` separates the fragment; one final `.md` is stripped only from the compatibility `target` field. Odd backslash parity escapes either link syntax; even parity does not.

Each record always carries `raw`, `range`, `line`, `label`, `destination`, `fragment`, `format` (`markdown|wikilink`), `embed`, `placeholder`, and `resolution`. `range.start.offset`/`range.end.offset` are a half-open range in **normalized UTF-8 bytes**; endpoints also carry 1-based line and 0-based character column. `resolution` is `{status, path, fragment, warnings}`. `display`, `target`, `resolved`, and top-level `warnings` remain schema-v1 compatibility aliases for consumers. `format: wikilink` is the authoritative import-debt count; the index also exposes aggregate `linkCounts`. A maintained repository has zero such records.

A destination or fragment containing `{{` is a placeholder: indexed with `status: placeholder`, counted, and exempt from normal resolution/validation. A fragment beginning `^` is an unsupported block reference: its path may resolve for backlink structure, but the record status/warning is explicit and migration refuses it. Raw/bare URLs and Markdown destinations with a URI scheme or `//` are external and excluded. A leading `/` Markdown destination is recorded as unsupported rather than treated as repository-relative; portable vault links are source-relative.

## 5.2 Exclusion zones

Links (and inline tags, §7.2) are **not** extracted from:

- the frontmatter block;
- **fenced code blocks** — a fence opens on a line whose first non-space characters are three or more backticks or tildes (info string allowed) and closes on a line of at least as many of the same character and nothing else but whitespace; an unclosed fence runs to end of file;
- **inline code spans**, matched **within a single line**: a run of N backticks opens a span closed by the next run of exactly N backticks on the same line; runs left unmatched at end of line are literal text and exclude nothing. (Multi-line CommonMark spans are deliberately not supported — the line-scoped rule is deterministic, keeps line numbers exact, and prevents one stray backtick from swallowing the rest of the document. §11.)

This removes the known false-positive source from the M4 link check. Indented (4-space) code blocks, HTML comments, and Obsidian `%%` comments are **not** excluded in v1 (§11).
