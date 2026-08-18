---
title: "brain — Vault Index CLI"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-18
expires: 2027-08-11
---

# `brain` — Vault Index CLI

Zero-dependency CLI (Python 3.10+, stdlib only) that indexes every note in the vault and enforces its conventions. The behavior contract is [spec](SPEC.md) (canonical); this README is usage only.

## Invocation

```
brain <command> [options]
```

From a clean checkout, use the repository resolver:

```text
./brain <command> [options]       # POSIX
brain.cmd <command> [options]    # Windows
```

Universal long-form fallback: `python3 10_Agents/tools/brain/brain.py <command>
[options]`. `brain install` previews a managed PATH copy; add `--apply` only
after reviewing its exact target and external ownership manifest. It never
edits shell startup files.

Every command accepts `--json` for machine-readable output, `--vault PATH` to override vault-root autodetection, and `--env current|SLUG` for environment selection. Where a command takes a `<note>`, both bare names (`prd`) and vault paths (`00_Meta/PRD.md`) work.

## Commands

| Command | Does |
|---------|------|
| `index` | Rebuild and write the committed `vault-index.json` (git-tracked files only) |
| `list` | Note paths; filters: `--dir PREFIX`, `--tag TAG` (repeatable; `type/*` matches a namespace), `--type X` |
| `search <query>` | Case-insensitive substring over titles, headings, and body. `--semantic` ranks whole notes by embedding similarity instead (spec §18.4), degrading to keyword search on a vectorless vault; `--query-vector` reads the query embedding from stdin, `--top N` caps results |
| `links <note>` | Outgoing links, backlinks, and unresolved targets for one note |
| `projects` | Canonical active Project inventory with all Areas, targets, criteria/overdue attention, and rollup drift/blockers (spec §27). `--write-rollups` compare-and-swap updates only Area `## Active Projects` sections and preserves concurrent owner edits |
| `archive-project <slug>` | Preview the exact approved whole-directory move/link plan (spec §27.4; use `--json` for every row/digest). `--write --approve-archive` requires a clean tree, repairs links, stages plan-bound blobs, reindexes, validates, and rolls back recognized failures; `--recover` authenticates interrupted evidence or reports that owner inspection is required |
| `aymt` | Deterministic local Actions You May Take brief (spec §23). Preview is read-only; `--json` explains scores and selection, `--check` verifies `00_Meta/AYMT.md` without writing, and explicit `--write` updates only the recognized generated file. Optional `--github-input PATH\|-` accepts a strict sanitized snapshot; brain never invokes GitHub or the network |
| `home` | Deterministic local Home (spec §24) built from structured AYMT plus safe tracked tasks, Inbox, active work, reviews, current state, health, environment metadata, and navigation. Preview/JSON/check are zero-write; explicit `--write` updates only recognized generated `00_Meta/HOME.md`. Optional `--github-input PATH\|-` affects only AYMT actions; brain never invokes GitHub or the network |
| `artifacts` | Deterministic offline link graph and health dashboard (spec §25). Preview/`--json` are read-only; `--check` verifies the exact generated inventory; `--write` updates only recognized files under `08_Assets/artifacts/`; `--open` opens fresh local HTML. `--as-of YYYY-MM-DD` controls the source timestamp |
| `notify` | Push-only owner notification boundary (spec §26). `--setup` writes ignored selected-environment policy but never sends; `--check` inspects it; `--input PATH\|-` previews by default. Actual delivery is limited to explicit local `--deliver-file --approve-private-send`; real-provider payloads are formatting-only pending the owner's private-destination choice and a test-send implementation |
| `tags` | Tag usage counts grouped by namespace |
| `show <note>` | The full index record for one note |
| `recent [n]` | Notes by `updated:` descending (default 10) |
| `validate` | Convention checks plus secret scanning (`secret-*` rules, spec §10.5; per-line escape: an HTML comment containing `brain:allow-secret-pattern`); exit 0 clean / 1 errors / 2 warnings. `--check-index` also verifies the committed index is fresh |
| `curate` | Re-review signals: expired / missing / over-cap `expires:`, oversized, stale (backlink-weighted), orphans, unreferenced assets. `--check-urls` adds network URL probes (opt-in; never pre-commit) |
| `context` | Bootstrap docs' sizes against their context budgets (spec §14; tunables live in one constants block in `brain.py`) |
| `config` | Effective vault config: `00_Meta/config.yaml` merged over built-in defaults — agent write-exception prefixes, VS Code extension trust, fork context, report thresholds (spec §15). The file is optional; absence means pure defaults. `validate` reports malformed or unknown config content as per-file findings on it |
| `report` | Vault-health synthesis (spec §16): stale-active notes, fully-disconnected orphans, Inbox aging buckets, tag drift vs the conventions taxonomy, unresolved-link count. `--since YYYY-MM-DD` scopes tag drift and unresolved links to notes updated in the review period. Thresholds come from the `report` config key (`stale_days`, `inbox_days`) |
| `tasks` | Checkbox tasks across the vault (spec §17; Obsidian Tasks emoji metadata — 📅 due, ⏫/🔼/🔽 priority). Filters: `--open`, `--due <YYYY-MM-DD\|today>`, `--overdue`, `--project PREFIX`. Ordered due-date first (undated last), then path, then line |
| `embed` | Maintain the gitignored semantic-search embeddings sidecar (`vault-embeddings.json`, spec §18): `--stdin-json` ingests precomputed vectors, `--local` embeds with the optional `sentence-transformers` model, `--status` reports coverage. Restricted/private notes never enter the sidecar |
| `remote-safety` | Redacted, fail-closed preflight before personal-data connector reads (spec §19). Verifies every push target is private and non-template; `--acknowledge-unknown` is invocation-only and never bypasses public/template. Add `--persist` for capture/write flows: no-push repositories are local-only, so that requested operation is blocked before the connector |
| `env detect\|list\|migrate` | Detect current hashed identity, list metadata-only environment records, or preview an exact legacy-directory migration (spec §20). Selection is `--env` > `SECOND_BRAIN_ENV` > ignored selector > unique fingerprint and fails closed on ambiguity/no match |
| `install` | Preview managed PATH installation (spec §21). `--apply` writes; `--doctor` diagnoses; `--uninstall` previews removal and combines with `--apply` to remove only a recognized artifact. `--target` and `--state-file` are explicit path overrides |

## The committed index

`vault-index.json` is committed so agents can read structured vault data **without running anything** — per note: frontmatter, headings, links with resolution state, backlinks, body tags. Check `schemaVersion` before consuming. The pre-commit hook (`.githooks/pre-commit`, installed via `git config core.hooksPath .githooks`) regenerates it on every commit and blocks commits with validation errors; CI (`.github/workflows/validate.yml`) re-checks both on push.

## Tests

```
python3 10_Agents/tools/run_tests.py
```

The runner is the canonical entrypoint for every tool suite (see [README](../README.md)); plain `unittest discover -s 10_Agents/tools/brain/tests` still works for this suite alone. Fixture mini-vaults under any `10_Agents/tools/*/tests/` tree are excluded from the real corpus by design (spec §2).
