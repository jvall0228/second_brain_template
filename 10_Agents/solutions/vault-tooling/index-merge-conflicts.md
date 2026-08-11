---
title: "Index Merge Conflicts"
tags:
  - type/solution
  - audience/agent
  - topic/software
updated: 2026-08-11
---

# Index Merge Conflicts

## Problem

Two branches both regenerated `10_Agents/tools/brain/vault-index.json` (the pre-commit hook does it on every commit), and merging them conflicts inside the JSON.

## Symptoms

- Merge conflict markers in `vault-index.json`
- `brain validate --check-index` failing after a merge with "stale index"
- CI failing on index freshness right after a merge commit

## Solution

**Never hand-merge the index — it is generated output.** Resolve the *notes*, then regenerate:

```sh
# resolve conflicts in the .md files normally, then:
git checkout --theirs 10_Agents/tools/brain/vault-index.json  # any side; it's about to be replaced
python3 10_Agents/tools/brain/brain.py index
git add 10_Agents/tools/brain/vault-index.json
python3 10_Agents/tools/brain/brain.py validate
```

The index is a pure function of tracked content (spec §8.2), so the regenerated file is correct by construction for whatever the merged tree contains.

## Prevention

- Deterministic serialization keeps diffs minimal, so conflicts are rare and always mechanical.
- Keep commits small and pull before writing (PRD §17) — the index diverges less.
- The pre-commit hook regenerates on every commit, so a merge commit made with the hook installed self-heals.

## Related

- `10_Agents/tools/brain/spec.md` §8.2 — determinism guarantees
- `.githooks/pre-commit` — the regeneration hook
