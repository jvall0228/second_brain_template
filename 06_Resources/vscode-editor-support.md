---
title: "VS Code as Alternative Editor: Requirements, Trust Policy, and Config"
tags:
  - audience/agent
  - audience/human
  - type/reference
  - topic/software
updated: 2026-08-11
expires: 2026-11-11
---

# VS Code as Alternative Editor: Requirements, Trust Policy, and Config

Owner-directed (2026-08-11): the vault spec supports **VS Code as an alternative editor** for when Obsidian is not available. This note records the requirements brainstorm, the extension **trust policy the owner set**, the online research behind the candidates, and the mapping from the shipped `.obsidian/` config to the shipped `.vscode/` config. The working config lives at `.vscode/settings.json` + `.vscode/extensions.json` (root-scope dot-path, outside the note corpus — the `.github/` / `CLAUDE.md` precedent from [PRD](../00_Meta/PRD.md) §9.3). Spec change: [PRD](../00_Meta/PRD.md) §6.5.

## Trust policy (owner decision, 2026-08-11)

**Only extensions published by first-party organization accounts (Microsoft, Anthropic, GitHub, and similar) may be recommended.** Community and personal-publisher extensions are excluded from `extensions.json` regardless of reputation. Preference order:

1. VS Code **built-in** capability (no extension at all)
2. **First-party org publishers** (`ms-vscode`, `anthropic`, `github`, …)
3. Everything else: documented here for reference, **never shipped**

Extensions must run locally, require no account for core function, and must not rewrite notes on save. Future agents must not add recommendations outside this policy without owner approval.

## Requirements (brainstormed, tiered)

**Tier 0 — built-ins, zero extensions (shipped via `settings.json`):**

1. Quick switcher (`Ctrl/Cmd+P`), global search, file explorer, outline, word count — native equivalents of the `switcher`, `global-search`, `file-explorer`, `outline`, `word-count` core plugins.
2. YAML frontmatter syntax highlighting (`properties` plugin) — native.
3. Markdown preview (`Ctrl/Cmd+Shift+V`) — native reading view.
4. Standard-markdown link validation and path autocompletion (`markdown.validate.enabled`, `markdown.suggest.paths.enabled`).
5. Pasted/dropped images auto-filed to `08_Assets/` (`markdown.copyFiles.destination`) — preserves the asset rule (PRD §16.1) with no extension.
6. **No write-behavior:** no format-on-save; Prettier in `unwantedRecommendations` (PRD §14 diffability).
7. Search hygiene: `vault-index.json` and `.obsidian/` excluded from workspace search.

**Tier 1 — first-party extensions (shipped via `extensions.json`):**

8. **HTML rendering** — Microsoft **Live Preview** (`ms-vscode.live-server`): embedded auto-refreshing browser panel for HTML files (exports, `08_Assets/` artifacts). Obsidian has no equivalent in our config (`webviewer` disabled).
9. **P0 harness companions** (PRD §8.3): **Claude Code** (`anthropic.claude-code`) and **Copilot** (`github.copilot`) — the two P0 harnesses with VS Code surfaces; wiring docs under `10_Agents/harnesses/`. With a harness attached, agent-mediated workflows (daily log via the [daily-log](../10_Agents/skills/daily-log/SKILL.md) skill, link queries via `brain`) partially compensate for the excluded community features below.

**Tier 2 — full Obsidian parity — evaluated and NOT shipped (fails trust policy):**

10. Backlinks panel, graph view, tag explorer, and daily-note command. Only community extensions provide the missing rich views (see research below). Canonical relative Markdown click-through, path completion, and validation are built in and shipped; the owner reviewed and declined the remaining extensions.

| Gap (Obsidian plugin) | Mitigation in VS Code |
|---|---|
| Relative Markdown navigation | Built-in click-through, path completion, and `markdown.validate`; `brain validate` adds fragment/encoding/case checks |
| Backlinks (`backlink`, `outgoing-link`) | `brain links --json`; workspace search for the target path |
| Graph (`graph`) | none (accepted) |
| Tag pane (`tag-pane`) | `brain tags`; workspace search for the tag string |
| Daily notes (`daily-notes`) | [daily-log](../10_Agents/skills/daily-log/SKILL.md) skill via an attached harness, or copy `09_Templates/template-daily-log.md` |
| Mermaid in preview | renders on GitHub and in Obsidian; not in VS Code preview (accepted) |
| Canvas, `bases` | Obsidian-proprietary; accepted (template ships neither) |

