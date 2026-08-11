---
name: solution-capture
description: Record a solved problem in the 10_Agents/solutions/ knowledge base so no agent re-derives it. Use immediately after solving anything non-obvious that could recur — this is a standing carve-out from the Inbox-first rule.
title: "Skill: Solution Capture"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Solution Capture

Append a solution note directly to `10_Agents/solutions/<category>/` — no Inbox detour, no prior approval needed (adding is the carve-out; restructuring or deleting still requires human direction).

## Steps

1. **Pick the category** — an existing directory under `10_Agents/solutions/` whose README fits the problem. If none fits, create a new kebab-case category directory *with a README* describing what belongs there.
2. **Name the note** with a kebab-case slug describing the problem (`wikilink-resolution-rules.md` is the worked example).
3. **Write in the standard shape:**
   ```markdown
   ---
   title: "Concise Problem Name"
   tags:
     - type/solution
     - audience/agent
     - topic/<subject>
   updated: YYYY-MM-DD
   ---

   # Concise Problem Name

   ## Problem      — what goes wrong and when it bites
   ## Symptoms     — how it presents
   ## Solution     — the fix, concrete enough to apply verbatim
   ## Prevention   — how to avoid hitting it again
   ## Related      — links/paths to affected docs
   ```
4. **Keep it evergreen:** facts and commands, no session narrative. If a solution supersedes an old note, update that note (bump `updated:`) instead of writing a duplicate.
5. **Validate and commit:** `python3 10_Agents/tools/brain/brain.py validate`, then commit.

## References

- `10_Agents/solutions/README.md` — category index and format
- `00_Meta/prd.md` §9.2 — the carve-out's exact terms
