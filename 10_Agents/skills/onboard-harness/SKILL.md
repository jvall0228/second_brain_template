---
name: onboard-harness
description: Install this vault's agent primitives into a coding harness's user-level config — symlink-first — and wire the harness to a shared second-brain registration. Use when setting up Claude Code, Codex, opencode, Pi, Cursor, Copilot, or Muse Code to use this vault everywhere, or to re-sync or uninstall a previous install.
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
3. **Shared second-brain registration.** Create or reconcile `~/.agents/second-brain/AGENTS.md`. This is installer-managed user state, not a tracked vault file. It is the one stable user-level location every harness adapter points at. Render the adopter's resolved vault path only here (and in the manifest), never into this template repository. Keep the file intentionally thin:
   ```markdown
   # Second Brain

   A personal second-brain vault is available at:

   `<resolved-vault-path>`

   It contains owner-specific context such as preferences, current priorities, projects, responsibilities, and reference material.

   When owner-specific context would materially help with the current task, read `<resolved-vault-path>/AGENTS.md` and follow its bootstrap and retrieval instructions. Do not scan the vault indiscriminately when the task does not need personal context.
   ```
   Re-running replaces this installer-managed file with the canonical rendering for the current vault path. If the path changes because the vault moved, this is the only context-registration file whose vault path must change.
4. **Harness memory adapter.** Add a marker-delimited block to the harness's **documented user-level instruction surface**, creating that file only when the harness supports a file there. The block points to `~/.agents/second-brain/AGENTS.md`, **not directly to the vault**. Prefer native include/import syntax when verified for that harness; otherwise use a plain instruction telling the agent to read the shared registration when owner context is relevant. Example native include:
   ```markdown
   <!-- BEGIN second-brain registration (managed by onboard-harness) -->
   @~/.agents/second-brain/AGENTS.md
   <!-- END second-brain registration -->
   ```
   Example plain-path fallback:
   ```markdown
   <!-- BEGIN second-brain registration (managed by onboard-harness) -->
   Personal second-brain context is registered in `~/.agents/second-brain/AGENTS.md`. Read it when owner-specific context would materially help with the task.
   <!-- END second-brain registration -->
   ```
   The exact surface and syntax are harness-specific and come from its wiring doc. Everything outside the markers is the user's own content: never touch it. Re-running replaces exactly one managed block; if duplicate managed blocks are found, collapse them to one canonical block. Uninstall removes only that block.
5. **Shared config files: merge, never link.** Where a primitive lives inside a config file the user also owns (settings JSON/TOML, MCP server registrations, hook registrations), edit additively and idempotently per the wiring doc — symlinking whole files would clobber user config.
6. **Pre-commit hook.** In the vault clone: `git config core.hooksPath .githooks`.
7. **Manifest.** Record every action in `~/.agents/second-brain-manifest.json`: vault path, shared registration path, harness, and each created link / copy (with hash) / memory-file block / merged config entry / registered skills location. Idempotence and uninstall both read this file.

## Re-run and uninstall

- **Re-run** (same vault + harness): reconcile against the manifest — recreate missing links, refresh drifted copies, rewrite the shared registration for the current vault path, and reconcile the harness adapter to exactly one canonical block. A fully-installed state is a no-op.
- **Uninstall**: remove exactly what the manifest records — links, copied dirs, the harness marker block, merged entries, and that vault's registration/manifest entry. Remove `~/.agents/second-brain/AGENTS.md` only when no remaining manifest entry uses it. Nothing else.

## Rules

- **Template portability invariant:** no adopter-specific filesystem path, username, home directory, repository location, or machine identifier may be written into a tracked template file. Resolve machine-specific values only at install time; they may appear only in adopter-local configuration and the manifest.
- Everything happens **at install time on the adopter's machine** — links are never committed to the repo (PRD §8.2 retired in-repo symlinks).
- No credentials or machine-specific paths ever get committed (PRD §16.2); the manifest and shared registration live in the home directory, not the vault.
- A harness adapter should reference the stable shared registration rather than duplicate its contents or embed the vault path. Native include/import > documented config injection > plain-path instruction; never depend on undocumented automatic discovery of `~/.agents/second-brain/AGENTS.md`.
- Report a summary at the end: created / already-correct / skipped-foreign / copied, the shared registration state, and the harness instruction surfaces touched.

## References

- `00_Meta/prd.md` §8.3 (support tiers), §19 M6 (the install decision)
- `10_Agents/harnesses/<name>/wiring.md` — per-harness paths (shipped with the adapters)
- `06_Resources/harness-primitives-research.md` — the research grounding the path map
