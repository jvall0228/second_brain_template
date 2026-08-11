---
title: "Copilot P0 Promotion Plan"
tags:
  - type/log
  - topic/software
  - audience/human
  - audience/agent
  - workflow/draft
updated: 2026-08-11
---

# Copilot P0 Promotion Plan

Owner directive (2026-08-11): "Add copilot support. Do research on the copilot harness and implement." Copilot has been a P1 adapter since M6.3; this plan promotes it to first-class **P0** support, grounded in [[02_Inbox/2026-08-11-copilot-harness-deep-dive|the same-day deep-dive research]]. Standards-first discipline holds: the adapter carries only what a cross-harness standard cannot.

## Scope decision

"Full support" = the vault bootstraps, enforces its conventions, and exposes its skills on every Copilot surface an adopter can reach — VS Code agent mode, Copilot CLI, the cloud agent, code review, github.com Chat, and the IDE-embedded chats — with zero per-adopter setup where the repo itself can carry the config.

The template already covers the agent surfaces' entrypoint (`AGENTS.md` is native). What's missing, per the research: (a) the non-agent surfaces get no bootstrap at all, (b) the cloud agent escapes the vault's enforcement chain (git hooks likely bypassed, CI gated behind human approval), (c) the documented skills install for Copilot (symlinks) doesn't actually work, and (d) the wiring doc predates the hooks/skills/CLI facts and the "cloud agent" rename.

## Deliverables

### D1 — Real repo config under `.github/` (zero-setup; outside the validated corpus)

`brain`'s corpus walk prunes dot-paths, so these ship as working files, not `.txt` examples — same pattern as the existing `.github/workflows/validate.yml`.

1. **`.github/copilot-instructions.md`** — thin bootstrap pointer (read AGENTS.md, Inbox-first, frontmatter contract, validate command). Reaches github.com Chat, Eclipse, Visual Studio, JetBrains — surfaces `AGENTS.md` cannot reach. Costs a few lines of duplication on surfaces that read both (instructions combine). Replaces `10_Agents/harnesses/copilot/copilot-instructions-example.txt`, which is deleted.
2. **`.github/hooks/vault-validate.json`** — GitHub-schema agent hook, `agentStop` event → runs `.github/scripts/agent-stop-validate.sh`. On `brain validate` exit 1 it returns `{"decision": "block", "reason": <error output + fix instructions>}`, forcing the agent to repair conventions before finishing; exit 0/2 → allow. Serves the cloud agent (needs default branch — true once merged) and the Copilot CLI from the same file.
3. **`.github/scripts/agent-stop-validate.sh`** — executable bash wrapper (shebang, `cd` to repo root from `$0`); delegates to python3 for JSON emission. Plain `validate` locally; adds `--check-index` only when `GITHUB_ACTIONS` is set (best-effort cloud detection — locally a stale index between commits is normal and the pre-commit hook regenerates it, so `--check-index` at every local agent stop would false-positive). Reason text is bounded (~2 KB tail) and tells the agent exactly what to run. Hook errors degrade to warnings for `agentStop` per the docs — graceful when python3 is missing.

### D2 — Adapter rewrite: `10_Agents/harnesses/copilot/wiring.md`

P0-depth rewrite, citing the deep-dive note:

