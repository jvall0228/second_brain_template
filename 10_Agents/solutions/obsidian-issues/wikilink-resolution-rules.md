---
title: "Obsidian Wikilink Resolution Rules"
tags:
  - type/reference
  - topic/obsidian
  - topic/productivity
  - audience/agent
updated: 2026-02-21
---

# Obsidian Wikilink Resolution Rules

## Problem

When migrating or reorganizing Obsidian vault files, wikilinks break in subtle ways. Understanding how Obsidian resolves `[[links]]` is essential to avoid broken references.

## Symptoms

- Links appear valid but don't navigate to the expected file
- Links work in one vault but break after migration
- Renamed or moved files cause cascading link failures
- Links to periodic notes resolve to wrong files or show as unresolved

## How Obsidian Resolves Wikilinks

Obsidian uses **filename matching** across the entire vault (shortest unique path). The resolution order:

1. **Exact filename match** (minus `.md`) — `[[foo]]` matches `foo.md` anywhere in the vault
2. **Shortest unique path** — if multiple `foo.md` exist, Obsidian picks the shortest disambiguating path
3. **Full path match** — `[[path/to/foo]]` matches `path/to/foo.md` exactly

### Key Rules

| Pattern | Resolves? | Why |
|---------|-----------|-----|
| `[[2024-01-02]]` | Yes | Matches `2024-01-02.md` by filename |
| `[[2024-01]]` | No | No file named `2024-01.md` exists (it's `2024-01-review.md`) |
| `[[2024-01-review]]` | Yes | Matches `2024-01-review.md` by filename |
| `[[Bits of Wisdom]]` | Yes* | Matches if a file's `title:` frontmatter equals "Bits of Wisdom" |
| `[[2024-12-31 (W01)]]` | No | Parentheses in filenames cause issues; title matching is unreliable |
| `[[path/to/file]]` | Yes | Exact path match — but breaks if the file moves |
| `[[path/to/file\|Display]]` | Yes | Same as above, with display text alias |

*Title-based resolution depends on Obsidian settings and may not work reliably.

## Solution: Safe Linking Patterns

### For links within the same directory

Use bare filenames — they survive directory renames:

```markdown
[[2024-01-02]]           <!-- daily note linking to another daily note -->
[[2024-W01-review]]      <!-- weekly note linking to another weekly note -->
```

### For links across directories

Use full paths with display text — explicit and unambiguous:

```markdown
[[03_Journal/periodic/weekly/2024-W01-review|Week 1]]
[[03_Journal/periodic/monthly/2024-01-review|January]]
[[06_Resources/example-resource|Example Resource]]
```

### For links to migrated content notes

If the filename is kebab-case but the original title used spaces, prefer the path:

```markdown
[[03_Journal/insights/lessons-learned|Lessons Learned]]
```

## Common Mistakes

### 1. Assuming partial filename matches work

```markdown
<!-- BROKEN: no file named "2024-01.md" exists -->
[[2024-01|January]]

<!-- FIXED: use the full filename -->
[[03_Journal/periodic/monthly/2024-01-review|January]]
```

### 2. Using old-vault title format as link target

```markdown
<!-- BROKEN: no file named "2024-12-31 (W01).md" exists -->
[[2024-12-31 (W01)|Week 1]]

<!-- FIXED: use the new filename -->
[[03_Journal/periodic/weekly/2024-W01-review|Week 1]]
```

### 3. Forgetting the `-review` suffix

```markdown
<!-- BROKEN: file is "2024-01-review.md" not "2024-01.md" -->
[[2024-01]]

<!-- FIXED -->
[[2024-01-review]]
```

## Prevention

When creating or migrating notes with cross-references:

1. **Check the actual filename** of the target, not the title
2. **Use full paths** for links that cross directory boundaries
3. **After reorganizing files**, grep for old link patterns: `grep -r '\[\[old-name' .`
4. **Test in Obsidian** — hover over links to verify they resolve

## Related

- `03_Journal/README.md` — periodic note naming conventions
- `09_Templates/README.md` — template destinations for each note type
