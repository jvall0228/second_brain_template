---
title: "brain Spec — Parsing, Link Resolution, and Index Schema"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# `brain` Spec — Parsing, Link Resolution, and Index Schema

## Sections

One file per numbered section under `spec/`; this file is the index and carries the preamble above. Section numbers are stable, and the `§N.x` cross-references used throughout the spec, the [README](README.md), and the skills name these files. Split from the single 925-line document on 2026-09-04; the text is unchanged apart from re-relativized links and headings lifted one level.

- [§1. Scope and status](spec/01-scope-and-status.md)
- [§2. Corpus](spec/02-corpus.md)
- [§3. Text model](spec/03-text-model.md)
- [§4. Frontmatter grammar](spec/04-frontmatter-grammar.md)
- [§5. Generic link grammar](spec/05-generic-link-grammar.md)
- [§6. Link and fragment resolution](spec/06-link-and-fragment-resolution.md)
- [§7. Body extraction](spec/07-body-extraction.md)
- [§8. Index schema and determinism](spec/08-index-schema-and-determinism.md)
- [§9. CLI command semantics](spec/09-cli-command-semantics.md)
- [§10. Validate semantics](spec/10-validate-semantics.md)
- [§11. Divergences from Obsidian and known limitations](spec/11-divergences-from-obsidian-and.md)
- [§12. Decisions this spec makes beyond the plan (review focus)](spec/12-decisions-this-spec-makes.md)
- [§13. Future considerations (out of M5 scope)](spec/13-future-considerations-out-of.md)
- [§14. Curation signals (ops plan Phase 4)](spec/14-curation-signals-ops-plan.md)
- [§15. Vault config (`00_Meta/config.yaml`) — issue #2](spec/15-vault-config-00-meta.md)
- [§16. Health report (`brain report`) — issue #16](spec/16-health-report-brain-report.md)
- [§17. Task tracking (`brain tasks`) — issue #28](spec/17-task-tracking-brain-tasks.md)
- [§18. Semantic search (QMD — issue #8)](spec/18-semantic-search-qmd.md)
- [§19. Remote safety (`brain remote-safety`) — issue #83](spec/19-remote-safety-brain-remote.md)
- [§20. Environment identity and scoped retrieval](spec/20-environment-identity-and-scoped.md)
- [§21. Portable `brain` resolver and installer](spec/21-portable-brain-resolver-and.md)
- [§22. Legacy link migration (`brain migrate-links`) — issue #74](spec/22-legacy-link-migration-brain.md)
- [§23. Actions You May Take (`brain aymt`) — issue #79](spec/23-actions-you-may-take.md)
- [§24. Home (`brain home`) — issue #78](spec/24-home-brain-home.md)
- [§25. Local offline artifacts (`brain artifacts`) — issue #23](spec/25-local-offline-artifacts-brain.md)
- [§26. Push-only owner notifications (`brain notify`) — issue #21](spec/26-push-only-owner-notifications.md)
- [§27. Project and Area registry (`brain projects`)](spec/27-project-and-area-registry.md)
- [§28. Bootstrap compilation (`brain bootstrap`, `brain context --for`)](spec/28-bootstrap-compilation-brain-bootstrap.md)
- [§29. Triage archival, periodic traces, and the agent logs (`brain triage-archive`, `brain trace`, `brain gap`, `brain accepted`)](spec/29-triage-archive-and-trace.md)
