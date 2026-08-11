---
name: sync-upstream
description: Pull upstream second_brain_template releases into this fork - detect pending releases via the template_version config key and upstream release tags, classify every changed file (machinery / owner content / canonical docs), apply per lane, backfill mechanical fixes, and report to the Inbox. Use when the owner asks to check for or adopt template updates. Pull-only, dry-run first.
title: "Skill: Sync Upstream"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Sync Upstream

**CODE stage:** System (outside the loop) — keeps the fork's machinery and spec current with the upstream template.

Keep an adopter's fork current with the upstream `second_brain_template`: detect what upstream has released since this fork last synced, classify every changed file into a handling lane, apply each lane by its own rules, backfill mechanical consequences, and report. Personalization and upstream tracking coexist (issue #22): the fork evolves toward its owner while still receiving template improvements.

## Ground rules

- **Pull-only — never push upstream.** This skill fetches from the upstream template repo and writes only to the fork. Agents never push, open PRs, or write in any form to the upstream public repo unless operating as its owner (issue #22's hard rule). A fork improvement worth generalizing is *suggested to the owner* in the sync report as "worth upstreaming?" — the owner carries it upstream by hand if they choose.
- **Dry-run first, mandatory.** The first pass of every sync is report-only: produce the full classified plan (what would change, lane by lane) as the Inbox report **before any write**. Applying requires the owner's go-ahead on that plan — like `recommended-automations`.
- **Idempotent.** Re-running against the same upstream release produces no new changes and a report saying so. Never re-apply what a previous sync already applied; never re-propose what the owner already rejected (check prior sync reports in the Inbox and `07_Archives/`).
- **Inbox-first report.** The sync report is an `02_Inbox/` note (see [[#Report]]); the owner triages it like anything else.
- **Owner content is never touched**, in any mode, under any flag. When in doubt about a path's lane, treat it as owner content and surface the question in the report.

## Detect

Before classification, resolve the current environment with `brain env detect
--json`. If registered environments exist and matching fails, stop before
reading environment content or writing a report. Treat every non-current
`10_Agents/environments/<slug>/` path as opaque owner content: report metadata
only, never diff or serialize its contents. `.second-brain/` is ignored local
state and must never be staged, classified, or proposed upstream.

Upstream version signaling (accepted design, issue #6): the fork records the upstream release it has adopted in the `template_version` key of [[00_Meta/config.yaml]] (spec §15.3, read via `brain config`); upstream marks each template release with a git tag (`template-v*`).

1. **Upstream remote.** Look for a git remote named `upstream` pointing at the template repo. If none is configured, this is a documented one-time setup step — propose it in the report and stop:
   ```
   git remote add upstream https://github.com/<template-owner>/second_brain_template.git
   ```
2. **Fetch tags:** `git fetch upstream --tags` (fetch only — see ground rules).
3. **Read the fork's recorded version:** `python3 10_Agents/tools/brain/brain.py config --json` → `templateVersion`. If unset, the fork predates version signaling: propose an initial baseline in the report (the newest upstream tag whose tree the fork already contains, or a full first-sync review) rather than guessing.
4. **Compare against upstream release tags** (`git tag -l 'template-v*'` on the upstream remote, version-sorted). The pending work is the tag-to-tag diff from the recorded version to the newest release — semantic release units, not raw commit soup: `git diff --name-status <recorded-tag>..<newest-tag>`.
5. **Edge cases:**
   - **Upstream has no tags** (it predates its own release duty): fall back to `00_Meta/VERSION` in the upstream tree if upstream ships one (the accepted design's stopgap the config key absorbs); if neither exists, diff against `upstream/main` and say so in the report — the sync still works, it just loses release granularity.
   - **Fork ahead of upstream** (recorded version is the newest tag, or local commits touch synced paths): nothing to pull; report "up to date" plus any fork-local divergence on machinery paths as "worth upstreaming?" candidates.
   - **Fork behind by several releases:** walk the whole span in one classified diff, but report the per-release changelog so the owner sees what each release brought.

## Classify

Every path in the upstream diff is sorted into exactly one lane by the tables below. **The path map covers every top-level path in the repo; the overrides table refines within them; the most specific matching rule wins.** A diff path matching no row is a defect — stop and add the row (this table is test-enforced).

Lanes:

- `machinery` — template plumbing. Safe to sync directly.
- `owner-content` — the owner's data. **Never touched.**
- `canonical-docs` — §6.3 change-controlled spec/meta docs. Changes are **proposed via PR**, never direct-committed.

### Path map

| Path | Lane |
|------|------|
| `.claude/` | machinery |
| `.extern/` | owner-content |
| `.gitattributes` | machinery |
| `.githooks/` | machinery |
| `.github/` | machinery |
| `.gitignore` | machinery |
| `.gitmodules` | owner-content |
| `.obsidian/` | machinery |
| `.vscode/` | machinery |
| `00_Meta/` | canonical-docs |
| `01_Profile/` | owner-content |
| `02_Inbox/` | owner-content |
| `02_Outbox/` | owner-content |
| `03_Journal/` | owner-content |
| `04_Projects/` | owner-content |
| `05_Areas/` | owner-content |
| `06_Resources/` | owner-content |
| `07_Archives/` | owner-content |
| `08_Assets/` | owner-content |
| `09_Templates/` | machinery |
| `10_Agents/` | machinery |
| `AGENTS.md` | canonical-docs |
| `CLAUDE.md` | canonical-docs |
| `README.md` | canonical-docs |

### Overrides

| Path | Lane | Why |
|------|------|-----|
| `00_Meta/config.yaml` | owner-content | Per-fork policy record (spec §15.1) — upstream grammar/comment changes are proposals at most |
| `00_Meta/changelog.md` | owner-content | The fork's own history, not the template's |
| `00_Meta/status.md` | owner-content | The fork's own state |
| `09_Templates/` templates onboard-owner actually rewrote from `variants/` | owner-content | Issue #12: a work-context fork owns the periodic templates the specialization stage rewrote in place (currently `template-daily-log.md` and `template-weekly-review.md`; detectable as diverged from upstream) — backfilling upstream updates over them would reintroduce the personal sections, so upstream changes to them become proposals. Periodic templates that were **never rewritten** stay machinery; the cross-cutting divergence rule governs them like any other file |
| `10_Agents/solutions/` | owner-content | The fork's learned solution notes |
| `10_Agents/environments/` | owner-content | Issue #15: per-environment inventories belong to the fork |
| `10_Agents/docs/` | canonical-docs | Operating rules and agent docs are §6.3 change-controlled |
| `10_Agents/docs/rejected-proposals.md` | owner-content | Append-only agent log (self-improve's memory) — fork-local history; sync never overwrites it |
| `10_Agents/components/` | machinery | First-party recommended-component registry, README, and vault-config presets — template machinery, synced directly. The human-facing catalog `06_Resources/recommended-skills.md` stays owner-content by its path-map lane, and `.gitmodules`/`.extern/` above are owner-content: re-tracking or advancing a third-party component is a curated owner decision, so sync proposes and never auto-advances it |

### Cross-cutting rules (apply after path lanes)

- **Personalized content (issue #22):** an upstream change to a file the fork has locally diverged from — in *any* lane — is a **conflict**, surfaced as a proposal in the report (machinery conflicts may ride the PR as explicit diffs), never an overwrite. Detect divergence by comparing the fork's copy against the *old* upstream version: identical → clean apply; diverged → proposal.
- **Pruned modules (issue #32):** paths the fork deliberately deleted are **never re-added**. New upstream modules/directories the fork has never had are **offered as opt-in** in the report, not auto-adopted.
- **Person notes and other owner data inside otherwise-synced directories** stay owner content wherever they live — lane by content ownership, not just by prefix, when the two disagree (and record the disagreement in the report so the table can grow a row).

## Apply

Only after the dry-run report is approved:

- **machinery** — apply directly on a sync branch and commit (normal non-canonical change control, §6.3).
- **canonical-docs** — the sync session opens a **PR** containing the canonical-doc changes (per §6.3 canonical notes require PR or explicit human approval; the sync session never direct-commits them). Machinery and canonical changes may share one PR when the owner prefers a single review unit.
- **owner-content** — never applied. Upstream changes here are listed in the report as skipped (with the reason), plus any that look like genuine template fixes flagged for the owner to hand-apply.
- Update `template_version:` in `00_Meta/config.yaml` to the newly-adopted release tag as part of the same change set (it rides the PR, since the config file is treated as §6.3 change-controlled).

## Backfill

Where a new upstream convention applies to existing fork content (a new frontmatter field, tag namespace, validate rule):

1. Run the mechanical regeneration steps: `python3 10_Agents/tools/brain/brain.py index` and `python3 10_Agents/tools/vscode/gen_snippets.py` (the pre-commit hook does both, but run them explicitly so the diff is reviewable).
2. Generate the mechanical fixes for fork content the new convention now covers — **owner-content files still are not edited**; convention gaps in owner content become a checklist in the report instead.
3. **Prove with `python3 10_Agents/tools/brain/brain.py validate` — 0 errors** before committing; run the test suite (`python3 10_Agents/tools/run_tests.py`).
4. Document the backfill pass (what was regenerated, what was fixed, what remains for the owner) as a section of the sync report.

## Report

Every run — dry-run or apply — ends with a sync report note in `02_Inbox/`, written per the `inbox-capture` rules:

- Filename `YYYY-MM-DD-upstream-sync-report.md` (collision suffix per inbox-capture).
- Frontmatter: `title`, `tags` (`audience/agent`, `audience/human`, `type/note`, `workflow/draft`), `updated`, and provenance `author:` + `session:` (conventions § Provenance).
- Body sections: **mode** (dry-run or apply) and the release span covered (`<from-tag>..<to-tag>`); **applied** (machinery commits, canonical PR link); **skipped** (every owner-content path with its reason); **conflicts/proposals** (diverged files, opt-in modules, "worth upstreaming?" candidates); **backfill** (regen + validate proof, owner checklist); **needs owner review** (everything gated on a human).

## Upstream release duty

The detect step only works if upstream releases are tagged. Whoever operates the upstream template (the template owner, not fork agents) carries a release duty: each meaningful template release gets an annotated git tag `template-v<MAJOR.MINOR.PATCH>` on the release commit, with the changes summarized in the tag message or release notes. Forks record the adopted tag in `template_version:`; untagged upstream work is invisible to the version comparison and falls back to the branch diff above. (Documented here rather than in the PRD — this skill is the only consumer; promote it to the PRD if more machinery starts depending on it.)

## Steps

1. Detect (above): remote, fetch, recorded version, pending release span. Nothing pending → short "up to date" report; done.
2. Classify the full diff with the tables; zero unclassified paths.
3. **Dry-run report** to the Inbox; stop and wait for the owner's go-ahead.
4. Apply per lane (machinery direct on a sync branch; canonical docs via PR; owner content never), bumping `template_version:`.
5. Backfill: regenerate, fix, `brain validate` 0 errors, tests green.
6. Final report to the Inbox; the owner merges the PR and triages the report.

## References

- [[00_Meta/prd]] §6.3 — change control the apply lanes implement
- `10_Agents/tools/brain/spec.md` §15.3 — the `template_version` config key
- `10_Agents/skills/inbox-capture/SKILL.md` — the report note's write rules
- `10_Agents/skills/recommended-automations/SKILL.md` — the dry-run-first pattern
- Issues #6 (design), #12 (specialized templates), #22 (pull-only + conflicts-as-proposals), #32 (pruned modules)
