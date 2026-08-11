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

This note is the **M5.0 deliverable**: the concrete parsing, link-resolution, index-schema, and command-semantics rules that `brain.py` implements. [[00_Meta/prd]] §19 M5 requires these rules to be specified in a spec note before implementation; the implementation plan's Phase M5.0 additionally required owner review before the Indexer phase (M5.1). **Reviewed and promoted to canonical by the owner on 2026-08-11** — changes now follow §6.3 change control.

Design inspiration is Obsidian's MetadataCache; the starting point is [[10_Agents/solutions/obsidian-issues/wikilink-resolution-rules]]. Where this spec deliberately diverges from Obsidian or from the implementation plan, the divergence is listed in §11 and §12.

**Editor surfaces this spec serves (must-consider on every change).** The vault has two supported editors — **Obsidian** (primary UI) and **VS Code** ([[00_Meta/prd]] §6.5) — and `brain` is the compatibility keystone between them:
- The **link-resolution model (§6) tracks Obsidian's**: a link that resolves differently in `brain` than in Obsidian is a bug in one of them, and every intentional divergence must be recorded in §11.
- The **VS Code surface consumes `brain` directly**: `.vscode/tasks.json` invokes `validate`, `index`, `search`, `recent`, `report`, `tasks`, and `links` (the backlinks-panel substitute there), so command semantics (§9–10) and output are part of that editor's UX contract.
- Any change to this spec or to `brain.py` behavior must therefore be checked against **both** editor surfaces, and structural consequences flow to the editor-surface parity duty in [[10_Agents/docs/operating-rules]] (update `.obsidian/`, `.vscode/`, and the §6.5 mapping together).

Normative language: **must** = required behavior; **records an error/warning** = the finding is stored in the index or produced by `validate` (§10), never silently dropped.

## 2. Corpus

- The **vault root** is the repository root. `brain` locates it as the directory **three levels above** the one containing `brain.py` — `Path(__file__).resolve().parents[3]`, since the file lives at `<root>/10_Agents/tools/brain/brain.py`. `--vault PATH` overrides it (used by tests).
- **Working corpus** (used by every query command and by `validate`): one filesystem walk over the vault root.
  - **Notes:** every file ending `.md`. **Assets:** every other file (recorded path-only, for embed resolution).
  - **Pruned:** any path with a component beginning with `.` (covers `.git/`, `.obsidian/`, `.github/`, `.githooks/`, `.gitignore`, …); any path with a `__pycache__` component; every tool test tree matching `10_Agents/tools/*/tests/` — mirroring `run_tests.py`'s suite-discovery rule, so fixture mini-vaults and secret-shaped test data never enter the real corpus no matter which tool they belong to; the index file itself (`10_Agents/tools/brain/vault-index.json`).
- **Index corpus** (used by `brain index` and `validate --check-index`): the working corpus restricted to files that are **git-tracked or staged** — the output of `git ls-files -z --cached`, run at the vault root. Content is still read from the working tree. This is what makes the committed index a pure function of committed content (§8.2): untracked scratch files, virtualenvs, and editor backups can never leak into it. If `git` is unavailable or the vault is not a repository, `index` falls back to the working corpus with a warning on stderr (this is the test-fixture path).
  - Known caveat (accepted): committing while a note has unstaged modifications, or committing a note that links to a still-untracked note, can produce a committed index that differs from a fresh CI rebuild. CI's freshness check catches it; the fix is `brain index` and a follow-up commit.
- **Paths** are vault-relative, `/`-separated on every platform, no leading `./`, and **Unicode-normalized to NFC** (`unicodedata.normalize("NFC", …)`) whether they come from the walk or from git — macOS filesystems report decomposed (NFD) names, which would otherwise change index bytes and break link resolution cross-platform. All path ordering is plain code-point sort over the NFC form.

## 3. Text model

- Files are read as bytes and decoded **UTF-8 (strict)**. A leading byte-order mark (U+FEFF) is stripped. Newlines are normalized (`\r\n` and `\r` → `\n`) before parsing. All line numbers are **1-based** over the normalized text.
- All downstream measurements (including `sizeBytes`, §8) are taken from the normalized text, so checkout-time newline conversion (e.g. `core.autocrlf`) cannot change the index.
- **Decode failure:** the note is still indexed with the frontmatter error `not-utf8` and this exact record: `frontmatter: {}`, `title: null`, `updated: null`, `headings: []`, `links: []`, `bodyTags: []`; `backlinks` computed normally (other notes may link to it); `sizeBytes` = the byte length after **byte-level** newline normalization (`b"\r\n"`/`b"\r"` → `b"\n"`) — deterministic without decoding.
- **Read failure:** an `OSError` raised while reading a note (broken symlink, permission denied, file vanished mid-walk) must never crash a command — parsing is best-effort, never fatal (§4). The note is still indexed, with the frontmatter error `not-readable`, the same empty record shape as decode failure, and `sizeBytes: 0` (nothing was read; no OS error text enters the index, keeping it deterministic). `validate` surfaces the finding as the note's **only** error — the derived frontmatter-field checks (`missing-frontmatter`, `missing-title`, `missing-tags`, `missing-updated`, tag checks) are suppressed for a note whose content could not be read or decoded, since they would be false claims burying the actual cause (§10.2); every other command (`index`, `list`, `search`, `recent`, `curate`, …) treats the note as content-empty and skips it.

