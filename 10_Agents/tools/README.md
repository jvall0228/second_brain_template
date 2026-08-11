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

## Rules

- Template-shipped tools are canonical (see [[00_Meta/prd]] §9.3); agent-generated tools start `workflow/draft` until the human promotes them.
- Tools must stay dependency-free and deterministic — see the spec of the tool you're changing before touching it.
