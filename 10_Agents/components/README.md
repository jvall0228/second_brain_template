---
title: "Recommended Components"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - workflow/draft
updated: 2026-08-11
expires: 2027-08-11
author: claude-code
session: https://claude.ai/code/session_0194H8b6W4qpn7DQVKEc7y73
---

# Recommended Components

The agent library's registry of **recommended components** an onboarder can install
into a coding harness. A component is a named, installable capability with one
machine-readable record. This directory is that registry — `manifest.json` is the
single source of truth; the human-facing curated catalog for the community items
stays at [recommended-skills](../../06_Resources/recommended-skills.md).

## What a recommended component is

A component bundles: an `id`, a `kind`, a `provenance` (`first-party` or
`community`), a one-line `description`, a `license`, a `signoff` gate, a `source`
(where the content lives), an `install` (how it lands), and a `reverse` (how it is
removed). Community items also carry a `catalog` anchor into the human-facing note.

Four kinds, each with its own install method:

| Kind | What it is | Installs by |
|------|------------|-------------|
| `skill` | A third-party `SKILL.md`-style skill | `copy` into the harness user scope (`~/.agents/skills/<id>/` and the Claude Code path) |
| `memory-block` | A curated user-scope `AGENTS.md`/`CLAUDE.md` block | `marker-block` merged into the user's instruction surface |
| `overlay` | A harness-native primitive bundle (rules, hooks, config) | `shipped-in-repo` — the overlay's own `manifest.json` stays the authority for its artifacts |
| `vault-config-preset` | A fork-policy starting point | `merge-config` — a preset fragment applied into `00_Meta/config.yaml` |

The install vocabulary is the overlay method vocabulary
([README](../harnesses/README.md) § Overlays) plus one new method, `merge-config`,
for presets. There is **one install engine** — the overlay + component installer
in [onboard-harness](../skills/onboard-harness/SKILL.md) — never a second model.

## The agent library includes third-party components — without vendoring them

The owner wants the agent library to cover third-party components too. It does — as
**pointers, not copies**. The registry (this manifest and README) lives in the vault;
the third-party content never does. Community content stays upstream as a
**branch-tracking** git submodule under `.extern/` (dot-path-pruned, opt-in via
`git submodule update --init --remote`) or a tracked remote URL, and materializes only
into the harness **user scope** on the adopter's machine at install time. Nothing under
`10_Agents/skills/` is third-party; that directory holds only vault-canonical or
agent-generated skills.

## Installer, sign-off, reversibility

[onboard-harness](../skills/onboard-harness/SKILL.md) reads `manifest.json`,
groups by kind, and installs each component by its declared method/scope/target,
recording every action in the machine manifest `~/.agents/second-brain-manifest.json`.
[onboard-owner](../skills/onboard-owner/SKILL.md) offers the install as a
first-class step and applies `vault-config-preset` components itself under its
live-session write exception (a config change is a vault write, and an owner decision).

- **Sign-off.** First-party components may be `default-ok` (installed without asking
  per item). Community components require `owner-per-item` — an explicit yes before
  anything is fetched, recorded in the machine manifest. A `vault-config-preset` is
  first-party but still `owner-per-item`, because changing fork policy is the owner's call.
- **Reversibility.** Every install is reversible by its `reverse.method` (`delete`,
  `remove-marker-block`, `restore-config`, or `none` for shipped-in-repo overlays),
  removing exactly what the machine manifest records.
- **Never-vendor / user-scope.** Community content is written only to user scope on
  the adopter's machine — never into the vault or this repository.

## Tracking latest (not pinning)

Community submodule components **track their upstream branch and install the latest**
(owner decision, 2026-08-11, reversing issue #7's pin-to-SHA). A component names the
branch in `source.track` (`main`); `.gitmodules` carries the matching `branch = main`,
so the install-time `git submodule update --init --remote` fetches the branch's current
tip. There is no frozen commit and no three-place SHA agreement
to maintain — the **supply-chain safeguard is the install-time per-item owner sign-off
against the content actually fetched** ([onboard-harness](../skills/onboard-harness/SKILL.md)).
`test_components.py` checks that each submodule component declares a `track` branch and
that `.gitmodules` configures branch-tracking for it.

## Files

- `manifest.json` — the machine-readable registry (schema `manifest_version: 1`).
- `presets/` — `vault-config-preset` fragments (currently `work-fork.yaml`).
- [recommended-skills](../../06_Resources/recommended-skills.md) — the human-facing curated catalog for community items.
