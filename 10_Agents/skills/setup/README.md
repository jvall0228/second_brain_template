---
title: "Setup Skills"
tags:
  - type/meta
  - audience/agent
  - audience/human
updated: 2026-09-01
expires: 2027-08-11
---

# Setup Skills

One-time skills that set the vault up for an owner, a harness, or a machine. They are grouped here so the everyday [catalog](../README.md) stays flat; the generated harness adapters still expose each by its own name (`.agents/skills/<name>/`, `.claude/skills/<name>/`), so invocation is unchanged.

| Skill | Does | Run when |
|-------|------|----------|
| [onboard-owner](onboard-owner/SKILL.md) | Guided first-run for a new vault owner: teach by doing, fill the profile, orchestrate the other setup skills | First run of a freshly adopted vault, or to resume an unfinished onboarding |
| [onboard-harness](onboard-harness/SKILL.md) | Verify the repository-local skill adapters and harness wiring; optionally preview or apply a user-global install | Setting up a new harness, or re-syncing / uninstalling prior global wiring |
| [agent-orientation](agent-orientation/SKILL.md) | Discover the context sources reachable from this environment and generate access tooling and capture skills | Once per new environment, or when the toolchain changes |

A group directory holds only skill directories and this README; `brain validate` treats each nested `SKILL.md` directory as the skill (spec §10.2).

## Related

- [Agent Skills](../README.md) — the full catalog and the cadence table
