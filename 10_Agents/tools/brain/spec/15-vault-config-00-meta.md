---
title: "brain Spec §15 — Vault config (`00_Meta/config.yaml`) — issue #2"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-04
expires: 2027-08-11
---

# 15. Vault config (`00_Meta/config.yaml`) — issue #2

*Section 15 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

A structured, machine-readable home for per-fork policy overrides, read by `brain` and (through it) by both editor surfaces. Decided 2026-08-11 per the accepted triage recommendation on issue #2.

## 15.1 Location, optionality, change control

- The config lives at **`00_Meta/config.yaml`** — vault-level policy beside the other canonical meta docs, visible to Obsidian and the note corpus (a root dotfile would hide it). It is an asset in the §2 corpus (secret-scanned, indexed path-only); it never carries frontmatter and is exempt from note checks by not being a note.
- The file is **optional, and absence changes nothing**: no file, an empty file, or an all-comment file (the shipped template) all yield the empty config, and every behavior stays at its built-in default. Adding the file must never be required for a working vault.
- **Change control:** like `CLAUDE.md` (PRD §8.2), the file cannot carry `workflow/canonical` — treat it as §6.3 change-controlled anyway, like the meta docs it sits beside.
- The config **never influences `index` output**: the committed index stays a pure function of tracked content (§8.2) with config-independent semantics. Config is consumed by `validate`, by the `config` command, and by future consumers via the reader API.

## 15.2 Grammar bounds

