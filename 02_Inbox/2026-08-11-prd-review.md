---
title: "PRD Review — Spec vs. Shipped Template"
tags:
  - type/reference
  - audience/human
  - audience/agent
  - workflow/draft
updated: 2026-08-11
---

# PRD Review — Spec vs. Shipped Template

A structured review of [[00_Meta/prd]] against the vault as shipped. Five review passes ran over distinct dimensions (spec-vs-implementation conformance, internal consistency, cross-document consistency, spec quality, and a scripted frontmatter/link/tag audit); every finding was independently re-verified against the files before inclusion, and claims that failed verification were dropped. Raw findings were then deduplicated into the themes below.

## Verdict

The PRD is a well-conceived spec with a genuinely strong core: the M0 bootstrap loop is minimal and testable, the Inbox-first write-safety model is coherent defense-in-depth, and the portability reasoning (stub aliases, dual-harness entrypoints) is unusually careful. The implementation is also in better shape than the spec: every markdown file in the vault passes the required-frontmatter check, and all real navigation links resolve.

The problem is drift. The PRD contradicts its own naming convention in most of the paths it specifies, directs agents to a `brain` CLI that does not exist, describes a `10_Agents/` layout that was never built while omitting the `solutions/` knowledge base that was, and carries a tag taxonomy and write-permission model that the operative docs (`00_Meta/conventions.md`, `10_Agents/docs/task-patterns.md`) have since replaced. An implementer rebuilding the template from this PRD alone would produce roughly half the shipped product; an agent trusting the PRD over the operative docs would mis-tag notes, hunt for missing tooling, and assume write permissions it does not have.

**Recommended posture:** declare `00_Meta/conventions.md` and the `10_Agents/docs/` files normative for day-to-day behavior, and revise the PRD to match reality — marking unbuilt milestones as future state — rather than treating the PRD as currently authoritative.

## Milestone Reality Check

The PRD gives no milestone status anywhere, and [[00_Meta/status]] never mentions milestones. Actual state:

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Bootstrap minimum (CONTEXT, now, preferences, conventions, aliases, Inbox) | Done (see caveat on blank profile shells below) |
| M1 | Full skeleton + section READMEs | Done |
| M2 | `index.md`, `defaults.md` | Done |
| M3 | Templates + `10_Agents/` docs | Done |
| M4 | Navigation integrity | Done — zero genuinely broken wikilinks |
| M5 | `brain` vault-index CLI at `.tools/brain/` | **Not started** — no `.tools/` exists |
| M6 | Plugin library (`skills/`, `tools/`, `harnesses/`) | **Not started** — none of these directories exist |

## What's Strong

- **M0 is genuinely minimal and falsifiable**, closed by an end-to-end success criterion (agent reads the sequence, writes a conforming Inbox note). This note is itself that test passing.
- **The four-file must-read sequence is honored at every entrypoint** — CONTEXT.md, index.md, and operating-rules.md all route agents through the same four documents; both root aliases resolve to CONTEXT.md.
- **100% frontmatter compliance** — a scripted pass over every markdown file found no note missing `title`, `tags`, or `updated`.
- **No broken navigation** — all 21 unresolved wikilink targets are intentional template placeholders or worked examples.
- **Layered write safety** — Inbox-first default, canonical read-only marking, a propose-via-Inbox protocol, and a self-validation checklist; `task-patterns.md` even anticipates the PRD's aspirational language ("Roadmap items in planning docs do not override this active policy").
- **Portability reasoning** — symlink fragility is anticipated (§3, §7.2) and the shipped symlinks are an explicitly permitted option under §7.2/§17.

## High-Severity Findings

### H1. The spec violates its own naming convention, and its paths don't resolve

§6 mandates kebab-case filenames with no exceptions, yet nearly every path the PRD specifies is capitalized: `01_Profile/Now.md`, `Preferences.md`, `00_Meta/Conventions.md`, `Index.md`, `Agent-Operating-Rules.md`, `Defaults.md`, `Changelog.md`, `10_Agents/docs/Task-Patterns.md`, `07_Archives/Assets/` (prd.md:191–193, 202–204, 231, 246, 250). Worse, the PRD spells its own contractual must-read files two different ways: §5.1 lists them lowercase (prd.md:41–43) while §10.1, §16 M0, and §18 capitalize the same files. The shipped files are all lowercase, so on a case-sensitive filesystem every §10-style path is file-not-found — for paths §11/§13 call "stable contracts." Even the conventional uppercase root files (CONTEXT.md, README.md, aliases) are never carved out as exceptions; that carve-out exists only in conventions.md:33–36.

**Fix:** normalize every path in the PRD to the shipped lowercase names and add the entrypoint-exception rule from conventions.md.

### H2. The contractual bootstrap points agents at tooling that does not exist

