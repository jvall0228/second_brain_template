---
title: "Accepted Proposals"
tags:
  - type/log
  - audience/agent
updated: 2026-09-04
expires: 2027-08-11
author: claude-code
---

# Accepted Proposals

The [self-improve](../skills/self-improve/SKILL.md) loop's acceptance memory, the mirror of [rejected-proposals](rejected-proposals.md): every proposal the owner accepted (PR merged, or Inbox proposal accepted at triage), one row each. **Append-only** — rows are never edited or removed. Each row names the verification the next cycle owes the change, so the Observe step checks whether it had its expected effect, and a later cycle never re-proposes what already shipped. Interactive sessions append here directly; an autonomous run carries its rows in the retrospective report it writes to `02_Inbox/` (under `## Accepted proposals`, same columns), and triage moves them here with `brain accepted --ingest <report> --write` — the only writer besides an interactive append; it rebases links and skips rows already present ([Write Authority Contract](write-authority.md) § Append-only agent logs).

| Date | Proposal | What changed | Verification owed |
|------|----------|--------------|-------------------|

## Related

- [self-improve](../skills/self-improve/SKILL.md) — the loop that reads and appends here
- [rejected-proposals](rejected-proposals.md) — the rejection memory
