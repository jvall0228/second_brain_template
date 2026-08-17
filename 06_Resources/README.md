---
title: "Resources"
tags:
  - type/meta
  - audience/human
  - audience/agent
updated: 2026-08-17
expires: 2027-08-11
---

# Resources

Reference material and topic notes — things you find interesting or useful, not tied to a current project or area of responsibility. Resources are shareable knowledge.

This directory is also the **home of Zettelkasten notes**: evergreen atomic notes live here, tagged `type/zettel` and created from [template-zettel](../09_Templates/template-zettel.md). Subjective sparks start in [Journal/ideas](../03_Journal/ideas/README.md) and graduate here once refined into shareable, atomic form.

## When to Put Something Here

Ask: **"Is this a topic of interest or reference material, not tied to a current project or responsibility?"**

- **Yes** — It's a Resource. Put it here.
- **Tied to a specific outcome with a deadline** — It's a Project. See [README](../04_Projects/README.md).
- **Tied to an ongoing responsibility** — It's an Area. See [README](../05_Areas/README.md).
- **Outdated or no longer useful** — Archive it. See [README](../07_Archives/README.md).

The key test: Could you share this with someone else without context about your life? If yes, it's a Resource.

Examples: "Rust concurrency patterns", "Proxmox setup guide", "Zettelkasten methodology".

## Structure

Each named Resource gets its own directory with an exact-uppercase entrypoint:

- `06_Resources/<resource-name>/RESOURCE.md` — canonical entry note for the Resource
- Supporting notes inside the Resource directory use descriptive kebab-case filenames.
- Atomic `type/zettel` notes remain standalone kebab-case files because each is already one self-contained unit.
- Nested organizational directories use `README.md`; the PARA root remains `06_Resources/README.md`.

## Current Resources

- [Example Resource](example-resource/RESOURCE.md) — Sample reference note. Delete once you've seen the pattern.

## Related

- [INDEX](../00_Meta/INDEX.md) — Full vault map
- [template-resource](../09_Templates/template-resource.md) — Template for reference notes
- [template-zettel](../09_Templates/template-zettel.md) — Template for atomic evergreen notes
