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

Per-harness adapters for the support tiers in [PRD](../../00_Meta/PRD.md) §8.3. **Standards-first:** the entrypoint (`AGENTS.md`), canonical skills in `10_Agents/skills/`, generated repository discovery adapters, and the `brain` CLI carry portable behavior. Each directory here carries **only what a cross-harness standard cannot**: exact config paths, import syntax, caps, and trust gates.

Every adapter ships a `wiring.md` (entrypoint loading, skill discovery paths, hook installation, how the harness invokes `brain`, harness-specific caveats) and reference config files to copy or merge. The [onboard-harness](../skills/onboard-harness/SKILL.md) skill verifies repository scope by default and gates optional user-global changes behind an exact preview and explicit apply approval.

## Project skill compatibility

`10_Agents/tools/skill_adapters/gen_skill_adapters.py` deterministically
generates text adapters from canonical skill `name` and `description`; adapters
point back to the canonical `SKILL.md` and never copy its workflow body or use
symlinks. This table records **documented and repository-contract expectations as of
2026-08-11**, not seven live host executions. The dated sources in each wiring
document are the authority for host behavior. Where the Codex CLI is installed,
the automated clean-clone smoke additionally inspects Codex's actual prompt
input and proves it discovers the checked-in `.agents/skills/` adapters.

| Harness | Documented project discovery | Contract expectation | Caveat / evidence |
|---|---|---|---|
| Claude Code | `.claude/skills/` | Checked-in adapters and `CLAUDE.md` import are present | Documented surface; see dated wiring sources |
| Codex | `.agents/skills/` | Checked-in adapters and native `AGENTS.md` are present | Trusted project required; automated CLI smoke when installed |
| opencode | `.agents/skills/`, `.claude/skills/` | Checked-in adapters and `AGENTS.md` are present | Project config may make bootstrap ordering more explicit; see wiring sources |
| Pi | `.agents/skills/` | Checked-in adapters and `AGENTS.md` are present | Run `/trust`; headless runs silently omit untrusted project skills |
| Cursor | `.agents/skills/`, `.claude/skills/` | Checked-in adapters and `AGENTS.md` are present | Workspace trust still applies; see wiring sources |
| Copilot | `.agents/skills/`, `.claude/skills/` | Supported project adapter surfaces are checked in | Optional user scope uses copy/CLI registration; do not use symlinks |
| Muse Code | `.agents/skills/` | Checked-in adapters and `AGENTS.md` are present on the documented surface | Volatile P1 surface; re-verify before relying on it |

| Adapter | Tier | Wiring |
|---------|------|--------|
| [Claude Code](claude-code/wiring.md) | P0 | needs the `CLAUDE.md` import; scans `.claude/skills/` only |
| [Codex](codex/wiring.md) | P0 | native `AGENTS.md`; 32 KiB project-doc cap; trusted-project config |
| [opencode](opencode/wiring.md) | P0 | native `AGENTS.md`; `instructions[]` makes bootstrap deterministic |
| [Pi](pi/wiring.md) | P0 | native `AGENTS.md`; trust gate; no MCP (extensions instead) |
| [Copilot](copilot/wiring.md) | P0 | native `AGENTS.md` on agent surfaces; shipped `.github/` shim + cloud-agent validate hook |
| [Cursor](cursor/wiring.md) | P1 | native `AGENTS.md`; `.mdc` rules; only harness with a real ignore file |
| [Muse Code](muse-code/wiring.md) | P1 | volatile (launched 2026-08-05); user-scope config only |

## Overlays

An adapter may additionally ship an **overlay**: installable harness-native primitives under `10_Agents/harnesses/<name>/overlay/` — e.g. Cursor glob-scoped `.mdc` rules and its `.cursorignore` template, or Copilot's instructions shim and cloud-agent hook. Overlays are governed by the **standards-first rule** ([PRD](../../00_Meta/PRD.md) §8.3, design principles §9.3): an overlay carries **only what a cross-harness standard cannot express**. If `AGENTS.md`, the Agent Skills format, or the `brain` CLI can do the job, the overlay must not duplicate it — most adapters correctly ship **no** `overlay/` directory, and that absence is the expected default, not a gap.

Every overlay contains a `manifest.json` describing what it installs, where, and how to reverse it:

- **Top level:** `overlay_version` (schema version, currently `1`), `harness` (must equal the adapter directory name), `description`, `standards_gap` (the explicit justification — which capability no cross-harness standard reaches), and `artifacts`.
- **Per artifact:** a unique `id`, `kind`, `source` + `source_root` (`overlay` = payload file inside `overlay/`; `repo` = working config already shipped elsewhere in the repository, e.g. Copilot's `.github/` files), an `install` object (`method`, portable `target`, `scope`), and a `reverse` object (`method`, optional `condition`).
- **Install methods:** `copy` (place the payload at the target; foreign files are never overwritten), `marker-block` (merge a marker-delimited block into a user-owned config file), `generate` (produce the target by running the recorded `generator` command, seeded from the payload template), `shipped-in-repo` (the artifact is tracked repo config present in every clone — nothing to install).
- **Reverse methods:** `delete`, `remove-marker-block`, `none` (only valid for `shipped-in-repo` — removing tracked config is a repo change, not an uninstall action).

Install and uninstall are performed by [onboard-harness](../skills/onboard-harness/SKILL.md) under the **same M6 contract as everything else it touches** — idempotent, reversible, marker-managed where it merges into user-owned files, every action recorded in the machine-local manifest (`~/.agents/second-brain-manifest.json`); there is no second install model. The template portability invariant applies in full: overlay files and manifests are tracked template content, so targets use only portable placeholders (`<vault>`, `~`) and never an adopter-specific path. Manifest shape is enforced mechanically by `10_Agents/tools/brain/tests/test_harness_overlays.py`.

Shipped overlays: [Cursor](cursor/wiring.md) (glob-scoped Inbox rule, `.cursorignore` privacy template) and [Copilot](copilot/wiring.md) (`shipped-in-repo` catalogue of the `.github/` instructions shim + cloud-agent validate hook).

Facts are grounded in [the 2026-08-11 harness research](../../06_Resources/harness-primitives-research.md) (sources linked there; its Copilot section was re-verified in depth the same day for the P0 promotion). Harness surfaces move fast — **re-verify a wiring doc against its sources before relying on it**, and bump `updated:` when you do.
