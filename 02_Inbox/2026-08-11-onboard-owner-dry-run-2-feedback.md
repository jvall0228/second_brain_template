---
title: "Onboard-owner template feedback — 2026-08-11 dry run 2"
tags:
  - audience/agent
  - audience/human
  - type/note
  - topic/onboarding
  - topic/template
  - workflow/draft
updated: 2026-08-11
author: claude-code
session: onboarding-2026-08-11
---

# Onboard-owner template feedback — 2026-08-11 dry run 2

Owner feedback from a second live [[10_Agents/skills/onboard-owner/SKILL|onboard-owner]] dry run (Claude Code, vault `second_brain_test`, cloned from the public `second_brain_template` repo). Capture for template / skill updates — not owner profile content. A prior dry run's feedback already landed as [[07_Archives/inbox/2026-08-11-onboard-owner-template-feedback|adaptive-interview requirements]]; this run surfaced gaps beyond that fix.

## Feedback

1. **The "ask + recommend" default didn't reach stage 1.** The skill's Interaction defaults say every owner-facing question pairs with 2–4 grounded options "across every stage," but stage 1's welcome question ("what are you hoping this helps with?") has no options of its own and reads as the genuinely-open-ended exception. In this run that produced a bare open question, a "dunno" answer, and a redo. Fix: give stage 1 explicit generic starter options (work / personal / exploring / not sure) so the default actually applies from question one, not just from stage 2 onward.

2. **No safeguard before writing to the owner's real machine.** Stages 7–8 (onboard-harness core install + recommended components) write to real user-scope state — `~/.claude/CLAUDE.md`, `~/.agents/second-brain/`, `~/.agents/skills/` — with no distinction in the skill between a real adoption and a dry run. The skill should detect signals that this is a test/dry-run vault (e.g. directory name containing `test`, or an explicit owner statement) and default to *not* touching real user-dir config without an explicit, scoped confirmation — rather than relying on the live agent to notice and ask.
   - **Owner-suggested structural fix (preferred over a detection heuristic):** ship project-scope skill wiring *in the template itself* — e.g. `.claude/skills/<name>` (and each other supported harness's project-level equivalent) checked into the repo, symlinked or pointing at `10_Agents/skills/<name>`. Then skills (including `onboard-owner`) are discoverable the moment the vault is cloned, with zero install step and no writes outside the repo — a dry run never needs to touch real machine state at all. `onboard-harness` (stages 7–8) stops being "the way skills become available" and becomes purely the **global-scope extension**: it makes the vault's skills reachable from *other* project directories too (`~/.claude/skills/`, `~/.agents/`), so captures can happen outside this vault's own context. That's an unambiguous, deliberate opt-in step (the owner is explicitly asking for cross-project reach), not something onboarding needs to guess about or guard by default.

3. **No safeguard before pulling real personal data into a public-remote vault.** Stage 9 (agent-orientation / "connect their world") offers to pull real calendar/email data with no check on whether the vault's `git remote` points at a public repo (here, `second_brain_template` itself). The owner had to catch this and call it a failure that the agent needed to ask live rather than the skill refusing by default. Fix: `agent-orientation` (and `onboard-owner` stage 9's offer) should check the vault's remote before offering real-data connections, and hard-skip / hard-warn by default when the remote looks public or template-like (e.g. matches the upstream template's own repo, or is public on the host).

4. **Stage 10 cleanup doesn't account for cross-links between example content.** Deleting `04_Projects/example-project/` (offered and approved once a real project existed) broke four unrelated files that linked to it as a worked example: `00_Meta/INDEX.md`, `04_Projects/README.md`, `05_Areas/example-area/README.md`, and the sample weekly review `03_Journal/periodic/weekly/2025-W03-review.md`. The skill should either treat the example set as a linked bundle (offer to update/remove all cross-references together) or, at minimum, warn the agent to `brain validate` and fix fallout immediately after any example deletion — the current text only says "offer to remove them," not "and repair what links to them."

## Context from the run (for triage)

- Goal stated: personal life, though the owner opened with "dunno, my brother told me to do this" — genuinely undecided at first
- New to notes apps / Obsidian
- Preferences settled on: explanatory tone (don't assume prior knowledge), concise but not under-explained, ask + recommend as the default question pattern
- Vault intent: personal, work kept fully separate — role/company interview correctly skipped
- People map: skipped — no orientation inventory existed yet and git history had nothing usable; correctly deferred per the skill's own fallback
- Seed content: one real project captured (car theft → repair/reimbursement follow-up), no area surfaced
- First capture → triage: worked well end to end (car interest → filed into `01_Profile/IDENTITY.md` § Interests, Inbox copy cleared)
- Stages 7, 8, 9 all deferred per owner instruction (see items 2–3 above)
- Related skill: [[10_Agents/skills/onboard-owner/SKILL]]; also touches [[10_Agents/skills/onboard-harness/SKILL]] and [[10_Agents/skills/agent-orientation/SKILL]]

## Suggested triage

- Add explicit starter options to onboard-owner stage 1's welcome question
- Ship project-scope skill wiring in the template repo itself (per supported harness) so skills work zero-install on clone; re-scope onboard-harness to be purely the global/"everywhere" extension step, not the thing that makes skills available in the first place
- Add a public/template-remote check to agent-orientation (and onboard-owner stage 9) that hard-skips real account connections by default on such vaults
- Extend onboard-owner stage 10 to either bundle cross-linked example content for removal together, or explicitly require an immediate `brain validate` + fixup pass after any example deletion
