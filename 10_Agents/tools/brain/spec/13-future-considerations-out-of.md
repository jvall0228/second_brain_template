---
title: "brain Spec §13 — Future considerations (out of M5 scope)"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 13. Future considerations (out of M5 scope)

*Section 13 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

- Verifying heading/block fragments against the target's indexed headings.
- Reference-style and multiline Markdown links remain future parser work; inline source-relative Markdown is the maintained authoring contract, with legacy parsing retained only for imports.
- Excluding HTML/`%%` comments from extraction.
- ~~A `restricted/*`-aware output filter~~ — adopted 2026-08-11 (issue #17): tag-only `restricted/private`, index reduction in §8.3, `restricted-link` warning in §10.2. Still future: directory-based restriction and finer-grained values, revisited only if tag-only proves insufficient.
