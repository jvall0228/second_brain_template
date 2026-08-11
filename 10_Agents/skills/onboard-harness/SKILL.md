---
name: onboard-harness
description: Verify this vault's repository-local agent skills and harness wiring, then optionally preview or apply an explicit user-global install. Use when setting up Claude Code, Codex, opencode, Pi, Cursor, Copilot, or Muse Code, or when checking, re-syncing, or uninstalling prior global wiring.
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

Make the vault work in the current repository first. A clean clone already
contains generated text adapters under `.agents/skills/` and `.claude/skills/`;
global availability outside this repository is a separate, optional operation.

## Inputs

- **Mode**: `project` (default), `global-preview`, `global-apply`, re-sync, or uninstall.
- **Harness**: needed for global or harness-specific checks (see `00_Meta/PRD.md` §8.3).
- **Vault path**: derive the clone root without writing it into tracked files.

Consult `10_Agents/harnesses/<harness>/wiring.md` when it exists — it is authoritative for that harness's exact paths and import syntax. The standards defaults below cover harnesses without a wiring doc.

## Project verification (default)

Project mode is read-only and is the default even when the owner merely says
"set up this harness." It must make **zero writes outside the clone** and must
not create a user manifest, registration, skill link/copy, or harness memory
block.

1. Run `python3 10_Agents/tools/skill_adapters/gen_skill_adapters.py --check`.
   Report missing, extra, symlinked, version-drifted, or metadata-mismatched
   adapters; regenerate inside the repository only after normal repository
   change approval.
   Executable read-only check:
   `python3 10_Agents/tools/skill_adapters/harness_setup.py project --harness <harness> --json`.
2. Confirm the harness's project entrypoint and generated discovery path from
   the compatibility table in `10_Agents/harnesses/README.md`. For Pi, also
   explain that project skills stay hidden until the repository is trusted.
3. Verify the repository-scoped hook/config described by the wiring doc. Offer
   to arm this clone's git hook separately; do not treat user-global setup as
   necessary for repository use.
4. End with a project-verification result. Mention global availability only as
   an optional follow-up for sessions started outside this repository.

## User-global approval boundary

Global mode is never inferred from project setup. It has two distinct passes:

1. **`global-preview` (read-only):** resolve and display every exact external
   path, command registration, link/copy, marker block, config merge, overlay,
   and manifest entry that would change. Label foreign collisions, shared
   ownership, and reversible actions. The preview makes zero writes, including
   to a supplied fake home. Run the executable base preview:
   `python3 10_Agents/tools/skill_adapters/harness_setup.py global-preview --harness <harness> --home <resolved-home> --json`;
   include wiring-doc overlay/config actions before approval. It has no apply command.
2. **`global-apply`:** only after the owner explicitly selects global mode and
   approves that exact preview. Re-run preflight immediately before mutation;
   if any target changed, discard the preview and present a new one. Consent to
   project verification, onboarding generally, or an earlier different preview
   is not consent to apply.

## User-global apply algorithm

1. **Skills (symlink-first).** Create only the links/copies approved in the exact global preview from the harness's user-level skills discovery path back to the canonical folders:
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

## Optional: recommended components

After the core install, optionally install **recommended components** from the registry `10_Agents/components/manifest.json` ([[10_Agents/components/README]], schema v1). Its `community` entries are the human-facing catalog [[06_Resources/recommended-skills]] (links-only; the skill and memory-block items **track their upstream branch and install the latest** commit); its `first-party` entries are the harness overlays (step 7 above, surfaced here as components) and the vault-config presets. This step is **opt-in and additive** — skipping it changes nothing above. Drive it from the manifest, **group by `kind`**, apply each component's declared `install` method/scope/target under the same M6 contract as everything above, and record every action in the machine manifest so it stays reversible. There is no second install model.

