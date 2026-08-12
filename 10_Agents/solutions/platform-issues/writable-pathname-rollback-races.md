---
title: "Writable Pathname Rollback Races"
tags:
  - type/solution
  - audience/agent
  - topic/filesystems
updated: 2026-08-12
author: codex
session: https://github.com/jvall0228/second_brain_template/pull/86
---

# Writable Pathname Rollback Races

## Problem

A transaction creates a file, a later state write fails, and rollback tries to delete the created pathname after checking its bytes and inode. The deletion is still unsafe when another process can already hold the file open for writing: it can mutate the same inode after authentication but before unlink. Device and inode equality also fail when a filesystem quickly reuses an inode after a pathname replacement.

## Symptoms

- A foreign same-inode rewrite disappears during rollback.
- Linux CI fails while macOS passes because inode reuse differs.
- A FIFO replacement blocks a verifier that opens it without `O_NONBLOCK`.
- A large or growing replacement is read without a bound.
- Files requested as mode `0600` become `000` or `0400` under a restrictive umask, breaking later ownership checks.

## Solution

Do not delete or replace a public pathname during failure cleanup when concurrent writers cannot be excluded. Preserve output, installed state, and private stages as explicit recovery evidence and fail closed. Block unsafe automatic retry with either explicit recovery evidence or a durable, bounded at-most-once reservation.

When authenticating that evidence or performing final verification:

1. Open descriptor-relatively with `O_NOFOLLOW`, `O_CLOEXEC`, and `O_NONBLOCK`.
2. Reject non-regular files, wrong mode, wrong device/inode, and a size that differs from the bounded expected payload before reading.
3. Read no more than `len(expected) + 1`, then compare bytes.
4. Compare descriptor metadata before and after the read, including size, mode, `mtime_ns`, and `ctime_ns`.
5. Treat any mismatch as foreign and preserve it without mutation.
6. Force the intended mode with `fchmod` before the file fsync; never rely on the process umask.
7. Publish a private stage with an atomic no-replace rename so success consumes the stage name; retain prior generations instead of unlinking writable backups.
8. Bound retained generations by count and bytes before beginning another transaction; an unfinished `migrate-new` always blocks retry, while an authenticated `migrate-old` may coexist with the canonical file.
9. For at-most-once delivery, reserve bounded dedupe state before publishing any default or explicit-temporary output. The state CAS serializes concurrent attempts; never roll its winner back after an output failure.
10. Authenticate current-user ownership for private files and directories. Require sensitive mode-`0700` directories to be provisioned before the transaction; do not create, chmod, or repair a pathname that cannot be bound to the requested directory identity.

Use the same bounded authenticator for final verification and recovery classification so hostile path types cannot reach an older blocking reader.

## Prevention

- Test same-inode in-place mutation separately from unlink-and-recreate replacement.
- Hold the original descriptor open in replacement tests so inode reuse cannot make a test nondeterministic.
- Include FIFO, symlink, wrong-mode, oversized-file, restrictive-umask, interruption, and state-rollback cases.
- Do not describe a path deletion as compare-and-swap unless the platform supplies a primitive that binds authentication and deletion against already-open writers.
- Prefer recoverable residue over a cleanup step that can destroy foreign content.

## Related

- [Notification implementation](../../tools/brain/notifications.py)
- [Notification transaction contract](../../tools/brain/spec.md#263-preview-and-local-file-delivery)
- [Configure Notifications](../../skills/configure-notifications/SKILL.md)
