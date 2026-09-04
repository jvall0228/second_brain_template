---
title: "brain Spec §11 — Divergences from Obsidian and known limitations"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 11. Divergences from Obsidian and known limitations

*Section 11 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

- **No title-based resolution** (deliberate; §6). Title matches become repair hints, not links.
- **No partial path-suffix matching for legacy imports** (`to/foo` matching `a/to/foo.md`): full path or bare name only — the plan's three-step ladder is the whole ladder.
- Block references (`#^id`) are explicitly unsupported and migration-blocking; heading fragments are verified per §6.4.
- Inline code spans are line-scoped; CommonMark multi-line spans are not recognized (§5.2).
- Indented code blocks, HTML comments, and `%%` comments are scanned for links/tags (only fenced blocks and inline spans are excluded).
- Setext headings are not recognized.
- Quoted-scalar escape sequences are not processed (§4.3).
- Ambiguous path or legacy-heading matches remain unresolved; migration never guesses.
