---
title: "Authenticated Removal and Derivative Privacy"
tags:
  - type/solution
  - audience/agent
  - topic/software
updated: 2026-09-07
author: codex
---

# Authenticated Removal and Derivative Privacy

## Problem

A digest check followed by pathname deletion can remove a concurrent replacement. Classifying a note separately from reading its body can copy private bytes under public metadata. Retries can then duplicate published content or mistake a recreated source for the original.

## Symptoms

- Replacing an Inbox parent or source between planning and deletion affects an unrelated file.
- A crash leaves the destination written while the source's deletion state is ambiguous.
- Public writers accept a derivative whose explicit tags are public but whose sources are private or missing.

## Solution

Use the [authenticated removal protocol](../../tools/brain/spec/29-triage-archive-and-trace.md) for deletion: bind the full parent chain and file identity, persist a vault-root recovery record, claim without replacement, then verify the claimed identity and digest. Preserve unexpected occupants and recovery evidence. Keep destination publication idempotent so a retained claim can supply the original bytes on retry.

Use immutable source snapshots for both transformation and effective privacy. Retain copied-substance dependencies in `privacy-sources`; merge existing provenance. Internal derivatives may include private work with inherited classification. Public writers reject private/unknown substance or retain a bare link. Removing a source requires transferring its underlying dependencies.

## Prevention

Test directory and final-file replacement, same-byte recreated sources, and subprocess termination immediately after claiming. Test source reclassification after a public derivative is stored. Full internal views must record indirect count and ranking dependencies, including rows omitted by display caps; display limits never establish a complete inventory count.

## Related

- [Privacy contract](../../../00_Meta/restricted-private.md)
- [Home specification](../../tools/brain/spec/24-home-brain-home.md)
- [Index merge conflicts](index-merge-conflicts.md)
