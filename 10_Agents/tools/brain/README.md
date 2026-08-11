---
title: "brain — Vault Index CLI"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# `brain` — Vault Index CLI

Zero-dependency CLI (Python 3.10+, stdlib only) that indexes every note in the vault and enforces its conventions. The behavior contract is [[10_Agents/tools/brain/spec]] (canonical); this README is usage only.

## Invocation

```
python3 10_Agents/tools/brain/brain.py <command> [options]
```

Convenient shell alias (add to your shell profile, adjusting the path):

```sh
alias brain='python3 "$(git rev-parse --show-toplevel)/10_Agents/tools/brain/brain.py"'
```

Every command accepts `--json` for machine-readable output and `--vault PATH` to override vault-root autodetection. Where a command takes a `<note>`, both bare names (`prd`) and vault paths (`00_Meta/prd.md`) work.

## Commands

| Command | Does |
|---------|------|
| `index` | Rebuild and write the committed `vault-index.json` (git-tracked files only) |
| `list` | Note paths; filters: `--dir PREFIX`, `--tag TAG` (repeatable; `type/*` matches a namespace), `--type X` |
| `search <query>` | Case-insensitive substring over titles, headings, and body. `--semantic` ranks whole notes by embedding similarity instead (spec §18.4), degrading to keyword search on a vectorless vault; `--query-vector` reads the query embedding from stdin, `--top N` caps results |
| `links <note>` | Outgoing links, backlinks, and unresolved targets for one note |
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
| `remote-safety` | Redacted, fail-closed preflight before personal-data connector reads (spec §19). Verifies every push target is private and non-template; `--acknowledge-unknown` is invocation-only and never bypasses public/template. No-push repositories are local-only and cannot persist connector results |

## The committed index

`vault-index.json` is committed so agents can read structured vault data **without running anything** — per note: frontmatter, headings, links with resolution state, backlinks, body tags. Check `schemaVersion` before consuming. The pre-commit hook (`.githooks/pre-commit`, installed via `git config core.hooksPath .githooks`) regenerates it on every commit and blocks commits with validation errors; CI (`.github/workflows/validate.yml`) re-checks both on push.

## Tests

```
python3 10_Agents/tools/run_tests.py
```

The runner is the canonical entrypoint for every tool suite (see [[10_Agents/tools/README]]); plain `unittest discover -s 10_Agents/tools/brain/tests` still works for this suite alone. Fixture mini-vaults under any `10_Agents/tools/*/tests/` tree are excluded from the real corpus by design (spec §2).
