---
title: "Environments"
tags:
  - type/meta
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
author: claude-code
session: "PR: feat/m10.1-orientation-contract"
---

# Environments

Environment-scoped notes: facts that are true of **one machine or execution environment** (a work laptop, a home desktop, a cloud container), not of the vault or the owner in general. The first resident is the orientation inventory produced by [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]].

## The contract

- **One directory per environment:** `10_Agents/environments/<env-slug>/`, where `<env-slug>` is a kebab-case name the owner chooses (e.g. `work-macbook`, `home-desktop`). The orientation inventory lives at `<env-slug>/orientation-inventory.md`.
- **Tracked identity:** each directory contains `environment.json` (brain spec §20.1) and a self-guarding `README.md`. Identity evidence is SHA-256 only; raw hostname, username, machine path, credential, and endpoint values are forbidden. `fingerprints` may be empty when the OS exposes no acceptable native machine ID; use explicit or selector selection in that case.
- **Clone-local selection:** `.second-brain/environment` contains the selected slug; `.second-brain/environments/<env-slug>/` holds secrets-adjacent overlays. Both are gitignored. Selection is `--env` > `SECOND_BRAIN_ENV` > selector > unique fingerprint; ambiguity or no match fails closed.
- **Environment-scoped, self-guarding:** every note in an environment directory opens with an applicability preamble naming the environment it belongs to and stating that agents in **any other environment must ignore it**. An agent consults only the directory matching the environment it is actually running in.
- **Never bootstrap-linked:** nothing here joins the bootstrap sequence in [[AGENTS]] or the global map in [[00_Meta/INDEX]]. Environment notes are pulled on demand by the skills that need them ([[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] writes; [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] and [[10_Agents/skills/self-maintenance/SKILL|self-maintenance]] read) — they are facts about a place, not context every agent needs.
- **Write posture:** notes here are agent-written (`workflow/draft`, with `author:`/`session:` provenance per [[00_Meta/CONVENTIONS]]) — this directory is the explicitly directed destination for orientation output, a standing exception to Inbox-first, review-gated like any draft.

## Detect, list, and migrate

- `brain env detect --json` returns SHA-256 evidence and the current match.
- `brain env list --json` shows metadata for every environment without exposing fingerprint digests or capability values.
- `brain env migrate <old-slug> <new-slug>` previews exact moves from an unregistered legacy directory to a target that does not yet exist, and never writes. Apply the reviewed move with version control, then let orientation create the manifest and landing note.
- `brain validate` is clone-neutral: it checks every manifest envelope plus shared content without requiring this machine to match an environment or reading foreign environment note bodies.

The long-form fallback is `python3 10_Agents/tools/brain/brain.py ...`. See brain spec §20 for the versioned schema, privacy boundary, and fail-closed reason codes.

## Related

- [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] — the required output contract and inventory note template
- [[10_Agents/harnesses/README|Harness adapters]] — static, template-shipped harness knowledge (environments record the live deltas)
- [[10_Agents/README]] — the agent library index
