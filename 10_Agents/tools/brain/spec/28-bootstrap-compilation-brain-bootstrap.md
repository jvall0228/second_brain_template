---
title: "brain Spec §28 — Bootstrap compilation (`brain bootstrap`, `brain context --for`)"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 28. Bootstrap compilation (`brain bootstrap`, `brain context --for`)

*Section 28 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 28.1 Purpose and output

Every agent session reads the six bootstrap docs (AGENTS § Bootstrap Sequence) — six file reads, in a fixed order, before any work. `brain bootstrap` compiles them into one file, `00_Meta/BOOTSTRAP.md`, so a harness that loads files one at a time can load one. The compiled file is a **pure function of the six source files' bytes** — no clock, no environment, no git — so equal sources always produce equal bytes.

Order is `BOOTSTRAP_ORDER`: `AGENTS.md`, `01_Profile/NOW.md`, `01_Profile/PREFERENCES.md`, `00_Meta/CONVENTIONS.md`, `00_Meta/INDEX.md`, `01_Profile/DEFAULTS.md`. Per source: frontmatter is stripped; ATX headings (the §7 grammar — up to three leading spaces, levels 1–5) outside fenced code are demoted one level (`#` → `##`; level 6 stays); relative link destinations outside fenced code and inline code spans are re-relativized from the source's directory to `00_Meta/`, fragments and titles preserved; leading and trailing blank lines are trimmed. The compiler reuses the vault's own Markdown machinery rather than a private grammar: the §5.2 fence scanner (three-, four-, and mixed-character fences, indented fences), exact-length code-span masking (a ``double`` span protects a single backtick inside it), and the §5 inline-link parser (optional titles, `<angle>` destinations, escaped brackets, percent-encoded paths). Left untouched, byte for byte: external and protocol-relative (`//host/x`) URLs, fragment-only links, `{{placeholder}}` links, root-relative (`/x`) destinations, destinations that escape the vault root (`../x` from `AGENTS.md`), and anything the parser rejects. Relativization is anchored at the vault root, never at the process working directory, so the same sources render the same bytes from any `cwd`. If the body then starts with the demoted H1, the line `*Source: [<path>](<00_Meta-relative path>)*` is inserted after it; otherwise a `## <title>` heading and that line are prepended. Sections join with one blank line.

The file's frontmatter is fixed: `title: "Bootstrap"`, tags `type/meta`, `audience/agent`, `workflow/canonical`, `updated:` = the lexicographic maximum of the sources' `updated:` values (the newest source date — deterministic, never today), `generated: brain-bootstrap-v1`, `content-digest:` = SHA-256 of the joined body. A short generated-file notice follows the H1.

## 28.2 Corpus status, freshness, and ownership

`00_Meta/BOOTSTRAP.md` is **pruned from the working corpus** (§2) exactly like the index: it is never indexed, searched, task-extracted, validated, or secret-scanned as a note, and it is never a valid link target (a link to it is `unresolved-link`; AGENTS and INDEX name it in backticks). This is what makes a verbatim copy of six notes safe — nothing is counted twice.

`brain bootstrap` prints the rendered bytes; `--check` prints `<path>: fresh|stale|missing (<size> / <budget> bytes)` and exits 1 when the committed bytes differ, the file is absent, or the size exceeds `BOOTSTRAP_TOTAL_BUDGET` (the same 32 KiB cap as the six sources combined). The rendered file is **not** guaranteed smaller than its sources — dropping frontmatter saves less than link rewriting (`x.md` → `../01_Profile/x.md`), the generated header, and the per-section source lines add — so the cap is enforced on the rendered bytes independently of the §14 per-source budgets: `--write` **refuses** an over-budget render (prints `refused … OVER BUDGET` to stderr, leaves any committed file untouched, exits 1); otherwise it writes only when the bytes differ and prints `written` or `unchanged`. JSON carries `{budget, fresh, overBudget, path, sizeBytes, sources: [{path, sizeBytes, title, updated}], state[, write]}`. A missing or undecodable source is an error (exit 1) — the file is never written partially.

Ownership: `--write` is the only writer; hand edits are foreign. The pre-commit hook regenerates it, runs `--check` on the result, and stages it before the index (`.githooks/pre-commit`); the post-merge hook regenerates it; `.gitattributes` gives it the `regenerate` merge driver; the hook transaction lists it among the generated paths; CI regenerates it, runs `--check`, and commits it with the other generated files. `brain context` appends the compiled file's size and state after the totals line. Unlike the index (§2 known caveat), unstaged source edits never ride into the compiled file: the pre-commit hook refuses to run while any of the six sources has unstaged or untracked changes, exactly as it does for canonical skill files, so the staged `BOOTSTRAP.md` is always a function of the staged sources.

## 28.3 Skill-scoped context (`brain context --for <skill>`)

Reports what one run of a skill loads, so skill authors can see the context tax of a `## References` section. `<skill>` is a directory name under `10_Agents/skills/` at any depth (`triage-inbox`, or a skill grouped one level down); the first match in `10_Agents/skills/<skill>/SKILL.md`, then sorted deeper matches, wins; none is an error. Output: the six bootstrap docs (path, size, title), the `SKILL.md` row, and one row per **existing note** the skill's `## References` section names — the section is found with the §7 heading grammar and ends at the next level-1 or level-2 heading; inside it, inline Markdown links (titles and `<angle>` destinations included) are parsed with the §5 parser over the §5.2 exclusion zones and resolved from the skill's directory, and single-backtick-quoted paths ending in `.md` are taken vault-relative; fenced code and multi-backtick spans are examples, never references — in first-mention order, deduplicated, the skill itself excluded; targets that are not corpus notes (directories, URLs, prose) are silently skipped. `totalBytes` sums all three groups. JSON: `{bootstrap, references, skill, totalBytes}`. Read-only; walks the all-clone corpus like `validate`, so it never needs an environment selection.
