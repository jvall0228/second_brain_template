---
name: vault-maintenance
description: Run the vault's health checks, fix what they find, and keep the status and changelog snapshots current. Use for "check the vault", "clean up", or as a recurring hygiene pass.
title: "Skill: Vault Maintenance"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Vault Maintenance

Keep the vault passing its own checks and its snapshots truthful.

## Steps

1. **Run the full check:** `python3 10_Agents/tools/brain/brain.py validate --check-index`.
2. **Fix errors by class:**
   - Stale index → `python3 10_Agents/tools/brain/brain.py index`
   - Unresolved links → use the `link-repair` skill
   - Frontmatter/tag/filename errors on **non-canonical** notes → fix directly (bump `updated:`)
   - Errors on `workflow/canonical` notes → do **not** edit directly; propose the fix via an Inbox note tagged `workflow/needs-review` (see `10_Agents/docs/operating-rules.md`), unless the human has directed the change in this session
3. **Investigate warnings** (ambiguous links, case mismatches): fix the link text to the unambiguous full path where intent is clear; otherwise list them for the human.
4. **Scan for duplication:** notes sharing a subject (e.g. one "supersedes" another, or two reference notes covering the same tool/topic) violate the one-topic-one-note rule — propose a merge to the human with a suggested surviving note and which conflicting sections get replaced — a merge rewrites overlapping content into one coherent whole, never concatenates two notes. Never merge unprompted. Approved proposals are executed via the [[10_Agents/skills/merge-notes/SKILL|merge-notes]] skill — detection proposes here; that skill executes.
5. **Refresh snapshots:**
   - `00_Meta/status.md` is deliberately non-canonical — update its snapshot/milestone table directly when reality moved.
   - Add a dated `00_Meta/changelog.md` entry **only** for structural changes (it's canonical: needs human direction).
6. **Re-validate, commit, push.** The commit message should say what was fixed, not just "maintenance".

## Rules

- Never delete or restructure content as "cleanup" — flag candidates for the human instead.
- Warnings don't block commits; errors do. Leave the vault at zero errors.
- Staleness and expiration are the [[10_Agents/skills/curate/SKILL|curate]] skill's charter (epistemic integrity); this skill stays mechanical.

## References

- `10_Agents/tools/brain/README.md` — the CLI
- `00_Meta/conventions.md` § Change Control — what needs approval
