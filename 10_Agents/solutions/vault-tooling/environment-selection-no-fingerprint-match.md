---
title: "Environment Selection Fails: no-fingerprint-match"
tags:
  - type/solution
  - audience/agent
  - topic/software
updated: 2026-08-28
---

# Environment Selection Fails: no-fingerprint-match

## Problem

`brain` resolves the current environment in this order: `--env <slug>` > `SECOND_BRAIN_ENV` > the clone-local `.second-brain/environment` selector > machine fingerprint match (SPEC §20.1). On a host whose fingerprint matches no registered environment — fresh containers and remote sessions (the machine id churns per boot), or a machine that was reprovisioned — the fingerprint step fails closed and content commands die with `error: environment selection failed (no-fingerprint-match)`. `brain aymt` / `brain home` collapse the same failure into the opaque `error: AYMT generation failed safely`, which hides the cause. A session that hits this with no remedy in view can run fully degraded, with no `brain list` / `search` / `validate` queries available.

## Symptoms

- `error: environment selection failed (no-fingerprint-match)` from `brain report`, `list`, `search`, `curate`, `context`, and other content commands
- `error: AYMT generation failed safely` from bare `brain aymt` / `brain home` on the same host
- The pre-commit hook path is unaffected: `brain index`, `brain validate`, and `brain artifacts --check` run without environment selection

## Solution

Select the environment explicitly — any of:

```sh
./brain env list                          # see registered slugs
./brain --env <slug> report               # per-invocation flag
export SECOND_BRAIN_ENV=<slug>            # per-shell
echo <slug> > .second-brain/environment   # per-clone selector file (gitignored)
```

## Prevention

- In ephemeral containers, pass `--env <slug>` (or write the selector file at session start) instead of trying to "fix" the fingerprint: container-class machine ids churn per boot, so re-running agent-orientation or refreshing the manifest cannot stick — that remedy is a misdiagnosis for this class. The spec explicitly permits an environment with an empty fingerprint list that is only ever selected explicitly.
- For a recurring container environment, bake the `.second-brain/environment` selector into the environment bootstrap so sessions auto-select without flags.

## Related

- [Environments registry](../../environments/README.md) — selection-order documentation
- `10_Agents/tools/brain/SPEC.md` §20.1 — selection contract and empty-fingerprint allowance
