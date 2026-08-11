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

A curated, **links-only** catalog of third-party / community `SKILL.md`-style content and user-scope memory-file content that pairs well with this vault. Decided in [issue #7](https://github.com/jvall0228/second_brain_template/issues/7) (2026-08-11), as amended by the owner's 2026-08-11 reversal from pin-to-SHA to **tracking the upstream branch and installing the latest**, gated by install-time per-item sign-off (see § Rules):

The **machine-readable source of truth** for the whole recommended-component library — these community skills and memory blocks *plus* the first-party overlays and vault-config presets — is `10_Agents/components/manifest.json` (schema v1); see the [[10_Agents/components/README|components registry]] for the model. This note stays the **human-facing curated catalog** for the community items: their trust notes, verification, and licensing. An onboarder installs from the manifest; the manifest's community entries point back here via their `catalog` anchor.

- **Links-only, tracking latest, never vendored copies.** Each item records its upstream URL, the branch it **tracks**, a one-paragraph local summary, its license, and a trust note. The vault never carries third-party content in its own history — only these curated pointers, plus (owner decision, 2026-08-11) **branch-tracking git submodules under `.extern/`** where materialization helps: a submodule stores only the `.gitmodules` tracking config (`branch = main`), content materializes opt-in via `git submodule update --init --remote` at the tracked branch's current tip, and the dot-prefixed path keeps it outside the note corpus, index, secret scan, and adopter flow. Licensing stays upstream's; the install fetches whatever the tracked branch currently holds.
- **Per-item owner sign-off**, matching the community-extension precedent ([[00_Meta/PRD]] §6.5): first-party items may install by default; community items require an explicit yes during onboarding, recorded in the install manifest. Because installs track latest, that yes is given **against the content fetched at install time** — the review is the supply-chain safeguard.
- **Install path:** [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] fetches the latest from the tracked branch into the harness's **user scope** at install time (see its "Optional: recommended components" section). Installs are manifest-driven and reversible.

## Item format

Every catalog entry is a `###` section under [[#Catalog]] and must carry all of:

| Field | Meaning |
|-------|---------|
| **Upstream** | Canonical source URL (repo or file) |
| **Tracks** | The upstream branch this item follows (e.g. `main`); the install pulls that branch's current tip — no frozen commit. The literal marker `TODO-pin` marks an item whose upstream has not yet been verified: **not installable** until verified. |
| **License** | Upstream license (or `TODO-pin` until verified) |
| **What it does** | One-paragraph local summary |
| **Trust note** | Author, provenance tier (`first-party` / `community`), why recommended |
| **Sign-off** | `default-ok` (first-party) or `owner-per-item` (community) |

Re-tracking an item (following a different branch) or advancing a verified recommendation is an ordinary curated edit to this note: re-verify the current upstream content, adjust the **Tracks** field, bump `updated:`.

## Catalog

### i-have-adhd

- **Upstream:** <https://github.com/ayghri/i-have-adhd> (the canonical community repo, ~19.6k stars)
- **Tracks:** <https://github.com/ayghri/i-have-adhd> @ `main` (latest — the install pulls the current tip, no frozen pin)
- **Local checkout:** `.extern/i-have-adhd` (branch-tracking submodule on `main`; opt-in via `git submodule update --init --remote`)
- **License:** MIT
- **What it does:** Ten persistent output rules that stop an agent from burying the answer — lead with the next action, number multi-step tasks, end with a concrete next step, cap lists, no preamble/recap/closers, visible progress, matter-of-fact error handling. Complements this vault's Inbox-first capture posture.
- **Trust note:** community; named by the owner (2026-08-11 session). Content on `main` was read and verified 2026-08-11 (formatting guidance only — no command execution, fetching, or exfiltration instructions). Because installs track latest, re-verify the current content at each onboarding sign-off.
- **Sign-off:** owner-per-item

### karpathy

- **Upstream:** <https://github.com/multica-ai/andrej-karpathy-skills> (the viral repo, ~200k stars; originally `forrestchang/andrej-karpathy-skills`, which now redirects here — not authored by Karpathy himself, but derived from his posted observations on LLM coding pitfalls)
- **Tracks:** <https://github.com/multica-ai/andrej-karpathy-skills> @ `main` (latest — the install pulls the current tip, no frozen pin)
- **Local checkout:** `.extern/andrej-karpathy-skills` (branch-tracking submodule on `main`; opt-in via `git submodule update --init --remote`)
- **License:** MIT
- **What it does:** Behavioral guardrails for coding agents distilled from Karpathy's four observed failure modes — no silent assumptions, no over-engineering, surgical changes only, goal-driven execution with verifiable success criteria. The repo also ships the same content as a root `CLAUDE.md` (same repo/branch) usable as user-scope memory-file content.
- **Trust note:** community; named by the owner (2026-08-11 session). Content on `main` was read and verified 2026-08-11 (engineering guidance only — no command execution, fetching, or exfiltration instructions). Because installs track latest, re-verify the current content at each onboarding sign-off.
- **Sign-off:** owner-per-item

## Recommended user-scope memory-file content

Curated blocks the owner may want in their harness **user-level** `AGENTS.md`/`CLAUDE.md`, outside the vault. These install through the same onboard-harness path as their own marker-delimited blocks (separate from the second-brain registration block), recorded in the manifest and removed on uninstall.

- **karpathy coding guidelines** — the root `CLAUDE.md` of the [[#karpathy]] item (same repo/branch: `.extern/andrej-karpathy-skills/CLAUDE.md` on `main`, installed latest). Four behavioral rails — think before coding (no silent assumptions), simplicity first, surgical changes, goal-driven execution — as a user-scope block for any coding harness. Offered by name during onboard-harness's optional step; owner sign-off per the [[#karpathy]] catalog entry covers it.

Propose further additions via the Inbox.

## Other recommended components

Beyond the community skills and memory blocks catalogued above, the recommended-component library also carries **first-party** items — not third-party content, so they need no pinning or per-item trust review:

- **Harness overlays** — the [[10_Agents/harnesses/cursor/wiring|Cursor]] and [[10_Agents/harnesses/copilot/wiring|Copilot]] overlays, made discoverable as `overlay` components. Their own `overlay/manifest.json` files stay the authority for what they install ([[10_Agents/harnesses/README]] § Overlays).
- **Vault-config presets** — fork-policy starting points applied via `merge-config` into `00_Meta/config.yaml` (currently the work-fork preset).

These are recorded only in `10_Agents/components/manifest.json` / [[10_Agents/components/README]]; their details are not duplicated here.

## Rules

- This note is the **human-facing** home for community-skill recommendations; the machine-readable registry is `10_Agents/components/manifest.json` ([[10_Agents/components/README]]). [[10_Agents/skills/README]] links here but lists only vault-canonical skills.
- Never vendor third-party skill content into the vault (no copies under `10_Agents/skills/`). Third-party content stays upstream as a **branch-tracking** `.extern/` submodule (or a tracked URL) and materializes only into the harness user scope at install time.
- These community components **track the upstream branch and install the latest** (owner decision, 2026-08-11, reversing issue #7's pin-to-SHA). The safeguard is the **install-time per-item owner sign-off against the fetched content** — not a frozen pin; there is no "three-place SHA agreement" to maintain.
- An item still marked `TODO-pin` (upstream not yet verified) must be skipped by installers.
- Adding, re-tracking, or advancing an item is a curated edit to a `06_Resources/` note — owner review applies per [[00_Meta/CONVENTIONS]] change control; `.gitmodules` and `.extern/` are owner-content to [[10_Agents/skills/sync-upstream/SKILL|sync-upstream]] (it proposes, never auto-advances).
