---
title: "VS Code as Alternative Editor: Requirements and Config"
tags:
  - audience/agent
  - audience/human
  - type/reference
  - topic/software
  - workflow/draft
updated: 2026-08-11
---

# VS Code as Alternative Editor: Requirements and Config

Owner-directed (2026-08-11): the vault spec should support **VS Code as an alternative editor** for when Obsidian is not available. This note records the requirements brainstorm, the online research behind the extension choices, and the mapping from the shipped `.obsidian/` config to the shipped `.vscode/` config. The working config itself lives at `.vscode/settings.json` + `.vscode/extensions.json` (root-scope dot-path, outside the note corpus — the `.github/` / `CLAUDE.md` precedent from [[00_Meta/prd]] §9.3). PRD change proposed alongside: new §6.5.

## Requirements (brainstormed)

**Must have — parity with the enabled `.obsidian` core plugins:**

1. **Wikilink navigation and completion** — follow `[[00_Meta/conventions]]`-style links (path-style, `#heading`, `|alias`), autocomplete targets while typing. Obsidian: core editor. VS Code: Foam.
2. **Backlinks** — see what links to the current note (`backlink`, `outgoing-link` plugins). VS Code: Foam's Connections/Backlinks panel.
3. **Graph view** — visualize the link graph (`graph` plugin). VS Code: Foam's "Show graph" command.
4. **Tag navigation** — browse slash-namespaced tags (`tag-pane` plugin). VS Code: Foam's Tag Explorer, which supports hierarchical (`topic/software`) tags.
5. **Markdown preview with mermaid** — rendered reading view. VS Code: built-in preview (`Ctrl/Cmd+Shift+V`) + mermaid extension.
6. **Daily notes** — one command to open today's log in `03_Journal/periodic/daily/` (`daily-notes` plugin). VS Code: Foam `openDailyNote`, configured to the same directory and `yyyy-mm-dd` filenames.
7. **Quick switcher / search / file explorer / outline / word count** (`switcher`, `global-search`, `file-explorer`, `outline`, `word-count` plugins) — all native VS Code (`Ctrl/Cmd+P`, search view, explorer, outline view, status bar).
8. **YAML frontmatter (`properties` plugin)** — native syntax highlighting in VS Code; no extension required.
9. **HTML rendering** — preview HTML files (exports, `08_Assets/` artifacts) inside the editor. Obsidian has no real equivalent (`webviewer` is disabled in our config); VS Code: Microsoft **Live Preview**.

**Must have — vault-contract safety:**

10. **No diff noise.** The editor must not rewrite notes on save (no format-on-save, no auto-appended link-reference definitions) — PRD §14 diffability. This drives two config decisions: `foam.edit.linkReferenceDefinitions: "off"` and Prettier in `unwantedRecommendations`.
11. **Asset rule preserved.** Pasted images must land in `08_Assets/` (PRD §16.1) — handled natively via `markdown.copyFiles.destination`, no extension needed (VS Code ≥1.79).
12. **Zero-setup onboarding.** Opening the repo folder must prompt "install recommended extensions" and work after one click — the same day-one usability bar as "usable as an Obsidian vault from day one" (PRD §13).
13. **Search hygiene.** `vault-index.json` duplicates every note's text; exclude it (and `.obsidian/`) from workspace search.

**Nice to have (documented, not shipped):**

- **Lint parity with `brain validate`** — markdownlint is shipped with a relaxed config (frontmatter-first notes, inline HTML allowed, soft wrap); it complements but does not replace `brain validate`, which stays authoritative.
- **Templates** — Foam templates live in `.foam/templates/`, which would duplicate `09_Templates/` (single-source violation). Not shipped; instantiate templates by copying from `09_Templates/` or via an agent, as today.
- **Canvas** (`canvas` plugin) — `.canvas` files are Obsidian-proprietary JSON; no faithful VS Code renderer. Accepted gap (the template ships no canvas files).
- **Sync / file recovery** — covered by Git in VS Code (built-in SCM view); Obsidian Sync is orthogonal.

## Shipped config: `.obsidian` → `.vscode` mapping