- **Entrypoint per surface**: agent surfaces read `AGENTS.md` natively; the shipped `.github/copilot-instructions.md` covers github.com Chat/Eclipse/VS/JetBrains; CLI expands `@`-includes in CLAUDE.md/AGENTS.md (and dedupes); code review reads `AGENTS.md` too. "Cloud agent" terminology throughout.
- **Skills**: in-repo, agents reach the skills library as plain repo content via the AGENTS.md bootstrap (the vault intentionally ships no `.agents/skills/` — in-repo symlinks were retired at §8.2, and copilot-cli#1021 says symlinked skills fail anyway). User scope: register the real dir — `copilot skill add <vault>/10_Agents/skills` (CLI) / `chat.agentSkillsLocations` (VS Code); note the nine built-in CLI skill names and the superset-frontmatter tolerance status.
- **Enforcement chain**: local git pre-commit (unchanged) → the shipped `agentStop` hook (cloud + CLI; default-branch requirement; fail-open on timeout; `ask`→`deny` downgrade note) → CI backstop, including the **"Approve and run workflows" gate** and the repo setting that disables it — an owner-action item, not a repo file.
- **Invoking brain**: `--allow-tool='shell(python3 10_Agents/tools/brain/brain.py)'` exact-match semantics vs `shell(python3:*)`; saved approvals in `permissions-config.json`; deny-beats-allow; cloud agent runs it offline (firewall-irrelevant).
- **User scope (onboard-harness)**: marker block goes in `~/.copilot/copilot-instructions.md` as **plain-text pointer** (absolute/`~/` `@`-refs are not loaded); skills via `copilot skill add`, not symlinks.
- **Harness-specific notes**: MCP per surface (repo-settings JSON not committable; `~/.copilot/mcp-config.json`; `.vscode/mcp.json`); Agents secrets (+ `COPILOT_MCP_` prefix; credentials never in the repo, PRD §16.2); egress firewall default-on; automation (`copilot -p`, `gh agent-task`, REST API preview, gh-aw); VS Code reads `.claude/settings.json` hooks but **ignores matchers** (the Claude Code adapter's PostToolUse example would fire on every tool call); content exclusion still org-managed (PRD §21 unchanged); VS Code camelCase-event caveat.

### D3 — onboard-harness correction (`10_Agents/skills/onboard-harness/SKILL.md`)

The install algorithm's step 1 claims the `~/.agents/skills/` symlinks cover Copilot — corrected: Copilot is dropped from the symlink-covered list and gets a per-wiring-doc registration step (real-directory `copilot skill add` / `chat.agentSkillsLocations`, recorded in the manifest as a merged-config entry). Canonical note; the owner's "add copilot support" directive is the approval.

### D4 — Promotion + docs

- **PRD §8.3** (canonical): Copilot row → P0, entrypoint column updated ("native `AGENTS.md` on agent surfaces + shipped `.github/copilot-instructions.md` shim"); tier-meaning bullet gains the promotion note (owner-directed, 2026-08-11, post-M6).
- **`10_Agents/harnesses/README.md`**: Copilot row → P0 tier with updated summary; intro sentence unchanged.
- **`00_Meta/changelog.md`**: new entry "Copilot Promoted to P0".
- No `00_Meta/status.md` change (milestone table; this is post-milestone work). No brain.py/spec/test changes (no `.md` semantics touched).

## Explicit non-goals

- `copilot-setup-steps.yml` — nothing to install; stdlib-only was the M5 design goal.
- `.github/instructions/*.instructions.md` — `AGENTS.md` already reaches every agent surface path-specific files reach; document the mechanism only.
- Prompt files, custom agents, committed MCP config, plugin manifest — legacy/polish/out-of-scope (vault MCP permanently out of scope, PRD §19).
- The privacy/ignore policy stays open (PRD §21) — Copilot's content exclusion is org-managed either way.

## Acceptance criteria

1. `python3 10_Agents/tools/brain/brain.py validate` exits 0 or 2 (no new errors); unit tests pass; index regenerates deterministically via the pre-commit hook.
2. The hook script is executable, emits valid JSON for the allow and block paths, and `bash .github/scripts/agent-stop-validate.sh` run locally on a clean tree prints an allow decision. A seeded frontmatter error produces a block decision with the validate output in `reason` (then reverted).
3. `.github/copilot-instructions.md` exists at root scope; the old example file is gone and nothing references it.
4. Wiring doc facts all trace to the deep-dive note; unverified items are marked as such, not asserted.
5. PRD table, harnesses README, changelog, and onboard-harness all consistent; commit + push to the designated branch.

## Risks / notes for review

- **Hook casing**: camelCase events per GitHub schema; VS Code may not fire them (unverified) — acceptable, VS Code-local users have the git hook; noted in wiring.
- **`GITHUB_ACTIONS` in the cloud-agent session** is an inference (Actions-powered env); `--check-index` there is best-effort hardening, plain `validate` is the guaranteed layer.
- **agentStop in interactive CLI**: fires at every turn end; validate is ~1–2 s and only blocks on real errors — acceptable, and `disableAllHooks` is the user escape hatch.
- The M6 research note's Copilot section stays as-is (historical Inbox capture; superseded pointer lives in the new note).