The config grammar is the **same bounded YAML subset** the frontmatter parser targets (§4), extended by exactly one construct — **one level of nested mapping** (a zero-indent key with an empty value followed by uniformly-indented `key: value` lines). Full grammar: blank lines; full-line `#` comments; zero-indent scalar entries and flow lists (§4.3–4.4 semantics: strings always, quote-stripping, no escapes, no type coercion); block lists of scalars under a top-level key; nested mappings whose values are scalars or flow lists. **No pyyaml, ever** — `brain` stays stdlib-only, and the parser is `parse_config` in `brain.py` (the config section there is the planned seed of #31's `shared` module).

Out-of-subset content is **best-effort, never fatal**: each offending line becomes a finding (`config-unsupported`, `config-nesting-too-deep` for a second mapping level, `config-list-item-without-key`, `config-duplicate-key`) and is skipped; the rest of the file still parses. `load_config` returns `({}, [finding])` for an unreadable (`config-not-readable`) or non-UTF-8 (`config-not-utf8`) file and `({}, [])` for an absent one — it never raises.

## 15.3 Key registry

Top-level keys are registered here so later issues cannot collide:

| Key | Status | Meaning |
|-----|--------|---------|
| `write_exceptions` | **implemented** | List of vault-relative directory paths **autonomous (unattended) runs** may write to **in addition to** the Inbox-first defaults (`02_Inbox/`, `02_Outbox/`, `10_Agents/solutions/` — `AGENT_WRITE_DEFAULT_PREFIXES`). Config only ever widens the set; entries are normalized to a trailing `/`. `agent_write_allowed(rel, config)` is the **autonomous destination contract** — the conservative predicate harness write-gates and skills consult for where an autonomous run may write; it also allows the built-in single-file exceptions in `AGENT_WRITE_DEFAULT_FILES` (append-only agent logs inside otherwise PR-only prefixes — currently `10_Agents/docs/rejected-proposals.md`, per conventions § Agent Write Rules). The helper does **not** model interactive write authority or task scope: those are prose policy (AGENTS.md § Where Agents Write), deliberately unenforced here because no tracked caller supplies trusted session metadata, so every caller receives the conservative autonomous fallback. Session-scoped carve-outs (onboard-owner, agent-generated skills/tools per PRD §6.2) remain policy prose, not paths. |
| `extension_trust` | **implemented** | VS Code extension trust policy (PRD §6.5): `first-party` (default) or `relaxed`. A documented override consumed by the editor docs ([vscode-editor-support](../../../../06_Resources/vscode-editor-support.md)) — `brain` exposes the effective value via `extension_trust(config)` and `brain config`; it drives no `brain` behavior itself. |
| `context` | **implemented** (#12) | Fork context recorded by [onboard-owner](../../../skills/setup/onboard-owner/SKILL.md)'s specialization step: **one scalar**, `personal` (the default when absent) or `work`. Beyond parsing and reporting it — `vault_context(config)` and `brain config` expose the effective value — `brain` acts on it in no way yet: specialization happens at onboarding time by rewriting the periodic templates in `09_Templates/` in place from `09_Templates/variants/`, not at read time, so the key is a record for tooling and future skills, not a switch. |
| `environments` | reserved (#15) | — |
| `modules` | reserved (#32) | — |
| `provenance` | reserved (#18) | — |
| `report` | **implemented** (#16) | Health-report thresholds (§16.4): a one-level nested mapping under `report:` whose subkeys are `stale_days` (stale-active threshold, default `30`) and `inbox_days` (Inbox triage-debt threshold, default `14`). Values are non-negative-integer scalars (digits only — §4.3 stores strings; `report_thresholds(config)` converts). A `null` value or absent subkey means the default; malformed values fall back to the default at read time while `check_config` reports them (§15.4). Consumed by `brain report` only — never by `index`, and it moves no `validate` severity. |
| `sync` | reserved (#26) | — |
| `tasks` | **implemented** (#28) | Task-module settings (§17.4): a one-level nested mapping under `tasks:` whose sole subkey is `carry_over` (`on` \| `off`, default `on`) — whether daily-note instantiation carries yesterday's unchecked tasks into the new note's Backlog section (§17.5). `tasks_carry_over(config)` converts; a `null` value or absent subkey means the default; malformed values fall back to the default at read time while `check_config` reports them (§15.4). Consumed by `daily_note.py` only — never by `index`, and it moves no `validate` severity. |
| `template_version` | **implemented** (#6) | Upstream template version record (issue #6): **one scalar**, a free-form version string (by convention the upstream release tag, e.g. `template-v1.2.0`), or absent when the fork has never recorded one. Written by the [sync-upstream](../../../skills/sync-upstream/SKILL.md) skill after a completed sync; that skill compares the recorded value against upstream release tags to find pending releases. A record, not a switch — `template_version(config)` and `brain config` expose the effective value (`null` when unset); `brain` drives no behavior from it and it never influences `index` output. |
| `timezone` | **implemented** | Vault timezone: **one scalar**, an IANA name (e.g. `America/New_York`), kept in parity with the owner's `01_Profile/DEFAULTS.md` § Locale. `vault_timezone(config)` yields the name only when it resolves on the host (else `null`, with a §15.4 warning); `vault_today(config)` computes calendar-today in that zone, falling back to the host clock when unset/unresolvable. Consumed wherever brain stamps or judges a calendar date: AYMT/HOME `updated:`/`expires:` stamping, curation staleness, `report` aging, `tasks --due today` and daily-note dating, and the §10.2 `future-updated` horizon (exact with a timezone; one day of grace without one, so a host anywhere in UTC-12..UTC+14 cannot false-positive). Never influences `index` output. Motivation: cloud agent hosts run UTC, so late-evening local sessions otherwise stamp tomorrow's date. |

Reserved keys parse and are **tolerated silently** whatever their shape. **Unknown** keys (neither implemented nor reserved) are tolerated too — forward compatibility — at the cost of a validate **warning** (`config-unknown-key`), never an error.

## 15.4 Validate semantics

All config findings land **on `00_Meta/config.yaml`** as per-file findings in the normal §10.4 shape. **Errors:** every §15.2 parse finding except `config-duplicate-key`; `config-not-readable` / `config-not-utf8`; `config-invalid-value` (an implemented key with the wrong shape — `write_exceptions` not a list, `extension_trust`, `context`, `template_version`, or `timezone` not a scalar, `report` or `tasks` not a nested mapping, a known `report` subkey whose value is not a digits-only non-negative integer, or a known `tasks` subkey whose value is not a scalar; an explicit `null` equals absent and is clean); `config-bad-write-exception` (an entry that is not a vault-relative path: empty, absolute, drive-lettered, or containing `..`). **Warnings:** `config-duplicate-key` (last wins, mirroring §4.2); `config-unknown-key` (an unknown top-level key, or an unknown subkey under `report` or `tasks`, reported dotted as `report.<key>` / `tasks.<key>`); `config-missing-directory` (a well-formed `write_exceptions` entry naming no existing directory — legal, since a fork may configure ahead of creating it); `config-unknown-value` (an `extension_trust`, `context`, or `tasks.carry_over` value outside its documented pair, or a `timezone` scalar that does not resolve as an IANA zone on this host — brain falls back to the host clock).

## 15.5 `config` command

`brain config` (§9 conventions: `--json`, exit 0) prints the **effective** configuration: presence, the raw parsed map, the merged write-exception prefixes (defaults first), the effective `extension_trust`, the effective `context`, the effective task carry-over toggle (§17.4), the recorded `template_version` (`null` when unset), the effective `timezone` (`null` when unset or unresolvable), the reserved-key list, and any findings. It is the non-Python surface of the reader API for harness tasks and scripts.
