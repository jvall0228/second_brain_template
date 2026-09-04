This repository is a personal knowledge vault shared with AI agents.

Before doing anything, read AGENTS.md at the repository root and follow its
bootstrap sequence (profile, preferences, conventions). All agent output goes
to 02_Inbox/ unless explicitly directed elsewhere. Every note needs YAML
frontmatter with title, tags, and updated.

Validate your changes with:
python3 10_Agents/tools/brain/brain.py validate

After adding, renaming, or deleting notes, regenerate the committed vault
index and include it in your commit:
python3 10_Agents/tools/brain/brain.py index

After editing AGENTS.md, 00_Meta/CONVENTIONS.md, 00_Meta/INDEX.md, or a
01_Profile/ doc, also regenerate the compiled bootstrap file and include
00_Meta/BOOTSTRAP.md in your commit:
python3 10_Agents/tools/brain/brain.py bootstrap --write
