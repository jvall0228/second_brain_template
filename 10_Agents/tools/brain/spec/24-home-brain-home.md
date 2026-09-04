---
title: "brain Spec §24 — Home (`brain home`) — issue #78"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 24. Home (`brain home`) — issue #78

*Section 24 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 24.1 Inputs, sections, and privacy

Home is a generated local startup and navigation surface at `00_Meta/HOME.md`; canonical `00_Meta/INDEX.md` remains the stable human map and is never dynamically rewritten. Home constructs one authenticated Git-tracked safe context and passes that same object to the structured `build_aymt()` API for its globally ranked top three selected actions; it never parses AYMT Markdown or takes a second corpus snapshot. Before returning, Home re-queries the exact Git tracked-path set and reauthenticates every consumed note and non-Markdown authority byte snapshot — including the committed index, seed inventory, tracked config, and selected environment manifest — through the confined no-follow reader. Any late set, path, or byte change fails closed behind the generic Home error. The same context supplies due/overdue tasks, aggregate Inbox age/debt, §27 canonical active Projects/Areas with mappings and target state, existing current-period review-note links plus exact-window missing cadence suggestions, current Now/Status/Changelog links, expiry/health, selected environment metadata/freshness, and fixed navigation.

Before any Home body-derived action work, generated Home/AYMT, authoritative seed paths, untracked files, and every environment body are removed. Remaining notes are opened without following links and captured once; privacy classification and link resolution share those immutable bytes, then Archives, Templates, restricted notes, and notes resolving to restricted targets are removed before task extraction, detailed health reporting, or rendering. Excluded sources cannot influence fields, counts, safe backlinks, or `inputDigest`; their only permitted signal is the generic committed-index freshness boolean described below. Git discovery failure is a refusal, never a working-tree fallback. Only the selected tracked environment manifest contributes `{state, slug, selection source, freshness dates}`; unconfigured is useful and unrelated manifests cannot block a valid selected one. Home makes no missed-automation claim because no run-log contract exists.

Optional GitHub data is absent by default. `--github-input PATH|-` delegates only to AYMT's strict local snapshot boundary (§23.1); brain never invokes `gh`, a connector, or the network. GitHub sources, when present, are computed canonical HTTPS links.

## 24.2 Output and editor surfaces

Markdown and `--json` are deterministic from schema version, local date, safe inputs, and selected environment metadata. Fields and lists are bounded with stable ordering; internal citations are source-relative URL-encoded Markdown links and maintained output contains no legacy syntax. Health exposes bounded generic safe-validation error/warning rule counts, tracked-safe committed-index freshness, expired and next-14-day expiry rows, stale-active/orphan/unresolved counts, and no unsafe body text. Freshness compares the canonical committed bytes with a separately built complete authenticated tracked shared index after standard restricted-note reduction, excluding the generated Home/AYMT records and their outbound count/backlink contributions on both sides. This prevents Home's own freshness line from making Home and the committed index perpetually invalidate each other; edits anywhere else, including transitions into or out of an excluded/restricted state, still change only the generic freshness boolean and never disclose a title, body, or path. Rendering has a fixed marker/frontmatter, next-day expiry, input/content SHA-256 digests, useful empty states, and sections in the order named above.

Obsidian's tracked native `openBehavior: file:00_Meta/HOME.md` setting opens the committed Home. VS Code's folder-open task best-effort opens the same file without regenerating it; it requires workspace trust, one-time automatic-task approval, and `code` on `PATH`, with manual open/`brain home` as recovery. A separate VS Code task previews Home read-only. These startup paths never write.

## 24.3 Freshness and exact-file ownership

No flag is a portable, zero-write Markdown preview; `--json` is the equivalent structured view. `--check` makes zero writes and exits 1 unless exact rendered bytes, a safe no-follow regular path, generated marker/content digest, and platform-appropriate writable mode are fresh. `--write` is the sole narrow exception and may mutate only exact `00_Meta/HOME.md`; `agent_write_allowed()` remains false, no config exception exists, and hand edits are foreign.

The dedicated writer uses the §23 descriptor-bound stage/quarantine/install transaction: marker/digest/mode ownership, casefold-collision refusal, held parent, authenticated final/stage identities, create-if-absent publication, rollback evidence, directory fsync, post-publication verification, `BaseException` cleanup, foreign/concurrent occupant preservation, and identical-byte no-op. Unsupported safe mutation runtimes remain preview/check-only. Home stays outside hooks and the merge driver because date/environment are clone-local; it refreshes only on explicit command or skill invocation.
