---
title: "brain Spec §16 — Health report (`brain report`) — issue #16"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# 16. Health report (`brain report`) — issue #16

*Section 16 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

A read-only synthesis of the in-memory index (§9's usual `walk_corpus` + `build_index` — **no new parsing**, no network, no git) into the five vault-health sections below, for the `periodic-review` and `vault-maintenance` skills and the "Brain: Health Report" VS Code task. Exit code is always `0` on success (the report informs; `validate` judges); `1` only for an operational error (a malformed `--since`). Ordering inside every section is deterministic; the human output prints the sections in the order listed here (most-actionable-first).

## 16.1 Sections

All tag reads in this section are **frontmatter tags only** (a bare-scalar `tags:` coerced to one element per §4.5; body `#tags` are informal, mirroring §10.2), and values containing `{{` (template placeholders) are ignored.

1. **Stale-active** (`staleActive`): notes carrying the frontmatter tag `status/active` whose `updated:` is **strictly more than** `stale_days` days (default 30) before today. Notes with `updated: null` cannot be aged and are skipped (`validate` already flags `missing-updated`/`invalid-updated`). Rows `{daysOld, path, title, updated}`, sorted oldest-first (`daysOld` descending, then path).
2. **Orphans** (`orphans`): notes with **zero backlinks and zero outgoing non-placeholder links** — fully disconnected, per the issue's definition. Excluded as legitimately leaf-like: any note whose basename is `README.md`, `AGENTS.md`, or `CLAUDE.md`, and everything under `07_Archives/` or `09_Templates/`. Sorted path list. (Distinct from `curate`'s inbound-only orphan signal, which serves the curation charter; this section measures disconnection.)
3. **Inbox aging** (`inboxAging`): every note under `02_Inbox/` except its `README.md`, bucketed by age in days. A note's **capture date** is the `YYYY-MM-DD` filename prefix of its basename when present and a valid calendar date (`source: "filename"`), else its `updated:` value (`source: "updated"`), else unknown (`source: "unknown"`, `ageDays: null`). Age = today − capture date, floored at 0. Buckets, fixed order: `0-7d` (≤ 7), `8-30d`, `31-90d`, `90+d`, `unknown`; each holds `{ageDays, path, source}` rows sorted by path. `triageDebt` additionally lists the paths whose age is strictly greater than `inbox_days` (default 14).
4. **Tag drift** (`tagDrift`): frontmatter tag usage vs the §10.1 conventions taxonomy, read by the **same** `load_taxonomy` machinery `validate` uses (consistency by construction). Tags are counted once per note that carries them, over the §16.3 note universe. `taxonomyReadable: false` (with all three lists empty) when the table is unreadable — `validate` owns that error. Otherwise: `unknown` — rows `{count, reason, tag}` sorted by tag, `reason` ∈ `not-namespaced` | `unknown-namespace` | `unknown-value` (closed namespaces only); `singleUse` — sorted tags in **open** namespaces used by exactly one note (near-duplicate bait, e.g. `topic/software-tools` beside `topic/software`); `nearDuplicates` — rows `{namespace, values: [shorter, longer]}` for pairs of distinct open-namespace values where, under the §6 folding rule, the shorter (≥ 2 chars, strictly shorter) matches the longer by **strict prefix** (`tool`/`tools`, `brand`/`branding`), **whole hyphen-segment run containment** (`art`/`ai-art`), or **segment-initial acronym** (`ml`/`machine-learning`); sorted by namespace then value pair. The original in-order-subsequence clause (which also caught single-word abbreviations, the issue's `sw`/`software`) was retired: it matched unrelated tags whose letters merely appear in order (a short tag scattered as a subsequence of an unrelated longer one), producing mostly false positives, while every genuine pair falls under the three rules above.
5. **Unresolved links** (`unresolvedLinks`): `{count, links}` where `links` rows are `{line, path, target}` for every non-placeholder link with `resolved: null`, over the §16.3 note universe, sorted by path, line, target — the same population `validate` errors on, given trend context here.

## 16.2 JSON shape

Top-level keys (always present): `inboxAging` (`{buckets, triageDebt}` with all five bucket keys always present), `orphans`, `since` (the `--since` date string or `null`), `staleActive`, `tagDrift` (`{nearDuplicates, singleUse, taxonomyReadable, unknown}`), `thresholds` (`{inboxDays, staleDays}` — the **effective** integers after config merge), `unresolvedLinks`. Emitted via the standard `--json` path. Output is a pure function of the tree, the config, today's date, and `--since` — no timestamps, mtimes, or environment data — so two runs on the same day are byte-identical.

## 16.3 `--since YYYY-MM-DD`

Review-period scoping. `--since` restricts **exactly two** sections — **tag drift** and **unresolved links** — to the notes whose `updated:` is on or after the given date (the changes attributable to the period under review; notes with `updated: null` are excluded from a scoped universe since they cannot be attributed). **Stale-active, orphans, and Inbox aging always cover the whole vault**: they measure accumulated debt, which a review must see regardless of period. A value that is not a real `YYYY-MM-DD` calendar date is an operational error (exit 1). Without `--since`, the note universe for every section is the full working corpus.

## 16.4 Thresholds

`stale_days` and `inbox_days` are read from the `report` config key (grammar and defaults in §15.3) via `report_thresholds(config)`; with no config file, both stay at their built-in defaults (`REPORT_STALE_ACTIVE_DAYS = 30`, `REPORT_INBOX_TRIAGE_DAYS = 14` — module constants beside the §14 tunables). Per §15.1 the config never influences `index` output, and the report is synthesis-only: nothing here feeds back into `validate` severities.
