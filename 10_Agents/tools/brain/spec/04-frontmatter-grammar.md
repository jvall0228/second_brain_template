---
title: "brain Spec §4 — Frontmatter grammar"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 4. Frontmatter grammar

*Section 4 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

`brain` parses the YAML **subset** implied by the §10.1 contract of [PRD](../../../../00_Meta/PRD.md) — not full YAML. Notes whose frontmatter falls outside the subset are **still indexed**; each violation is recorded in that note's `frontmatterErrors` for `validate` to surface (parsing is best-effort, never fatal).

## 4.1 Block detection

- Frontmatter exists iff **line 1** of the file is exactly `---`. The block ends at the next line that is exactly `---`.
- Opener with no closer: error `unterminated-frontmatter`; everything after the opener is treated as body (so links still index).
- No opener: the note has no frontmatter (`frontmatter` is `{}`); `validate` flags it unless the path is exempt (§10.3).

## 4.2 Line grammar (inside the block)

Evaluated top to bottom; first matching rule wins. A **key line** requires zero indent, a key matching `[A-Za-z0-9_-]+`, a colon, and then either end-of-line or at least one space (`title:"Foo"` with no space is not a key line — it falls through to `unsupported-yaml`).

| Line shape | Meaning |
|------------|---------|
| blank | ignored |
| first non-space char `#` | comment, ignored |
| key line with non-empty value | scalar entry (§4.3); a value of `[...]` is a flow list (§4.4) |
| key line with empty value | opens a block list; if no list items follow before the next key line or block end, the value is `null` |
| `- item` (any indent ≥ 0, `-` then whitespace) | item appended to the open block list; the list **closes at the next key line or block end**, and a list item with no open list → error `list-item-without-key` |
| anything else | error `unsupported-yaml:<line>`; line skipped |

- **Duplicate keys:** error `duplicate-key:<key>`; the **last** occurrence wins (mirrors common YAML loaders).
- Nested mappings, block scalars (`|`, `>`), anchors, and multi-document markers are all outside the subset → `unsupported-yaml`.

## 4.3 Scalars

- Scalars are strings, always — `true`, `2026-08-11`, and `42` are stored as the strings `"true"`, `"2026-08-11"`, `"42"`. No type coercion.
- A scalar wrapped in a matching pair of double or single quotes has the outer pair stripped. **No escape processing** is performed inside quotes (known limitation, §11).
- Whitespace is trimmed before quote-stripping. Full-line comments only: a `#` inside a value is part of the value.
- Block-list and flow-list items receive this same scalar treatment (trim, then quote-strip).

## 4.4 Lists

- **Block lists** (house style) parse per §4.2.
- **Flow lists:** a value starting `[` and ending `]` has the outer brackets stripped; if any `[` or `]` remains inside → `unsupported-yaml` (nested flow is out of subset). The remainder splits on commas **not inside** single or double quotes; items are then scalars (§4.3). A value starting `[` without a closing `]` → `unsupported-yaml`.

## 4.5 Typed fields

From the parsed map, three fields get convenience extraction into the note record:

- `title` — scalar → string. Missing or non-scalar → `null` (validate flags per §10).
- `tags` — list of strings. A bare scalar is **coerced** to a one-element list with error `tags-not-a-list` (Obsidian tolerates the scalar form; house style does not).
- `updated` — scalar matching `^\d{4}-\d{2}-\d{2}$` **and** a valid calendar date → kept as that string. Anything else → record `updated: null` plus error `invalid-updated` (the raw value stays visible in `frontmatter`).

The full parsed map is preserved as-is under `frontmatter` (values: string, list of strings, or `null`), so future skills can read keys this spec doesn't type.

Template placeholders (`{{…}}`) are ordinary strings to the parser; the `09_Templates/` exemption is applied by `validate`, not the parser (§10.3).
