---
title: "Solutions: Vault Tooling"
tags:
  - type/meta
  - audience/agent
updated: 2026-08-28
---

# Solutions: Vault Tooling

Solved problems involving the vault's own tooling — the `brain` CLI, the committed index, the pre-commit hook, and CI.

- [Index Merge Conflicts](index-merge-conflicts.md) — never hand-merge `vault-index.json`
- [Environment Selection Fails: no-fingerprint-match](environment-selection-no-fingerprint-match.md) — select explicitly with `--env <slug>`; don't chase container fingerprints
