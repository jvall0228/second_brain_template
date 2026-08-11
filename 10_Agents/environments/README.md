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

## The convention

- **One directory per environment:** `10_Agents/environments/<env-slug>/`, where `<env-slug>` is a kebab-case name the owner chooses (e.g. `work-macbook`, `home-desktop`). The orientation inventory lives at `<env-slug>/orientation-inventory.md`.
- **Environment-scoped, self-guarding:** every note in an environment directory opens with an applicability preamble naming the environment it belongs to and stating that agents in **any other environment must ignore it**. An agent consults only the directory matching the environment it is actually running in.
- **Never bootstrap-linked:** nothing here joins the bootstrap sequence in [[AGENTS]] or the global map in [[00_Meta/index]]. Environment notes are pulled on demand by the skills that need them ([[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] writes; [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]] and [[10_Agents/skills/self-maintenance/SKILL|self-maintenance]] read) — they are facts about a place, not context every agent needs.
- **Write posture:** notes here are agent-written (`workflow/draft`, with `author:`/`session:` provenance per [[00_Meta/conventions]]) — this directory is the explicitly directed destination for orientation output, a standing exception to Inbox-first, review-gated like any draft.

## Deferred (#15)

This README documents the **minimal landing convention only**. The full environment-scoping machinery — environment fingerprinting, automatic environment detection and matching, gating rules for which notes load where — is deferred to #15. Until it ships, matching an environment to its directory is a judgment call: read each directory's preamble and pick the one describing the environment you are in; if none matches, orientation creates a new one.

## Related

- [[10_Agents/skills/agent-orientation/SKILL|agent-orientation]] — the required output contract and inventory note template
- [[10_Agents/harnesses/README|Harness adapters]] — static, template-shipped harness knowledge (environments record the live deltas)
- [[10_Agents/README]] — the agent library index
