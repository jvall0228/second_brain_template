---
title: "brain Spec §12 — Decisions this spec makes beyond the plan (review focus)"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 12. Decisions this spec makes beyond the plan (review focus)

*Section 12 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

1. **mtime is excluded from the index** (plan listed it in extraction scope) — required for the committed-index/CI determinism the plan itself mandates; `recent` stats the working tree live instead. §8.2.
2. **The committed index is built from git-tracked files only** (working corpus ∩ `git ls-files`); query commands see the full working tree. Untracked scratch can never make CI's freshness check fail. §2.
3. **`sizeBytes` measures normalized text**, not on-disk bytes — same determinism argument against `autocrlf` checkouts. §8.2, §3.
4. **Query commands always rebuild in memory** rather than reading the committed index. §9.
5. **Folding-rule matching (NFC + casefold) with `case-mismatch` warnings**; all paths NFC-normalized. §2, §6.
6. **Assets are recorded (path-only)** so Markdown images and imported embeds can resolve; legacy resolution tries notes first, then assets. §2, §6.2.
7. **Validate's tag checks cover frontmatter tags only**; inline `#tags` are informal. §10.2.
8. **The template-placeholder exemption is per-value**, so real notes in `09_Templates/` (its README) stay fully checked. §10.3.
9. **Warnings never block commits** (exit 2 passes the hook); only errors do. §10.4.
10. **The test-fixture tree is excluded from the corpus**, and M5.4 ships a `.gitattributes` guard for the index file. §2, §8.2.
