---
name: curate
description: Work through the brain curate report — refresh still-good notes, re-verify stale claims, propose archives and splits, and run the semantic-lint pass. Use ad hoc, on a cadence, or when validate's curation warnings pile up.
title: "Skill: Curate"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Curate

**CODE stage:** System (outside the loop) — epistemic integrity of distilled knowledge.

Epistemic integrity, where [vault-maintenance](../vault-maintenance/SKILL.md) is mechanical integrity: this skill keeps the vault's *claims* current, not its links and frontmatter. Detection is `brain`'s job; this skill supplies the judgment.

## Steps

1. **Get the report:** `brain curate --json` (add `--check-urls` only when the owner asks — it's network-bound and slow).
2. **Work each flagged note to one of four outcomes.** Read the note first; never decide from the report line alone:
   1. **Still good** → bump `updated:` and set a fresh `expires:` per the TTL table in [CONVENTIONS](../../../00_Meta/CONVENTIONS.md) § Expiration. Agent-executable directly.
   2. **Stale claims** → re-verify via [research-to-resource](../research-to-resource/SKILL.md) in corrective mode (merge fixes into the note, note the re-verification date). Agent-executable; canonical notes still follow canonical change control.
   3. **Dead** (superseded, no longer true, no longer relevant) → **propose** archiving to `07_Archives/` — never archive unprompted.
   4. **Too big** (oversized signal) → **propose** a split, naming the intended pieces; execution goes through [merge-notes](../merge-notes/SKILL.md) after approval.
3. **Judge the structural signals:** orphans (link them in, or propose archiving), unreferenced `08_Assets/` files (propose deletion or link them), dead URLs (find replacement sources or mark claims unverifiable).
4. **Semantic lint** — the checks only judgment can make. Scan the flagged notes and their link neighborhoods for:
   - **Contradictions:** two notes asserting incompatible claims.
   - **Superseded claims:** an older note stating what a newer note has since corrected.
   - **Concepts with no note:** a subject mentioned across several notes that has no note of its own.
   - **Missing cross-links:** clearly related notes with no relative Markdown link between them.
   All findings are **proposals** — never silently fix a contradiction (that's choosing a winner; see the Stuck/Escalation Protocol in [OPERATING-RULES](../../docs/OPERATING-RULES.md) when two sources conflict).
5. **Write the run summary** as an Inbox report note (slug `curate-report`, tag `workflow/needs-review`): what was refreshed or re-verified directly, and every proposal from steps 2–4 with a one-line rationale each.
6. **Finish:** `brain index`, `validate --check-index` at zero errors, commit, push.

## Rules

- Outcomes 1–2 are executable; outcomes 3–4 and all lint findings are proposals. When unsure which side a case falls on, it's a proposal.
- Refreshing `expires:` asserts the content is *verified current* — never bump a date without reading the note.
- Don't re-propose what the owner already declined; check earlier curate reports (Inbox and Archives) first.

## References

- `10_Agents/tools/brain/README.md` — the `curate` and `context` commands
- `10_Agents/tools/brain/spec.md` § 14 — signal definitions and tunables
- [CONVENTIONS](../../../00_Meta/CONVENTIONS.md) § Expiration — TTL policy
- [vault-maintenance](../vault-maintenance/SKILL.md) — the mechanical counterpart
