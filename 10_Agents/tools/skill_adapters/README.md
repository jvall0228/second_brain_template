---
title: "Project Skill Adapter Generator"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-07
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
Pre-commit builds from a private checkout of the **staged tree**, including
skip-worktree paths. Indexing, validation, and artifacts use shared-only scope.
Unstaged source edits and their staged versions remain separate; owned generated
files are replaced with their staged-source result.

The hook holds Git's real `index.lock` while generators use a private index.
Validation failures cannot modify the live index or generated files. Publication
holds no-follow parent directory descriptors, verifies ownership, quarantines
prior files, and installs with create-if-absent links. A concurrent generated edit
is preserved; an obstructed rollback leaves the original and replacement recovery
evidence in the reported `.precommit-generated-transaction-*` directory. Do not
remove recovery evidence or an existing Git lock while its writer is active.

Git computes automatic merge trees before running `pre-merge-commit`. If the
merge needs regenerated outputs, that hook stages them and **pauses the merge**;
run `git commit` to finish using the fresh index. `post-merge` checks the committed
tree without changing the worktree. `pre-push` checks outgoing committed ref tips,
so refreshing a dirty worktree cannot hide stale committed bytes. The automatic
`generated-consistency` workflow repeats read-only checks on pushes and PRs;
automatic `tool-tests` runs behavioral tests, validation, and the adoption smoke
test on Linux and macOS; manual `validate` retains explicit repair. Making that CI
status mandatory for GitHub merges requires repository branch protection.

Safe hook publication currently requires POSIX; unsupported runtimes refuse the
commit hook and retain read-only checks. Project verification is
read-only. `harness_setup.py` is also read-only: it verifies repository
surfaces or emits exact external paths/commands for approval, and deliberately
has no apply mode. Optional user-global installation remains separately consented by
[onboard-harness](../../skills/setup/onboard-harness/SKILL.md).
