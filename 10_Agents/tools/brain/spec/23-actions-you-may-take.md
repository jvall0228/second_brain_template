---
title: "brain Spec §23 — Actions You May Take (`brain aymt`) — issue #79"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# 23. Actions You May Take (`brain aymt`) — issue #79

*Section 23 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 23.1 Inputs and privacy boundary

AYMT is a deterministic local next-action brief built from the **Git-tracked shared corpus only**: concrete Now focus/key dates, open tasks and due metadata, aggregate Inbox/triage debt, canonical active Projects and their target/first action, exact cadence windows, and metadata for the selected environment. The §27 registry is built from the same complete internal authenticated snapshot: supporting notes and NOW bullets cannot become duplicate Projects, inactive Project-directory tasks are excluded, and estimated/overdue targets remain explicit. Every shared note is opened without following links and captured once; privacy classification, link resolution, report inputs, and candidate extraction consume that same authenticated byte snapshot. Unsafe or unreadable paths contribute no content. Generated AYMT/Home, Archives, Templates, the authoritative `adopt_examples.json` seeded-example bundle, and all `10_Agents/environments/**` note bodies are removed before candidate construction. The seed inventory itself must be Git-tracked and is read once through the same confined, no-follow stable-file boundary; an untracked/missing/unsafe inventory fails closed before examples can become candidates. Untracked files never affect candidates, counts, output, or `inputDigest`. Open tasks with due/priority/malformed action metadata are eligible from any remaining safe note; plain undated tasks are limited to Journal/Projects/Areas so canonical and Inbox planning checklists do not masquerade as owner commitments. Malformed task dates create a bounded Unblock or decide repair action without repeating task text. Environment contribution is only `{state, slug, selection source, freshness dates}` from the validated selected manifest; unrelated environment manifests are not loaded for an explicit/environment/selector-selected current slug and cannot block it. Unconfigured is a useful shared-only state, while malformed or ambiguous current selection fails with one redacted error (JSON: the bare safe-failure object; stderr appends the stable §20.3 reason code and, for fingerprint failures, the remedy hint). Expired environment metadata yields Do next; expiry within 14 days yields Keep warm, citing only the shared environments README.

Private notes and valid links to private notes remain eligible internally. Both candidate paths restrict Project-directory recommendations to open tasks under `## Next Actions`; criteria and historical/paused work elsewhere remain queryable tasks but cannot become recommendations. Future start/scheduled dates suppress immediate recommendations, using the captured source line; an empty section reports no current action. Urgent or high-priority Project tasks receive leverage 4 so concrete work can rank ahead of generic reminders.

The optional `--github-input PATH|-` boundary reads at most 64 KiB from a no-follow, identity-checked regular file or stdin. Version 1 accepts exactly a validated `repository`, issue `number`, `title`, `status`, `updated`, and bounded labels. URLs and score fields are forbidden; effort/dependency are derived from allowlisted labels/status, and the source URL is computed as `https://github.com/OWNER/REPO/issues/N`. Brain never invokes `gh`, a connector, or the network.

## 23.2 Candidates, scoring, and selection

Each bounded candidate exposes `id` (full SHA-256), `kind`, exact normalized `outcome`, `section`, integer `score`, six `signals`, `whyNow`, `nextStep`, `caveat`, and at most three safe sources. All text is NFC, single-line, control-stripped, bounded, and Markdown-escaped at render. Signals are integers 0–4; dependency is blocker severity (`0` ready, `4` hard-blocked). The exact score is:

`6*urgency + 4*leverage + 3*confidence + 2*staleness + 2*(4-effort) - 5*dependency`.

Exact NFC/case-folded outcomes dedupe before selection; highest score then stable ID wins. Stable ordering is section order, descending score, folded outcome, ID. The initial soft caps are Do next 3, Unblock or decide 2, Keep warm 2; a second global fill reaches `min(7, eligible)` and at least 5 whenever five eligible candidates exist. JSON includes `{collected,deduplicated,selected,truncated}` plus every selected candidate/signals/source so ranking is auditable. Cadence appears only when the period's tracked note is missing: daily today; weekly Friday–Sunday; monthly final three calendar days; quarterly final seven calendar days; yearly December 26–31.

## 23.3 Rendering, freshness, and write ownership

The canonical rendering is `00_Meta/AYMT.md`: fixed generated marker; canonical frontmatter; `updated` as local date; `expires` the next calendar day; input/content SHA-256 digests; Do next / Unblock or decide / Keep warm sections; and environment context. Vault sources are source-relative URL-encoded Markdown links; computed GitHub sources are canonical HTTPS Markdown links. Empty sections state that no safe concrete suggestion exists.

No flag is a zero-write Markdown preview; `--json` is the zero-write explanation surface. `--check` also writes nothing and exits 1 unless exact bytes, regular-file type, no-follow path, generated marker/content digest, and mode 0644 are fresh. Explicit `--write` is the sole narrow canonical exception and may mutate **only** AYMT; `agent_write_allowed()` remains false so agents cannot hand-edit it. Existing content is owned only when marker, content digest, regular type, and mode match. Foreign, edited, linked, mode-changed, or concurrently replaced content is preserved and refused. On supported POSIX runtimes the dedicated writer holds the parent descriptor, stages/fsyncs with authenticated ownership, performs atomic create-if-absent or quarantine/install CAS, verifies before retiring rollback evidence, cleans authenticated artifacts under `BaseException`, and treats identical bytes as a no-op. Unsupported safe-mutation runtimes are preview/check-only. AYMT is intentionally excluded from automatic hooks and the merge driver because date/environment are local inputs.

**Derived source classification (§8.3).** The structured payload carries sorted `privacySources`, and generated frontmatter records the same paths as `privacy-sources`. These are all eligible authenticated inputs contributing facts, ranking, or aggregate counts, including undisplayed candidates. Fixed navigation and excluded source bodies add no dependencies. The payload also exposes `privacy: public|private|unknown`; private renders inherit `restricted/private`. They participate in the input/content digests. If a contributing source later becomes private, explicit public-only synthesis treats the stored brief as effectively private without prohibiting local generation, indexing, or commits. Legacy output lacking provenance is unknown only for public-only filtering; ordinary use remains available. Default AYMT is a complete internal view; explicit public-only retrieval and notification/export boundaries retain their restrictions.
