---
title: "VS Code as Alternative Editor: Requirements, Trust Policy, and Config"
tags:
  - audience/agent
  - audience/human
  - type/reference
  - topic/software
  - workflow/draft
updated: 2026-08-11
---

# VS Code as Alternative Editor: Requirements, Trust Policy, and Config

Owner-directed (2026-08-11): the vault spec supports **VS Code as an alternative editor** for when Obsidian is not available. This note records the requirements brainstorm, the extension **trust policy the owner set**, the online research behind the candidates, and the mapping from the shipped `.obsidian/` config to the shipped `.vscode/` config. The working config lives at `.vscode/settings.json` + `.vscode/extensions.json` (root-scope dot-path, outside the note corpus — the `.github/` / `CLAUDE.md` precedent from [[00_Meta/prd]] §9.3). Spec change: [[00_Meta/prd]] §6.5.

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
9. **P0 harness companions** (PRD §8.3): **Claude Code** (`anthropic.claude-code`) and **Copilot** (`github.copilot`) — the two P0 harnesses with VS Code surfaces; wiring docs under `10_Agents/harnesses/`. With a harness attached, agent-mediated workflows (daily log via the [[10_Agents/skills/daily-log/SKILL|daily-log]] skill, link queries via `brain`) partially compensate for the excluded community features below.

**Tier 2 — full Obsidian parity — evaluated and NOT shipped (fails trust policy):**

10. Wikilink click-through/completion, backlinks panel, graph view, tag explorer, daily-note command. Only community extensions provide these (see research below). Owner reviewed and declined; accepted gaps with mitigations:

| Gap (Obsidian plugin) | Mitigation in VS Code |
|---|---|
| Wikilink navigation | `Ctrl/Cmd+P` / search on the target name; `brain links <note>` for outgoing/backlinks; `brain validate` catches broken links |
| Backlinks (`backlink`, `outgoing-link`) | `brain links --json`; workspace search for `[[target` |
| Graph (`graph`) | none (accepted) |
| Tag pane (`tag-pane`) | `brain tags`; workspace search for the tag string |
| Daily notes (`daily-notes`) | [[10_Agents/skills/daily-log/SKILL|daily-log]] skill via an attached harness, or copy `09_Templates/template-daily-log.md` |
| Mermaid in preview | renders on GitHub and in Obsidian; not in VS Code preview (accepted) |
| Canvas, `bases` | Obsidian-proprietary; accepted (template ships neither) |

## Candidates evaluated (research, 2026-08-11)

| Candidate | Publisher type | Verdict under policy |
|---|---|---|
| Live Preview (`ms-vscode.live-server`) | Microsoft org | **Shipped** |
| Claude Code (`anthropic.claude-code`) | Anthropic org | **Shipped** |
| Copilot (`github.copilot`) | GitHub org | **Shipped** |
| Foam (`foam.foam-vscode`) | Community (MIT, 17.3k★, 133 contributors, ~268k installs, 5.0★) | Excluded — best-in-class for wikilinks/backlinks/graph/tags/daily notes, and the closest Obsidian equivalent, but community-published with no org backing. Documented as the owner-optional upgrade if the policy is ever relaxed. |
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
| Wikilinks, `backlink`, `outgoing-link`, `graph`, `tag-pane`, `page-preview`, `daily-notes`, `templates`, `note-composer` | not shipped — see gap table above | 2 (declined) |
| `canvas`, `bases`, `appearance.json` font | not shipped | — |

## Process notes

- Requirements were brainstormed first and the trust policy set by the owner before this configuration was finalized; an earlier draft of this branch shipped the Tier 2 community set (Foam et al.) and was reworked to strict first-party on owner direction.
- Delivered on the dedicated branch `claude/vscode-editor-support`, isolated from parallel skill-rearchitecture work.
- `brain validate` remains the sole authoritative convention check for the vault; editor tooling is assistance only.
