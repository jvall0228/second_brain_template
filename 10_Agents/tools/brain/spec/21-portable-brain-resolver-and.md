---
title: "brain Spec §21 — Portable `brain` resolver and installer"
tags:
  - type/reference
  - audience/agent
  - audience/human
  - topic/software
  - workflow/canonical
updated: 2026-09-01
expires: 2027-08-11
---

# 21. Portable `brain` resolver and installer

*Section 21 of the [`brain` spec](../SPEC.md); section numbers are stable and `§N.x` references across the spec point at these files.*

## 21.1 Repository launchers

The tracked root `brain` is a POSIX `sh` resolver; `brain.cmd` is its Windows
`cmd.exe` counterpart. They are location-independent copies: neither embeds the
checkout that supplied it. Resolution precedence is one CLI `--vault PATH` (or
`--vault=PATH`) > `BRAIN_VAULT` > the nearest ancestor of the physical CWD that
contains both a regular `AGENTS.md` and
`10_Agents/tools/brain/brain.py`. Missing values, repeated CLI overrides,
invalid roots, symlinked markers/tools, and no ancestor match are rejected
without printing the candidate path. A higher-precedence invalid input never
falls through. This gives nested vaults nearest-root behavior and keeps sibling
forks isolated. The Windows resolver uses `cmd.exe`'s built-in file-attribute
expansion for every trusted component and fails closed if attributes cannot be
verified; it does not depend on optional `fsutil` behavior.

After resolution, the launcher invokes that checkout's Python 3 tool with the
original argument vector. It does not capture or transform stdout/stderr and
returns the exact child exit status. POSIX requires `python3` and returns 127
when it is unavailable. Windows prefers `py -3`, then `python3`, then `python`,
and forwards `%ERRORLEVEL%`. Paths containing spaces and Unicode are quoted;
the launchers never evaluate arguments, source shell files, honor a `PYTHON`
override, or modify the environment.

## 21.2 Managed PATH installation

`brain install` is preview-only by default. It selects the first existing,
absolute, non-symlinked, writable directory in `PATH`; `--target DIRECTORY`
selects another existing writable directory explicitly. It never creates a PATH
directory or edits shell/profile/registry configuration. `--apply` copies the
platform launcher with a final-component compare-and-swap. `--doctor` is
read-only. `--uninstall` previews;
`--uninstall --apply` removes only the recognized managed launcher.

Ownership lives in a version-1 external manifest: POSIX defaults to
`$XDG_STATE_HOME/second-brain/brain-install.json` or
`~/.local/state/second-brain/brain-install.json`; Windows defaults under
`%LOCALAPPDATA%\second-brain`. `--state-file` or `BRAIN_INSTALL_STATE` may
override it with an absolute path. The manifest is outside the vault and stores
one artifact per platform: absolute target, platform, and installed SHA-256.
Install output previews the exact target and manifest paths. Unknown schemas,
foreign shapes, symlinked state/targets, targets inside the vault, stale hashes,
and a requested target different from the recorded target are refusals.

An absent target or a byte-identical current launcher is safe to record. A
different target is replaceable only when its digest matches this manifest's
recorded digest. POSIX apply publishes absent files with create-if-absent and
replaces existing files with an atomic exchange whose displaced object is
digest-verified before removal. POSIX uninstall first moves the final component
to a no-replace quarantine name and verifies it there. Windows holds every
verified non-reparse parent-chain handle without delete sharing and performs
create/open/delete through a bound final handle; the digest is checked on that
handle before mutation. If manifest update fails after a target mutation, the
old target is restored (or the new target removed). Uninstall likewise refuses
drift and restores a removed target if manifest cleanup fails. Platforms without
the required parent-bound mutation primitives fail closed. State directories
created for an attempted install are identity-bound and removed in reverse order
on rollback, restoring the pre-transaction directory state. A `KeyboardInterrupt` during target mutation or
before the ownership-manifest commit rolls the mutation back before propagating;
an already committed target/manifest pair remains consistent. Preview, doctor,
and refused operations make zero writes. Tests use fake PATH/state/home
directories exclusively.

## 21.3 Host capability boundary

The current official Codex plugin manifest schema does not document a `bin` or
executable-export field. This repository therefore does not invent plugin
metadata; project and managed PATH launchers are the supported surfaces. Revisit
plugin exposure only after an official host schema documents it and an
end-to-end compatibility test passes.
