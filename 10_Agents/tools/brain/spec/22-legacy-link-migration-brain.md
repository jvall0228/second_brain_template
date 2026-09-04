---
title: "brain Spec §22 — Legacy link migration (`brain migrate-links`) — issue #74"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 22. Legacy link migration (`brain migrate-links`) — issue #74

*Section 22 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 22.1 Preview and plan

No flag is a read-only preview. The migrator scans tracked working-corpus notes, parses raw UTF-8 bytes without newline conversion, resolves each legacy record through the same §6 engine, and emits a deterministic version-1 plan. The envelope is `{schemaVersion, planId, status, summary, edits, blockers, regenerateRequired}`. Each path-sorted edit carries `path`, `restricted`, preserved `mode`, raw `sourceSha256`/`resultSha256`, and ordered replacements with raw-byte half-open `range`, `line`, `before`, `after`, and `resolved`. `planId` is SHA-256 over canonical compact JSON excluding the ID. The summary counts scanned/changed files, legacy/Markdown links, conversions, placeholders, and unsupported block refs. A second identical preview is byte-stable. Internal exact replacement text remains available for apply, but every serialized CLI plan nulls `before`/`after` and sets `redacted: true` for `restricted/private` sources so migration diagnostics do not republish protected body prose.

Placeholders stay unchanged and counted. Ambiguous paths/headings, unresolved targets/fragments, block refs, unsafe sources, stale ranges, and overlapping edits are blockers; a plan with any blocker is never writable. Rendering uses the resolved target rather than regex text: notes keep explicit `.md`, paths are relative to the source and URL-encoded, heading links use §6.4 slugs, aliases become escaped labels, self-headings stay fragment-only, and embeds become Markdown images with a meaningful alt label. Splicing operates on raw byte ranges, preserving UTF-8 BOM, LF/CRLF/mixed endings, final-newline state, unrelated bytes, and file mode.

`--check` is read-only and exits 1 while **any legacy record** (placeholders included), edit, or blocker remains, otherwise 0. It is the zero-legacy acceptance gate rather than merely an automatic-edit-complete signal. `--json` exposes the same complete plan. Explicit `--write` is the only mutation mode; every successful write reports that the index, snippets, and skill adapters require immediate regeneration. The shipped corpus itself has zero legacy records; this command remains available for importing older vaults.

## 22.2 Write refusal and transaction

Write requires Git to establish that every **planned source path** is clean; unrelated owner edits do not block and are never touched. Before mutation the plan ID/shape, source hash, mode, replacement text/ranges, result hash, regular-file type, parent chain, and final identity are rechecked. Symlink/reparse paths, stale content/mode, unsupported mutation primitives, a foreign journal, or concurrent activity fail closed before overwrite.

On POSIX, every source parent is opened component-by-component with directory descriptors and no-follow flags and held through the transaction. Random same-directory stage names are journaled durably before creation, then desired files are fsynced there. Stage ownership identity is recorded before the staging helper returns, so an interruption at the return boundary still authenticates/removes that stage before the journal can retire; a concurrent occupant at the reserved name is preserved. Originals are descriptor-relatively quarantined and hash/mode/identity-verified, then desired files are installed with hard-link create-if-absent, so a concurrent final-component insertion is preserved and refused rather than overwritten. Publication attempts are rollback-tracked before the directory fsync, every containing directory is fsynced before the durable commit marker, and installed bytes/mode/inode are re-authenticated after that marker before success can remove recovery evidence. Any ordinary exception, `KeyboardInterrupt`, `SystemExit`, or trapped `SIGTERM` removes only authenticated staged outputs and restores quarantined originals without overwriting concurrent content. Platforms without the required held-parent descriptor operations (including the current unimplemented Win32 mutation path) are preview/check-only and fail before any write.

## 22.3 Crash recovery and idempotence

The O_EXCL lock and recovery journal is `.brain-link-migration.json` at the vault root (dot-pruned from the corpus, mode 0600). It records only authenticated transaction names, source/result hashes, modes, plan ID, PID, and commit state — no note bodies. Creation returns a held descriptor/inode/content guard; later states are complete append-only JSON lines written and fsynced through that descriptor, never path-replaced. Every update verifies the path still names the held inode with the expected mode/content before and after append. Cleanup descriptor-relatively quarantines the pathname, authenticates the moved inode, and deletes only that owned journal. A foreign replacement or in-place mutation is never overwritten or removed: it is preserved byte-for-byte with its mode and the operation fails closed. A second starter receives a stable active-migration refusal. The root journal and per-directory `.NAME.migrate-{new,old}-*` recovery artifacts are gitignored so a crash cannot make them accidental commit candidates; their existence remains visible to the recovery detector.

Preview and `--check` never recover: if a journal exists they report `interrupted-migration`, exit nonzero, and make zero writes. Explicit `--write` recovers a dead transaction before planning. If `committed: false`, recovery removes only verified installed results and restores verified backups; foreign final content is preserved and the backup retained for explicit manual recovery. If `committed: true`, recovery finishes the commit by verifying current results and removing verified backup/stage artifacts. Malformed/unsafe journals, live owning PIDs, hash drift, or missing evidence fail closed. Once complete, the journal disappears. A successful second automatic migration has zero edits; `--check` reaches 0 only after placeholders and every other maintained legacy record are also gone.
