---
title: "Harness Adapters"
tags:
  - type/meta
  - audience/agent
  - audience/human
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# Harness Adapters

Per-harness adapters for the support tiers in [[00_Meta/prd]] §8.3. **Standards-first:** the entrypoint (`AGENTS.md`), the skills library (`10_Agents/skills/`, Agent Skills format), and the `brain` CLI work in any harness with no adapter — each directory here carries **only what a cross-harness standard cannot**: exact config paths, import syntax, caps, and trust gates.

Every adapter ships a `wiring.md` (entrypoint loading, skills install paths, hook installation, how the harness invokes `brain`, harness-specific caveats) and reference config files to copy or merge. The [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] skill consumes these wiring docs for user-scope installs.

| Adapter | Tier | Wiring |
|---------|------|--------|
| [[10_Agents/harnesses/claude-code/wiring\|Claude Code]] | P0 | needs the `CLAUDE.md` import; scans `.claude/skills/` only |
| [[10_Agents/harnesses/codex/wiring\|Codex]] | P0 | native `AGENTS.md`; 32 KiB project-doc cap; trusted-project config |
| [[10_Agents/harnesses/opencode/wiring\|opencode]] | P0 | native `AGENTS.md`; `instructions[]` makes bootstrap deterministic |
| [[10_Agents/harnesses/pi/wiring\|Pi]] | P0 | native `AGENTS.md`; trust gate; no MCP (extensions instead) |
| [[10_Agents/harnesses/copilot/wiring\|Copilot]] | P0 | native `AGENTS.md` on agent surfaces; shipped `.github/` shim + cloud-agent validate hook |
| [[10_Agents/harnesses/cursor/wiring\|Cursor]] | P1 | native `AGENTS.md`; `.mdc` rules; only harness with a real ignore file |
| [[10_Agents/harnesses/muse-code/wiring\|Muse Code]] | P1 | volatile (launched 2026-08-05); user-scope config only |

## Overlays

An adapter may additionally ship an **overlay**: installable harness-native primitives under `10_Agents/harnesses/<name>/overlay/` — e.g. Cursor glob-scoped `.mdc` rules and its `.cursorignore` template, or Copilot's instructions shim and cloud-agent hook. Overlays are governed by the **standards-first rule** ([[00_Meta/prd]] §8.3, design principles §9.3): an overlay carries **only what a cross-harness standard cannot express**. If `AGENTS.md`, the Agent Skills format, or the `brain` CLI can do the job, the overlay must not duplicate it — most adapters correctly ship **no** `overlay/` directory, and that absence is the expected default, not a gap.

Every overlay contains a `manifest.json` describing what it installs, where, and how to reverse it:

- **Top level:** `overlay_version` (schema version, currently `1`), `harness` (must equal the adapter directory name), `description`, `standards_gap` (the explicit justification — which capability no cross-harness standard reaches), and `artifacts`.
- **Per artifact:** a unique `id`, `kind`, `source` + `source_root` (`overlay` = payload file inside `overlay/`; `repo` = working config already shipped elsewhere in the repository, e.g. Copilot's `.github/` files), an `install` object (`method`, portable `target`, `scope`), and a `reverse` object (`method`, optional `condition`).
- **Install methods:** `copy` (place the payload at the target; foreign files are never overwritten), `marker-block` (merge a marker-delimited block into a user-owned config file), `generate` (produce the target by running the recorded `generator` command, seeded from the payload template), `shipped-in-repo` (the artifact is tracked repo config present in every clone — nothing to install).
- **Reverse methods:** `delete`, `remove-marker-block`, `none` (only valid for `shipped-in-repo` — removing tracked config is a repo change, not an uninstall action).

Install and uninstall are performed by [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] under the **same M6 contract as everything else it touches** — idempotent, reversible, marker-managed where it merges into user-owned files, every action recorded in the machine-local manifest (`~/.agents/second-brain-manifest.json`); there is no second install model. The template portability invariant applies in full: overlay files and manifests are tracked template content, so targets use only portable placeholders (`<vault>`, `~`) and never an adopter-specific path. Manifest shape is enforced mechanically by `10_Agents/tools/brain/tests/test_harness_overlays.py`.

Shipped overlays: [[10_Agents/harnesses/cursor/wiring|Cursor]] (glob-scoped Inbox rule, `.cursorignore` privacy template) and [[10_Agents/harnesses/copilot/wiring|Copilot]] (`shipped-in-repo` catalogue of the `.github/` instructions shim + cloud-agent validate hook).

Facts are grounded in [[06_Resources/harness-primitives-research|the 2026-08-11 harness research]] (sources linked there; its Copilot section was re-verified in depth the same day for the P0 promotion). Harness surfaces move fast — **re-verify a wiring doc against its sources before relying on it**, and bump `updated:` when you do.
