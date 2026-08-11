---
name: onboard-harness
description: Install this vault's agent primitives into a coding harness's user-level config — symlink-first — wire the harness to a shared second-brain registration, and install the harness's overlay (harness-native rules, hooks, config) where one ships. Use when setting up Claude Code, Codex, opencode, Pi, Cursor, Copilot, or Muse Code to use this vault everywhere, or to re-sync or uninstall a previous install.
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
   Link each skill **folder** individually (never the whole `skills/` dir — the user may have their own skills there). An existing correct link is a no-op; an existing foreign file/dir is **never overwritten** — report it and skip. A link/copy already recorded by this second-brain manifest for another registered vault is **shared-managed, not foreign**: record this vault as another consumer and preserve the current provider. Record a content hash per consumer/provider. If registered vaults carry different versions of the same globally installed skill, report managed version drift and keep the current provider; never silently retarget or overwrite a shared global skill just because another vault was onboarded.
2. **Copy fallback.** Where symlinks are unavailable (e.g. Windows without Developer Mode), copy instead and record the copy + a content hash in the manifest so later runs detect drift and offer re-sync. Shared copied skills follow the same provider/consumer ownership rule as symlinks.
3. **Shared second-brain registration.** Create or reconcile `~/.agents/second-brain/AGENTS.md`. This is installer-managed user state, not a tracked vault file. It is a stable registry that harness adapters reference, and it may contain **multiple adopted vaults** (for example separate personal and work brains). On first install for a vault, generate a stable opaque `registration_id` and persist it in that vault's manifest entry; do not derive the ID from the filesystem path, because the vault may move. Add or replace only that vault's marker-delimited registry entry and preserve all other registered vault entries. Render adopter-specific paths only here (and in the manifest), never into this template repository. The registry stays thin:
   ```markdown
   # Second Brain Registry

   Registered second-brain vaults are listed below. Use only the vault whose label or purpose materially matches the current task. Do not load unrelated vaults; if none is relevant, continue without personal context.

   <!-- BEGIN second-brain vault <registration-id> -->
   ## <vault-label>

   Vault root: `<resolved-vault-path>`

   This vault contains owner-specific context such as preferences, current priorities, projects, responsibilities, and reference material. When that context materially helps, read `<resolved-vault-path>/AGENTS.md` and follow its bootstrap and retrieval instructions.
   <!-- END second-brain vault <registration-id> -->
   ```
   Default `<vault-label>` to a human-readable repository/directory name when no better context label is already known; do not require a technical setup question just to obtain it. Re-running replaces only the entry matching `registration_id`; if the vault moved, update its path in that entry without disturbing the others. Duplicate entries for the same `registration_id` collapse to one canonical entry.
4. **Harness memory adapter.** Add a marker-delimited block to the harness's **documented user-level instruction surface**, creating that file only when the harness supports a file there. The block points to `~/.agents/second-brain/AGENTS.md`, **not directly to any vault**. Prefer native include/import syntax when verified for that harness; otherwise use a plain instruction telling the agent to read the shared registry when owner context is relevant. Example native include:
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
   The exact surface and syntax are harness-specific and come from its wiring doc. Everything outside the markers is the user's own content: never touch it. Re-running replaces exactly one harness-level managed block; if duplicate harness blocks are found, collapse them to one canonical block. Because all adopted vaults share the registry, onboarding another vault does **not** add another harness-level block.
5. **Shared config files: merge, never link.** Where a primitive lives inside a config file the user also owns (settings JSON/TOML, MCP server registrations, hook registrations), edit additively and idempotently per the wiring doc — symlinking whole files would clobber user config.
6. **Pre-commit hook.** In the vault clone: `git config core.hooksPath .githooks`. Also install the generated-file merge driver in the same clone: `git config merge.regenerate.driver true` (keeps ours on conflicts in the committed generated files; the hooks regenerate them — see `.gitattributes`).
7. **Overlay.** If `<vault>/10_Agents/harnesses/<harness>/overlay/manifest.json` exists, install its artifacts per that manifest (schema and method semantics: the Overlays section of `10_Agents/harnesses/README.md`). Overlays carry only harness-native primitives a cross-harness standard cannot express; most harnesses ship none, and that is not an error. Apply each artifact by its declared `install.method` under the same contract as every step above: `copy` places the payload at the resolved target (an existing foreign file is never overwritten — report and skip; record a content hash for drift re-sync); `marker-block` merges a marker-delimited block into the user-owned target file, touching nothing outside the markers; `generate` seeds the target from the payload template and runs the manifest's recorded generator command (re-run on later syncs); `shipped-in-repo` artifacts are tracked repo config already present in every clone — install nothing, record nothing. Resolve `<vault>` and `~` placeholders only at install time; record each installed overlay artifact (id, resolved target, hash where applicable) under this vault's entry in the machine manifest.
8. **Manifest.** Record every action in `~/.agents/second-brain-manifest.json`: stable `registration_id`, vault path, vault label, shared registration path, harness, and each created link / copy (with hash) / memory-file block / merged config entry / registered skills location / installed overlay artifact. Model the manifest as multiple vault entries plus shared resources (harness adapters and globally installed skills) with provider/consumer ownership so onboarding or removing one vault cannot overwrite or delete another vault's state. Idempotence and uninstall both read this file.

