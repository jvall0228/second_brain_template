---
title: "Project and Area Contract"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-18
expires: 2027-08-18
---

# Project and Area Contract

This is the machinery-lane contract for discovering, relating, reviewing, closing, and archiving Projects and Areas. Human-facing PARA guidance stays in the [Projects](../../04_Projects/README.md), [Areas](../../05_Areas/README.md), and [Archives](../../07_Archives/README.md) guides.

## Entity Identity

- A Project exists only at `04_Projects/<slug>/PROJECT.md` or `07_Archives/projects/<slug>/PROJECT.md`.
- An Area exists only at `05_Areas/<slug>/AREA.md` or `07_Archives/areas/<slug>/AREA.md`.
- The directory slug is the entity identity. It is kebab-case and remains reserved after archival.
- The entrypoint carries its matching `project/<slug>` or `area/<slug>` tag. Every other Markdown note beneath the entity directory carries the same membership tag, except `README.md` and `type/meta` notes.
- A Project entrypoint alone carries its `area/*` mappings. Supporting Project notes use `project/*`, not `area/*`; this prevents every supporting note from becoming a second relationship assertion.
- Cross-directory membership is explicit. Agents do not infer it from prose or incidental links.

## Relationship Model

Projects may map to multiple Areas; Areas may own multiple Projects. Project entrypoint `area/*` tags are the machine-readable source of truth. The Project's `## Areas` links are the human-readable view.

Each Area's `## Active Projects` section is a derived reciprocal rollup. Preview the canonical inventory, drift, and blockers with `brain projects`; apply only the owned rollup sections with `brain projects --write-rollups`. Writes require unchanged source generations and preserve concurrent owner edits; surrounding Area prose remains human-owned. A restricted Project never enters an unrestricted Area rollup.

## Project Lifecycle

Every Project carries exactly one lifecycle tag:

| Status | Meaning | Active target fields | Active rollups |
|---|---|---|---|
| `status/active` | Established work being advanced now | Required | Included |
| `status/deprioritized` | Established work intentionally paused by a stronger priority, dependency, or resource constraint | Removed | Excluded |
| `status/someday` | Uncommitted possibility, not yet established work | Removed | Excluded |
| `status/done` | Completed, cancelled, or superseded | Removed | Excluded |

`parked` and `icebox` are retired synonyms; normalize reviewed established work to `status/deprioritized`. Reactivation replaces the inactive status with `status/active` and sets a new target. Deprioritization records the previous target and reason in `## Log` before removing active target fields.

## Active Project Contract

An active Project has:

- one or more resolvable `area/*` mappings;
- a specific `## Outcome`;
- at least one non-placeholder item in `## Completion Criteria`;
- flat frontmatter `target: YYYY-MM-DD` and `target_status: estimated|confirmed`.

`expires:` remains the note-curation TTL; it is never the Project target. When the owner has not supplied a date, an agent may set a defensible working date and mark it `estimated`. An estimate is still a firm review date. Record target changes in `## Log`; an agent-made change resets the status to `estimated`.

An overdue Project remains structurally active. Reviews must confirm, recalibrate, deprioritize, or close it. `brain projects`, Home, and AYMT visibly distinguish estimated and overdue targets.

## Review and Derived Surfaces

`brain projects --json` is the canonical active-work inventory. It lists each active Project once with all Areas, target state, completion-criteria presence, overdue state, and attention signals. `01_Profile/NOW.md` is a curated priority view, not a competing complete registry, and may not list inactive Projects.

Home and AYMT consume the same privacy-filtered entity registry. They do not promote supporting notes or stale NOW bullets into Projects, and they suppress tasks in inactive Project directories.

Validation constructs the path-based registry before checking identity tags. Project/Area findings are warning-only during ordinary editing. Focused migration and release checks require zero unresolved membership and lifecycle warnings. Free-form `project/*` and `area/*` identities are exempt from generic single-use and near-duplicate tag-drift hints, but must resolve to canonical entities.

## Closeout and Archive

Completion, cancellation, or supersession immediately replaces every other lifecycle with `status/done`, removes target fields, adds `closed: YYYY-MM-DD`, records a substantive `## Final Outcome`, and reconciles Area rollups and curated active navigation. A done Project under `04_Projects/` is valid archive-pending work.

Moving it to `07_Archives/projects/` is a separate owner-approved operation. `brain archive-project <slug>` previews the exact move and link edits; use `--json` to inspect every path and digest. Explicit `--write --approve-archive` requires a clean worktree, moves the whole directory, stages only plan-bound blobs, preserves historical tags, repairs inbound/outbound/nested/attachment links, regenerates the index, and validates; failure restores only authenticated transaction state. `--recover` requires the matching slug and intact evidence, and refuses foreign or concurrently changed content for owner inspection. The staged Git change remains the rollback path until commit. Never perform the directory move as an unreviewed side effect of setting `status/done`.

## Normalization

Standalone files such as `04_Projects/name.md`, duplicate active/archive slugs, and Project-shaped supporting notes are migration candidates, not alternate valid entity shapes. Inventory every candidate, assign one disposition, then normalize directories, tags, relationships, targets, and rollups before declaring migration complete.
