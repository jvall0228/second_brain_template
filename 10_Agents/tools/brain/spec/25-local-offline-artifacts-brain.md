---
title: "brain Spec §25 — Local offline artifacts (`brain artifacts`) — issue #23"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 25. Local offline artifacts (`brain artifacts`) — issue #23

*Section 25 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 25.1 Authenticated source and derived-data boundary

The version-1 artifact pipeline emits exactly `08_Assets/artifacts/link-graph.html`, `health-dashboard.html`, and `manifest.json`. Its only input is the Git-tracked shared corpus from §2. Git unavailability is a refusal, never a working-tree fallback. Each candidate note is opened once through the no-follow descriptor reader and supplied to the shared index builder as an authenticated snapshot, so privacy classification, link resolution, titles, tags, tasks, and report metrics cannot observe different file versions. Symlinks/reparse paths, unreadable files, untracked files, `10_Agents/environments/**`, and the artifact directory itself contribute nothing.

Before derivation, the pipeline removes `restricted/private` notes, every note targeting one, and every note containing a recognized credential or webhook-like value. Serialized data is bounded metadata only: safe title, vault-relative note path, allowlisted tag shape, safe relative href, numeric link edges, and aggregate link/Inbox/task/freshness/expiry counts. Raw bodies, headings, task text, asset content, environment bodies or metadata, absolute paths, owner/host names, credentials, webhook values, and privacy-filter counts are never serialized. A title with unsafe metadata falls back to its relative basename; an unsafe note is excluded. The output is therefore a private local summary, not an access-control surface.

The graph ranks nodes by degree and stable folded title/path, then caps display at 500 nodes and 2,000 path-sorted edges; truncation counts are explicit. Layout uses deterministic bounded concentric rings, suppressing visual labels above 80 nodes while preserving every accessible link in the keyboard list. Search and tag filters re-render the bounded graph; navigation stays relative and safe. Health metrics reuse the shared index/report/task/expiry semantics and expose counts only. The default controlled `asOf` date is the newest valid `updated` date in the already-filtered source, or `1970-01-01` for an empty vault. `--as-of YYYY-MM-DD` sets it explicitly. `generatedAt` is deterministically that date at `T00:00:00Z`; wall clock and current environment never influence bytes.

## 25.2 Offline rendering and manifest

Both UTF-8/LF HTML files are self-contained and contain no CDN, remote font, telemetry, `fetch`, XHR, WebSocket, EventSource, or runtime network URL. The CSP is `default-src 'none'` with `connect-src 'none'`, no `unsafe-inline`, and SHA-256 sources for the exact inline style, JSON data block, and executable script. Canonical JSON is escaped for `&`, `<`, `>`, U+2028, and U+2029 before entering the script context. Dynamic values are written with `textContent` or safe DOM attributes; raw note HTML is never inserted.

Each document includes a useful static summary and note links or metrics before JavaScript runs, an explicit `noscript` explanation, labels and live counts, native/explicit keyboard operation, visible focus, responsive layout, reduced-motion behavior, empty states, and light/dark colors. Local note navigation is source-relative and percent-encoded under the repository Markdown-link contract.

The canonical JSON manifest records schema/generator/owner, controlled source time, scope/filter policy, source `inputDigest`, exact HTML paths, sizes, and SHA-256 values. Each HTML file has a generated marker and a digest over its complete bytes with the digest field neutralized; the manifest has the equivalent canonical content digest. Output bytes are deterministic for identical authenticated inputs and `asOf`.

## 25.3 Modes, ownership, and local opening

No mode is a read-only preview; `--json` exposes the same stable plan. `--check` is also zero-write and exits 1 unless all three exact files are recognized mode-0644 regular files with fresh bytes. Explicit `--write` is the sole write lane. It never grants generic authority over `08_Assets/`: the documented README is human-maintained, and the writer refuses an unexpected inventory.

On supported POSIX runtimes the writer holds each output parent, rejects case-fold collisions and foreign/edited/linked/mode-changed occupants, rechecks case-fold siblings before every forward mutation and commit, stages and fsyncs exact bytes, re-authenticates every final immediately before mutation, quarantines recognized prior outputs, and publishes with create-if-absent hard links. Stage cleanup removes only the inode created by the staging descriptor, so a replacement at its reserved name survives even when interruption precedes the normal ownership handoff. Before rollback evidence retires, the command rebuilds the complete plan and then the writer reauthenticates every created, replaced, or unchanged output's held-parent case state, exact bytes, mode, and inode; a late foreign replacement fails generically, remains untouched, and leaves verified prior recovery evidence where restoration would collide. A caught exception, `KeyboardInterrupt`, `SystemExit`, or trapped `SIGTERM` removes only authenticated stages/results and restores verified prior files without overwriting a concurrent final. A concurrent insertion or replacement is preserved. Identical files are inode-preserving no-ops. Unsupported safe-mutation runtimes remain preview/check-only. Because all three outputs are reproducible and source-free, a process crash may leave authenticated `.migrate-{new,old}` recovery evidence; a fresh plan remains fail-closed on final ownership and regeneration is the recovery path.

`--open` is explicit and opens only fresh local `file:` URIs for the two HTML files. Each URI names a mode-0400 temporary snapshot whose bytes are re-authenticated against the owned artifact before browser dispatch, so a late redirect of the canonical pathname cannot change what is opened; the snapshots are removed after dispatch or refusal. Tests inject a browser spy and never open a real browser. Hosting, upload, public URLs, credentials, and notifications are absent from this package. Any future hosting is a separate opt-in feature requiring environment-scoped configuration, explicit owner consent, and privacy review.
