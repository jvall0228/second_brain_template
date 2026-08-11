---
title: "Copilot P0 Promotion Plan"
tags:
  - type/plan
  - topic/software
  - audience/human
  - audience/agent
  - status/done
updated: 2026-08-11
---

# Copilot P0 Promotion Plan

Owner directive (2026-08-11): "Add copilot support. Do research on the copilot harness and implement." Copilot has been a P1 adapter since M6.3; this plan brings it to first-class support, grounded in [[06_Resources/copilot-harness-deep-dive|the same-day deep-dive research]]. Standards-first discipline holds: the adapter carries only what a cross-harness standard cannot. The plan was adversarially reviewed before implementation (see the review log at the end); all accepted findings are folded in below.

## Scope decision

"Full support" = the vault bootstraps, enforces its conventions, and exposes its skills on every Copilot surface an adopter can reach — VS Code agent mode, Copilot CLI, the cloud agent, code review, github.com Chat, and the IDE-embedded chats — with zero per-adopter setup where the repo itself can carry the config.

The template already covers the agent surfaces' entrypoint (`AGENTS.md` is native). What's missing, per the research: (a) the non-agent surfaces get no bootstrap at all, (b) the cloud agent escapes the vault's enforcement chain (git hooks likely bypassed, CI gated behind human approval), (c) the documented skills install for Copilot (symlinks) doesn't actually work, and (d) the wiring doc predates the hooks/skills/CLI facts and the "cloud agent" rename.

**Tier framing:** implementing the above is directed work. Recording it as a P0 row in [[00_Meta/prd]] §8.3 is this plan's *interpretation* of "add copilot support" (support that demonstrably works end-to-end = the P0 bar) — the PRD edit marks the promotion as owner-directed-in-substance but **pending owner confirmation of the tier itself**, and the final report surfaces it.

## Deliverables

### D1 — Real repo config under `.github/` (zero-setup; outside the validated corpus)

`brain`'s corpus walk prunes dot-paths, so these ship as working files, not `.txt` examples — same pattern as the existing `.github/workflows/validate.yml`.

