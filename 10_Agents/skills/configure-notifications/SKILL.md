---
name: configure-notifications
description: Configure, inspect, preview, and locally test push-only private owner notifications through brain's provider-neutral boundary. Use when the owner asks for operational alerts, notification setup, notification policy checks, or a safe fake/file test; real-provider test sends remain gated on the owner's provider and private-destination choice.
title: "Skill: Configure Notifications"
tags:
  - type/reference
  - audience/agent
  - workflow/canonical
updated: 2026-08-12
expires: 2027-08-11
---

# Configure Notifications

Configure operational notifications without turning the vault into a messaging client. The shipped path is push-only: `fake` previews and `file` deliveries work locally; provider-specific payload formatting exists for review, but real-provider test sends and delivery do not.

## Guardrails

- Require a selected environment, an owner-named private destination, `--private-destination-ack`, and explicit category opt-ins. Stop on ambiguity.
- Never send vault prose, credentials, absolute paths, provider errors, tracking URLs, or `restricted/private` content. Notifications carry only the strict operational envelope in the [brain spec](../../tools/brain/SPEC.md) §26.
- Never pass a secret value on the command line or write one to the vault. For a future real provider, record only the uppercase environment-variable name with `--secret-env`.
- Treat setup and delivery as persistence. Let `brain notify` run the mandatory remote-safety guard immediately before writing; do not bypass a block or unknown result.
- Do not add callbacks, reply/mutation actions, inbound webhooks, or Outbox content. Provider buttons may only open links that passed the central safe-link validator. This skill's narrow exception covers only its ignored environment overlay and an explicitly approved local file test.

## Workflow

1. Resolve the environment with `brain env detect --json`. Continue only when the result is selected.
2. Ask the owner for the provider, private destination label, enabled categories, quiet hours/timezone, hourly rate, and dedupe window. Categories are `automation`, `inbox-review`, `maintenance`, `pr-review`, and `validation`; all default off.
3. Configure a shippable local path. For example:

   ```text
   brain notify --setup --provider file --destination-label "Private local notification test" --private-destination-ack --enable-category validation --quiet-start 22:00 --quiet-end 07:00 --timezone America/New_York --rate-limit 6 --dedupe-hours 24 --json
   ```

   Before setup, the selected environment overlay directory must already exist and be owned by the current user. Use `fake` for preview-only evaluation. Repeat `--enable-category` and `--allow-https-host` as needed. Setup writes the ignored mode-`0600` `.second-brain/environments/<slug>/notifications.json`; a safe update or interrupted write may also retain authenticated ignored `.notifications.json.{notify-claim,migrate-{old,new}-*}` generation/recovery evidence. It sends nothing.
4. Run `brain notify --check --json`. Confirm the destination is private, only intended categories are enabled, and `testSendRequired` is false for the local path.
5. Prepare a version-1 JSON envelope and preview it with `brain notify --input PATH --json` or `brain notify --input - --json`. Preview is the default no-write path. Review the normalized envelope, provider payload, policy reason codes, and `writesPerformed: false`.
6. For an owner-approved file test only, run:

   ```text
   brain notify --input PATH --deliver-file --approve-private-send --json
   ```

   Use `--output PATH` only for a new file under the system temporary directory and outside the repository. Otherwise first create and review a current-user-owned mode-`0700` `notification-output/` directory in the selected overlay outside this transaction; the tool creates a private file there but never creates or repairs the directory. Never overwrite or reuse an occupied path.
   If delivery reports a safe failure, do not infer success and do not resend automatically. The tool reserves the dedupe state before publishing any default or explicit-temporary output, so concurrent attempts serialize and an output failure remains at-most-once for the configured dedupe window. It deliberately retains installed state, any created private output, and authenticated ignored `.notification-state.json.{notify-claim,migrate-{old,new}-*}` evidence needed for safe recovery; inspect that evidence manually and choose whether to wait, remove confirmed-obsolete generations, or use a new owner-approved dedupe key.
   Transaction generations are capped at 32 files and 2 MiB for each canonical config/state family. At the cap, stop scheduled notification runs; inspect the ignored mode-`0600` exact-prefix generations, preserve anything uncertain, and delete only owner-confirmed obsolete generations before retrying.
7. Re-run `brain notify --check --json` and report the provider, enabled categories, policy outcome, and whether a local test file was created. Do not quote notification payload text in the report.

## Real-provider gate

If the owner chooses `slack`, `google-chat`, or `teams`, record only their approved private destination label and secret environment-variable name. Explain that the current implementation can validate and format a provider payload but has no real transport or test-send implementation. Do not claim issue #21 resolved, do not attempt HTTP delivery, and leave the final test-send gate open until the owner selects and verifies the private destination.

If `brain` is not installed, replace `brain` with `./brain` on POSIX, `brain.cmd` on Windows, or `python3 10_Agents/tools/brain/brain.py` as the universal fallback.
