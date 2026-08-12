---
title: "brain Spec — Parsing, Link Resolution, and Index Schema"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# `brain` Spec — Parsing, Link Resolution, and Index Schema

## 1. Scope and status

This note is the **M5.0 deliverable**: the concrete parsing, link-resolution, index-schema, and command-semantics rules that `brain.py` implements. [PRD](../../../00_Meta/PRD.md) §19 M5 requires these rules to be specified in a spec note before implementation; the implementation plan's Phase M5.0 additionally required owner review before the Indexer phase (M5.1). **Reviewed and promoted to canonical by the owner on 2026-08-11** — changes now follow §6.3 change control.

Design inspiration is Obsidian's MetadataCache; the portable authoring contract is [Relative Markdown Link Rules](../../solutions/obsidian-issues/wikilink-resolution-rules.md). Where this spec deliberately diverges from Obsidian or from the implementation plan, the divergence is listed in §11 and §12.

**Editor surfaces this spec serves (must-consider on every change).** The vault has two supported editors — **Obsidian** (primary UI) and **VS Code** ([PRD](../../../00_Meta/PRD.md) §6.5) — and `brain` is the compatibility keystone between them:
- The **link-resolution model (§6) tracks Obsidian's**: a link that resolves differently in `brain` than in Obsidian is a bug in one of them, and every intentional divergence must be recorded in §11.
- The **VS Code surface consumes `brain` directly**: `.vscode/tasks.json` invokes `validate`, `index`, `search`, `recent`, `report`, `tasks`, and `links` (the backlinks-panel substitute there), so command semantics (§9–10) and output are part of that editor's UX contract.
- Any change to this spec or to `brain.py` behavior must therefore be checked against **both** editor surfaces, and structural consequences flow to the editor-surface parity duty in [OPERATING-RULES](../../docs/OPERATING-RULES.md) (update `.obsidian/`, `.vscode/`, and the §6.5 mapping together).

Normative language: **must** = required behavior; **records an error/warning** = the finding is stored in the index or produced by `validate` (§10), never silently dropped.

## 2. Corpus

- The **vault root** is the repository root. `brain` locates it as the directory **three levels above** the one containing `brain.py` — `Path(__file__).resolve().parents[3]`, since the file lives at `<root>/10_Agents/tools/brain/brain.py`. `--vault PATH` overrides it (used by tests).
- **Working corpus** (used by every query command and by `validate`): one filesystem walk over the vault root.
  - **Notes:** every file ending `.md`. **Assets:** every other file (recorded path-only, for embed resolution).
  - **Pruned:** any path with a component beginning with `.` (covers `.git/`, `.obsidian/`, `.github/`, `.githooks/`, `.gitignore`, …); any path with a `__pycache__` component; every tool test tree matching `10_Agents/tools/*/tests/` — mirroring `run_tests.py`'s suite-discovery rule, so fixture mini-vaults and secret-shaped test data never enter the real corpus no matter which tool they belong to; the index file itself (`10_Agents/tools/brain/vault-index.json`); the embeddings sidecar (`10_Agents/tools/brain/vault-embeddings.json`, §18.1 — gitignored and machine-local, it must never surface as an asset or be secret-scanned as content).
- **Index corpus** (used by `brain index` and `validate --check-index`): the working corpus restricted to files that are **git-tracked or staged** — the output of `git ls-files -z --cached`, run at the vault root. Content is still read from the working tree. This is what makes the committed index a pure function of committed content (§8.2): untracked scratch files, virtualenvs, and editor backups can never leak into it. If `git` is unavailable or the vault is not a repository, `index` falls back to the working corpus with a warning on stderr (this is the test-fixture path).
  - Known caveat (accepted): committing while a note has unstaged modifications, or committing a note that links to a still-untracked note, can produce a committed index that differs from a fresh CI rebuild. CI's freshness check catches it; the fix is `brain index` and a follow-up commit.
- **Paths** are vault-relative, `/`-separated on every platform, no leading `./`, and **Unicode-normalized to NFC** (`unicodedata.normalize("NFC", …)`) whether they come from the walk or from git — macOS filesystems report decomposed (NFD) names, which would otherwise change index bytes and break link resolution cross-platform. All path ordering is plain code-point sort over the NFC form.

## 3. Text model

- Files are read as bytes and decoded **UTF-8 (strict)**. A leading byte-order mark (U+FEFF) is stripped. Newlines are normalized (`\r\n` and `\r` → `\n`) before parsing. All line numbers are **1-based** over the normalized text.
- All downstream measurements (including `sizeBytes`, §8) are taken from the normalized text, so checkout-time newline conversion (e.g. `core.autocrlf`) cannot change the index.
- **Decode failure:** the note is still indexed with the frontmatter error `not-utf8` and this exact record: `frontmatter: {}`, `title: null`, `updated: null`, `headings: []`, `links: []`, `bodyTags: []`; `backlinks` computed normally (other notes may link to it); `sizeBytes` = the byte length after **byte-level** newline normalization (`b"\r\n"`/`b"\r"` → `b"\n"`) — deterministic without decoding.
- **Read failure:** an `OSError` raised while reading a note (broken symlink, permission denied, file vanished mid-walk) must never crash a command — parsing is best-effort, never fatal (§4). The note is still indexed, with the frontmatter error `not-readable`, the same empty record shape as decode failure, and `sizeBytes: 0` (nothing was read; no OS error text enters the index, keeping it deterministic). `validate` surfaces the finding as the note's **only** error — the derived frontmatter-field checks (`missing-frontmatter`, `missing-title`, `missing-tags`, `missing-updated`, tag checks) are suppressed for a note whose content could not be read or decoded, since they would be false claims burying the actual cause (§10.2); every other command (`index`, `list`, `search`, `recent`, `curate`, …) treats the note as content-empty and skips it.

## 4. Frontmatter grammar

`brain` parses the YAML **subset** implied by the §10.1 contract of [PRD](../../../00_Meta/PRD.md) — not full YAML. Notes whose frontmatter falls outside the subset are **still indexed**; each violation is recorded in that note's `frontmatterErrors` for `validate` to surface (parsing is best-effort, never fatal).

### 4.1 Block detection

- Frontmatter exists iff **line 1** of the file is exactly `---`. The block ends at the next line that is exactly `---`.
- Opener with no closer: error `unterminated-frontmatter`; everything after the opener is treated as body (so links still index).
- No opener: the note has no frontmatter (`frontmatter` is `{}`); `validate` flags it unless the path is exempt (§10.3).

### 4.2 Line grammar (inside the block)

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

### 4.3 Scalars

- Scalars are strings, always — `true`, `2026-08-11`, and `42` are stored as the strings `"true"`, `"2026-08-11"`, `"42"`. No type coercion.
- A scalar wrapped in a matching pair of double or single quotes has the outer pair stripped. **No escape processing** is performed inside quotes (known limitation, §11).
- Whitespace is trimmed before quote-stripping. Full-line comments only: a `#` inside a value is part of the value.
- Block-list and flow-list items receive this same scalar treatment (trim, then quote-strip).

### 4.4 Lists

- **Block lists** (house style) parse per §4.2.
- **Flow lists:** a value starting `[` and ending `]` has the outer brackets stripped; if any `[` or `]` remains inside → `unsupported-yaml` (nested flow is out of subset). The remainder splits on commas **not inside** single or double quotes; items are then scalars (§4.3). A value starting `[` without a closing `]` → `unsupported-yaml`.

### 4.5 Typed fields

From the parsed map, three fields get convenience extraction into the note record:

- `title` — scalar → string. Missing or non-scalar → `null` (validate flags per §10).
- `tags` — list of strings. A bare scalar is **coerced** to a one-element list with error `tags-not-a-list` (Obsidian tolerates the scalar form; house style does not).
- `updated` — scalar matching `^\d{4}-\d{2}-\d{2}$` **and** a valid calendar date → kept as that string. Anything else → record `updated: null` plus error `invalid-updated` (the raw value stays visible in `frontmatter`).

The full parsed map is preserved as-is under `frontmatter` (values: string, list of strings, or `null`), so future skills can read keys this spec doesn't type.

Template placeholders (`{{…}}`) are ordinary strings to the parser; the `09_Templates/` exemption is applied by `validate`, not the parser (§10.3).

## 5. Generic link grammar

### 5.1 Recognized forms and records

The schema-v2 extractor reads the maintained format plus one import-only legacy format into one record shape:

- **Standard inline Markdown:** `[label](destination)`, `![alt](destination)`, angle-bracket destinations, balanced parentheses, escaped delimiters, one optional fully quoted/parenthesized ignored title, URL-encoded paths/fragments, and fragment-only self-links. Arbitrary text after a destination is invalid rather than silently discarded. Reference-style and multiline links are intentionally not recognized.
- **Legacy import format:** `[[target]]`, `[[target|label]]`, `[[target#fragment]]`, `[[target#fragment|label]]`, and the `!` embed forms. The first `|` (or table-safe `\|`) separates the label; the first `#` separates the fragment; one final `.md` is stripped only from the compatibility `target` field. Odd backslash parity escapes either link syntax; even parity does not.

Each record always carries `raw`, `range`, `line`, `label`, `destination`, `fragment`, `format` (`markdown|wikilink`), `embed`, `placeholder`, and `resolution`. `range.start.offset`/`range.end.offset` are a half-open range in **normalized UTF-8 bytes**; endpoints also carry 1-based line and 0-based character column. `resolution` is `{status, path, fragment, warnings}`. `display`, `target`, `resolved`, and top-level `warnings` remain schema-v1 compatibility aliases for consumers. `format: wikilink` is the authoritative import-debt count; the index also exposes aggregate `linkCounts`. A maintained repository has zero such records.

A destination or fragment containing `{{` is a placeholder: indexed with `status: placeholder`, counted, and exempt from normal resolution/validation. A fragment beginning `^` is an unsupported block reference: its path may resolve for backlink structure, but the record status/warning is explicit and migration refuses it. Raw/bare URLs and Markdown destinations with a URI scheme or `//` are external and excluded. A leading `/` Markdown destination is recorded as unsupported rather than treated as repository-relative; portable vault links are source-relative.

### 5.2 Exclusion zones

Links (and inline tags, §7.2) are **not** extracted from:

