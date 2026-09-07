---
title: "restricted/private Contract"
tags:
  - type/meta
  - workflow/canonical
  - audience/agent
  - audience/human
updated: 2026-09-07
expires: 2027-08-11
---

# restricted/private Contract

`restricted/private` is **publication classification plus leak resistance, not access control**. It classifies material for public-only synthesis and publishing or export. Private content remains permitted in local context, generated content, the repository, and ordinary commits. This note is the single full statement of the contract; the summary at [CONVENTIONS § restricted/private](CONVENTIONS.md#restrictedprivate) points here.

## Local Access

Agents may read, search, link, quote, summarize, create, and edit private content by default. Local keyword and semantic search include restricted notes; the machine-local semantic sidecar is working context, not a publication surface, and includes private notes. Per-agent access restriction belongs to harness hooks or permissions, not this tag — Cursor's `.cursorignore` exclusion is an owner-selected opt-in, and such path exclusion is harness-specific and incomplete.

## Propagation

A note that quotes, summarizes, or otherwise carries private substance from a restricted source also carries `restricted/private` — including when the transformation obscures the provenance. A bare link does not propagate the tag. A link from a non-restricted note to a restricted note is valid; the `restricted-link` validation warning is an informational provenance check asking whether nearby prose carries private substance and therefore requires propagation.

Private or mixed generated content remains permitted internally. Generated bootstrap includes the complete internal source bodies and inherits the private tag if any source has it. AYMT/Home record actual source dependencies in `privacy-sources`; Area `## Active Projects` links record the dependencies of that generated section. Public-only consumers compute effective classification from the current source snapshot, including multiple derivation steps. If a source becomes private after generation, the derived content is effectively private without prohibiting its continued local existence or use. Missing or invalid generated provenance is unknown: public-only synthesis excludes it conservatively, while ordinary reading, generation, indexing, and commits remain allowed. Unrelated bare links do not become derivation edges.

Any note may declare substantive dependencies with `privacy-sources`. This records source paths and current classification, not complete historical inference provenance or prior source-version hashes. AYMT/Home include the eligible inputs contributing counts, ranking, and health aggregates, including undisplayed rows. Both are complete internal views over eligible tracked work; privacy alone or a valid private link never hides a Project, Area, or task. Output caps still bound the brief. The inherited private tag keeps copied private substance private even if its source is later declassified.

Trace, triage archival, gap/acceptance ingestion, and daily carry-over classify the same captured bytes they transform. Private or unknown sources cannot enter public logs as summaries; traces retain bare links, private/unknown triage reports retain their own classified archive note, and private gap captures require explicit declassification before entering the public queue. Public summaries retain substantive dependencies so later source reclassification propagates. Local query provenance distinguishes effective classification from the explicit tag.

## Blast Radius

The tag is note-granular: moving one private claim into a broad review or rollup makes the entire destination private. Linking instead of copying stays the recommended lower-blast-radius practice — a recommendation, not a prohibition.

## Tag Flips

A change that adds or removes `restricted/private` on an existing note must be surfaced in the diff or validation output, because generated and publication-facing surfaces may change what they include.

## Public-only Synthesis

For a reply that should use public notes only, choose this route **before personal bootstrap**. Start a fresh synthesis context containing only policy instructions, the request, and admitted sources. Load this contract and the necessary safety/write instructions, omitting NOW, profile, personal index, generated bootstrap, and inherited conversation content. This is a context route, not a new permission to send messages. If the harness automatically injects private context or cannot establish that isolation, report **unsupported public-only isolation** and produce no purported public-only synthesis.

Retrieve admitted sources within the isolated route:

- `brain search <query> --public-only` filters private and unknown derived notes before returning lexical or semantic results.
- `brain show <note> --public-only` returns an admitted note's structured record.
- `brain read <note>... --public-only --json` returns complete source text and its content hash from the same bytes used for classification. A disallowed requested source refuses the whole read, without partial source output.

These flags do not erase private material already loaded into an agent's context. The reply workflow must keep its synthesis context scoped from the start, rather than combining filtered retrieval with unrestricted bootstrap or earlier private context. These tools supply context; they do not authorize or send emails or texts.

## Existing Filtered Views

Some commands deliberately produce reduced or filtered views: committed index reduction (spec §8.3), notification formatting, artifact views, link-migration plan redaction, and daily carry-over into otherwise public journals. The Area rollup writer retains its restricted-mapping check. These destination-specific rules do not prohibit private generated content. The committed index keeps every record; derived private records receive effective classification and body reduction. Private notes remain available through ordinary local search, reads, Home, and AYMT. Public-only helpers also exclude unknown derivations.

Public publishing and export exclude private content automatically; inclusion requires an explicit owner override for that individual operation.

## Accepted Residual Risk

An agent may fail to recognize that text earlier in its context originated in a private note. Source tags and derivation provenance make scoped retrieval possible; they cannot retroactively cleanse model context or replace a reply workflow's decision about which sources to provide.
