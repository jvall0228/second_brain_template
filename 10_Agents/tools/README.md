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
- [[10_Agents/tools/vscode/README|vscode]] — scripts behind the VS Code editor surface ([[00_Meta/prd]] §6.5): template-synced snippet generation (hook-enforced) and daily-note creation, both wired to `.vscode/tasks.json`.
- `adopt_check.py` — the adopter-flow smoke test (issue #20): replays the root README's "Adopt this template" steps in a scratch copy — delete the seeded examples, dumb-fill `01_Profile/`, write a first Inbox capture — and requires `brain validate` to stay at zero errors. The delete list is data-driven from `adopt_examples.json` and cross-checked against the README so the two can't drift; CI runs it on every push, and its unit tests live in `brain/tests/test_adopt_check.py` (single-script tool, shared suite home).

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

- Template-shipped tools are canonical (see [[00_Meta/prd]] §9.3); agent-generated tools start `workflow/draft` until the human promotes them.
- Tools must stay dependency-free and deterministic — see the spec of the tool you're changing before touching it.