The PRD is tagged `audience/agent`, declares §5.1 "contractual," and tells agents in present tense they "can also use the `brain` tool … to query the vault index" (prd.md:45), with §8.3 adding that agents "discover available skills and tools via the `brain` index" (prd.md:142). There is no `.tools/` directory, no `brain` CLI, no `vault-index.json`, and no mention of the tool in any other doc. Similarly, §8.2's normative structure for `10_Agents/` (`skills/`, `tools/`, `harnesses/claude|cursor`) doesn't exist — the directory actually contains `docs/` and `solutions/`. Meanwhile `solutions/` appears nowhere in the PRD despite being a standing agent write destination (`10_Agents/README.md`: "Add a note whenever you solve something worth not re-deriving later") that bypasses the Inbox-first rule the PRD itself defines in §5.2 — the write ladder there only ever contemplates Inbox → Resources → Projects.

**Fix:** future-tense-mark the `brain` references ("Planned, M5 — not yet built"), restate §8.2 as the shipped layout with skills/tools/harnesses as M6 target state, add `solutions/` to the PRD with an explicit write-policy carve-out (or route solution notes through the Inbox).

## Medium-Severity Themes

### M-A. Tag taxonomy drift — the PRD and conventions.md describe different vocabularies

- `status/*`: PRD says `active, on-hold, done, archived` (prd.md:184); conventions.md:72 and CONTEXT.md say `active, someday, done`.
- `workflow/*`: PRD lists `workflow/inbox` (prd.md:183), which exists nowhere else — the Inbox README prescribes `workflow/draft` instead; conventions adds `workflow/review`, which the PRD lacks.
- `topic/*`: a whole namespace defined in conventions.md:70 and used in 6+ notes, absent from PRD §9.4 and CONTEXT.md's tag table.
- `type/*`: the vault uses and documents values (`reference`, `log`, `note`, `idea`, `decision`, `solution`, `area`, …) the PRD never enumerates.
- `workflow/agent-writable`: load-bearing in §5.2 as the Projects opt-in mechanism, but registered in no tag table and used nowhere.

An agent tagging per the PRD emits values the vault's operative conventions don't recognize. **Fix:** sync §9.4 to conventions.md or state explicitly that conventions.md owns the evolving taxonomy.

### M-B. The write-permission model in the spec is contradicted by the operative policy

§5.2 grants "later milestones" (never numbered) direct writes to `06_Resources/` and opt-in `04_Projects/`; §12 requires task-patterns.md to document that ladder. The shipped task-patterns.md:20–22 does the opposite: flat Inbox-only policy, explicit human direction for anything else, and a disclaimer that roadmap items don't override it. Either the ladder was abandoned (then §5.2/§12 should say so) or task-patterns.md is non-compliant (then it needs the ladder). The spec doesn't say which.

### M-C. Template requirements are violated by all shipped templates

- **No template carries any `workflow/*` tag** — §11 requires suggested tag sets "including `type/*` and relevant `workflow/*`"; `grep -rn "workflow/" 09_Templates/` returns zero matches. This also breaks the vault's own default (`workflow/draft` per defaults.md:38 and task-patterns.md:39): a note instantiated from any template lacks the triage signal.
- **`template-daily-log.md` and `template-weekly-review.md` contain no link placeholders** (zero `[[` in either), violating §11's "must include placeholders for links to related notes"; the monthly/quarterly/yearly templates are borderline (a links heading, no placeholder).
- Eleven templates use `updated: {{date}}`, which violates §9.3 as the PRD is written — the placeholder carve-out exists only in conventions.md:58–60.
- Inventory drift: §11 requires 7 templates, 12 ship; CONTEXT.md's list omits `template-comparison.md`, whose own frontmatter (`type/meta`) contradicts the selection guide (`type/reference`).

### M-D. Spec drift — large parts of the shipped template are undocumented

- **`03_Journal/`** is specced as "daily/weekly/monthly logs + reviews" (prd.md:75) but ships `periodic/{daily,weekly,monthly,quarterly,yearly}` plus `ideas/`, `insights/`, `memories/`, `people/`, `plans/`, governed by a subjective-vs-objective routing doctrine that appears nowhere in the PRD.
- **`01_Profile/`** ships four notes the spec never mentions (identity, work, tooling-stack, long-running-themes) — some listed under "Core Context (Agent Bootstrap)" in the index.
- **`00_Meta/status.md` and the root README.md** appear nowhere in the PRD, including §14 (recency) where status.md logically belongs.
- **The template phase itself is unspecified:** §10.1 requires the M0 files to "exist and be meaningful," but `now.md`/`preferences.md` ship as placeholder shells and status.md concedes they're blank. The repo openly being a *template* is fine — but the PRD was never amended to describe the fork-and-fill model, so the shipped state contradicts the spec's M0 guarantee with no bridging text.
- **§18 presents settled decisions as open questions:** the "agents never edit canonical" posture is decided and shipped (operating-rules.md:28, conventions.md:74); the review-cadence question is largely resolved by the five shipped periodic templates.

### M-E. Governance and lifecycle gaps in the spec

