---
title: "brain Spec §19 — Remote safety (`brain remote-safety`) — issue #83"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 19. Remote safety (`brain remote-safety`) — issue #83

*Section 19 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

`remote-safety` is the mandatory preflight before a skill or tool reads personal
data from email, calendar, contacts, chat, drive, task, transcript, or similar
accounts. Capability inventory (which CLIs/connectors exist and which scopes they
claim) is harmless and stays separate; account data is not read until this gate
allows it.

## 19.1 Push-target discovery and normalization

- Discovery uses `git remote` plus `git remote get-url --push --all <remote>` and
  therefore evaluates every effective **push** URL, never fetch URLs alone. Exact
  `DISABLED`, `NO_PUSH`, and `no-push`/`no_push` sentinel values are treated as a
  deliberately fetch-only remote. A discovery failure is `unknown`, not local-only.
- Repository-local `include.path` and `includeIf.*.path` directives are also
  `unknown` (`unsafe-local-config-include`). They can expand through ambient
  HOME or another path outside the clone and substitute a target, so discovery
  reads the raw local config with includes disabled and refuses the indirection.
- Discovery evaluates the union of a sanitized repository-local view and the
  current invocation's ambient-effective Git view. The latter accounts for
  global/system `remote.*.pushurl`, `url.*.insteadOf`/`pushInsteadOf`, HOME, and
  `GIT_CONFIG_*` controls that a later Git invocation would honor; the union
  prevents either view from replacing and hiding a target in the other.
- GitHub HTTPS and SSH (`ssh://` or SCP-style) URLs on their default ports
  normalize to a provider key without userinfo, query, fragment, or `.git`.
  Insecure transports, nonstandard ports, malformed URLs, and non-GitHub hosts
  are `unknown`.
- Output never includes raw URLs, credentials, hostnames other than the provider
  class, owner/repository names, local paths, provider stderr, OS errors, or hashes
  derived from sensitive URL text. Targets are represented only by
  `github.com/<redacted>` (or `<redacted>`) and evaluation-local ordinal identifiers.

## 19.2 Provider boundary and decisions

The default injectable provider runs `gh repo view OWNER/REPO --json
visibility,isPrivate,isTemplate,templateRepository` with prompting disabled and a
bounded timeout. It pins `GH_HOST=github.com` and removes debug/trace sinks and Git
control/config-injection variables from provider child environments. Git target
discovery separately evaluates both repository-local and ambient-effective config;
local config that delegates to another file is rejected as described in §19.1.
Missing `gh`, auth/access
failures, timeouts, malformed JSON, and missing or inconsistent fields are stable
`unknown` reason codes; subprocess text is never forwarded.

Per target, verified `isTemplate: true` or consistent non-private metadata is
`block`; only `visibility: PRIVATE`, `isPrivate: true`, and `isTemplate: false` is
`pass`. Missing or inconsistent fields are `unknown`. `templateRepository` is
queried for provenance but does not make an otherwise private generated repository
a template destination. The combined verified state is `block` if any target
blocks, else `unknown` if any target is unknown, else `pass`.

`--acknowledge-unknown` changes the effective state from `unknown` to `pass` for
that process invocation only and records `verifiedState: unknown` plus the
`unknown-acknowledged` reason. It is never persisted. A verified block remains a
block even with the flag. With no push targets the result is a local-only pass:
personal-data reads may occur in memory, but connector-derived data must not be
written anywhere in the vault.

## 19.3 Output, exit status, and shared guard

Human and `--json` output carry the same stable facts: `schemaVersion`, effective
`state` (`pass|block|unknown`), `verifiedState`, sorted reason codes, target summaries,
`localOnly`, `personalDataAllowed`, `persistenceAllowed`, and
`unknownAcknowledged`. The command adds `persistenceRequested` and
`operationAllowed`. Without `--persist`, operation permission follows the guarded
read; with `--persist`, local-only mode makes `operationAllowed` false. Exit is `0`
only when the requested operation is allowed and `1` otherwise.

All personal-data adapters must call `require_remote_safety(...)` immediately
before the connector and before opening an output file, passing `persist=True`
for capture/write flows. Process-boundary adapters use `remote-safety --persist
--json` and require both zero exit and `operationAllowed: true`. The helper raises
`RemoteSafetyError` on blocked/unknown access and on persistence in local-only
mode; `guarded_personal_data_call(...)` is the reference sequencing wrapper.
