---
title: "DR: Static-Site Framework Choice"
tags:
  - type/decision
  - audience/human
updated: 2025-01-10
---

# Static-Site Framework Choice

> **Sample note from the Second Brain template** — delete along with the rest of `example-project/`.

## Status

Accepted

## Context

The personal-website redesign needs a static-site generator. It should be easy to
maintain, fast to build, and something I already know or can pick up quickly.

## Options Considered

1. **Astro** — Modern, component-friendly, ships zero JS by default. Slight learning curve.
2. **Plain HTML + CSS** — Zero dependencies, but tedious to keep consistent across pages.

## Decision

Go with Astro — its content-collection model fits a blog-plus-pages site, and the build
output is fast and dependency-light.

## Consequences

- Need to learn Astro's content collections (small — one evening).
- Layout components make future redesigns cheaper.

## Related

- Project: [[04_Projects/example-project/README|Example Project]]
