---
name: agent-orientation
description: Discover the high-value context sources available in this adopter's environment (chat, email, calendar, transcripts, task trackers) and generate the vault tooling to access them. Produces a structured inventory note under 10_Agents/environments/<env-slug>/ following the required output contract. Use once per new environment, or when the owner's toolchain changes.
title: "Skill: Agent Orientation"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-11
expires: 2027-08-11
---

# Agent Orientation

**CODE stage:** Onboarding.

Map what this environment can reach, agree on what's worth ingesting, and generate the access layer — the vault reaches outward from here.

Orientation is not open-ended discovery: it produces a **structured inventory note** with the required sections defined in [[#Required output contract]] below. Infer as much as possible from the environment itself (installed CLIs, MCP/connector lists, config files); interview the owner only for what can't be observed.

## Interface ranking ladder (apply to every inventory entry)

When a source needs access tooling, prefer in this order (PRD §19 M7, decision #9; extended per #13):

1. **Environment-specific custom tooling** — a CLI script or MCP integration built for this environment
2. **The vendor's first-party CLI** (e.g. `gh`, `gcloud`, `m365`, mail/calendar CLIs)
3. **A first-party MCP server / connector**
4. **Vendor API, wrapped in a generated script/CLI** — when rungs 1–3 don't exist but the service has an API. Raw API access must be **wrapped** in a generated tool (the M7 pattern), never left as ad-hoc calls agents improvise per session: wrapping keeps the interface documented, reusable, auditable, and maintainable by `self-maintenance`, and gives credential handling one place to live.
5. **Browser automation** — explicit last resort; gated by the environment's browser availability (see the contract's environment-capabilities section)
6. **None** — recorded explicitly. "None identified" is a valid, recorded outcome — never an omission.

**Credentials never enter the repo** (PRD §16.2): auth lives in local CLI sessions, keychains, or environment variables — a generated tool reads `$SOURCE_TOKEN`, it never contains one. Refuse to write any secret into a committed file.

## Required output contract

Orientation **must** produce one inventory note containing all of the following sections. Empty findings are recorded, not skipped.

### 1. Solution inventory

Per category, the solution in use **and how an agent can interface with it**, ranked on the ladder above. Categories:

| Category | Examples to distinguish |
|---|---|
| Version control | GitHub, GitLab, Bitbucket, other/self-hosted |
| Email | Gmail, Outlook/Exchange, other |
| Chat | Microsoft Teams, Slack, Google Chat, other |
| Cloud storage / drive | Google Drive, OneDrive/SharePoint, Dropbox, other |
| Calendar | Google Calendar, Outlook, other |
| Task tracking | Jira, Linear, Asana, Todoist, GitHub Projects/Issues, none (vault-native only) |
| Artifact sharing / hosting | Figma; render hosting (GitHub Pages, harness-native artifacts, wiki/Notion); none (local only) — include a **sharing-audience note** (personal-only vs shareable-with-team) |
| Automation platforms | n8n (self-hosted = environment fact), Zapier, Make, none |
| Other high-use tools | marketplaces, CRM systems, anything the owner touches daily |

Per entry: solution name → best available ladder rung(s) → or **none**, with evidence (which CLI/MCP/connector was actually observed).

### 2. Harness introspection

- **The current harness** — which harness the orienting agent itself runs in, mapped to the PRD §8.3 support tier, plus a **capability nuance profile**: does-it-support-X checks (Agent Skills and discovery paths, MCP servers, hooks and lifecycle events, scheduled/recurring runs, subagents, memory-file imports, ignore/privacy mechanisms, network policy in the current surface), unique tools this harness exposes that others don't (in-thread interactive prompts, artifact rendering, background monitoring, PR subscriptions), and **constraints as first-class facts** (what the harness cannot do here).
- **Other harnesses detected** on the machine (e.g. `claude`, `codex`, `copilot`, `cursor` CLIs, VS Code + extensions), each mapped to the PRD §8.3 tier and its `10_Agents/harnesses/<name>/wiring.md` doc.
- Wiring docs are the *static, template-shipped* knowledge; introspection is the *live check*. Verify static claims against the running harness and record **deltas in the environment inventory** — never edit canonical wiring docs mid-orientation.

### 3. Ecosystem identification

- Which agent products the owner actually uses (Claude Code? Copilot? both?).
- Which **productivity suite** anchors their work (Microsoft 365, Google Workspace, other). Detect this **first** and use it as the prior for the email/chat/storage/calendar entries above.
- How agents reach that ecosystem: available CLIs, MCP servers/connectors already configured, or nothing yet.

### 4. Environment capabilities & policy

Environment facts (not harness or vault facts):

- **Computer use (CUA):** is a screen/desktop-control surface available? This changes what the browser rung can reach and whether GUI-only tools are automatable at all.
- **Browser availability:** headless (Playwright/Chromium preinstalled), full GUI browser, or none — and with what session/auth state. Gates ladder rung 5.
- **Permission envelope:** may agents install third-party packages (npm/PyPI, restricted mirrors)? Allowed extension/plugin/tool provenance (corporate allowlists, MDM)? Network egress policy (proxied, allowlisted, open)? Sandbox/approval gates on shell, file, or credential access? Where policy is **unknown/unverifiable, record that** and treat it as "ask the owner before acting." Generated tools and `recommended-automations` proposals must stay inside this envelope.

## Where the inventory lands

One inventory note **per environment**, under `10_Agents/environments/<env-slug>/` (e.g. `10_Agents/environments/work-macbook/orientation-inventory.md`). See [[10_Agents/environments/README]] for the convention: environment-scoped, **never bootstrap-linked**, and each note opens with a self-guarding applicability preamble naming its environment. Full environment-scoping machinery (fingerprinting, automatic detection) is deferred to #15 — this is the minimal landing convention only.

## Inventory note template

```markdown
---
title: "Orientation Inventory: <env-slug>"
tags:
  - type/log
  - audience/agent
  - workflow/draft
updated: <YYYY-MM-DD>
expires: <YYYY-MM-DD +3 months — wiring/product facts TTL per conventions § Expiration>
author: <harness-id>
session: <session-or-pr-ref>
---

# Orientation Inventory: <env-slug>

> **Applies only to the `<env-slug>` environment.** Agents in any other
> environment must ignore this note. This note is never bootstrap-linked.

## Solution inventory

| Category | Solution | Interface (ladder rung) | Evidence / notes |
|---|---|---|---|
| Version control | <solution-or-none> | <rung> | <observed-how> |
| Email | <solution-or-none> | <rung> | <observed-how> |
| Chat | <solution-or-none> | <rung> | <observed-how> |
| Cloud storage / drive | <solution-or-none> | <rung> | <observed-how> |
| Calendar | <solution-or-none> | <rung> | <observed-how> |
| Task tracking | <solution-or-none> | <rung> | <observed-how> |
| Artifact sharing / hosting | <solution-or-none> | <rung> | <sharing-audience: personal-only|team> |
| Automation platforms | <solution-or-none> | <rung> | <observed-how> |
| Other high-use tools | <solution-or-none> | <rung> | <observed-how> |

## Harness introspection

- Current harness: <name> (PRD §8.3 tier <tier>) — wiring: 10_Agents/harnesses/<name>/wiring.md
- Capability profile: <supports-X checks, unique tools, constraints>
- Deltas vs wiring doc: <deltas-or-none>
- Other harnesses detected: <list-with-tiers-or-none>

## Ecosystem identification

- Productivity suite: <M365 | Google Workspace | other | unknown>
- Agent products in use: <list>
- Reach: <CLIs / MCP servers / connectors configured, or none yet>

## Environment capabilities & policy

- Computer use (CUA): <available | none | unknown>
- Browser: <headless | GUI | none>, auth state: <logged-in-as | none>
- Permission envelope: <packages / provenance / egress / sandbox gates; unknown = ask owner>

## Owner decisions

- <adopted sources, priorities, exclusions>
```

## Steps

1. **Detect the ecosystem first** (contract §3) — the productivity suite is the prior for most solution-inventory answers.
2. **Introspect the harness and environment** (contract §2 and §4): harness-provided tools and MCP servers/connectors, CLIs on PATH, schedulers (see `recommended-automations`), the wiring doc in `10_Agents/harnesses/<name>/wiring.md`, browser/CUA availability, and the permission envelope.
3. **Fill the solution inventory** (contract §1) per category, ranking each entry on the ladder. Record "none" explicitly.
4. **Interview the owner** for what can't be observed: which sources carry real context, per-source value, sensitivity (some sources shouldn't enter the vault at all — PRD §16.2), and desired freshness. Source priorities are the owner's call, decided here.
5. **Write the inventory note** to `10_Agents/environments/<env-slug>/orientation-inventory.md` using the template above (`workflow/draft`; the self-guarding preamble is mandatory). If the environment directory doesn't exist yet, create it with the owner's chosen slug.
6. **Generate the access layer for each adopted source:**
   - **Tooling** under `10_Agents/tools/<source>/` — a script (stdlib-first, config via env vars) where the rung is a CLI or wrapped API; an access doc naming the exact harness tools where the rung is MCP/connector.
   - **A paired skill** at `10_Agents/skills/<source>-capture/SKILL.md` describing when and how to pull from the source and capture into the vault **via the `inbox-capture` rules**.
   - Both tagged `workflow/draft` (agent-generated; the owner promotes — PRD §9.3). Everything must pass `python3 10_Agents/tools/brain/brain.py validate`.
7. **Hand off:** propose recurring flows to `recommended-automations` (it reads this environment's inventory note); register everything generated for `self-maintenance` audits (it probes the inventory's recorded sources on its cycle).

## References

- [[10_Agents/environments/README]] — the environment-scoped landing convention (minimal slice of #15)
- `10_Agents/harnesses/<name>/wiring.md` — what this harness can reach and how (static; verify live)
- `00_Meta/prd.md` §19 M7, §16.2, §8.3 — the ladder, the credentials rule, the harness tiers
