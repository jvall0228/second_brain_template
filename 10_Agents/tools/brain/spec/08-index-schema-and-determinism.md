---
title: "brain Spec §8 — Index schema and determinism"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 8. Index schema and determinism

*Section 8 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 8.1 Shape

```json
{
 "assets": ["08_Assets/example.png"],
 "notes": {
  "00_Meta/PRD.md": {
   "backlinks": ["AGENTS.md"],
   "bodyTags": [],
   "frontmatter": {"tags": ["type/meta"], "title": "PRD", "updated": "2026-08-11"},
   "frontmatterErrors": [],
   "headings": [{"level": 1, "line": 8, "slug": "prd", "text": "PRD"}],
   "links": [
    {"destination": "../AGENTS.md", "display": "AGENTS", "embed": false,
     "format": "markdown", "fragment": null, "label": "AGENTS", "line": 12,
     "placeholder": false,
     "range": {"start": {"column": 0, "line": 12, "offset": 200},
               "end": {"column": 22, "line": 12, "offset": 222}},
     "raw": "[AGENTS](../AGENTS.md)",
     "resolution": {"fragment": null, "path": "AGENTS.md",
                    "status": "resolved", "warnings": []},
     "resolved": "AGENTS.md", "target": "../AGENTS.md", "warnings": []}
   ],
   "sizeBytes": 12345,
   "tasks": [
    {"due": "2026-08-15", "line": 40, "malformed": [], "priority": "high",
     "status": "open", "text": "call dentist"}
   ],
   "title": "PRD",
   "updated": "2026-08-11"
  }
 },
 "linkCounts": {"legacy": 0, "markdown": 1, "placeholder": 0,
                "unsupportedBlockReference": 0, "wikilink": 0},
 "schemaVersion": 2
}
```

Field meanings are as defined in §3–§7 and §17 (`tasks`). Every field is always present (empty lists/`null` rather than omitted keys). `linkCounts` is the deterministic aggregate over every indexed record; `legacy` currently equals `wikilink` and remains named explicitly for migration/report consumers.

`schemaVersion` bumps on any breaking change to this shape; consumers must check it.

## 8.2 Deterministic serialization

The committed index must be a **pure function of tracked file contents** — a fresh CI clone rebuild must be byte-identical to the committed copy. Hence the index corpus in §2, plus:

- Serialized exactly as Python's `json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True)` plus a single trailing `\n`, written as UTF-8 with LF endings. Only strings, integers, booleans, `null`, objects, and arrays appear (no floats), so output is stable across Python ≥ 3.10. (The §8.1 example shows the real emitted key order: `assets` < `linkCounts` < `notes` < `schemaVersion`.)
- Object keys sort via `sort_keys`; every array is either **document order** (links, headings — deterministic from file content) or **explicitly sorted** (assets, backlinks, bodyTags, and the `notes` keys via key sort).
- **No timestamps, no mtimes, no absolute paths, no environment data, no tool-version stamp.** In particular, **file mtime is excluded** even though the plan's extraction-scope bullet listed it: git does not preserve mtimes, so a fresh clone would always produce a different index and the CI freshness check could never pass. The `recent` command's mtime tiebreak stats the working tree at query time instead (§9). *(Deviation from the plan — flagged for owner review, §12.)*
- `sizeBytes` is the UTF-8 byte length of the **normalized** text (§3; byte-level normalization for `not-utf8` files), not the on-disk size, for the same reason.
- M5.4 must ship a `.gitattributes` entry marking `10_Agents/tools/brain/vault-index.json` as `-text`, so `core.autocrlf=true` checkouts (the Git-for-Windows default) don't smudge the committed copy to CRLF and fail every `--check-index` byte-compare.
- **Merge driver (M8.6, issue #25):** `.gitattributes` additionally marks the three committed generated files — `10_Agents/tools/brain/vault-index.json`, `.vscode/second-brain.code-snippets`, and the compiled `00_Meta/BOOTSTRAP.md` (§28) — with `merge=regenerate`. The driver is defined per clone as `git config merge.regenerate.driver true` (the `true` command exits 0 leaving `%A` = ours): merges of generated content resolve keep-ours, and **correctness comes from regeneration, not resolution** — the `.githooks/post-merge` hook re-runs bootstrap, `index`, and snippet generation best-effort immediately after a merge, the pre-commit hook regenerates on the next commit, and the manually dispatched validation workflow's freshness checks catch any skip. Clones without the driver configured degrade to a normal conflict plus the documented fallback recipe (`10_Agents/solutions/vault-tooling/index-merge-conflicts.md`). Any future committed generated file adopts the same attribute.

## 8.3 Restricted-note reduction (issue #17)

A note whose **frontmatter tags** contain `restricted/private` (bodyTags are informal and never trigger this, matching §10.2's posture) is **reduced** in the committed index rather than excluded — decided 2026-08-11 per the accepted triage recommendation on issue #17. The committed index is the vault's most-copied artifact (PRD §9.4); without reduction it would re-leak the very content the tag marks.

- **Kept:** path (the `notes` key), `title`, `frontmatter` (including `tags` — consumers must be able to see *why* the record is reduced), `updated`, `sizeBytes`, `frontmatterErrors`, `links`, and `backlinks`. Links/backlinks stay so containment and discovery retain structure. On a reduced link, `label`/`display` and `fragment` are nulled, the nested fragment resolution is nulled, and `raw` is rewritten to a label-free canonical form for its format, so link prose never reaches the committed index.
- **Dropped (emptied/nulled, not omitted):** `headings: []`, `bodyTags: []`, and `tasks: []` — body-derived fields — plus the link-record prose fields above.
- The reduction applies to the **committed index only**: `brain index` output and the `validate --check-index` rebuild (both serialize the reduced form, so the byte-compare stays consistent). Query commands (§9) keep the full in-memory record — they run against the local working tree, where the note body sits right beside them; reducing them would cost the owner `search`/`show` utility while protecting nothing.
- This is a **sanctioned, tag-driven exception** to the spirit of the §15.1 config/index invariant: index output varies with note *content* (the tag), never with `00_Meta/config.yaml`. The committed index remains a pure function of tracked file contents (§8.2).
- Honest framing (conventions § restricted/private): reduction is leak resistance, not access control — the note body is still in the repo, readable by anything that reads files.