| Obsidian (`.obsidian/`, enabled plugin) | VS Code equivalent | How |
|---|---|---|
| Editor wikilinks | Foam | `foam.foam-vscode` extension |
| `backlink`, `outgoing-link` | Foam Connections panel | same |
| `graph` | Foam: Show graph | same |
| `tag-pane` | Foam Tag Explorer | same |
| `page-preview` (hover) | Foam link hover preview | same |
| `daily-notes` → `03_Journal/periodic/daily/` | Foam daily note | `foam.openDailyNote.*` in settings.json |
| `switcher`, `command-palette` | native | `Ctrl/Cmd+P` / `Ctrl/Cmd+Shift+P` |
| `global-search`, `file-explorer`, `outline`, `word-count`, `bookmarks`, `editor-status` | native | built-in views |
| `properties` (frontmatter) | native YAML highlighting | built-in |
| Reading view / preview | native preview + mermaid | `bierner.markdown-mermaid` |
| — (no Obsidian equivalent) | HTML rendering | `ms-vscode.live-server` (Live Preview) |
| `templates`, `note-composer` | partially via Markdown All in One | `yzhang.markdown-all-in-one`; templates stay manual (see above) |
| `sync`, `file-recovery` | Git | built-in SCM |
| `canvas`, `bases` | no equivalent | accepted gap |
| `appearance.json` font | not imposed | user-level setting, not workspace |

## Research notes (2026-08-11)

- **Foam vs. alternatives.** The Obsidian-like VS Code ecosystem has four candidates: **Foam** (FOSS, active, works on plain markdown folders, explicitly compatible with Obsidian-style vaults), **Dendron** (imposes its own hierarchical vault structure — wrong fit), **Markdown Memo** (bidirectional links, less active), and **AS Notes** (newer, smaller). Foam wins: no structural demands on the repo, supports path-style wikilinks, `#heading` anchors, `|` aliases, hierarchical tags, backlinks, graph, daily notes, and hover preview.
- **Foam's own template** ships `.vscode/settings.json` + `extensions.json` with auto-save, markdown quick-suggestions, and its recommended-extension prompt — the pattern our shipped config follows. Its default `foam.edit.linkReferenceDefinitions` behavior (appending link-reference blocks) is deliberately disabled here for diff hygiene.
- **Markdown editing/preview extension consensus (2026):** Markdown All in One (editing shortcuts, tables, ToC — 5M+ installs), markdownlint (style consistency), Markdown Preview Enhanced (heavier alternative preview with PlantUML/math — omitted from recommendations as overkill; the built-in preview + mermaid covers our notes), and mermaid support for the built-in preview.
- **HTML rendering:** Microsoft's first-party **Live Preview** (`ms-vscode.live-server`) renders HTML in an embedded, auto-refreshing browser panel — the standard answer for viewing HTML inside VS Code.
- **Native VS Code has absorbed a lot:** markdown link validation (`markdown.validate.enabled`), path completion, drag/paste-image-to-destination (`markdown.copyFiles.destination`), frontmatter highlighting — several former extension jobs need no extension now.

Sources:

- [XDA: Using VS Code instead of Obsidian for notes](https://www.xda-developers.com/tried-using-vs-code-obsidian-notes/)
- [Deep Notes: Integrating Obsidian with VS Code](https://deepaksood619.github.io/devops/ides/obsidian-in-vscode/)
- [Foam (GitHub)](https://github.com/foambubble/foam) and [foam-template `.vscode/`](https://github.com/foambubble/foam-template)
- [Foam on the VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=foam.foam-vscode)
- [Best Markdown Extensions for VS Code in 2026](https://www.merge-json-files.com/blog/best-markdown-extensions-for-vscode)
- [VS Code Markdown Guide 2026](https://allmarkdowntools.com/vscode-markdown)
- [Live Preview extension (Microsoft)](https://marketplace.visualstudio.com/items?itemName=ms-vscode.live-server)

## Known caveats

- **Embeds:** Obsidian `![[file.png]]` embeds render in Obsidian only; Foam renders `![[note]]` embeds in preview but image-attachment embeds are weaker. The conventions already name relative markdown links as the portable option (PRD §16.1) — VS Code renders those fine.
- **Foam writes nothing by default with our settings** — but if a future setting change re-enables link-reference definitions, expect bulk diffs; keep it off.
- **`brain validate` stays authoritative** for vault conventions; markdownlint is cosmetic assistance only.

## Proposed spec amendment

Applied on this branch for review (canonical change per §6.3): [[00_Meta/prd]] gains **§6.5 Alternative editor: VS Code** — Obsidian remains the primary human UI (§2 unchanged); the repo additionally ships `.vscode/` workspace config so the vault is usable in VS Code with feature parity for linking, backlinks, graph, tags, daily notes, markdown preview, and HTML rendering. [[00_Meta/changelog]] entry added.
