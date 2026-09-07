---
title: "Index Merge Conflicts"
tags:
  - type/solution
  - audience/agent
  - topic/software
updated: 2026-09-07
---

# Index Merge Conflicts

## Status

**Background + fallback.** Since issue #25 the primary mechanism is the `merge=regenerate` git merge driver: `.gitattributes` marks the committed index, compiled bootstrap, snippets, and skill adapters, and clones configured with

```sh
git config merge.regenerate.driver true
```

merge them by keeping ours. `pre-merge-commit` regenerates from the staged snapshot and pauses an automatic merge when fresh output needs recording; run `git commit` to finish. `post-merge` is read-only, and `pre-push` plus automatic CI verify committed freshness. The manual recipe below applies only to clones **without** the driver configured, which degrade to a normal conflict.

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

The index is a pure function of tracked content (spec §8.2), so the regenerated file is correct by construction for whatever the merged tree contains. A conflicted snippets file works the same way: take either side, run `python3 10_Agents/tools/vscode/gen_snippets.py`, and stage the result. A conflicted `00_Meta/BOOTSTRAP.md` likewise: take either side, run `python3 10_Agents/tools/brain/brain.py bootstrap --write`, and stage the result.

## Prevention

- **Install the merge driver** (`git config merge.regenerate.driver true`) so these conflicts never surface — this is now part of the standard per-clone setup alongside `git config core.hooksPath .githooks`.
- Deterministic serialization keeps diffs minimal, so conflicts are rare and always mechanical.
- Keep commits small and pull before writing (PRD §17) — the index diverges less.
- The pre-commit hook generates from staged sources. Automatic merges needing regeneration pause with fresh outputs staged; finish with `git commit`. Pre-push and automatic CI reject stale committed output.

## Related

- `10_Agents/tools/brain/SPEC.md` §8.2 — determinism guarantees and the merge-driver contract
- `.gitattributes` — the `merge=regenerate` mappings
- `.githooks/pre-commit`, `.githooks/pre-merge-commit` — staged regeneration; `.githooks/post-merge`, `.githooks/pre-push` — committed checks
