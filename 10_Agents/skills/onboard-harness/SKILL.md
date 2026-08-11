---
name: onboard-harness
description: Install this vault's agent primitives into a coding harness's user-level config — symlink-first — and wire the harness's memory file to import the vault entrypoint. Use when setting up Claude Code, Codex, opencode, Pi, Cursor, Copilot, or Muse Code to use this vault everywhere, or to re-sync or uninstall a previous install.
title: "Skill: Onboard Harness"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Onboard Harness

**CODE stage:** Onboarding.

Make the vault's skills and context available in **every session** of a harness, not just when working inside this repo. User scope, symlink-first, manifest-driven, idempotent, reversible.

## Inputs

- **Harness**: which one to onboard (see the support tiers in `00_Meta/prd.md` §8.3).
- **Vault path**: the absolute path of this vault's local clone (derive from the working directory; confirm with the user if ambiguous).

Consult `10_Agents/harnesses/<harness>/wiring.md` when it exists — it is authoritative for that harness's exact paths and import syntax. The standards defaults below cover harnesses without a wiring doc.

## Install algorithm

1. **Skills (symlink-first).** Create symlinks from the harness's user-level skills discovery path back to the canonical folders:
   - `~/.agents/skills/<skill-name>` → `<vault>/10_Agents/skills/<skill-name>` — the shared standard path scanned by Codex, opencode, Pi, Cursor, and Muse Code (one install covers all five).
   - `~/.claude/skills/<skill-name>` → same targets — Claude Code scans only its own directory.
   - **Copilot is the exception — no symlinks:** its CLI ignores symlinked skills and does not reliably discover `~/.agents/skills/`. Register the vault's real directory instead (`copilot skill add <vault>/10_Agents/skills`; uninstall via `copilot skill remove`), or copy skill folders into `~/.copilot/skills/` with hashes recorded for drift re-sync — see [[10_Agents/harnesses/copilot/wiring]].
   Link each skill **folder** individually (never the whole `skills/` dir — the user may have their own skills there). An existing correct link is a no-op; an existing foreign file/dir is **never overwritten** — report it and skip.
2. **Copy fallback.** Where symlinks are unavailable (e.g. Windows without Developer Mode), copy instead and record the copy + a content hash in the manifest so later runs detect drift and offer re-sync.
3. **Memory-file import block.** Append a marker-delimited block to the harness's **user-level** memory file (its `CLAUDE.md` equivalent — e.g. `~/.claude/CLAUDE.md` for Claude Code), creating the file if absent, using the adopter's absolute vault path:
   ```
   <!-- BEGIN second-brain vault import (managed by onboard-harness) -->
   @/absolute/path/to/vault/AGENTS.md
   <!-- END second-brain vault import -->
   ```
   The import line inside the block is harness-specific (Claude Code uses `@path` imports; AGENTS.md-native harnesses may instead need an instruction line or a config entry — per wiring doc). Everything outside the markers is the user's own content: never touch it. Re-running replaces only the block; uninstall removes only the block.
4. **Shared config files: merge, never link.** Where a primitive lives inside a config file the user also owns (settings JSON/TOML, MCP server registrations, hook registrations), edit additively and idempotently per the wiring doc — symlinking whole files would clobber user config.
5. **Pre-commit hook.** In the vault clone: `git config core.hooksPath .githooks`.
6. **Manifest.** Record every action in `~/.agents/second-brain-manifest.json`: vault path, harness, and each created link / copy (with hash) / memory-file block / merged config entry / registered skills location. Idempotence and uninstall both read this file.

## Re-run and uninstall

- **Re-run** (same vault + harness): reconcile against the manifest — recreate missing links, refresh drifted copies, rewrite the memory block. A fully-installed state is a no-op.
- **Uninstall**: remove exactly what the manifest records — links, copied dirs, the marker block, merged entries — and delete the manifest entry. Nothing else.

## Rules

- Everything happens **at install time on the adopter's machine** — links are never committed to the repo (PRD §8.2 retired in-repo symlinks).
- No credentials or machine-specific paths ever get committed (PRD §16.2); the manifest lives in the home directory, not the vault.
- Report a summary at the end: created / already-correct / skipped-foreign / copied, and the memory files touched.

## References

- `00_Meta/prd.md` §8.3 (support tiers), §19 M6 (the install decision)
- `10_Agents/harnesses/<name>/wiring.md` — per-harness paths (shipped with the adapters)
- `06_Resources/harness-primitives-research.md` — the research grounding the path map
