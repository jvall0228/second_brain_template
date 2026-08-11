---
title: "Changelog"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-08-11
---

# Changelog

Notable structural changes to the vault. For individual file history, use `git log`.

## 2026-08-11 — PRD v2 + Spec Alignment

Resolved the findings of the spec review in `02_Inbox/2026-08-11-prd-review.md` (applied with explicit human approval):

- Rewrote [[00_Meta/prd]] as revision 2.0: kebab-case paths throughout, milestone status recorded (M0–M4 done, M5–M6 not started), `brain` CLI marked as planned, shipped surface documented (Journal subtree, `10_Agents/solutions/`, extra profile notes and templates), template phase described, and new sections for data sensitivity, concurrency, and validation. Tagged the PRD `workflow/canonical`.
- Declared the tag table in [[00_Meta/conventions]] the authoritative taxonomy; synced the PRD and [[CONTEXT]] to it (added `topic/*` to CONTEXT's summary).
- Recorded decisions: Zettelkasten home is `06_Resources/` (`type/zettel`); the milestone write-permission ladder is unadopted roadmap (Inbox-first plus the `10_Agents/solutions/` carve-out is the active policy); root aliases ship as symlinks; `00_Meta/status.md` is deliberately non-canonical and agent-updatable.
- Added the `updated:`-bump-on-edit duty (conventions, operating-rules checklist) and Inbox filename-collision rules (conventions, task-patterns, Inbox README).
- Templates: added `workflow/draft` to every suggested tag set; added related-link placeholders to the daily/weekly (and placeholder links to monthly/quarterly/yearly) review templates; normalized `template-comparison.md` frontmatter (`type/reference`, placeholder title/date).
- Navigation/docs: CONTEXT gained PARA-root links and the comparison template listing; the index now maps `08_Assets/`; asset lifecycle guidance added to `08_Assets/README`; milestone table added to [[00_Meta/status]]; removed the unshipped community-theme pin from `.obsidian/appearance.json`.

## 2026-08-10 — Template Initialized

- Forked from a personal knowledge vault into a reusable, context-neutral template.
- Removed all owner-specific content (profile data, projects, journal entries, people, resources, archives).
- Reset profile notes (`01_Profile/`) to blank templates with fill-in guidance.
- Seeded one worked example per section (project, area, resource, person, idea, daily log, weekly review) — delete these once you've learned the pattern.
- Preserved structure, conventions, note templates, and agent operating docs.

<!-- Add a dated entry here each time you make a structural change to the vault. -->