1. **`.github/copilot-instructions.md`** — thin bootstrap pointer (read AGENTS.md, Inbox-first, frontmatter contract, validate command, and: after adding/deleting notes, regenerate `10_Agents/tools/brain/vault-index.json` with `brain index` and commit it). Reaches github.com Chat, Eclipse, Visual Studio, JetBrains — surfaces `AGENTS.md` cannot reach. Costs a few lines of duplication on surfaces that read both (instructions combine). Replaces `10_Agents/harnesses/copilot/copilot-instructions-example.txt`, which is deleted.
2. **`.github/hooks/vault-validate.json`** — GitHub-schema agent hook, `agentStop` event → runs `.github/scripts/agent-stop-validate.sh`, with explicit `timeoutSec: 120`. Effective in the **cloud agent** (config read from the default branch — true once merged); in local CLI sessions the script allows immediately (see D1.3), so the CLI's enforcement remains `.githooks/pre-commit`.
3. **`.github/scripts/agent-stop-validate.sh`** — executable bash stub whose only job is to `exec` an embedded python3 program (heredoc), locating `brain.py` relative to `$0` (no `cd`; brain derives the vault root from its own path). Behavior:
   - **Escape hatch:** exit-allow immediately if `SECOND_BRAIN_HOOK_DISABLE=1`.
   - **Local sessions** (`GITHUB_ACTIONS` unset): emit `{"decision": "allow"}` without running validate — a half-edited human note is normal local state; pre-commit is the local gate.
   - **Cloud sessions** (`GITHUB_ACTIONS` set — an inference from the Actions-powered environment; if unset there, the hook fails open to the CI backstop): run `brain validate --check-index --json`; exit 0/2 → allow; exit 1 → `{"decision": "block", "reason": ...}` where the reason lists the first ~10 errors plus the exact fix commands (`brain validate` to see all; `brain index` + commit the refreshed index for staleness).
   - **Loop guard (review blocker):** persist a count keyed by the sha256 of the error set in the sandbox temp dir; after 2 consecutive blocks on the same error set, emit allow (with the errors in the reason text as a warning) — CI remains the backstop. The sandbox is ephemeral, so state self-cleans.
   - Never reads stdin (the agentStop payload isn't needed), so a bare terminal run cannot hang; python emits all JSON (`json.dumps` neutralizes any note text embedded in validate output).
   - Known limits, documented in wiring: `--check-index` sees only git-tracked files, so a note the agent created but never locally tracked can leave the pushed index stale undetected (mitigated by the instructions-file rule in D1.1; caught by CI once approved); Windows cloud runners are unverified (bash-only hook → fail-open); `agentStop` firing timing in interactive CLI sessions is an inference from the event name, not documented.

### D2 — Adapter rewrite: `10_Agents/harnesses/copilot/wiring.md`

P0-depth rewrite. Facts trace to the deep-dive note, or — for topics it did not re-verify (content exclusion, gh-aw substance) — to the M6 research note, cited as such:

- **Entrypoint per surface**: agent surfaces read `AGENTS.md` natively; the shipped `.github/copilot-instructions.md` covers github.com Chat/Eclipse/VS/JetBrains; CLI expands `@`-includes in CLAUDE.md/AGENTS.md (and dedupes); code review reads `AGENTS.md` too. "Cloud agent" terminology throughout.
- **Skills**: in-repo, agents reach the skills library as plain repo content via the AGENTS.md bootstrap (the vault intentionally ships no `.agents/skills/` — in-repo symlinks were retired at §8.2, and copilot-cli#1021 says symlinked skills fail anyway). User scope: register the real dir with `copilot skill add <vault>/10_Agents/skills` (CLI; remove via `copilot skill remove` / `/skills remove`; where it persists the registration is undocumented), or **copy** skill folders into `~/.copilot/skills/` (documented personal path; copies, not symlinks) — `chat.agentSkillsLocations` is documented for *project* locations only, so its user-scope use is marked unverified. Note the nine built-in CLI skill names and the superset-frontmatter tolerance status.
- **Enforcement chain**: local git pre-commit (unchanged, also the CLI-session gate) → the shipped `agentStop` hook as the **cloud agent's** in-session layer (default-branch requirement; loop guard; fail-open on timeout; escape hatch; tracked-files blind spot) → CI backstop, including the **"Approve and run workflows" gate** and the repo setting that disables it — an owner-action item, not a repo file. General hooks note: `preToolUse` decisions are where `ask` is downgraded to `deny` on the cloud agent; `disableAllHooks` cross-scope semantics are unverified (hence the script's own env-var escape hatch).
- **Invoking brain**: `--allow-tool='shell(python3 10_Agents/tools/brain/brain.py)'` exact-match semantics vs `shell(python3:*)`; saved approvals in `permissions-config.json`; deny-beats-allow; cloud agent runs it offline (firewall-irrelevant).
- **User scope (onboard-harness)**: marker block goes in `~/.copilot/copilot-instructions.md` as **plain-text pointer** (absolute/`~/` `@`-refs are not loaded); skills via `copilot skill add` or copies, not symlinks.
- **Harness-specific notes**: MCP per surface (repo-settings JSON not committable; `~/.copilot/mcp-config.json`; `.vscode/mcp.json`); Agents secrets (+ `COPILOT_MCP_` prefix; credentials never in the repo, PRD §16.2); egress firewall default-on; automation (`copilot -p`, `gh agent-task`, REST API preview, gh-aw scheduled workflows); VS Code reads `.claude/settings.json` hooks but **ignores matchers** (the Claude Code adapter's PostToolUse example would fire on every tool call); VS Code camelCase-event acceptance unverified; content exclusion still org-managed (M6 research; PRD §21 unchanged).

### D3 — onboard-harness correction (`10_Agents/skills/onboard-harness/SKILL.md`)

The install algorithm's step 1 claims the `~/.agents/skills/` symlinks cover Copilot — corrected: Copilot is dropped from the symlink-covered list and gets a per-wiring-doc step — register the real skills directory (`copilot skill add`, reversible with `copilot skill remove`) or copy into `~/.copilot/skills/` with the skill's existing copy+hash drift mechanism. The manifest records the registration/copies; uninstall runs the remove command / deletes recorded copies. Canonical note; edited as directed implementation work under the owner's directive.

### D4 — Promotion + docs closeout

- **PRD** (canonical):
  - §8.3: Copilot row → P0, entrypoint column updated; the P0 tier bullet's harness list gains Copilot, "all five rows" → "all six rows", plus a dated promotion note framed as pending owner confirmation (per Scope decision above).
  - §9.3: one clause sanctioning root-scope shipped adapter files where zero-setup requires them (CLAUDE.md is the §8.2 precedent), noting dot-paths sit outside the note corpus.
  - §18: bullet recording the Copilot `agentStop` hook as a shipped enforcement layer (cloud agent; approval-gate caveat).
- **`10_Agents/skills/recommended-automations/SKILL.md`** (canonical): move Copilot out of the "no built-in scheduler" bucket — gh-aw scheduled workflows / `gh agent-task` for cloud flows; cron + `copilot -p` locally.
- **`10_Agents/harnesses/README.md`**: Copilot row → P0 tier with updated summary; grounding sentence notes Copilot facts now live in the deep-dive note.
- **`06_Resources/harness-primitives-research.md`**: one-line supersession pointer at the top of its Copilot section (the [[07_Archives/inbox/2026-08-11-m5-m7-implementation-plan|M5–M7 plan]]'s Copilot line stays as-is — executed history).
- **`00_Meta/changelog.md`**: new entry "Copilot Promoted to P0".
- No `00_Meta/status.md` change (milestone table; this is post-milestone work). No brain.py/spec/test changes (no `.md` semantics touched).
- Implementation detail: run `python3 10_Agents/tools/brain/brain.py index` explicitly before committing (not relying on the pre-commit hook as a side effect), then `validate`.

## Explicit non-goals

- `copilot-setup-steps.yml` — nothing to install; stdlib-only was the M5 design goal.
- `.github/instructions/*.instructions.md` — `AGENTS.md` already reaches every agent surface path-specific files reach; document the mechanism only.
- Prompt files, custom agents, committed MCP config, plugin manifest — legacy/polish/out-of-scope (vault MCP permanently out of scope, PRD §19).
- The privacy/ignore policy stays open (PRD §21) — Copilot's content exclusion is org-managed either way.

## Acceptance criteria

1. `python3 10_Agents/tools/brain/brain.py validate` exits 0 or 2 (no new errors); unit tests pass; the index is regenerated explicitly and byte-stable.
2. Hook script tests, run locally: (a) bare run on a clean tree → allow, no hang (stdin never read); (b) `GITHUB_ACTIONS=1` + seeded frontmatter error → block with the validate output in `reason`; (c) same seeded error twice more → third run allows (loop guard); (d) `SECOND_BRAIN_HOOK_DISABLE=1` → allow instantly; (e) all emitted JSON parses. Seeded state reverted afterward.
3. `.github/copilot-instructions.md` exists; the old example file is gone and nothing references it.
4. Wiring doc facts trace to the deep-dive note or (cited) the M6 research note; unverified items are marked as such, not asserted.
5. PRD, recommended-automations, harnesses README, changelog, and onboard-harness all consistent; commit + push to the designated branch.

## Adversarial review log (2026-08-11)

Four-lens workflow review (research fidelity, scope/standards-first, vault mechanics, failure modes) before implementation. Accepted and folded in: **1 blocker** — no repeat-block guard on the `agentStop` hook (fixed: consecutive-block counter + allow-after-2); **should-fixes** — local-session blocking would fight human mid-edits (fixed: cloud-only blocking), `disableAllHooks` scope unverified (fixed: script-level env escape hatch + hedged wiring), P0 promotion framed as pre-approved (fixed: pending-confirmation framing), PRD §18/§9.3 and the P0 bullet's list/row-count under-scoped (fixed: added to D4), canonical recommended-automations scheduler claim contradicted by research (fixed: added to D4), `copilot skill add` reversibility undocumented (fixed: `copilot skill remove` + unverified-storage note), Windows-CLI hook gap (resolved by cloud-only design; noted), CLI firing-timing asserted as fact (fixed: labeled inference), criterion 4 unsatisfiable as written (fixed: widened to cited M6-note facts); **nits** — `ask`→`deny` mis-scoped to agentStop (moved), `chat.agentSkillsLocations` user-scope unverified (hedged; copy path preferred), `type/log`→`type/plan` retag, stdin-hang risk in acceptance test (fixed: stdin never read), supersession pointer for the old research note (added), explicit `brain index` step (added), explicit `timeoutSec` (added), no-`cd` script (adopted). Rejected: none.
