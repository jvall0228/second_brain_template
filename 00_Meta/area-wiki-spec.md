---
title: "Area Wiki Specification"
tags:
  - type/meta
  - workflow/canonical
  - audience/human
  - audience/agent
updated: 2026-08-18
expires: 2027-08-18
---

# Area Wiki Specification

## Purpose

An Area may maintain a persistent, compounding knowledge layer when its responsibility spans enough sources, entities, or changing claims that a single `AREA.md` is no longer sufficient. New evidence should improve existing understanding rather than force every future query to reconstruct it from raw material.

This is a progressive contract, not mandatory scaffolding. A simple Area keeps `AREA.md` and only the supporting notes it needs. Activate the fuller wiki pattern when at least one is true:

- The Area repeatedly reconciles two or more systems of record.
- It contains several durable entities or concepts with meaningful relationships.
- Claims change independently and need evidence or verification dates.
- The same context is repeatedly reconstructed during questions, planning, or reviews.
- Contradictions, duplicate notes, or stale operating knowledge have become a recurring risk.

## Three Layers

| Layer | Vault adaptation | Ownership rule |
|---|---|---|
| Evidence and sources | Live systems, owned repositories, original documents, external references, and raw captures | Keep the original under its existing owner; an Area ingest does not rewrite it unless separately authorized |
| Area wiki | Cross-linked Markdown synthesis under `05_Areas/<area-name>/` | Humans and agents maintain current understanding through normal write lanes and Git review |
| Schema | This specification plus the Area's `AREA.md` and any domain-specific operating model | Vault rules govern globally; the Area records only its domain additions |

No `sources/` directory is required. Preserve or point to evidence where it naturally lives. Never copy credentials, unnecessary raw identifiers, or large source dumps into the Area merely to make it self-contained.

## Page Roles

The vault reuses its existing note types rather than creating a parallel wiki taxonomy:

| Wiki role | Vault representation |
|---|---|
| Index and start page | `AREA.md` — standard to maintain, current focus, knowledge model, and curated map |
| Entity page | `type/reference` note for a specific system, provider, person, asset, or other durable thing |
| Concept page | `type/reference` within the Area; an atomic evergreen concept belongs as a standalone `type/zettel` in Resources and is linked from the Area |
| Source summary | `type/reference` note for a source important enough to query independently |
| Activity or verification log | `type/log`, append-only and limited to material ingests, reconciliations, and state changes |
| Backlog or operating plan | `type/plan`; contextual tasks remain with the relevant note |

`AREA.md` replaces a separate per-Area `index.md`. Supporting notes use descriptive kebab-case filenames and source-relative Markdown links. When a person, concept, project, or resource already has a canonical home elsewhere in the vault, link it rather than duplicate it inside the Area. Do not create empty entity, summary, or log pages just to satisfy the model.

## Evidence and Frontmatter

All normal frontmatter requirements still apply. Notes whose primary claims depend on external evidence may also use:

```yaml
sources:
  - "source-relative note link, external URL, or named system of record"
verification: verified  # verified | unverified | disputed
verified: YYYY-MM-DD    # required when verification is time-sensitive
```

- `updated` records when the note changed; it does not prove that an external claim was rechecked.
- `verification` describes evidentiary confidence, not actionability. Continue using `status/*` only for the vault's existing active/someday/done lifecycle.
- Domain lifecycle such as planned, active, parked, or retired belongs in prose or a clearly named domain-specific field.
- Cite vault sources with portable relative links. For live systems, name the provider, command class, dashboard, or host check without pasting secret-bearing output.
- Preserve disagreement. A disputed claim names the competing evidence and the check needed to resolve it.

## Ingest Workflow

When durable source material arrives or a live system changes:

1. Identify the source, its owner, its date, and whether it may be retained or only referenced.
2. Read `AREA.md`, search the Area, and prefer updating an existing page over creating a duplicate.
3. Extract the claims, relationships, decisions, uncertainties, and actions that change maintained understanding.
4. Create a source-summary page only when the source is likely to be queried independently; otherwise cite it from the affected notes.
5. Update every materially affected entity or concept page. There is no page-count quota and no churn for its own sake.
6. Refresh the curated map in `AREA.md` when navigation changes.
7. Append the Area log only for a material ingest, reconciliation, or state change.
8. Mark unverified or disputed claims explicitly, then run the normal link and vault validation checks.

Inbox-first still applies when the destination or interpretation is uncertain. Explicit owner direction, triage, or a documented skill may authorize direct Area updates.

## Query Workflow

1. Start at `AREA.md`, then search the Area and its linked sources.
2. Prefer the most specific page and most recent verification evidence.
3. State whether an answer is verified, unverified, disputed, planned, or an inference when that distinction matters.
4. Cite the supporting Area notes with source-relative Markdown links.
5. If evidence conflicts, report the conflict instead of silently selecting a convenient claim.

## Lint and Curation

Area-wiki maintenance is part of normal vault maintenance:

- Run `brain validate` for frontmatter, link, filename, privacy, and staleness findings.
- Use curation to re-verify expired claims, merge duplicates, repair weak links, and archive superseded pages.
- Check that every maintained supporting page is reachable from `AREA.md` or another deliberate hub.
- Review unverified and disputed claims, orphan pages, stale source summaries, and entity pages that disagree with live systems.
- Replace obsolete current-state prose; keep append-only behavior only for genuine logs.

## Guardrails

- **Source preservation:** Derived synthesis never silently mutates or deletes its evidence.
- **Write-time deduplication:** Search before creating a page; merge overlapping claims into the strongest existing home.
- **Incremental synthesis:** Update the pages whose meaning changed, not the whole Area.
- **Portable linking:** Use relative Markdown links, not legacy wikilinks or machine-specific absolute paths.
- **Privacy:** A summary must be safer than its source. Omit credentials and unnecessary identifiers; apply `restricted/private` when content must not spread beyond its note.
- **Human and agent co-maintenance:** The template does not adopt the source model's single-LLM writer constraint. Git history, write lanes, and review handle concurrent stewardship.
- **Reversibility:** Deactivating the wiki pattern requires no file migration; the notes remain ordinary Area notes and unused scaffolding can be removed through normal review.

## Provenance

Adapted for the Second Brain template from [Andrej Karpathy's LLM Wiki specification](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The adaptation preserves the evidence → synthesis → schema model and ingest/query/lint loop while replacing separate wiki conventions with PARA entrypoints, portable links, frontmatter, privacy rules, and human review.
