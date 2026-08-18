---
title: "Projects"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-18
expires: 2027-08-11
---

# Projects

Bounded efforts with a specific outcome and target. Active, deprioritized, someday, and archive-pending Projects remain here; only an approved directory move sends done work to [Archives](../07_Archives/README.md).

## When to Put Something Here

Ask: **"Does this have a specific outcome and a finish line?"**

- **Yes** — It's a Project. Give it a target, completion criteria, and one or more Areas.
- **No deadline, but ongoing responsibility** — It's an Area. See [README](../05_Areas/README.md).
- **No outcome, just reference material** — It's a Resource. See [README](../06_Resources/README.md).
- **Completed or cancelled** — Close it now; archive the directory separately with approval.

The key test: Can you say exactly what “done” means? If yes, it can be a Project. If it is established but intentionally paused, use `status/deprioritized`; reserve `status/someday` for an uncommitted possibility.

## Structure

Each Project gets its own directory with an exact-uppercase entrypoint:

- `04_Projects/<project-name>/PROJECT.md` — canonical entry note for the Project
- Supporting notes inside the Project directory use descriptive kebab-case filenames.
- `PROJECT.md` carries `project/<project-name>`, every related `area/*` tag, `target`, and `target_status`; supporting notes carry only the Project membership tag.
- Nested organizational directories use `README.md`; the PARA root remains `04_Projects/README.md`.

## Inventory and Lifecycle

Run `brain projects` for the canonical active inventory and `brain projects --write-rollups` to reconcile Area rollups. `01_Profile/NOW.md` is a curated priority view, not the complete registry.

- [Example Project](example-project/PROJECT.md) — Sample active Project showing the structure. Delete once you've seen the pattern.

## Related

- [INDEX](../00_Meta/INDEX.md) — Full vault map
- [template-project](../09_Templates/template-project.md) — Template for new projects
- [template-decision-record](../09_Templates/template-decision-record.md) — Template for project decisions
- [Project and Area Contract](../10_Agents/docs/project-area-contract.md) — Machine-enforced identity, lifecycle, mapping, and closeout rules