- **No milestone status tracking** anywhere (§16 has no states/dates; §17 covers only M0), and no per-milestone acceptance criteria.
- **"Canonical" is never defined** — no criteria, no statement of who assigns/removes the tag, no promotion path — despite gating agent write access.
- **The PRD itself is unprotected:** prd.md and status.md lack `workflow/canonical`, and the change-control table (conventions.md:84–88) allows direct commits to any untagged note — so under the vault's own rules an agent may rewrite the governing spec without review. Every peer foundational doc carries the tag.
- **The recency contract decays:** §14 makes `updated:` the primary signal and conventions.md:101 tells agents *not* to re-read unchanged-`updated:` files, but no doc ever imposes a duty to bump `updated:` on edit — only at creation. Day-level granularity also can't distinguish same-day edits.
- **Frontmatter scope is ambiguous:** §9.1 is titled "Requirement" but says only that notes "support" frontmatter; §9.3 never states which notes the required fields apply to; only CONTEXT.md asserts "every note must."
- **§10.3 is stale:** it still requires `00_Meta/Agent-Operating-Rules.md` although §8.1/§16 M3 declare that location superseded (shipped file: `10_Agents/docs/operating-rules.md`), and the "earlier `00_Meta/Agents/` plan" cited twice has no antecedent in the document.
- **Zettelkasten has no home:** it's a §2 framework goal and a §5.4 migration destination, but §6 assigns it no directory; the template guide lists the zettel destination as "Any" and the Inbox triage list names only the four PARA directories.
- **Unaddressed for a multi-agent, personal-data repo:** concurrent-write/conflict handling (no Inbox filename-collision rule, no pull-before-write guidance); PII/sensitivity rules (the taxonomy anticipates `topic/health` and a `people/` directory of notes about third parties; §9.4's default is "assume all notes are readable"); any validation/enforcement mechanism for the "must" rules (no lint, hook, or CI — only an honor-system checklist); spec versioning (in-place revisions with no revision history); and Inbox triage lifecycle (no ownership/definition of done).

## Minor Findings

- CONTEXT.md's Key Links omit direct links to the PARA roots required by §7.1's "Links to navigation (PARA roots, Inbox, Templates)".
- §15's asset lifecycle guidance (append-only, archive to `07_Archives/Assets/`, relative-path links) is implemented nowhere; `08_Assets/README.md` recommends Obsidian embeds rather than the relative paths §15 specifies.
- `00_Meta/index.md` maps every top-level directory except `08_Assets/`.
- `.obsidian/appearance.json` pins the community theme "Tokyo Night," which is not shipped, so first open falls back to default styling (harmless but untidy for §17's "opens cleanly").
- Canonical change-control strength varies by doc: PRD "prefer PRs" / "unless explicitly allowed" vs conventions "PR or explicit approval required" vs README "read-only."
- CONTEXT.md adds a "Complete bootstrap" tier (index + defaults, "required" for structured notes) beyond the PRD's contractual 4-item sequence — sensible, but the contract never acknowledges the second tier.
- §16 M1/M3 re-deliver directory creation that §6/§10.2 already require at M0.
- The frontmatter examples inside the PRD carry `updated: 2026-02-12`, months older than the document's own `updated: 2026-08-10` — evidence of in-place revision without a changelog entry.
- `2025-W03-review.md` breaks strict kebab-case; the ISO-week exception exists only in conventions.md, not the PRD.
- M5 specifies the brain CLI's core behavior by analogy ("Modeled after Obsidian's MetadataCache") rather than by concrete resolution rules, and gives the tool two homes (`.tools/brain/` at M5, migrated to `10_Agents/tools/` at M6) with the index path undefined after migration.
- §9.4 tells agents notes are readable "unless explicitly restricted," but no restriction mechanism exists (the `restricted/*` namespace is only a §18 maybe).

## Claims Checked and Rejected

Two plausible-looking findings were refuted during verification and are *not* defects: the shipped symlink aliases (§7.2/§17 explicitly permit symlinks as an optional optimization), and the §5.1 "verbatim" wording as a standalone issue (its substance is the casing conflict in H1).

## Prioritized Recommendations

1. **Fix H1:** lowercase every path in the PRD; import the entrypoint-casing exception from conventions.md.
2. **Fix H2:** mark M5/M6 tooling as future state in §5.1/§8; document `solutions/` and its write carve-out.
3. **Add milestone status** to §16 (M0–M4 done; M5/M6 not started) and cross-link `00_Meta/status.md`.
4. **Declare taxonomy ownership:** one line in §9.4 stating conventions.md is authoritative, then sync the values.
5. **Reconcile the write ladder** (§5.2/§12) with task-patterns.md's flat policy — record whichever is intended.
6. **Bring templates into compliance:** add `workflow/draft` to suggested tag sets; add link placeholders to the daily/weekly templates.
7. **Protect the spec:** add `workflow/canonical` to prd.md (and decide deliberately for status.md).
8. **Close the recency loop:** require bumping `updated:` on every edit, in §14 and in the operating-rules checklist.
9. **Document the template phase** (fork-and-fill model, blank profile shells, seeded examples) in the PRD.
10. **Add short sections** for the structural gaps: concurrency/collision rules, data-sensitivity handling, a home for zettels, and a minimal validation story (even if deferred to M5 as a `brain validate` subcommand).
