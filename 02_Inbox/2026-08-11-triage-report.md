---
title: "Inbox Triage Report — 2026-08-11"
tags:
  - type/log
  - audience/human
  - audience/agent
  - workflow/draft
  - status/active
updated: 2026-08-11
---

# Inbox Triage Report — 2026-08-11

Owner-requested triage of the four notes in `02_Inbox/` (README excluded). Per [[10_Agents/skills/triage-inbox/SKILL|the triage skill]], these are **proposals** — moves happen only after explicit approval.

## Proposals

| Note | What it is | Proposed destination | Proposed filename | Tag changes | Links to update on move |
|------|-----------|---------------------|-------------------|-------------|------------------------|
| `2026-08-11-harness-primitives-research.md` | Verified per-harness primitive specs + overlap matrix for all seven harnesses; actively cited as grounding by every wiring doc | `06_Resources/` | `harness-primitives-research.md` | drop `workflow/draft` | 7 wiring docs (`10_Agents/harnesses/*/wiring.md`, incl. `#Section` anchors), `10_Agents/harnesses/README.md`, `10_Agents/skills/onboard-harness/SKILL.md` (plain path), `00_Meta/changelog.md` (plain path), its own link exchange with the M5–M7 plan |
| `2026-08-11-copilot-harness-deep-dive.md` | Verified Copilot surface reference (supersedes the note above's Copilot section); grounds the P0 wiring doc | `06_Resources/` | `copilot-harness-deep-dive.md` | drop `workflow/draft` | `10_Agents/harnesses/copilot/wiring.md`, `10_Agents/harnesses/README.md`, the supersession blockquote in the primitives research, `00_Meta/changelog.md` (wikilink) |
| `2026-08-11-m5-m7-implementation-plan.md` | M5–M7 build plan — fully executed and closed out | `07_Archives/inbox/` | unchanged (dated, per `prd-review` precedent) | drop `workflow/draft`, add `status/done` | `00_Meta/changelog.md` (plain path), the primitives research's related-links line |
| `2026-08-11-copilot-p0-plan.md` | Copilot P0 promotion plan + adversarial-review log — fully executed | `07_Archives/inbox/` | unchanged (dated, per `prd-review` precedent) | drop `workflow/draft`, add `status/done` | `00_Meta/changelog.md` (plain path) |

## Rationale

- The two research notes are living reference material — wiring docs instruct agents to re-verify against them and bump `updated:`, so they stay non-canonical (`type/reference`, no workflow tag after the draft tag drops), matching the archived `prd-review` pattern.
- The two plans are done/dead in triage terms: their outcomes shipped, changelogged, and merged. `07_Archives/inbox/` is the established home for spent Inbox process docs.
- Resource filenames drop the `YYYY-MM-DD-` prefix (an Inbox-only convention); the verification date survives in each note's prose, title context, and `updated:` field.

## Open questions

1. Keep the date prefix on the two research notes instead? (They are dated snapshots; the prefix would signal that at a glance, at the cost of the Resources naming convention.)
2. `00_Meta/changelog.md` mentions the old Inbox paths in past entries. Proposal: update all four mentions to the new paths (the changelog is navigation, not a frozen record). Alternative: leave plain-text mentions as history and fix only the wikilink.

## On approval

Apply moves with `git mv`, bump each moved note's `updated:` if past 2026-08-11, rewrite the inbound links listed above, regenerate the index (`brain.py index`), run `brain.py validate --check-index`, commit.
