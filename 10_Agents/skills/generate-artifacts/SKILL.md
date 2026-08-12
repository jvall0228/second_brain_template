---
name: generate-artifacts
description: Generate, verify, or locally open the vault's deterministic offline link graph and health dashboard. Use when the owner asks for a vault visualization, graph, health dashboard, artifact refresh, artifact freshness check, or local HTML view.
title: "Skill: Generate Local Artifacts"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Generate Local Artifacts

Use the dedicated `brain artifacts` pipeline. Keep these views local; Mermaid remains the better choice for small diagrams inside notes.

## Workflow

1. Preview the exact three-file plan with `brain artifacts` or inspect it with `brain artifacts --json`. Preview and `--check` write nothing.
2. Explain the source scope, privacy filters, bounded graph caps, and health metrics. Never supplement the output with restricted, untracked, environment, credential, or raw-body content.
3. When the owner asks to refresh the committed artifacts, run `brain artifacts --write`. Never hand-edit files owned by the generator.
4. Run `brain artifacts --check`. Open fresh local views with `brain artifacts --open`, or use the VS Code artifact task.

## Safety contract

- Inputs are Git-tracked shared notes read through the confined snapshot layer. Restricted notes, notes targeting them, non-current environment content, secret-bearing notes, unsafe paths, untracked files, and generated outputs are filtered before derivation.
- Outputs contain bounded titles, relative paths, safe tags, link edges, and aggregate health counts only. They contain no raw note bodies, task text, credentials, host paths, or owner username.
- The self-contained HTML has no CDN or runtime network path. Its CSP hashes the inline style, data, and script; dynamic text uses safe DOM APIs.
- `--write` may mutate only `08_Assets/artifacts/link-graph.html`, `health-dashboard.html`, and `manifest.json`. It preserves foreign, edited, linked, mode-changed, or concurrently inserted content.
- Hosting is not implemented here. Any future host must be separately configured, environment-scoped, owner-consented, and privacy-reviewed. Notifications are independent.
