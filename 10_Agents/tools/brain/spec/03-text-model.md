---
title: "brain Spec §3 — Text model"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 3. Text model

*Section 3 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

- Files are read as bytes and decoded **UTF-8 (strict)**. A leading byte-order mark (U+FEFF) is stripped. Newlines are normalized (`\r\n` and `\r` → `\n`) before parsing. All line numbers are **1-based** over the normalized text.
- All downstream measurements (including `sizeBytes`, §8) are taken from the normalized text, so checkout-time newline conversion (e.g. `core.autocrlf`) cannot change the index.
- **Decode failure:** the note is still indexed with the frontmatter error `not-utf8` and this exact record: `frontmatter: {}`, `title: null`, `updated: null`, `headings: []`, `links: []`, `bodyTags: []`; `backlinks` computed normally (other notes may link to it); `sizeBytes` = the byte length after **byte-level** newline normalization (`b"\r\n"`/`b"\r"` → `b"\n"`) — deterministic without decoding.
- **Read failure:** an `OSError` raised while reading a note (broken symlink, permission denied, file vanished mid-walk) must never crash a command — parsing is best-effort, never fatal (§4). The note is still indexed, with the frontmatter error `not-readable`, the same empty record shape as decode failure, and `sizeBytes: 0` (nothing was read; no OS error text enters the index, keeping it deterministic). `validate` surfaces the finding as the note's **only** error — the derived frontmatter-field checks (`missing-frontmatter`, `missing-title`, `missing-tags`, `missing-updated`, tag checks) are suppressed for a note whose content could not be read or decoded, since they would be false claims burying the actual cause (§10.2); every other command (`index`, `list`, `search`, `recent`, `curate`, …) treats the note as content-empty and skips it.
