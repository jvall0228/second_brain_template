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
| `search <query>` | Case-insensitive substring over titles, headings, and body |
| `links <note>` | Outgoing links, backlinks, and unresolved targets for one note |
| `tags` | Tag usage counts grouped by namespace |
| `show <note>` | The full index record for one note |
| `recent [n]` | Notes by `updated:` descending (default 10) |
| `validate` | Convention checks plus secret scanning (`secret-*` rules, spec §10.5; per-line escape: an HTML comment containing `brain:allow-secret-pattern`); exit 0 clean / 1 errors / 2 warnings. `--check-index` also verifies the committed index is fresh |
| `curate` | Re-review signals: expired / missing / over-cap `expires:`, oversized, stale (backlink-weighted), orphans, unreferenced assets. `--check-urls` adds network URL probes (opt-in; never pre-commit) |
| `context` | Bootstrap docs' sizes against their context budgets (spec §14; tunables live in one constants block in `brain.py`) |
| `config` | Effective vault config: `00_Meta/config.yaml` merged over built-in defaults — agent write-exception prefixes, VS Code extension trust (spec §15). The file is optional; absence means pure defaults. `validate` reports malformed or unknown config content as per-file findings on it |

## The committed index

`vault-index.json` is committed so agents can read structured vault data **without running anything** — per note: frontmatter, headings, links with resolution state, backlinks, body tags. Check `schemaVersion` before consuming. The pre-commit hook (`.githooks/pre-commit`, installed via `git config core.hooksPath .githooks`) regenerates it on every commit and blocks commits with validation errors; CI (`.github/workflows/validate.yml`) re-checks both on push.

## Tests

```
python3 10_Agents/tools/run_tests.py
```

The runner is the canonical entrypoint for every tool suite (see [[10_Agents/tools/README]]); plain `unittest discover -s 10_Agents/tools/brain/tests` still works for this suite alone. Fixture mini-vaults under any `10_Agents/tools/*/tests/` tree are excluded from the real corpus by design (spec §2).
