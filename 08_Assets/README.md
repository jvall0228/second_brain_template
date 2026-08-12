---
title: "Assets"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-11
expires: 2027-08-11
---

# Assets

Non-markdown files — images, PDFs, attachments, and other binary assets referenced by vault notes.

## When to Put Something Here

Any file that isn't a markdown note: screenshots, diagrams, exported PDFs, audio clips, etc. Reference these from notes with portable relative Markdown images such as `![Diagram](../08_Assets/diagram.png)` or links such as `[PDF](../08_Assets/report.pdf)`. Percent-encode spaces and Unicode bytes in destinations.

## Lifecycle

This directory is **append-only** by default. Move large or obsolete assets to `07_Archives/assets/` (or delete them if they're reproducible) rather than editing in place.
