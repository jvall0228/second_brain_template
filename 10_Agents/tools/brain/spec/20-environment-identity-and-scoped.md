---
title: "brain Spec §20 — Environment identity and scoped retrieval"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-07
expires: 2027-08-11
---

# 20. Environment identity and scoped retrieval

*Section 20 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

Environment-scoped infrastructure is explicit, privacy-safe, and fail-closed.
Shared vault content remains portable; live wiring belongs to exactly one
owner-chosen environment.

## 20.1 Tracked manifest

Each registered environment is an immediate kebab-case directory at
`10_Agents/environments/<slug>/`. It contains a tracked `environment.json` and
a self-guarding `README.md`. The UTF-8 JSON manifest is at most 64 KiB and has
this exact version-1 shape:

```json
{
 "capabilities": {"computer-use": true},
 "class": "laptop",
 "fingerprints": [{"algorithm": "sha256", "digest": "<64 lowercase hex>", "source": "machine-v1"}],
 "freshness": {"checkedAt": "2026-08-11", "expiresAt": "2026-11-11"},
 "maintenance": {"inventory": "orientation-inventory.md", "ownerReviewRequired": true},
 "schemaVersion": 1,
 "slug": "work-laptop",
 "surfaces": ["codex", "vscode"]
}
```

`class` is `desktop`, `laptop`, `server`, `container`, `cloud`, or `other`.
Surfaces are sorted unique kebab-case identifiers. Capabilities map sorted
non-secret kebab-case names to booleans; identity, path, endpoint, and
credential-shaped names are forbidden. Fingerprints are SHA-256 evidence over
high-entropy, platform-native OS machine identifiers consumed inside the hash
boundary; malformed, nil, weak, and placeholder identifiers are rejected
before hashing. The list may be empty when the OS supplies no acceptable
identifier; that environment remains selectable explicitly or by selector. A
hostname/username fallback is forbidden because hashing low-entropy identity is
dictionary-identifiable; when no high-entropy ID is available, automatic
fingerprint matching is unavailable and explicit/selector selection is
required. Raw hostname, username,
home/repository path, credential, URL, and endpoint values never enter tracked
data, output, logs, or errors. `freshness` dates are real and ordered. The
maintenance record always points to the local inventory and requires owner
review. JSON field types are exact: schema version is integer `1` (never a
boolean/float), and every fingerprint component is a string before duplicate
or digest checks. Malformed values produce redacted findings rather than an
exception. Unknown keys or schema versions are errors.

## 20.2 Clone-local state

`.second-brain/environment` contains one selected slug. It and
`.second-brain/environments/<slug>/` are gitignored. The latter is the only
repository-local home for secrets-adjacent environment overlays such as
integration settings, notification destinations, hosting configuration, and
delivery state. Selectors/manifests may not be symlinks; directories must be
immediate children of their declared roots. Inputs are length- and grammar-
bounded before use.

Environment files are re-confined when opened, not merely when discovered.
Every child component and the final file must remain a non-link/reparse-point
path inside the vault; an identity change or race fails closed before content
can reach a result.

## 20.3 Selection

Selection precedence is `--env <slug>` > `SECOND_BRAIN_ENV` > the selector > a
unique local fingerprint match. `--env current` and the environment-variable
value `current` request normal automatic selection. An invalid value, missing
explicit/selected slug, invalid manifest, no fingerprint match, or multiple
fingerprint matches fails closed with a stable reason code; lower-precedence
sources are never consulted after a higher-precedence source is present. A
vault with zero registered manifests is `unconfigured` and shared-only.
Reason codes are non-identifying by design, so the CLI's human (stderr) error
path names them; for the automatic-selection failures (`no-fingerprint-match`,
`ambiguous-fingerprint`) it also prints a one-line remedy hint naming the
explicit-selection precedence chain (`brain env list`, `--env <slug>`,
`SECOND_BRAIN_ENV`, the selector file), so a host whose fingerprint matches
no registered environment names its own recovery instead of failing opaquely.
JSON output never carries the hint; `aymt`/`home` JSON keeps the bare
safe-failure object while their stderr message appends the reason code.

All content-query consumers use the selected corpus: shared paths plus
`10_Agents/environments/<selected>/`, never another environment. This includes
list/search/links/tags/show/recent, report/curate/tasks, semantic embedding, and
current-scoped maintenance. Generic `brain validate` is intentionally
environment-neutral for CI and foreign clones: it validates every manifest
envelope, validates shared content, and does not select or read any environment
note body. The committed index deliberately contains shared tracked content
only, so its bytes do not vary by clone; selected environment notes remain
available through live commands. `brain env list` is the sole all-environment
diagnostic and emits only slug, registered/selected status, and freshness. It
never emits class, surfaces, capabilities, fingerprint counts/digests, or
capability values.

### Explicit shared scope

`brain --shared-only <command>` (also accepted after the command) deliberately
uses shared content without selecting or registering an environment. It ignores
the environment variable, clone-local selector, and machine fingerprint; it does
not claim that this machine is a registered host. Combining it with any `--env`
value, including `current`, is an error. Default selection remains fail-closed.

Shared scope excludes every per-environment subtree before discovery and refuses
environment note bodies at the normal confined-read boundary. This includes
unmatched registrations, invalid manifests, and unregistered or malformed
directory names. The shared `10_Agents/environments/README.md` landing note
remains in scope. Query operations need no manifest reads; `validate` still
checks all manifest envelopes as documented above.

Supported commands are `list`, `search`, `links`, `tags`, `show`, `read`, `recent`,
`report`, `curate`, `tasks`, `validate`, `context`, `config`, `projects`,
`migrate-links` (preview/check only), and the owning shared generators `index`,
`bootstrap`, `artifacts`, `aymt`, and `home`. Shared-only Home/AYMT records the
explicit `shared-only` state with no selected slug or environment freshness.
Environment operations, notifications, installation, and unsupported commands
refuse the flag. Content scope does not grant write authority: permitted owning
generator writes still follow the write-authority contract and their existing safeguards.

Python callers can wrap compound read/query operations in
`with brain.shared_corpus_scope():`. The scope covers `walk_corpus` and confined
note reads, rejects an explicit per-environment corpus override, and restores the
previous context even after exceptions. This is the supported scope for
shared-corpus repository tests and foreign-clone/CI queries; do not select a
registered host merely to make those tests pass.

## 20.4 Commands and migration

- `brain env detect` prints the selected slug/source plus SHA-256 evidence for
  creating or refreshing a manifest. JSON never includes raw identity.
- `brain env list` prints metadata-only records and remains usable when current
  matching fails, so an owner can diagnose the selector safely.
- `brain env migrate <source> <target>` is preview-only. It enumerates exact
  vault-relative moves for an unregistered legacy directory, refuses symlinks,
  registered sources, invalid slugs, any existing target directory, and
  collisions, and performs zero writes. Traversal binds source directories and
  regular files without following links; any identity change discards the
  entire in-memory preview before a row can be emitted.
  The owner applies the reviewed move with version control, then creates the
  target manifest/landing note through orientation.

`agent-orientation` owns manifest creation/refresh and migration handoff.
Bootstrap, maintenance, automation, sync reports, generated integrations, and
personal-data tools must resolve the current environment first. Sync treats all
environment directories and `.second-brain/` as owner-local: non-current
contents are neither read nor serialized, and overlays are never proposed for
commit.
