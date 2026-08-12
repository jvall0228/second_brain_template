---
title: "Operating Rules"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Operating Rules

Behavior expectations for agents working in this vault. These supplement — not duplicate — the rules in [AGENTS](../../AGENTS.md) and [CONVENTIONS](../../00_Meta/CONVENTIONS.md).

## Bootstrap Before Working

Always read the bootstrap sequence before producing output. See [AGENTS](../../AGENTS.md#bootstrap-sequence-must-read-order).

**Arm the pre-commit hook before your first commit:** run `git config core.hooksPath .githooks` once per clone. Fresh agent environments (cloud containers, CI checkouts, new clones) do not have it, and without it your commits ship a stale vault index that fails CI for everyone. Claude Code sessions get this automatically via the repo's `.claude/settings.json` SessionStart hook; every other harness runs it manually at bootstrap.

## Read Before Write

Before creating or modifying a note, read:

1. The target directory's README (e.g., `04_Projects/README.md`)
2. Any existing note you're about to update
3. Relevant templates from `09_Templates/`

## Update by Replacement, Not Accumulation

When updating an existing note, **replace** the sections the new content conflicts with or obsoletes — never append a new section alongside a stale one. Append-only editing bloats notes into contradictory context dumps that mislead every future reader, human or agent. A note must always read as the current state of knowledge; git history preserves every prior version for posterity, so deleting outdated content loses nothing. Appending is right only for genuinely additive structures — logs, journals, changelog-style records — where entries are events, not claims.

For [PRD](../../00_Meta/PRD.md) specifically, edit superseded requirements in place and describe only shipped behavior, the live roadmap, and genuinely unresolved decisions. Record a structural PRD change once in [CHANGELOG](../../00_Meta/CHANGELOG.md); Git holds detailed revision history. Do not add revision banners, compatibility addenda, resolved incident narratives, or duplicate consideration logs to the PRD.

## Canonical Note Handling

Notes tagged `workflow/canonical` are vault infrastructure. The same protection applies to canonical-by-policy artifacts without note tags: template-shipped skills/tools, `00_Meta/config.yaml`, and named entrypoint/editor/harness adapters. Agents modify either class only through a pull request or current, explicit human approval.

Location alone does not make an artifact canonical. A live, user-invoked `agent-orientation` session may create the inventory and paired access-tool/capture-skill bundle at the paths in its contract. The inventory, skill, and tool documentation remain `workflow/draft`; non-note files inherit that bundle state until the owner promotes the whole bundle.

Without that authority, propose a change:

1. Write a note to `02_Inbox/` explaining the proposed change
2. Tag it `workflow/needs-review`
3. Reference the canonical note with a source-relative Markdown link

The human reviews and applies (or rejects) the change.

## Stuck/Escalation Protocol

When blocked — a required input is missing, an instruction is ambiguous in a way more reading can't resolve, or two vault sources contradict each other — never guess-and-commit, and never silently resolve a conflict between notes. Instead:

1. Write a `02_Inbox/` note tagged `workflow/needs-review` stating what you were doing, what blocked you (for conflicts: link both sources and quote the conflicting claims), and the options you see.
2. Stop that line of work. Continue any unaffected work; if nothing remains, end the session cleanly (see Session-End Flush below).

The human resolves the conflict; the resolution usually becomes an edit to one of the conflicting notes, so the vault — not just the session — gets unstuck.

## Self-Validation

Before writing any note, verify:

- [ ] Frontmatter includes `title`, `tags`, `updated`
- [ ] `updated:` is set to today's date — on every edit, not just creation
- [ ] Tags use defined namespaces (see [CONVENTIONS](../../00_Meta/CONVENTIONS.md#tag-namespaces))
- [ ] Filename follows [CONVENTIONS](../../00_Meta/CONVENTIONS.md#filename-convention) and does not collide with an existing note
- [ ] Agent-authored Inbox notes carry provenance: `author:` (harness identifier, e.g. `claude-code`) plus `session:` when a session URL / PR / task reference exists (see [CONVENTIONS](../../00_Meta/CONVENTIONS.md) § Provenance)
- [ ] Destination is the right lane: `02_Inbox/` for vault content, `02_Outbox/` for outbound packets via express-packet, or a documented standing exception (solutions, rejection log, live `onboard-owner`, or live user-invoked `agent-orientation` inventory plus paired draft bundle)
- [ ] Generated AYMT changes came only from explicit `brain aymt --write`; generic agents and `agent_write_allowed()` cannot hand-edit `00_Meta/AYMT.md`, and no config exception was added
- [ ] Generated Home changes came only from explicit `brain home --write`; generic agents and `agent_write_allowed()` cannot hand-edit `00_Meta/HOME.md`, and no config exception was added
- [ ] Generated local artifact changes came only from explicit `brain artifacts --write`; the exact two HTML files and manifest passed `--check`, and no generic `08_Assets/` write exception, hosting, or notification claim was added
- [ ] A generated orientation bundle is still draft: its inventory, skill, and tool documentation say `workflow/draft`, and no non-note file is treated as canonical-by-policy before owner promotion
- [ ] **Restricted containment** ([restricted/private](../../00_Meta/CONVENTIONS.md#tag-namespaces)): never quote or summarize `restricted/*` content into non-restricted notes — link it instead (validate warns `restricted-link` even on the bare link, as a reminder). The tag is advisory outside mechanically-enforced surfaces; your restraint *is* the mechanism.
- [ ] Run `brain validate` after writing — fix any errors it reports before committing (clean-checkout and long-form fallbacks are in [brain](../tools/brain/README.md))
- [ ] **Editor-surface parity** ([PRD](../../00_Meta/PRD.md) §6.5): if the change alters vault structure, navigation, or templates, update both editor surfaces — `.obsidian/` and `.vscode/` (settings/tasks by hand; snippets regenerate automatically via the pre-commit hook) — and the §6.5 feature mapping

## Upstream Boundary

**Never push upstream.** The fork pulls updates from the public upstream template ([sync-upstream](../skills/sync-upstream/SKILL.md), pull-only); agents never push, open PRs, or write in any form to the upstream public repo unless operating as its owner. Generalizable improvements discovered in this fork are *suggested to the owner* as "worth upstreaming?" (in sync reports or [self-improve](../skills/self-improve/SKILL.md) retrospectives) — the owner carries them upstream by hand if they choose.

## Personal-data remote safety

Capability inventory is safe: agents may identify installed CLIs/connectors and
their declared scopes without reading account data. Immediately before any email,
calendar, contacts, chat, drive, task, transcript, or similar personal-data read,
run `brain remote-safety --json` and use the shared
guard in generated tooling (brain spec §19). Add `--persist` for any capture or
other flow that will write connector-derived data; require both a zero exit status
and `operationAllowed: true` at a process boundary.

- `block` and `unknown` stop before the connector and before opening an output file.
- The owner may acknowledge `unknown` for the current invocation only with
  `--acknowledge-unknown`; a verified public, non-private, or template push target
  is never overrideable.
- A no-push repository is local-only. Connector-derived data remains in memory and
  is never written into the vault.
- Raw remote URLs, provider errors, credentials, repository identities, and local
  paths never enter output, logs, notes, or artifacts.

## Concurrency

Multiple agents may work in this vault. Sync (pull) before writing when the environment allows, keep commits small, and never force-push. Merge conflicts are resolved by the human.

## Session-End Flush

The vault only knows what reaches disk — chat context evaporates. Before ending a working session, and when the harness is about to compact or truncate its context, flush anything durable:

- A solved problem worth reusing → the [solution-capture](../skills/solution-capture/SKILL.md) skill.
- General session learnings — decisions made, surprises found, the state of half-finished work → today's daily log ([daily-log](../skills/daily-log/SKILL.md)) or an Inbox capture.
- Nothing durable happened → write nothing; don't manufacture a note to satisfy this rule.

Then commit and push, so the flush actually survives the session.

## Related

- [AGENTS](../../AGENTS.md) — Vault entrypoint
- [CONVENTIONS](../../00_Meta/CONVENTIONS.md) — Full convention reference
- [TASK-PATTERNS](TASK-PATTERNS.md) — Write rules and examples
