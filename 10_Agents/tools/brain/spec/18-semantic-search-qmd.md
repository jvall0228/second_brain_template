---
title: "brain Spec §18 — Semantic search (QMD — issue #8)"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 18. Semantic search (QMD — issue #8)

*Section 18 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

Natural-language, relevance-ranked retrieval over vault notes, layered **beside** the keyword machinery, never replacing it. Decided 2026-08-11 per the owner correction and accepted recommendation on issue #8 (QMD = **Query Markdown**, not Quarto). Two commands carry the whole feature: `brain embed` maintains a local vector store (§18.3), `brain search --semantic` queries it (§18.4). Every supported harness reaches it through the CLI — the universal layer (each `10_Agents/harnesses/*/wiring.md` documents invocation); no per-harness plugin is part of the compatibility contract.

## 18.1 Embeddings sidecar

- **Location:** `10_Agents/tools/brain/vault-embeddings.json`, beside the committed index but — unlike it — **gitignored** (a `.gitignore` entry ships with this section). Vectors are large, model-dependent, and environment-specific: each clone regenerates its own sidecar incrementally, and the #25 committed-generated-file machinery (merge driver, freshness CI) never applies to it. The path is pruned from the §2 corpus the same way the index file is, so the sidecar can never appear as an asset, enter the committed index, or be content-scanned by `validate`.
- **Shape** (serialized like §8.2 — `json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True)` + trailing `\n`, UTF-8/LF — except that **floats are allowed** here; the §8.2 no-floats rule protects the *committed* index only):

```json
{
 "dim": 384,
 "model": "all-MiniLM-L6-v2",
 "notes": {
  "04_Projects/example.md": {"hash": "<sha256 hex>", "vector": [0.1, -0.2]}
 },
 "schemaVersion": 1
}
```

- **Granularity is per-note** in v1 (`notes` keys are §2 vault-relative note paths). Per-section vectors are an anticipated refinement: `schemaVersion` bumps if the record shape changes, and consumers must check it — an unknown `schemaVersion` is treated as an absent store (§18.2).
- **Keying:** each entry carries `hash` — the SHA-256 hex digest of the note's full **normalized text** (§3, frontmatter included), computed at embed time. `model` and `dim` are store-global: vectors from different models are not comparable, so one sidecar holds exactly one model's vectors (§18.3 replacement rule). Every stored vector's length must equal `dim`.
- **Restricted inclusion (2026-08-24 privacy policy — R12/KTD5):** the sidecar is **machine-local working context, not a publication surface** (conventions § restricted/private): it is gitignored, path-confined, and never copied outward, so local semantic search follows the same local-access posture as keyword search (§9). A note whose frontmatter tags contain `restricted/private` (§8.3's trigger, frontmatter tags only) **embeds and ranks like any other note**: `embed` accepts it through every mode, freshness/staleness/pruning treat its entry as ordinary, and gaining or losing the tag never by itself removes the note from semantic ranking. Provenance rides on the results instead of on exclusion — semantic rows carry the note's `restricted` classification exactly like keyword rows (§18.4, R11/KTD3). The **committed-index reduction (§8.3) is untouched**: the sidecar never influences `index` output (§18.5), and the same restricted note stays reduced in the committed index while its vector sits in the local sidecar.

## 18.2 Staleness and store loading

- A sidecar entry is **fresh** for a note iff the note exists in the working corpus, its recomputed content hash equals the stored `hash`, and the vector length equals `dim`. Anything else — edited note (hash mismatch), deleted/renamed note (no such path), wrong-length vector — makes the entry **stale**, and stale entries are **excluded** from semantic ranking (never re-ranked, never partially trusted): the note participates through the keyword component only, exactly as if it had no vector. Incremental re-embedding (`embed --local`, or a harness re-piping changed notes) restores freshness at cost proportional to edits.
- **Loading is best-effort, never fatal** (§4 posture): a missing sidecar yields an empty store; an unreadable, non-UTF-8, non-JSON, wrong-`schemaVersion`, or shape-invalid file is treated as **absent** with a one-line stderr notice naming the fix (`brain embed`). No command ever crashes on sidecar content.

## 18.3 `brain embed`

Maintains the sidecar. §9 conventions apply (`--json`, exit `0` success / `1` operational error). Exactly one mode flag is required:

- **`--stdin-json`** — the harness/API ingestion interface. Stdin is one JSON object: `{"model": "<non-empty string>", "vectors": {"<note path>": [<numbers>], …}}`. Validation (any violation is an operational error — message on stderr, exit 1, **sidecar untouched**): top level must be an object with exactly those two keys; `model` a non-empty string; `vectors` a non-empty object; every value a non-empty array of finite numbers (booleans are not numbers), all the same length; every key a working-corpus note path (§2 normalization applies) — unknown paths are reported and fail the whole call (all-or-nothing, so a typo cannot half-apply). Entries for restricted notes are **accepted** per §18.1; entries for notes whose content cannot be read or decoded (§3) are skipped with a stderr notice (not an error — pipelines may blindly embed everything) — there is no text to hash. **Partial-update semantics:** when the incoming `model` and vector length match the existing store's `model`/`dim`, entries merge over it (each ingested note's `hash` recomputed from its current normalized text; unmentioned notes keep their entries); when either differs, the store is **replaced wholesale** with a stderr notice — mixed-model stores are never representable. Output: a summary — `{"dim", "model", "path", "skippedUnreadable", "stored"}` under `--json`, the same facts as text otherwise (`--local` emits the analogous `{"dim", "embedded", "model", "path", "total"}`). The former `skippedRestricted` key was **removed** with the 2026-08-24 restricted-inclusion change (§18.1), not frozen at an always-empty value: the key existed to report a filter that no longer exists, and a permanently-`[]` field would misdocument the contract as still filtering.
- **`--local [--model NAME]`** — the offline path, and the **one sanctioned optional non-stdlib dependency** in the vault: `sentence-transformers`, imported lazily inside this feature only, never at module import time, never required. When the import (or model load) fails, `embed --local` exits 1 with a message naming the three alternatives (install the optional package, pipe vectors via `--stdin-json`, or use keyword search) — a clean degradation message, never a traceback. When available: embed every readable note whose entry is missing or stale (restricted notes included, §18.1; incremental by hash; fresh entries untouched), under the model named by `--model`, else the store's recorded `model`, else the default constant (`EMBED_LOCAL_MODEL_DEFAULT`); a model different from the store's replaces the store wholesale, as above. When there is nothing to embed **and** nothing retained (an empty vault, or every note unreadable), the command reports and exits 0 **without writing** — a `{"dim": null}` store would violate the §18.1 shape.
- **`--status`** — coverage report, no writes, no model needed: `{"dim", "embedded", "missing", "model", "notes", "present", "stale"}` — total corpus notes (only unreadable notes are excluded from the embeddable universe; restricted notes count, §18.1), fresh/stale/missing counts, and whether the sidecar file exists.
- **External embedding APIs** are supported as **adapters outside `brain`**: a thin script (harness-side or personal) calls the API and pipes the result through `--stdin-json` / `--query-vector` — the same interface as harness-computed vectors. `brain` itself never takes an API key, endpoint, or credential in any form (PRD §16.2); no such adapter ships in the template.

## 18.4 `brain search --semantic <query>`

Ranks whole notes by a hybrid of vector similarity and keyword match. `--tag` filters (effective-tag semantics, §9) restrict the note universe for **both** components. Exit `0` on success — including every degraded case; `1` only for operational errors (malformed `--query-vector` input).

- **Query embedding sourcing**, in order: (1) `--query-vector` — read one JSON array of finite numbers from stdin (the harness/API path: whatever computed the note vectors embeds the query too); its length must equal the store's `dim`, else an operational error (exit 1). (2) Otherwise, the optional local model (§18.3), loaded with the store's recorded `model` — best-effort: any import/load/encode failure yields no query vector, silently eligible for (3). (3) Otherwise **no query embedding exists** → keyword degradation, below.
- **Keyword degradation:** when semantic ranking is impossible — no usable query vector, or the fresh-entry set (§18.2) is empty (no sidecar, empty store, everything stale) — the command behaves **exactly** like plain `search` (§9): same rows (including the §9 `restricted` field and human `[restricted]` marker), same human and `--json` output shape, exit 0, plus a one-line stderr notice naming the cause and the fix. `--semantic` must never hard-fail on a vectorless vault.
- **Hybrid ranking rule** (exact): for each note `n` in the (tag-filtered) universe, let `sem(n) = (cos(q, v_n) + 1) / 2` when `n` has a fresh vector `v_n` (cosine similarity, stdlib `math`; zero-magnitude vectors give `cos = 0`), else `sem(n) = 0`; let `kw(n) = 1` if the note has at least one plain-`search` hit (title, heading, or body) for the query, else `0`. Then `score(n) = round(0.7 · sem(n) + 0.3 · kw(n), 6)` — the weights are the module constants `SEMANTIC_WEIGHT` / `KEYWORD_WEIGHT`. A note enters the results iff it has a fresh vector or a keyword hit; results sort by `score` descending, then path ascending, truncated to `--top N` (default 10). Rounding before sorting makes ranking a pure function of the stored vectors, the query vector, the tree, and the flags — **deterministic given fixed vectors**.
- **Output** (semantic mode): JSON — an array of `{"keywordHits": int, "path", "restricted": bool, "score": float, "semanticScore": float|null, "title"}` rows in rank order (`semanticScore` is the rounded `sem(n)`, `null` when the note has no fresh vector; `restricted` is the note's §8.3 privacy classification — R11/KTD3, additive, the same provenance treatment as §9 keyword rows); human — one `score  path  (title)` line per row, with a trailing `  [restricted]` marker on restricted rows. This intentionally ranks *notes* where plain `search` lists *hits*; the degraded mode keeps plain `search`'s shape so a vectorless vault still gets exactly the §9 contract.

## 18.5 Determinism and invariants

- The sidecar never influences `index` output, `validate` findings, or any command other than `embed` and `search --semantic` — the committed index stays a pure function of tracked content (§8.2) with or without embeddings present.
- Given a fixed sidecar and query vector, `search --semantic` output is byte-identical across runs and platforms (IEEE-754 arithmetic over identical inputs, rounded per §18.4; all ordering is explicit). No timestamps, mtimes, or environment data appear in the sidecar or in query output.
- Stdlib-only holds everywhere outside the §18.3 optional-import boundary: every other path of `embed` and all of `search --semantic` run with no third-party code, and the optional dependency's absence is never an import-time or default-path failure.
