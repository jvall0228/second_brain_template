---
title: "brain Spec §7 — Body extraction"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 7. Body extraction

*Section 7 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 7.1 Headings

ATX headings only: 1–6 `#` characters at the start of a line (up to 3 leading spaces allowed), followed by a space and text; trailing closing-`#` sequences are stripped. Recorded in document order as `{level, line, slug, text}` (`line` per §3; `slug` per §6.4). Setext headings are not recognized (§11). Exclusion zones (§5.2) apply.

## 7.2 Inline tags

A body tag is `#` immediately followed by one or more of `[A-Za-z0-9_/-]`, containing **at least one non-digit** character, and preceded by start-of-line or whitespace (so URLs like `…/page#anchor` never match; `# Heading` fails because the space stops the match). Exclusion zones apply. Stored in `bodyTags` sorted and de-duplicated, without the `#`.

**Effective tags** of a note = frontmatter `tags` ∪ `bodyTags`. Query filters (§9) match against the union; `validate`'s tag checks apply to **frontmatter tags only** (§10.2); the index stores the two sources separately.
