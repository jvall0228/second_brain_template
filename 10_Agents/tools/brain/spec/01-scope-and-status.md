---
title: "brain Spec §1 — Scope and status"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 1. Scope and status

*Section 1 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

This note is the **M5.0 deliverable**: the concrete parsing, link-resolution, index-schema, and command-semantics rules that `brain.py` implements. [PRD](../../../../00_Meta/PRD.md) §19 M5 requires these rules to be specified in a spec note before implementation; the implementation plan's Phase M5.0 additionally required owner review before the Indexer phase (M5.1). **Reviewed and promoted to canonical by the owner on 2026-08-11** — changes now follow §6.3 change control.

Design inspiration is Obsidian's MetadataCache; the portable authoring contract is [Relative Markdown Link Rules](../../../solutions/obsidian-issues/wikilink-resolution-rules.md). Where this spec deliberately diverges from Obsidian or from the implementation plan, the divergence is listed in §11 and §12.

**Editor surfaces this spec serves (must-consider on every change).** The vault has two supported editors — **Obsidian** (primary UI) and **VS Code** ([PRD](../../../../00_Meta/PRD.md) §6.5) — and `brain` is the compatibility keystone between them:
- The **link-resolution model (§6) tracks Obsidian's**: a link that resolves differently in `brain` than in Obsidian is a bug in one of them, and every intentional divergence must be recorded in §11.
- The **VS Code surface consumes `brain` directly**: `.vscode/tasks.json` invokes `validate`, `index`, `search`, `recent`, `report`, `tasks`, and `links` (the backlinks-panel substitute there), so command semantics (§9–10) and output are part of that editor's UX contract.
- Any change to this spec or to `brain.py` behavior must therefore be checked against **both** editor surfaces, and structural consequences flow to the editor-surface parity duty in [OPERATING-RULES](../../../docs/OPERATING-RULES.md) (update `.obsidian/`, `.vscode/`, and the §6.5 mapping together).

Normative language: **must** = required behavior; **records an error/warning** = the finding is stored in the index or produced by `validate` (§10), never silently dropped.
