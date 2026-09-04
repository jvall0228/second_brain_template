---
title: "brain Spec §6 — Link and fragment resolution"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 6. Link and fragment resolution

*Section 6 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

Markdown links use source-relative explicit paths compatible with GitHub, VS Code, and Obsidian. Legacy imports retain Obsidian's filename-first model until `migrate-links` converts them. Title matching remains a hint only.

**Folding rule:** every case-insensitive comparison in this section means NFC normalization followed by `str.casefold()`. (For vaults conforming to the §10.2 filename rules this reduces to ASCII case-insensitivity, making behavior independent of the interpreter's Unicode database version.)

## 6.1 Resolution table

From the note corpus: **basename** (final path component minus `.md`) → list of paths, keyed by the folding rule with original case retained for mismatch detection.

## 6.2 Legacy algorithm

For a target `T` (post §5.1 normalization), resolution tries **notes first, then assets**:

1. **Self:** `T` is empty → resolves to the containing note.
2. **Bare name** (`T` contains no `/`): look up the note basename table.
   - one candidate → resolved;
   - multiple → **ambiguous**: `path: null`, status `ambiguous`, and deterministic candidate warnings; never guess;
   - none → step 4.
3. **Path** (`T` contains `/`): exact match against note path `T + ".md"`, case-sensitively; failing that, by the folding rule (unique hit → resolved; multiple hits → ambiguity rule above; none → step 4). Partial path *suffix* matching is **not** supported (§11).
4. **Asset fallback:** if `T`'s final component has an extension — it matches `\.[A-Za-z0-9]+$` and the suffix is not `md` — resolve against the **asset list** with the same branch structure as steps 2–3 (bare name → asset basename table, *including* the extension; path → exact asset path; same ambiguity and case rules). Trying notes first means the legacy target `web-2.0` finds a note named `web-2.0.md` even though `.0` looks like an extension; an imported image target `img.png` finds the asset.
5. **Unresolved:** `path: null`. If some note's `title` equals `T` under the folding rule, each such path is recorded as a `title-match:<path>` repair hint.

## 6.3 Markdown algorithm

Percent-decode with UTF-8 semantics (`+` stays literal), normalize NFC, then repeat external-scheme/protocol-relative classification so encoding cannot disguise a URI as a local path. Join local destinations to the containing note's parent with POSIX separators. Reject a leading `/`, a normalized path that escapes the vault, external schemes, protocol-relative URLs, and unsafe/unsupported destinations. An explicit `.md` resolves as a note; an extensionless destination may resolve as a note for import tolerance; other extensions resolve as assets. Exact case wins, a unique folded match carries `case-mismatch`, and multiple folded candidates remain unresolved/ambiguous. Fragment-only destinations resolve to the containing note.

## 6.4 Heading fragments and slugs

ATX headings receive GitHub-compatible slugs in document order from their rendered inline text: inline link/image markup contributes its label/alt text rather than its destination, raw HTML tags are removed, and HTML entities are decoded before NFC + casefold. Inline punctuation/format marks (including `_`) are removed, whitespace collapses to `-`, Unicode letters/numbers/marks are preserved, and duplicate bases receive `-1`, `-2`, and so on. Markdown fragments match these unique slugs. Legacy fragments match heading text under the folding rule; duplicate text is ambiguous and leaves the whole link unresolved. A missing legacy fragment is recorded as `unresolved-fragment` while retaining the resolved path/backlink so WP8 can read the unchanged corpus honestly; migration still refuses it. A successful fragment resolution records `{line, slug}`.

## 6.5 Case mismatches

Any difference between the link text and the actual filename/path casing on a resolved link records the warning `case-mismatch` — the repo lives on case-sensitive filesystems where such links are latent breakage even though Obsidian resolves them.

## 6.6 Backlinks and warnings

- **Backlinks:** for every resolved note-target link (embed or not), the containing note's path is added to the target's `backlinks` (sorted, de-duplicated).
- Per-link warnings carry ambiguity candidates, case/fragment-case mismatches, title hints, unresolved fragments, and unsupported block/destination states; `validate` maps the blocking path states while import previews report legacy fragment debt before any write.
