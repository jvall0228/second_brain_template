---
title: "Areas"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-18
expires: 2027-08-11
---

# Areas

Ongoing areas of responsibility — things you maintain but never "finish." Areas have standards to uphold, not outcomes to achieve.

## When to Put Something Here

Ask: **"Is this an ongoing responsibility with a standard to maintain, but no end date?"**

- **Yes** — It's an Area. Put it here.
- **Has a bounded outcome and target** — It's a Project. See [README](../04_Projects/README.md).
- **Just reference material, no responsibility** — It's a Resource. See [README](../06_Resources/README.md).
- **No longer relevant** — Archive it. See [README](../07_Archives/README.md).

The key test: Will this still matter in a year, with no "done" state? If yes, it's an Area.

Examples: Health & Fitness, Finances, Home, Career Development.

One Project may advance several Areas, and one Area may own several Projects. Project entrypoint `area/*` tags are authoritative; `brain projects --write-rollups` derives each Area's `## Active Projects` list from them.

## Structure

Each Area gets its own directory with an exact-uppercase entrypoint:

- `05_Areas/<area-name>/AREA.md` — canonical entry note for the Area
- Supporting notes inside the Area directory use descriptive kebab-case filenames.
- `AREA.md` and its supporting notes carry `area/<area-name>` membership.
- Nested organizational directories use `README.md`; the PARA root remains `05_Areas/README.md`.

## Progressive Wiki Layer

Every Area begins with `AREA.md`. When an Area spans multiple sources, durable entities, changing claims, or repeated reconciliation, it may adopt the [Area Wiki Specification](../00_Meta/area-wiki-spec.md):

- `AREA.md` remains the curated index and start page; do not add a parallel `index.md`.
- Supporting notes synthesize entities, concepts, important sources, plans, and material history using existing vault note types.
- Evidence stays in its owning system or source note; Area notes cite and reconcile it.
- Simple Areas keep only the notes they need. Empty wiki scaffolding is discouraged.

## Contents

- [Example Area](example-area/AREA.md) — Sample area showing the structure. Delete once you've seen the pattern.

## Related

- [INDEX](../00_Meta/INDEX.md) — Full vault map
- [template-area](../09_Templates/template-area.md) — Template for new areas
- [Project and Area Contract](../10_Agents/docs/project-area-contract.md) — Relationship and rollup rules
