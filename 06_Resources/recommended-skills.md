---
title: "Recommended Community Skills"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
updated: 2026-08-11
expires: 2026-11-11
author: claude-code
session: https://claude.ai/code/session_0194H8b6W4qpn7DQVKEc7y73
---

# Recommended Community Skills

A curated, **links-only** catalog of third-party / community `SKILL.md`-style content and user-scope memory-file content that pairs well with this vault. Decided in [issue #7](https://github.com/jvall0228/second_brain_template/issues/7) (2026-08-11):

- **Links-only with pinned refs, never vendored copies.** Each item records its upstream URL plus a **pinned commit/tag ref**, a one-paragraph local summary, its license, and a trust note. The vault never carries third-party content — only these curated pointers. Licensing stays upstream's; staleness is visible in the explicit pin instead of silent in a drifting copy.
- **Per-item owner sign-off**, matching the community-extension precedent ([[00_Meta/prd]] §6.5): first-party items may install by default; community items require an explicit yes during onboarding, recorded in the install manifest.
- **Install path:** [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] fetches from the pinned ref into the harness's **user scope** at install time (see its "Optional: recommended community content" section). Installs are manifest-driven and reversible.

## Item format

Every catalog entry is a `###` section under [[#Catalog]] and must carry all of:

| Field | Meaning |
|-------|---------|
| **Upstream** | Canonical source URL (repo or file) |
| **Pinned ref** | Commit-sha- or tag-pinned URL to the exact content recommended — or the literal marker `TODO-pin` when the exact ref has not yet been verified. `TODO-pin` items are **not installable** until pinned. |
| **License** | Upstream license (or `TODO-pin` until verified) |
| **What it does** | One-paragraph local summary |
| **Trust note** | Author, provenance tier (`first-party` / `community`), why recommended |
| **Sign-off** | `default-ok` (first-party) or `owner-per-item` (community) |

Updating a pin is an ordinary curated edit to this note: verify the new ref's content, replace the pinned URL, bump `updated:`.

## Catalog

### i-have-adhd

- **Upstream:** <https://github.com/ayghri/i-have-adhd> (the canonical community repo, ~19.6k stars)
- **Pinned ref:** <https://github.com/ayghri/i-have-adhd/blob/2ed064090711586e0c97a2fbbf15465fe8f1808b/skills/i-have-adhd/SKILL.md> (main @ 2026-08-10)
- **License:** MIT
- **What it does:** Ten persistent output rules that stop an agent from burying the answer — lead with the next action, number multi-step tasks, end with a concrete next step, cap lists, no preamble/recap/closers, visible progress, matter-of-fact error handling. Complements this vault's Inbox-first capture posture.
- **Trust note:** community; named by the owner (2026-08-11 session). Content at the pinned ref was read and verified 2026-08-11 (formatting guidance only — no command execution, fetching, or exfiltration instructions). Re-verify on any re-pin.
- **Sign-off:** owner-per-item

### karpathy

- **Upstream:** <https://github.com/multica-ai/andrej-karpathy-skills> (the viral repo, ~200k stars; originally `forrestchang/andrej-karpathy-skills`, which now redirects here — not authored by Karpathy himself, but derived from his posted observations on LLM coding pitfalls)
- **Pinned ref:** <https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/skills/karpathy-guidelines/SKILL.md> (main @ 2026-04-20)
- **License:** MIT
- **What it does:** Behavioral guardrails for coding agents distilled from Karpathy's four observed failure modes — no silent assumptions, no over-engineering, surgical changes only, goal-driven execution with verifiable success criteria. The repo also ships the same content as a root `CLAUDE.md` (same pin) usable as user-scope memory-file content.
- **Trust note:** community; named by the owner (2026-08-11 session). Content at the pinned ref was read and verified 2026-08-11 (engineering guidance only — no command execution, fetching, or exfiltration instructions). Re-verify on any re-pin.
- **Sign-off:** owner-per-item

## Recommended user-scope memory-file content

Curated blocks the owner may want in their harness **user-level** `AGENTS.md`/`CLAUDE.md`, outside the vault. These install through the same onboard-harness path as their own marker-delimited blocks (separate from the second-brain registration block), recorded in the manifest and removed on uninstall. No entries yet beyond what the catalog items above provide as memory-file content; propose additions via the Inbox.

## Rules

- This note is the **only** home for community-skill recommendations; [[10_Agents/skills/README]] links here but lists only vault-canonical skills.
- Never vendor third-party skill content into the vault (no copies under `10_Agents/skills/`).
- An item without a resolved **Pinned ref** (i.e. still `TODO-pin`) must be skipped by installers.
- Adding or re-pinning an item is a curated edit to a `06_Resources/` note — owner review applies per [[00_Meta/conventions]] change control.
