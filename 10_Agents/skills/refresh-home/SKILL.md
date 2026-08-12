---
name: refresh-home
description: Preview, explain, verify, or explicitly refresh the generated local Home from structured AYMT actions and the safe tracked vault corpus. Use when the owner asks for the vault homepage, a current dashboard, a Home refresh, or an editor startup surface check.
title: "Skill: Refresh Home"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Refresh Home

Use `brain home` as the sole Home generator. Home is a navigation and review surface, not permission to send, publish, purchase, delete, or contact anyone.

## Workflow

1. Preview with `brain home`, or inspect the same structured fields with `brain home --json`.
2. Explain top actions, current/due reviews, and bounded health/freshness signals from their included sources. Never add private, untracked, seed, archived, or foreign-environment context.
3. When the owner explicitly asks to refresh the committed snapshot, run `brain home --write`. Never hand-edit `00_Meta/HOME.md`.
4. Verify exact freshness with `brain home --check`. Exit 0 means content, marker, digest, mode, date, tracked inputs, and selected-environment metadata match.

## Safety contract

- Home consumes structured AYMT data; never parse `00_Meta/AYMT.md`.
- Home and structured AYMT share one authenticated corpus snapshot and reauthenticate the exact tracked set plus consumed note/index/config/manifest bytes before output. Restricted notes, notes targeting restricted content, untracked files, seeded examples, generated Home/AYMT, and all environment bodies are excluded. The seed inventory and selected environment manifest must be tracked; only selected environment metadata can contribute.
- Preview and `--check` are portable and zero-write. `--write` may change exactly the recognized generated `00_Meta/HOME.md`; generic agent write authority remains closed.
- Home is outside automatic hooks and the merge driver because its date and environment inputs are clone-local. Optional GitHub actions require a separately supplied strict sanitized snapshot; brain never invokes GitHub or the network.
