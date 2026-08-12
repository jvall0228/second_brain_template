---
title: "Project Skill Adapter Generator"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Project Skill Adapter Generator

`gen_skill_adapters.py` derives checked-in text adapters for
`.agents/skills/` and `.claude/skills/` from the canonical skill directories
under `10_Agents/skills/`. The canonical `name` and `description` are copied
for discovery; the workflow body is never copied. Each adapter carries a
generator version and a relative pointer to its canonical `SKILL.md`.

```sh
python3 10_Agents/tools/skill_adapters/gen_skill_adapters.py
python3 10_Agents/tools/skill_adapters/gen_skill_adapters.py --check
python3 10_Agents/tools/skill_adapters/harness_setup.py project --harness codex --json
python3 10_Agents/tools/skill_adapters/harness_setup.py global-preview --harness codex --home /path/to/home --json
```

The check fails on missing, extra, drifted, colliding, or symlinked output.
Before pre-commit regenerates anything, it snapshots the exact Git index and
the working index/snippets/adapter trees; any later failure or caught
interruption restores both layers byte-for-byte. The post-merge hook also
regenerates adapters, while CI checks freshness before its generated-file backfill. Project verification is
read-only. `harness_setup.py` is also read-only: it verifies repository
surfaces or emits exact external paths/commands for approval, and deliberately
has no apply mode. Optional user-global installation remains separately consented by
[onboard-harness](../../skills/onboard-harness/SKILL.md).
