---
title: "Agent Tools"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Agent Tools

Executable tools that give agents structured access to the vault. Tools here are harness-agnostic: plain scripts with no third-party dependencies, callable from any environment (and from skills, once `10_Agents/skills/` lands at M6).

## Contents

- [[10_Agents/tools/brain/README|brain]] — the vault index CLI: query commands plus `validate`, backing the committed `vault-index.json` and the pre-commit hook. Its behavior contract is [[10_Agents/tools/brain/spec]].
- [[10_Agents/tools/vscode/README|vscode]] — scripts behind the VS Code editor surface ([[00_Meta/PRD]] §6.5): template-synced snippet generation (hook-enforced) and daily-note creation, both wired to `.vscode/tasks.json`.
- [[10_Agents/tools/skill_adapters/README|skill adapters]] — deterministic, hook/CI-enforced text adapters exposing canonical skills at `.agents/skills/` and `.claude/skills/` without workflow duplication or symlinks.
- `adopt_check.py` + `adopt_cleanup.py` — preview/apply the manifest-owned seeded-example bundle with exact deletion inventories/reference edits, source and validator hashes, ignored/untracked/dirty/stale/unmarked refusal, a durable recovery lock (`recover`), transactional rollback, and independently checked post-apply validation. With no subcommand, the CI smoke test replays cleanup, profile fill, and first capture in a scratch copy.

## Testing (TDD convention)

Every tool keeps a stdlib-`unittest` suite in `<tool>/tests/`, and one command runs them all — locally and in CI:

```
python3 10_Agents/tools/run_tests.py        # add -v for verbose
```

The runner discovers every `*/tests/` directory automatically, so a new tool's suite is picked up with no wiring. Rules:

- **Tests land with or before the change.** A behavior change to any tool ships in the same commit as the tests that pin it; bug fixes start from a failing repro test.
- Test module filenames must be unique across tools (unittest imports by module name).
- Suites use only the standard library and temp-directory fixtures — no network, no third-party packages, deterministic.

## Rules

- Template-shipped tools are canonical (see [[00_Meta/PRD]] §9.3); agent-generated tools start `workflow/draft` until the human promotes them.
- Tools must stay dependency-free and deterministic — see the spec of the tool you're changing before touching it.
