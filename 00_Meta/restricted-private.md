---
title: "restricted/private Contract"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-09-04
expires: 2027-08-11
---

# restricted/private Contract

`restricted/private` is **publication classification plus leak resistance, not access control**. It marks content that public publishing or export must exclude; it does not restrict what agents may read or use locally. This note is the single full statement of the contract (adopted 2026-08-24; see the [CHANGELOG](CHANGELOG.md) entry of that date); other documents — including the load-bearing summary at [CONVENTIONS § restricted/private](CONVENTIONS.md#restrictedprivate) — point here.

## Local Access

Agents may read, search, link, quote, summarize, create, and edit private content by default. Local keyword and semantic search include restricted notes; the machine-local semantic sidecar is working context, not a publication surface, and includes private notes. Per-agent access restriction belongs to harness hooks or permissions, not this tag — Cursor's `.cursorignore` exclusion is an owner-selected opt-in, and such path exclusion is harness-specific and incomplete.

## Propagation

A note that quotes, summarizes, or otherwise carries private substance from a restricted source also carries `restricted/private` — including when the transformation obscures the provenance. A bare link does not propagate the tag. A link from a non-restricted note to a restricted note is valid; the `restricted-link` validation warning is an informational provenance check asking whether nearby prose carries private substance and therefore requires propagation.

## Blast Radius

The tag is note-granular: moving one private claim into a broad review or rollup makes the entire destination private. Linking instead of copying stays the recommended lower-blast-radius practice — a recommendation, not a prohibition.

## Tag Flips

A change that adds or removes `restricted/private` on an existing note must be surfaced in the diff or validation output, because generated and publication-facing surfaces may change what they include.

## Retained Mechanical Boundaries

These outward filters remain enforced and non-optional:

- committed index reduction (spec §8.3: body content and link prose emptied; path/title/frontmatter/link targets stay published);
- notification filtering;
- generated artifact filtering;
- AYMT and Home exclusion;
- link-migration plan redaction;
- daily task carry-over skipping;
- restricted Project → non-restricted Area rollup blocking; and
- the `restricted-link` provenance warning above.

Public publishing and export exclude private content automatically; inclusion requires an explicit owner override for that individual operation.

## Accepted Residual Risk

An agent may fail to recognize that text earlier in its context originated in a private note; export filters are the final mechanical boundary.
