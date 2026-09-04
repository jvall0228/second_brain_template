---
title: "Vault Answer Gaps"
tags:
  - type/log
  - audience/agent
updated: 2026-09-04
expires: 2027-08-11
author: claude-code
---

# Vault Answer Gaps

The retrieval loop's gap memory: every question [vault-answer](../skills/vault-answer/SKILL.md) could not answer from the vault, one checkbox each. It is the default queue for [research-to-resource](../skills/research-to-resource/SKILL.md): a run invoked without a topic takes the oldest open row, and a run that fills a gap ticks the row and links the note it wrote. `brain tasks --open` lists the open rows with every other task.

Row shape (one line, oldest first, never reordered):

```markdown
- [ ] YYYY-MM-DD — <the question as asked> — searched: `term`, `term` — nearest: [note](../../path.md) or none <!-- gap: <id> -->
```

Rows are written only by `brain gap` (spec §29.3): the question and terms are forced onto one escaped line, and a nearest note is linked by title — or by path only when it is `restricted/private`. Ticking a row appends ` → [note](../../06_Resources/slug.md)`. Rows are never deleted; a question the owner decides not to research is ticked with ` → declined` so it is not re-queued. Interactive sessions append here directly; an autonomous run (`brain gap --inbox`) puts the row in an Inbox capture instead (Inbox-first rule), and triage moves it here with `brain gap --ingest <capture> --write`, which appends the row once (each row ends in a `<!-- gap: <id> -->` identity marker) and deletes the capture. A **sensitive** gap — one whose nearest notes are restricted, or flagged `--sensitive` because the question itself is private — never appears here: it becomes a `restricted/private` Inbox capture; `--ingest` refuses it unless the owner passes `--declassify`, an explicit triage decision ([Write Authority Contract](write-authority.md) § Append-only agent logs).

## Open and filled gaps

## Related

- [vault-answer](../skills/vault-answer/SKILL.md) — appends rows at its step 6
- [research-to-resource](../skills/research-to-resource/SKILL.md) — consumes rows at its step 1
- [rejected-proposals](rejected-proposals.md) — the self-improve loop's equivalent memory