1. **Per-component sign-off.** Read each component's `signoff`. A `default-ok` component (the first-party overlays) may install without asking per item. An `owner-per-item` component — every `community` item, plus the vault-config presets — requires an **explicit yes from the owner, per item**, before anything is fetched or changed. Record each sign-off (component id, pinned ref where applicable, decision, date) in the manifest entry for the install. No sign-off, no install.
2. **`skill` components (`install.method: copy`, scope user).** These **track their upstream branch and install the latest** commit — `source.track` names the branch (`main`). The vault ships each as a branch-tracking submodule under `.extern/` (`source.type: submodule`, the catalog's **Local checkout** field): run `git submodule update --init --remote .extern/<name>` to fetch the current tip of the tracked branch, then copy from the checked-out submodule. Skip any catalog item still marked `TODO-pin`. Because there is no frozen pin, the **per-item owner sign-off (step 1) happens against the content fetched at install time — that review is the supply-chain safeguard.** Copy into the harness user scope at `install.target` (`~/.agents/skills/<id>/` plus the Claude Code path, following the same discovery paths, foreign-file protections, and shared provider/consumer rules as step 1 of the install algorithm), with a content hash recorded so later runs detect drift and can re-offer an update.
3. **`memory-block` components (`install.method: marker-block`, scope user).** When the block's `source.type` is `submodule` (the karpathy coding guidelines on `.extern/andrej-karpathy-skills`, tracking `main`), first run `git submodule update --init --remote .extern/<name>` to fetch the current tip of the tracked branch — exactly as for `skill` components in step 2 — so the per-item owner sign-off (step 1) reviews the freshly fetched content, not a stale checkout. Curated `AGENTS.md`/`CLAUDE.md` blocks install into the harness user-level instruction surface at `install.target` (and the shared `~/.agents` surface) as **their own marker-delimited blocks** (one per item, e.g. `<!-- BEGIN second-brain recommended <id> -->` … `<!-- END second-brain recommended <id> -->`) — offer the catalog's listed memory-file blocks here by name (currently the karpathy coding guidelines; see [[06_Resources/recommended-skills]] § Recommended user-scope memory-file content) — managed exactly like the registration block in step 4 of the install algorithm: everything outside the markers is the user's own content, re-runs replace only the matching block, duplicates collapse to one.
4. **`overlay` components (`install.method: shipped-in-repo`, scope project).** These make the harness overlays discoverable in the registry; each component just points at the harness's own `overlay/manifest.json`, which **remains the authority** for its artifacts. Install exactly as step 7 of the install algorithm — the same overlay engine, nothing new to run.
5. **`vault-config-preset` components (`install.method: merge-config`, scope vault).** A preset is a config fragment merged into `00_Meta/config.yaml`. This is a **vault** write, not a user-scope one — onboard-harness does not perform it; [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] applies it under its live-session write exception. Its `reverse.method` is `restore-config`.
6. **Manifest and reversibility.** Record each installed component in the manifest with its provenance (`community` items marked as such), pinned ref where applicable, content hash, sign-off record, and every file/block created. Uninstall removes exactly these recorded resources by each component's `reverse.method` (`delete` / `remove-marker-block` / `restore-config` / `none`), alongside the vault's own, under the same shared-ownership rules.
7. **Separation invariant.** Community content is installed only into user scope on the adopter's machine — it is **never** written into the vault or committed to this repository. The vault carries only the curated pointers in [[06_Resources/recommended-skills]].

## Re-run and uninstall

- **Re-run** (same vault + harness): identify the vault by its persisted `registration_id`; recreate missing resources it owns, refresh drifted copies only when that vault is the recorded provider, replace only that vault's registry entry with its current path/label, and reconcile the shared harness adapter to exactly one canonical block. A fully-installed state is a no-op. If another registered vault provides a shared skill, compare hashes and record this vault as a consumer rather than stealing ownership. Overlay artifacts re-sync the same way: re-apply a `copy` only on recorded-hash drift, reconcile a `marker-block` to exactly one canonical block, and re-run a `generate` artifact's generator; `shipped-in-repo` artifacts never need re-run work.
- **Uninstall**: preflight shared ownership before changing anything. Remove exactly what that vault's manifest entry exclusively owns — its private links/copies/registrations and its marker-delimited registry entry. Shared harness adapters and global skills are reference-counted: remove them only when no remaining registered vault consumes them. If the departing vault is the provider for a shared skill and consumers remain, transfer the provider to a remaining vault **only when its recorded content hash matches**; if no remaining copy matches, stop before mutation and ask the owner which remaining version should become global. Never leave a broken symlink, silently change a shared skill version, delete another vault's entry, or alter user-owned surrounding config. Remove `~/.agents/second-brain/AGENTS.md` only when the registry has no remaining vault entries. Overlay artifacts reverse by their manifest-declared `reverse.method` and only when this vault's machine-manifest entry records them as installed: `delete` removes the created file, `remove-marker-block` strips exactly the managed block, and `shipped-in-repo` artifacts (`reverse: none`) are tracked repo config that uninstall never touches.

## Rules

- Project verification and every preview are read-only outside the clone.
- Global apply requires an explicit global-mode request plus approval of the
  exact external-path preview; stale previews are invalid.
- **Template portability invariant:** no adopter-specific filesystem path, username, home directory, repository location, machine identifier, or generated `registration_id` may be written into a tracked template file. Resolve machine-specific values only at install time; they may appear only in adopter-local configuration and the manifest.
- User-global links/copies happen only during approved global apply — links are never committed to the repo (PRD §8.2 retired in-repo symlinks). Project discovery uses committed generated text adapters.
- No credentials or machine-specific paths ever get committed (PRD §16.2); the manifest and shared registration live in the home directory, not the vault.
- A harness adapter should reference the stable shared registry rather than duplicate its contents or embed a vault path. Native include/import > documented config injection > plain-path instruction; never depend on undocumented automatic discovery of `~/.agents/second-brain/AGENTS.md`.
- Report a summary at the end: created / already-correct / skipped-foreign / shared-managed / copied, the affected vault registry entry, and the harness instruction surfaces touched.

## References

- `00_Meta/PRD.md` §8.3 (support tiers), §19 M6 (the install decision)
- `10_Agents/harnesses/<name>/wiring.md` — per-harness paths (shipped with the adapters)
- `10_Agents/harnesses/README.md` §Overlays — the `overlay/manifest.json` schema and install/reverse method semantics
- `10_Agents/harnesses/<name>/overlay/manifest.json` — per-harness overlay artifacts, where an overlay ships
- `06_Resources/harness-primitives-research.md` — the research grounding the path map
