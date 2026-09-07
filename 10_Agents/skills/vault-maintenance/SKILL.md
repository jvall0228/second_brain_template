---
name: vault-maintenance
description: Run the vault's health checks, fix what they find, and keep the status and changelog snapshots current. Use for "check the vault", "clean up", or as a recurring hygiene pass.
title: "Skill: Vault Maintenance"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# Vault Maintenance

**CODE stage:** System (outside the loop) — mechanical integrity.

Keep the vault passing its own checks and its snapshots truthful.

**Execution mode:** the repair steps below are interactive. An autonomous run reports proposed edits to existing notes and STATUS in a new Inbox note, including exact targets and corrections; it may run only the owning generators listed as standing exceptions in the [Write Authority Contract](../../docs/write-authority.md). Do not treat non-canonical status as permission to edit unattended. `validate --write-baseline` and link migrations require interactive execution, so an unattended run reports their need.

## Steps

1. **Open with the health report:** `brain report` — stale-active notes, disconnected orphans, Inbox triage debt, tag drift, and the unresolved-link count in one pass. It sets the agenda for the steps below; the tag-drift section (single-use and near-duplicate tags) is a direct input to the duplication scan in step 5.
2. **Run the full check:** `brain validate --check-index`. Check generated Home and AYMT separately with the read-only `brain home --check` and `brain aymt --check` commands, or their `--json` `fresh` fields. An index check or recent `updated:` date does not prove those date/environment-dependent snapshots are current.
3. **Check entity integrity:** `brain projects --json` — inspect canonical Project/Area membership, lifecycle, target, completion-criteria, overdue, collision, and rollup findings. Preview with `brain projects`; apply with `brain projects --write-rollups` only when the relationship source tags are already correct.
4. **Fix errors by class:**
   - Stale index → `brain index`
   - Unresolved links → use the `link-repair` skill
   - Frontmatter/tag/filename errors → fix within the interactive user-directed task (bump `updated:`); autonomous runs propose corrections in Inbox
   - Canonical or canonical-by-policy sources → follow the [Write Authority Contract](../../docs/write-authority.md): interactive task scope permits appropriate source repairs with scoped review and validation; autonomous runs propose them in Inbox.
5. **Investigate warnings** (including Project/Area findings, ambiguous links, and case mismatches). Fix mechanical rollup drift only from correct Project mappings; never mechanically reactivate, deprioritize, close, archive, or invent a target. Present those decisions to the owner.
6. **Scan for duplication:** notes sharing a subject (e.g. one "supersedes" another, or two reference notes covering the same tool/topic) violate the one-topic-one-note rule — propose a merge to the human with a suggested surviving note and which conflicting sections get replaced — a merge rewrites overlapping content into one coherent whole, never concatenates two notes. Never merge unprompted. Approved proposals are executed via the [merge-notes](../merge-notes/SKILL.md) skill — detection proposes here; that skill executes.
7. **Refresh snapshots:**
   - `00_Meta/STATUS.md` is deliberately non-canonical — update its snapshot/milestone table in an interactive task when reality moved; autonomous runs propose the new snapshot in Inbox. Give each measurement its observation date and command/scope. `updated:` records a prose edit; a generator's render date records rendering. Neither renews an older test total, inventory count, or freshness result. Replace obsolete figures; mark unmeasured checks pending.
   - Finalize source changes and regenerate the index and other generated surfaces through their owning commands. Then explicitly refresh authorized Home/AYMT snapshots with `brain aymt --write` and `brain home --write`; never hand-edit them. Recheck both after the final source/index transaction, including commit-time regeneration. They stay outside automatic hooks and the merge driver.
   - Internal Home/AYMT include eligible private work with classification and provenance. Retain that provenance when summarizing them; notification/public-only restrictions remain separate. Public-only synthesis must use the [fresh policy-only context route](../../../00_Meta/restricted-private.md#public-only-synthesis), or report unsupported isolation without synthesis.
   - Add a dated `00_Meta/CHANGELOG.md` entry for structural changes under the current interactive task's authority.
8. **Re-validate and record evidence.** Run checks appropriate to the actual changes and record observed results; do not carry forward an old suite total as current. Commit/push only within the authorized session scope. The commit message should say what was fixed, not just "maintenance".

## Rules

- Never delete or restructure content as "cleanup" — flag candidates for the human instead.
- Warnings don't block commits; errors do. Leave the vault at zero errors.
- Staleness and expiration are the [curate](../curate/SKILL.md) skill's charter (epistemic integrity); this skill stays mechanical.

## References

- `10_Agents/tools/brain/README.md` — the CLI
- `00_Meta/CONVENTIONS.md` § Change Control — what needs approval
- [Project and Area Contract](../../docs/project-area-contract.md) — warning interpretation and transition boundaries
