---
title: "Relative Markdown Link Rules"
tags:
  - type/solution
  - topic/obsidian
  - topic/productivity
  - audience/agent
updated: 2026-08-11
---

# Relative Markdown Link Rules

## Problem

Internal links can work in one editor yet break in another when their destination is ambiguous, vault-root-relative, incorrectly encoded, or tied to editor-specific syntax. The vault needs one form that resolves identically in Obsidian, VS Code, GitHub, and `brain`.

## Symptoms

- Links appear valid but don't navigate to the expected file
- Links work in one vault but break after migration
- Renamed or moved files cause cascading link failures
- Links to periodic notes resolve to wrong files or show as unresolved

## Solution: one portable form

Maintained content uses inline Markdown with a human label and a destination relative to the source note. Note destinations include `.md`; asset destinations include their real extension. Paths use `/`, exact case, and UTF-8 percent encoding for spaces and non-ASCII bytes. Obsidian's tracked settings create this form by default.

`brain` resolves the destination from the source file, rejects paths that escape the vault or disguise external schemes, and never guesses among ambiguous case-folded paths. Heading fragments use GitHub's rendered-heading slug rules, including duplicate suffixes such as `-1`.

## Safe linking patterns

### For links within the same directory

Use the sibling filename including its extension:

```markdown
[Previous day](2024-01-02.md)
[Weekly review](2024-W01-review.md)
```

### For links across directories

Walk from the source directory with `../` segments or a child directory:

```markdown
[Week 1](../weekly/2024-W01-review.md)
[January](../monthly/2024-01-review.md)
[Example Resource](../../../06_Resources/example-resource.md)
```

### For links to migrated content notes

Keep the readable title in the label and the real filename in the destination:

```markdown
[Lessons Learned](../insights/lessons-learned.md)
```

## Common Mistakes

### 1. Using a partial or title-shaped destination

```markdown
<!-- BROKEN: no file named "2024-01.md" exists -->
[January](2024-01.md)

<!-- FIXED: use the full filename -->
[January](2024-01-review.md)
```

### 2. Omitting percent encoding

```markdown
<!-- BROKEN: a literal space is not the canonical destination form -->
[Café notes](café notes.md)

<!-- FIXED: encode the UTF-8 path bytes -->
[Café notes](caf%C3%A9%20notes.md)
```

### 3. Using a vault-root path

```markdown
<!-- BROKEN: leading slash is not source-relative -->
[Conventions](/00_Meta/CONVENTIONS.md)

<!-- FIXED from a note under 03_Journal/periodic/monthly/ -->
[Conventions](../../../00_Meta/CONVENTIONS.md)
```

## Prevention

When creating or migrating notes with cross-references:

1. **Check the actual filename and exact case** of the target, not its title.
2. **Compute the destination from the source note**, not from the vault root.
3. **Keep explicit extensions and encode path bytes**; preserve a meaningful label or image alt text.
4. **After reorganizing files**, run `brain validate --check-index` and inspect `brain links <note>`.
5. **Use `brain migrate-links` only for imports**; maintained content must make `brain migrate-links --check` return zero.

## Related

- `03_Journal/README.md` — periodic note naming conventions
- `09_Templates/README.md` — template destinations for each note type