## Candidates evaluated (research, 2026-08-11)

| Candidate | Publisher type | Verdict under policy |
|---|---|---|
| Live Preview (`ms-vscode.live-server`) | Microsoft org | **Shipped** |
| Claude Code (`anthropic.claude-code`) | Anthropic org | **Shipped** |
| Copilot (`github.copilot`) | GitHub org | **Shipped** |
| Foam (`foam.foam-vscode`) | Community (MIT, 17.3k★, 133 contributors, ~268k installs, 5.0★) | Excluded — best-in-class for backlinks/graph/tags/daily notes, and a close Obsidian equivalent, but community-published with no org backing. Documented as the owner-optional upgrade if the policy is ever relaxed. |
| Markdown All in One (`yzhang`) | Personal (5M+ installs) | Excluded — personal publisher |
| markdownlint (`DavidAnson`) | Personal (author is a Microsoft engineer; publishes from a personal account) | Excluded — personal publisher; `brain validate` is the vault's real linter anyway |
| Markdown Mermaid (`bierner`) | Personal (author maintains VS Code's built-in markdown at Microsoft; personal account) | Excluded — personal publisher |
| Markdown Preview Enhanced (`shd101wyy`) | Personal | Excluded |
| Dendron | Community; imposes its own vault hierarchy | Excluded — structurally invasive regardless of trust |
| Markdown Memo, AS Notes | Community, smaller | Excluded |

Sources:

- [Foam (GitHub)](https://github.com/foambubble/foam) · [Foam on the Marketplace](https://marketplace.visualstudio.com/items?itemName=foam.foam-vscode)
- [Live Preview extension (Microsoft)](https://marketplace.visualstudio.com/items?itemName=ms-vscode.live-server)
- [XDA: Using VS Code instead of Obsidian for notes](https://www.xda-developers.com/tried-using-vs-code-obsidian-notes/)
- [Deep Notes: Integrating Obsidian with VS Code](https://deepaksood619.github.io/devops/ides/obsidian-in-vscode/)
- [Best Markdown Extensions for VS Code in 2026](https://www.merge-json-files.com/blog/best-markdown-extensions-for-vscode)
- [VS Code Markdown Guide 2026](https://allmarkdowntools.com/vscode-markdown)

## Shipped config: `.obsidian` → `.vscode` mapping

| Obsidian (enabled plugin) | VS Code equivalent | Tier |
|---|---|---|
| `switcher`, `command-palette` | `Ctrl/Cmd+P` / `Ctrl/Cmd+Shift+P` | 0 (built-in) |
| `global-search`, `file-explorer`, `outline`, `word-count`, `bookmarks`, `editor-status` | built-in views | 0 |
| `properties` (frontmatter) | native YAML highlighting | 0 |
| Reading view | native preview | 0 |
| `sync`, `file-recovery` | Git (built-in SCM) | 0 |
| — (no Obsidian equivalent) | HTML rendering via Live Preview | 1 |
| Agent workflows | Claude Code / Copilot extensions | 1 |
| Relative Markdown links | built-in click-through, path completion, validation | 0 |
| `backlink`, `outgoing-link`, `graph`, `tag-pane`, `page-preview`, `daily-notes`, `templates`, `note-composer` | not shipped — see gap table above | 2 (declined) |
| `canvas`, `bases`, `appearance.json` font | not shipped | — |

## Round-two decisions (owner, 2026-08-11) and what shipped

1. **Trust policy scope:** strict first-party is the *template default*, overridable per fork. The structured vault-config file for such overrides shipped as `00_Meta/config.yaml` (issue #2): set `extension_trust: relaxed` there to record that a fork admits community extensions such as Foam — see [spec](../10_Agents/tools/brain/spec.md) §15 and `brain config`.
2. **AI harness extensions:** kept (Claude Code, Copilot) — the vault is agent-oriented and both are P0 harnesses.
3. **Brain tooling in-editor:** shipped `.vscode/tasks.json` — validate / rebuild index / search / recent / links-for-current-note (the backlinks substitute) / health / tasks / read-only AYMT and Home previews, all built-in task machinery, `python3` the only requirement.
4. **Snippets over raw templates as the user-facing surface:** shipped `.vscode/second-brain.code-snippets`, **generated** from `09_Templates/` by `10_Agents/tools/vscode/gen_snippets.py` and kept in sync automatically by the pre-commit hook (`--check` mode available). `{{date}}` maps to VS Code's auto-filling date variables; other tokens become tabstops. Plus an `sb-frontmatter` snippet for bare capture.
5. **Cursor synergy:** noted in [wiring](../10_Agents/harnesses/cursor/wiring.md) — the whole `.vscode/` surface works in Cursor unchanged.
6. **Acceptance criteria:** written into PRD §6.5. Config is script-verified in this environment (snippet generation deterministic + valid JSON, daily-note output passes `brain validate`, tasks reference real commands); the open-in-real-VS-Code acceptance pass was waived by the owner at merge (2026-08-11).
7. **Homepage on open:** shipped as a `folderOpen` automatic task opening generated [Home](../00_Meta/HOME.md) without writing (VS Code prompts once to allow automatic tasks; needs the `code` CLI on `PATH`, silently no-ops without it). Recovery is **Tasks: Manage Automatic Tasks in Folder**, trust/allow, reopen; otherwise open Home manually or run read-only `brain home`. Obsidian uses its native tracked `openBehavior: file:00_Meta/HOME.md` setting, grounded in the installed 1.12.7 implementation and the official [1.11.4 setting release](https://obsidian.md/changelog/2026-01-12-desktop-v1.11.4/) plus [1.11.5 extension fix](https://obsidian.md/changelog/2026-01-20-desktop-v1.11.5/).
8. **Old duplicate branch:** ignore/delete note stands (below).

**Spec-parity mechanism (owner follow-up):** two layers. (a) *Automated:* the snippet surface regenerates from templates on every commit — template changes cannot leave VS Code behind. (b) *Procedural:* the **editor-surface parity** checklist item in [OPERATING-RULES](../10_Agents/docs/OPERATING-RULES.md) requires structural/navigation/template changes to update `.obsidian/`, `.vscode/`, and the §6.5 mapping together. Generated Home now has native Obsidian startup behavior and a read-only VS Code folder-open route; explicit `brain home --write` remains the editor-neutral refresh path.

## Verification and adversarial review (2026-08-11)

Machine verification: brain's 22-test suite passes; snippet generation is deterministic (`--check` clean on re-run) and valid JSON; the instantiated daily note passes `brain validate`; all `.vscode/*.json` files parse as JSONC; the full hook chain ran on every commit. An adversarial review over the whole branch diff produced five findings. **Fixed on this branch:**

1. CI now runs `gen_snippets.py --check` (`.github/workflows/validate.yml`) — previously a hookless clone could commit a template change and CI would pass with stale snippets, breaking the §6.5 no-drift guarantee.
2. `brain` note arguments now accept backslash paths (`resolve_note_arg` normalizes `\` → `/`, regression-tested) — the "Links for Current Note" task passes `${relativeFile}` OS-natively and failed on every note on Windows.
3. Every task gained a `windows` command variant (`python` vs `python3`; the homepage task avoids `||`, a parse error in Windows PowerShell 5.1).

**Out of scope for this branch — pre-existing issues recorded for follow-up:**

- `brain` crashes with a traceback on an unreadable note (e.g. broken symlink) instead of recording a per-note error — turns the hook/CI failure message misleading.
- `tags: []` (explicitly empty list) passes `brain validate`; the missing-tags check only fires when the key is absent.
- The Claude Code reference hook (`10_Agents/harnesses/claude-code/settings-example.json`) ends `brain validate || true`, so edit-time findings never reach the agent (needs exit 2 + stderr semantics).

**Human verification (§6.5 acceptance pass):** waived by the owner at merge (2026-08-11); the in-editor pass — extension prompt, `sb-` snippets, task menu, image paste, folder-open homepage — remains a recommended spot-check.

## Process notes

- Requirements were brainstormed first and the trust policy set by the owner before this configuration was finalized; an earlier draft of this branch shipped the Tier 2 community set (Foam et al.) and was reworked to strict first-party on owner direction.
- Delivered on branch `claude/second-brain-vscode-support-jjtrlg` (owner decision 2026-08-11). `claude/vscode-editor-support` is a session-created duplicate pointing at the same history — no unique commits; ignore it. Deleting it currently fails with a GitHub permission error (HTTP 403), so it needs the repo web UI.
- `brain validate` remains the sole authoritative convention check for the vault; editor tooling is assistance only.
