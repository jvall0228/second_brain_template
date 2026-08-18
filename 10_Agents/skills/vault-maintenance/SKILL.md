---
name: vault-maintenance
description: Run the vault's health checks, fix what they find, and keep the status and changelog snapshots current. Use for "check the vault", "clean up", or as a recurring hygiene pass.
title: "Skill: Vault Maintenance"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-18
expires: 2027-08-11
---

# Vault Maintenance

**CODE stage:** System (outside the loop) — mechanical integrity.

Keep the vault passing its own checks and its snapshots truthful.

## Steps

1. **Open with the health report:** `brain report` — stale-active notes, disconnected orphans, Inbox triage debt, tag drift, and the unresolved-link count in one pass. It sets the agenda for the steps below; the tag-drift section (single-use and near-duplicate tags) is a direct input to the duplication scan in step 5.
2. **Run the full check:** `brain validate --check-index`.
3. **Check entity integrity:** `brain projects --json` — inspect canonical Project/Area membership, lifecycle, target, completion-criteria, overdue, collision, and rollup findings. Preview with `brain projects`; apply with `brain projects --write-rollups` only when the relationship source tags are already correct.
4. **Fix errors by class:**
   - Stale index → `brain index`
   - Unresolved links → use the `link-repair` skill
   - Frontmatter/tag/filename errors on **non-canonical** notes → fix directly (bump `updated:`)
   - Errors on `workflow/canonical` notes → do **not** edit directly; propose the fix via an Inbox note tagged `workflow/needs-review` (see `10_Agents/docs/OPERATING-RULES.md`), unless the human has directed the change in this session
5. **Investigate warnings** (including Project/Area findings, ambiguous links, and case mismatches). Fix mechanical rollup drift only from correct Project mappings; never mechanically reactivate, deprioritize, close, archive, or invent a target. Present those decisions to the owner.
6. **Scan for duplication:** notes sharing a subject (e.g. one "supersedes" another, or two reference notes covering the same tool/topic) violate the one-topic-one-note rule — propose a merge to the human with a suggested surviving note and which conflicting sections get replaced — a merge rewrites overlapping content into one coherent whole, never concatenates two notes. Never merge unprompted. Approved proposals are executed via the [merge-notes](../merge-notes/SKILL.md) skill — detection proposes here; that skill executes.
7. **Refresh snapshots:**
   - `00_Meta/STATUS.md` is deliberately non-canonical — update its snapshot/milestone table directly when reality moved.
   - Add a dated `00_Meta/CHANGELOG.md` entry **only** for structural changes (it's canonical: needs human direction).
8. **Re-validate, commit, push.** The commit message should say what was fixed, not just "maintenance".

## Rules

- Never delete or restructure content as "cleanup" — flag candidates for the human instead.
- Warnings don't block commits; errors do. Leave the vault at zero errors.
- Staleness and expiration are the [curate](../curate/SKILL.md) skill's charter (epistemic integrity); this skill stays mechanical.

## References

- `10_Agents/tools/brain/README.md` — the CLI
- `00_Meta/CONVENTIONS.md` § Change Control — what needs approval
- [Project and Area Contract](../../docs/project-area-contract.md) — warning interpretation and transition boundaries
