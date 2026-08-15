---
title: "Index Merge Conflicts"
tags:
  - type/solution
  - audience/agent
  - topic/software
updated: 2026-08-11
---

# Index Merge Conflicts

## Status

**Background + fallback.** Since issue #25 the primary mechanism is the `merge=regenerate` git merge driver: `.gitattributes` marks both committed generated files (`10_Agents/tools/brain/vault-index.json` and `.vscode/second-brain.code-snippets`), and clones configured with

```sh
git config merge.regenerate.driver true
```

merge them cleanly by keeping ours — correctness comes from regeneration (`.githooks/post-merge` rebuilds both immediately; the pre-commit hook and CI freshness checks are the backstop). The manual recipe below applies only to clones **without** the driver configured, which degrade to a normal conflict.

## Problem

Two branches both regenerated `10_Agents/tools/brain/vault-index.json` (the pre-commit hook does it on every commit), and merging them conflicts inside the JSON.

## Symptoms

- Merge conflict markers in `vault-index.json` (or `.vscode/second-brain.code-snippets`)
- `brain validate --check-index` failing after a merge with "stale index"
- CI failing on index freshness right after a merge commit

## Solution (fallback, when the driver is not configured)

**Never hand-merge the index — it is generated output.** Resolve the *notes*, then regenerate:

```sh
# resolve conflicts in the .md files normally, then:
git checkout --theirs 10_Agents/tools/brain/vault-index.json  # any side; it's about to be replaced
python3 10_Agents/tools/brain/brain.py index
git add 10_Agents/tools/brain/vault-index.json
python3 10_Agents/tools/brain/brain.py validate
```

The index is a pure function of tracked content (spec §8.2), so the regenerated file is correct by construction for whatever the merged tree contains. A conflicted snippets file works the same way: take either side, run `python3 10_Agents/tools/vscode/gen_snippets.py`, and stage the result.

## Prevention

- **Install the merge driver** (`git config merge.regenerate.driver true`) so these conflicts never surface — this is now part of the standard per-clone setup alongside `git config core.hooksPath .githooks`.
- Deterministic serialization keeps diffs minimal, so conflicts are rare and always mechanical.
- Keep commits small and pull before writing (PRD §17) — the index diverges less.
- The pre-commit hook regenerates on every commit, and the post-merge hook regenerates right after a merge, so a clone with hooks installed self-heals.

## Related

- `10_Agents/tools/brain/SPEC.md` §8.2 — determinism guarantees and the merge-driver contract
- `.gitattributes` — the `merge=regenerate` mappings
- `.githooks/pre-commit`, `.githooks/post-merge` — the regeneration hooks