## Optional: recommended community content

After the core install, optionally offer items from the curated catalog [[06_Resources/recommended-skills]] (links-only, pinned refs). This step is **opt-in and additive** — skipping it changes nothing above.

1. **Per-item owner sign-off.** First-party items may install by default; **community items require an explicit yes from the owner, per item**, before anything is fetched. Record each sign-off (item, pinned ref, decision, date) in the manifest entry for the install. No sign-off, no install.
2. **Fetch from the pinned ref only.** Download the item's content at its commit-sha- or tag-pinned URL — never a moving branch. When the vault ships the item as a pinned submodule under `.extern/` (see the catalog's **Local checkout** field), prefer copying from the initialized submodule (`git submodule update --init .extern/<name>` — the checked-out commit **is** the pin, no network fetch needed); verify the submodule sits at the catalog's pinned SHA before copying. Skip any catalog item still marked `TODO-pin`. Install as a **copy** into the harness's user scope (`~/.agents/skills/<name>/` plus the Claude Code path, following the same discovery paths, foreign-file protections, and shared provider/consumer rules as step 1 of the install algorithm), with a content hash recorded so later runs detect drift against the pin.
3. **User-scope memory-file content.** Curated `AGENTS.md`/`CLAUDE.md` blocks from the catalog install into the harness's user-level instruction surface as **their own marker-delimited blocks** (one per item, e.g. `<!-- BEGIN second-brain recommended <item> -->` … `<!-- END second-brain recommended <item> -->`) — offer the catalog's listed memory-file blocks here by name (currently the karpathy coding guidelines; see [[06_Resources/recommended-skills]] § Recommended user-scope memory-file content) — managed exactly like the registration block in step 4: everything outside the markers is the user's own content, re-runs replace only the matching block, duplicates collapse to one.
4. **Manifest and reversibility.** Record each installed community item in the manifest with origin `community`, its pinned ref, content hash, sign-off record, and every file/block created. Uninstall removes exactly these recorded resources alongside the vault's own, under the same shared-ownership rules.
5. **Separation invariant.** Community content is installed only into user scope on the adopter's machine — it is **never** written into the vault or committed to this repository. The vault carries only the curated pointers in [[06_Resources/recommended-skills]].

## Re-run and uninstall

- **Re-run** (same vault + harness): identify the vault by its persisted `registration_id`; recreate missing resources it owns, refresh drifted copies only when that vault is the recorded provider, replace only that vault's registry entry with its current path/label, and reconcile the shared harness adapter to exactly one canonical block. A fully-installed state is a no-op. If another registered vault provides a shared skill, compare hashes and record this vault as a consumer rather than stealing ownership. Overlay artifacts re-sync the same way: re-apply a `copy` only on recorded-hash drift, reconcile a `marker-block` to exactly one canonical block, and re-run a `generate` artifact's generator; `shipped-in-repo` artifacts never need re-run work.
- **Uninstall**: preflight shared ownership before changing anything. Remove exactly what that vault's manifest entry exclusively owns — its private links/copies/registrations and its marker-delimited registry entry. Shared harness adapters and global skills are reference-counted: remove them only when no remaining registered vault consumes them. If the departing vault is the provider for a shared skill and consumers remain, transfer the provider to a remaining vault **only when its recorded content hash matches**; if no remaining copy matches, stop before mutation and ask the owner which remaining version should become global. Never leave a broken symlink, silently change a shared skill version, delete another vault's entry, or alter user-owned surrounding config. Remove `~/.agents/second-brain/AGENTS.md` only when the registry has no remaining vault entries. Overlay artifacts reverse by their manifest-declared `reverse.method` and only when this vault's machine-manifest entry records them as installed: `delete` removes the created file, `remove-marker-block` strips exactly the managed block, and `shipped-in-repo` artifacts (`reverse: none`) are tracked repo config that uninstall never touches.

## Rules

- **Template portability invariant:** no adopter-specific filesystem path, username, home directory, repository location, machine identifier, or generated `registration_id` may be written into a tracked template file. Resolve machine-specific values only at install time; they may appear only in adopter-local configuration and the manifest.
- Everything happens **at install time on the adopter's machine** — links are never committed to the repo (PRD §8.2 retired in-repo symlinks).
- No credentials or machine-specific paths ever get committed (PRD §16.2); the manifest and shared registration live in the home directory, not the vault.
- A harness adapter should reference the stable shared registry rather than duplicate its contents or embed a vault path. Native include/import > documented config injection > plain-path instruction; never depend on undocumented automatic discovery of `~/.agents/second-brain/AGENTS.md`.
- Report a summary at the end: created / already-correct / skipped-foreign / shared-managed / copied, the affected vault registry entry, and the harness instruction surfaces touched.

## References

- `00_Meta/prd.md` §8.3 (support tiers), §19 M6 (the install decision)
- `10_Agents/harnesses/<name>/wiring.md` — per-harness paths (shipped with the adapters)
- `10_Agents/harnesses/README.md` §Overlays — the `overlay/manifest.json` schema and install/reverse method semantics
- `10_Agents/harnesses/<name>/overlay/manifest.json` — per-harness overlay artifacts, where an overlay ships
- `06_Resources/harness-primitives-research.md` — the research grounding the path map