- the frontmatter block;
- **fenced code blocks** — a fence opens on a line whose first non-space characters are three or more backticks or tildes (info string allowed) and closes on a line of at least as many of the same character and nothing else but whitespace; an unclosed fence runs to end of file;
- **inline code spans**, matched **within a single line**: a run of N backticks opens a span closed by the next run of exactly N backticks on the same line; runs left unmatched at end of line are literal text and exclude nothing. (Multi-line CommonMark spans are deliberately not supported — the line-scoped rule is deterministic, keeps line numbers exact, and prevents one stray backtick from swallowing the rest of the document. §11.)

This removes the known false-positive source from the M4 link check. Indented (4-space) code blocks, HTML comments, and Obsidian `%%` comments are **not** excluded in v1 (§11).

## 6. Link and fragment resolution

Markdown links use source-relative explicit paths compatible with GitHub, VS Code, and Obsidian. Legacy imports retain Obsidian's filename-first model until `migrate-links` converts them. Title matching remains a hint only.

**Folding rule:** every case-insensitive comparison in this section means NFC normalization followed by `str.casefold()`. (For vaults conforming to the §10.2 filename rules this reduces to ASCII case-insensitivity, making behavior independent of the interpreter's Unicode database version.)

### 6.1 Resolution table

From the note corpus: **basename** (final path component minus `.md`) → list of paths, keyed by the folding rule with original case retained for mismatch detection.

### 6.2 Legacy algorithm

For a target `T` (post §5.1 normalization), resolution tries **notes first, then assets**:

1. **Self:** `T` is empty → resolves to the containing note.
2. **Bare name** (`T` contains no `/`): look up the note basename table.
   - one candidate → resolved;
   - multiple → **ambiguous**: `path: null`, status `ambiguous`, and deterministic candidate warnings; never guess;
   - none → step 4.
3. **Path** (`T` contains `/`): exact match against note path `T + ".md"`, case-sensitively; failing that, by the folding rule (unique hit → resolved; multiple hits → ambiguity rule above; none → step 4). Partial path *suffix* matching is **not** supported (§11).
4. **Asset fallback:** if `T`'s final component has an extension — it matches `\.[A-Za-z0-9]+$` and the suffix is not `md` — resolve against the **asset list** with the same branch structure as steps 2–3 (bare name → asset basename table, *including* the extension; path → exact asset path; same ambiguity and case rules). Trying notes first means the legacy target `web-2.0` finds a note named `web-2.0.md` even though `.0` looks like an extension; an imported image target `img.png` finds the asset.
5. **Unresolved:** `path: null`. If some note's `title` equals `T` under the folding rule, each such path is recorded as a `title-match:<path>` repair hint.

### 6.3 Markdown algorithm

Percent-decode with UTF-8 semantics (`+` stays literal), normalize NFC, then repeat external-scheme/protocol-relative classification so encoding cannot disguise a URI as a local path. Join local destinations to the containing note's parent with POSIX separators. Reject a leading `/`, a normalized path that escapes the vault, external schemes, protocol-relative URLs, and unsafe/unsupported destinations. An explicit `.md` resolves as a note; an extensionless destination may resolve as a note for import tolerance; other extensions resolve as assets. Exact case wins, a unique folded match carries `case-mismatch`, and multiple folded candidates remain unresolved/ambiguous. Fragment-only destinations resolve to the containing note.

### 6.4 Heading fragments and slugs

ATX headings receive GitHub-compatible slugs in document order from their rendered inline text: inline link/image markup contributes its label/alt text rather than its destination, raw HTML tags are removed, and HTML entities are decoded before NFC + casefold. Inline punctuation/format marks (including `_`) are removed, whitespace collapses to `-`, Unicode letters/numbers/marks are preserved, and duplicate bases receive `-1`, `-2`, and so on. Markdown fragments match these unique slugs. Legacy fragments match heading text under the folding rule; duplicate text is ambiguous and leaves the whole link unresolved. A missing legacy fragment is recorded as `unresolved-fragment` while retaining the resolved path/backlink so WP8 can read the unchanged corpus honestly; migration still refuses it. A successful fragment resolution records `{line, slug}`.

### 6.5 Case mismatches

Any difference between the link text and the actual filename/path casing on a resolved link records the warning `case-mismatch` — the repo lives on case-sensitive filesystems where such links are latent breakage even though Obsidian resolves them.

### 6.6 Backlinks and warnings

- **Backlinks:** for every resolved note-target link (embed or not), the containing note's path is added to the target's `backlinks` (sorted, de-duplicated).
- Per-link warnings carry ambiguity candidates, case/fragment-case mismatches, title hints, unresolved fragments, and unsupported block/destination states; `validate` maps the blocking path states while import previews report legacy fragment debt before any write.

## 7. Body extraction

### 7.1 Headings

ATX headings only: 1–6 `#` characters at the start of a line (up to 3 leading spaces allowed), followed by a space and text; trailing closing-`#` sequences are stripped. Recorded in document order as `{level, line, slug, text}` (`line` per §3; `slug` per §6.4). Setext headings are not recognized (§11). Exclusion zones (§5.2) apply.

### 7.2 Inline tags

A body tag is `#` immediately followed by one or more of `[A-Za-z0-9_/-]`, containing **at least one non-digit** character, and preceded by start-of-line or whitespace (so URLs like `…/page#anchor` never match; `# Heading` fails because the space stops the match). Exclusion zones apply. Stored in `bodyTags` sorted and de-duplicated, without the `#`.

**Effective tags** of a note = frontmatter `tags` ∪ `bodyTags`. Query filters (§9) match against the union; `validate`'s tag checks apply to **frontmatter tags only** (§10.2); the index stores the two sources separately.

## 8. Index schema and determinism

### 8.1 Shape

```json
{
 "assets": ["08_Assets/example.png"],
 "notes": {
  "00_Meta/PRD.md": {
   "backlinks": ["AGENTS.md"],
   "bodyTags": [],
   "frontmatter": {"tags": ["type/meta"], "title": "PRD", "updated": "2026-08-11"},
   "frontmatterErrors": [],
   "headings": [{"level": 1, "line": 8, "slug": "prd", "text": "PRD"}],
   "links": [
    {"destination": "../AGENTS.md", "display": "AGENTS", "embed": false,
     "format": "markdown", "fragment": null, "label": "AGENTS", "line": 12,
     "placeholder": false,
     "range": {"start": {"column": 0, "line": 12, "offset": 200},
               "end": {"column": 22, "line": 12, "offset": 222}},
     "raw": "[AGENTS](../AGENTS.md)",
     "resolution": {"fragment": null, "path": "AGENTS.md",
                    "status": "resolved", "warnings": []},
     "resolved": "AGENTS.md", "target": "../AGENTS.md", "warnings": []}
   ],
   "sizeBytes": 12345,
   "tasks": [
    {"due": "2026-08-15", "line": 40, "malformed": [], "priority": "high",
     "status": "open", "text": "call dentist"}
   ],
   "title": "PRD",
   "updated": "2026-08-11"
  }
 },
 "linkCounts": {"legacy": 0, "markdown": 1, "placeholder": 0,
                "unsupportedBlockReference": 0, "wikilink": 0},
 "schemaVersion": 2
}
```

Field meanings are as defined in §3–§7 and §17 (`tasks`). Every field is always present (empty lists/`null` rather than omitted keys). `linkCounts` is the deterministic aggregate over every indexed record; `legacy` currently equals `wikilink` and remains named explicitly for migration/report consumers.

`schemaVersion` bumps on any breaking change to this shape; consumers must check it.

### 8.2 Deterministic serialization

The committed index must be a **pure function of tracked file contents** — a fresh CI clone rebuild must be byte-identical to the committed copy. Hence the index corpus in §2, plus:

- Serialized exactly as Python's `json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True)` plus a single trailing `\n`, written as UTF-8 with LF endings. Only strings, integers, booleans, `null`, objects, and arrays appear (no floats), so output is stable across Python ≥ 3.10. (The §8.1 example shows the real emitted key order: `assets` < `linkCounts` < `notes` < `schemaVersion`.)
- Object keys sort via `sort_keys`; every array is either **document order** (links, headings — deterministic from file content) or **explicitly sorted** (assets, backlinks, bodyTags, and the `notes` keys via key sort).
- **No timestamps, no mtimes, no absolute paths, no environment data, no tool-version stamp.** In particular, **file mtime is excluded** even though the plan's extraction-scope bullet listed it: git does not preserve mtimes, so a fresh clone would always produce a different index and the CI freshness check could never pass. The `recent` command's mtime tiebreak stats the working tree at query time instead (§9). *(Deviation from the plan — flagged for owner review, §12.)*
- `sizeBytes` is the UTF-8 byte length of the **normalized** text (§3; byte-level normalization for `not-utf8` files), not the on-disk size, for the same reason.
- M5.4 must ship a `.gitattributes` entry marking `10_Agents/tools/brain/vault-index.json` as `-text`, so `core.autocrlf=true` checkouts (the Git-for-Windows default) don't smudge the committed copy to CRLF and fail every `--check-index` byte-compare.
- **Merge driver (M8.6, issue #25):** `.gitattributes` additionally marks the two committed generated files — `10_Agents/tools/brain/vault-index.json` and `.vscode/second-brain.code-snippets` — with `merge=regenerate`. The driver is defined per clone as `git config merge.regenerate.driver true` (the `true` command exits 0 leaving `%A` = ours): merges of generated content resolve keep-ours, and **correctness comes from regeneration, not resolution** — the `.githooks/post-merge` hook re-runs `index` and snippet generation best-effort immediately after a merge, the pre-commit hook regenerates on the next commit, and CI freshness checks catch any skip. Clones without the driver configured degrade to a normal conflict plus the documented fallback recipe (`10_Agents/solutions/vault-tooling/index-merge-conflicts.md`). Any future committed generated file adopts the same attribute.

### 8.3 Restricted-note reduction (issue #17)

A note whose **frontmatter tags** contain `restricted/private` (bodyTags are informal and never trigger this, matching §10.2's posture) is **reduced** in the committed index rather than excluded — decided 2026-08-11 per the accepted triage recommendation on issue #17. The committed index is the vault's most-copied artifact (PRD §9.4); without reduction it would re-leak the very content the tag marks.

- **Kept:** path (the `notes` key), `title`, `frontmatter` (including `tags` — consumers must be able to see *why* the record is reduced), `updated`, `sizeBytes`, `frontmatterErrors`, `links`, and `backlinks`. Links/backlinks stay so containment and discovery retain structure. On a reduced link, `label`/`display` and `fragment` are nulled, the nested fragment resolution is nulled, and `raw` is rewritten to a label-free canonical form for its format, so link prose never reaches the committed index.
- **Dropped (emptied/nulled, not omitted):** `headings: []`, `bodyTags: []`, and `tasks: []` — body-derived fields — plus the link-record prose fields above.
- The reduction applies to the **committed index only**: `brain index` output and the `validate --check-index` rebuild (both serialize the reduced form, so the byte-compare stays consistent). Query commands (§9) keep the full in-memory record — they run against the local working tree, where the note body sits right beside them; reducing them would cost the owner `search`/`show` utility while protecting nothing.
- This is a **sanctioned, tag-driven exception** to the spirit of the §15.1 config/index invariant: index output varies with note *content* (the tag), never with `00_Meta/config.yaml`. The committed index remains a pure function of tracked file contents (§8.2).
- Honest framing (conventions § restricted/private): reduction is leak resistance, not access control — the note body is still in the repo, readable by anything that reads files.

## 9. CLI command semantics

Invocation: `brain <command> [args]`. A clean checkout can use the root resolver (`./brain` on POSIX, `brain.cmd` on Windows); the universal long-form fallback is `python3 10_Agents/tools/brain/brain.py <command> [args]`. Every command accepts `--json`; human output is plain text. Query commands **rebuild the index in memory from the working corpus on every run** (the vault is small; stale reads are worse than the milliseconds) — the committed `vault-index.json` exists for consumers who read JSON without running Python and is written only by `index`. Exit codes: `0` success, `1` operational error (bad argument, note not found); `validate` alone uses the three-code contract in §10.4. Resolver-specific failures use §21.1.

Where a command takes a `<note>` argument, it accepts a vault-relative path or a bare name; the argument gets §5.1 target normalization (one trailing `.md` stripped — so `brain show 00_Meta/PRD.md` works) and then the §6 ladder.

- **`index`** — rebuild from the index corpus and write `vault-index.json` per §8; print the path written.
- **`list`** — note paths, sorted. Filters (ANDed): `--dir PREFIX` (path prefix), `--tag TAG` repeatable (effective-tag exact match; a trailing `/*` matches the whole namespace), `--type X` (sugar for `--tag type/X`). JSON: array of `{path, title, updated}`.
- **`search <query>`** — case-insensitive substring over title, heading texts, and body (body searched in full, code blocks included); combinable with `--tag`. Human: `path:line: snippet` for body/heading hits, `path: title: <title>` for title hits. JSON: array of `{path, field, line, snippet}` (`field` ∈ `title` | `heading` | `body`; `line` is `null` for title hits). With `--semantic`, the command instead ranks whole notes by the §18.4 hybrid rule (degrading to exactly this keyword behavior when semantic ranking is impossible — §18.4 defines both modes).
- **`links <note>`** — the note's outgoing generic records, backlinks, unresolved targets, and explicit `legacyCount`/`placeholderCount`. JSON: `{path, outgoing, backlinks, unresolved, legacyCount, placeholderCount}`.
- **`migrate-links`** — §22: source-hashed preview by default; `--check` exits 1 while any legacy link (including a placeholder) or blocker remains; explicit `--write` performs recovery and the crash-recoverable transaction. `--check` and `--write` are mutually exclusive; all modes support `--json`.
- **`tags`** — effective-tag usage counts grouped by namespace (text before the first `/`; tags without `/` group under `(none)`), sorted by namespace then value. JSON: `{namespace: {value: count}}`.
- **`show <note>`** — the full §8.1 record for one note (human output: a readable summary of the same fields).
- **`recent [n]`** — `n` (default 10) notes by `updated` descending; ties broken by working-tree mtime descending, then path ascending; notes with `updated: null` sort last (per PRD §15, `updated` is the primary recency signal and day-granular). JSON: array of `{path, title, updated}`.
- **`validate`** — §10.
- **`curate`** — the §14 re-review signals as one report: expired, missing `expires:`, expires beyond the one-year cap, oversized, stale (days-old weighted by backlink count, sorted worst-first), orphans, unreferenced `08_Assets/` files; `--check-urls` additionally probes source URLs over the network (opt-in only; never runs pre-commit). JSON: one sorted array per signal.
- **`context`** — each bootstrap doc's byte size against its §14 budget, plus the total; missing docs report `null`. JSON: `{docs, totalBudget, totalBytes}`.
- **`report`** — §16: the five-section vault-health synthesis (stale-active, orphans, Inbox aging, tag drift, unresolved links); `--since YYYY-MM-DD` scopes the two change-attributable sections per §16.3. Thresholds come from the `report` config key (§15.3) with built-in defaults.
- **`tasks`** — §17.3: checkbox tasks across the vault, filterable by `--open`, `--due <date|today>`, `--overdue`, `--project PREFIX`.
- **`embed`** — §18.3: maintain the semantic-search embeddings sidecar. `--stdin-json` ingests precomputed vectors, `--local` embeds with the optional local model, `--status` reports coverage.

## 10. Validate semantics

### 10.1 Rule sources

Tag namespace membership is read **at runtime** from the authoritative table in [CONVENTIONS](../../../00_Meta/CONVENTIONS.md#tag-namespaces) — `brain` hardcodes no taxonomy. Mechanically: take the first markdown table after the `## Tag Namespaces` heading; skip the header and separator rows; for each data row, the **namespace** is the first backtick-quoted token in column 1 with any trailing `/*` removed; if column 3's cell text begins with `Free-form` (case-insensitive), the namespace is **open** (any value passes); otherwise the namespace is **closed** and its value list is the backtick-quoted tokens in column 3. Applied to the current table this yields closed `audience`, `type`, `workflow`, `status` and open `topic` — and if the owner adds or re-marks a namespace, `brain` follows the table with no code change. A missing or unparseable table, or a row yielding no namespace, is a validate **error** (`conventions-table-unreadable`), never a silent pass.

### 10.2 Checks

**Errors** (exit 1): missing frontmatter; missing/null `title` or `updated`; a missing, null, or **empty** `tags` list (`tags: []` declares no tags and fails the same `missing-tags` check; the §10.3 template-placeholder exemption is per-value, and an empty list has no values to exempt, so it fires in `09_Templates/` too); `not-readable` (§3 read failure — `validate` reports it as the note's only finding, suppressing the derived frontmatter-field checks, and `not-utf8` behaves the same way; every other command skips the file); `invalid-updated`; any §4 `frontmatterErrors` entry except the warning-mapped ones below; a frontmatter tag not slash-delimited, in a namespace absent from the conventions table, or (for closed namespaces) not in the value list — **frontmatter tags only; `bodyTags` are informal and never checked**; a filename-convention violation; an unresolved or ambiguous internal link (placeholders exempt); `path-collision` — two corpus paths equal under the §6 folding rule, which cannot co-exist on default macOS/Windows filesystems. Secret-scanning findings (§10.5) are also errors.

**Filename convention:** applies to the **basename** of note files only (directories and assets are not checked). A note basename must match `^[a-z0-9]+(-[a-z0-9]+)*\.md$` — all-digit segments are allowed, so dated notes like `2025-01-15.md` and `2024-01-review.md` pass. Exceptions per [CONVENTIONS](../../../00_Meta/CONVENTIONS.md): `AGENTS.md`, `CLAUDE.md`, `README.md` at any level; the 14 exact-case framework paths registered in `CORE_FRAMEWORK_PATHS`; periodic tokens `YYYY-W##-review.md` and `YYYY-Q#-review.md`; `SKILL.md` inside `10_Agents/skills/` (Agent Skills format, M6). Case variants of a registered framework path fail even when the lowercase basename would otherwise match kebab-case; the exception does not apply to an identically named note elsewhere.

**Agent Skills contract (`10_Agents/skills/`, added at M6 per the implementation plan):** every skill directory (a direct child of `10_Agents/skills/` containing notes) must hold a `SKILL.md` whose frontmatter carries — in addition to the vault contract — an Agent Skills `name` equal to the directory name (`skill-name-mismatch`) and a non-empty `description` string (`skill-missing-description`); a skill directory without a `SKILL.md` is `skill-missing`. All three are errors.

**Warnings** (exit 2 if no errors): `case-mismatch`; `unsupported-block-reference`; `tags-not-a-list`; `duplicate-key`; `restricted-link` — a note **without** `restricted/private` in its frontmatter tags links to or embeds a resolved note **with** it. Legacy `unresolved-fragment` remains visible in records/migration blockers without a validate finding during the WP8 compatibility window. `missing-author` — a `02_Inbox/` agent draft with no non-empty `author:`; `task-invalid-date`; and the §14 curation signals. `invalid-expires` remains an error. Placeholders are counted/reported but exempt.

**`--check-index`:** re-serialize the index corpus per §8.2 and byte-compare against the committed `vault-index.json`; a mismatch or missing file is an error ("stale index — run `brain index`").

### 10.3 Exemptions

- `09_Templates/**`: any frontmatter value (or list item) containing `{{` is deemed to satisfy the required-field, format, and membership checks it would otherwise fail — the placeholder **is** the value. The exemption is per-value, not per-note: a template-directory note without placeholder values (e.g. the section README) is fully checked. The glob is recursive, so `09_Templates/variants/` (issue #12 specialization sources) is covered the same way — variant files carry placeholder frontmatter like the templates they mirror. Placeholder **links** are exempt everywhere by construction (§5.1).
- `CLAUDE.md` at the vault root: exempt from all frontmatter checks (one-line adapter, PRD §8.2).

### 10.4 Output and exit codes

Human output: one line per finding — `ERROR <path>[:<line>] <rule>: <message>` / `WARN …` — sorted by path, then line (findings without a line first), then rule; a final summary line `N errors, M warnings`. JSON: `{"errors": [...], "warnings": [...]}` where each finding is `{"line": int|null, "message": str, "path": str, "rule": str}`.

Exit codes: `0` clean · `1` at least one error · `2` warnings only. The pre-commit hook and CI (M5.4) block on exit 1 and pass on 0/2.

### 10.5 Secret scanning

PRD §16.2's never-commit-credentials rule is enforced by `validate` itself, so the existing hook/CI/agent-stop chain blocks credentials with no new wiring. Every finding is an **error** (rule `secret-<name>`, exit 1); severity is fixed by design.

**Scope.** Every file in the **working corpus** (§2) — notes *and* assets — one pass per `validate` run. The §2 pruning already keeps the scan safe by construction: dot-directories (`.git/`, `.obsidian/`, `.vscode/`, …), every `10_Agents/tools/*/tests/` tree, and the committed `vault-index.json` never enter the corpus. Binary files are skipped by NUL-byte sniff (a `0x00` byte in the first 8 KiB); text is decoded UTF-8 with replacement characters and newline-normalized per §3, so line numbers match the rest of `validate`. Frontmatter and code blocks are **not** excluded — a credential is a credential wherever it sits.

**Rule table.** Detection is **data-driven**: the module-level `SECRET_RULES` table in `brain.py` — `(name, compiled pattern)` pairs — is authoritative for the exact patterns; extending detection is a table edit (add a row there and a row here in the same commit; #22's self-improvement loop and upstream sync extend it the same way). The table below describes each rule in words (deliberately not as literal match-bait):

| Rule name | Detects | Pattern (in words) |
|-----------|---------|--------------------|
| `aws-access-key-id` | AWS access key IDs | `AKIA` followed by exactly 16 uppercase letters/digits, word-bounded |
| `github-token` | GitHub tokens | prefix `ghp_`, `gho_`, or `github_pat_` followed by 20+ word characters |
| `slack-token` | Slack tokens | `xox` + one lowercase letter + `-` + 10+ token characters |
| `private-key` | PEM private-key headers | five dashes, `BEGIN`, an optional uppercase label, `PRIVATE KEY`, five dashes |
| `generic-credential` | literal credential assignments | a key named like api-key / secret / token / password (case-insensitive), then `:` or `=`, then a **quoted** literal of 12+ token characters containing at least one digit |
| `high-entropy-string` | long opaque literals (the one conservative entropy heuristic) | `:` or `=`, then a **quoted** run of 40+ base64 characters containing lowercase, uppercase, and a digit (padding `=` allowed) |

The two assignment rules require the value to be *entirely* quoted token characters, and the entropy heuristic requires mixed case plus a digit — so prose, link markup, bare git SHAs (lowercase hex has no uppercase), and long URLs (contain `:`/`.`/`?` outside the charset) never flag; tuned to zero false positives on this repo's own tree, which the test suite pins with a repo self-scan.

**Allowlist.** A line is exempt when it carries an HTML comment containing the token `brain:allow-secret-pattern` — marker and pattern on the **same line**. The committed marker is the audit trail: documentation *about* token shapes stays possible, and every suppression is greppable. There is no file- or directory-level allowlist.

**Output.** Findings follow §10.4 (`ERROR <path>:<line> secret-<name>: …`) but the message **never echoes the matched text** — it names the rule and points at the marker escape, so a real credential is not additionally copied into terminals, CI logs, or agent transcripts.

**Backstop.** GitHub-side secret scanning + push protection (issue #24 item 3) is a repository setting owned outside this tool — it catches formats this table doesn't know, including in git history. Tracked separately; `validate` neither depends on nor replaces it.

## 11. Divergences from Obsidian and known limitations

- **No title-based resolution** (deliberate; §6). Title matches become repair hints, not links.
- **No partial path-suffix matching for legacy imports** (`to/foo` matching `a/to/foo.md`): full path or bare name only — the plan's three-step ladder is the whole ladder.
- Block references (`#^id`) are explicitly unsupported and migration-blocking; heading fragments are verified per §6.4.
- Inline code spans are line-scoped; CommonMark multi-line spans are not recognized (§5.2).
- Indented code blocks, HTML comments, and `%%` comments are scanned for links/tags (only fenced blocks and inline spans are excluded).
- Setext headings are not recognized.
- Quoted-scalar escape sequences are not processed (§4.3).
- Ambiguous path or legacy-heading matches remain unresolved; migration never guesses.

## 12. Decisions this spec makes beyond the plan (review focus)

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

## 13. Future considerations (out of M5 scope)

- Verifying heading/block fragments against the target's indexed headings.
- Reference-style and multiline Markdown links remain future parser work; inline source-relative Markdown is the maintained authoring contract, with legacy parsing retained only for imports.
- Excluding HTML/`%%` comments from extraction.
- ~~A `restricted/*`-aware output filter~~ — adopted 2026-08-11 (issue #17): tag-only `restricted/private`, index reduction in §8.3, `restricted-link` warning in §10.2. Still future: directory-based restriction and finer-grained values, revisited only if tag-only proves insufficient.

## 14. Curation signals (ops plan Phase 4)

Detection lives in `brain`; the judgment lives in the `curate` skill; findings needing owner decisions land as Inbox proposals. Every tunable is a module constant in one block at the top of `brain.py` — `CURATE_MAX_LINES`/`CURATE_MAX_BYTES` (oversized), `CURATE_STALE_DAYS`, `EXPIRES_CAP_DAYS`, the exemption sets, and the `BOOTSTRAP_BUDGETS` map with `BOOTSTRAP_TOTAL_BUDGET`. Policy prose (TTL defaults, what's exempt and why) lives in [CONVENTIONS](../../../00_Meta/CONVENTIONS.md) § Expiration; the constants are authoritative for values.

- **`expires:`** — optional frontmatter date (`YYYY-MM-DD`). Malformed → `invalid-expires` error (§10.2). Present and past → **expired** (curate report only). More than `EXPIRES_CAP_DAYS` after `updated:` → **expires-beyond-cap**. Absent on a note that should carry one → **missing-expires**; exempt by path: `02_Inbox/` (zero-friction capture; assigned at triage), `02_Outbox/` (ephemeral packets; lifecycle is the archive path), `03_Journal/`, `07_Archives/`, `09_Templates/`, `10_Agents/solutions/`, the changelog, `00_Meta/STATUS.md`, and `CLAUDE.md`; exempt by type tag: `type/decision` (event records, via `EXPIRES_EXEMPT_TYPE_TAGS`). The orphan check uses the path exemptions only — a decision record still wants inbound links.
- **oversized** — normalized size or line count over the constants; exempt `07_Archives/` and the changelog (frozen/append-only content is never a split candidate).
- **stale** — `updated:` older than `CURATE_STALE_DAYS`; score = days-old × (1 + backlink count), sorted worst-first, so heavily-referenced stale notes surface first.
- **orphans** — zero backlinks; exempt the expires-exempt set plus `AGENTS.md`, `CLAUDE.md`, and the root `README.md`.
- **unreferenced assets** — `08_Assets/` files no resolved generic link or embed points at.
- **dead URLs** — `--check-urls` only: HEAD each distinct `http(s)` URL (10s timeout); 403/405 responses are HEAD-hostile hosts, not dead links. Network access makes this opt-in forever: never run by `validate`, the pre-commit hook, or CI.

`validate` surfaces only the free, offline, low-noise subset as warnings — `missing-expires`, `expires-beyond-cap`, `oversized`, `bootstrap-budget[-total]` — gated behind `VALIDATE_CURATION_WARNINGS` (flipped on with the one-time backfill). Warnings never block commits (§10.4); expired/stale/orphan findings stay report-only because they demand judgment, not mechanical fixes.

## 15. Vault config (`00_Meta/config.yaml`) — issue #2

A structured, machine-readable home for per-fork policy overrides, read by `brain` and (through it) by both editor surfaces. Decided 2026-08-11 per the accepted triage recommendation on issue #2.

### 15.1 Location, optionality, change control

- The config lives at **`00_Meta/config.yaml`** — vault-level policy beside the other canonical meta docs, visible to Obsidian and the note corpus (a root dotfile would hide it). It is an asset in the §2 corpus (secret-scanned, indexed path-only); it never carries frontmatter and is exempt from note checks by not being a note.
- The file is **optional, and absence changes nothing**: no file, an empty file, or an all-comment file (the shipped template) all yield the empty config, and every behavior stays at its built-in default. Adding the file must never be required for a working vault.
- **Change control:** like `CLAUDE.md` (PRD §8.2), the file cannot carry `workflow/canonical` — treat it as §6.3 change-controlled anyway, like the meta docs it sits beside.
- The config **never influences `index` output**: the committed index stays a pure function of tracked content (§8.2) with config-independent semantics. Config is consumed by `validate`, by the `config` command, and by future consumers via the reader API.

### 15.2 Grammar bounds

The config grammar is the **same bounded YAML subset** the frontmatter parser targets (§4), extended by exactly one construct — **one level of nested mapping** (a zero-indent key with an empty value followed by uniformly-indented `key: value` lines). Full grammar: blank lines; full-line `#` comments; zero-indent scalar entries and flow lists (§4.3–4.4 semantics: strings always, quote-stripping, no escapes, no type coercion); block lists of scalars under a top-level key; nested mappings whose values are scalars or flow lists. **No pyyaml, ever** — `brain` stays stdlib-only, and the parser is `parse_config` in `brain.py` (the config section there is the planned seed of #31's `shared` module).

Out-of-subset content is **best-effort, never fatal**: each offending line becomes a finding (`config-unsupported`, `config-nesting-too-deep` for a second mapping level, `config-list-item-without-key`, `config-duplicate-key`) and is skipped; the rest of the file still parses. `load_config` returns `({}, [finding])` for an unreadable (`config-not-readable`) or non-UTF-8 (`config-not-utf8`) file and `({}, [])` for an absent one — it never raises.

### 15.3 Key registry

Top-level keys are registered here so later issues cannot collide:

| Key | Status | Meaning |
|-----|--------|---------|
| `write_exceptions` | **implemented** | List of vault-relative directory paths agents may write to **in addition to** the Inbox-first defaults (`02_Inbox/`, `02_Outbox/`, `10_Agents/solutions/` — `AGENT_WRITE_DEFAULT_PREFIXES`). Config only ever widens the set; entries are normalized to a trailing `/`. The enforcement point is `agent_write_allowed(rel, config)`, for harness write-gates and skills; it also allows the built-in single-file exceptions in `AGENT_WRITE_DEFAULT_FILES` (append-only agent logs inside otherwise PR-only prefixes — currently `10_Agents/docs/rejected-proposals.md`, per conventions § Agent Write Rules). Session-scoped carve-outs (onboard-owner, agent-generated skills/tools per PRD §6.2) remain policy prose, not paths. |
| `extension_trust` | **implemented** | VS Code extension trust policy (PRD §6.5): `first-party` (default) or `relaxed`. A documented override consumed by the editor docs ([vscode-editor-support](../../../06_Resources/vscode-editor-support.md)) — `brain` exposes the effective value via `extension_trust(config)` and `brain config`; it drives no `brain` behavior itself. |
| `context` | **implemented** (#12) | Fork context recorded by [onboard-owner](../../skills/onboard-owner/SKILL.md)'s specialization step: **one scalar**, `personal` (the default when absent) or `work`. Beyond parsing and reporting it — `vault_context(config)` and `brain config` expose the effective value — `brain` acts on it in no way yet: specialization happens at onboarding time by rewriting the periodic templates in `09_Templates/` in place from `09_Templates/variants/`, not at read time, so the key is a record for tooling and future skills, not a switch. |
| `environments` | reserved (#15) | — |
| `modules` | reserved (#32) | — |
| `provenance` | reserved (#18) | — |
| `report` | **implemented** (#16) | Health-report thresholds (§16.4): a one-level nested mapping under `report:` whose subkeys are `stale_days` (stale-active threshold, default `30`) and `inbox_days` (Inbox triage-debt threshold, default `14`). Values are non-negative-integer scalars (digits only — §4.3 stores strings; `report_thresholds(config)` converts). A `null` value or absent subkey means the default; malformed values fall back to the default at read time while `check_config` reports them (§15.4). Consumed by `brain report` only — never by `index`, and it moves no `validate` severity. |
| `sync` | reserved (#26) | — |
| `tasks` | **implemented** (#28) | Task-module settings (§17.4): a one-level nested mapping under `tasks:` whose sole subkey is `carry_over` (`on` \| `off`, default `on`) — whether daily-note instantiation carries yesterday's unchecked tasks into the new note's Backlog section (§17.5). `tasks_carry_over(config)` converts; a `null` value or absent subkey means the default; malformed values fall back to the default at read time while `check_config` reports them (§15.4). Consumed by `daily_note.py` only — never by `index`, and it moves no `validate` severity. |
| `template_version` | **implemented** (#6) | Upstream template version record (issue #6): **one scalar**, a free-form version string (by convention the upstream release tag, e.g. `template-v1.2.0`), or absent when the fork has never recorded one. Written by the [sync-upstream](../../skills/sync-upstream/SKILL.md) skill after a completed sync; that skill compares the recorded value against upstream release tags to find pending releases. A record, not a switch — `template_version(config)` and `brain config` expose the effective value (`null` when unset); `brain` drives no behavior from it and it never influences `index` output. |

Reserved keys parse and are **tolerated silently** whatever their shape. **Unknown** keys (neither implemented nor reserved) are tolerated too — forward compatibility — at the cost of a validate **warning** (`config-unknown-key`), never an error.

### 15.4 Validate semantics

All config findings land **on `00_Meta/config.yaml`** as per-file findings in the normal §10.4 shape. **Errors:** every §15.2 parse finding except `config-duplicate-key`; `config-not-readable` / `config-not-utf8`; `config-invalid-value` (an implemented key with the wrong shape — `write_exceptions` not a list, `extension_trust`, `context`, or `template_version` not a scalar, `report` or `tasks` not a nested mapping, a known `report` subkey whose value is not a digits-only non-negative integer, or a known `tasks` subkey whose value is not a scalar; an explicit `null` equals absent and is clean); `config-bad-write-exception` (an entry that is not a vault-relative path: empty, absolute, drive-lettered, or containing `..`). **Warnings:** `config-duplicate-key` (last wins, mirroring §4.2); `config-unknown-key` (an unknown top-level key, or an unknown subkey under `report` or `tasks`, reported dotted as `report.<key>` / `tasks.<key>`); `config-missing-directory` (a well-formed `write_exceptions` entry naming no existing directory — legal, since a fork may configure ahead of creating it); `config-unknown-value` (an `extension_trust`, `context`, or `tasks.carry_over` value outside its documented pair).

### 15.5 `config` command

`brain config` (§9 conventions: `--json`, exit 0) prints the **effective** configuration: presence, the raw parsed map, the merged write-exception prefixes (defaults first), the effective `extension_trust`, the effective `context`, the effective task carry-over toggle (§17.4), the recorded `template_version` (`null` when unset), the reserved-key list, and any findings. It is the non-Python surface of the reader API for harness tasks and scripts.

## 16. Health report (`brain report`) — issue #16

A read-only synthesis of the in-memory index (§9's usual `walk_corpus` + `build_index` — **no new parsing**, no network, no git) into the five vault-health sections below, for the `periodic-review` and `vault-maintenance` skills and the "Brain: Health Report" VS Code task. Exit code is always `0` on success (the report informs; `validate` judges); `1` only for an operational error (a malformed `--since`). Ordering inside every section is deterministic; the human output prints the sections in the order listed here (most-actionable-first).

### 16.1 Sections

All tag reads in this section are **frontmatter tags only** (a bare-scalar `tags:` coerced to one element per §4.5; body `#tags` are informal, mirroring §10.2), and values containing `{{` (template placeholders) are ignored.

1. **Stale-active** (`staleActive`): notes carrying the frontmatter tag `status/active` whose `updated:` is **strictly more than** `stale_days` days (default 30) before today. Notes with `updated: null` cannot be aged and are skipped (`validate` already flags `missing-updated`/`invalid-updated`). Rows `{daysOld, path, title, updated}`, sorted oldest-first (`daysOld` descending, then path).
2. **Orphans** (`orphans`): notes with **zero backlinks and zero outgoing non-placeholder links** — fully disconnected, per the issue's definition. Excluded as legitimately leaf-like: any note whose basename is `README.md`, `AGENTS.md`, or `CLAUDE.md`, and everything under `07_Archives/` or `09_Templates/`. Sorted path list. (Distinct from `curate`'s inbound-only orphan signal, which serves the curation charter; this section measures disconnection.)
3. **Inbox aging** (`inboxAging`): every note under `02_Inbox/` except its `README.md`, bucketed by age in days. A note's **capture date** is the `YYYY-MM-DD` filename prefix of its basename when present and a valid calendar date (`source: "filename"`), else its `updated:` value (`source: "updated"`), else unknown (`source: "unknown"`, `ageDays: null`). Age = today − capture date, floored at 0. Buckets, fixed order: `0-7d` (≤ 7), `8-30d`, `31-90d`, `90+d`, `unknown`; each holds `{ageDays, path, source}` rows sorted by path. `triageDebt` additionally lists the paths whose age is strictly greater than `inbox_days` (default 14).
4. **Tag drift** (`tagDrift`): frontmatter tag usage vs the §10.1 conventions taxonomy, read by the **same** `load_taxonomy` machinery `validate` uses (consistency by construction). Tags are counted once per note that carries them, over the §16.3 note universe. `taxonomyReadable: false` (with all three lists empty) when the table is unreadable — `validate` owns that error. Otherwise: `unknown` — rows `{count, reason, tag}` sorted by tag, `reason` ∈ `not-namespaced` | `unknown-namespace` | `unknown-value` (closed namespaces only); `singleUse` — sorted tags in **open** namespaces used by exactly one note (near-duplicate bait, e.g. `topic/sw`); `nearDuplicates` — rows `{namespace, values: [shorter, longer]}` for pairs of distinct open-namespace values where, under the §6 folding rule, the shorter (≥ 2 chars, strictly shorter) shares its first character with the longer and is an in-order subsequence of it — catching both prefixes (`tool`/`tools`) and abbreviations (the issue's `sw`/`software`); sorted by namespace then value pair.
5. **Unresolved links** (`unresolvedLinks`): `{count, links}` where `links` rows are `{line, path, target}` for every non-placeholder link with `resolved: null`, over the §16.3 note universe, sorted by path, line, target — the same population `validate` errors on, given trend context here.

### 16.2 JSON shape

Top-level keys (always present): `inboxAging` (`{buckets, triageDebt}` with all five bucket keys always present), `orphans`, `since` (the `--since` date string or `null`), `staleActive`, `tagDrift` (`{nearDuplicates, singleUse, taxonomyReadable, unknown}`), `thresholds` (`{inboxDays, staleDays}` — the **effective** integers after config merge), `unresolvedLinks`. Emitted via the standard `--json` path. Output is a pure function of the tree, the config, today's date, and `--since` — no timestamps, mtimes, or environment data — so two runs on the same day are byte-identical.

### 16.3 `--since YYYY-MM-DD`

Review-period scoping. `--since` restricts **exactly two** sections — **tag drift** and **unresolved links** — to the notes whose `updated:` is on or after the given date (the changes attributable to the period under review; notes with `updated: null` are excluded from a scoped universe since they cannot be attributed). **Stale-active, orphans, and Inbox aging always cover the whole vault**: they measure accumulated debt, which a review must see regardless of period. A value that is not a real `YYYY-MM-DD` calendar date is an operational error (exit 1). Without `--since`, the note universe for every section is the full working corpus.

### 16.4 Thresholds

`stale_days` and `inbox_days` are read from the `report` config key (grammar and defaults in §15.3) via `report_thresholds(config)`; with no config file, both stay at their built-in defaults (`REPORT_STALE_ACTIVE_DAYS = 30`, `REPORT_INBOX_TRIAGE_DAYS = 14` — module constants beside the §14 tunables). Per §15.1 the config never influences `index` output, and the report is synthesis-only: nothing here feeds back into `validate` severities.

## 17. Task tracking (`brain tasks`) — issue #28

Markdown-native checkbox tasks, adopted 2026-08-11 per the accepted triage recommendation on issue #28: **Obsidian Tasks emoji grammar is the canonical inline metadata**, so Obsidian users get the native plugin experience with zero vault changes while `brain` answers the same queries on every other surface. The conventions entry ([CONVENTIONS](../../../00_Meta/CONVENTIONS.md) § Tasks) carries the human-facing emoji ↔ meaning table and the location rule: tasks live where their context lives (any note); there is no central task file.

### 17.1 Recognition

A task is a list-item checkbox line in the note body: optional leading whitespace (nested subtasks index like any other), a bullet (`-`, `*`, or `+`), one space, `[c]` where `c` is exactly one character, one space, then non-empty text. `c` = space → `status: "open"`; any other character (`x`, `X`, Obsidian custom statuses like `-` or `/`) → `status: "done"`. A bracket pair with no text after it is not a task. The §5.2 exclusion zones apply: detection runs on the **masked** line, so checkboxes inside fenced code blocks or inline code spans never index; the task text is then taken from the **raw** line at the matched offset (masking preserves length), so inline code *within* a real task's text survives verbatim. Blockquoted checkboxes (`> - [ ]`) and ordered-list checkboxes (`1. [ ]`) are not recognized (out of grammar, mirroring Obsidian Tasks' default).

Extraction happens in the same `extract_body` line walk as links, headings, and body tags — **no additional parsing pass** — and each note record carries the results as the `tasks` array (document order). The field addition is purely additive to §8.1 (every field still always present), so `schemaVersion` stays 1.

### 17.2 Task record and emoji metadata

Each task record: `{due, line, malformed, priority, status, text}` — every field always present.

- `line` — 1-based source line (§3). `status` — `"open"` | `"done"` (§17.1).
- **Emoji tokens** are parsed out of the checkbox text and stripped from `text` (whitespace then collapsed to single spaces). Date-bearing emoji — 📅 due, ⏳ scheduled, 🛫 start, ✅ done, ➕ created — take an optionally-space-separated `YYYY-MM-DD` token (ASCII digits only — non-ASCII digit forms are not date-shaped); ⏫/🔼/🔽 set `priority` `high`/`medium`/`low`; 🔁 takes free text running to the next recognized emoji or end of line. A trailing emoji variation selector (U+FE0F) is tolerated. For a repeated field the **last** occurrence wins (mirroring §4.2's duplicate-key posture).
- **Indexed fields:** only `due` (`"YYYY-MM-DD"` or `null`) and `priority` (`"high"` | `"medium"` | `"low"` | `null`) — the queryable subset. Scheduled/start/done/created dates and recurrence rules are recognized and stripped from `text` but not stored (future consumers re-read the source line, which `line` pins).
- **Malformed metadata:** a date-bearing emoji whose value is date-*shaped* but not a real calendar date has the token consumed; a missing or non-date-shaped value leaves the text in place. Either way the task **still indexes** with the affected field at its null/default and the field's name appended to `malformed` (sorted, de-duplicated) — and `validate` surfaces each entry as the `task-invalid-date` **warning** (§10.2). Parsing is best-effort, never fatal (§4's posture); 🔁 takes free text and can never be malformed.

Restricted notes (§8.3): `tasks` is emptied to `[]` in the committed index — task text and metadata are body prose.

### 17.3 `tasks` command

`brain tasks` (§9 conventions: in-memory index, `--json`, exit 0; `1` for a malformed `--due` value) lists every task in the working corpus. Filters, ANDed:

- `--open` — `status == "open"` only.
- `--due <YYYY-MM-DD|today>` — tasks **with** a due date on or **before** the given date (`today` resolves to the current date); a task with no due date never matches.
- `--overdue` — open tasks whose due date is **strictly before** today (due today is not overdue).
- `--project PREFIX` — note-path prefix match (e.g. `04_Projects/example-project/`).

**Ordering (deterministic):** due date ascending with `null` due dates last, then path (code-point order), then line. JSON: an array of task records each extended with `path`. Human output: `path:line  [ ]|[x] text` plus a parenthesized suffix listing due date, priority, and malformed fields when present. The VS Code surface runs `tasks --open` via the "Brain: Tasks (open)" task (§6.5 parity).

### 17.4 Config: `tasks.carry_over`

The `tasks` config key (§15.3) holds the module's settings; its sole subkey `carry_over` (`on` | `off`, default **on**) gates §17.5's daily-note carry-over. `tasks_carry_over(config)` is the reader (malformed → default; `check_config` reports per §15.4), and `brain config` prints the effective value. Per §15.1 the config never influences `index` output.

### 17.5 Surfacing: daily-note carry-over

`daily_note.py` (the VS Code daily-note task), when **creating** today's note and the §17.4 toggle is on, copies **yesterday's unchecked task lines** — open checkboxes per §17.1, including nested ones, indentation preserved, fenced-code/inline-code exclusions applied via the shared `brain` parser — verbatim into the end of the new note's `### Backlog` section (before the section's trailing blank lines; if the instantiated template has no such heading, the section is appended). "Yesterday" is calendar yesterday (`today − 1 day`), so month, ISO-week, and year boundaries need no special casing; a missing, unreadable, or task-free yesterday note simply carries nothing, and a yesterday note tagged `restricted/private` carries nothing either (containment — task text must not flow from a restricted note into a new, non-restricted one). Existing notes are never rewritten — carry-over runs only at instantiation. The weekly-review template instead carries a prompt line pointing at `brain tasks --open` / `--overdue` (live query beats a stale snapshot at week granularity).

**Deferred surfacing (explicitly out of scope here):** VS Code task *views* and web-UI views (#27), notification/overdue digests (#21), external-tracker mirroring (#26 directionality).

## 20. Environment identity and scoped retrieval

Environment-scoped infrastructure is explicit, privacy-safe, and fail-closed.
Shared vault content remains portable; live wiring belongs to exactly one
owner-chosen environment.

### 20.1 Tracked manifest

Each registered environment is an immediate kebab-case directory at
`10_Agents/environments/<slug>/`. It contains a tracked `environment.json` and
a self-guarding `README.md`. The UTF-8 JSON manifest is at most 64 KiB and has
this exact version-1 shape:

```json
{
 "capabilities": {"computer-use": true},
 "class": "laptop",
 "fingerprints": [{"algorithm": "sha256", "digest": "<64 lowercase hex>", "source": "machine-v1"}],
 "freshness": {"checkedAt": "2026-08-11", "expiresAt": "2026-11-11"},
 "maintenance": {"inventory": "orientation-inventory.md", "ownerReviewRequired": true},
 "schemaVersion": 1,
 "slug": "work-laptop",
 "surfaces": ["codex", "vscode"]
}
```

`class` is `desktop`, `laptop`, `server`, `container`, `cloud`, or `other`.
Surfaces are sorted unique kebab-case identifiers. Capabilities map sorted
non-secret kebab-case names to booleans; identity, path, endpoint, and
credential-shaped names are forbidden. Fingerprints are SHA-256 evidence over
high-entropy, platform-native OS machine identifiers consumed inside the hash
boundary; malformed, nil, weak, and placeholder identifiers are rejected
before hashing. The list may be empty when the OS supplies no acceptable
identifier; that environment remains selectable explicitly or by selector. A
hostname/username fallback is forbidden because hashing low-entropy identity is
dictionary-identifiable; when no high-entropy ID is available, automatic
fingerprint matching is unavailable and explicit/selector selection is
required. Raw hostname, username,
home/repository path, credential, URL, and endpoint values never enter tracked
data, output, logs, or errors. `freshness` dates are real and ordered. The
maintenance record always points to the local inventory and requires owner
review. JSON field types are exact: schema version is integer `1` (never a
boolean/float), and every fingerprint component is a string before duplicate
or digest checks. Malformed values produce redacted findings rather than an
exception. Unknown keys or schema versions are errors.

### 20.2 Clone-local state

`.second-brain/environment` contains one selected slug. It and
`.second-brain/environments/<slug>/` are gitignored. The latter is the only
repository-local home for secrets-adjacent environment overlays such as
integration settings, notification destinations, hosting configuration, and
delivery state. Selectors/manifests may not be symlinks; directories must be
immediate children of their declared roots. Inputs are length- and grammar-
bounded before use.

Environment files are re-confined when opened, not merely when discovered.
Every child component and the final file must remain a non-link/reparse-point
path inside the vault; an identity change or race fails closed before content
can reach a result.

### 20.3 Selection

Selection precedence is `--env <slug>` > `SECOND_BRAIN_ENV` > the selector > a
unique local fingerprint match. `--env current` and the environment-variable
value `current` request normal automatic selection. An invalid value, missing
explicit/selected slug, invalid manifest, no fingerprint match, or multiple
fingerprint matches fails closed with a stable reason code; lower-precedence
sources are never consulted after a higher-precedence source is present. A
vault with zero registered manifests is `unconfigured` and shared-only.

All content-query consumers use the selected corpus: shared paths plus
`10_Agents/environments/<selected>/`, never another environment. This includes
list/search/links/tags/show/recent, report/curate/tasks, semantic embedding, and
current-scoped maintenance. Generic `brain validate` is intentionally
environment-neutral for CI and foreign clones: it validates every manifest
envelope, validates shared content, and does not select or read any environment
note body. The committed index deliberately contains shared tracked content
only, so its bytes do not vary by clone; selected environment notes remain
available through live commands. `brain env list` is the sole all-environment
diagnostic and emits only slug, registered/selected status, and freshness. It
never emits class, surfaces, capabilities, fingerprint counts/digests, or
capability values.

### 20.4 Commands and migration

- `brain env detect` prints the selected slug/source plus SHA-256 evidence for
  creating or refreshing a manifest. JSON never includes raw identity.
- `brain env list` prints metadata-only records and remains usable when current
  matching fails, so an owner can diagnose the selector safely.
- `brain env migrate <source> <target>` is preview-only. It enumerates exact
  vault-relative moves for an unregistered legacy directory, refuses symlinks,
  registered sources, invalid slugs, any existing target directory, and
  collisions, and performs zero writes. Traversal binds source directories and
  regular files without following links; any identity change discards the
  entire in-memory preview before a row can be emitted.
  The owner applies the reviewed move with version control, then creates the
  target manifest/landing note through orientation.

`agent-orientation` owns manifest creation/refresh and migration handoff.
Bootstrap, maintenance, automation, sync reports, generated integrations, and
personal-data tools must resolve the current environment first. Sync treats all
environment directories and `.second-brain/` as owner-local: non-current
contents are neither read nor serialized, and overlays are never proposed for
commit.

## 21. Portable `brain` resolver and installer

### 21.1 Repository launchers

The tracked root `brain` is a POSIX `sh` resolver; `brain.cmd` is its Windows
`cmd.exe` counterpart. They are location-independent copies: neither embeds the
checkout that supplied it. Resolution precedence is one CLI `--vault PATH` (or
`--vault=PATH`) > `BRAIN_VAULT` > the nearest ancestor of the physical CWD that
contains both a regular `AGENTS.md` and
`10_Agents/tools/brain/brain.py`. Missing values, repeated CLI overrides,
invalid roots, symlinked markers/tools, and no ancestor match are rejected
without printing the candidate path. A higher-precedence invalid input never
falls through. This gives nested vaults nearest-root behavior and keeps sibling
forks isolated. The Windows resolver uses `cmd.exe`'s built-in file-attribute
expansion for every trusted component and fails closed if attributes cannot be
verified; it does not depend on optional `fsutil` behavior.

After resolution, the launcher invokes that checkout's Python 3 tool with the
original argument vector. It does not capture or transform stdout/stderr and
returns the exact child exit status. POSIX requires `python3` and returns 127
when it is unavailable. Windows prefers `py -3`, then `python3`, then `python`,
and forwards `%ERRORLEVEL%`. Paths containing spaces and Unicode are quoted;
the launchers never evaluate arguments, source shell files, honor a `PYTHON`
override, or modify the environment.

### 21.2 Managed PATH installation

`brain install` is preview-only by default. It selects the first existing,
absolute, non-symlinked, writable directory in `PATH`; `--target DIRECTORY`
selects another existing writable directory explicitly. It never creates a PATH
directory or edits shell/profile/registry configuration. `--apply` copies the
platform launcher with a final-component compare-and-swap. `--doctor` is
read-only. `--uninstall` previews;
`--uninstall --apply` removes only the recognized managed launcher.

Ownership lives in a version-1 external manifest: POSIX defaults to
`$XDG_STATE_HOME/second-brain/brain-install.json` or
`~/.local/state/second-brain/brain-install.json`; Windows defaults under
`%LOCALAPPDATA%\second-brain`. `--state-file` or `BRAIN_INSTALL_STATE` may
override it with an absolute path. The manifest is outside the vault and stores
one artifact per platform: absolute target, platform, and installed SHA-256.
Install output previews the exact target and manifest paths. Unknown schemas,
foreign shapes, symlinked state/targets, targets inside the vault, stale hashes,
and a requested target different from the recorded target are refusals.

An absent target or a byte-identical current launcher is safe to record. A
different target is replaceable only when its digest matches this manifest's
recorded digest. POSIX apply publishes absent files with create-if-absent and
replaces existing files with an atomic exchange whose displaced object is
digest-verified before removal. POSIX uninstall first moves the final component
to a no-replace quarantine name and verifies it there. Windows holds every
verified non-reparse parent-chain handle without delete sharing and performs
create/open/delete through a bound final handle; the digest is checked on that
handle before mutation. If manifest update fails after a target mutation, the
old target is restored (or the new target removed). Uninstall likewise refuses
drift and restores a removed target if manifest cleanup fails. Platforms without
the required parent-bound mutation primitives fail closed. State directories
created for an attempted install are identity-bound and removed in reverse order
on rollback, restoring the pre-transaction directory state. A `KeyboardInterrupt` during target mutation or
before the ownership-manifest commit rolls the mutation back before propagating;
an already committed target/manifest pair remains consistent. Preview, doctor,
and refused operations make zero writes. Tests use fake PATH/state/home
directories exclusively.

### 21.3 Host capability boundary

The current official Codex plugin manifest schema does not document a `bin` or
executable-export field. This repository therefore does not invent plugin
metadata; project and managed PATH launchers are the supported surfaces. Revisit
plugin exposure only after an official host schema documents it and an
end-to-end compatibility test passes.

## 22. Legacy link migration (`brain migrate-links`) — issue #74

### 22.1 Preview and plan

No flag is a read-only preview. The migrator scans tracked working-corpus notes, parses raw UTF-8 bytes without newline conversion, resolves each legacy record through the same §6 engine, and emits a deterministic version-1 plan. The envelope is `{schemaVersion, planId, status, summary, edits, blockers, regenerateRequired}`. Each path-sorted edit carries `path`, `restricted`, preserved `mode`, raw `sourceSha256`/`resultSha256`, and ordered replacements with raw-byte half-open `range`, `line`, `before`, `after`, and `resolved`. `planId` is SHA-256 over canonical compact JSON excluding the ID. The summary counts scanned/changed files, legacy/Markdown links, conversions, placeholders, and unsupported block refs. A second identical preview is byte-stable. Internal exact replacement text remains available for apply, but every serialized CLI plan nulls `before`/`after` and sets `redacted: true` for `restricted/private` sources so migration diagnostics do not republish protected body prose.

Placeholders stay unchanged and counted. Ambiguous paths/headings, unresolved targets/fragments, block refs, unsafe sources, stale ranges, and overlapping edits are blockers; a plan with any blocker is never writable. Rendering uses the resolved target rather than regex text: notes keep explicit `.md`, paths are relative to the source and URL-encoded, heading links use §6.4 slugs, aliases become escaped labels, self-headings stay fragment-only, and embeds become Markdown images with a meaningful alt label. Splicing operates on raw byte ranges, preserving UTF-8 BOM, LF/CRLF/mixed endings, final-newline state, unrelated bytes, and file mode.

`--check` is read-only and exits 1 while **any legacy record** (placeholders included), edit, or blocker remains, otherwise 0. It is the zero-legacy acceptance gate rather than merely an automatic-edit-complete signal. `--json` exposes the same complete plan. Explicit `--write` is the only mutation mode; every successful write reports that the index, snippets, and skill adapters require immediate regeneration. The shipped corpus itself has zero legacy records; this command remains available for importing older vaults.

### 22.2 Write refusal and transaction

Write requires Git to establish that every **planned source path** is clean; unrelated owner edits do not block and are never touched. Before mutation the plan ID/shape, source hash, mode, replacement text/ranges, result hash, regular-file type, parent chain, and final identity are rechecked. Symlink/reparse paths, stale content/mode, unsupported mutation primitives, a foreign journal, or concurrent activity fail closed before overwrite.

On POSIX, every source parent is opened component-by-component with directory descriptors and no-follow flags and held through the transaction. Random same-directory stage names are journaled durably before creation, then desired files are fsynced there. Stage ownership identity is recorded before the staging helper returns, so an interruption at the return boundary still authenticates/removes that stage before the journal can retire; a concurrent occupant at the reserved name is preserved. Originals are descriptor-relatively quarantined and hash/mode/identity-verified, then desired files are installed with hard-link create-if-absent, so a concurrent final-component insertion is preserved and refused rather than overwritten. Publication attempts are rollback-tracked before the directory fsync, every containing directory is fsynced before the durable commit marker, and installed bytes/mode/inode are re-authenticated after that marker before success can remove recovery evidence. Any ordinary exception, `KeyboardInterrupt`, `SystemExit`, or trapped `SIGTERM` removes only authenticated staged outputs and restores quarantined originals without overwriting concurrent content. Platforms without the required held-parent descriptor operations (including the current unimplemented Win32 mutation path) are preview/check-only and fail before any write.

### 22.3 Crash recovery and idempotence

The O_EXCL lock and recovery journal is `.brain-link-migration.json` at the vault root (dot-pruned from the corpus, mode 0600). It records only authenticated transaction names, source/result hashes, modes, plan ID, PID, and commit state — no note bodies. Creation returns a held descriptor/inode/content guard; later states are complete append-only JSON lines written and fsynced through that descriptor, never path-replaced. Every update verifies the path still names the held inode with the expected mode/content before and after append. Cleanup descriptor-relatively quarantines the pathname, authenticates the moved inode, and deletes only that owned journal. A foreign replacement or in-place mutation is never overwritten or removed: it is preserved byte-for-byte with its mode and the operation fails closed. A second starter receives a stable active-migration refusal. The root journal and per-directory `.NAME.migrate-{new,old}-*` recovery artifacts are gitignored so a crash cannot make them accidental commit candidates; their existence remains visible to the recovery detector.

Preview and `--check` never recover: if a journal exists they report `interrupted-migration`, exit nonzero, and make zero writes. Explicit `--write` recovers a dead transaction before planning. If `committed: false`, recovery removes only verified installed results and restores verified backups; foreign final content is preserved and the backup retained for explicit manual recovery. If `committed: true`, recovery finishes the commit by verifying current results and removing verified backup/stage artifacts. Malformed/unsafe journals, live owning PIDs, hash drift, or missing evidence fail closed. Once complete, the journal disappears. A successful second automatic migration has zero edits; `--check` reaches 0 only after placeholders and every other maintained legacy record are also gone.

## 18. Semantic search (QMD — issue #8)

Natural-language, relevance-ranked retrieval over vault notes, layered **beside** the keyword machinery, never replacing it. Decided 2026-08-11 per the owner correction and accepted recommendation on issue #8 (QMD = **Query Markdown**, not Quarto). Two commands carry the whole feature: `brain embed` maintains a local vector store (§18.3), `brain search --semantic` queries it (§18.4). Every supported harness reaches it through the CLI — the universal layer (each `10_Agents/harnesses/*/wiring.md` documents invocation); no per-harness plugin is part of the compatibility contract.

### 18.1 Embeddings sidecar

- **Location:** `10_Agents/tools/brain/vault-embeddings.json`, beside the committed index but — unlike it — **gitignored** (a `.gitignore` entry ships with this section). Vectors are large, model-dependent, and environment-specific: each clone regenerates its own sidecar incrementally, and the #25 committed-generated-file machinery (merge driver, freshness CI) never applies to it. The path is pruned from the §2 corpus the same way the index file is, so the sidecar can never appear as an asset, enter the committed index, or be content-scanned by `validate`.
- **Shape** (serialized like §8.2 — `json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True)` + trailing `\n`, UTF-8/LF — except that **floats are allowed** here; the §8.2 no-floats rule protects the *committed* index only):

```json
{
 "dim": 384,
 "model": "all-MiniLM-L6-v2",
 "notes": {
  "04_Projects/example.md": {"hash": "<sha256 hex>", "vector": [0.1, -0.2]}
 },
 "schemaVersion": 1
}
```

- **Granularity is per-note** in v1 (`notes` keys are §2 vault-relative note paths). Per-section vectors are an anticipated refinement: `schemaVersion` bumps if the record shape changes, and consumers must check it — an unknown `schemaVersion` is treated as an absent store (§18.2).
- **Keying:** each entry carries `hash` — the SHA-256 hex digest of the note's full **normalized text** (§3, frontmatter included), computed at embed time. `model` and `dim` are store-global: vectors from different models are not comparable, so one sidecar holds exactly one model's vectors (§18.3 replacement rule). Every stored vector's length must equal `dim`.
- **Restricted containment:** a note whose frontmatter tags contain `restricted/private` (§8.3's trigger, frontmatter tags only) **never enters the sidecar**. `embed` skips such entries with a stderr notice (never an error — pipelines may blindly embed everything), and `search --semantic` ignores any sidecar entry whose note is *currently* restricted, so tagging a note restricted immediately removes it from semantic ranking even before the sidecar is regenerated. Embedding vectors are body-derived data in a queryable store; the §8.3 containment posture applies. Restricted notes can still surface through the keyword component — the same exposure §8.3 deliberately accepts for local query commands. As there, this is leak resistance, not access control.

### 18.2 Staleness and store loading

- A sidecar entry is **fresh** for a note iff the note exists in the working corpus, its recomputed content hash equals the stored `hash`, and the vector length equals `dim`. Anything else — edited note (hash mismatch), deleted/renamed note (no such path), wrong-length vector — makes the entry **stale**, and stale entries are **excluded** from semantic ranking (never re-ranked, never partially trusted): the note participates through the keyword component only, exactly as if it had no vector. Incremental re-embedding (`embed --local`, or a harness re-piping changed notes) restores freshness at cost proportional to edits.
- **Loading is best-effort, never fatal** (§4 posture): a missing sidecar yields an empty store; an unreadable, non-UTF-8, non-JSON, wrong-`schemaVersion`, or shape-invalid file is treated as **absent** with a one-line stderr notice naming the fix (`brain embed`). No command ever crashes on sidecar content.

### 18.3 `brain embed`

Maintains the sidecar. §9 conventions apply (`--json`, exit `0` success / `1` operational error). Exactly one mode flag is required:

- **`--stdin-json`** — the harness/API ingestion interface. Stdin is one JSON object: `{"model": "<non-empty string>", "vectors": {"<note path>": [<numbers>], …}}`. Validation (any violation is an operational error — message on stderr, exit 1, **sidecar untouched**): top level must be an object with exactly those two keys; `model` a non-empty string; `vectors` a non-empty object; every value a non-empty array of finite numbers (booleans are not numbers), all the same length; every key a working-corpus note path (§2 normalization applies) — unknown paths are reported and fail the whole call (all-or-nothing, so a typo cannot half-apply). Entries for restricted notes are **skipped with a stderr notice** per §18.1 (not an error), as are entries for notes whose content cannot be read or decoded (§3) — there is no text to hash. **Partial-update semantics:** when the incoming `model` and vector length match the existing store's `model`/`dim`, entries merge over it (each ingested note's `hash` recomputed from its current normalized text; unmentioned notes keep their entries); when either differs, the store is **replaced wholesale** with a stderr notice — mixed-model stores are never representable. Output: a summary — `{"dim", "model", "path", "skippedRestricted", "skippedUnreadable", "stored"}` under `--json`, the same facts as text otherwise (`--local` emits the analogous `{"dim", "embedded", "model", "path", "total"}`).
- **`--local [--model NAME]`** — the offline path, and the **one sanctioned optional non-stdlib dependency** in the vault: `sentence-transformers`, imported lazily inside this feature only, never at module import time, never required. When the import (or model load) fails, `embed --local` exits 1 with a message naming the three alternatives (install the optional package, pipe vectors via `--stdin-json`, or use keyword search) — a clean degradation message, never a traceback. When available: embed every non-restricted, readable note whose entry is missing or stale (incremental by hash; fresh entries untouched), under the model named by `--model`, else the store's recorded `model`, else the default constant (`EMBED_LOCAL_MODEL_DEFAULT`); a model different from the store's replaces the store wholesale, as above. When there is nothing to embed **and** nothing retained (an empty vault, or every note restricted/unreadable), the command reports and exits 0 **without writing** — a `{"dim": null}` store would violate the §18.1 shape.
- **`--status`** — coverage report, no writes, no model needed: `{"dim", "embedded", "missing", "model", "notes", "present", "stale"}` — total corpus notes (restricted and unreadable notes excluded from the embeddable universe), fresh/stale/missing counts, and whether the sidecar file exists.
- **External embedding APIs** are supported as **adapters outside `brain`**: a thin script (harness-side or personal) calls the API and pipes the result through `--stdin-json` / `--query-vector` — the same interface as harness-computed vectors. `brain` itself never takes an API key, endpoint, or credential in any form (PRD §16.2); no such adapter ships in the template.

### 18.4 `brain search --semantic <query>`

Ranks whole notes by a hybrid of vector similarity and keyword match. `--tag` filters (effective-tag semantics, §9) restrict the note universe for **both** components. Exit `0` on success — including every degraded case; `1` only for operational errors (malformed `--query-vector` input).

- **Query embedding sourcing**, in order: (1) `--query-vector` — read one JSON array of finite numbers from stdin (the harness/API path: whatever computed the note vectors embeds the query too); its length must equal the store's `dim`, else an operational error (exit 1). (2) Otherwise, the optional local model (§18.3), loaded with the store's recorded `model` — best-effort: any import/load/encode failure yields no query vector, silently eligible for (3). (3) Otherwise **no query embedding exists** → keyword degradation, below.
- **Keyword degradation:** when semantic ranking is impossible — no usable query vector, or the fresh-entry set (§18.2, restricted excluded) is empty (no sidecar, empty store, everything stale) — the command behaves **exactly** like plain `search` (§9): same rows, same human and `--json` output shape, exit 0, plus a one-line stderr notice naming the cause and the fix. `--semantic` must never hard-fail on a vectorless vault.
- **Hybrid ranking rule** (exact): for each note `n` in the (tag-filtered) universe, let `sem(n) = (cos(q, v_n) + 1) / 2` when `n` has a fresh vector `v_n` (cosine similarity, stdlib `math`; zero-magnitude vectors give `cos = 0`), else `sem(n) = 0`; let `kw(n) = 1` if the note has at least one plain-`search` hit (title, heading, or body) for the query, else `0`. Then `score(n) = round(0.7 · sem(n) + 0.3 · kw(n), 6)` — the weights are the module constants `SEMANTIC_WEIGHT` / `KEYWORD_WEIGHT`. A note enters the results iff it has a fresh vector or a keyword hit; results sort by `score` descending, then path ascending, truncated to `--top N` (default 10). Rounding before sorting makes ranking a pure function of the stored vectors, the query vector, the tree, and the flags — **deterministic given fixed vectors**.
- **Output** (semantic mode): JSON — an array of `{"keywordHits": int, "path", "score": float, "semanticScore": float|null, "title"}` rows in rank order (`semanticScore` is the rounded `sem(n)`, `null` when the note has no fresh vector); human — one `score  path  (title)` line per row. This intentionally ranks *notes* where plain `search` lists *hits*; the degraded mode keeps plain `search`'s shape so a vectorless vault still gets exactly the §9 contract.

### 18.5 Determinism and invariants

- The sidecar never influences `index` output, `validate` findings, or any command other than `embed` and `search --semantic` — the committed index stays a pure function of tracked content (§8.2) with or without embeddings present.
- Given a fixed sidecar and query vector, `search --semantic` output is byte-identical across runs and platforms (IEEE-754 arithmetic over identical inputs, rounded per §18.4; all ordering is explicit). No timestamps, mtimes, or environment data appear in the sidecar or in query output.
- Stdlib-only holds everywhere outside the §18.3 optional-import boundary: every other path of `embed` and all of `search --semantic` run with no third-party code, and the optional dependency's absence is never an import-time or default-path failure.

## 19. Remote safety (`brain remote-safety`) — issue #83

`remote-safety` is the mandatory preflight before a skill or tool reads personal
data from email, calendar, contacts, chat, drive, task, transcript, or similar
accounts. Capability inventory (which CLIs/connectors exist and which scopes they
claim) is harmless and stays separate; account data is not read until this gate
allows it.

### 19.1 Push-target discovery and normalization

- Discovery uses `git remote` plus `git remote get-url --push --all <remote>` and
  therefore evaluates every effective **push** URL, never fetch URLs alone. Exact
  `DISABLED`, `NO_PUSH`, and `no-push`/`no_push` sentinel values are treated as a
  deliberately fetch-only remote. A discovery failure is `unknown`, not local-only.
- Repository-local `include.path` and `includeIf.*.path` directives are also
  `unknown` (`unsafe-local-config-include`). They can expand through ambient
  HOME or another path outside the clone and substitute a target, so discovery
  reads the raw local config with includes disabled and refuses the indirection.
- Discovery evaluates the union of a sanitized repository-local view and the
  current invocation's ambient-effective Git view. The latter accounts for
  global/system `remote.*.pushurl`, `url.*.insteadOf`/`pushInsteadOf`, HOME, and
  `GIT_CONFIG_*` controls that a later Git invocation would honor; the union
  prevents either view from replacing and hiding a target in the other.
- GitHub HTTPS and SSH (`ssh://` or SCP-style) URLs on their default ports
  normalize to a provider key without userinfo, query, fragment, or `.git`.
  Insecure transports, nonstandard ports, malformed URLs, and non-GitHub hosts
  are `unknown`.
- Output never includes raw URLs, credentials, hostnames other than the provider
  class, owner/repository names, local paths, provider stderr, OS errors, or hashes
  derived from sensitive URL text. Targets are represented only by
  `github.com/<redacted>` (or `<redacted>`) and evaluation-local ordinal identifiers.

### 19.2 Provider boundary and decisions

The default injectable provider runs `gh repo view OWNER/REPO --json
visibility,isPrivate,isTemplate,templateRepository` with prompting disabled and a
bounded timeout. It pins `GH_HOST=github.com` and removes debug/trace sinks and Git
control/config-injection variables from provider child environments. Git target
discovery separately evaluates both repository-local and ambient-effective config;
local config that delegates to another file is rejected as described in §19.1.
Missing `gh`, auth/access
failures, timeouts, malformed JSON, and missing or inconsistent fields are stable
`unknown` reason codes; subprocess text is never forwarded.

Per target, verified `isTemplate: true` or consistent non-private metadata is
`block`; only `visibility: PRIVATE`, `isPrivate: true`, and `isTemplate: false` is
`pass`. Missing or inconsistent fields are `unknown`. `templateRepository` is
queried for provenance but does not make an otherwise private generated repository
a template destination. The combined verified state is `block` if any target
blocks, else `unknown` if any target is unknown, else `pass`.

`--acknowledge-unknown` changes the effective state from `unknown` to `pass` for
that process invocation only and records `verifiedState: unknown` plus the
`unknown-acknowledged` reason. It is never persisted. A verified block remains a
block even with the flag. With no push targets the result is a local-only pass:
personal-data reads may occur in memory, but connector-derived data must not be
written anywhere in the vault.

### 19.3 Output, exit status, and shared guard

Human and `--json` output carry the same stable facts: `schemaVersion`, effective
`state` (`pass|block|unknown`), `verifiedState`, sorted reason codes, target summaries,
`localOnly`, `personalDataAllowed`, `persistenceAllowed`, and
`unknownAcknowledged`. The command adds `persistenceRequested` and
`operationAllowed`. Without `--persist`, operation permission follows the guarded
read; with `--persist`, local-only mode makes `operationAllowed` false. Exit is `0`
only when the requested operation is allowed and `1` otherwise.

All personal-data adapters must call `require_remote_safety(...)` immediately
before the connector and before opening an output file, passing `persist=True`
for capture/write flows. Process-boundary adapters use `remote-safety --persist
--json` and require both zero exit and `operationAllowed: true`. The helper raises
`RemoteSafetyError` on blocked/unknown access and on persistence in local-only
mode; `guarded_personal_data_call(...)` is the reference sequencing wrapper.
