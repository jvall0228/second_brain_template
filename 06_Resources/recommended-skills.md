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

- **Upstream:** TODO-pin — community `SKILL.md`; exact source to be confirmed with the owner and pinned.
- **Pinned ref:** TODO-pin
- **License:** TODO-pin
- **What it does:** A skill/memory-file block that adapts agent interaction style for an ADHD owner — shorter turns, explicit next actions, externalized working memory, and low-friction capture prompts. Complements this vault's Inbox-first capture posture.
- **Trust note:** community; named by the owner (2026-08-11 session) as an example of community skill content worth recommending. Content must be read in full at the pinned ref before install.
- **Sign-off:** owner-per-item

### karpathy

- **Upstream:** TODO-pin — community `SKILL.md`; exact source to be confirmed with the owner and pinned.
- **Pinned ref:** TODO-pin
- **License:** TODO-pin
- **What it does:** A skill/memory-file block distilling Andrej Karpathy-style working guidance for coding agents — terse, first-principles explanations and pragmatic engineering defaults. Useful as user-scope guidance alongside vault skills.
- **Trust note:** community; named by the owner (2026-08-11 session) as an example of community skill content worth recommending. Content must be read in full at the pinned ref before install.
- **Sign-off:** owner-per-item

## Recommended user-scope memory-file content

Curated blocks the owner may want in their harness **user-level** `AGENTS.md`/`CLAUDE.md`, outside the vault. These install through the same onboard-harness path as their own marker-delimited blocks (separate from the second-brain registration block), recorded in the manifest and removed on uninstall. No entries yet beyond what the catalog items above provide as memory-file content; propose additions via the Inbox.

## Rules

- This note is the **only** home for community-skill recommendations; [[10_Agents/skills/README]] links here but lists only vault-canonical skills.
- Never vendor third-party skill content into the vault (no copies under `10_Agents/skills/`).
- An item without a resolved **Pinned ref** (i.e. still `TODO-pin`) must be skipped by installers.
- Adding or re-pinning an item is a curated edit to a `06_Resources/` note — owner review applies per [[00_Meta/conventions]] change control.
