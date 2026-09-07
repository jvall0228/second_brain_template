---
name: refresh-home
description: Preview, explain, verify, or explicitly refresh the generated local Home from structured AYMT actions and the complete eligible tracked vault corpus. Use when the owner asks for the vault homepage, a current dashboard, a Home refresh, or an editor startup surface check.
title: "Skill: Refresh Home"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# Refresh Home

Use `brain home` as the sole Home generator. Home is a navigation and review surface, not permission to send, publish, purchase, delete, or contact anyone.

## Workflow

1. Preview with `brain home`, or inspect the same structured fields with `brain home --json`.
2. Explain top actions, current/due reviews, and bounded health/freshness signals from their included sources. Home is a complete internal view of eligible tracked work, including private work. Preserve classification and provenance when reusing its substance; do not add untracked, seed, archived, or foreign-environment context.
3. When the owner explicitly asks to refresh the committed snapshot, run `brain home --write`. Never hand-edit `00_Meta/HOME.md`.
4. Verify exact freshness with `brain home --check`, or inspect the read-only `fresh` field in `brain home --json`. Exit 0 from `--check` means content, marker, digest, mode, date, tracked inputs, and selected-environment metadata match. Record the observation date separately from the edit/render date, and recheck after the final source/index update.

## Safety contract

- Home consumes structured AYMT data; never parse `00_Meta/AYMT.md`.
- Home and structured AYMT share one authenticated corpus snapshot and reauthenticate the exact tracked set plus consumed note/index/config/manifest bytes before output. Private notes and valid private links remain eligible. Untracked files, seeded examples, Archives, Templates, generated Home/AYMT, and all environment bodies are excluded. The seed inventory and selected environment manifest must be tracked; only selected environment metadata can contribute.
- Output caps bound display, not the eligible source inventory. `privacySources` in JSON and `privacy-sources` in frontmatter retain dependencies contributing text, ranking, counts, and health signals, including undisplayed rows. Private renders inherit `restricted/private`; current source restrictions continue to propagate through stored-output reuse. Missing or invalid provenance is unknown for public-only admission, while internal use remains permitted.
- Home uses AYMT's curated Project `## Next Actions` gate and does not convert criteria or historical tasks into recommendations. See the [Project and Area Contract](../../docs/project-area-contract.md#next-actions).
- Internal inclusion authorizes no sending or public export. Public-only synthesis requires the [fresh policy-only context route](../../../00_Meta/restricted-private.md#public-only-synthesis) and admitted sources. Retrieval flags cannot remove prior private context; unsupported isolation means no purported public-only synthesis. Notification and public-only restrictions remain in force.
- Preview and `--check` are portable and zero-write. `--write` may change exactly the recognized generated `00_Meta/HOME.md`; generic agent write authority remains closed.
- Home is outside automatic hooks and the merge driver because its date and environment inputs are clone-local. Optional GitHub actions require a separately supplied strict sanitized snapshot; brain never invokes GitHub or the network.
