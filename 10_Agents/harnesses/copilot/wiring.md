---
title: "Copilot Wiring"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-08-11
expires: 2026-11-11
---

# Copilot Wiring

Facts verified 2026-08-11 against [docs.github.com/copilot](https://docs.github.com/copilot) and the VS Code docs — see [[06_Resources/harness-copilot|the harness research's Copilot section]] (sources linked there; it absorbed the same-day deep-dive). Re-verify before relying on paths. GitHub now brands the async agent the **Copilot cloud agent**.

## Entrypoint loading

Copilot's **agent surfaces** read `AGENTS.md` natively — no setup:

- **Cloud agent** and **Copilot CLI**: `AGENTS.md` (nearest in tree wins) plus `CLAUDE.md`/`GEMINI.md`; the CLI even expands `@`-includes inside `AGENTS.md`/`CLAUDE.md` (so the vault's one-line `CLAUDE.md` works there) and dedupes identical instruction files.
- **Code review**: reads `AGENTS.md` (only — not CLAUDE/GEMINI), so vault rules reach review comments too.
- **VS Code agent mode**: `AGENTS.md` via `chat.useAgentsMdFile`.

Surfaces that **never read `AGENTS.md`** — github.com Copilot Chat, Eclipse, Visual Studio, JetBrains chat — get the bootstrap from the shipped **`.github/copilot-instructions.md`** (a thin pointer to the bootstrap sequence, plus the index-regeneration rule). Instruction files **combine** on surfaces that read several; no file suppresses another, so the pointer costs a few duplicated lines at most. Keep `AGENTS.md` the single source — the pointer must stay thin.

## Skills

Copilot supports Agent Skills on the cloud agent, code review, the CLI, the Copilot app, and agent mode in VS Code/JetBrains. Project discovery paths are `.github/skills/`, `.claude/skills/`, `.agents/skills/` — the vault deliberately ships **none** of these (in-repo symlinks were retired at PRD §8.2, and [copilot-cli#1021](https://github.com/github/copilot-cli/issues/1021) reports symlinked skills are ignored anyway). In-repo, agents reach `10_Agents/skills/` as plain content via the `AGENTS.md` bootstrap.

User scope (what `onboard-harness` does for Copilot — **not** the `~/.agents/skills/` symlinks, which the CLI does not reliably discover):

- **CLI:** the first registered second-brain vault that provides the global skill set becomes the manifest-recorded provider; register that real directory with `copilot skill add <vault>/10_Agents/skills` (in-session: `/skills add`). Additional registered vaults with the same skill names become consumers rather than adding duplicate directories. Compare recorded hashes; if another vault's copies differ, report managed version drift and keep the current provider until the owner explicitly chooses a global version. Provider removal follows the generic `onboard-harness` transfer/preflight rule. Reversible with `copilot skill remove` / `/skills remove`; where the registration persists is undocumented.
- **VS Code / fallback:** **copy** skill folders into `~/.copilot/skills/` (a documented personal path; copies, not symlinks) and treat those copies as shared manifest-owned resources with provider/consumer references and content hashes. Do not overwrite them merely because another vault is onboarded. `chat.agentSkillsLocations` is documented for *project* locations; treating it as user-scope config is unverified.

Caveats: the CLI ships nine built-in skills (`analyze`, `design`, `document`, `fix`, `investigate`, `research`, `security`, `test`, `verify`) that can override same-named user skills — none of the vault's twenty canonical skills collide; keep it that way. The vault's superset SKILL.md frontmatter (`title`/`tags`/`updated` beyond `name`/`description`) is tolerated in practice (GitHub's own `gh skill install` writes extra frontmatter) but officially undefined — the spec's `metadata:` map is the sanctioned home if a surface ever objects.

## Enforcement chain

1. **Local sessions (CLI, VS Code):** `git config core.hooksPath .githooks` in the clone — the pre-commit hook regenerates the index and blocks bad commits, exactly as everywhere else.
2. **Cloud agent:** its commits are signed and authored by Copilot, so assume repo git hooks do **not** fire (inference — undocumented), and its PRs don't run Actions until someone clicks **"Approve and run workflows"** (default; a repo setting under Settings → Copilot → cloud agent can disable that gate — an owner action, not a repo file). The shipped agent hook closes this gap: `.github/hooks/vault-validate.json` (`agentStop`, `timeoutSec: 120`) runs `.github/scripts/agent-stop-validate.sh`, which in the cloud environment runs `brain validate --check-index --json` and **blocks the agent from finishing** while errors exist, with the findings and fix commands in the block reason. Design points:
   - Cloud-only: local sessions always allow (a half-edited note is normal working-tree state; pre-commit is the local gate). Cloud detection is `GITHUB_ACTIONS` (inferred from the Actions-powered environment; if unset there, the hook fails open to CI).
   - Repeat-block guard: after two blocks on the same error set it allows and defers to CI, so an unfixable error can't loop a session into the 59-minute cap.
   - Escape hatch: `SECOND_BRAIN_HOOK_DISABLE=1` (the cross-scope semantics of the schema's `disableAllHooks` are unverified).
   - The cloud agent only reads hook config from the **default branch**; timeouts fail open; `--check-index` sees git-tracked files only, so an untracked new note can leave the pushed index stale — the instructions file tells agents to run `brain index` and commit the result, and CI catches the rest.
3. **CI backstop:** `.github/workflows/validate.yml`, unchanged — subject to the approval gate above on cloud-agent PRs.

General hook facts: config schema `{"version": 1, "hooks": {...}}`, camelCase events (`sessionStart` … `agentStop`), `bash`/`powershell`/`command` fields (cloud agent honors `bash`/`command` only; Windows runners unverified → fail-open); `preToolUse` hooks can return `permissionDecision: allow|deny|ask`, and the cloud agent downgrades `ask` to `deny`; whether VS Code accepts camelCase event names in `.github/hooks/*.json` is unverified (its docs show PascalCase) — VS Code users are covered by the git hook regardless.

## Invoking brain

```
python3 10_Agents/tools/brain/brain.py <command> --json
```

CLI pre-approval: `--allow-tool='shell(python3 10_Agents/tools/brain/brain.py)'` matches the **exact** bare command only (argument matching is undocumented); `--allow-tool='shell(python3:*)'` covers all python3 invocations (the colon wildcard is shell's only wildcard). Interactive approvals persist per-directory in `~/.copilot/permissions-config.json`. Deny rules always beat allow rules, even under `--allow-all`/`--yolo`. The cloud agent runs brain fine offline — the egress firewall (default-on) only affects network access, which brain never uses.

**Semantic search** ([[10_Agents/tools/brain/spec|spec]] §18): `python3 10_Agents/tools/brain/brain.py search --semantic "question" --json` returns relevance-ranked notes once the gitignored embeddings sidecar is populated, and degrades to keyword search (exit 0) on a vectorless vault. This harness can supply the vectors itself: compute embeddings with its model and pipe them in via `python3 10_Agents/tools/brain/brain.py embed --stdin-json`, then pass the embedded query at search time with `--query-vector` on stdin. Credentials for any external embedding API stay outside the vault (PRD §16.2).

## Harness-specific notes

- **MCP is per-surface:** `.vscode/mcp.json` (VS Code workspace), `~/.copilot/mcp-config.json` (CLI, `/mcp add`), and the cloud agent's JSON config lives in **repository settings on github.com** (shared with code review — cannot be committed as a file). The vault ships no servers (vault MCP is permanently out of scope, PRD §19); M7 external-source servers register per-surface.
- **Secrets:** the cloud agent has a dedicated **Agents** secrets/variables store (Settings → Secrets and variables → Agents), exposed as env vars; names prefixed `COPILOT_MCP_` go only to MCP servers. Credentials never enter the repo (PRD §16.2).
- **Automation:** headless `copilot -p "<prompt>"`; cloud tasks via `gh agent-task` (gh ≥ 2.80), the Agent tasks REST API (public preview, user-to-server tokens only), or scheduled [gh-aw](https://github.github.com/gh-aw/reference/copilot-cloud-agent/) workflows — see [[10_Agents/skills/recommended-automations/SKILL|recommended-automations]].
- **VS Code reads Claude Code hook config** (`.claude/settings.json`[`.local`]) but **ignores matchers** — the Claude Code adapter's PostToolUse validate example would fire on *every* tool call under VS Code Copilot. Fine at ~1–2 s per validate, but know it's there.
- **Content-exclusion is org-managed** (and ignored by the CLI/agent surfaces — M6 research) — no repo-level privacy mechanism; feeds the open policy decision (PRD §21).
- Glob-scoped instruction files (`.github/instructions/*.instructions.md`, `applyTo` frontmatter) exist but add nothing here: `AGENTS.md` already reaches every agent surface they reach. Prompt files and custom agents likewise are not shipped — skills are the vault's portable unit.

## User scope (onboard-harness)

- **Memory:** create or reconcile `~/.agents/second-brain/AGENTS.md`, then append a marker-delimited **plain-text pointer** to that stable shared registration in `~/.copilot/copilot-instructions.md`. Do not put the adopter's vault path in Copilot's file. Because import behavior for external home-directory paths varies by Copilot surface and documentation, baseline onboarding does not rely on `@` here; the instruction says to read `~/.agents/second-brain/AGENTS.md` when owner-specific context materially helps. The shared registration contains the runtime-resolved vault path and routes onward to the vault's `AGENTS.md`.
- **Skills:** use one manifest-owned global provider at a time: `copilot skill add` that provider's real directory, or maintain the shared copies in `~/.copilot/skills/` (see Skills above). Additional vaults are consumers, not duplicate registrations. Record provider, consumers, and hashes in the manifest; uninstall/removal follows the generic shared-resource preflight and provider-transfer rules.

## Reference config

None to copy — the working config ships in the repo itself: `.github/copilot-instructions.md` (IDE/web bootstrap shim), `.github/hooks/vault-validate.json` + `.github/scripts/agent-stop-validate.sh` (cloud-agent enforcement). All three sit outside the note corpus (dot-paths are pruned), so `brain` never validates or indexes them. They are catalogued as `shipped-in-repo` artifacts in `overlay/manifest.json` — the Copilot **overlay** (see the Overlays section of [[10_Agents/harnesses/README]]): present in every clone, so [[10_Agents/skills/onboard-harness/SKILL|onboard-harness]] installs and removes nothing for them.
