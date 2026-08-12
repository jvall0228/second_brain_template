---
title: "Template Variants"
tags:
  - type/meta
  - audience/agent
  - audience/human
updated: 2026-08-11
---

# Template Variants

Context-specific **source material** for fork-time template specialization (issue #12, option 2). During [onboard-owner](../../10_Agents/skills/onboard-owner/SKILL.md)'s context-specialization step, a **work**-context answer rewrites the shipped periodic templates in `09_Templates/` **in place** from the matching file here — template paths never change, so everything that resolves templates by stable name (`daily_note.py`, the daily-log and periodic-review skills, snippet generation) keeps working untouched.

| Variant source | Rewrites | Work-context difference |
|----------------|----------|-------------------------|
| `work-daily-log.md` | `09_Templates/template-daily-log.md` | No Mood/Health sections; adds Standup, Blockers, Decisions, Meeting Notes |
| `work-weekly-review.md` | `09_Templates/template-weekly-review.md` | No Health/Mood/Sleep status; adds Wins, Blockers & Risks, Decisions Log |

Omitting mood/health at specialization time is data-sensitivity enforcement **by construction** (PRD §16.2): an employer-visible fork never ships sections that invite personal health content.

## Contract: variants are not templates

- Files here are **outside the resolve-by-name template contract** (PRD §12). Nothing instantiates them directly; only onboard-owner reads them, as raw material.
- They are **excluded from VS Code snippet generation**: `10_Agents/tools/vscode/gen_snippets.py` globs `template-*.md` at the top level of `09_Templates/` only, and a test pins that this directory never reaches the generated snippets. Once specialization has rewritten the real templates, the pre-commit hook's snippet regeneration carries the specialized content to the VS Code surface automatically (PRD §6.5 parity).
- The template-placeholder frontmatter exemption (spec §10.3, `09_Templates/**`) applies here recursively, so variant files carry the same `{{…}}` placeholder frontmatter as the templates they mirror.
- For the upstream sync skill (issue #6): specialized templates in `09_Templates/` are **owner content, not template machinery** — never backfill upstream template updates over them.

## Related

- [README](../README.md) — Template selection guide and placeholder syntax
- [onboard-owner](../../10_Agents/skills/onboard-owner/SKILL.md) — The specialization step