## 4. Frontmatter grammar

`brain` parses the YAML **subset** implied by the §10.1 contract of [[00_Meta/prd]] — not full YAML. Notes whose frontmatter falls outside the subset are **still indexed**; each violation is recorded in that note's `frontmatterErrors` for `validate` to surface (parsing is best-effort, never fatal).

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

## 5. Wikilink grammar

### 5.1 Recognized forms

`[[target]]`, `[[target|display]]`, `[[target#fragment]]`, `[[target#fragment|display]]`, and the embed variants prefixed `!`. Parsing inside the brackets:

1. Split at the **first display separator**: a `|`, optionally preceded by a backslash which is consumed — Obsidian requires the escaped form `[[target\|Display]]` inside markdown tables, and both forms mean the same link. Left of the separator is the link path, right is the display text.
2. Split the link path at the **first `#`** → target / fragment. A fragment beginning `^` is a block reference; otherwise a heading reference. Fragments are recorded but **never affect resolution** (§6).
3. Trim surrounding whitespace from target, fragment, and display.
4. A target ending `.md` has **exactly one** such extension stripped (`[[foo.md]]` → `foo`; `[[foo.md.md]]` → `foo.md`). An **empty** target (`[[#heading]]`) is a self-reference and resolves to the containing note.
5. A target containing `{{` is a **placeholder link**: recorded with `placeholder: true`, exempt from resolution (`resolved: null`, not counted as unresolved).

The bracket body must be non-empty and may not contain `[`, `]`, or a newline. A `[[` preceded by a backslash is not a link.

### 5.2 Exclusion zones

Links (and inline tags, §7.2) are **not** extracted from:

- the frontmatter block;
- **fenced code blocks** — a fence opens on a line whose first non-space characters are three or more backticks or tildes (info string allowed) and closes on a line of at least as many of the same character and nothing else but whitespace; an unclosed fence runs to end of file;
- **inline code spans**, matched **within a single line**: a run of N backticks opens a span closed by the next run of exactly N backticks on the same line; runs left unmatched at end of line are literal text and exclude nothing. (Multi-line CommonMark spans are deliberately not supported — the line-scoped rule is deterministic, keeps line numbers exact, and prevents one stray backtick from swallowing the rest of the document. §11.)

This removes the known false-positive source from the M4 link check. Indented (4-space) code blocks, HTML comments, and Obsidian `%%` comments are **not** excluded in v1 (§11).

### 5.3 Recorded fields

Each link is recorded in document order with: `raw` (full matched text), `target`, `fragment` (or `null`), `display` (or `null`), `embed` (bool), `placeholder` (bool), `line`, `resolved` (vault path or `null`), and `warnings` (list of strings, §6.5).

## 6. Link resolution

Mirrors Obsidian's filename-first model with **one deliberate omission: no title-based resolution.** The solutions note marks title matching unreliable, so a link that only matches some note's `title:` stays **unresolved** and `validate` flags it (with a repair hint, §6.5).

