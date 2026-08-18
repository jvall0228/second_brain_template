---
title: "Archives"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-18
---

# Archives

Completed, cancelled, superseded, or no-longer-relevant items. Archives are cold storage for content worth retaining after its active lifecycle ends.

## When to Put Something Here

Ask: **"Is this completed, cancelled, or no longer actively relevant?"**

- **Yes** — Close it in place first, then archive its directory through the separately approved move.
- **Still active or intentionally deprioritized** — It remains a Project. See [README](../04_Projects/README.md).
- **Still an ongoing responsibility** — It's an Area. See [README](../05_Areas/README.md).
- **Still useful as reference** — It's a Resource. See [README](../06_Resources/README.md).

Deprioritized and someday Projects are not archived merely for being inactive. A done Project under `04_Projects/` is valid archive-pending work until the owner approves the structural move.

## Structure

Mirror the source structure:
- `07_Archives/projects/` — completed or cancelled projects
- `07_Archives/areas/` — areas you've stepped away from
- `07_Archives/resources/` — outdated reference material
- `07_Archives/inbox/` — Inbox items that served their purpose without migrating to PARA
- `07_Archives/outbox/` — shipped (or abandoned) Outbox packets, moved here with `status/done` — see [README](../02_Outbox/README.md)
- `07_Archives/assets/` — large or obsolete assets moved from `08_Assets/`

After closeout records `closed:` and `## Final Outcome`, preview with `brain archive-project <slug>`. The explicit `--write --approve-archive` path moves the whole directory, preserves historical `project/*` and `area/*` tags, repairs relative links and backlinks, regenerates the index, stages the exact change, and validates as one rollback-capable transaction. See the [Project and Area Contract](../10_Agents/docs/project-area-contract.md).

## Contents

- [PRD Review (2026-08-11)](inbox/2026-08-11-prd-review.md) — Spec review record; findings resolved in PRD revision 2.0
- [expires: Backfill Review (2026-08-11)](inbox/2026-08-11-expires-backfill-report.md) — Resolved: decision-record exemption, harness-research split, orphan-README links

## Related

- [INDEX](../00_Meta/INDEX.md) — Full vault map
