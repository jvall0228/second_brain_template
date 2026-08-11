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

## 2026-08-11 — Harness Support Tiers

- Recorded the target harness support list in [[00_Meta/prd]] §8.3: **P0** — Claude Code (CLI, web, desktop app), Codex (CLI, web, desktop app), Opencode, Pi, plus universal standards + protocols as a first-class standards track (unlisted harnesses bootstrap via the `AGENTS.md` convention, MCP, and portable skills with no bespoke adapter); **P1** — Cursor, Copilot, Muse Code.
- Rescoped milestone M6 accordingly: harness adapters for all four P0 harnesses and the standards track (was "at least one harness (Claude Code)"), with P1 as a second wave.

## 2026-08-11 — AGENTS.md Becomes the Entrypoint

- Retired `CONTEXT.md`: its content now lives in `AGENTS.md`, the standard cross-harness agent entrypoint (git history preserved via rename).
- Replaced the symlink aliases with a thin one-line `CLAUDE.md` containing only the `@AGENTS.md` memory-import line — Claude Code auto-loads it and injects the entrypoint's contents; other harnesses read `AGENTS.md` directly. As a one-line adapter, `CLAUDE.md` is exempt from the frontmatter requirement (see [[00_Meta/conventions]]) but follows canonical change control.
- Updated every reference across the vault (PRD §8 rewritten as "Universal agent entrypoint" with the decision history; bootstrap sequences, index, conventions' entrypoint exceptions, READMEs, operating rules, status).

## 2026-08-11 — PRD v2 + Spec Alignment

Resolved the findings of the spec review in `2026-08-11-prd-review.md` (then in the Inbox, since archived to `07_Archives/inbox/`; applied with explicit human approval):

- Rewrote [[00_Meta/prd]] as revision 2.0: kebab-case paths throughout, milestone status recorded (M0–M4 done, M5–M6 not started), `brain` CLI marked as planned, shipped surface documented (Journal subtree, `10_Agents/solutions/`, extra profile notes and templates), template phase described, and new sections for data sensitivity, concurrency, and validation. Tagged the PRD `workflow/canonical`.
- Declared the tag table in [[00_Meta/conventions]] the authoritative taxonomy; synced the PRD and the entrypoint (then `CONTEXT.md`, now [[AGENTS]]) to it (added `topic/*` to its summary).
- Recorded decisions: Zettelkasten home is `06_Resources/` (`type/zettel`); the milestone write-permission ladder is unadopted roadmap (Inbox-first plus the `10_Agents/solutions/` carve-out is the active policy); root aliases ship as symlinks; `00_Meta/status.md` is deliberately non-canonical and agent-updatable.
- Added the `updated:`-bump-on-edit duty (conventions, operating-rules checklist) and Inbox filename-collision rules (conventions, task-patterns, Inbox README).
- Templates: added `workflow/draft` to every suggested tag set; added related-link placeholders to the daily/weekly (and placeholder links to monthly/quarterly/yearly) review templates; normalized `template-comparison.md` frontmatter (`type/reference`, placeholder title/date).
- Navigation/docs: the entrypoint gained PARA-root links and the comparison template listing; the index now maps `08_Assets/`; asset lifecycle guidance added to `08_Assets/README`; milestone table added to [[00_Meta/status]]; removed the unshipped community-theme pin from `.obsidian/appearance.json`.

## 2026-08-10 — Template Initialized

- Forked from a personal knowledge vault into a reusable, context-neutral template.
- Removed all owner-specific content (profile data, projects, journal entries, people, resources, archives).
- Reset profile notes (`01_Profile/`) to blank templates with fill-in guidance.
- Seeded one worked example per section (project, area, resource, person, idea, daily log, weekly review) — delete these once you've learned the pattern.
- Preserved structure, conventions, note templates, and agent operating docs.

<!-- Add a dated entry here each time you make a structural change to the vault. -->