**Folding rule:** every case-insensitive comparison in this section means NFC normalization followed by `str.casefold()`. (For vaults conforming to the §10.2 filename rules this reduces to ASCII case-insensitivity, making behavior independent of the interpreter's Unicode database version.)

### 6.1 Resolution table

From the note corpus: **basename** (final path component minus `.md`) → list of paths, keyed by the folding rule with original case retained for mismatch detection.

### 6.2 Algorithm

For a target `T` (post §5.1 normalization), resolution tries **notes first, then assets**:

1. **Self:** `T` is empty → resolves to the containing note.
2. **Bare name** (`T` contains no `/`): look up the note basename table.
   - one candidate → resolved;
   - multiple → **ambiguous**: resolve to the candidate with the fewest path segments, tie-broken by code-point path order; warning `ambiguous`;
   - none → step 4.
3. **Path** (`T` contains `/`): exact match against note path `T + ".md"`, case-sensitively; failing that, by the folding rule (unique hit → resolved; multiple hits → ambiguity rule above; none → step 4). Partial path *suffix* matching is **not** supported (§11).
4. **Asset fallback:** if `T`'s final component has an extension — it matches `\.[A-Za-z0-9]+$` and the suffix is not `md` — resolve against the **asset list** with the same branch structure as steps 2–3 (bare name → asset basename table, *including* the extension; path → exact asset path; same ambiguity and case rules). Trying notes first means `[[web-2.0]]` finds a note named `web-2.0.md` even though `.0` looks like an extension; `![[img.png]]` finds the asset.
5. **Unresolved:** `resolved: null`. If some note's `title` equals `T` under the folding rule, each such path is recorded as a `title-match:<path>` warning — the repair hint for the future `link-repair` skill.

### 6.3 Case mismatches

Any difference between the link text and the actual filename/path casing on a resolved link records the warning `case-mismatch` — the repo lives on case-sensitive filesystems where such links are latent breakage even though Obsidian resolves them.

### 6.4 Backlinks and warnings

- **Backlinks:** for every resolved note-target link (embed or not), the containing note's path is added to the target's `backlinks` (sorted, de-duplicated).
- Per-link `warnings` carry `ambiguous`, `case-mismatch`, and `title-match:<path>` entries; `validate` maps them to severities (§10).

## 7. Body extraction

### 7.1 Headings

ATX headings only: 1–6 `#` characters at the start of a line (up to 3 leading spaces allowed), followed by a space and text; trailing closing-`#` sequences are stripped. Recorded in document order as `{level, line, text}` (`line` per §3, needed for `search` heading hits). Setext (underline) headings are not recognized (§11); the vault uses ATX exclusively. Exclusion zones (§5.2) apply.

### 7.2 Inline tags

A body tag is `#` immediately followed by one or more of `[A-Za-z0-9_/-]`, containing **at least one non-digit** character, and preceded by start-of-line or whitespace (so URLs like `…/page#anchor` never match; `# Heading` fails because the space stops the match). Exclusion zones apply. Stored in `bodyTags` sorted and de-duplicated, without the `#`.

**Effective tags** of a note = frontmatter `tags` ∪ `bodyTags`. Query filters (§9) match against the union; `validate`'s tag checks apply to **frontmatter tags only** (§10.2); the index stores the two sources separately.

## 8. Index schema and determinism

### 8.1 Shape

```json
{
 "assets": ["08_Assets/example.png"],
 "notes": {
  "00_Meta/prd.md": {
   "backlinks": ["AGENTS.md"],
   "bodyTags": [],
   "frontmatter": {"tags": ["type/meta"], "title": "PRD", "updated": "2026-08-11"},
   "frontmatterErrors": [],
   "headings": [{"level": 1, "line": 8, "text": "PRD"}],
   "links": [
    {"display": null, "embed": false, "fragment": null, "line": 12,
     "placeholder": false, "raw": "[[AGENTS]]", "resolved": "AGENTS.md",
     "target": "AGENTS", "warnings": []}
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
 "schemaVersion": 1
}
```

Field meanings are as defined in §3–§7 and §17 (`tasks`). Every field is always present (empty lists/`null` rather than omitted keys) so the shape is predictable for consumers reading the JSON directly — the committed index is the primary discovery mechanism per PRD §9.4, usable without running Python.

`schemaVersion` bumps on any breaking change to this shape; consumers must check it.

### 8.2 Deterministic serialization

The committed index must be a **pure function of tracked file contents** — a fresh CI clone rebuild must be byte-identical to the committed copy. Hence the index corpus in §2, plus:

- Serialized exactly as Python's `json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True)` plus a single trailing `\n`, written as UTF-8 with LF endings. Only strings, integers, booleans, `null`, objects, and arrays appear (no floats), so output is stable across Python ≥ 3.10. (The §8.1 example shows the real emitted key order: `sort_keys` puts `assets` < `notes` < `schemaVersion`.)
- Object keys sort via `sort_keys`; every array is either **document order** (links, headings — deterministic from file content) or **explicitly sorted** (assets, backlinks, bodyTags, and the `notes` keys via key sort).
- **No timestamps, no mtimes, no absolute paths, no environment data, no tool-version stamp.** In particular, **file mtime is excluded** even though the plan's extraction-scope bullet listed it: git does not preserve mtimes, so a fresh clone would always produce a different index and the CI freshness check could never pass. The `recent` command's mtime tiebreak stats the working tree at query time instead (§9). *(Deviation from the plan — flagged for owner review, §12.)*
- `sizeBytes` is the UTF-8 byte length of the **normalized** text (§3; byte-level normalization for `not-utf8` files), not the on-disk size, for the same reason.
- M5.4 must ship a `.gitattributes` entry marking `10_Agents/tools/brain/vault-index.json` as `-text`, so `core.autocrlf=true` checkouts (the Git-for-Windows default) don't smudge the committed copy to CRLF and fail every `--check-index` byte-compare.
- **Merge driver (M8.6, issue #25):** `.gitattributes` additionally marks the two committed generated files — `10_Agents/tools/brain/vault-index.json` and `.vscode/second-brain.code-snippets` — with `merge=regenerate`. The driver is defined per clone as `git config merge.regenerate.driver true` (the `true` command exits 0 leaving `%A` = ours): merges of generated content resolve keep-ours, and **correctness comes from regeneration, not resolution** — the `.githooks/post-merge` hook re-runs `index` and snippet generation best-effort immediately after a merge, the pre-commit hook regenerates on the next commit, and CI freshness checks catch any skip. Clones without the driver configured degrade to a normal conflict plus the documented fallback recipe (`10_Agents/solutions/vault-tooling/index-merge-conflicts.md`). Any future committed generated file adopts the same attribute.

### 8.3 Restricted-note reduction (issue #17)

A note whose **frontmatter tags** contain `restricted/private` (bodyTags are informal and never trigger this, matching §10.2's posture) is **reduced** in the committed index rather than excluded — decided 2026-08-11 per the accepted triage recommendation on issue #17. The committed index is the vault's most-copied artifact (PRD §9.4); without reduction it would re-leak the very content the tag marks.

- **Kept:** path (the `notes` key), `title`, `frontmatter` (including `tags` — consumers must be able to see *why* the record is reduced), `updated`, `sizeBytes`, `frontmatterErrors`, `links`, and `backlinks`. Links and backlinks stay so restricted notes remain discoverable and the §10.2 containment check has structure to work with — but only their **structure**: on a reduced record each link's `display` and `fragment` are nulled and `raw` is rewritten to the canonical `[[target]]` / `![[target]]` form, so alias text and verbatim body markup (which are body prose) never reach the committed index.
- **Dropped (emptied/nulled, not omitted — §8.1's every-field-present shape holds, so no `schemaVersion` bump):** `headings: []`, `bodyTags: []`, and `tasks: []` (issue #28: task text and metadata are body prose) — the body-derived fields the index would otherwise publish — plus the link-record prose fields above.
- The reduction applies to the **committed index only**: `brain index` output and the `validate --check-index` rebuild (both serialize the reduced form, so the byte-compare stays consistent). Query commands (§9) keep the full in-memory record — they run against the local working tree, where the note body sits right beside them; reducing them would cost the owner `search`/`show` utility while protecting nothing.
- This is a **sanctioned, tag-driven exception** to the spirit of the §15.1 config/index invariant: index output varies with note *content* (the tag), never with `00_Meta/config.yaml`. The committed index remains a pure function of tracked file contents (§8.2).
- Honest framing (conventions § restricted/private): reduction is leak resistance, not access control — the note body is still in the repo, readable by anything that reads files.

## 9. CLI command semantics

Invocation: `python 10_Agents/tools/brain/brain.py <command> [args]` (a shell alias is documented in the tool README at M5.5). Every command accepts `--json`; human output is plain text. Query commands **rebuild the index in memory from the working corpus on every run** (the vault is small; stale reads are worse than the milliseconds) — the committed `vault-index.json` exists for consumers who read JSON without running Python and is written only by `index`. Exit codes: `0` success, `1` operational error (bad argument, note not found); `validate` alone uses the three-code contract in §10.4.

Where a command takes a `<note>` argument, it accepts a vault-relative path or a bare name; the argument gets §5.1 target normalization (one trailing `.md` stripped — so `brain show 00_Meta/prd.md` works) and then the §6 ladder.

- **`index`** — rebuild from the index corpus and write `vault-index.json` per §8; print the path written.
- **`list`** — note paths, sorted. Filters (ANDed): `--dir PREFIX` (path prefix), `--tag TAG` repeatable (effective-tag exact match; a trailing `/*` matches the whole namespace), `--type X` (sugar for `--tag type/X`). JSON: array of `{path, title, updated}`.
- **`search <query>`** — case-insensitive substring over title, heading texts, and body (body searched in full, code blocks included); combinable with `--tag`. Human: `path:line: snippet` for body/heading hits, `path: title: <title>` for title hits. JSON: array of `{path, field, line, snippet}` (`field` ∈ `title` | `heading` | `body`; `line` is `null` for title hits).
- **`links <note>`** — the note's outgoing links (with resolution state and warnings), its backlinks, and its unresolved targets. JSON: `{path, outgoing, backlinks, unresolved}` drawn from the index record.
- **`tags`** — effective-tag usage counts grouped by namespace (text before the first `/`; tags without `/` group under `(none)`), sorted by namespace then value. JSON: `{namespace: {value: count}}`.
- **`show <note>`** — the full §8.1 record for one note (human output: a readable summary of the same fields).
- **`recent [n]`** — `n` (default 10) notes by `updated` descending; ties broken by working-tree mtime descending, then path ascending; notes with `updated: null` sort last (per PRD §15, `updated` is the primary recency signal and day-granular). JSON: array of `{path, title, updated}`.
- **`validate`** — §10.
- **`curate`** — the §14 re-review signals as one report: expired, missing `expires:`, expires beyond the one-year cap, oversized, stale (days-old weighted by backlink count, sorted worst-first), orphans, unreferenced `08_Assets/` files; `--check-urls` additionally probes source URLs over the network (opt-in only; never runs pre-commit). JSON: one sorted array per signal.
- **`context`** — each bootstrap doc's byte size against its §14 budget, plus the total; missing docs report `null`. JSON: `{docs, totalBudget, totalBytes}`.
- **`report`** — §16: the five-section vault-health synthesis (stale-active, orphans, Inbox aging, tag drift, unresolved links); `--since YYYY-MM-DD` scopes the two change-attributable sections per §16.3. Thresholds come from the `report` config key (§15.3) with built-in defaults.
- **`tasks`** — §17.3: checkbox tasks across the vault, filterable by `--open`, `--due <date|today>`, `--overdue`, `--project PREFIX`.

## 10. Validate semantics

### 10.1 Rule sources

Tag namespace membership is read **at runtime** from the authoritative table in [[00_Meta/conventions#Tag Namespaces]] — `brain` hardcodes no taxonomy. Mechanically: take the first markdown table after the `## Tag Namespaces` heading; skip the header and separator rows; for each data row, the **namespace** is the first backtick-quoted token in column 1 with any trailing `/*` removed; if column 3's cell text begins with `Free-form` (case-insensitive), the namespace is **open** (any value passes); otherwise the namespace is **closed** and its value list is the backtick-quoted tokens in column 3. Applied to the current table this yields closed `audience`, `type`, `workflow`, `status` and open `topic` — and if the owner adds or re-marks a namespace, `brain` follows the table with no code change. A missing or unparseable table, or a row yielding no namespace, is a validate **error** (`conventions-table-unreadable`), never a silent pass.

### 10.2 Checks

**Errors** (exit 1): missing frontmatter; missing/null `title` or `updated`; a missing, null, or **empty** `tags` list (`tags: []` declares no tags and fails the same `missing-tags` check; the §10.3 template-placeholder exemption is per-value, and an empty list has no values to exempt, so it fires in `09_Templates/` too); `not-readable` (§3 read failure — `validate` reports it as the note's only finding, suppressing the derived frontmatter-field checks, and `not-utf8` behaves the same way; every other command skips the file); `invalid-updated`; any §4 `frontmatterErrors` entry except the warning-mapped ones below; a frontmatter tag not slash-delimited, in a namespace absent from the conventions table, or (for closed namespaces) not in the value list — **frontmatter tags only; `bodyTags` are informal and never checked**; a filename-convention violation; an unresolved wikilink (placeholder links exempt); `path-collision` — two corpus paths equal under the §6 folding rule, which cannot co-exist on default macOS/Windows filesystems. Secret-scanning findings (§10.5) are also errors.

**Filename convention:** applies to the **basename** of note files only (directories and assets are not checked). A note basename must match `^[a-z0-9]+(-[a-z0-9]+)*\.md$` — all-digit segments are allowed, so dated notes like `2025-01-15.md` and `2024-01-review.md` pass. Exceptions per [[00_Meta/conventions]]: `AGENTS.md`, `CLAUDE.md`, `README.md` at any level; periodic tokens `YYYY-W##-review.md` and `YYYY-Q#-review.md`; `SKILL.md` inside `10_Agents/skills/` (Agent Skills format, M6).

**Agent Skills contract (`10_Agents/skills/`, added at M6 per the implementation plan):** every skill directory (a direct child of `10_Agents/skills/` containing notes) must hold a `SKILL.md` whose frontmatter carries — in addition to the vault contract — an Agent Skills `name` equal to the directory name (`skill-name-mismatch`) and a non-empty `description` string (`skill-missing-description`); a skill directory without a `SKILL.md` is `skill-missing`. All three are errors.

**Warnings** (exit 2 if no errors): `ambiguous` links; `case-mismatch` links; `tags-not-a-list`; `duplicate-key`; `restricted-link` — a note **without** `restricted/private` in its frontmatter tags links to or embeds a resolved note **with** it (context bleed, issue #17: the linking note's prose tends to carry a summary of what it links; restricted → restricted links are clean). Advisory by design — a warning, never an error, because linking restricted content can be legitimate; the duty not to quote/summarize it lives in [[10_Agents/docs/operating-rules]]. `missing-author` — a `02_Inbox/` note whose frontmatter tags include **both** `audience/agent` and `workflow/draft` but whose frontmatter has no non-empty `author:` value (issue #18 provenance; field semantics — harness-level `author:`, optional `session:` reference — are defined in [[00_Meta/conventions]] § Provenance; templates are exempt per the §10.3 placeholder pattern, a placeholder `author:` value counting as present); a `title-match:` hint accompanies its unresolved-link error message. `task-invalid-date` — a date-bearing task emoji whose value is missing or not a real `YYYY-MM-DD` date (§17.2; tasks are informal body content, matching the `bodyTags` posture, so this never blocks a commit; a template task whose text contains `{{` is exempt per the §10.3 placeholder pattern). With the §14 curation gate on: `missing-expires`, `expires-beyond-cap`, `oversized`, `bootstrap-budget`, and `bootstrap-budget-total`. `invalid-expires` (an `expires:` value that is not a real `YYYY-MM-DD`) is an **error**, with the same template-placeholder exemption as `invalid-updated`.

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

The two assignment rules require the value to be *entirely* quoted token characters, and the entropy heuristic requires mixed case plus a digit — so prose, wikilinks, bare git SHAs (lowercase hex has no uppercase), and long URLs (contain `:`/`.`/`?` outside the charset) never flag; tuned to zero false positives on this repo's own tree, which the test suite pins with a repo self-scan.

**Allowlist.** A line is exempt when it carries an HTML comment containing the token `brain:allow-secret-pattern` — marker and pattern on the **same line**. The committed marker is the audit trail: documentation *about* token shapes stays possible, and every suppression is greppable. There is no file- or directory-level allowlist.

**Output.** Findings follow §10.4 (`ERROR <path>:<line> secret-<name>: …`) but the message **never echoes the matched text** — it names the rule and points at the marker escape, so a real credential is not additionally copied into terminals, CI logs, or agent transcripts.

**Backstop.** GitHub-side secret scanning + push protection (issue #24 item 3) is a repository setting owned outside this tool — it catches formats this table doesn't know, including in git history. Tracked separately; `validate` neither depends on nor replaces it.

## 11. Divergences from Obsidian and known limitations

- **No title-based resolution** (deliberate; §6). Title matches become repair hints, not links.
- **No partial path-suffix matching** (`[[to/foo]]` matching `a/to/foo.md`): full path or bare name only — the plan's three-step ladder is the whole ladder.
- Block references (`#^id`) and heading fragments parse but are never verified against the target (deferred, §13).
- Inline code spans are line-scoped; CommonMark multi-line spans are not recognized (§5.2).
- Indented code blocks, HTML comments, and `%%` comments are scanned for links/tags (only fenced blocks and inline spans are excluded).
- Setext headings are not recognized.
- Quoted-scalar escape sequences are not processed (§4.3).
- Ambiguous bare links resolve deterministically (fewest segments, then path order) — an approximation of Obsidian's "shortest path" pick — and always warn, so ambiguity never persists silently.

## 12. Decisions this spec makes beyond the plan (review focus)

1. **mtime is excluded from the index** (plan listed it in extraction scope) — required for the committed-index/CI determinism the plan itself mandates; `recent` stats the working tree live instead. §8.2.
2. **The committed index is built from git-tracked files only** (working corpus ∩ `git ls-files`); query commands see the full working tree. Untracked scratch can never make CI's freshness check fail. §2.
3. **`sizeBytes` measures normalized text**, not on-disk bytes — same determinism argument against `autocrlf` checkouts. §8.2, §3.
4. **Query commands always rebuild in memory** rather than reading the committed index. §9.
5. **Folding-rule matching (NFC + casefold) with `case-mismatch` warnings**; all paths NFC-normalized. §2, §6.
6. **Assets are recorded (path-only)** so `![[embeds]]` can resolve; resolution tries notes first, then assets. §2, §6.2.
7. **Validate's tag checks cover frontmatter tags only**; inline `#tags` are informal. §10.2.
8. **The template-placeholder exemption is per-value**, so real notes in `09_Templates/` (its README) stay fully checked. §10.3.
9. **Warnings never block commits** (exit 2 passes the hook); only errors do. §10.4.
10. **The test-fixture tree is excluded from the corpus**, and M5.4 ships a `.gitattributes` guard for the index file. §2, §8.2.

## 13. Future considerations (out of M5 scope)

- Verifying heading/block fragments against the target's indexed headings.
- Indexing markdown-style relative links (`[text](path)`) — today only wikilinks are the navigation contract.
- Excluding HTML/`%%` comments from extraction.
- ~~A `restricted/*`-aware output filter~~ — adopted 2026-08-11 (issue #17): tag-only `restricted/private`, index reduction in §8.3, `restricted-link` warning in §10.2. Still future: directory-based restriction and finer-grained values, revisited only if tag-only proves insufficient.

## 14. Curation signals (ops plan Phase 4)

Detection lives in `brain`; the judgment lives in the `curate` skill; findings needing owner decisions land as Inbox proposals. Every tunable is a module constant in one block at the top of `brain.py` — `CURATE_MAX_LINES`/`CURATE_MAX_BYTES` (oversized), `CURATE_STALE_DAYS`, `EXPIRES_CAP_DAYS`, the exemption sets, and the `BOOTSTRAP_BUDGETS` map with `BOOTSTRAP_TOTAL_BUDGET`. Policy prose (TTL defaults, what's exempt and why) lives in [[00_Meta/conventions]] § Expiration; the constants are authoritative for values.

- **`expires:`** — optional frontmatter date (`YYYY-MM-DD`). Malformed → `invalid-expires` error (§10.2). Present and past → **expired** (curate report only). More than `EXPIRES_CAP_DAYS` after `updated:` → **expires-beyond-cap**. Absent on a note that should carry one → **missing-expires**; exempt by path: `02_Inbox/` (zero-friction capture; assigned at triage), `02_Outbox/` (ephemeral packets; lifecycle is the archive path), `03_Journal/`, `07_Archives/`, `09_Templates/`, `10_Agents/solutions/`, the changelog, `00_Meta/status.md`, and `CLAUDE.md`; exempt by type tag: `type/decision` (event records, via `EXPIRES_EXEMPT_TYPE_TAGS`). The orphan check uses the path exemptions only — a decision record still wants inbound links.
- **oversized** — normalized size or line count over the constants; exempt `07_Archives/` and the changelog (frozen/append-only content is never a split candidate).
- **stale** — `updated:` older than `CURATE_STALE_DAYS`; score = days-old × (1 + backlink count), sorted worst-first, so heavily-referenced stale notes surface first.
- **orphans** — zero backlinks; exempt the expires-exempt set plus `AGENTS.md`, `CLAUDE.md`, and the root `README.md`.
- **unreferenced assets** — `08_Assets/` files no resolved link or embed points at (only `08_Assets/`: reference configs elsewhere are cited by backticked path, not wikilink).
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
| `write_exceptions` | **implemented** | List of vault-relative directory paths agents may write to **in addition to** the Inbox-first defaults (`02_Inbox/`, `02_Outbox/`, `10_Agents/solutions/` — `AGENT_WRITE_DEFAULT_PREFIXES`). Config only ever widens the set; entries are normalized to a trailing `/`. The enforcement point is `agent_write_allowed(rel, config)`, for harness write-gates and skills; session-scoped carve-outs (onboard-owner, agent-generated skills/tools per PRD §6.2) remain policy prose, not paths. |
| `extension_trust` | **implemented** | VS Code extension trust policy (PRD §6.5): `first-party` (default) or `relaxed`. A documented override consumed by the editor docs ([[06_Resources/vscode-editor-support]]) — `brain` exposes the effective value via `extension_trust(config)` and `brain config`; it drives no `brain` behavior itself. |
| `context` | **implemented** (#12) | Fork context recorded by [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]]'s specialization step: **one scalar**, `personal` (the default when absent) or `work`. Beyond parsing and reporting it — `vault_context(config)` and `brain config` expose the effective value — `brain` acts on it in no way yet: specialization happens at onboarding time by rewriting the periodic templates in `09_Templates/` in place from `09_Templates/variants/`, not at read time, so the key is a record for tooling and future skills, not a switch. |
| `environments` | reserved (#15) | — |
| `modules` | reserved (#32) | — |
| `provenance` | reserved (#18) | — |
| `report` | **implemented** (#16) | Health-report thresholds (§16.4): a one-level nested mapping under `report:` whose subkeys are `stale_days` (stale-active threshold, default `30`) and `inbox_days` (Inbox triage-debt threshold, default `14`). Values are non-negative-integer scalars (digits only — §4.3 stores strings; `report_thresholds(config)` converts). A `null` value or absent subkey means the default; malformed values fall back to the default at read time while `check_config` reports them (§15.4). Consumed by `brain report` only — never by `index`, and it moves no `validate` severity. |
| `sync` | reserved (#26) | — |
| `tasks` | **implemented** (#28) | Task-module settings (§17.4): a one-level nested mapping under `tasks:` whose sole subkey is `carry_over` (`on` \| `off`, default `on`) — whether daily-note instantiation carries yesterday's unchecked tasks into the new note's Backlog section (§17.5). `tasks_carry_over(config)` converts; a `null` value or absent subkey means the default; malformed values fall back to the default at read time while `check_config` reports them (§15.4). Consumed by `daily_note.py` only — never by `index`, and it moves no `validate` severity. |
| `template_version` | reserved (#6) | — |

Reserved keys parse and are **tolerated silently** whatever their shape. **Unknown** keys (neither implemented nor reserved) are tolerated too — forward compatibility — at the cost of a validate **warning** (`config-unknown-key`), never an error.

### 15.4 Validate semantics

All config findings land **on `00_Meta/config.yaml`** as per-file findings in the normal §10.4 shape. **Errors:** every §15.2 parse finding except `config-duplicate-key`; `config-not-readable` / `config-not-utf8`; `config-invalid-value` (an implemented key with the wrong shape — `write_exceptions` not a list, `extension_trust` or `context` not a scalar, `report` or `tasks` not a nested mapping, a known `report` subkey whose value is not a digits-only non-negative integer, or a known `tasks` subkey whose value is not a scalar; an explicit `null` equals absent and is clean); `config-bad-write-exception` (an entry that is not a vault-relative path: empty, absolute, drive-lettered, or containing `..`). **Warnings:** `config-duplicate-key` (last wins, mirroring §4.2); `config-unknown-key` (an unknown top-level key, or an unknown subkey under `report` or `tasks`, reported dotted as `report.<key>` / `tasks.<key>`); `config-missing-directory` (a well-formed `write_exceptions` entry naming no existing directory — legal, since a fork may configure ahead of creating it); `config-unknown-value` (an `extension_trust`, `context`, or `tasks.carry_over` value outside its documented pair).

### 15.5 `config` command

`brain config` (§9 conventions: `--json`, exit 0) prints the **effective** configuration: presence, the raw parsed map, the merged write-exception prefixes (defaults first), the effective `extension_trust`, the effective `context`, the effective task carry-over toggle (§17.4), the reserved-key list, and any findings. It is the non-Python surface of the reader API for harness tasks and scripts.

## 16. Health report (`brain report`) — issue #16

A read-only synthesis of the in-memory index (§9's usual `walk_corpus` + `build_index` — **no new parsing**, no network, no git) into the five vault-health sections below, for the `periodic-review` and `vault-maintenance` skills and the "Brain: Health Report" VS Code task. Exit code is always `0` on success (the report informs; `validate` judges); `1` only for an operational error (a malformed `--since`). Ordering inside every section is deterministic; the human output prints the sections in the order listed here (most-actionable-first).

### 16.1 Sections

All tag reads in this section are **frontmatter tags only** (a bare-scalar `tags:` coerced to one element per §4.5; body `#tags` are informal, mirroring §10.2), and values containing `{{` (template placeholders) are ignored.

1. **Stale-active** (`staleActive`): notes carrying the frontmatter tag `status/active` whose `updated:` is **strictly more than** `stale_days` days (default 30) before today. Notes with `updated: null` cannot be aged and are skipped (`validate` already flags `missing-updated`/`invalid-updated`). Rows `{daysOld, path, title, updated}`, sorted oldest-first (`daysOld` descending, then path).
2. **Orphans** (`orphans`): notes with **zero backlinks and zero outgoing wikilinks** (placeholder links don't count as outgoing) — fully disconnected, per the issue's definition. Excluded as legitimately leaf-like: any note whose basename is `README.md`, `AGENTS.md`, or `CLAUDE.md`, and everything under `07_Archives/` or `09_Templates/`. Sorted path list. (Distinct from `curate`'s inbound-only orphan signal, which serves the curation charter; this section measures disconnection.)
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

Markdown-native checkbox tasks, adopted 2026-08-11 per the accepted triage recommendation on issue #28: **Obsidian Tasks emoji grammar is the canonical inline metadata**, so Obsidian users get the native plugin experience with zero vault changes while `brain` answers the same queries on every other surface. The conventions entry ([[00_Meta/conventions]] § Tasks) carries the human-facing emoji ↔ meaning table and the location rule: tasks live where their context lives (any note); there is no central task file.

### 17.1 Recognition

A task is a list-item checkbox line in the note body: optional leading whitespace (nested subtasks index like any other), a bullet (`-`, `*`, or `+`), one space, `[c]` where `c` is exactly one character, one space, then non-empty text. `c` = space → `status: "open"`; any other character (`x`, `X`, Obsidian custom statuses like `-` or `/`) → `status: "done"`. A bracket pair with no text after it is not a task. The §5.2 exclusion zones apply: detection runs on the **masked** line, so checkboxes inside fenced code blocks or inline code spans never index; the task text is then taken from the **raw** line at the matched offset (masking preserves length), so inline code *within* a real task's text survives verbatim. Blockquoted checkboxes (`> - [ ]`) and ordered-list checkboxes (`1. [ ]`) are not recognized (out of grammar, mirroring Obsidian Tasks' default).

Extraction happens in the same `extract_body` line walk as links, headings, and body tags — **no additional parsing pass** — and each note record carries the results as the `tasks` array (document order). The field addition is purely additive to §8.1 (every field still always present), so `schemaVersion` stays 1.

### 17.2 Task record and emoji metadata

Each task record: `{due, line, malformed, priority, status, text}` — every field always present.

- `line` — 1-based source line (§3). `status` — `"open"` | `"done"` (§17.1).
- **Emoji tokens** are parsed out of the checkbox text and stripped from `text` (whitespace then collapsed to single spaces). Date-bearing emoji — 📅 due, ⏳ scheduled, 🛫 start, ✅ done, ➕ created — take an optionally-space-separated `YYYY-MM-DD` token; ⏫/🔼/🔽 set `priority` `high`/`medium`/`low`; 🔁 takes free text running to the next recognized emoji or end of line. A trailing emoji variation selector (U+FE0F) is tolerated. For a repeated field the **last** occurrence wins (mirroring §4.2's duplicate-key posture).
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

`daily_note.py` (the VS Code daily-note task), when **creating** today's note and the §17.4 toggle is on, copies **yesterday's unchecked task lines** — open checkboxes per §17.1, including nested ones, indentation preserved, fenced-code/inline-code exclusions applied via the shared `brain` parser — verbatim into the end of the new note's `### Backlog` section (before the section's trailing blank lines; if the instantiated template has no such heading, the section is appended). "Yesterday" is calendar yesterday (`today − 1 day`), so month, ISO-week, and year boundaries need no special casing; a missing, unreadable, or task-free yesterday note simply carries nothing. Existing notes are never rewritten — carry-over runs only at instantiation. The weekly-review template instead carries a prompt line pointing at `brain tasks --open` / `--overdue` (live query beats a stale snapshot at week granularity).

**Deferred surfacing (explicitly out of scope here):** VS Code task *views* and web-UI views (#27), notification/overdue digests (#21), external-tracker mirroring (#26 directionality).
