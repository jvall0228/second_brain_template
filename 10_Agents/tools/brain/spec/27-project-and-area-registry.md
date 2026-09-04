---
title: "brain Spec §27 — Project and Area registry (`brain projects`)"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 27. Project and Area registry (`brain projects`)

*Section 27 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 27.1 Identity and model

The version-1 entity registry discovers only exact path entrypoints: `04_Projects/<slug>/PROJECT.md`, `07_Archives/projects/<slug>/PROJECT.md`, `05_Areas/<slug>/AREA.md`, and `07_Archives/areas/<slug>/AREA.md`. Directory slugs are kebab-case identities and remain reserved across active/archive roots. Entrypoints carry matching `project/<slug>` or `area/<slug>` tags. Markdown notes inside entity directories carry their owner's membership tag except `README.md` and `type/meta`; Project supporting notes may not carry `area/*`, because Project-to-Area mappings live only on `PROJECT.md`.

Every Project has exactly one of `active`, `deprioritized`, `someday`, or `done`. Active requires one or more resolvable Areas, substantive Outcome and Completion Criteria sections, `target: YYYY-MM-DD`, and `target_status: estimated|confirmed`. Inactive states reject active target fields. Overdue is an attention finding, not an invalid lifecycle. Done requires `closed: YYYY-MM-DD` and substantive `## Final Outcome`; under `04_Projects/` it is archive-pending. Active/archive slug collisions, unknown memberships, nonstandard standalone entrypoints, malformed targets, conflicting lifecycle, and missing mappings/criteria are findings.

## 27.2 Inventory and rollups

`brain projects` rebuilds the working-corpus registry and lists only canonical active Projects, once each, with all Areas, target/status, criteria presence, overdue, and attention. `--json` returns `{schemaVersion: 1, projects, findings, rollups}`. The command bypasses environment selection because shared entity identity is environment-independent.

Area `## Active Projects` sections are derived from active Project entrypoint mappings. Preview reports source/result digests for every changed Area plus structured blockers without mutating or failing merely because a restricted Project maps to an unrestricted Area. Blockers name only the public Area for that privacy boundary; a restricted Project mapping to a restricted Area is not a blocker — that rollup proceeds normally, since disclosure stays inside the already-restricted Area note. Explicit `--write-rollups` refuses while any blocker remains, then compare-and-swap replaces each authenticated Area note through a held parent-directory descriptor while preserving all prose outside the exact section; a second run is a no-op. A later failure rolls back only still-recognized installed generations. Concurrent owner edits are preserved, and an incomplete safe rollback returns the distinct `project-rollup-recovery-required` response for manual inspection. Validation is bidirectional: a named Area must list its active Project, and a rollup may not contain an inactive, archived, or unmapped Project.

## 27.3 Consumers and validation posture

Home and AYMT build the registry from their already privacy-filtered immutable snapshot; they do not reread excluded note bodies. `compute_report` retains taxonomy resolution but exempts `project/*` and `area/*` identities from generic single-use and near-duplicate hints. `validate` emits registry findings as warnings so ordinary edits remain possible; focused migration and release verification may require the Project/Area warning family to be empty.

## 27.4 Whole-directory archive

`brain archive-project <slug>` is a zero-write version-2 plan. It requires the canonical active-root entrypoint to carry exactly `status/done`, no target fields, a closeout date/final outcome, preserved identity/mapping tags, no active Area rollup, no unresolved Project membership finding, an absent destination, and a completely tracked regular-file directory. It inventories nested notes and assets, blocks affected legacy/unresolved links, and source-hashes every rewritten note without serializing note prose. The public plan binds `planId` to every moved path, old/new link destination, source/result path, line, and digest, with bounded human output and the full inventory in `--json`. It retargets inbound backlinks and rebases outbound, internal, nested, fragment, asset, and titled Markdown links for `07_Archives/projects/<slug>/` while preserving labels and title suffixes.

Mutation requires both `--write` and `--approve-archive`, POSIX-safe filesystem primitives, Git, and a completely clean worktree/index. Git subprocesses discard ambient repository, object-store, worktree, config, and index selectors and resolve the vault-bound index before planning. The command exclusively owns and durably publishes a private journal, snapshots the whole source, every edited backlink, committed index, and raw Git index into ignored authenticated rollback evidence, then reauthenticates bytes, modes, identities, plan, journal ownership, and each recovery target before mutation. Descriptor-relative guarded operations move the directory and install exact hashed edits. The command writes planned bytes as Git blobs, precomputes and installs only recognized Git-index generations, durably records the generated vault-index digest before installing it, stages exactly the planned move/backlinks/index, and runs `validate --check-index`; it never rereads working-tree content as staging authority. Any exception or failed validation restores only recognized transaction states. `--recover` requires the matching slug, schema, plan, confined paths, intact snapshots, and recognized live generations; it preserves any foreign or concurrently changed content and returns the distinct `project-archive-recovery-required` error when owner inspection is necessary. Success removes the journal before deleting private transaction evidence but leaves the exact archive staged, so Git remains the rollback path until commit. A cleanup failure after that committed boundary returns success with bounded `cleanupWarnings` and retained evidence for later removal rather than misreporting a rolled-back write.
