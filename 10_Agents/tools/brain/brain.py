#!/usr/bin/env python3
"""brain — vault index CLI.

Structured, queryable access to the vault for agents and humans.
Behavior is governed by spec.md in this directory (canonical); section
references below (§n) point there. Stdlib-only, Python 3.10+.

Usage: ./brain <command> [options]
Commands: index, list, search, links, migrate-links, aymt, home, artifacts, notify, tags, show, recent,
          validate, curate, context, config, report, tasks, embed,
          remote-safety, env
"""

from __future__ import annotations

import argparse
import calendar
import ctypes
import hashlib
import html
import importlib.util
import json
import math
import os
import posixpath
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, unquote_to_bytes, urlsplit

SCHEMA_VERSION = 2
LINK_MIGRATION_SCHEMA_VERSION = 1
LINK_MIGRATION_JOURNAL_RELPATH = ".brain-link-migration.json"
INDEX_RELPATH = "10_Agents/tools/brain/vault-index.json"
AYMT_RELPATH = "00_Meta/AYMT.md"
AYMT_SCHEMA_VERSION = 1
AYMT_MARKER = "<!-- generated-by: brain aymt v1; do not edit -->"
HOME_RELPATH = "00_Meta/HOME.md"
HOME_SCHEMA_VERSION = 1
HOME_MARKER = "<!-- generated-by: brain home v1; do not edit -->"
HOME_FIELD_LIMIT = 240
HOME_TASK_CAP = 5
HOME_ACTIVE_CAP = 8
AYMT_SECTION_CAPS = {"do-next": 3, "unblock-or-decide": 2, "keep-warm": 2}
AYMT_FIELD_LIMIT = 240
AYMT_SOURCE_LIMIT = 3
AYMT_GITHUB_MAX_BYTES = 64 * 1024
AYMT_GITHUB_MAX_ISSUES = 100
ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_DIR_RELPATH = "08_Assets/artifacts"
ARTIFACT_OUTPUTS = (
    f"{ARTIFACT_DIR_RELPATH}/link-graph.html",
    f"{ARTIFACT_DIR_RELPATH}/health-dashboard.html",
    f"{ARTIFACT_DIR_RELPATH}/manifest.json",
)
ARTIFACT_GENERATOR = "brain-artifacts-v1"
ARTIFACT_HTML_MARKER = "<!-- generated-by: brain artifacts v1; do not edit -->"
ARTIFACT_MAX_NODES = 500
ARTIFACT_MAX_EDGES = 2_000
ARTIFACT_STATIC_LINK_CAP = 40
ARTIFACT_TEXT_LIMIT = 160
ADOPT_EXAMPLES_RELPATH = "10_Agents/tools/adopt_examples.json"
# §18.1 embeddings sidecar: gitignored, machine-local, pruned from the corpus
# exactly like the index file (constants for the rest of §17 sit with its code).
EMBED_RELPATH = "10_Agents/tools/brain/vault-embeddings.json"
# Any tool's test tree (fixture mini-vaults, secret-shaped test data) stays
# out of the corpus — mirrors run_tests.py's */tests/ discovery rule.
TOOL_TESTS_RE = re.compile(r"^10_Agents/tools/[^/]+/tests$")
CORE_FRAMEWORK_PATHS = {
    "conventions": "00_Meta/CONVENTIONS.md",
    "index": "00_Meta/INDEX.md",
    "changelog": "00_Meta/CHANGELOG.md",
    "prd": "00_Meta/PRD.md",
    "status": "00_Meta/STATUS.md",
    "now": "01_Profile/NOW.md",
    "preferences": "01_Profile/PREFERENCES.md",
    "defaults": "01_Profile/DEFAULTS.md",
    "identity": "01_Profile/IDENTITY.md",
    "work": "01_Profile/WORK.md",
    "tooling-stack": "01_Profile/TOOLING-STACK.md",
    "long-running-themes": "01_Profile/LONG-RUNNING-THEMES.md",
    "operating-rules": "10_Agents/docs/OPERATING-RULES.md",
    "task-patterns": "10_Agents/docs/TASK-PATTERNS.md",
}
CORE_FRAMEWORK_PATH_SET = frozenset(CORE_FRAMEWORK_PATHS.values())
CORE_FRAMEWORK_CASE = {path.casefold(): path for path in CORE_FRAMEWORK_PATH_SET}
CONVENTIONS_RELPATH = CORE_FRAMEWORK_PATHS["conventions"]

# ---------------------------------------------------------------------------
# §14 Curation tunables — the single place these numbers live.
# Policy prose: 00_Meta/CONVENTIONS.md § Expiration / § Bootstrap Context.

CURATE_MAX_LINES = 400
CURATE_MAX_BYTES = 20_000
CURATE_STALE_DAYS = 180
EXPIRES_CAP_DAYS = 366

# Events, not claims — never asked for an expires: date. 02_Inbox/ is exempt
# because capture is zero-friction (expires assigned at triage); 02_Outbox/
# because packets are ephemeral — their lifecycle is the archive path.
EXPIRES_EXEMPT_PREFIXES = (
    "02_Inbox/",
    "02_Outbox/",
    "03_Journal/",
    "07_Archives/",
    "09_Templates/",
    "10_Agents/solutions/",
)
EXPIRES_EXEMPT_PATHS = frozenset(
    {
        CORE_FRAMEWORK_PATHS["changelog"],
        CORE_FRAMEWORK_PATHS["status"],
        "CLAUDE.md",
    }
)
# type/* tag values whose notes are event records (a decision made on a date),
# not living claims — exempt from expires: wherever they live (e.g. a decision
# record under 04_Projects/). Journal/log types already sit in exempt dirs.
EXPIRES_EXEMPT_TYPE_TAGS = frozenset({"decision"})
ORPHAN_EXEMPT_PATHS = frozenset({"AGENTS.md", "CLAUDE.md", "README.md"})
OVERSIZED_EXEMPT_PATHS = frozenset({CORE_FRAMEWORK_PATHS["changelog"]})

# Gate for the validate-side curation warnings (missing-expires,
# expires-beyond-cap, oversized, bootstrap-budget). On since the one-time
# expires: backfill (2026-08-11); `brain curate` always reports regardless.
VALIDATE_CURATION_WARNINGS = True

# R20 bootstrap context budgets (bytes): measured 2026-08-11 sizes + ~50%
# headroom, rounded up. Total ties to the smallest harness project-doc cap.
# Portable Markdown paths and the exact artifact write lane add bytes to two
# bootstrap docs; issues #74/#23 raise only their per-file ceilings. Actual
# aggregate size remains below 32 KiB.
BOOTSTRAP_BUDGETS = {
    CORE_FRAMEWORK_PATHS["conventions"]: 12800,
    CORE_FRAMEWORK_PATHS["index"]: 4096,
    CORE_FRAMEWORK_PATHS["defaults"]: 2048,
    CORE_FRAMEWORK_PATHS["now"]: 2048,
    CORE_FRAMEWORK_PATHS["preferences"]: 3072,
    "AGENTS.md": 8832,
}
BOOTSTRAP_TOTAL_BUDGET = 32768

# §19 Remote safety. These values are part of the stable JSON/reason-code
# contract. Provider and git subprocess text never crosses the output boundary.
REMOTE_SAFETY_SCHEMA_VERSION = 1
REMOTE_SAFETY_GIT_TIMEOUT = 5
REMOTE_SAFETY_PROVIDER_TIMEOUT = 10
NO_PUSH_SENTINELS = frozenset({"disabled", "no_push", "no-push"})
GITHUB_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SCP_REMOTE_RE = re.compile(
    r"^(?:[^@/\s]+@)?(?P<host>[A-Za-z0-9.-]+):(?P<path>[^?#\s]+)$"
)

# §16 Health-report defaults — overridable per fork via the `report` config
# key (spec §15.3 / §16.4): report: → stale_days / inbox_days.
REPORT_STALE_ACTIVE_DAYS = 30
REPORT_INBOX_TRIAGE_DAYS = 14

# §20 Environment identity. Tracked manifests contain only hashed machine
# evidence. The selector and overlays are clone-local and gitignored.
ENVIRONMENT_SCHEMA_VERSION = 1
ENVIRONMENTS_RELPATH = "10_Agents/environments"
ENVIRONMENT_MANIFEST_NAME = "environment.json"
ENVIRONMENT_SELECTOR_RELPATH = ".second-brain/environment"
ENVIRONMENT_OVERLAYS_RELPATH = ".second-brain/environments"
ENVIRONMENT_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENVIRONMENT_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ENVIRONMENT_CLASS_VALUES = frozenset(
    {"desktop", "laptop", "server", "container", "cloud", "other"}
)
ENVIRONMENT_SECRET_KEY_RE = re.compile(
    r"(?i)(?:secret|token|password|passwd|credential|webhook|hostname|username|user|path|url)"
)


class EnvironmentSelectionError(RuntimeError):
    """Fail-closed environment selection with a stable, non-identifying code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"environment selection failed: {code}")


_ENVIRONMENT_UNSET = object()
_ACTIVE_ENVIRONMENT: object | str | None = _ENVIRONMENT_UNSET

# §21 Portable resolver installation. The manifest is deliberately outside
# the repository and records only artifacts this installer may later replace.
INSTALL_MANIFEST_SCHEMA_VERSION = 1
INSTALL_MANIFEST_ENV = "BRAIN_INSTALL_STATE"


# ---------------------------------------------------------------------------
# §19 Remote safety


class MetadataProviderError(RuntimeError):
    """A stable, already-redacted provider failure reason."""


class RemoteSafetyError(RuntimeError):
    """Raised before a personal-data connector when remote safety denies it."""

    def __init__(self, result: dict, reason: str | None = None):
        self.result = result
        safe_reason = reason or result["state"]
        codes = ",".join(result["reasonCodes"])
        super().__init__(f"remote safety denied: {safe_reason} ({codes})")


def normalize_push_url(url: str) -> dict:
    """Normalize one push URL without exposing it through the public result.

    The returned owner/repo/key fields are internal inputs to the provider.
    Callers that render or serialize must pass the record through
    ``public_remote_target``.
    """
    raw = url.strip()
    base = {
        "id": "target-redacted",
        "provider": "unknown",
        "summary": "<redacted>",
        "key": None,
        "owner": None,
        "repo": None,
    }
    if raw.casefold() in NO_PUSH_SENTINELS:
        return {**base, "disabled": True, "reasonCode": "push-disabled"}
    if not raw or any(ch in raw for ch in "\r\n\0"):
        return {**base, "disabled": False, "reasonCode": "malformed-push-url"}

    host: str | None = None
    path: str | None = None
    transport: str | None = None
    scp = SCP_REMOTE_RE.fullmatch(raw) if "://" not in raw else None
    if scp:
        host = scp.group("host")
        path = scp.group("path")
        transport = "ssh"
    else:
        try:
            parsed = urlsplit(raw)
            # Accessing .port validates malformed ports even though GitHub's
            # default provider does not need the value.
            port = parsed.port
        except ValueError:
            return {**base, "disabled": False, "reasonCode": "malformed-push-url"}
        transport = parsed.scheme.casefold()
        if not transport:
            return {**base, "disabled": False, "reasonCode": "malformed-push-url"}
        if transport not in {"https", "ssh"}:
            return {
                **base,
                "disabled": False,
                "reasonCode": "unsupported-push-transport",
            }
        if port is not None and port != {"https": 443, "ssh": 22}[transport]:
            return {
                **base,
                "disabled": False,
                "reasonCode": "nonstandard-push-port",
            }
        if parsed.query or parsed.fragment:
            return {**base, "disabled": False, "reasonCode": "malformed-push-url"}
        host = parsed.hostname
        path = parsed.path

    if not host or host.casefold() != "github.com":
        return {**base, "disabled": False, "reasonCode": "unsupported-push-host"}
    if not path or "%" in path:
        return {**base, "disabled": False, "reasonCode": "malformed-push-url"}
    parts = path.strip("/").split("/")
    if len(parts) != 2:
        return {**base, "disabled": False, "reasonCode": "malformed-push-url"}
    owner, repo = parts
    if repo.casefold().endswith(".git"):
        repo = repo[:-4]
    if (
        not owner
        or not repo
        or owner in {".", ".."}
        or repo in {".", ".."}
        or not GITHUB_COMPONENT_RE.fullmatch(owner)
        or not GITHUB_COMPONENT_RE.fullmatch(repo)
    ):
        return {**base, "disabled": False, "reasonCode": "malformed-push-url"}
    key = f"github.com/{owner.casefold()}/{repo.casefold()}"
    return {
        "id": "target-redacted",
        "provider": "github",
        "summary": "github.com/<redacted>",
        "key": key,
        "owner": owner,
        "repo": repo,
        "disabled": False,
        "reasonCode": None,
    }


def public_remote_target(target: dict) -> dict:
    """Return the only remote-target shape permitted at output boundaries."""
    row = {
        "id": target["id"],
        "provider": target["provider"],
        "repository": target["summary"],
    }
    if "state" in target:
        row["state"] = target["state"]
    codes = target.get("reasonCodes")
    if codes:
        row["reasonCodes"] = sorted(set(codes))
    elif target.get("reasonCode") and target["reasonCode"] != "push-disabled":
        row["reasonCodes"] = [target["reasonCode"]]
    else:
        row["reasonCodes"] = []
    return row


def _safe_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    # Prevent interactive auth and debug traces. Output is captured regardless,
    # but removing debug toggles also avoids side-channel writes by child tools.
    env["GH_PROMPT_DISABLED"] = "1"
    env["GH_HOST"] = "github.com"
    # Remote discovery must reflect repository-local config, not ambient
    # process or user/system config. In particular, Git's GIT_CONFIG_COUNT /
    # GIT_CONFIG_KEY_* / GIT_CONFIG_VALUE_* family can inject a replacement
    # push URL and hide the configured public destination. Clear every Git
    # control variable, then opt back into only the non-interactive flag and
    # explicit empty global/system config files. Local .git/config still loads.
    env.pop("GH_DEBUG", None)
    env.pop("GH_FORCE_TTY", None)
    for key in list(env):
        if key.startswith("GIT_"):
            env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    return env


def _ambient_git_subprocess_env() -> dict[str, str]:
    """Model this invocation's effective Git config without trace side effects."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    # Discovery is local and non-networked, but Git trace variables can write
    # repository/config details to attacker-chosen sinks. Preserve config,
    # HOME, and repository-selection variables because a later Git invocation
    # in this same environment will honor them; the local-only discovery pass
    # is unioned with this one so neither view can hide the other.
    unsafe_stdio = {
        "GIT_REDIRECT_STDIN",
        "GIT_REDIRECT_STDOUT",
        "GIT_REDIRECT_STDERR",
    }
    for key in list(env):
        if (
            key.startswith("GIT_TRACE")
            or key == "GIT_CURL_VERBOSE"
            or key in unsafe_stdio
        ):
            env.pop(key, None)
    return env


class GitHubMetadataProvider:
    """Injectable GitHub repository-metadata boundary (§19.2)."""

    def __init__(self, timeout: int = REMOTE_SAFETY_PROVIDER_TIMEOUT):
        self.timeout = timeout

    def __call__(self, owner: str, repo: str) -> dict:
        try:
            completed = subprocess.run(
                [
                    "gh",
                    "repo",
                    "view",
                    f"{owner}/{repo}",
                    "--json",
                    "visibility,isPrivate,isTemplate,templateRepository",
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout,
                env=_safe_subprocess_env(),
            )
        except FileNotFoundError:
            raise MetadataProviderError("provider-unavailable") from None
        except subprocess.TimeoutExpired:
            raise MetadataProviderError("provider-timeout") from None
        except (OSError, subprocess.CalledProcessError):
            raise MetadataProviderError("provider-query-failed") from None
        try:
            value = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError):
            raise MetadataProviderError("provider-response-invalid") from None
        if not isinstance(value, dict):
            raise MetadataProviderError("provider-response-invalid")
        return value


def _git_push_urls(root: Path) -> tuple[list[str], list[str]]:
    """Return effective push URLs and stable discovery reason codes."""
    command = ["git", "-C", str(root)]
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "capture_output": True,
        "text": True,
        "check": True,
        "timeout": REMOTE_SAFETY_GIT_TIMEOUT,
        "env": _safe_subprocess_env(),
    }
    try:
        inside = subprocess.run(
            command + ["rev-parse", "--is-inside-work-tree"], **kwargs
        )
    except FileNotFoundError:
        return [], ["git-unavailable"]
    except subprocess.TimeoutExpired:
        return [], ["push-url-enumeration-failed"]
    except (OSError, UnicodeError, subprocess.CalledProcessError):
        return [], ["not-git-repository"]
    if inside.stdout.strip() != "true":
        return [], ["not-git-repository"]

    # `--local` does not make an include local: a repository can name
    # `include.path = ~/...`, and Git expands that path through ambient HOME.
    # Such an include can replace a public push target with a private-looking
    # one (or the reverse) after the repository itself has been inspected.
    # Read the raw local config with includes disabled and fail closed on every
    # include/includeIf directive before asking Git for effective URLs.
    include_kwargs = dict(kwargs)
    include_kwargs["check"] = False
    try:
        include_result = subprocess.run(
            command
            + [
                "config",
                "--local",
                "--no-includes",
                "--name-only",
                "--get-regexp",
                r"^include.*\.path$",
            ],
            **include_kwargs,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return [], ["push-url-enumeration-failed"]
    if include_result.returncode not in (0, 1):
        return [], ["push-url-enumeration-failed"]
    if include_result.stdout.splitlines():
        return [], ["unsafe-local-config-include"]

    try:
        remote_result = subprocess.run(command + ["remote"], **kwargs)
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return [], ["push-url-enumeration-failed"]
    remotes = sorted(line for line in remote_result.stdout.splitlines() if line)
    urls: list[str] = []
    reasons: list[str] = []
    for remote in remotes:
        try:
            result = subprocess.run(
                command + ["remote", "get-url", "--push", "--all", remote],
                **kwargs,
            )
        except (OSError, UnicodeError, subprocess.SubprocessError):
            reasons.append("push-url-enumeration-failed")
            continue
        found = result.stdout.splitlines()
        if not found:
            reasons.append("push-url-enumeration-failed")
        else:
            urls.extend(found)

    # A real later `git push` also honors ambient global/system config, HOME,
    # url.* rewrites, and GIT_CONFIG_* controls. Ignoring that view permits a
    # local private target to be rewritten to public. Trusting it alone permits
    # the opposite substitution. Evaluate the union of the repository-local
    # view above and this invocation's ambient-effective view.
    ambient_kwargs = dict(kwargs)
    ambient_kwargs["env"] = _ambient_git_subprocess_env()
    try:
        ambient_inside = subprocess.run(
            command + ["rev-parse", "--is-inside-work-tree"], **ambient_kwargs
        )
        if ambient_inside.stdout.strip() != "true":
            reasons.append("ambient-push-url-enumeration-failed")
        else:
            ambient_remotes = subprocess.run(command + ["remote"], **ambient_kwargs)
            for remote in sorted(
                line for line in ambient_remotes.stdout.splitlines() if line
            ):
                result = subprocess.run(
                    command + ["remote", "get-url", "--push", "--all", remote],
                    **ambient_kwargs,
                )
                found = result.stdout.splitlines()
                if not found:
                    reasons.append("ambient-push-url-enumeration-failed")
                else:
                    urls.extend(found)
    except (OSError, UnicodeError, subprocess.SubprocessError):
        reasons.append("ambient-push-url-enumeration-failed")
    # The two discovery views commonly return the same strings. Deduplicate
    # exact raw values in memory before normalization; raw values and any
    # credential-bearing equality keys never cross the output boundary.
    return list(dict.fromkeys(urls)), sorted(set(reasons))


def _classify_github_metadata(metadata: dict) -> tuple[str, list[str]]:
    required = {"visibility", "isPrivate", "isTemplate", "templateRepository"}
    if not isinstance(metadata, dict) or not required.issubset(metadata):
        return "unknown", ["provider-response-invalid"]
    visibility = metadata["visibility"]
    private = metadata["isPrivate"]
    template = metadata["isTemplate"]
    template_repository = metadata["templateRepository"]
    if (
        not isinstance(visibility, str)
        or type(private) is not bool
        or type(template) is not bool
        or (template_repository is not None and not isinstance(template_repository, dict))
    ):
        return "unknown", ["provider-response-invalid"]
    visibility = visibility.upper()
    if template:
        return "block", ["repository-template"]
    if (visibility == "PRIVATE") != private:
        return "unknown", ["provider-response-inconsistent"]
    if private and visibility == "PRIVATE":
        return "pass", ["repository-private"]
    if visibility == "PUBLIC":
        return "block", ["repository-public"]
    if not private and visibility == "INTERNAL":
        return "block", ["repository-not-private"]
    return "unknown", ["provider-response-invalid"]


def evaluate_remote_safety(
    root: Path,
    metadata_provider=None,
    acknowledge_unknown: bool = False,
) -> dict:
    """Evaluate whether personal-data access is safe for this invocation."""
    provider = metadata_provider or GitHubMetadataProvider()
    urls, discovery_reasons = _git_push_urls(root)
    normalized: list[dict] = []
    for url in urls:
        target = normalize_push_url(url)
        if not target["disabled"]:
            normalized.append(target)

    # Deduplicate verified provider identities, while retaining every malformed
    # or unsupported target as a distinct fail-closed finding.
    unique: list[dict] = []
    seen_provider_keys: set[str] = set()
    for target in normalized:
        # Provider keys are safe only inside this process. Unknown targets stay
        # distinct so the evaluator truthfully accounts for every push URL;
        # neither raw URLs nor hashes derived from credentials reach output.
        if target["key"]:
            if target["key"] in seen_provider_keys:
                continue
            seen_provider_keys.add(target["key"])
        unique.append(target)
    targets = sorted(
        unique,
        key=lambda target: (
            target["key"] is None,
            target["key"] or "",
            target["reasonCode"] or "",
        ),
    )
    for number, target in enumerate(targets, start=1):
        target["id"] = f"target-{number:03d}"

    evaluated: list[dict] = []
    for target in targets:
        if target["reasonCode"]:
            evaluated.append(
                {**target, "state": "unknown", "reasonCodes": [target["reasonCode"]]}
            )
            continue
        try:
            metadata = provider(target["owner"], target["repo"])
            state, reasons = _classify_github_metadata(metadata)
        except MetadataProviderError as exc:
            code = str(exc)
            if code not in {
                "provider-query-failed",
                "provider-response-invalid",
                "provider-timeout",
                "provider-unavailable",
            }:
                code = "provider-query-failed"
            state, reasons = "unknown", [code]
        except Exception:
            # An injected provider is still an external boundary. Its exception
            # text may contain a URL, token, or local identity and is never emitted.
            state, reasons = "unknown", ["provider-query-failed"]
        evaluated.append({**target, "state": state, "reasonCodes": reasons})

    local_only = not evaluated and not discovery_reasons
    all_reasons = set(discovery_reasons)
    for target in evaluated:
        all_reasons.update(target["reasonCodes"])
    if local_only:
        verified_state = "pass"
        all_reasons.add("no-push-targets-local-only")
    elif discovery_reasons or any(t["state"] == "unknown" for t in evaluated):
        verified_state = "unknown"
    elif any(t["state"] == "block" for t in evaluated):
        verified_state = "block"
    else:
        verified_state = "pass"

    # A verified block has priority over unknown discovery/provider failures and
    # is never bypassable. Unknown acknowledgment is invocation-local only.
    if any(t["state"] == "block" for t in evaluated):
        verified_state = "block"
    unknown_acknowledged = verified_state == "unknown" and acknowledge_unknown
    state = "pass" if unknown_acknowledged else verified_state
    if unknown_acknowledged:
        all_reasons.add("unknown-acknowledged")
    personal_data_allowed = state == "pass"
    persistence_allowed = personal_data_allowed and not local_only
    return {
        "localOnly": local_only,
        "persistenceAllowed": persistence_allowed,
        "personalDataAllowed": personal_data_allowed,
        "reasonCodes": sorted(all_reasons),
        "schemaVersion": REMOTE_SAFETY_SCHEMA_VERSION,
        "state": state,
        "targets": [public_remote_target(t) for t in evaluated],
        "unknownAcknowledged": unknown_acknowledged,
        "verifiedState": verified_state,
    }


def require_remote_safety(
    root: Path,
    *,
    metadata_provider=None,
    acknowledge_unknown: bool = False,
    persist: bool = False,
) -> dict:
    """Fail before personal-data access or an unsafe persistence attempt."""
    result = evaluate_remote_safety(
        root,
        metadata_provider=metadata_provider,
        acknowledge_unknown=acknowledge_unknown,
    )
    if not result["personalDataAllowed"]:
        raise RemoteSafetyError(result)
    if persist and not result["persistenceAllowed"]:
        raise RemoteSafetyError(result, "persistence-not-allowed")
    return result


def guarded_personal_data_call(
    root: Path,
    connector,
    *connector_args,
    metadata_provider=None,
    acknowledge_unknown: bool = False,
    persist: bool = False,
    **connector_kwargs,
):
    """Reference wrapper proving the guard runs before the connector call."""
    require_remote_safety(
        root,
        metadata_provider=metadata_provider,
        acknowledge_unknown=acknowledge_unknown,
        persist=persist,
    )
    return connector(*connector_args, **connector_kwargs)


# ---------------------------------------------------------------------------
# §20 Environment identity and selection


def _valid_environment_slug(value: object) -> bool:
    return isinstance(value, str) and bool(ENVIRONMENT_SLUG_RE.fullmatch(value))


def _link_like_stat(info: os.stat_result) -> bool:
    """True for POSIX symlinks and Windows reparse-point path redirects."""
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def _stable_read_identity(info: os.stat_result) -> tuple[int, ...]:
    """Descriptor metadata that changes on truncate/rewrite during a read."""
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        stat.S_IMODE(info.st_mode),
        info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1_000_000_000)),
    )


def _read_nofollow_file(
    root: Path, relative: str, *, max_bytes: int | None = None
) -> tuple[bytes, os.stat_result]:
    """Read a regular vault file without following any child path redirect.

    On POSIX this walks from an open vault-directory descriptor using openat
    plus O_NOFOLLOW. The portable fallback snapshots every component, opens
    the final file, verifies its identity before reading, and rechecks the
    component chain afterward. Any race discards the bytes and fails closed.
    """
    parts = Path(relative).parts
    if (
        not parts
        or Path(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise OSError("unsafe vault-relative read")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    if nofollow and directory and os.open in getattr(os, "supports_dir_fd", set()):
        descriptors: list[int] = []
        try:
            current = os.open(root, os.O_RDONLY | directory | cloexec)
            descriptors.append(current)
            for part in parts[:-1]:
                current = os.open(
                    part,
                    os.O_RDONLY | directory | nofollow | cloexec,
                    dir_fd=current,
                )
                descriptors.append(current)
                if not stat.S_ISDIR(os.fstat(current).st_mode):
                    raise OSError("unsafe vault-relative read")
            final = os.open(
                parts[-1], os.O_RDONLY | nofollow | cloexec, dir_fd=current
            )
            descriptors.append(final)
            before_read = os.fstat(final)
            if not stat.S_ISREG(before_read.st_mode):
                raise OSError("unsafe vault-relative read")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(final, 64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise OSError("vault file exceeds safe read limit")
                chunks.append(chunk)
            after_read = os.fstat(final)
            if _stable_read_identity(before_read) != _stable_read_identity(after_read):
                raise OSError("vault file changed during read")
            return b"".join(chunks), after_read
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    # Windows and restricted Python builds: compare the pre-open lstat chain
    # to both the opened descriptor and a post-read lstat chain. Content is
    # not consumed until the final descriptor matches the expected file.
    paths: list[Path] = []
    snapshots: list[tuple[int, int, int]] = []
    current_path = root
    for index, part in enumerate(parts):
        current_path = current_path / part
        info = os.lstat(current_path)
        if _link_like_stat(info):
            raise OSError("unsafe vault-relative read")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise OSError("unsafe vault-relative read")
        paths.append(current_path)
        snapshots.append((info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)))
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | cloexec
    descriptor = os.open(paths[-1], flags)
    try:
        opened = os.fstat(descriptor)
        expected = snapshots[-1]
        actual = (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode))
        if actual != expected or not stat.S_ISREG(opened.st_mode):
            raise OSError("vault path changed during read")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                raise OSError("vault file exceeds safe read limit")
            chunks.append(chunk)
        after_read = os.fstat(descriptor)
        if _stable_read_identity(opened) != _stable_read_identity(after_read):
            raise OSError("vault file changed during read")
    finally:
        os.close(descriptor)
    for path, expected in zip(paths, snapshots):
        info = os.lstat(path)
        actual = (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
        if _link_like_stat(info) or actual != expected:
            raise OSError("vault path changed during read")
    return b"".join(chunks), after_read


def _read_nofollow_bytes(
    root: Path, relative: str, *, max_bytes: int | None = None
) -> bytes:
    """Compatibility wrapper for callers that need only authenticated bytes."""
    return _read_nofollow_file(root, relative, max_bytes=max_bytes)[0]


def _environment_slug_for_path(relative: str) -> str | None:
    prefix = ENVIRONMENTS_RELPATH + "/"
    if not relative.startswith(prefix):
        return None
    remainder = relative[len(prefix) :]
    if "/" not in remainder:
        return None
    return remainder.split("/", 1)[0]


def _read_vault_bytes(
    root: Path,
    relative: str,
    *,
    enforce_environment: bool = True,
    max_bytes: int | None = None,
) -> bytes:
    """Read a vault file, enforcing selected-environment confinement at open."""
    slug = _environment_slug_for_path(relative)
    if slug is None:
        return (root / relative).read_bytes()
    if not _valid_environment_slug(slug):
        raise OSError("unsafe environment path")
    if enforce_environment:
        try:
            selected = _environment_for_corpus(root)
        except EnvironmentSelectionError:
            raise OSError("current environment cannot be selected safely") from None
        if slug != selected:
            raise OSError("environment path is outside the selected corpus")
    return _read_nofollow_bytes(root, relative, max_bytes=max_bytes)


def _has_symlink_component(root: Path, relative: str) -> bool:
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _safe_environment_dir(root: Path, slug: str) -> Path:
    """Return an immediate environment directory without following a link."""
    if not _valid_environment_slug(slug):
        raise EnvironmentSelectionError("invalid-slug")
    base = root / ENVIRONMENTS_RELPATH
    candidate = base / slug
    try:
        if _has_symlink_component(root, f"{ENVIRONMENTS_RELPATH}/{slug}"):
            raise EnvironmentSelectionError("unsafe-environment-path")
        resolved_base = base.resolve()
        resolved_candidate = candidate.resolve(strict=False)
        resolved_candidate.relative_to(resolved_base)
    except (OSError, ValueError):
        raise EnvironmentSelectionError("unsafe-environment-path") from None
    return candidate


def _strong_native_identifier(value: bytes | str, *, uuid_shape: bool) -> bytes | None:
    """Normalize only platform-native, non-placeholder 128-bit identifiers."""
    try:
        text = value.decode("ascii") if isinstance(value, bytes) else value
    except UnicodeError:
        return None
    text = text.strip().lower()
    if uuid_shape:
        if not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32}",
            text,
        ):
            return None
        try:
            compact = uuid.UUID(text).hex
        except ValueError:
            return None
    else:
        if not re.fullmatch(r"[0-9a-f]{32}", text):
            return None
        compact = text
    placeholders = {
        "0" * 32,
        "f" * 32,
        "0123456789abcdef" * 2,
        "fedcba9876543210" * 2,
        "deadbeef" * 4,
    }
    # A valid machine identifier is 128 bits of opaque OS-generated material.
    # Very low symbol diversity is a fail-closed placeholder/weak-ID signal.
    if compact in placeholders or len(set(compact)) < 8:
        return None
    return compact.encode("ascii")


def machine_fingerprints() -> list[dict[str, str]]:
    """Return stable SHA-256 evidence; raw identity never leaves this function."""
    material: bytes | None = None
    source = "machine-v1"
    if sys.platform.startswith("linux"):
        for candidate in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
            try:
                if candidate.is_symlink():
                    continue
                raw = candidate.read_bytes().strip()
            except OSError:
                continue
            normalized = _strong_native_identifier(raw, uuid_shape=False)
            if normalized is not None:
                material = b"linux-machine-id-v1\0" + normalized
                break
    elif sys.platform == "darwin":
        try:
            proc = subprocess.run(
                ["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                check=False,
                env=_safe_subprocess_env(),
                timeout=5,
            )
            match = re.search(
                rb'"IOPlatformUUID"\s*=\s*"([0-9A-Fa-f-]{32,40})"',
                proc.stdout[:128 * 1024],
            )
            normalized = (
                _strong_native_identifier(match.group(1), uuid_shape=True)
                if match
                else None
            )
            if proc.returncode == 0 and normalized is not None:
                material = b"darwin-platform-uuid-v1\0" + normalized
        except (OSError, subprocess.SubprocessError):
            pass
    elif os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
            ) as key:
                raw, _kind = winreg.QueryValueEx(key, "MachineGuid")
            normalized = (
                _strong_native_identifier(raw, uuid_shape=True)
                if isinstance(raw, str)
                else None
            )
            if normalized is not None:
                material = b"windows-machine-guid-v1\0" + normalized
        except (ImportError, OSError):
            pass
    if material is None:
        # Hostnames and usernames are low entropy and dictionary-identifiable
        # even after hashing. Explicit selection is required when the OS does
        # not expose a high-entropy machine identifier.
        return []
    return [
        {
            "algorithm": "sha256",
            "digest": hashlib.sha256(material).hexdigest(),
            "source": source,
        }
    ]


def _manifest_finding(rule: str, message: str) -> dict:
    return {"rule": rule, "message": message}


def validate_environment_manifest(data: object, expected_slug: str) -> list[dict]:
    """Validate the complete tracked v1 manifest shape without echoing values."""
    findings: list[dict] = []
    if not isinstance(data, dict):
        return [_manifest_finding("environment-schema", "manifest must be an object")]
    allowed = {
        "schemaVersion",
        "slug",
        "class",
        "surfaces",
        "capabilities",
        "fingerprints",
        "freshness",
        "maintenance",
    }
    keys_are_strings = all(type(key) is str for key in data)
    unknown = set(data) - allowed if keys_are_strings else set()
    if not keys_are_strings or unknown:
        findings.append(
            _manifest_finding(
                "environment-schema",
                "manifest has unknown keys (names suppressed at the privacy boundary)",
            )
        )
    version = data.get("schemaVersion")
    if type(version) is not int or version != ENVIRONMENT_SCHEMA_VERSION:
        findings.append(
            _manifest_finding(
                "environment-schema-version",
                f"schemaVersion must be {ENVIRONMENT_SCHEMA_VERSION}",
            )
        )
    slug = data.get("slug")
    if not _valid_environment_slug(slug) or slug != expected_slug:
        findings.append(
            _manifest_finding(
                "environment-slug",
                "slug must be kebab-case and equal its immediate directory name",
            )
        )
    environment_class = data.get("class")
    if (
        type(environment_class) is not str
        or environment_class not in ENVIRONMENT_CLASS_VALUES
    ):
        findings.append(
            _manifest_finding(
                "environment-class",
                "class must be desktop, laptop, server, container, cloud, or other",
            )
        )
    surfaces = data.get("surfaces")
    if (
        not isinstance(surfaces, list)
        or not all(type(item) is str and _valid_environment_slug(item) for item in surfaces)
        or len(set(surfaces)) != len(surfaces)
        or surfaces != sorted(surfaces)
    ):
        findings.append(
            _manifest_finding(
                "environment-surfaces",
                "surfaces must be a sorted unique list of kebab-case identifiers",
            )
        )
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict) or not all(
        type(key) is str and _valid_environment_slug(key) and type(value) is bool
        for key, value in capabilities.items()
    ) or (isinstance(capabilities, dict) and list(capabilities) != sorted(capabilities)):
        findings.append(
            _manifest_finding(
                "environment-capabilities",
                "capabilities must map kebab-case non-secret names to booleans",
            )
        )
    elif any(ENVIRONMENT_SECRET_KEY_RE.search(key) for key in capabilities):
        findings.append(
            _manifest_finding(
                "environment-private-key",
                "capability names must not describe identity, locations, credentials, or endpoints",
            )
        )
    fingerprints = data.get("fingerprints")
    if not isinstance(fingerprints, list):
        findings.append(
            _manifest_finding(
                "environment-fingerprints", "fingerprints must be a list"
            )
        )
    else:
        seen: set[tuple[str, str, str]] = set()
        for row in fingerprints:
            if not isinstance(row, dict) or set(row) != {
                "algorithm",
                "digest",
                "source",
            }:
                findings.append(
                    _manifest_finding(
                        "environment-fingerprints",
                        "each fingerprint must contain only algorithm, digest, and source",
                    )
                )
                continue
            algorithm = row.get("algorithm")
            digest = row.get("digest")
            source = row.get("source")
            if (
                type(algorithm) is not str
                or type(digest) is not str
                or type(source) is not str
                or algorithm != "sha256"
                or not ENVIRONMENT_DIGEST_RE.fullmatch(digest)
                or source != "machine-v1"
            ):
                findings.append(
                    _manifest_finding(
                        "environment-fingerprints",
                        "fingerprints require a SHA-256 digest and a supported generic source",
                    )
                )
                continue
            key = (algorithm, digest, source)
            if key in seen:
                findings.append(
                    _manifest_finding(
                        "environment-fingerprints", "duplicate fingerprint record"
                    )
                )
            else:
                seen.add(key)
    freshness = data.get("freshness")
    if not isinstance(freshness, dict) or set(freshness) != {
        "checkedAt",
        "expiresAt",
    }:
        findings.append(
            _manifest_finding(
                "environment-freshness",
                "freshness must contain only checkedAt and expiresAt",
            )
        )
    else:
        checked = iso_date(freshness.get("checkedAt"))
        expires = iso_date(freshness.get("expiresAt"))
        if checked is None or expires is None or expires < checked:
            findings.append(
                _manifest_finding(
                    "environment-freshness", "freshness dates must be real and ordered"
                )
            )
    maintenance = data.get("maintenance")
    if not isinstance(maintenance, dict) or set(maintenance) != {
        "inventory",
        "ownerReviewRequired",
    }:
        findings.append(
            _manifest_finding(
                "environment-maintenance",
                "maintenance must contain only inventory and ownerReviewRequired",
            )
        )
    elif (
        maintenance.get("inventory") != "orientation-inventory.md"
        or maintenance.get("ownerReviewRequired") is not True
    ):
        findings.append(
            _manifest_finding(
                "environment-maintenance",
                "maintenance requires the local inventory filename and owner review",
            )
        )
    return findings


def load_environment_manifests(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Load only immediate, non-symlinked environment directories."""
    base = root / ENVIRONMENTS_RELPATH
    manifests: dict[str, dict] = {}
    findings: list[dict] = []
    if _has_symlink_component(root, ENVIRONMENTS_RELPATH):
        return manifests, [
            {
                "path": ENVIRONMENTS_RELPATH + "/",
                **_manifest_finding(
                    "environment-unsafe-path",
                    "environments root must be a real directory inside the vault",
                ),
            }
        ]
    try:
        entries = sorted(os.scandir(base), key=lambda item: item.name)
    except OSError:
        return manifests, findings
    invalid_ordinal = 0
    for entry in entries:
        if entry.name.startswith(".") or entry.name == "README.md":
            continue
        valid_entry_name = _valid_environment_slug(entry.name)
        if not valid_entry_name:
            invalid_ordinal += 1
        diagnostic_name = (
            entry.name if valid_entry_name else f"<invalid-entry-{invalid_ordinal:03d}>"
        )
        if entry.is_symlink():
            findings.append(
                {
                    "path": f"{ENVIRONMENTS_RELPATH}/{diagnostic_name}/",
                    **_manifest_finding(
                        "environment-unsafe-path",
                        "environment entries must not be symlinks",
                    ),
                }
            )
            continue
        if not entry.is_dir(follow_symlinks=False):
            continue
        slug = entry.name
        rel = f"{ENVIRONMENTS_RELPATH}/{diagnostic_name}/{ENVIRONMENT_MANIFEST_NAME}"
        if not _valid_environment_slug(slug):
            findings.append(
                {
                    "path": rel,
                    **_manifest_finding(
                        "environment-slug", "environment directory must be kebab-case"
                    ),
                }
            )
            continue
        manifest_path = Path(entry.path) / ENVIRONMENT_MANIFEST_NAME
        if manifest_path.is_symlink():
            findings.append(
                {
                    "path": rel,
                    **_manifest_finding(
                        "environment-unsafe-path", "manifest must not be a symlink"
                    ),
                }
            )
            continue
        try:
            raw = _read_vault_bytes(
                root, rel, enforce_environment=False, max_bytes=64 * 1024
            )
            data = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            findings.append(
                {
                    "path": rel,
                    **_manifest_finding(
                        "environment-manifest-unreadable",
                        "manifest must be readable UTF-8 JSON under 64 KiB",
                    ),
                }
            )
            continue
        row_findings = validate_environment_manifest(data, slug)
        for dirpath, dirnames, filenames in os.walk(entry.path, followlinks=False):
            unsafe = [
                name
                for name in [*dirnames, *filenames]
                if (Path(dirpath) / name).is_symlink()
            ]
            if unsafe:
                row_findings.append(
                    _manifest_finding(
                        "environment-unsafe-path",
                        "environment contents must not contain symlinks",
                    )
                )
                break
        findings.extend({"path": rel, **finding} for finding in row_findings)
        if not row_findings:
            manifests[slug] = data
    return manifests, findings


def _read_environment_selector(root: Path) -> str | None:
    selector = root / ENVIRONMENT_SELECTOR_RELPATH
    if _has_symlink_component(root, ".second-brain"):
        raise EnvironmentSelectionError("unsafe-selector-parent")
    if not selector.exists() and not selector.is_symlink():
        return None
    if selector.is_symlink():
        raise EnvironmentSelectionError("unsafe-selector")
    try:
        raw = _read_nofollow_bytes(root, ENVIRONMENT_SELECTOR_RELPATH, max_bytes=128)
    except OSError:
        raise EnvironmentSelectionError("selector-unreadable") from None
    if len(raw) > 128 or b"\0" in raw:
        raise EnvironmentSelectionError("selector-invalid")
    try:
        value = raw.decode("utf-8").strip()
    except UnicodeError:
        raise EnvironmentSelectionError("selector-invalid") from None
    if not _valid_environment_slug(value):
        raise EnvironmentSelectionError("selector-invalid")
    return value


def select_environment(
    root: Path,
    requested: str | None = None,
    *,
    environ: dict[str, str] | None = None,
    fingerprints: list[dict[str, str]] | None = None,
) -> dict:
    """Resolve CLI > environment variable > selector > unique fingerprint."""
    manifests, findings = load_environment_manifests(root)
    if findings:
        raise EnvironmentSelectionError("invalid-manifest")
    env = os.environ if environ is None else environ
    if requested not in (None, "current"):
        if not _valid_environment_slug(requested):
            raise EnvironmentSelectionError("invalid-explicit")
        if requested not in manifests:
            raise EnvironmentSelectionError("explicit-not-found")
        return {"slug": requested, "source": "cli", "state": "selected"}

    if "SECOND_BRAIN_ENV" in env:
        variable = env["SECOND_BRAIN_ENV"]
    else:
        variable = None
    if variable is not None and variable != "current":
        if not _valid_environment_slug(variable):
            raise EnvironmentSelectionError("invalid-environment-variable")
        if variable not in manifests:
            raise EnvironmentSelectionError("environment-variable-not-found")
        return {"slug": variable, "source": "environment", "state": "selected"}

    selector = _read_environment_selector(root)
    if selector is not None:
        if selector not in manifests:
            raise EnvironmentSelectionError("selector-not-found")
        return {"slug": selector, "source": "selector", "state": "selected"}

    if not manifests:
        return {"slug": None, "source": "none", "state": "unconfigured"}

    local_rows = fingerprints if fingerprints is not None else machine_fingerprints()
    local = {(row["algorithm"], row["digest"], row["source"]) for row in local_rows}
    matches = []
    for slug, data in manifests.items():
        recorded = {
            (row["algorithm"], row["digest"], row["source"])
            for row in data["fingerprints"]
        }
        if local & recorded:
            matches.append(slug)
    if len(matches) == 1:
        return {"slug": matches[0], "source": "fingerprint", "state": "selected"}
    if len(matches) > 1:
        raise EnvironmentSelectionError("ambiguous-fingerprint")
    raise EnvironmentSelectionError("no-fingerprint-match")


def select_aymt_environment(
    root: Path,
    requested: str | None = None,
    *,
    environ: dict[str, str] | None = None,
    fingerprints: list[dict[str, str]] | None = None,
) -> dict:
    """Resolve AYMT's current slug without letting unrelated defects block it.

    Explicit, environment-variable, and selector choices identify one manifest
    without loading siblings. Automatic fingerprint matching tolerates invalid
    unrelated registrations but still requires one unique valid match.
    """
    env = os.environ if environ is None else environ
    if requested not in (None, "current"):
        if not _valid_environment_slug(requested):
            raise EnvironmentSelectionError("invalid-explicit")
        return {"slug": requested, "source": "cli", "state": "selected"}
    variable = env.get("SECOND_BRAIN_ENV")
    if variable is not None and variable != "current":
        if not _valid_environment_slug(variable):
            raise EnvironmentSelectionError("invalid-environment-variable")
        return {"slug": variable, "source": "environment", "state": "selected"}
    selector = _read_environment_selector(root)
    if selector is not None:
        return {"slug": selector, "source": "selector", "state": "selected"}

    manifests, findings = load_environment_manifests(root)
    if not manifests:
        if findings:
            raise EnvironmentSelectionError("invalid-manifest")
        return {"slug": None, "source": "none", "state": "unconfigured"}
    local_rows = fingerprints if fingerprints is not None else machine_fingerprints()
    local = {(row["algorithm"], row["digest"], row["source"]) for row in local_rows}
    matches = []
    for slug, data in manifests.items():
        recorded = {
            (row["algorithm"], row["digest"], row["source"])
            for row in data["fingerprints"]
        }
        if local & recorded:
            matches.append(slug)
    if len(matches) == 1:
        return {"slug": matches[0], "source": "fingerprint", "state": "selected"}
    if len(matches) > 1:
        raise EnvironmentSelectionError("ambiguous-fingerprint")
    raise EnvironmentSelectionError("no-fingerprint-match")


def environment_metadata(data: dict, selected: str | None) -> dict:
    """Metadata-only row: no digest, capability values, endpoint, or path."""
    return {
        "freshness": data["freshness"],
        "slug": data["slug"],
        "status": "selected" if data["slug"] == selected else "registered",
    }


def _environment_for_corpus(root: Path) -> str | None:
    if _ACTIVE_ENVIRONMENT is not _ENVIRONMENT_UNSET:
        return _ACTIVE_ENVIRONMENT  # type: ignore[return-value]
    return select_environment(root)["slug"]


def _environment_path_allowed(rel: str, selected: str | None) -> bool:
    prefix = ENVIRONMENTS_RELPATH + "/"
    if not rel.startswith(prefix):
        return True
    remainder = rel[len(prefix) :]
    if "/" not in remainder:
        return True
    slug = remainder.split("/", 1)[0]
    return selected is not None and slug == selected

# ---------------------------------------------------------------------------
# §2 Corpus


def default_vault_root() -> Path:
    return Path(__file__).resolve().parents[3]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def fold(s: str) -> str:
    # §6 folding rule: NFC then casefold.
    return nfc(s).casefold()


def walk_corpus(
    root: Path, *, selected_environment: object | str | None = _ENVIRONMENT_UNSET
) -> tuple[list[str], list[str]]:
    """Working corpus: (note paths, asset paths), vault-relative NFC, sorted."""
    if selected_environment is _ENVIRONMENT_UNSET:
        selected = _environment_for_corpus(root)
    else:
        selected = selected_environment
    notes: list[str] = []
    assets: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d != "__pycache__"
            and not TOOL_TESTS_RE.match(
                nfc(f"{rel_dir}/{d}" if rel_dir != "." else d)
            )
        ]
        if rel_dir == ENVIRONMENTS_RELPATH:
            dirnames[:] = [
                name
                for name in dirnames
                if selected is not None and name == selected
            ]
        dirnames.sort()
        for name in filenames:
            if name.startswith("."):
                continue
            rel = nfc(f"{rel_dir}/{name}" if rel_dir != "." else name)
            if rel in (INDEX_RELPATH, EMBED_RELPATH):
                continue
            if not _environment_path_allowed(rel, selected):
                continue
            if name.endswith(".md"):
                notes.append(rel)
            else:
                assets.append(rel)
    return sorted(notes), sorted(assets)


def git_tracked(root: Path) -> set[str] | None:
    """NFC paths of tracked/staged files, or None if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {nfc(p.decode("utf-8")) for p in out.split(b"\0") if p}


def index_corpus(root: Path) -> tuple[list[str], list[str]]:
    """Index corpus (§2): tracked shared content only.

    The committed index must be byte-stable across clones. Environment notes
    remain queryable at runtime for the selected environment, but never enter
    this cross-environment generated artifact.
    """
    notes, assets = walk_corpus(root, selected_environment=None)
    tracked = git_tracked(root)
    if tracked is None:
        print(
            "warning: git unavailable — building index from the working tree",
            file=sys.stderr,
        )
        return notes, assets
    return [p for p in notes if p in tracked], [p for p in assets if p in tracked]


# ---------------------------------------------------------------------------
# §3 Text model


def _decode_note_bytes(raw: bytes) -> tuple[str | None, int]:
    """Normalize one already-authenticated note snapshot."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        norm = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return None, len(norm)
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, len(text.encode("utf-8"))


def load_text(root: Path, rel: str) -> tuple[str | None, int]:
    """(normalized text or None on decode failure, sizeBytes)."""
    return _decode_note_bytes(_read_vault_bytes(root, rel))


# ---------------------------------------------------------------------------
# §4 Frontmatter grammar

KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:$|\s+(.*)$|\s+$)")
LIST_ITEM_RE = re.compile(r"^\s*-\s(.*)$")


def scalar(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s


def split_flow(inner: str) -> list[str]:
    if not inner.strip():
        return []
    items: list[str] = []
    buf = ""
    quote: str | None = None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
    items.append(buf)
    return [scalar(i) for i in items]


def parse_frontmatter(lines: list[str]) -> tuple[dict, list[str], int, bool]:
    """Returns (frontmatter map, errors, body start line index, has_frontmatter)."""
    if not lines or lines[0] != "---":
        return {}, [], 0, False
    errors: list[str] = []
    close = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            close = i
            break
    if close is None:
        errors.append("unterminated-frontmatter")
        body_start = 1
        block: list[str] = lines[1:]
    else:
        body_start = close + 1
        block = lines[1:close]

    fm: dict = {}
    open_list: str | None = None
    for offset, line in enumerate(block, start=2):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        m = KEY_RE.match(line)
        if m:
            key, value = m.group(1), (m.group(2) or "").strip()
            if key in fm:
                errors.append(f"duplicate-key:{key}")
            open_list = None
            if not value:
                fm[key] = None
                open_list = key
            elif value.startswith("["):
                if value.endswith("]"):
                    inner = value[1:-1]
                    if "[" in inner or "]" in inner:
                        errors.append(f"unsupported-yaml:{offset}")
                    else:
                        fm[key] = split_flow(inner)
                else:
                    errors.append(f"unsupported-yaml:{offset}")
            else:
                fm[key] = scalar(value)
            continue
        m = LIST_ITEM_RE.match(line)
        if m:
            if open_list is None:
                errors.append("list-item-without-key")
            else:
                if fm[open_list] is None:
                    fm[open_list] = []
                fm[open_list].append(scalar(m.group(1)))
            continue
        errors.append(f"unsupported-yaml:{offset}")
    return fm, errors, body_start, True


UPDATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def typed_fields(fm: dict, errors: list[str]) -> tuple[str | None, list[str] | None, str | None]:
    """§4.5: (title, tags, updated) with coercions recorded into errors."""
    title = fm.get("title") if isinstance(fm.get("title"), str) else None
    raw_tags = fm.get("tags")
    tags: list[str] | None
    if isinstance(raw_tags, list):
        tags = raw_tags
    elif isinstance(raw_tags, str):
        errors.append("tags-not-a-list")
        tags = [raw_tags]
    else:
        tags = None
    updated = None
    raw_updated = fm.get("updated")
    if isinstance(raw_updated, str):
        if UPDATED_RE.match(raw_updated):
            y, mo, d = (int(x) for x in raw_updated.split("-"))
            try:
                date(y, mo, d)
                updated = raw_updated
            except ValueError:
                errors.append("invalid-updated")
        else:
            errors.append("invalid-updated")
    elif "updated" in fm:
        errors.append("invalid-updated")
    return title, tags, updated


def iso_date(s: str | None) -> date | None:
    if not isinstance(s, str) or not UPDATED_RE.match(s):
        return None
    y, mo, d = (int(x) for x in s.split("-"))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def check_expires(fm: dict, errors: list[str]) -> None:
    """§14: expires: must be a real YYYY-MM-DD when present (templates may
    hold a placeholder — exempted in run_validate like invalid-updated)."""
    if "expires" not in fm:
        return
    raw = fm.get("expires")
    if not isinstance(raw, str) or iso_date(raw) is None:
        errors.append("invalid-expires")


# ---------------------------------------------------------------------------
# §5.2 Exclusion zones

FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
TICK_RUN_RE = re.compile(r"`+")


def mask_code_spans(line: str) -> str:
    """Blank out line-scoped inline code spans (backticks included)."""
    runs = [(m.start(), m.end()) for m in TICK_RUN_RE.finditer(line)]
    if not runs:
        return line
    out = list(line)
    i = 0
    while i < len(runs):
        n = runs[i][1] - runs[i][0]
        j = i + 1
        while j < len(runs) and runs[j][1] - runs[j][0] != n:
            j += 1
        if j < len(runs):
            for k in range(runs[i][0], runs[j][1]):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def body_lines_masked(lines: list[str], body_start: int):
    """Yield (line number, raw line, masked line) outside fenced code blocks."""
    fence_char = ""
    fence_len = 0
    for i in range(body_start, len(lines)):
        raw = lines[i]
        if fence_char:
            stripped = raw.strip()
            if stripped and set(stripped) == {fence_char} and len(stripped) >= fence_len:
                fence_char = ""
            continue
        m = FENCE_OPEN_RE.match(raw)
        if m:
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            continue
        yield i + 1, raw, mask_code_spans(raw)


# ---------------------------------------------------------------------------
# §5 Link grammar / §7 body extraction

WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
HEADING_RE = re.compile(r"^( {0,3})(#{1,6}) (.*)$")
BODY_TAG_RE = re.compile(r"(?:^|(?<=\s))#([A-Za-z0-9_/-]+)")
EXT_RE = re.compile(r"\.[A-Za-z0-9]+$")
EXTERNAL_DESTINATION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
INVALID_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
ENCODED_SEPARATOR_RE = re.compile(r"%(?:2[fF]|5[cC])")

# §17 checkbox tasks (issue #28). Detection runs on the MASKED line (so
# checkboxes inside fenced code or inline code spans never index); the task
# text is taken from the raw line at the same offset (masking preserves
# length), so inline code inside a real task's text survives.
TASK_RE = re.compile(r"^\s*[-*+] \[(.)\] ")
# Obsidian Tasks emoji grammar (accepted design, issue #28). Date-bearing
# emoji take a YYYY-MM-DD token; only 📅 (due) is indexed as a field, but a
# bad date after ANY of them flags `malformed` (§17.2).
TASK_DATE_EMOJI = {
    "\U0001f4c5": "due",  # 📅
    "⏳": "scheduled",  # ⏳
    "\U0001f6eb": "start",  # 🛫
    "✅": "done",  # ✅
    "➕": "created",  # ➕
}
TASK_PRIORITY_EMOJI = {
    "⏫": "high",  # ⏫
    "\U0001f53c": "medium",  # 🔼
    "\U0001f53d": "low",  # 🔽
}
TASK_RECURRENCE_EMOJI = "\U0001f501"  # 🔁 — free-text value, stripped only
TASK_EMOJI_RE = re.compile(
    "("
    + "|".join(
        sorted(TASK_DATE_EMOJI) + sorted(TASK_PRIORITY_EMOJI) + [TASK_RECURRENCE_EMOJI]
    )
    + ")\ufe0f?"  # tolerate an emoji variation selector
)
# ASCII digits only: unicode \d would accept e.g. Arabic-Indic digits that
# int() then mis-parses into a "valid" date the owner never wrote.
TASK_DATE_TOKEN_RE = re.compile(r"\s*([0-9]{4}-[0-9]{2}-[0-9]{2})(?![0-9])")


def parse_task_text(text: str) -> tuple[str, str | None, str | None, list[str]]:
    """§17.2: split a task's raw text into (clean description, due, priority,
    malformed field names). Emoji tokens (emoji + value) are stripped from the
    description; the last occurrence wins for a repeated field. A date-shaped
    token that is not a real calendar date is consumed and flags the field;
    a missing/non-date-shaped value flags the field and leaves the text."""
    due: str | None = None
    priority: str | None = None
    malformed: set[str] = set()
    pieces: list[str] = []
    pos = 0
    matches = list(TASK_EMOJI_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.start() < pos:
            continue  # inside a value a previous token consumed
        pieces.append(text[pos : m.start()])
        emoji = m.group(1)
        if emoji == TASK_RECURRENCE_EMOJI:
            # Recurrence is free text: runs to the next emoji or end of text.
            pos = next(
                (n.start() for n in matches[i + 1 :] if n.start() >= m.end()),
                len(text),
            )
            continue
        if emoji in TASK_PRIORITY_EMOJI:
            priority = TASK_PRIORITY_EMOJI[emoji]
            pos = m.end()
            continue
        field = TASK_DATE_EMOJI[emoji]
        dm = TASK_DATE_TOKEN_RE.match(text, m.end())
        if dm and iso_date(dm.group(1)) is not None:
            if field == "due":
                due = dm.group(1)
            pos = dm.end()
        else:
            malformed.add(field)
            pos = dm.end() if dm else m.end()
    pieces.append(text[pos:])
    clean = " ".join(" ".join(pieces).split())
    return clean, due, priority, sorted(malformed)


def _source_range(
    start: int, end: int, line: int, column: int, end_column: int
) -> dict:
    """End-exclusive UTF-8 byte range over the normalized source text."""
    return {
        "end": {"column": end_column, "line": line, "offset": end},
        "start": {"column": column, "line": line, "offset": start},
    }


def _link_record(
    *,
    destination: str,
    embed: bool,
    format_name: str,
    fragment: str | None,
    label: str | None,
    line: int,
    raw: str,
    source_start: int,
    source_end: int,
    column: int,
    target: str | None = None,
) -> dict:
    logical_target = destination if target is None else target
    placeholder = "{{" in destination or (fragment is not None and "{{" in fragment)
    unsupported_block = bool(fragment and fragment.startswith("^"))
    status = (
        "placeholder"
        if placeholder
        else "unsupported-block-reference"
        if unsupported_block
        else "unresolved"
    )
    warnings = ["unsupported-block-reference"] if unsupported_block else []
    resolution = {
        "fragment": None,
        "path": None,
        "status": status,
        "warnings": list(warnings),
    }
    return {
        "destination": destination,
        "display": label,  # schema-v1 compatibility alias
        "embed": embed,
        "format": format_name,
        "fragment": fragment,
        "label": label,
        "line": line,
        "placeholder": placeholder,
        "range": _source_range(
            source_start, source_end, line, column, column + len(raw)
        ),
        "raw": raw,
        "resolution": resolution,
        "resolved": None,  # schema-v1 compatibility alias
        "target": logical_target,  # schema-v1 compatibility alias
        "warnings": warnings,  # schema-v1 compatibility alias
    }


def parse_link(
    inner: str,
    embed: bool,
    raw: str,
    line: int,
    *,
    source_start: int = 0,
    column: int = 0,
) -> dict:
    """Parse one legacy wikilink into the generic schema-v2 link record."""
    i = inner.find("|")
    if i == -1:
        linkpath, label = inner, None
    elif i > 0 and inner[i - 1] == "\\":
        linkpath, label = inner[: i - 1], inner[i + 1 :]
    else:
        linkpath, label = inner[:i], inner[i + 1 :]
    if "#" in linkpath:
        destination, fragment = linkpath.split("#", 1)
        fragment = fragment.strip()
    else:
        destination, fragment = linkpath, None
    destination = destination.strip()
    label = label.strip() if label is not None else None
    target = destination
    if target.endswith(".md"):
        target = target[:-3]
    return _link_record(
        destination=destination,
        embed=embed,
        format_name="wikilink",
        fragment=fragment,
        label=label,
        line=line,
        raw=raw,
        source_start=source_start,
        source_end=source_start + len(raw.encode("utf-8")),
        column=column,
        target=target,
    )


def _is_escaped(text: str, index: int) -> bool:
    slashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        slashes += 1
        index -= 1
    return bool(slashes % 2)


def _balanced_close(text: str, start: int, opener: str, closer: str) -> int | None:
    depth = 0
    for index in range(start, len(text)):
        if _is_escaped(text, index):
            continue
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    return None


def _unescape_markdown(text: str) -> str:
    return re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])", r"\1", text)


def _markdown_destination(body: str) -> str | None:
    body = body.strip()
    if not body:
        return ""
    if body.startswith("<"):
        end = next(
            (i for i in range(1, len(body)) if body[i] == ">" and not _is_escaped(body, i)),
            None,
        )
        if end is None:
            return None
        destination = _unescape_markdown(body[1:end])
        remainder = body[end + 1 :].strip()
        return destination if _valid_markdown_title(remainder) else None
    end = len(body)
    for index, char in enumerate(body):
        if char.isspace() and not _is_escaped(body, index):
            end = index
            break
    destination = _unescape_markdown(body[:end])
    remainder = body[end:].strip()
    return destination if _valid_markdown_title(remainder) else None


def _valid_markdown_title(remainder: str) -> bool:
    """Accept an absent or one fully-delimited inline-link title, nothing else."""
    if not remainder:
        return True
    opener = remainder[0]
    closer = {"\"": "\"", "'": "'", "(": ")"}.get(opener)
    if closer is None or len(remainder) < 2 or remainder[-1] != closer:
        return False
    inner = remainder[1:-1]
    if opener == "(":
        depth = 0
        for index, char in enumerate(inner):
            if _is_escaped(inner, index):
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    return False
                depth -= 1
        return depth == 0
    return not any(char == closer and not _is_escaped(inner, index) for index, char in enumerate(inner))


def _external_destination(destination: str) -> bool:
    return destination.startswith("//") or bool(EXTERNAL_DESTINATION_RE.match(destination))


def _decode_link_component(value: str, *, path: bool) -> str | None:
    if INVALID_PERCENT_RE.search(value) or (path and ENCODED_SEPARATOR_RE.search(value)):
        return None
    try:
        decoded = unquote_to_bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\0" in decoded:
        return None
    return nfc(decoded)


def parse_markdown_links(
    raw_line: str, masked_line: str, line: int, line_offset: int
) -> list[dict]:
    """Parse inline Markdown links/images; reference links and URLs stay out."""
    records: list[dict] = []
    index = 0
    while index < len(masked_line):
        embed = masked_line.startswith("![", index) and not _is_escaped(masked_line, index)
        open_index = index + 1 if embed else index
        if masked_line[open_index : open_index + 1] != "[" or _is_escaped(
            masked_line, open_index
        ):
            index += 1
            continue
        if masked_line.startswith("[[", open_index):
            index += 1
            continue
        label_end = _balanced_close(masked_line, open_index, "[", "]")
        if label_end is None or label_end + 1 >= len(masked_line) or masked_line[label_end + 1] != "(":
            index = label_end + 1 if label_end is not None else index + 1
            continue
        destination_end = _balanced_close(masked_line, label_end + 1, "(", ")")
        if destination_end is None:
            index = label_end + 1
            continue
        raw_destination = _markdown_destination(
            raw_line[label_end + 2 : destination_end]
        )
        if raw_destination is None or _external_destination(raw_destination):
            index = destination_end + 1
            continue
        if "#" in raw_destination:
            encoded_destination, encoded_fragment = raw_destination.split("#", 1)
            fragment = _decode_link_component(encoded_fragment, path=False)
        else:
            encoded_destination, fragment = raw_destination, None
        destination = _decode_link_component(encoded_destination, path=True)
        if destination is not None and _external_destination(destination):
            # Percent-encoding cannot disguise a URI scheme as a vault path.
            index = destination_end + 1
            continue
        invalid_encoding = (
            destination is None
            or ("#" in raw_destination and fragment is None)
            or "?" in encoded_destination
        )
        if destination is None:
            destination = encoded_destination
        source_start = line_offset + len(raw_line[:index].encode("utf-8"))
        raw = raw_line[index : destination_end + 1]
        label = _unescape_markdown(raw_line[open_index + 1 : label_end])
        record = _link_record(
                destination=destination,
                embed=embed,
                format_name="markdown",
                fragment=fragment,
                label=label,
                line=line,
                raw=raw,
                source_start=source_start,
                source_end=source_start + len(raw.encode("utf-8")),
                column=index,
            )
        if invalid_encoding:
            record["warnings"] = ["invalid-url-encoding"]
            record["resolution"] = {
                "fragment": None,
                "path": None,
                "status": "unsupported-destination",
                "warnings": ["invalid-url-encoding"],
            }
        records.append(record)
        index = destination_end + 1
    return records


def _render_heading_inline(text: str) -> str:
    """Bounded inline rendering needed for GitHub-compatible anchor text."""
    text = re.sub(r"<[^>]*>", "", text)
    rendered = []
    index = 0
    while index < len(text):
        embed = text.startswith("![", index) and not _is_escaped(text, index)
        open_index = index + 1 if embed else index
        if text[open_index : open_index + 1] == "[" and not _is_escaped(
            text, open_index
        ):
            label_end = _balanced_close(text, open_index, "[", "]")
            if (
                label_end is not None
                and label_end + 1 < len(text)
                and text[label_end + 1] == "("
            ):
                destination_end = _balanced_close(
                    text, label_end + 1, "(", ")"
                )
                if destination_end is not None:
                    rendered.append(
                        _unescape_markdown(text[open_index + 1 : label_end])
                    )
                    index = destination_end + 1
                    continue
        rendered.append(text[index])
        index += 1
    return html.unescape("".join(rendered))


def heading_slug(text: str) -> str:
    """Portable GitHub/Obsidian heading slug: NFC, lowercase, punctuation out."""
    text = nfc(_render_heading_inline(text))
    text = re.sub(r"[`*_~]", "", text).casefold().strip()
    chars = []
    for char in text:
        category = unicodedata.category(char)
        if char.isspace():
            chars.append(" ")
        elif char == "-" or category[0] in {"L", "N", "M"}:
            chars.append(char)
    return re.sub(r"\s+", "-", "".join(chars))


def extract_body(
    lines: list[str], body_start: int, *, line_offsets: list[int] | None = None
) -> tuple[list[dict], list[dict], list[str], list[dict]]:
    """Returns generic links, headings, bodyTags, and tasks in document order."""
    links: list[dict] = []
    headings: list[dict] = []
    heading_slug_counts: dict[str, int] = {}
    body_tags: set[str] = set()
    tasks: list[dict] = []
    if line_offsets is None:
        line_offsets = []
        offset = 0
        for source_line in lines:
            line_offsets.append(offset)
            offset += len(source_line.encode("utf-8")) + 1
    for lineno, raw, masked in body_lines_masked(lines, body_start):
        tm = TASK_RE.match(masked)
        if tm:
            raw_text = raw[tm.end() :].strip()
            if raw_text:
                text, due, priority, malformed = parse_task_text(raw_text)
                tasks.append(
                    {
                        "due": due,
                        "line": lineno,
                        "malformed": malformed,
                        "priority": priority,
                        "status": "open" if tm.group(1) == " " else "done",
                        "text": text,
                    }
                )
        hm = HEADING_RE.match(masked)
        if hm:
            text = raw[hm.start(3) :]
            text = re.sub(r"\s+#+\s*$", "", text).strip()
            base_slug = heading_slug(text)
            duplicate = heading_slug_counts.get(base_slug, 0)
            heading_slug_counts[base_slug] = duplicate + 1
            slug = base_slug if duplicate == 0 else f"{base_slug}-{duplicate}"
            headings.append(
                {
                    "level": len(hm.group(2)),
                    "line": lineno,
                    "slug": slug,
                    "text": text,
                }
            )
        line_offset = line_offsets[lineno - 1]
        for m in WIKILINK_RE.finditer(masked):
            if _is_escaped(masked, m.start()):
                continue
            raw_link = raw[m.start() : m.end()]
            inner = raw_link[3:-2] if m.group(1) == "!" else raw_link[2:-2]
            links.append(
                parse_link(
                    inner,
                    m.group(1) == "!",
                    raw_link,
                    lineno,
                    source_start=line_offset + len(raw[: m.start()].encode("utf-8")),
                    column=m.start(),
                )
            )
        links.extend(parse_markdown_links(raw, masked, lineno, line_offset))
        for m in BODY_TAG_RE.finditer(masked):
            tag = m.group(1)
            if any(not c.isdigit() for c in tag):
                body_tags.add(tag)
    links.sort(key=lambda record: record["range"]["start"]["offset"])
    return links, headings, sorted(body_tags), tasks


# ---------------------------------------------------------------------------
# §6 Link resolution


class Resolver:
    def __init__(self, notes: list[str], assets: list[str], titles: dict[str, str | None]):
        self.notes = set(notes)
        self.note_base: dict[str, list[str]] = {}
        for p in notes:
            self.note_base.setdefault(fold(p.rsplit("/", 1)[-1][:-3]), []).append(p)
        self.note_fold = {}
        for p in notes:
            self.note_fold.setdefault(fold(p), []).append(p)
        self.assets = set(assets)
        self.asset_base: dict[str, list[str]] = {}
        for p in assets:
            self.asset_base.setdefault(fold(p.rsplit("/", 1)[-1]), []).append(p)
        self.asset_fold = {}
        for p in assets:
            self.asset_fold.setdefault(fold(p), []).append(p)
        self.title_fold: dict[str, list[str]] = {}
        for p, t in titles.items():
            if t:
                self.title_fold.setdefault(fold(t), []).append(p)

    def _ladder(
        self, target: str, base: dict, full_set: set, full_fold: dict, suffix: str
    ) -> tuple[str | None, list[str]]:
        if "/" not in target:
            cands = base.get(fold(target))
            if cands:
                warnings = []
                if len(cands) > 1:
                    return None, ["ambiguous", *(f"candidate:{p}" for p in sorted(cands))]
                r = cands[0]
                actual = r.rsplit("/", 1)[-1]
                if suffix:
                    actual = actual[: -len(suffix)]
                if actual != target:
                    warnings.append("case-mismatch")
                return r, warnings
            return None, []
        full = target + suffix
        if full in full_set:
            return full, []
        ci = full_fold.get(fold(full))
        if ci:
            warnings = ["case-mismatch"]
            if len(ci) > 1:
                return None, ["ambiguous", *(f"candidate:{p}" for p in sorted(ci))]
            r = ci[0]
            return r, warnings
        return None, []

    def _full_path(
        self, full: str, full_set: set[str], full_fold: dict[str, list[str]]
    ) -> tuple[str | None, list[str]]:
        if full in full_set:
            return full, []
        candidates = full_fold.get(fold(full), [])
        if len(candidates) > 1:
            return None, ["ambiguous", *(f"candidate:{p}" for p in sorted(candidates))]
        if candidates:
            return candidates[0], ["case-mismatch"]
        return None, []

    def _resolve_markdown(self, target: str, containing: str) -> tuple[str | None, list[str]]:
        if target == "":
            return containing, []
        raw = target.replace("\\", "/")
        if raw.startswith("/"):
            return None, ["unsupported-absolute-path"]
        parent = posixpath.dirname(containing)
        candidate = posixpath.normpath(posixpath.join(parent, raw))
        if candidate in {"", ".", ".."} or candidate.startswith("../"):
            return None, ["outside-vault"]
        final = candidate.rsplit("/", 1)[-1]
        if candidate.endswith(".md"):
            return self._full_path(candidate, self.notes, self.note_fold)
        if not EXT_RE.search(final):
            resolved, warnings = self._full_path(
                candidate + ".md", self.notes, self.note_fold
            )
            if resolved is not None or warnings:
                return resolved, warnings
        return self._full_path(candidate, self.assets, self.asset_fold)

    def resolve(
        self, target: str, containing: str, *, format: str = "wikilink"
    ) -> tuple[str | None, list[str]]:
        if format == "markdown":
            return self._resolve_markdown(target, containing)
        if target == "":
            return containing, []
        r, warnings = self._ladder(target, self.note_base, self.notes, self.note_fold, ".md")
        if r is not None or warnings:
            return r, warnings
        final = target.rsplit("/", 1)[-1]
        if EXT_RE.search(final) and not final.endswith(".md"):
            r, warnings = self._ladder(target, self.asset_base, self.assets, self.asset_fold, "")
            if r is not None or warnings:
                return r, warnings
        hints = sorted(self.title_fold.get(fold(target), []))
        return None, [f"title-match:{p}" for p in hints]


# ---------------------------------------------------------------------------
# §8 Index build and serialization


def _resolve_link_record(
    link: dict, containing: str, resolver: Resolver, records: dict[str, dict]
) -> None:
    """Populate both schema-v2 resolution and schema-v1 compatibility aliases."""
    if link["placeholder"]:
        return
    if link.get("resolution", {}).get("status") == "unsupported-destination":
        # Syntax-level destination failures are terminal. In particular, do
        # not let a decodable path prefix turn an invalid query/fragment into
        # a resolved v1 alias during the resolution pass.
        link["resolved"] = None
        link["warnings"] = list(link["resolution"].get("warnings", []))
        return
    resolved, warnings = resolver.resolve(
        link["target"], containing, format=link["format"]
    )
    fragment_resolution = None
    status = "resolved" if resolved is not None else "unresolved"
    if "ambiguous" in warnings:
        status = "ambiguous"
    elif "unsupported-absolute-path" in warnings:
        status = "unsupported-destination"
    fragment = link["fragment"]
    if resolved is not None and fragment:
        if fragment.startswith("^"):
            status = "unsupported-block-reference"
            if "unsupported-block-reference" not in warnings:
                warnings.append("unsupported-block-reference")
        else:
            headings = records.get(resolved, {}).get("headings", [])
            if link["format"] == "wikilink":
                candidates = [h for h in headings if fold(h["text"]) == fold(fragment)]
            else:
                candidates = [h for h in headings if h["slug"] == fragment]
                if not candidates:
                    candidates = [h for h in headings if fold(h["slug"]) == fold(fragment)]
                    if candidates:
                        warnings.append("fragment-case-mismatch")
            if len(candidates) > 1:
                warnings.extend(
                    ["ambiguous-fragment"]
                    + [f"heading-candidate:{h['line']}" for h in candidates]
                )
                resolved = None
                status = "ambiguous"
            elif candidates:
                heading = candidates[0]
                fragment_resolution = {
                    "line": heading["line"],
                    "slug": heading["slug"],
                }
            else:
                # Path resolution remains useful for backlinks and legacy
                # imports. WP9 can repair these before converting the corpus.
                warnings.append("unresolved-fragment")
                status = "unresolved-fragment"
    link["resolved"] = resolved
    link["warnings"] = warnings
    link["resolution"] = {
        "fragment": fragment_resolution,
        "path": resolved,
        "status": status,
        "warnings": list(warnings),
    }


def build_index(
    root: Path,
    notes: list[str],
    assets: list[str],
    *,
    note_snapshots: dict[str, bytes | None] | None = None,
) -> dict:
    records: dict[str, dict] = {}
    for rel in notes:
        try:
            if note_snapshots is None:
                text, size = load_text(root, rel)
            else:
                raw = note_snapshots.get(rel)
                if raw is None:
                    raise OSError("note snapshot unavailable")
                text, size = _decode_note_bytes(raw)
            read_error = "not-utf8" if text is None else None
        except OSError:
            # §3 read failure: broken symlink, permission denied, … — never fatal.
            text, size, read_error = None, 0, "not-readable"
        if text is None:
            records[rel] = {
                "backlinks": [],
                "bodyTags": [],
                "frontmatter": {},
                "frontmatterErrors": [read_error],
                "headings": [],
                "links": [],
                "sizeBytes": size,
                "tasks": [],
                "title": None,
                "updated": None,
            }
            continue
        lines = text.split("\n")
        fm, errors, body_start, _has_fm = parse_frontmatter(lines)
        title, _tags, updated = typed_fields(fm, errors)
        check_expires(fm, errors)
        links, headings, body_tags, tasks = extract_body(lines, body_start)
        records[rel] = {
            "backlinks": [],
            "bodyTags": body_tags,
            "frontmatter": fm,
            "frontmatterErrors": errors,
            "headings": headings,
            "links": links,
            "sizeBytes": size,
            "tasks": tasks,
            "title": title,
            "updated": updated,
        }
    resolver = Resolver(notes, assets, {p: r["title"] for p, r in records.items()})
    backlinks: dict[str, set[str]] = {p: set() for p in notes}
    link_counts = {
        "legacy": 0,
        "markdown": 0,
        "placeholder": 0,
        "unsupportedBlockReference": 0,
        "wikilink": 0,
    }
    for rel, rec in records.items():
        for link in rec["links"]:
            link_counts[link["format"]] += 1
            if link["format"] == "wikilink":
                link_counts["legacy"] += 1
            if link["placeholder"]:
                link_counts["placeholder"] += 1
            if link["fragment"] and link["fragment"].startswith("^"):
                link_counts["unsupportedBlockReference"] += 1
            _resolve_link_record(link, rel, resolver, records)
            if link["resolved"] in backlinks:
                backlinks[link["resolved"]].add(rel)
    for rel, rec in records.items():
        rec["backlinks"] = sorted(backlinks[rel])
    return {
        "assets": assets,
        "linkCounts": link_counts,
        "notes": records,
        "schemaVersion": SCHEMA_VERSION,
    }


# §8.3 restricted-note reduction (issue #17). Frontmatter tags only —
# bodyTags are informal (§10.2 posture) and never trigger restriction.
RESTRICTED_TAG = "restricted/private"


def note_frontmatter_tags(rec: dict) -> list[str]:
    tags = rec["frontmatter"].get("tags")
    return tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])


def is_restricted(rec: dict) -> bool:
    return RESTRICTED_TAG in note_frontmatter_tags(rec)


def reduce_restricted(index: dict) -> dict:
    """§8.3: reduce restricted notes for the COMMITTED index — keep
    path/title/frontmatter(tags)/updated/sizeBytes/frontmatterErrors/links/
    backlinks, empty the body-derived fields (headings, bodyTags) the index
    would otherwise re-leak, and strip body prose from link records
    (display alias text, fragments, verbatim raw markup) — only the
    structural target/resolution survives. Emptied/nulled, never omitted:
    the §8.1 shape holds, so no schemaVersion bump. In-memory query indexes
    stay unreduced (§8.3)."""
    for rec in index["notes"].values():
        if is_restricted(rec):
            rec["headings"] = []
            rec["bodyTags"] = []
            rec["tasks"] = []  # §17: task text/metadata is body content
            for link in rec.get("links", []):
                link["display"] = None
                link["label"] = None
                link["fragment"] = None
                target = link.get("target") or ""
                if link.get("format") == "markdown":
                    destination = link.get("destination") or ""
                    link["raw"] = (
                        ("![](%s)" if link.get("embed") else "[](%s)")
                        % destination
                    )
                else:
                    link["raw"] = (
                        "![[%s]]" if link.get("embed") else "[[%s]]"
                    ) % target
                link["resolution"]["fragment"] = None
    return index


def serialize(index: dict) -> bytes:
    return (json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode(
        "utf-8"
    )


# ---------------------------------------------------------------------------
# §10.1 Conventions taxonomy

TICK_TOKEN_RE = re.compile(r"`([^`]+)`")


def load_taxonomy(root: Path) -> dict[str, list[str] | None] | None:
    """namespace -> closed value list, or None for open. None overall = unreadable."""
    try:
        text, _ = load_text(root, CONVENTIONS_RELPATH)
    except OSError:
        return None
    if text is None:
        return None
    lines = text.split("\n")
    try:
        start = lines.index("## Tag Namespaces")
    except ValueError:
        return None
    table: list[str] = []
    for line in lines[start + 1 :]:
        if line.lstrip().startswith("|"):
            table.append(line)
        elif table:
            break
    if len(table) < 3:
        return None
    taxonomy: dict[str, list[str] | None] = {}
    for row in table[2:]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 3:
            return None
        m = TICK_TOKEN_RE.search(cells[0])
        if not m:
            return None
        namespace = m.group(1)
        if namespace.endswith("/*"):
            namespace = namespace[:-2]
        if cells[2].lower().startswith("free-form"):
            taxonomy[namespace] = None
        else:
            taxonomy[namespace] = TICK_TOKEN_RE.findall(cells[2])
    return taxonomy or None


# ---------------------------------------------------------------------------
# §15 Vault config (00_Meta/config.yaml) — issue #2.
#
# Module-internal section, deliberately self-contained: the planned `shared`
# module (#31) seeds from here. Public surface for later consumers
# (M9.2–M9.5: #16 report, #15 environments, #26 sync, …):
#
#   load_config(root)              -> (config map, findings)   — never raises
#   parse_config(text)             -> (config map, findings)
#   check_config(root, config, findings) -> (errors, warnings) — validate rows
#   write_exception_prefixes(config) -> tuple of dir prefixes agents may write
#   agent_write_allowed(rel, config) -> bool  (Inbox-first + exceptions)
#   extension_trust(config)        -> policy string (default "first-party")
#   vault_context(config)          -> context string (default "personal")
#   template_version(config)       -> recorded upstream version or None
#
# The config is OPTIONAL: an absent file (or empty/all-comment file) yields
# ({}, []) and every behavior stays at its built-in default. Malformed
# content becomes per-file validate findings on CONFIG_RELPATH — never a
# crash, and never a behavior change beyond ignoring the malformed part.

CONFIG_RELPATH = "00_Meta/config.yaml"
CONFIG_IMPLEMENTED_KEYS = frozenset(
    {
        "context",
        "extension_trust",
        "report",
        "tasks",
        "template_version",
        "write_exceptions",
    }
)
# Named-but-unimplemented keys reserved for the issues that claimed them
# (#15 environments, #32 modules, #18 provenance, #26 sync). Parsed and
# tolerated with no finding, so a forward-looking config never fails an
# older brain.
CONFIG_RESERVED_KEYS = frozenset(
    {
        "environments",
        "modules",
        "provenance",
        "sync",
    }
)
# §16.4: known subkeys of the `report` mapping (values: digits-only scalars).
REPORT_CONFIG_KEYS = frozenset({"inbox_days", "stale_days"})
# §17.4: known subkeys of the `tasks` mapping (issue #28).
TASKS_CONFIG_KEYS = frozenset({"carry_over"})
TASKS_CARRY_OVER_VALUES = frozenset({"off", "on"})
DEFAULT_TASKS_CARRY_OVER = True  # carry_over: on
# Inbox-first defaults (PRD §6.2 / AGENTS.md): always writable, config only
# ever ADDS to this set. Session-scoped carve-outs (onboard-owner interviews,
# agent-generated skills/tools) are policy prose, not path constants.
AGENT_WRITE_DEFAULT_PREFIXES = ("02_Inbox/", "02_Outbox/", "10_Agents/solutions/")
# Single-file standing exceptions: append-only agent logs that live inside
# otherwise PR-only prefixes (conventions § Agent Write Rules).
AGENT_WRITE_DEFAULT_FILES = ("10_Agents/docs/rejected-proposals.md",)
DEFAULT_EXTENSION_TRUST = "first-party"
EXTENSION_TRUST_VALUES = frozenset({"first-party", "relaxed"})
DEFAULT_CONTEXT = "personal"
CONTEXT_VALUES = frozenset({"personal", "work"})

CONFIG_KEY_RE = re.compile(r"^( *)([A-Za-z0-9_-]+):(?:$|\s+(.*)$|\s+$)")


def _cfg_finding(line: int | None, rule: str, message: str) -> dict:
    return {"line": line, "message": message, "rule": rule}


def parse_config(text: str) -> tuple[dict, list[dict]]:
    """Parse the bounded YAML subset (§15.2): scalars, flat lists, one level
    of nested mapping. Best-effort — malformed lines become findings and are
    skipped; parsing never raises."""
    config: dict = {}
    findings: list[dict] = []
    open_key: str | None = None  # top-level key that may still take a block
    open_kind: str | None = None  # None (undecided) | "list" | "map"
    nested_indent = 0
    for lineno, raw in enumerate(text.split("\n"), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        km = CONFIG_KEY_RE.match(raw)
        if km:
            indent, key, value = len(km.group(1)), km.group(2), (km.group(3) or "").strip()
            if indent == 0:
                open_key, open_kind = None, None
                if key in config:
                    findings.append(
                        _cfg_finding(
                            lineno, "config-duplicate-key", f"duplicate key {key!r} (last wins)"
                        )
                    )
                if not value:
                    config[key] = None
                    open_key = key
                elif value.startswith("["):
                    if value.endswith("]") and "[" not in value[1:-1] and "]" not in value[1:-1]:
                        config[key] = split_flow(value[1:-1])
                    else:
                        findings.append(
                            _cfg_finding(
                                lineno,
                                "config-unsupported",
                                f"unparseable flow list for key {key!r}",
                            )
                        )
                else:
                    config[key] = scalar(value)
                continue
            # Indented key line: one nested mapping level under open_key.
            if open_key is None or open_kind == "list":
                findings.append(
                    _cfg_finding(
                        lineno, "config-unsupported", "indented key with no open mapping"
                    )
                )
                continue
            if open_kind is None:
                open_kind = "map"
                nested_indent = indent
                config[open_key] = {}
            elif indent > nested_indent:
                findings.append(
                    _cfg_finding(
                        lineno,
                        "config-nesting-too-deep",
                        "mappings nest at most one level (§15.2)",
                    )
                )
                continue
            mapping = config[open_key]
            if key in mapping:
                findings.append(
                    _cfg_finding(
                        lineno,
                        "config-duplicate-key",
                        f"duplicate nested key {open_key}.{key} (last wins)",
                    )
                )
            if not value:
                mapping[key] = None
            elif value.startswith("["):
                if value.endswith("]") and "[" not in value[1:-1] and "]" not in value[1:-1]:
                    mapping[key] = split_flow(value[1:-1])
                else:
                    findings.append(
                        _cfg_finding(
                            lineno,
                            "config-unsupported",
                            f"unparseable flow list for key {open_key}.{key}",
                        )
                    )
            else:
                mapping[key] = scalar(value)
            continue
        lm = LIST_ITEM_RE.match(raw)
        if lm:
            if open_key is None or open_kind == "map":
                findings.append(
                    _cfg_finding(
                        lineno, "config-list-item-without-key", "list item with no open list"
                    )
                )
                continue
            if open_kind is None:
                open_kind = "list"
                config[open_key] = []
            config[open_key].append(scalar(lm.group(1)))
            continue
        findings.append(
            _cfg_finding(
                lineno, "config-unsupported", "line outside the bounded YAML subset (§15.2)"
            )
        )
    return config, findings


def load_config(root: Path) -> tuple[dict, list[dict]]:
    """Effective raw config for a vault. Absent file -> ({}, []) — the
    defaults; unreadable/undecodable file -> ({}, [finding]). Never raises."""
    path = root / CONFIG_RELPATH
    if not path.exists():
        return {}, []
    try:
        text, _ = load_text(root, CONFIG_RELPATH)
    except OSError:
        return {}, [_cfg_finding(None, "config-not-readable", "config file cannot be read")]
    if text is None:
        return {}, [_cfg_finding(None, "config-not-utf8", "config file is not UTF-8")]
    return parse_config(text)


def write_exception_prefixes(config: dict) -> tuple[str, ...]:
    """Directory prefixes agents may write to: the Inbox-first defaults plus
    any well-formed `write_exceptions` entries (normalized to a trailing /).
    Malformed entries are ignored here — check_config reports them."""
    prefixes = list(AGENT_WRITE_DEFAULT_PREFIXES)
    extras = config.get("write_exceptions")
    for entry in extras if isinstance(extras, list) else []:
        if not isinstance(entry, str):
            continue
        p = nfc(entry.strip()).replace("\\", "/")
        if not p or p.startswith("/") or ".." in p.split("/") or ":" in p:
            continue
        p = p.removeprefix("./").rstrip("/")
        if p in ("", "."):
            # Effectively-empty entry ('.', './') — dropped here, reported
            # by check_config as config-bad-write-exception (same rule).
            continue
        p += "/"
        if p not in prefixes:
            prefixes.append(p)
    return tuple(prefixes)


def agent_write_allowed(rel: str, config: dict) -> bool:
    """Whether an agent may write vault-relative path `rel` under the
    Inbox-first rule plus configured exceptions. The enforcement point for
    harness write-gates; with no config it is exactly current policy."""
    rel = nfc(rel.strip()).replace("\\", "/").removeprefix("./")
    # Fail closed on traversal and non-vault-relative shapes: a prefix match
    # means nothing if the path can climb back out of the allowed directory.
    if rel.startswith("/") or ":" in rel.split("/", 1)[0]:
        return False
    if any(part in ("..", ".") for part in rel.split("/")):
        return False
    if rel in AGENT_WRITE_DEFAULT_FILES:
        return True
    return rel.startswith(write_exception_prefixes(config))


def extension_trust(config: dict) -> str:
    """Effective VS Code extension trust policy (PRD §6.5): the configured
    scalar, or the strict template default when absent/malformed."""
    value = config.get("extension_trust")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_EXTENSION_TRUST


def report_thresholds(config: dict) -> dict:
    """Effective §16 health-report thresholds: the `report` config mapping
    (spec §15.3) merged over the built-in defaults. Malformed values fall
    back to the default here — check_config reports them (§15.4)."""
    thresholds = {
        "inboxDays": REPORT_INBOX_TRIAGE_DAYS,
        "staleDays": REPORT_STALE_ACTIVE_DAYS,
    }
    section = config.get("report")
    if isinstance(section, dict):
        for subkey, out in (("inbox_days", "inboxDays"), ("stale_days", "staleDays")):
            value = section.get(subkey)
            v = value.strip() if isinstance(value, str) else ""
            if v.isascii() and v.isdigit():
                thresholds[out] = int(v)
    return thresholds


def tasks_carry_over(config: dict) -> bool:
    """Effective §17.4 daily-note carry-over toggle: `tasks: carry_over:`
    (spec §15.3), default on. Malformed values fall back to the default
    here — check_config reports them (§15.4)."""
    section = config.get("tasks")
    if isinstance(section, dict):
        value = section.get("carry_over")
        if isinstance(value, str) and value.strip() in TASKS_CARRY_OVER_VALUES:
            return value.strip() == "on"
    return DEFAULT_TASKS_CARRY_OVER


def vault_context(config: dict) -> str:
    """Effective vault context (issue #12): the scalar recorded by
    onboard-owner's fork-time specialization step, or the personal default
    when absent/malformed. Parse-and-report only — brain drives no behavior
    from it; templates are specialized at onboarding time, in place."""
    value = config.get("context")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_CONTEXT


def template_version(config: dict) -> str | None:
    """Recorded upstream template version (issue #6, spec §15.3): the
    free-form scalar the sync-upstream skill writes after a completed sync
    and compares against upstream release tags, or None when the fork has
    never recorded one. A record, not a switch — brain drives no behavior
    from it."""
    value = config.get("template_version")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def check_config(
    root: Path, config: dict, findings: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Semantic checks over a parsed config (§15.4). Returns (errors,
    warnings) as validate-shaped findings minus the path (the caller stamps
    CONFIG_RELPATH). Parse findings are errors except duplicate-key."""
    errors: list[dict] = []
    warnings: list[dict] = []
    for f in findings:
        (warnings if f["rule"] == "config-duplicate-key" else errors).append(f)
    for key in sorted(config):
        if key in CONFIG_IMPLEMENTED_KEYS or key in CONFIG_RESERVED_KEYS:
            continue
        warnings.append(
            _cfg_finding(
                None,
                "config-unknown-key",
                f"unknown key {key!r} is ignored (forward compatibility)",
            )
        )
    if "write_exceptions" in config:
        raw = config["write_exceptions"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, list):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "write_exceptions must be a list of directory paths",
                )
            )
        else:
            for entry in raw:
                p = nfc(entry.strip()).replace("\\", "/") if isinstance(entry, str) else ""
                # Normalize BEFORE judging, mirroring write_exception_prefixes,
                # so an entry that normalizes to nothing ('.', './') is
                # reported instead of silently granting nothing (§15.4).
                bad = not p or p.startswith("/") or ".." in p.split("/") or ":" in p
                p = p.removeprefix("./").rstrip("/")
                if bad or p in ("", "."):
                    errors.append(
                        _cfg_finding(
                            None,
                            "config-bad-write-exception",
                            f"write_exceptions entry {entry!r} is not a "
                            "vault-relative directory path (the vault root "
                            "itself cannot be granted)",
                        )
                    )
                    continue
                if not (root / p).is_dir():
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-missing-directory",
                            f"write_exceptions entry {entry!r} names no existing directory",
                        )
                    )
    if "report" in config:
        raw = config["report"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, dict):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "report must be a nested mapping of thresholds (§16.4)",
                )
            )
        else:
            for subkey in sorted(raw):
                value = raw[subkey]
                if subkey not in REPORT_CONFIG_KEYS:
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-unknown-key",
                            f"unknown key 'report.{subkey}' is ignored "
                            "(forward compatibility)",
                        )
                    )
                    continue
                if value is None:
                    continue  # explicit empty — same as absent
                if not (
                    isinstance(value, str)
                    and value.strip().isascii()
                    and value.strip().isdigit()
                ):
                    errors.append(
                        _cfg_finding(
                            None,
                            "config-invalid-value",
                            f"report.{subkey} must be a non-negative integer "
                            "number of days",
                        )
                    )
    if "tasks" in config:
        raw = config["tasks"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, dict):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "tasks must be a nested mapping of task-module settings (§17.4)",
                )
            )
        else:
            for subkey in sorted(raw):
                value = raw[subkey]
                if subkey not in TASKS_CONFIG_KEYS:
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-unknown-key",
                            f"unknown key 'tasks.{subkey}' is ignored "
                            "(forward compatibility)",
                        )
                    )
                    continue
                if value is None:
                    continue  # explicit empty — same as absent
                if not isinstance(value, str):
                    errors.append(
                        _cfg_finding(
                            None,
                            "config-invalid-value",
                            f"tasks.{subkey} must be a scalar string",
                        )
                    )
                elif value.strip() not in TASKS_CARRY_OVER_VALUES:
                    warnings.append(
                        _cfg_finding(
                            None,
                            "config-unknown-value",
                            f"tasks.{subkey} {value!r} is not a documented "
                            "value (on | off)",
                        )
                    )
    if "extension_trust" in config:
        raw = config["extension_trust"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, str):
            errors.append(
                _cfg_finding(
                    None, "config-invalid-value", "extension_trust must be a scalar string"
                )
            )
        elif raw.strip() not in EXTENSION_TRUST_VALUES:
            warnings.append(
                _cfg_finding(
                    None,
                    "config-unknown-value",
                    f"extension_trust {raw!r} is not a documented policy "
                    "(first-party | relaxed)",
                )
            )
    if "template_version" in config:
        raw = config["template_version"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, str):
            errors.append(
                _cfg_finding(
                    None,
                    "config-invalid-value",
                    "template_version must be a scalar version string",
                )
            )
        # Free-form by design (§15.3): any scalar is a documented value,
        # so there is no config-unknown-value warning for this key.
    if "context" in config:
        raw = config["context"]
        if raw is None:
            pass  # explicit empty — same as absent
        elif not isinstance(raw, str):
            errors.append(
                _cfg_finding(
                    None, "config-invalid-value", "context must be a scalar string"
                )
            )
        elif raw.strip() not in CONTEXT_VALUES:
            warnings.append(
                _cfg_finding(
                    None,
                    "config-unknown-value",
                    f"context {raw!r} is not a documented context "
                    "(personal | work)",
                )
            )
    return errors, warnings


# ---------------------------------------------------------------------------
# §10.5 Secret scanning

# Inline allowlist: an HTML comment containing this token on the SAME line
# suppresses every secret finding on that line — the committed marker is the
# audit trail for an intentional example.
SECRET_ALLOW_MARKER = "brain:allow-secret-pattern"
SECRET_ALLOW_RE = re.compile(r"<!--[^\n]*" + re.escape(SECRET_ALLOW_MARKER) + r"[^\n]*-->")

# Data-driven rule table (§10.5): (name, compiled pattern). Every finding is
# an ERROR with rule `secret-<name>`. Extending detection is a table edit —
# add a row here and a row to the spec.md §10.5 table in the same commit.
# Patterns are written so they never match their own source text, keeping the
# repo self-scan clean by construction.
SECRET_RULES: tuple[tuple[str, re.Pattern], ...] = (
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[a-z]-[A-Za-z0-9-]{10,}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "generic-credential",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|secret|token|passwd|password)"""
            r"""\s*[:=]\s*["'](?=[^"']*\d)[A-Za-z0-9_\-+/=]{12,}["']"""
        ),
    ),
    (
        "high-entropy-string",
        re.compile(
            r"""[:=]\s*["'](?=[^"']*[a-z])(?=[^"']*[A-Z])(?=[^"']*\d)"""
            r"""[A-Za-z0-9+/]{40,}={0,2}["']"""
        ),
    ),
)


def scan_secrets(root: Path, paths: list[str]) -> list[dict]:
    """§10.5: secret findings over every text file in the working corpus.

    Binary files (NUL byte in the first 8 KiB) are skipped; text is decoded
    UTF-8 with replacement and newline-normalized per §3, so line numbers
    match the rest of validate. One finding per (line, rule); the matched
    text is never echoed into the message."""
    findings: list[dict] = []
    for rel in sorted(paths):
        try:
            raw = _read_vault_bytes(root, rel)
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue
        text = raw.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        for lineno, line in enumerate(text.split("\n"), start=1):
            if SECRET_ALLOW_RE.search(line):
                continue
            for name, pattern in SECRET_RULES:
                if pattern.search(line):
                    findings.append(
                        {
                            "line": lineno,
                            "message": (
                                f"matches secret rule {name!r} — remove the "
                                "credential, or mark an intentional example "
                                "with an HTML comment containing "
                                f"{SECRET_ALLOW_MARKER} on this line"
                            ),
                            "path": rel,
                            "rule": f"secret-{name}",
                        }
                    )
    return findings


# ---------------------------------------------------------------------------
# §10 Validate

NOTE_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
PERIODIC_RE = re.compile(r"^\d{4}-(W\d{2}|Q\d)-review\.md$")
NAME_EXCEPTIONS = {"AGENTS.md", "CLAUDE.md", "README.md"}
EXACT_NOTE_PATH_EXCEPTIONS = frozenset({AYMT_RELPATH, HOME_RELPATH})
FM_WARNING_RULES = {"tags-not-a-list"}
SKILLS_PREFIX = "10_Agents/skills/"


def valid_note_filename(rel: str) -> bool:
    """Apply exact framework exceptions without weakening ordinary kebab-case."""
    name = rel.rsplit("/", 1)[-1]
    expected_case = CORE_FRAMEWORK_CASE.get(rel.casefold())
    if expected_case is not None:
        return rel == expected_case
    if rel.casefold() in {path.casefold() for path in EXACT_NOTE_PATH_EXCEPTIONS}:
        return rel in EXACT_NOTE_PATH_EXCEPTIONS
    return bool(
        NOTE_NAME_RE.match(name)
        or name in NAME_EXCEPTIONS
        or PERIODIC_RE.match(name)
        or (name == "SKILL.md" and rel.startswith(SKILLS_PREFIX))
    )


def is_template(rel: str) -> bool:
    return rel.startswith("09_Templates/")


def has_placeholder(value) -> bool:
    if isinstance(value, str):
        return "{{" in value
    if isinstance(value, list):
        return any(isinstance(v, str) and "{{" in v for v in value)
    return False


def run_validate(
    root: Path,
    check_index: bool,
    requested_environment: str | None = None,
) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []

    def err(path: str, rule: str, message: str, line: int | None = None):
        errors.append({"line": line, "message": message, "path": path, "rule": rule})

    def warn(path: str, rule: str, message: str, line: int | None = None):
        warnings.append({"line": line, "message": message, "path": path, "rule": rule})

    _manifests, environment_findings = load_environment_manifests(root)
    for finding in environment_findings:
        err(
            finding["path"],
            finding["rule"],
            finding["message"],
        )
    # Validation is the CI-safe all-clone diagnostic: validate every tracked
    # manifest envelope, but never require this machine to match one and never
    # read a foreign environment's note bodies. Current-scoped query and
    # maintenance commands still fail closed in main() before corpus access.
    notes, assets = walk_corpus(root, selected_environment=None)
    index = build_index(root, notes, assets)
    taxonomy = load_taxonomy(root)
    if taxonomy is None:
        err(
            CONVENTIONS_RELPATH,
            "conventions-table-unreadable",
            "cannot read the authoritative Tag Namespaces table",
        )

    # §15 vault config: parse + semantic findings land on the config file
    # itself (per-file, never a crash); write_exception_prefixes(config) is
    # where the Inbox-first write-destination policy is materialized for
    # enforcement (harness write-gates call agent_write_allowed).
    config, cfg_findings = load_config(root)
    cfg_errors, cfg_warnings = check_config(root, config, cfg_findings)
    for f in cfg_errors:
        err(CONFIG_RELPATH, f["rule"], f["message"], f["line"])
    for f in cfg_warnings:
        warn(CONFIG_RELPATH, f["rule"], f["message"], f["line"])

    errors.extend(scan_secrets(root, notes + assets))

    folded: dict[str, list[str]] = {}
    for p in notes + assets:
        folded.setdefault(fold(p), []).append(p)
    for group in folded.values():
        if len(group) > 1:
            group = sorted(group)
            err(
                group[0],
                "path-collision",
                "collides case-insensitively with " + ", ".join(group[1:]),
            )

    # §8.3/§10.2 restricted containment: notes tagged restricted/private
    # (frontmatter tags only — bodyTags never trigger restriction).
    restricted_paths = {p for p, r in index["notes"].items() if is_restricted(r)}

    for rel in notes:
        rec = index["notes"][rel]
        template = is_template(rel)
        exempt_frontmatter = rel == "CLAUDE.md"

        name = rel.rsplit("/", 1)[-1]
        if not valid_note_filename(rel):
            err(rel, "filename-convention", f"filename {name!r} is not kebab-case")

        if not exempt_frontmatter:
            fm = rec["frontmatter"]
            for fe in rec["frontmatterErrors"]:
                rule = fe.split(":", 1)[0]
                if rule in FM_WARNING_RULES or rule == "duplicate-key":
                    warn(rel, rule, fe)
                elif rule == "invalid-updated" and template and has_placeholder(
                    fm.get("updated")
                ):
                    continue
                elif rule == "invalid-expires" and template and has_placeholder(
                    fm.get("expires")
                ):
                    continue
                else:
                    err(rel, rule, fe)
            if {"not-utf8", "not-readable"} & set(rec["frontmatterErrors"]):
                # §10.2: the read/decode failure is the note's only finding —
                # frontmatter was never read, so derived missing-* checks
                # would be false claims that bury the actual cause.
                pass
            elif not fm:
                if "unterminated-frontmatter" not in rec["frontmatterErrors"]:
                    err(rel, "missing-frontmatter", "note has no frontmatter block")
            else:
                if rec["title"] is None and not (
                    template and has_placeholder(fm.get("title"))
                ):
                    err(rel, "missing-title", "frontmatter lacks a title string")
                raw_tags = fm.get("tags")
                if raw_tags is None or raw_tags == []:
                    # §10.2: an explicitly empty list declares no tags — same
                    # missing-tags error as an absent/null key. The per-value
                    # template exemption cannot apply: no values to exempt.
                    err(rel, "missing-tags", "frontmatter lacks a tags list")
                if "updated" not in fm:
                    err(rel, "missing-updated", "frontmatter lacks an updated date")
                tags = raw_tags if isinstance(raw_tags, list) else (
                    [raw_tags] if isinstance(raw_tags, str) else []
                )
                for tag in tags:
                    if template and "{{" in tag:
                        continue
                    if "/" not in tag:
                        err(rel, "tag-not-namespaced", f"tag {tag!r} has no namespace")
                        continue
                    if taxonomy is None:
                        continue
                    namespace, value = tag.split("/", 1)
                    if namespace not in taxonomy:
                        err(rel, "unknown-namespace", f"tag namespace {namespace!r} is not in conventions")
                    elif taxonomy[namespace] is not None and value not in taxonomy[namespace]:
                        err(
                            rel,
                            "unknown-tag-value",
                            f"tag {tag!r} is not in the conventions value list",
                        )
                # §10.2 missing-author (issue #18 provenance): an Inbox note
                # tagged as agent-authored draft should say which harness wrote
                # it. Warning only — absence elsewhere means pre-convention or
                # human-authored. Template placeholders satisfy per §10.3, and
                # `09_Templates/` never sits under `02_Inbox/` anyway.
                if (
                    rel.startswith("02_Inbox/")
                    and not template
                    and "audience/agent" in tags
                    and "workflow/draft" in tags
                    and not fm.get("author")
                ):
                    warn(
                        rel,
                        "missing-author",
                        "agent-authored Inbox note has no author: field "
                        "(see conventions § Provenance)",
                    )

        # §17.2 task-invalid-date: a date-bearing task emoji whose value is
        # not a real YYYY-MM-DD. Warning only — tasks are informal body
        # content (same posture as bodyTags); template placeholders exempt.
        for task in rec["tasks"]:
            if template and "{{" in task["text"]:
                continue
            for field in task["malformed"]:
                warn(
                    rel,
                    "task-invalid-date",
                    f"task {field} metadata is not a real YYYY-MM-DD date",
                    task["line"],
                )

        for link in rec["links"]:
            if link["placeholder"]:
                continue
            status = link["resolution"]["status"]
            if status == "unsupported-block-reference":
                warn(
                    rel,
                    "unsupported-block-reference",
                    f"{link['raw']} uses an unsupported block reference",
                    link["line"],
                )
            if link["resolved"] is None:
                if status == "ambiguous":
                    err(
                        rel,
                        "ambiguous-link",
                        f"{link['raw']} has multiple path or heading candidates",
                        link["line"],
                    )
                    continue
                hints = [w[len("title-match:") :] for w in link["warnings"]]
                message = f"unresolved link {link['raw']}"
                if hints:
                    message += " (title matches: " + ", ".join(hints) + ")"
                err(rel, "unresolved-link", message, link["line"])
            else:
                if link["resolved"] in restricted_paths and rel not in restricted_paths:
                    # §10.2 restricted-link (issue #17): context bleed —
                    # restricted -> restricted links stay clean.
                    warn(
                        rel,
                        "restricted-link",
                        f"{link['raw']} links a restricted/private note "
                        f"({link['resolved']}) from a non-restricted one — "
                        "never quote or summarize its content here",
                        link["line"],
                    )
                for w in link["warnings"]:
                    if w in {"case-mismatch", "fragment-case-mismatch"}:
                        warn(rel, "case-mismatch", f"{link['raw']} differs in case from {link['resolved']}", link["line"])

    skill_dirs: dict[str, list[str]] = {}
    for rel in notes:
        if rel.startswith(SKILLS_PREFIX) and "/" in rel[len(SKILLS_PREFIX) :]:
            skill_dirs.setdefault(rel[len(SKILLS_PREFIX) :].split("/", 1)[0], []).append(rel)
    for dirname in sorted(skill_dirs):
        skill_md = f"{SKILLS_PREFIX}{dirname}/SKILL.md"
        if skill_md not in index["notes"]:
            err(f"{SKILLS_PREFIX}{dirname}/", "skill-missing", "skill directory has no SKILL.md")
            continue
        fm = index["notes"][skill_md]["frontmatter"]
        if fm.get("name") != dirname:
            err(
                skill_md,
                "skill-name-mismatch",
                f"frontmatter name {fm.get('name')!r} != directory name {dirname!r}",
            )
        description = fm.get("description")
        if not (isinstance(description, str) and description.strip()):
            err(skill_md, "skill-missing-description", "frontmatter lacks a description string")

    if VALIDATE_CURATION_WARNINGS:
        cur = compute_curation(root, index, today())
        for rel in cur["missingExpires"]:
            warn(rel, "missing-expires", "no expires: date (see conventions § Expiration)")
        for row in cur["beyondCap"]:
            warn(
                row["path"],
                "expires-beyond-cap",
                f"expires {row['expires']} is more than a year after updated {row['updated']}",
            )
        for row in cur["oversized"]:
            warn(
                row["path"],
                "oversized",
                f"{row['sizeBytes']} bytes / {row['lines']} lines exceeds "
                f"{CURATE_MAX_BYTES} bytes / {CURATE_MAX_LINES} lines — split candidate",
            )
        ctx = context_report(root)
        for row in ctx["docs"]:
            if row["sizeBytes"] is not None and row["sizeBytes"] > row["budget"]:
                warn(
                    row["path"],
                    "bootstrap-budget",
                    f"{row['sizeBytes']} bytes exceeds its {row['budget']}-byte bootstrap budget",
                )
        if ctx["totalBytes"] > ctx["totalBudget"]:
            warn(
                "AGENTS.md",
                "bootstrap-budget-total",
                f"bootstrap docs total {ctx['totalBytes']} bytes, budget {ctx['totalBudget']}",
            )

    if check_index:
        tnotes, tassets = index_corpus(root)
        fresh = serialize(reduce_restricted(build_index(root, tnotes, tassets)))
        index_path = root / INDEX_RELPATH
        if not index_path.exists() or index_path.read_bytes() != fresh:
            err(INDEX_RELPATH, "stale-index", "stale index — run `brain index`")

    def key(f: dict):
        return (f["path"], 0 if f["line"] is None else 1, f["line"] or 0, f["rule"])

    return sorted(errors, key=key), sorted(warnings, key=key)


# ---------------------------------------------------------------------------
# §14 Curation signals


def today() -> date:
    return date.today()


def path_exempt_from_expires(rel: str) -> bool:
    """Directory/path-based exemption: notes reached by convention, not by
    inbound links (Inbox, Journal, Archives, Templates, solutions, Outbox)."""
    return rel in EXPIRES_EXEMPT_PATHS or rel.startswith(EXPIRES_EXEMPT_PREFIXES)


def note_type_tags(fm: dict) -> set[str]:
    tags = fm.get("tags")
    tags = tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])
    return {t.split("/", 1)[1] for t in tags if isinstance(t, str) and t.startswith("type/")}


def expires_exempt(rel: str, fm: dict) -> bool:
    """Whether a note is exempt from carrying an expires: date — by path, or
    by an event-record type tag (e.g. type/decision)."""
    return path_exempt_from_expires(rel) or bool(
        note_type_tags(fm) & EXPIRES_EXEMPT_TYPE_TAGS
    )


def compute_curation(root: Path, index: dict, today_d: date) -> dict:
    """All re-review signals, deterministic given the tree and today's date.
    Detection lives here; the judgment lives in the curate skill."""
    notes = index["notes"]
    expired: list[dict] = []
    missing: list[str] = []
    beyond_cap: list[dict] = []
    oversized: list[dict] = []
    stale: list[dict] = []
    orphans: list[str] = []
    for rel in sorted(notes):
        rec = notes[rel]
        fm = rec["frontmatter"]
        if rel == "CLAUDE.md":
            continue
        exp_d = iso_date(fm.get("expires"))
        upd_d = iso_date(rec["updated"])
        if exp_d:
            if exp_d < today_d:
                expired.append(
                    {"expires": fm["expires"], "path": rel, "title": rec["title"]}
                )
            if upd_d and (exp_d - upd_d).days > EXPIRES_CAP_DAYS:
                beyond_cap.append(
                    {"expires": fm["expires"], "path": rel, "updated": rec["updated"]}
                )
        elif "expires" not in fm and fm and not expires_exempt(rel, fm) and not is_template(rel):
            missing.append(rel)
        if not (rel in OVERSIZED_EXEMPT_PATHS or rel.startswith("07_Archives/")):
            try:
                text, _ = load_text(root, rel)
            except OSError:  # §3 read failure: skip, best-effort
                text = None
            lines = len(text.splitlines()) if text else 0
            if rec["sizeBytes"] > CURATE_MAX_BYTES or lines > CURATE_MAX_LINES:
                oversized.append(
                    {"lines": lines, "path": rel, "sizeBytes": rec["sizeBytes"]}
                )
        if upd_d:
            days = (today_d - upd_d).days
            if days > CURATE_STALE_DAYS:
                stale.append(
                    {
                        "backlinks": len(rec["backlinks"]),
                        "daysOld": days,
                        "path": rel,
                        "score": days * (1 + len(rec["backlinks"])),
                        "updated": rec["updated"],
                    }
                )
        if (
            not rec["backlinks"]
            and not path_exempt_from_expires(rel)
            and rel not in ORPHAN_EXEMPT_PATHS
        ):
            orphans.append(rel)
    stale.sort(key=lambda r: (-r["score"], r["path"]))
    referenced = {
        link["resolved"]
        for rec in notes.values()
        for link in rec["links"]
        if link["resolved"]
    }
    unreferenced_assets = [
        a
        for a in index["assets"]
        if a.startswith("08_Assets/") and a not in referenced
    ]
    return {
        "beyondCap": beyond_cap,
        "expired": expired,
        "missingExpires": missing,
        "orphans": orphans,
        "oversized": oversized,
        "stale": stale,
        "unreferencedAssets": unreferenced_assets,
    }


def context_report(root: Path) -> dict:
    """R20: bootstrap docs' actual sizes against their byte budgets."""
    docs: list[dict] = []
    total = 0
    for rel in sorted(BOOTSTRAP_BUDGETS):
        budget = BOOTSTRAP_BUDGETS[rel]
        try:
            _, size = load_text(root, rel)
        except OSError:
            size = None
        if size is not None:
            total += size
        docs.append({"budget": budget, "path": rel, "sizeBytes": size})
    return {"docs": docs, "totalBudget": BOOTSTRAP_TOTAL_BUDGET, "totalBytes": total}


# ---------------------------------------------------------------------------
# §16 Health report

INBOX_PREFIX = "02_Inbox/"
# Boundary lookahead: '2026-08-1234-note.md' must NOT parse as 2026-08-12.
INBOX_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?=[-.]|$)")
REPORT_BUCKET_LABELS = ("0-7d", "8-30d", "31-90d", "90+d", "unknown")
REPORT_ORPHAN_EXEMPT_BASENAMES = frozenset({"AGENTS.md", "CLAUDE.md", "README.md"})
REPORT_ORPHAN_EXEMPT_PREFIXES = ("07_Archives/", "09_Templates/")


def frontmatter_tags(rec: dict) -> list[str]:
    """§16.1: a note's frontmatter tags (bare scalar coerced per §4.5),
    template placeholders excluded. Body #tags are informal — never counted."""
    tags = rec["frontmatter"].get("tags")
    tags = tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])
    return [t for t in tags if isinstance(t, str) and "{{" not in t]


def is_abbreviation(short: str, long: str) -> bool:
    """§16.1 near-duplicate heuristic: `short` (folded, ≥ 2 chars, strictly
    shorter) shares its first character with `long` and is an in-order
    subsequence of it — catches both prefixes (`tool`/`tools`) and
    abbreviations (`sw`/`software`)."""
    if len(short) < 2 or len(short) >= len(long) or short[0] != long[0]:
        return False
    it = iter(long)
    return all(ch in it for ch in short)


def age_bucket(days: int) -> str:
    if days <= 7:
        return "0-7d"
    if days <= 30:
        return "8-30d"
    if days <= 90:
        return "31-90d"
    return "90+d"


def compute_report(
    index: dict,
    today_d: date,
    thresholds: dict,
    taxonomy: dict[str, list[str] | None] | None,
    since_d: date | None = None,
) -> dict:
    """§16: the five vault-health sections, synthesized from the in-memory
    index — no new parsing, deterministic given tree + config + date."""
    notes = index["notes"]

    def in_window(rec: dict) -> bool:
        # §16.3: --since scopes tag drift and unresolved links only.
        if since_d is None:
            return True
        upd = iso_date(rec["updated"])
        return upd is not None and upd >= since_d

    # 1. Stale-active + 2. Orphans (whole vault, never --since-scoped).
    stale_active: list[dict] = []
    orphans: list[str] = []
    for rel in sorted(notes):
        rec = notes[rel]
        upd_d = iso_date(rec["updated"])
        if "status/active" in frontmatter_tags(rec) and upd_d is not None:
            days = (today_d - upd_d).days
            if days > thresholds["staleDays"]:
                stale_active.append(
                    {
                        "daysOld": days,
                        "path": rel,
                        "title": rec["title"],
                        "updated": rec["updated"],
                    }
                )
        outgoing = any(not l["placeholder"] for l in rec["links"])
        if (
            not rec["backlinks"]
            and not outgoing
            and rel.rsplit("/", 1)[-1] not in REPORT_ORPHAN_EXEMPT_BASENAMES
            and not rel.startswith(REPORT_ORPHAN_EXEMPT_PREFIXES)
        ):
            orphans.append(rel)
    stale_active.sort(key=lambda r: (-r["daysOld"], r["path"]))

    # 3. Inbox aging (whole vault, never --since-scoped).
    buckets: dict[str, list[dict]] = {label: [] for label in REPORT_BUCKET_LABELS}
    triage_debt: list[str] = []
    for rel in sorted(notes):
        if not rel.startswith(INBOX_PREFIX):
            continue
        name = rel.rsplit("/", 1)[-1]
        if name == "README.md":
            continue
        rec = notes[rel]
        m = INBOX_DATE_PREFIX_RE.match(name)
        captured = iso_date(m.group(1)) if m else None
        if captured is not None:
            source = "filename"
        else:
            captured = iso_date(rec["updated"])
            source = "updated" if captured is not None else "unknown"
        if captured is None:
            buckets["unknown"].append({"ageDays": None, "path": rel, "source": source})
            continue
        days = max(0, (today_d - captured).days)
        buckets[age_bucket(days)].append(
            {"ageDays": days, "path": rel, "source": source}
        )
        if days > thresholds["inboxDays"]:
            triage_debt.append(rel)

    # 4. Tag drift (--since-scoped) — same taxonomy machinery as validate.
    counts: dict[str, int] = {}
    for rel in sorted(notes):
        rec = notes[rel]
        if not in_window(rec):
            continue
        for tag in sorted(set(frontmatter_tags(rec))):
            counts[tag] = counts.get(tag, 0) + 1
    unknown: list[dict] = []
    single_use: list[str] = []
    near_duplicates: list[dict] = []
    if taxonomy is not None:
        open_values: dict[str, set[str]] = {}
        for tag in sorted(counts):
            if "/" not in tag:
                unknown.append({"count": counts[tag], "reason": "not-namespaced", "tag": tag})
                continue
            namespace, value = tag.split("/", 1)
            if namespace not in taxonomy:
                unknown.append(
                    {"count": counts[tag], "reason": "unknown-namespace", "tag": tag}
                )
            elif taxonomy[namespace] is not None and value not in taxonomy[namespace]:
                unknown.append(
                    {"count": counts[tag], "reason": "unknown-value", "tag": tag}
                )
            else:
                if taxonomy[namespace] is None:
                    open_values.setdefault(namespace, set()).add(value)
                    if counts[tag] == 1:
                        single_use.append(tag)
        for namespace in sorted(open_values):
            values = sorted(open_values[namespace])
            for a in values:
                for b in values:
                    if a != b and is_abbreviation(fold(a), fold(b)):
                        near_duplicates.append({"namespace": namespace, "values": [a, b]})

    # 5. Unresolved links (--since-scoped) — same population validate errors on.
    unresolved: list[dict] = []
    for rel in sorted(notes):
        rec = notes[rel]
        if not in_window(rec):
            continue
        for link in rec["links"]:
            if not link["placeholder"] and link["resolved"] is None:
                unresolved.append(
                    {"line": link["line"], "path": rel, "target": link["target"]}
                )
    unresolved.sort(key=lambda r: (r["path"], r["line"], r["target"]))

    return {
        "inboxAging": {"buckets": buckets, "triageDebt": triage_debt},
        "orphans": orphans,
        "since": since_d.isoformat() if since_d else None,
        "staleActive": stale_active,
        "tagDrift": {
            "nearDuplicates": near_duplicates,
            "singleUse": single_use,
            "taxonomyReadable": taxonomy is not None,
            "unknown": unknown,
        },
        "thresholds": dict(sorted(thresholds.items())),
        "unresolvedLinks": {"count": len(unresolved), "links": unresolved},
    }


URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")


def collect_urls(root: Path, notes: list[str]) -> dict[str, str]:
    """url -> first note path mentioning it. Frontmatter and code (fenced
    blocks + inline spans) are excluded, matching the link/tag extractors —
    so example URLs in code samples are never probed as source URLs."""
    found: dict[str, str] = {}
    for rel in notes:
        try:
            text, _ = load_text(root, rel)
        except OSError:  # §3 read failure: skip, best-effort
            continue
        if text is None:
            continue
        lines = text.split("\n")
        _fm, _errs, body_start, _has = parse_frontmatter(lines)
        for _lineno, _raw, masked in body_lines_masked(lines, body_start):
            for m in URL_RE.finditer(masked):
                url = m.group(0).rstrip(".,;:!?")
                found.setdefault(url, rel)
    return found


def check_urls(root: Path, notes: list[str]) -> list[dict]:
    """Opt-in (network): dead source URLs. Never runs pre-commit."""
    import urllib.error
    import urllib.request

    dead: list[dict] = []
    urls = collect_urls(root, notes)
    for url in sorted(urls):
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "brain-curate/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.HTTPError as e:
            if e.code in (403, 405):  # HEAD-hostile hosts are not dead links
                continue
            dead.append({"error": f"HTTP {e.code}", "path": urls[url], "url": url})
        except (urllib.error.URLError, OSError, ValueError) as e:
            dead.append({"error": str(e), "path": urls[url], "url": url})
    return dead


# ---------------------------------------------------------------------------
# §18 Semantic search (QMD — issue #8)
#
# Module-internal store section: the sidecar (EMBED_RELPATH, gitignored) is
# read and written ONLY here, and only `embed` and `search --semantic` ever
# touch it — index/validate output is provably unaffected (§17.5). The one
# sanctioned optional non-stdlib dependency (sentence-transformers) is
# imported lazily inside local_embedder(); every other path is stdlib.

EMBED_SCHEMA_VERSION = 1
EMBED_LOCAL_MODEL_DEFAULT = "all-MiniLM-L6-v2"
# §18.4 hybrid ranking weights: score = 0.7·sem + 0.3·kw, rounded to 6 dp.
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3
SEMANTIC_TOP_DEFAULT = 10


def note_content_hash(text: str) -> str:
    """§17.1: SHA-256 hex over the note's full normalized text (§3)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _empty_store() -> dict:
    return {"dim": None, "model": None, "notes": {}, "schemaVersion": EMBED_SCHEMA_VERSION}


def _valid_vector(v, dim: int | None = None) -> bool:
    """A non-empty list of finite numbers (bools excluded), optionally of
    exactly `dim` components."""
    return (
        isinstance(v, list)
        and bool(v)
        and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
            for x in v
        )
        and (dim is None or len(v) == dim)
    )


def load_embeddings(root: Path) -> dict:
    """§18.2: best-effort sidecar load. Missing file -> empty store; any
    malformed content is treated as absent with a stderr notice. Never raises."""

    def ignored(reason: str) -> dict:
        print(
            f"warning: ignoring embeddings sidecar ({reason}) — "
            "regenerate it with `brain embed`",
            file=sys.stderr,
        )
        return _empty_store()

    path = root / EMBED_RELPATH
    if not path.exists():
        return _empty_store()
    try:
        raw = path.read_bytes()
    except OSError:
        return ignored("not readable")
    try:
        store = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ignored("not valid JSON")
    if not isinstance(store, dict) or store.get("schemaVersion") != EMBED_SCHEMA_VERSION:
        return ignored("unknown schemaVersion")
    dim, model, entries = store.get("dim"), store.get("model"), store.get("notes")
    if not (
        isinstance(dim, int)
        and not isinstance(dim, bool)
        and dim > 0
        and isinstance(model, str)
        and model
        and isinstance(entries, dict)
    ):
        return ignored("invalid shape")
    for rel, entry in entries.items():
        if not (
            isinstance(rel, str)
            and isinstance(entry, dict)
            and isinstance(entry.get("hash"), str)
            and _valid_vector(entry.get("vector"), dim)
        ):
            return ignored("invalid entry shape")
    return {"dim": dim, "model": model, "notes": entries, "schemaVersion": EMBED_SCHEMA_VERSION}


def save_embeddings(root: Path, store: dict) -> None:
    """§17.1 serialization: like the index (§8.2) but floats are allowed."""
    path = root / EMBED_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")
    )


def cosine(a: list[float], b: list[float]) -> float:
    """§18.4 cosine similarity; zero-magnitude vectors give 0.0."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def note_hashes(root: Path, index: dict) -> dict[str, str | None]:
    """path -> current content hash; None for notes that cannot be read or
    decoded (§3) — such notes are never embeddable."""
    hashes: dict[str, str | None] = {}
    for rel in index["notes"]:
        try:
            text, _ = load_text(root, rel)
        except OSError:
            text = None
        hashes[rel] = None if text is None else note_content_hash(text)
    return hashes


def fresh_entries(index: dict, store: dict, hashes: dict) -> dict[str, list[float]]:
    """§18.2 freshness ∩ §18.1 restricted containment: path -> vector for
    every sidecar entry that is current (note exists, hash matches, length
    == dim) and whose note is not currently restricted/private. Everything
    else is stale — excluded, never re-ranked."""
    fresh: dict[str, list[float]] = {}
    for rel, entry in store["notes"].items():
        rec = index["notes"].get(rel)
        if rec is None or is_restricted(rec):
            continue
        if (
            hashes.get(rel) is not None
            and entry["hash"] == hashes[rel]
            and len(entry["vector"]) == store["dim"]
        ):
            fresh[rel] = entry["vector"]
    return fresh


def embeddable_notes(index: dict, hashes: dict) -> list[str]:
    """§18.3: the embeddable universe — readable, non-restricted notes."""
    return sorted(
        rel
        for rel, rec in index["notes"].items()
        if hashes[rel] is not None and not is_restricted(rec)
    )


def local_embedder(model_name: str):
    """§17.3: the ONE sanctioned optional non-stdlib dependency
    (sentence-transformers), imported lazily and only here. Returns a
    texts -> vectors callable, or None when the import or model load fails —
    callers degrade cleanly, never crash."""
    try:
        from sentence_transformers import SentenceTransformer  # optional — §17.3
    except Exception:
        return None
    try:
        model = SentenceTransformer(model_name)
    except Exception:
        return None

    def encode(texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vec] for vec in model.encode(texts)]

    return encode


def cmd_embed(root: Path, args) -> int:
    """§18.3: maintain the embeddings sidecar (--stdin-json / --local /
    --status). Exit 0 success, 1 operational error; the sidecar is written
    only on a fully-validated update."""
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    store = load_embeddings(root)
    hashes = note_hashes(root, index)

    if args.status:
        fresh = fresh_entries(index, store, hashes)
        universe = embeddable_notes(index, hashes)
        payload = {
            "dim": store["dim"],
            "embedded": len(fresh),
            "missing": len([r for r in universe if r not in store["notes"]]),
            "model": store["model"],
            "notes": len(universe),
            "present": (root / EMBED_RELPATH).exists(),
            "stale": len([r for r in store["notes"] if r not in fresh]),
        }
        emit(
            payload,
            args.json,
            [
                f"sidecar: {EMBED_RELPATH} "
                f"({'present' if payload['present'] else 'absent'})",
                f"model: {payload['model']}  dim: {payload['dim']}",
                f"embeddable notes: {payload['notes']}  fresh: {payload['embedded']}  "
                f"stale: {payload['stale']}  missing: {payload['missing']}",
            ],
        )
        return 0

    if args.stdin_json:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"error: --stdin-json input is not valid JSON: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, dict) or set(data) != {"model", "vectors"}:
            print(
                'error: input must be an object with exactly the keys "model" and "vectors"',
                file=sys.stderr,
            )
            return 1
        if not (isinstance(data["model"], str) and data["model"].strip()):
            print("error: model must be a non-empty string", file=sys.stderr)
            return 1
        if not (isinstance(data["vectors"], dict) and data["vectors"]):
            print(
                "error: vectors must be a non-empty object of note path -> number array",
                file=sys.stderr,
            )
            return 1
        model = data["model"].strip()
        vectors: dict[str, list[float]] = {}
        dim: int | None = None
        unknown: list[str] = []
        for key in sorted(data["vectors"]):
            vec = data["vectors"][key]
            if not _valid_vector(vec):
                print(
                    f"error: vector for {key!r} must be a non-empty array of finite numbers",
                    file=sys.stderr,
                )
                return 1
            if dim is None:
                dim = len(vec)
            elif len(vec) != dim:
                print(
                    f"error: vector for {key!r} has length {len(vec)}, expected {dim} "
                    "— all vectors must share one dimension",
                    file=sys.stderr,
                )
                return 1
            rel = nfc(key.strip()).replace("\\", "/").removeprefix("./")
            if rel not in index["notes"]:
                unknown.append(key)
                continue
            vectors[rel] = [float(x) for x in vec]
        if unknown:
            print(
                "error: unknown note paths (nothing written): " + ", ".join(unknown),
                file=sys.stderr,
            )
            return 1
        skipped_restricted = sorted(
            rel for rel in vectors if is_restricted(index["notes"][rel])
        )
        for rel in skipped_restricted:
            del vectors[rel]
            print(
                f"notice: skipping restricted note {rel} — restricted/private "
                "content never enters the embeddings sidecar (spec §18.1)",
                file=sys.stderr,
            )
        skipped_unreadable = sorted(rel for rel in vectors if hashes[rel] is None)
        for rel in skipped_unreadable:
            del vectors[rel]
            print(
                f"notice: skipping unreadable note {rel} — no text to hash (spec §17.3)",
                file=sys.stderr,
            )
        if store["notes"] and (store["model"] != model or store["dim"] != dim):
            print(
                f"notice: model/dim changed ({store['model']}/{store['dim']} -> "
                f"{model}/{dim}) — replacing the sidecar wholesale (spec §18.3)",
                file=sys.stderr,
            )
            merged: dict[str, dict] = {}
        else:
            # Switching environments must also prune the ignored local
            # sidecar: non-current vectors are derived content and cannot
            # survive merely because they remain fresh on another machine.
            merged = {
                rel: entry
                for rel, entry in store["notes"].items()
                if rel in index["notes"] and not is_restricted(index["notes"][rel])
            }
        for rel, vec in vectors.items():
            merged[rel] = {"hash": hashes[rel], "vector": vec}
        save_embeddings(
            root,
            {"dim": dim, "model": model, "notes": merged, "schemaVersion": EMBED_SCHEMA_VERSION},
        )
        payload = {
            "dim": dim,
            "model": model,
            "path": EMBED_RELPATH,
            "skippedRestricted": skipped_restricted,
            "skippedUnreadable": skipped_unreadable,
            "stored": len(vectors),
        }
        emit(
            payload,
            args.json,
            [
                f"stored {len(vectors)} vectors (model {model}, dim {dim}) "
                f"-> {EMBED_RELPATH}"
            ]
            + [f"skipped restricted: {r}" for r in skipped_restricted]
            + [f"skipped unreadable: {r}" for r in skipped_unreadable],
        )
        return 0

    # --local (§17.3): the offline path via the optional dependency.
    model_name = args.model or store["model"] or EMBED_LOCAL_MODEL_DEFAULT
    encode = local_embedder(model_name)
    if encode is None:
        print(
            "error: local embedding model unavailable — install the optional "
            "`sentence-transformers` package, pipe precomputed vectors via "
            "`brain embed --stdin-json`, or use keyword `brain search` (spec §18.3)",
            file=sys.stderr,
        )
        return 1
    if store["notes"] and store["model"] != model_name:
        print(
            f"notice: model changed ({store['model']} -> {model_name}) — "
            "replacing the sidecar wholesale (spec §18.3)",
            file=sys.stderr,
        )
        store = _empty_store()
    fresh = fresh_entries(index, store, hashes)
    todo = [rel for rel in embeddable_notes(index, hashes) if rel not in fresh]
    texts: list[str] = []
    for rel in todo:
        text, _ = load_text(root, rel)  # readable by construction (hash present)
        texts.append(text)
    vecs = encode(texts) if todo else []
    dim = store["dim"]
    merged = {rel: store["notes"][rel] for rel in fresh}
    if not todo and not merged:
        # Nothing to embed and nothing retained: writing a {"dim": null}
        # store would be shape-invalid (§18.1) — report and leave it absent.
        print("nothing to embed — sidecar unchanged", file=sys.stderr)
        return 0
    for rel, vec in zip(todo, vecs):
        if dim is None:
            dim = len(vec)
        merged[rel] = {"hash": hashes[rel], "vector": vec}
    save_embeddings(
        root,
        {"dim": dim, "model": model_name, "notes": merged, "schemaVersion": EMBED_SCHEMA_VERSION},
    )
    payload = {
        "dim": dim,
        "embedded": len(todo),
        "model": model_name,
        "path": EMBED_RELPATH,
        "total": len(merged),
    }
    emit(
        payload,
        args.json,
        [
            f"embedded {len(todo)} notes (model {model_name}, dim {dim}), "
            f"{len(merged)} total -> {EMBED_RELPATH}"
        ],
    )
    return 0


def semantic_search(root: Path, index: dict, args) -> int:
    """§18.4: hybrid semantic+keyword note ranking, degrading to the plain
    keyword search (exit 0, identical output shape) whenever semantic
    ranking is impossible."""
    store = load_embeddings(root)
    hashes = note_hashes(root, index)
    fresh = fresh_entries(index, store, hashes)

    def degrade(reason: str) -> int:
        print(
            f"notice: semantic search unavailable ({reason}) — falling back to "
            "keyword search; populate the sidecar with `brain embed` (spec §18.4)",
            file=sys.stderr,
        )
        emit_keyword_hits(keyword_hits(root, index, args.query, args.tag), args.json)
        return 0

    if not fresh:
        return degrade("no fresh embeddings")

    qvec: list[float] | None = None
    if args.query_vector:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"error: --query-vector stdin is not valid JSON: {e}", file=sys.stderr)
            return 1
        if not _valid_vector(data):
            print(
                "error: --query-vector must be a non-empty JSON array of finite numbers",
                file=sys.stderr,
            )
            return 1
        if len(data) != store["dim"]:
            print(
                f"error: --query-vector has length {len(data)}, store dim is {store['dim']}",
                file=sys.stderr,
            )
            return 1
        qvec = [float(x) for x in data]
    else:
        encode = local_embedder(store["model"])
        if encode is not None:
            try:
                qvec = encode([args.query])[0]
            except Exception:
                qvec = None
            if qvec is not None and len(qvec) != store["dim"]:
                qvec = None
    if qvec is None:
        return degrade("no query embedding source")

    kw_counts: dict[str, int] = {}
    for h in keyword_hits(root, index, args.query, args.tag):
        kw_counts[h["path"]] = kw_counts.get(h["path"], 0) + 1
    rows: list[dict] = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if args.tag and not all(tag_matches(t, effective_tags(rec)) for t in args.tag):
            continue
        vec = fresh.get(rel)
        kw = kw_counts.get(rel, 0)
        if vec is None and kw == 0:
            continue
        sem_raw = 0.0 if vec is None else (cosine(qvec, vec) + 1) / 2
        rows.append(
            {
                "keywordHits": kw,
                "path": rel,
                "score": round(
                    SEMANTIC_WEIGHT * sem_raw + KEYWORD_WEIGHT * (1.0 if kw else 0.0), 6
                ),
                "semanticScore": None if vec is None else round(sem_raw, 6),
                "title": rec["title"],
            }
        )
    rows.sort(key=lambda r: (-r["score"], r["path"]))
    rows = rows[: args.top]
    emit(
        rows,
        args.json,
        (
            f"{r['score']:.6f}  {r['path']}" + (f"  ({r['title']})" if r["title"] else "")
            for r in rows
        ),
    )
    return 0


# ---------------------------------------------------------------------------
# §9 CLI commands


def effective_tags(rec: dict) -> set[str]:
    tags = rec["frontmatter"].get("tags")
    fm_tags = tags if isinstance(tags, list) else ([tags] if isinstance(tags, str) else [])
    return set(fm_tags) | set(rec["bodyTags"])


def tag_matches(tag_filter: str, tags: set[str]) -> bool:
    if tag_filter.endswith("/*"):
        prefix = tag_filter[:-1]
        return any(t.startswith(prefix) for t in tags)
    return tag_filter in tags


# ---------------------------------------------------------------------------
# §22 Legacy-link migration


class LinkMigrationError(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(data: object) -> bytes:
    return json.dumps(
        data, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _raw_document(raw: bytes) -> tuple[str, list[str], list[int], int]:
    """Decode without newline conversion; offsets are raw UTF-8 byte offsets."""
    bom_bytes = 3 if raw.startswith(b"\xef\xbb\xbf") else 0
    try:
        text = raw[bom_bytes:].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LinkMigrationError("migration source is not UTF-8") from exc
    # Match the indexer's physical-line contract exactly: CRLF, CR, and LF
    # are line endings; Unicode NEL/VT/FF/line separators are ordinary body
    # characters rather than implicit lines.
    kept: list[str] = []
    start = 0
    cursor = 0
    while cursor < len(text):
        char = text[cursor]
        if char == "\r":
            cursor += 2 if cursor + 1 < len(text) and text[cursor + 1] == "\n" else 1
            kept.append(text[start:cursor])
            start = cursor
        elif char == "\n":
            cursor += 1
            kept.append(text[start:cursor])
            start = cursor
        else:
            cursor += 1
    if start < len(text):
        kept.append(text[start:])
    lines: list[str] = []
    offsets: list[int] = []
    offset = bom_bytes
    for physical in kept:
        offsets.append(offset)
        if physical.endswith("\r\n"):
            content = physical[:-2]
        elif physical.endswith(("\n", "\r")):
            content = physical[:-1]
        else:
            content = physical
        lines.append(content)
        offset += len(physical.encode("utf-8"))
    if not lines:
        lines = [""]
        offsets = [bom_bytes]
    return text, lines, offsets, bom_bytes


def _migration_links(raw: bytes) -> tuple[list[dict], list[dict]]:
    _text, lines, offsets, _bom = _raw_document(raw)
    _fm, _errors, body_start, _has = parse_frontmatter(lines)
    links, headings, _tags, _tasks = extract_body(
        lines, body_start, line_offsets=offsets
    )
    return links, headings


def _escape_markdown_label(label: str) -> str:
    return label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _encoded_relative_path(source: str, resolved: str) -> str:
    parent = posixpath.dirname(source) or "."
    relative = posixpath.relpath(resolved, parent)
    return quote(relative, safe="/-._~")


def render_migrated_link(source: str, link: dict) -> str:
    """Render a resolved wikilink as source-relative standard Markdown."""
    resolved = link["resolved"]
    if resolved is None:
        raise LinkMigrationError("cannot render an unresolved legacy link")
    fragment = link["resolution"].get("fragment")
    if link.get("fragment") and fragment is None:
        raise LinkMigrationError("cannot render an unresolved legacy fragment")
    if link["target"] == "" and fragment is not None:
        destination = ""
    else:
        destination = _encoded_relative_path(source, resolved)
    if fragment is not None:
        destination += "#" + quote(fragment["slug"], safe="-._~")
    if link["label"] is not None:
        label = link["label"]
    elif link["target"] == "" and link["fragment"]:
        label = link["fragment"]
    else:
        label = posixpath.basename(link["destination"] or resolved)
        if label.endswith(".md"):
            label = label[:-3]
    escaped = _escape_markdown_label(label)
    prefix = "!" if link["embed"] else ""
    return f"{prefix}[{escaped}]({destination})"


def _migration_blocker(path: str, link: dict, rule: str, message: str) -> dict:
    return {"line": link["line"], "message": message, "path": path, "rule": rule}


def build_link_migration_plan(root: Path) -> dict:
    """Build a deterministic, source-hashed preview without changing files."""
    notes, assets = walk_corpus(root)
    tracked = git_tracked(root)
    if tracked is not None:
        notes = [path for path in notes if path in tracked]
        assets = [path for path in assets if path in tracked]
    index = build_index(root, notes, assets)
    resolver = Resolver(
        notes, assets, {path: rec["title"] for path, rec in index["notes"].items()}
    )
    blockers: list[dict] = []
    edits: list[dict] = []
    summary = {
        "filesChanged": 0,
        "filesScanned": len(notes),
        "legacyLinks": 0,
        "linksConverted": 0,
        "markdownLinks": index["linkCounts"]["markdown"],
        "placeholders": 0,
        "unsupportedBlockReferences": 0,
    }
    for rel in notes:
        try:
            raw = _read_nofollow_bytes(root, rel)
            links, _headings = _migration_links(raw)
        except (OSError, LinkMigrationError):
            blockers.append(
                {"line": None, "message": "source is unreadable or unsafe", "path": rel, "rule": "unsafe-source"}
            )
            continue
        replacements: list[dict] = []
        previous_end = -1
        for link in links:
            if link["format"] != "wikilink":
                continue
            summary["legacyLinks"] += 1
            if link["placeholder"]:
                summary["placeholders"] += 1
                continue
            start = link["range"]["start"]["offset"]
            end = link["range"]["end"]["offset"]
            if any(
                other is not link
                and start < other["range"]["end"]["offset"]
                and other["range"]["start"]["offset"] < end
                for other in links
            ):
                blockers.append(
                    _migration_blocker(
                        rel,
                        link,
                        "overlapping-edits",
                        "legacy link overlaps another parsed link",
                    )
                )
                continue
            _resolve_link_record(link, rel, resolver, index["notes"])
            if link["resolution"]["status"] == "unsupported-block-reference":
                summary["unsupportedBlockReferences"] += 1
                blockers.append(
                    _migration_blocker(
                        rel,
                        link,
                        "unsupported-block-reference",
                        "legacy block references cannot be migrated safely",
                    )
                )
                continue
            if link["resolution"]["status"] == "ambiguous":
                blockers.append(
                    _migration_blocker(
                        rel,
                        link,
                        "ambiguous-link",
                        "legacy target or heading has multiple candidates",
                    )
                )
                continue
            if link["resolved"] is None:
                blockers.append(
                    _migration_blocker(
                        rel, link, "unresolved-link", "legacy target is unresolved"
                    )
                )
                continue
            if link["resolution"]["status"] == "unresolved-fragment":
                blockers.append(
                    _migration_blocker(
                        rel,
                        link,
                        "unresolved-fragment",
                        "legacy heading fragment has no matching heading",
                    )
                )
                continue
            if start < previous_end:
                blockers.append(
                    _migration_blocker(
                        rel, link, "overlapping-edits", "migration ranges overlap"
                    )
                )
                continue
            before_bytes = raw[start:end]
            try:
                before = before_bytes.decode("utf-8")
            except UnicodeDecodeError:
                blockers.append(
                    _migration_blocker(
                        rel, link, "invalid-range", "source range is not valid UTF-8"
                    )
                )
                continue
            if before != link["raw"]:
                blockers.append(
                    _migration_blocker(
                        rel, link, "stale-range", "source range does not match parsed link"
                    )
                )
                continue
            after = render_migrated_link(rel, link)
            replacements.append(
                {
                    "after": after,
                    "before": before,
                    "line": link["line"],
                    "range": {"end": end, "start": start},
                    "resolved": link["resolved"],
                }
            )
            previous_end = end
        if not replacements:
            continue
        desired = raw
        for replacement in reversed(replacements):
            start = replacement["range"]["start"]
            end = replacement["range"]["end"]
            desired = (
                desired[:start]
                + replacement["after"].encode("utf-8")
                + desired[end:]
            )
        summary["linksConverted"] += len(replacements)
        edits.append(
            {
                "mode": stat.S_IMODE(os.lstat(root / rel).st_mode),
                "path": rel,
                "replacements": replacements,
                "restricted": is_restricted(index["notes"][rel]),
                "resultSha256": _sha256_bytes(desired),
                "sourceSha256": _sha256_bytes(raw),
            }
        )
    edits.sort(key=lambda row: row["path"])
    blockers.sort(key=lambda row: (row["path"], row["line"] or 0, row["rule"]))
    summary["filesChanged"] = len(edits)
    body = {
        "blockers": blockers,
        "edits": edits,
        "regenerateRequired": [
            INDEX_RELPATH,
            ".vscode/second-brain.code-snippets",
            "generated skill adapters",
        ],
        "schemaVersion": LINK_MIGRATION_SCHEMA_VERSION,
        "status": "blocked" if blockers else "ready",
        "summary": summary,
    }
    body["planId"] = _sha256_bytes(_canonical_json(body))
    return body


def public_link_migration_plan(plan: dict) -> dict:
    """Redact restricted-note body prose from any serialized CLI plan."""
    public = json.loads(json.dumps(plan, ensure_ascii=False))
    for edit in public.get("edits", []):
        if not edit.get("restricted"):
            continue
        for replacement in edit.get("replacements", []):
            replacement["after"] = None
            replacement["before"] = None
            replacement["redacted"] = True
    return public


def _migration_planned_paths(plan: dict) -> list[str]:
    return sorted({row["path"] for row in plan.get("edits", [])})


def dirty_migration_paths(root: Path, plan: dict) -> list[str] | None:
    paths = _migration_planned_paths(plan)
    if not paths:
        return []
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=True,
            text=True,
        )
        if probe.stdout.strip() != "true":
            return None
        status_result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--",
                *paths,
            ],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return sorted(
        entry.decode("utf-8", "replace")
        for entry in status_result.stdout.split(b"\0")
        if entry
    )


def _validate_migration_plan(plan: dict) -> None:
    if not isinstance(plan, dict) or plan.get("schemaVersion") != LINK_MIGRATION_SCHEMA_VERSION:
        raise LinkMigrationError("unsupported or malformed migration plan")
    supplied = plan.get("planId")
    body = {key: value for key, value in plan.items() if key != "planId"}
    if not isinstance(supplied, str) or supplied != _sha256_bytes(_canonical_json(body)):
        raise LinkMigrationError("migration plan ID does not match its contents")
    if plan.get("blockers"):
        raise LinkMigrationError("migration plan has blockers")


def _desired_migration_bytes(source: bytes, row: dict) -> bytes:
    previous_end = -1
    replacements = row.get("replacements")
    if not isinstance(replacements, list):
        raise LinkMigrationError("malformed migration replacements")
    for replacement in replacements:
        source_range = replacement.get("range", {})
        start, end = source_range.get("start"), source_range.get("end")
        if type(start) is not int or type(end) is not int or start < previous_end or end <= start:
            raise LinkMigrationError("overlapping or malformed migration ranges")
        before = replacement.get("before")
        after = replacement.get("after")
        if not isinstance(before, str) or not isinstance(after, str):
            raise LinkMigrationError("malformed migration replacement text")
        if source[start:end] != before.encode("utf-8"):
            raise LinkMigrationError("stale migration replacement range")
        previous_end = end
    desired = source
    for replacement in reversed(replacements):
        start = replacement["range"]["start"]
        end = replacement["range"]["end"]
        desired = desired[:start] + replacement["after"].encode("utf-8") + desired[end:]
    if _sha256_bytes(desired) != row.get("resultSha256"):
        raise LinkMigrationError("migration result hash mismatch")
    return desired


def _migration_mutation_supported() -> bool:
    """Mutation needs held-parent descriptor operations; preview stays portable."""
    required = (os.open, os.rename, os.link, os.unlink, os.stat)
    return all(function in getattr(os, "supports_dir_fd", set()) for function in required)


def _open_migration_parent(root: Path, relative: str) -> tuple[int, str]:
    parts = Path(relative).parts
    if (
        not parts
        or Path(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise LinkMigrationError("migration source path is unsafe")
    directory = getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    if not directory or not nofollow:
        raise LinkMigrationError("safe link migration writes are unavailable on this runtime")
    descriptor = os.open(root, os.O_RDONLY | directory | cloexec)
    try:
        for part in parts[:-1]:
            child = os.open(
                part,
                os.O_RDONLY | directory | nofollow | cloexec,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor, parts[-1]
    except BaseException:
        os.close(descriptor)
        raise


def _read_migration_at(parent: int, name: str) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=parent)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise LinkMigrationError("migration source is not a regular file")
        chunks = []
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), info
    finally:
        os.close(descriptor)


def _link_migration_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        stat.S_IMODE(info.st_mode),
    )


def _unused_migration_name(parent: int, basename: str, kind: str) -> str:
    for _attempt in range(64):
        candidate = f".{basename}.migrate-{kind}-{secrets.token_hex(12)}"
        try:
            os.stat(candidate, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return candidate
    raise LinkMigrationError("cannot allocate a migration transaction name")


def _stage_migration_at(
    parent: int,
    basename: str,
    data: bytes,
    mode: int,
    *,
    ownership: dict | None = None,
    reserved_name: str | None = None,
) -> str:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    attempts = 1 if reserved_name is not None else 64
    for _attempt in range(attempts):
        name = reserved_name or f".{basename}.migrate-new-{secrets.token_hex(12)}"
        if reserved_name is not None and not _transaction_name_valid(
            name, basename, "new"
        ):
            raise LinkMigrationError("reserved migration name is unsafe")
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=parent)
        except FileExistsError:
            if reserved_name is not None:
                raise LinkMigrationError("reserved migration stage is occupied")
            continue
        created_info = os.fstat(descriptor)
        created_identity = (
            created_info.st_dev,
            created_info.st_ino,
            stat.S_IFMT(created_info.st_mode),
        )
        try:
            offset = 0
            while offset < len(data):
                offset += os.write(descriptor, data[offset:])
            os.fchmod(descriptor, stat.S_IMODE(mode))
            os.fsync(descriptor)
            if ownership is not None:
                ownership["identity"] = _link_migration_identity(
                    os.fstat(descriptor)
                )
        except BaseException:
            try:
                current = os.stat(
                    name, dir_fd=parent, follow_symlinks=False
                )
            except FileNotFoundError:
                pass
            else:
                current_identity = (
                    current.st_dev,
                    current.st_ino,
                    stat.S_IFMT(current.st_mode),
                )
                if current_identity == created_identity:
                    os.unlink(name, dir_fd=parent)
            finally:
                os.close(descriptor)
            raise
        os.close(descriptor)
        return name
    raise LinkMigrationError("cannot stage migration output")


def _remove_owned_migration_stage(item: dict) -> None:
    expected_identity = item.get("stage_ownership", {}).get("identity")
    if expected_identity is None:
        return
    try:
        contents, info = _read_migration_at(item["parent"], item["new"])
    except FileNotFoundError:
        return
    if (
        _link_migration_identity(info) != expected_identity
        or contents != item["desired"]
    ):
        raise LinkMigrationError(
            "migration stage ownership changed; foreign stage preserved"
        )
    os.unlink(item["new"], dir_fd=item["parent"])
    os.fsync(item["parent"])


def _remove_owned_migration_backup(item: dict) -> None:
    try:
        contents, info = _read_migration_at(item["parent"], item["backup"])
    except FileNotFoundError:
        return
    if (
        _link_migration_identity(info) != item["identity"]
        or contents != item["source"]
    ):
        raise LinkMigrationError(
            "migration backup ownership changed; foreign backup preserved"
        )
    os.unlink(item["backup"], dir_fd=item["parent"])
    os.fsync(item["parent"])


def _quarantine_migration_at(parent: int, name: str, backup: str) -> None:
    os.rename(name, backup, src_dir_fd=parent, dst_dir_fd=parent)
    os.fsync(parent)


def _install_migration_at(parent: int, staged: str, name: str) -> None:
    # Hard-link creation is atomic and refuses a concurrently recreated target.
    os.link(
        staged,
        name,
        src_dir_fd=parent,
        dst_dir_fd=parent,
        follow_symlinks=False,
    )
    os.fsync(parent)


def _verify_installed_migration(item: dict) -> None:
    actual, actual_info = _read_migration_at(item["parent"], item["name"])
    staged_info = os.stat(
        item["new"], dir_fd=item["parent"], follow_symlinks=False
    )
    if (
        actual != item["desired"]
        or stat.S_IMODE(actual_info.st_mode) != item["identity"][3]
        or (actual_info.st_dev, actual_info.st_ino)
        != (staged_info.st_dev, staged_info.st_ino)
    ):
        raise LinkMigrationError("migration result changed during apply")


def _restore_quarantined_at(parent: int, backup: str, name: str) -> bool:
    try:
        os.link(
            backup,
            name,
            src_dir_fd=parent,
            dst_dir_fd=parent,
            follow_symlinks=False,
        )
    except FileExistsError:
        return False
    os.fsync(parent)
    return True


def _journal_payload(plan: dict, prepared: list[dict]) -> dict:
    return {
        "committed": False,
        "owner": "brain-link-migration",
        "pid": os.getpid(),
        "planId": plan["planId"],
        "rows": [
            {
                "backup": item["backup"],
                "mode": item["identity"][3],
                "name": item["name"],
                "new": item["new"],
                "path": item["rel"],
                "resultSha256": _sha256_bytes(item["desired"]),
                "sourceSha256": _sha256_bytes(item["source"]),
            }
            for item in prepared
            if "new" in item
        ],
        "schemaVersion": LINK_MIGRATION_SCHEMA_VERSION,
    }


def _read_descriptor_bytes(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(descriptor, 64 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _journal_guard_matches(root_parent: int, guard: dict) -> bool:
    try:
        descriptor_info = os.fstat(guard["descriptor"])
        path_info = os.stat(
            LINK_MIGRATION_JOURNAL_RELPATH,
            dir_fd=root_parent,
            follow_symlinks=False,
        )
        return (
            _link_migration_identity(descriptor_info) == guard["identity"]
            and _link_migration_identity(path_info) == guard["identity"]
            and _read_descriptor_bytes(guard["descriptor"]) == guard["contents"]
        )
    except (OSError, KeyError):
        return False


def _close_migration_journal_guard(guard: dict | None) -> None:
    if guard is None:
        return
    try:
        os.close(guard["descriptor"])
    except OSError:
        pass


def _write_migration_journal(
    root_parent: int,
    payload: dict,
    *,
    create: bool,
    guard: dict | None = None,
) -> dict:
    """Create once with O_EXCL, then append states through the held inode."""
    data = _canonical_json(payload) + b"\n"
    if create:
        temporary = _stage_migration_at(
            root_parent, LINK_MIGRATION_JOURNAL_RELPATH, data, 0o600
        )
        descriptor = None
        result_guard = None
        try:
            try:
                os.link(
                    temporary,
                    LINK_MIGRATION_JOURNAL_RELPATH,
                    src_dir_fd=root_parent,
                    dst_dir_fd=root_parent,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise LinkMigrationError("another link migration is active") from exc
            temporary_info = os.stat(
                temporary, dir_fd=root_parent, follow_symlinks=False
            )
            descriptor = os.open(
                LINK_MIGRATION_JOURNAL_RELPATH,
                os.O_RDWR
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=root_parent,
            )
            info = os.fstat(descriptor)
            candidate_guard = {
                "contents": data,
                "descriptor": descriptor,
                "identity": _link_migration_identity(info),
            }
            if (
                _link_migration_identity(temporary_info)
                != candidate_guard["identity"]
                or not _journal_guard_matches(root_parent, candidate_guard)
            ):
                raise LinkMigrationError(
                    "migration journal ownership changed during creation"
                )
            os.fsync(root_parent)
            result_guard = candidate_guard
            return result_guard
        finally:
            try:
                os.unlink(temporary, dir_fd=root_parent)
            except FileNotFoundError:
                pass
            if descriptor is not None and result_guard is None:
                os.close(descriptor)
    if guard is None or not _journal_guard_matches(root_parent, guard):
        raise LinkMigrationError(
            "migration journal ownership changed; foreign replacement preserved"
        )
    descriptor = guard["descriptor"]
    os.lseek(descriptor, 0, os.SEEK_END)
    offset = 0
    while offset < len(data):
        offset += os.write(descriptor, data[offset:])
    os.fsync(descriptor)
    guard["contents"] += data
    if not _journal_guard_matches(root_parent, guard):
        raise LinkMigrationError(
            "migration journal ownership changed; foreign replacement preserved"
        )
    return guard


def _parse_migration_journal(raw: bytes) -> dict:
    # Every durable state is a complete JSON line. An unterminated tail is a
    # power-loss write and is ignored in favor of the preceding durable state.
    complete = raw.split(b"\n")
    if not raw.endswith(b"\n"):
        complete = complete[:-1]
    candidates = [line for line in complete if line]
    if not candidates:
        raise LinkMigrationError("migration journal is malformed")
    try:
        payload = json.loads(candidates[-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LinkMigrationError("migration journal is malformed") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("owner") != "brain-link-migration"
        or payload.get("schemaVersion") != LINK_MIGRATION_SCHEMA_VERSION
        or type(payload.get("pid")) is not int
        or type(payload.get("committed")) is not bool
        or not isinstance(payload.get("rows"), list)
    ):
        raise LinkMigrationError("migration journal is malformed")
    return payload


def _read_migration_journal(root_parent: int) -> tuple[dict, dict]:
    descriptor = os.open(
        LINK_MIGRATION_JOURNAL_RELPATH,
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0),
        dir_fd=root_parent,
    )
    info = os.fstat(descriptor)
    if stat.S_IMODE(info.st_mode) != 0o600:
        os.close(descriptor)
        raise LinkMigrationError("migration journal permissions are unsafe")
    try:
        raw = _read_descriptor_bytes(descriptor)
        guard = {
            "contents": raw,
            "descriptor": descriptor,
            "identity": _link_migration_identity(info),
        }
        if not _journal_guard_matches(root_parent, guard):
            raise LinkMigrationError(
                "migration journal ownership changed; foreign replacement preserved"
            )
        return _parse_migration_journal(raw), guard
    except BaseException:
        os.close(descriptor)
        raise


def _remove_migration_journal(root_parent: int, guard: dict) -> None:
    """Remove only the held journal inode; never unlink a replacement."""
    if not _journal_guard_matches(root_parent, guard):
        raise LinkMigrationError(
            "migration journal ownership changed; foreign replacement preserved"
        )
    quarantine = _unused_migration_name(
        root_parent, LINK_MIGRATION_JOURNAL_RELPATH, "old"
    )
    os.rename(
        LINK_MIGRATION_JOURNAL_RELPATH,
        quarantine,
        src_dir_fd=root_parent,
        dst_dir_fd=root_parent,
    )
    os.fsync(root_parent)
    moved_info = os.stat(quarantine, dir_fd=root_parent, follow_symlinks=False)
    if _link_migration_identity(moved_info) != guard["identity"]:
        try:
            os.link(
                quarantine,
                LINK_MIGRATION_JOURNAL_RELPATH,
                src_dir_fd=root_parent,
                dst_dir_fd=root_parent,
                follow_symlinks=False,
            )
            os.fsync(root_parent)
        except FileExistsError:
            pass
        raise LinkMigrationError(
            "migration journal ownership changed; foreign replacement preserved"
        )
    try:
        os.stat(
            LINK_MIGRATION_JOURNAL_RELPATH,
            dir_fd=root_parent,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        pass
    else:
        os.unlink(quarantine, dir_fd=root_parent)
        os.fsync(root_parent)
        raise LinkMigrationError(
            "migration journal ownership changed; foreign replacement preserved"
        )
    os.unlink(quarantine, dir_fd=root_parent)
    os.fsync(root_parent)
    try:
        os.stat(
            LINK_MIGRATION_JOURNAL_RELPATH,
            dir_fd=root_parent,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return
    raise LinkMigrationError(
        "migration journal ownership changed; foreign replacement preserved"
    )


def _migration_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _transaction_name_valid(name: object, basename: str, kind: str) -> bool:
    return isinstance(name, str) and bool(
        re.fullmatch(
            rf"\.{re.escape(basename)}\.migrate-{kind}-[0-9a-f]{{24}}", name
        )
    )


def recover_link_migration(root: Path) -> bool:
    """Roll an interrupted journal back to source bytes before a new command."""
    if not _migration_mutation_supported():
        journal = root / LINK_MIGRATION_JOURNAL_RELPATH
        if os.path.lexists(journal):
            raise LinkMigrationError(
                "an interrupted migration exists but safe recovery is unavailable"
            )
        return False
    root_parent, _unused = _open_migration_parent(root, "recovery-placeholder")
    journal_guard = None
    try:
        try:
            payload, journal_guard = _read_migration_journal(root_parent)
        except FileNotFoundError:
            return False
        if payload["pid"] != os.getpid() and _migration_pid_alive(payload["pid"]):
            raise LinkMigrationError("another link migration is active")
        unresolved: list[str] = []
        if payload["committed"]:
            for row in payload["rows"]:
                if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                    raise LinkMigrationError("migration journal is malformed")
                parent, name = _open_migration_parent(root, row["path"])
                try:
                    if name != row.get("name") or not _transaction_name_valid(
                        row.get("backup"), name, "old"
                    ) or not _transaction_name_valid(row.get("new"), name, "new"):
                        raise LinkMigrationError("migration journal names are unsafe")
                    try:
                        current, current_info = _read_migration_at(parent, name)
                    except FileNotFoundError:
                        unresolved.append(row["path"])
                        continue
                    if (
                        _sha256_bytes(current) != row.get("resultSha256")
                        or stat.S_IMODE(current_info.st_mode) != row.get("mode")
                    ):
                        unresolved.append(row["path"])
                        continue
                    for temporary, expected in (
                        (row["backup"], row.get("sourceSha256")),
                        (row["new"], row.get("resultSha256")),
                    ):
                        try:
                            contents, temporary_info = _read_migration_at(
                                parent, temporary
                            )
                        except FileNotFoundError:
                            continue
                        if (
                            _sha256_bytes(contents) != expected
                            or stat.S_IMODE(temporary_info.st_mode) != row.get("mode")
                        ):
                            unresolved.append(row["path"])
                            continue
                        os.unlink(temporary, dir_fd=parent)
                finally:
                    os.close(parent)
            if unresolved:
                raise LinkMigrationError(
                    "committed migration needs manual recovery: "
                    + ", ".join(sorted(set(unresolved)))
                )
            _remove_migration_journal(root_parent, journal_guard)
            return True
        for row in reversed(payload["rows"]):
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise LinkMigrationError("migration journal is malformed")
            parent, name = _open_migration_parent(root, row["path"])
            try:
                if name != row.get("name") or not _transaction_name_valid(
                    row.get("backup"), name, "old"
                ) or not _transaction_name_valid(row.get("new"), name, "new"):
                    raise LinkMigrationError("migration journal names are unsafe")
                backup = None
                try:
                    backup = _read_migration_at(parent, row["backup"])
                except FileNotFoundError:
                    pass
                current = None
                try:
                    current = _read_migration_at(parent, name)
                except FileNotFoundError:
                    pass
                if backup is not None:
                    backup_bytes, backup_info = backup
                    if (
                        _sha256_bytes(backup_bytes) != row.get("sourceSha256")
                        or stat.S_IMODE(backup_info.st_mode) != row.get("mode")
                    ):
                        unresolved.append(row["path"])
                        continue
                    if current is not None:
                        current_bytes, current_info = current
                        current_hash = _sha256_bytes(current_bytes)
                        if current_hash == row.get("sourceSha256") and stat.S_IMODE(
                            current_info.st_mode
                        ) == row.get("mode"):
                            os.unlink(row["backup"], dir_fd=parent)
                        elif current_hash == row.get(
                            "resultSha256"
                        ) and stat.S_IMODE(current_info.st_mode) == row.get("mode"):
                            os.unlink(name, dir_fd=parent)
                            _install_migration_at(parent, row["backup"], name)
                            os.unlink(row["backup"], dir_fd=parent)
                        else:
                            unresolved.append(row["path"])
                            continue
                    else:
                        _install_migration_at(parent, row["backup"], name)
                        os.unlink(row["backup"], dir_fd=parent)
                elif current is None or _sha256_bytes(current[0]) != row.get(
                    "sourceSha256"
                ):
                    unresolved.append(row["path"])
                    continue
                try:
                    staged, staged_info = _read_migration_at(parent, row["new"])
                    if (
                        _sha256_bytes(staged) == row.get("resultSha256")
                        and stat.S_IMODE(staged_info.st_mode) == row.get("mode")
                    ):
                        os.unlink(row["new"], dir_fd=parent)
                    else:
                        unresolved.append(row["path"])
                except FileNotFoundError:
                    pass
            finally:
                os.close(parent)
        if unresolved:
            raise LinkMigrationError(
                "interrupted migration needs manual recovery: "
                + ", ".join(sorted(set(unresolved)))
            )
        _remove_migration_journal(root_parent, journal_guard)
        return True
    finally:
        _close_migration_journal_guard(journal_guard)
        os.close(root_parent)


def apply_link_migration_plan(root: Path, plan: dict) -> dict:
    """Held-parent CAS transaction; never overwrites a concurrent final path."""
    _validate_migration_plan(plan)
    edits = plan.get("edits", [])
    if not edits:
        return {"filesChanged": 0, "linksConverted": 0, "planId": plan["planId"]}
    if not _migration_mutation_supported():
        raise LinkMigrationError(
            "safe link migration writes are unavailable on this runtime; preview/check only"
        )
    recover_link_migration(root)
    dirty = dirty_migration_paths(root, plan)
    if dirty is None:
        raise LinkMigrationError("cannot establish clean Git state for planned paths")
    if dirty:
        raise LinkMigrationError("planned migration paths are dirty")
    root_parent, _unused = _open_migration_parent(root, "journal-placeholder")
    prepared: list[dict] = []
    quarantined: list[dict] = []
    applied: list[dict] = []
    previous_term = None
    can_handle_term = hasattr(signal, "SIGTERM")
    if can_handle_term:
        try:
            previous_term = signal.getsignal(signal.SIGTERM)

            def interrupt_on_term(_signum, _frame):
                raise KeyboardInterrupt

            signal.signal(signal.SIGTERM, interrupt_on_term)
        except (ValueError, OSError):
            previous_term = None
    recovery: list[str] = []
    committed = False
    journal_active = False
    journal_guard = None
    retire_journal = False
    journal_payload = _journal_payload(plan, prepared)
    try:
        journal_guard = _write_migration_journal(
            root_parent, journal_payload, create=True
        )
        journal_active = True
        # Preparation is inside the same BaseException scope as mutation, so
        # a later staging failure or interrupt cannot leak earlier siblings.
        for row in edits:
            rel = row.get("path")
            if not isinstance(rel, str):
                raise LinkMigrationError("migration source path is unsafe")
            parent, name = _open_migration_parent(root, rel)
            item = {"parent": parent, "name": name, "rel": rel}
            prepared.append(item)
            source, info = _read_migration_at(parent, name)
            mode = stat.S_IMODE(info.st_mode)
            if _sha256_bytes(source) != row.get("sourceSha256") or mode != row.get("mode"):
                raise LinkMigrationError("stale migration source or file mode")
            desired = _desired_migration_bytes(source, row)
            item.update(
                {
                    "backup": _unused_migration_name(parent, name, "old"),
                    "desired": desired,
                    "identity": _link_migration_identity(info),
                    "new": _unused_migration_name(parent, name, "new"),
                    "source": source,
                    "stage_ownership": {},
                    "staged_owned": False,
                }
            )
            # Make the random stage name durable before creating it. Recovery
            # can now remove a verified complete stage after a power loss in
            # the preparation window instead of leaving an unjournaled file.
            journal_payload = _journal_payload(plan, prepared)
            _write_migration_journal(
                root_parent,
                journal_payload,
                create=False,
                guard=journal_guard,
            )
            item["new"] = _stage_migration_at(
                parent,
                name,
                desired,
                mode,
                ownership=item["stage_ownership"],
                reserved_name=item["new"],
            )
            item["staged_owned"] = True
        # Final held-handle preflight, then quarantine every original. A race
        # becomes quarantined evidence and is restored, never overwritten.
        for item in prepared:
            current, info = _read_migration_at(item["parent"], item["name"])
            if current != item["source"] or _link_migration_identity(info) != item["identity"]:
                raise LinkMigrationError("migration source changed before quarantine")
            quarantined.append(item)
            _quarantine_migration_at(
                item["parent"], item["name"], item["backup"]
            )
            moved, moved_info = _read_migration_at(item["parent"], item["backup"])
            if moved != item["source"] or _link_migration_identity(moved_info) != item["identity"]:
                raise LinkMigrationError("migration source changed during quarantine")
        for item in prepared:
            # Record the publication attempt before the helper's directory
            # fsync: a successful link followed by fsync failure is still an
            # installed result that rollback must authenticate and remove.
            applied.append(item)
            _install_migration_at(item["parent"], item["new"], item["name"])
        for item in prepared:
            _verify_installed_migration(item)
        journal_payload["committed"] = True
        _write_migration_journal(
            root_parent,
            journal_payload,
            create=False,
            guard=journal_guard,
        )
        # The commit-marker write is a mutation window. Re-authenticate every
        # installed inode before declaring success or deleting recovery data.
        for item in prepared:
            _verify_installed_migration(item)
        committed = True
    except BaseException as exc:
        rollback_errors: list[str] = []
        for item in reversed(applied):
            try:
                current, info = _read_migration_at(item["parent"], item["name"])
                staged_info = os.stat(
                    item["new"], dir_fd=item["parent"], follow_symlinks=False
                )
                if current == item["desired"] and (
                    info.st_dev,
                    info.st_ino,
                ) == (staged_info.st_dev, staged_info.st_ino) and stat.S_IMODE(
                    info.st_mode
                ) == item["identity"][3]:
                    os.unlink(item["name"], dir_fd=item["parent"])
            except FileNotFoundError:
                # Publication may have failed before creating the final name.
                pass
            except (OSError, LinkMigrationError) as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        for item in reversed(quarantined):
            try:
                try:
                    _read_migration_at(item["parent"], item["backup"])
                except FileNotFoundError:
                    current, info = _read_migration_at(
                        item["parent"], item["name"]
                    )
                    if current == item["source"] and _link_migration_identity(info) == item["identity"]:
                        continue
                    raise LinkMigrationError("quarantined original is unavailable")
                restored = _restore_quarantined_at(
                    item["parent"], item["backup"], item["name"]
                )
                if restored:
                    os.unlink(item["backup"], dir_fd=item["parent"])
                else:
                    recovery.append(f"{item['rel']}::{item['backup']}")
            except (OSError, LinkMigrationError) as rollback_exc:
                rollback_errors.append(str(rollback_exc))
                recovery.append(f"{item['rel']}::{item['backup']}")
        if rollback_errors:
            detail = ", ".join(recovery) if recovery else "unknown backup"
            raise LinkMigrationError(
                f"migration failed and rollback needs recovery from {detail}"
            ) from exc
        if recovery:
            raise LinkMigrationError(
                "migration refused concurrent content; originals retained at "
                + ", ".join(recovery)
            ) from exc
        retire_journal = journal_active
        raise
    finally:
        journal_cleanup_error = None
        artifact_cleanup_error = None
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
        for item in prepared:
            parent = item["parent"]
            try:
                _remove_owned_migration_stage(item)
                if committed:
                    _remove_owned_migration_backup(item)
            except LinkMigrationError as cleanup_exc:
                if artifact_cleanup_error is None:
                    artifact_cleanup_error = cleanup_exc
            try:
                os.close(parent)
            except OSError:
                pass
        if artifact_cleanup_error is None and (committed or retire_journal) and journal_active:
            try:
                _remove_migration_journal(root_parent, journal_guard)
                journal_active = False
            except LinkMigrationError as cleanup_exc:
                journal_cleanup_error = cleanup_exc
        _close_migration_journal_guard(journal_guard)
        os.close(root_parent)
        if artifact_cleanup_error is not None:
            raise artifact_cleanup_error
        if journal_cleanup_error is not None:
            raise journal_cleanup_error
    return {
        "filesChanged": len(edits),
        "linksConverted": plan["summary"]["linksConverted"],
        "planId": plan["planId"],
    }


def cmd_migrate_links(root: Path, args) -> int:
    recovered = False
    if args.write:
        try:
            recovered = recover_link_migration(root)
        except LinkMigrationError as exc:
            if args.json:
                print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=1, sort_keys=True))
            else:
                print(f"error: {exc}", file=sys.stderr)
            return 1
    elif os.path.lexists(root / LINK_MIGRATION_JOURNAL_RELPATH):
        # Preview and --check are strict zero-write operations. Recovery is a
        # mutation and therefore requires the caller's explicit --write.
        message = "interrupted-migration: explicit --write is required for recovery"
        if args.json:
            print(json.dumps({"error": message}, ensure_ascii=False, indent=1, sort_keys=True))
        else:
            print(f"error: {message}", file=sys.stderr)
        return 1
    plan = build_link_migration_plan(root)
    public_plan = public_link_migration_plan(plan)
    if args.write:
        try:
            applied = apply_link_migration_plan(root, plan)
        except (LinkMigrationError, KeyboardInterrupt) as exc:
            if args.json:
                print(json.dumps({"error": str(exc), "plan": public_plan}, ensure_ascii=False, indent=1, sort_keys=True))
            else:
                print(f"error: {exc}", file=sys.stderr)
            return 1
        payload = {"applied": applied, "plan": public_plan, "recovered": recovered}
        emit(
            payload,
            args.json,
            [
                f"migrated {applied['linksConverted']} links in {applied['filesChanged']} files",
                "regenerate: " + ", ".join(plan["regenerateRequired"]),
            ],
        )
        return 0
    if args.json:
        print(json.dumps(public_plan, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        summary = plan["summary"]
        print(
            f"preview: {summary['linksConverted']} links in {summary['filesChanged']} files; "
            f"{len(plan['blockers'])} blockers; {summary['placeholders']} placeholders"
        )
        for finding in plan["blockers"]:
            location = finding["path"] + (f":{finding['line']}" if finding["line"] else "")
            print(f"BLOCK {location} {finding['rule']}: {finding['message']}")
    if args.check and (
        plan["summary"]["legacyLinks"] > 0 or plan["edits"] or plan["blockers"]
    ):
        return 1
    return 1 if plan["blockers"] else 0


# ---------------------------------------------------------------------------
# §23 Actions You May Take (AYMT)


class AymtError(RuntimeError):
    """Stable, privacy-safe refusal at the AYMT CLI boundary."""


class HomeError(RuntimeError):
    """Stable, privacy-safe refusal at the Home CLI boundary."""


def _aymt_text(value: object, *, limit: int = AYMT_FIELD_LIMIT) -> str:
    """Single-line, bounded text safe for JSON and Markdown."""
    text = nfc(" ".join(str(value if value is not None else "").split()))
    text = "".join(ch for ch in text if ch >= " " and ch != "\x7f")
    return text[:limit].rstrip()


def _aymt_label(value: object) -> str:
    return _escape_markdown_label(_aymt_text(value, limit=120))


def _aymt_markdown_text(value: object, *, limit: int = AYMT_FIELD_LIMIT) -> str:
    text = _aymt_text(value, limit=limit)
    for char in "\\`*_{}[]<>#|":
        text = text.replace(char, "\\" + char)
    return text


def _aymt_score(signals: dict[str, int]) -> int:
    """The documented integer score; dependency is blocker severity 0..4."""
    return (
        6 * signals["urgency"]
        + 4 * signals["leverage"]
        + 3 * signals["confidence"]
        + 2 * signals["staleness"]
        + 2 * (4 - signals["effort"])
        - 5 * signals["dependency"]
    )


def _aymt_source(path: str, label: str | None = None) -> dict:
    return {
        "kind": "vault",
        "label": _aymt_text(label or path, limit=120),
        "path": path,
    }


def _aymt_candidate(
    *,
    kind: str,
    outcome: str,
    section: str,
    why_now: str,
    next_step: str,
    caveat: str,
    sources: list[dict],
    urgency: int,
    leverage: int,
    effort: int,
    confidence: int,
    dependency: int,
    staleness: int,
) -> dict:
    if section not in AYMT_SECTION_CAPS:
        raise AymtError("AYMT candidate section is invalid")
    signals = {
        "confidence": confidence,
        "dependency": dependency,
        "effort": effort,
        "leverage": leverage,
        "staleness": staleness,
        "urgency": urgency,
    }
    if any(type(value) is not int or not 0 <= value <= 4 for value in signals.values()):
        raise AymtError("AYMT candidate signals are invalid")
    normalized_outcome = _aymt_text(outcome).casefold()
    if not normalized_outcome:
        raise AymtError("AYMT candidate outcome is empty")
    safe_sources: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        if source.get("kind") == "vault":
            key = ("vault", source.get("path", ""))
        elif source.get("kind") == "github":
            key = ("github", source.get("url", ""))
        else:
            continue
        if key in seen or not key[1]:
            continue
        seen.add(key)
        safe_sources.append(source)
        if len(safe_sources) == AYMT_SOURCE_LIMIT:
            break
    return {
        "caveat": _aymt_text(caveat),
        "id": hashlib.sha256(f"{kind}\0{normalized_outcome}".encode()).hexdigest(),
        "kind": kind,
        "nextStep": _aymt_text(next_step),
        "outcome": _aymt_text(outcome),
        "score": _aymt_score(signals),
        "section": section,
        "signals": signals,
        "sources": safe_sources,
        "whyNow": _aymt_text(why_now),
    }


def _select_aymt_candidates(candidates: list[dict]) -> tuple[list[dict], dict]:
    """Dedupe evidence, apply soft section caps, then fill by global rank."""
    deduped: dict[str, dict] = {}
    for candidate in candidates:
        key = fold(candidate["outcome"])
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = candidate
            continue
        winner = candidate if (-candidate["score"], candidate["id"]) < (
            -existing["score"], existing["id"]
        ) else existing
        source_map: dict[tuple[str, str], dict] = {}
        for source in [*existing["sources"], *candidate["sources"]]:
            location = source.get("path") if source.get("kind") == "vault" else source.get("url")
            source_map[(source.get("kind", ""), location or "")] = source
        merged_sources = [
            source_map[source_key]
            for source_key in sorted(source_map)
            if source_key[0] in {"vault", "github"} and source_key[1]
        ][:AYMT_SOURCE_LIMIT]
        deduped[key] = {**winner, "sources": merged_sources}
    section_order = {name: index for index, name in enumerate(AYMT_SECTION_CAPS)}
    ordered = sorted(
        deduped.values(),
        key=lambda row: (
            section_order[row["section"]],
            -row["score"],
            fold(row["outcome"]),
            row["id"],
        ),
    )
    global_ordered = sorted(
        ordered,
        key=lambda row: (
            -row["score"],
            -row["signals"]["urgency"],
            -row["signals"]["leverage"],
            row["signals"]["effort"],
            row["signals"]["dependency"],
            row["id"],
        ),
    )
    selected: list[dict] = []
    used = {section: 0 for section in AYMT_SECTION_CAPS}
    for row in ordered:
        if len(selected) == 7:
            break
        if used[row["section"]] >= AYMT_SECTION_CAPS[row["section"]]:
            continue
        selected.append(row)
        used[row["section"]] += 1
    selected_ids = {row["id"] for row in selected}
    target_count = min(7, len(ordered))
    for row in global_ordered:
        if len(selected) >= target_count:
            break
        if row["id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["id"])
    selected.sort(
        key=lambda row: (
            section_order[row["section"]],
            -row["score"],
            fold(row["outcome"]),
            row["id"],
        )
    )
    summary = {
        "collected": len(candidates),
        "deduplicated": len(ordered),
        "selected": len(selected),
        "truncated": max(0, len(ordered) - len(selected)),
    }
    return selected, summary


def _aymt_note_allowed(rel: str, rec: dict, restricted_paths: set[str]) -> bool:
    if (
        rel in {AYMT_RELPATH, HOME_RELPATH}
        or rel.startswith(("07_Archives/", "09_Templates/", ENVIRONMENTS_RELPATH + "/"))
        or rel in restricted_paths
    ):
        return False
    # A non-restricted note pointing at a restricted note is excluded before
    # any body-derived field can become an AYMT candidate.
    return not any(link.get("resolved") in restricted_paths for link in rec.get("links", []))


def _aymt_seed_paths(raw: bytes) -> tuple[str, ...]:
    """Parse the authenticated manifest-owned example inventory."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, ValueError):
        raise AymtError("seed inventory is unavailable") from None
    delete = data.get("delete") if isinstance(data, dict) else None
    if (
        data.get("schema_version") != 1
        or not isinstance(delete, list)
        or not all(type(item) is str and item and not item.startswith("/") and ".." not in item.split("/") for item in delete)
    ):
        raise AymtError("seed inventory is invalid")
    return tuple(sorted(delete))


def _aymt_is_seed_path(rel: str, seeds: tuple[str, ...]) -> bool:
    return any(rel == seed.rstrip("/") or (seed.endswith("/") and rel.startswith(seed)) for seed in seeds)


def _aymt_heading_items(text: str | None, heading: str) -> list[str]:
    """Concrete bullets from one authenticated note snapshot section."""
    if text is None:
        return []
    lines = text.split("\n")
    wanted = fold(heading)
    inside = False
    items: list[str] = []
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(2))
            title = fold(match.group(3).strip())
            if level == 2:
                inside = title == wanted
                continue
            if inside and level <= 2:
                break
        if inside:
            item = re.match(r"^\s*[-*+]\s+(.*)$", line)
            if not item:
                continue
            text = re.sub(r"<!--.*?-->", "", item.group(1)).strip()
            if text and "{{" not in text and "template note" not in fold(text):
                items.append(_aymt_text(text))
    return items


def _aymt_first_next_action(root: Path, rel: str, rec: dict) -> tuple[str, str]:
    for task in rec.get("tasks", []):
        if task.get("status") == "open" and not task.get("malformed"):
            return _aymt_text(task.get("text")), "The next project task is explicit."
    return "Define the project's next concrete action.", "No open project task is recorded."


def _aymt_cadence_candidates(today_d: date, tracked_paths: set[str]) -> list[dict]:
    rows: list[dict] = []
    daily_path = f"03_Journal/periodic/daily/{today_d.isoformat()}.md"
    if daily_path not in tracked_paths:
        rows.append(
            _aymt_candidate(
                kind="cadence",
                outcome="Start today's daily log",
                section="do-next",
                why_now="Today's tracked daily log is missing.",
                next_step="Run the daily-log skill and capture today's first concrete entry.",
                caveat="The check uses the tracked corpus; an untracked draft is intentionally invisible.",
                sources=[_aymt_source("10_Agents/skills/README.md", "The Rhythm")],
                urgency=4,
                leverage=2,
                effort=1,
                confidence=4,
                dependency=0,
                staleness=0,
            )
        )
    iso_year, iso_week, _iso_day = today_d.isocalendar()
    weekly_path = f"03_Journal/periodic/weekly/{iso_year}-W{iso_week:02d}-review.md"
    if today_d.weekday() >= 4 and weekly_path not in tracked_paths:  # Friday through Sunday
        rows.append(
            _aymt_candidate(
                kind="cadence",
                outcome="Complete the weekly organize rhythm",
                section="do-next",
                why_now="The weekly cadence window is Friday through Sunday.",
                next_step="Triage Inbox, run the weekly periodic review, then sweep Outbox.",
                caveat="Record completion in the weekly review so it is not suggested twice manually.",
                sources=[_aymt_source("10_Agents/skills/README.md", "The Rhythm")],
                urgency=4,
                leverage=4,
                effort=3,
                confidence=4,
                dependency=0,
                staleness=1,
            )
        )
    last_day = calendar.monthrange(today_d.year, today_d.month)[1]
    monthly_path = f"03_Journal/periodic/monthly/{today_d.year}-{today_d.month:02d}-review.md"
    if today_d.day >= last_day - 2 and monthly_path not in tracked_paths:
        rows.append(
            _aymt_candidate(
                kind="cadence",
                outcome="Complete the monthly maintenance rhythm",
                section="unblock-or-decide",
                why_now="The monthly cadence window is the last three calendar days.",
                next_step="Run monthly review, vault-maintenance, curate, and self-improve.",
                caveat="Review generated findings before applying any canonical change.",
                sources=[_aymt_source("10_Agents/skills/README.md", "The Rhythm")],
                urgency=3,
                leverage=4,
                effort=4,
                confidence=4,
                dependency=0,
                staleness=2,
            )
        )
    quarter_end = date(today_d.year, ((today_d.month - 1) // 3 + 1) * 3, 1)
    quarter_end = quarter_end.replace(
        day=calendar.monthrange(quarter_end.year, quarter_end.month)[1]
    )
    quarter = (today_d.month - 1) // 3 + 1
    quarterly_path = f"03_Journal/periodic/quarterly/{today_d.year}-Q{quarter}-review.md"
    if 0 <= (quarter_end - today_d).days <= 6 and quarterly_path not in tracked_paths:
        rows.append(
            _aymt_candidate(
                kind="cadence",
                outcome="Complete the quarterly review rhythm",
                section="unblock-or-decide",
                why_now="The quarterly cadence window is the final seven calendar days.",
                next_step="Run quarterly review, refresh Now, curate, and audit self-maintenance.",
                caveat="Confirm the quarter's decisions with the owner before canonical updates.",
                sources=[_aymt_source("10_Agents/skills/README.md", "The Rhythm")],
                urgency=3,
                leverage=4,
                effort=4,
                confidence=4,
                dependency=0,
                staleness=3,
            )
        )
    yearly_path = f"03_Journal/periodic/yearly/{today_d.year}-review.md"
    if today_d.month == 12 and 26 <= today_d.day <= 31 and yearly_path not in tracked_paths:
        rows.append(
            _aymt_candidate(
                kind="cadence",
                outcome="Complete the yearly review",
                section="keep-warm",
                why_now="The yearly cadence window is December 26 through 31.",
                next_step="Run the yearly periodic review and capture next year's themes.",
                caveat="Treat it as reflection, not an automatic commitment to every idea.",
                sources=[_aymt_source("10_Agents/skills/README.md", "The Rhythm")],
                urgency=3,
                leverage=3,
                effort=4,
                confidence=4,
                dependency=0,
                staleness=3,
            )
        )
    return rows


def _load_aymt_github_input(path: str | None, stdin, as_of: date) -> list[dict]:
    if path is None:
        return []
    try:
        if path == "-":
            stream = getattr(stdin, "buffer", stdin)
            raw = stream.read(AYMT_GITHUB_MAX_BYTES + 1)
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
        else:
            candidate = Path(path)
            if not candidate.is_absolute():
                raise AymtError("GitHub input must be an absolute regular file or '-'")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(candidate, flags)
            try:
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode) or before.st_size > AYMT_GITHUB_MAX_BYTES:
                    raise AymtError("GitHub input is not a bounded regular file")
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = os.read(descriptor, 64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > AYMT_GITHUB_MAX_BYTES:
                        raise AymtError("GitHub input exceeds the 64 KiB limit")
                    chunks.append(chunk)
                after = os.fstat(descriptor)
                final = os.lstat(candidate)
                identity = lambda info: (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size)
                if identity(before) != identity(after) or identity(after) != identity(final) or _link_like_stat(final):
                    raise AymtError("GitHub input changed during bounded read")
                raw = b"".join(chunks)
            finally:
                os.close(descriptor)
        if len(raw) > AYMT_GITHUB_MAX_BYTES:
            raise AymtError("GitHub input exceeds the 64 KiB limit")
        data = json.loads(raw.decode("utf-8"))
    except AymtError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise AymtError("GitHub input is unreadable or malformed") from None
    if not isinstance(data, dict) or set(data) != {"issues", "repository", "schemaVersion"}:
        raise AymtError("GitHub input has an unsupported shape")
    repo = data.get("repository")
    component = r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?"
    if (
        type(data.get("schemaVersion")) is not int
        or data.get("schemaVersion") != 1
        or type(repo) is not str
        or not re.fullmatch(rf"{component}/{component}", repo)
        or any(part in {".", ".."} for part in repo.split("/"))
    ):
        raise AymtError("GitHub input repository identity is invalid")
    issues = data.get("issues")
    if not isinstance(issues, list) or len(issues) > AYMT_GITHUB_MAX_ISSUES:
        raise AymtError("GitHub input issues must be a bounded list")
    rows: list[dict] = []
    seen_numbers: set[int] = set()
    for issue in issues:
        if not isinstance(issue, dict) or set(issue) != {
            "labels", "number", "status", "title", "updated"
        }:
            raise AymtError("GitHub input issue has an unsupported shape")
        number, title, labels = issue.get("number"), issue.get("title"), issue.get("labels")
        status = issue.get("status")
        updated_value = issue.get("updated")
        updated = iso_date(updated_value) if type(updated_value) is str else None
        if (
            type(number) is not int
            or not 1 <= number <= 2_147_483_647
            or type(title) is not str
            or not title.strip()
            or len(title) > AYMT_FIELD_LIMIT
            or not isinstance(labels, list)
            or len(labels) > 20
            or not all(type(label) is str and 0 < len(label) <= 80 for label in labels)
            or type(status) is not str
            or status not in {"ready", "blocked", "open"}
            or updated is None
        ):
            raise AymtError("GitHub input issue values are invalid")
        if number in seen_numbers:
            raise AymtError("GitHub input contains a duplicate issue number")
        seen_numbers.add(number)
        url = f"https://github.com/{repo}/issues/{number}"
        normalized_labels = {label.casefold() for label in labels}
        ready = status == "ready"
        effort = 4 if "effort/xl" in normalized_labels else 3 if "effort/l" in normalized_labels else 2 if "effort/m" in normalized_labels else 1 if "effort/s" in normalized_labels else 2
        dependency = 4 if status == "blocked" else 2 if "needs-decision" in normalized_labels else 0
        staleness = min(4, max(0, (as_of - updated).days // 30))
        rows.append(
            _aymt_candidate(
                kind="github",
                outcome=_aymt_text(title),
                section="do-next" if ready and dependency == 0 else "unblock-or-decide",
                why_now="The sanitized GitHub snapshot marks this issue Ready." if ready else "This issue remains in the sanitized planning snapshot.",
                next_step=f"Open {repo}#{number} and take the smallest reviewable implementation step.",
                caveat="GitHub state is caller-supplied; refresh the sanitized snapshot before acting.",
                sources=[{"kind": "github", "label": f"{repo}#{number}", "url": url}],
                urgency=3 if ready else 1,
                leverage=3,
                effort=effort,
                confidence=3,
                dependency=dependency,
                staleness=staleness,
            )
        )
    return rows


def _aymt_environment(selection: dict, raw: bytes | None) -> dict:
    if selection["state"] == "unconfigured":
        return {"freshness": None, "slug": None, "source": "none", "state": "unconfigured"}
    slug = selection.get("slug")
    if not _valid_environment_slug(slug) or raw is None:
        raise AymtError("current environment metadata is unavailable")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, ValueError):
        raise AymtError("current environment metadata is unavailable") from None
    if validate_environment_manifest(manifest, slug):
        raise AymtError("current environment metadata is unavailable")
    meta = environment_metadata(manifest, slug)
    return {
        "freshness": meta["freshness"],
        "slug": meta["slug"],
        "source": selection["source"],
        "state": "selected",
    }


def build_aymt(
    root: Path,
    *,
    today_d: date | None = None,
    selection: dict | None = None,
    github_input: str | None = None,
    stdin=None,
    _context: dict | None = None,
) -> dict:
    """Build a deterministic, tracked-corpus-only and privacy-filtered brief."""
    today_d = today_d or today()
    stdin = stdin or sys.stdin
    if _context is None:
        try:
            selected = selection or select_aymt_environment(root)
        except EnvironmentSelectionError:
            raise AymtError("current environment selection is unavailable") from None
        _context = _build_action_context(root, today_d, selected)
    context = _context
    environment = context["environment"]
    note_snapshots = context["snapshots"]
    snapshot_texts = context["snapshotTexts"]
    index = context["index"]
    allowed = context["allowed"]
    safe_report = context["report"]
    candidates: list[dict] = []
    now_rel = CORE_FRAMEWORK_PATHS["now"]
    if now_rel in allowed:
        for focus in _aymt_heading_items(snapshot_texts.get(now_rel), "Current Focus")[:6]:
            candidates.append(
                _aymt_candidate(
                    kind="focus",
                    outcome=focus,
                    section="keep-warm",
                    why_now="This is recorded in the current focus list.",
                    next_step="Choose one concrete move that advances this focus.",
                    caveat="The Now page expresses attention, not a hard deadline.",
                    sources=[_aymt_source(now_rel, "Now — Current Focus")],
                    urgency=1,
                    leverage=3,
                    effort=2,
                    confidence=4,
                    dependency=0,
                    staleness=0,
                )
            )
        for project in _aymt_heading_items(snapshot_texts.get(now_rel), "Active Projects")[:8]:
            candidates.append(
                _aymt_candidate(
                    kind="now-project",
                    outcome=project,
                    section="keep-warm",
                    why_now="This project is explicitly active on the Now page.",
                    next_step="Open the project source and confirm its next action.",
                    caveat="Prefer the project note when its status conflicts with Now.",
                    sources=[_aymt_source(now_rel, "Now — Active Projects")],
                    urgency=1,
                    leverage=3,
                    effort=2,
                    confidence=4,
                    dependency=0,
                    staleness=0,
                )
            )
        for key_date in _aymt_heading_items(snapshot_texts.get(now_rel), "Key Dates / Deadlines")[:6]:
            if fold(key_date) in {"none", "none right now", "no hard deadlines at the moment."}:
                continue
            date_match = re.search(r"(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])", key_date)
            parsed_date = iso_date(date_match.group(0)) if date_match else None
            if parsed_date is not None:
                days_until = (parsed_date - today_d).days
                urgency = 4 if days_until <= 7 else 3 if days_until <= 30 else 2
                section = "do-next" if days_until <= 30 else "keep-warm"
                confidence = 4
                why_now = f"The Now page records the concrete date {parsed_date.isoformat()}."
            else:
                urgency, section, confidence = 1, "keep-warm", 2
                why_now = "The Now page highlights this item, but it has no machine-readable ISO date."
            candidates.append(
                _aymt_candidate(
                    kind="key-date",
                    outcome=key_date,
                    section=section,
                    why_now=why_now,
                    next_step="Confirm the next milestone and schedule its nearest action.",
                    caveat="Verify date details in the underlying project before committing.",
                    sources=[_aymt_source(now_rel, "Now — Key Dates")],
                    urgency=urgency,
                    leverage=3,
                    effort=2,
                    confidence=confidence,
                    dependency=0,
                    staleness=0,
                )
            )
    profile_template_paths: list[str] = []
    for key in ("identity", "work", "preferences", "defaults", "tooling-stack"):
        rel = CORE_FRAMEWORK_PATHS[key]
        if rel not in allowed:
            continue
        profile_raw = note_snapshots.get(rel)
        if profile_raw is not None and b"**Template note:**" in profile_raw:
            profile_template_paths.append(rel)
    if profile_template_paths:
        candidates.append(
            _aymt_candidate(
                kind="profile-readiness",
                outcome="Complete the owner profile",
                section="unblock-or-decide",
                why_now=f"{len(profile_template_paths)} safe canonical profile notes still carry template markers.",
                next_step="Fill the most relevant profile note and remove its Template note callout.",
                caveat="Profile completion is optional; add only context you want agents to use.",
                sources=[_aymt_source(rel) for rel in profile_template_paths[:AYMT_SOURCE_LIMIT]],
                urgency=1,
                leverage=4,
                effort=2,
                confidence=4,
                dependency=1,
                staleness=1,
            )
        )
    for rel in sorted(allowed):
        rec = allowed[rel]
        owner_lane = rel.startswith(("03_Journal/", "04_Projects/", "05_Areas/"))
        for task in rec.get("tasks", []):
            if task.get("status") != "open":
                continue
            actionable_metadata = bool(
                task.get("due") or task.get("priority") or task.get("malformed")
            )
            # Undated/unprioritized checkboxes in canonical docs and Inbox
            # plans are procedural checklists, not owner commitments. Due,
            # priority, or malformed action metadata is relevant in any safe
            # tracked note; plain tasks come from the owner work lanes.
            if not owner_lane and not actionable_metadata:
                continue
            if task.get("malformed"):
                candidates.append(
                    _aymt_candidate(
                        kind="task-metadata",
                        outcome=f"Repair task metadata in {rel}",
                        section="unblock-or-decide",
                        why_now="An open task has malformed date metadata, so its urgency cannot be ranked safely.",
                        next_step=f"Open line {task['line']} and replace the malformed metadata with a real ISO date or remove it.",
                        caveat="The malformed task text is not repeated in the generated brief.",
                        sources=[_aymt_source(rel)],
                        urgency=2,
                        leverage=2,
                        effort=1,
                        confidence=4,
                        dependency=2,
                        staleness=1,
                    )
                )
                continue
            due = iso_date(task.get("due"))
            overdue = due is not None and due < today_d
            due_soon = due is not None and 0 <= (due - today_d).days <= 7
            priority = task.get("priority")
            urgency = 4 if overdue else 3 if due_soon else 2 if priority == "high" else 1
            candidates.append(
                _aymt_candidate(
                    kind="task",
                    outcome=task["text"],
                    section="do-next" if urgency >= 2 else "keep-warm",
                    why_now=(
                        f"This open task was due {task['due']}." if overdue else
                        f"This open task is due {task['due']}." if due is not None else
                        "This is an explicit open task."
                    ),
                    next_step=f"Open {rel} and complete or refine the task on line {task['line']}.",
                    caveat="Re-check surrounding note context before changing task status.",
                    sources=[_aymt_source(rel)],
                    urgency=urgency,
                    leverage=3 if rel.startswith("04_Projects/") else 2,
                    effort=2,
                    confidence=4,
                    dependency=0,
                    staleness=min(4, max(0, (today_d - iso_date(rec.get("updated"))).days // 30)) if iso_date(rec.get("updated")) else 0,
                )
            )
    active_projects = [
        (rel, rec)
        for rel, rec in sorted(allowed.items())
        if rel.startswith("04_Projects/") and "status/active" in frontmatter_tags(rec)
    ]
    for rel, rec in active_projects:
        next_step, caveat = _aymt_first_next_action(root, rel, rec)
        candidates.append(
            _aymt_candidate(
                kind="project",
                outcome=f"Advance {rec.get('title') or rel.rsplit('/', 1)[-1]}",
                section="keep-warm",
                why_now="The project is tagged status/active.",
                next_step=next_step,
                caveat=caveat,
                sources=[_aymt_source(rel)],
                urgency=1,
                leverage=4,
                effort=2,
                confidence=4,
                dependency=1 if "No open project task" in caveat else 0,
                staleness=min(4, max(0, (today_d - iso_date(rec.get("updated"))).days // 30)) if iso_date(rec.get("updated")) else 0,
            )
        )
    inbox_paths = [
        rel for rel in sorted(allowed)
        if rel.startswith(INBOX_PREFIX) and rel != "02_Inbox/README.md"
    ]
    if inbox_paths:
        debt = len(safe_report["inboxAging"]["triageDebt"])
        candidates.append(
            _aymt_candidate(
                kind="inbox",
                outcome="Triage the Inbox",
                section="do-next" if debt else "keep-warm",
                why_now=f"The tracked Inbox contains {len(inbox_paths)} notes; {debt} exceed the triage threshold.",
                next_step="Run triage-inbox and review the oldest actionable capture first.",
                caveat="The count excludes untracked and restricted material by design.",
                sources=[_aymt_source("02_Inbox/README.md", "Inbox")],
                urgency=4 if debt else 1,
                leverage=4,
                effort=3,
                confidence=4,
                dependency=0,
                staleness=min(4, debt),
            )
        )
    stale_active = safe_report["staleActive"]
    if stale_active:
        candidates.append(
            _aymt_candidate(
                kind="report-stale-active",
                outcome="Review stale active work",
                section="unblock-or-decide",
                why_now=f"The safe tracked health report contains {len(stale_active)} stale active notes.",
                next_step="Open the oldest stale active source and confirm, refresh, or retire its status.",
                caveat="This is bounded report debt, not proof that every listed project should remain active.",
                sources=[_aymt_source(row["path"]) for row in stale_active[:AYMT_SOURCE_LIMIT]],
                urgency=2,
                leverage=3,
                effort=2,
                confidence=4,
                dependency=1,
                staleness=min(4, max(row["daysOld"] for row in stale_active) // 30),
            )
        )
    orphans = safe_report["orphans"]
    if orphans:
        candidates.append(
            _aymt_candidate(
                kind="report-orphans",
                outcome="Review disconnected notes",
                section="keep-warm",
                why_now=f"The safe tracked health report contains {len(orphans)} disconnected notes.",
                next_step="Review the first source and link it, classify it as a deliberate leaf, or archive it.",
                caveat="A disconnected note can be intentional; inspect substance before changing it.",
                sources=[_aymt_source(rel) for rel in orphans[:AYMT_SOURCE_LIMIT]],
                urgency=1,
                leverage=2,
                effort=2,
                confidence=4,
                dependency=0,
                staleness=min(4, len(orphans)),
            )
        )
    candidates.extend(_aymt_cadence_candidates(today_d, set(allowed)))
    if environment["state"] == "selected":
        environment_expiry = iso_date(environment["freshness"]["expiresAt"])
        if environment_expiry is not None and (environment_expiry - today_d).days <= 14:
            expired = environment_expiry < today_d
            candidates.append(
                _aymt_candidate(
                    kind="environment",
                    outcome="Refresh the selected environment inventory",
                    section="do-next" if expired else "keep-warm",
                    why_now=(
                        "The selected environment metadata is expired."
                        if expired
                        else f"The selected environment metadata expires in {(environment_expiry - today_d).days} days."
                    ),
                    next_step="Run agent-orientation for the selected environment and review its metadata refresh.",
                    caveat="AYMT uses manifest metadata only and never reads environment note bodies.",
                    sources=[_aymt_source("10_Agents/environments/README.md", "Environment contract")],
                    urgency=4 if expired else 2,
                    leverage=3,
                    effort=2,
                    confidence=4,
                    dependency=0,
                    staleness=4 if expired else 1,
                )
            )
    candidates.extend(_load_aymt_github_input(github_input, stdin, today_d))
    selected_candidates, summary = _select_aymt_candidates(candidates)
    inputs = {
        "candidates": selected_candidates,
        "date": today_d.isoformat(),
        "environment": environment,
        "schemaVersion": AYMT_SCHEMA_VERSION,
        "summary": summary,
    }
    digest = _sha256_bytes(_canonical_json(inputs))
    return {**inputs, "inputDigest": digest}


def _aymt_relative_destination(source: str, target: str) -> str:
    return quote(posixpath.relpath(target, posixpath.dirname(source)), safe="/-._~")


def render_aymt(payload: dict) -> bytes:
    tomorrow = (date.fromisoformat(payload["date"]) + timedelta(days=1)).isoformat()
    sections = (
        ("do-next", "Do next"),
        ("unblock-or-decide", "Unblock or decide"),
        ("keep-warm", "Keep warm"),
    )
    lines = [
        "---",
        'title: "Actions You May Take"',
        "tags:",
        "  - audience/agent",
        "  - audience/human",
        "  - type/meta",
        "  - workflow/canonical",
        f"updated: {payload['date']}",
        f"expires: {tomorrow}",
        "generated: brain-aymt-v1",
        f'input-digest: "{payload["inputDigest"]}"',
        'content-digest: "PENDING"',
        "---",
        "",
        AYMT_MARKER,
        "",
        "# Actions You May Take",
        "",
        "A deterministic local brief. It suggests options; it does not authorize external action.",
        "",
    ]
    for section, heading in sections:
        lines.extend([f"## {heading}", ""])
        rows = [row for row in payload["candidates"] if row["section"] == section]
        if not rows:
            lines.extend(["_No safe, concrete suggestion for this section._", ""])
            continue
        for row in rows:
            lines.append(f"### {_aymt_markdown_text(row['outcome'])}")
            lines.append("")
            lines.append(f"- **Why now:** {_aymt_markdown_text(row['whyNow'] or 'No stronger timing signal.')}")
            lines.append(f"- **Next step:** {_aymt_markdown_text(row['nextStep'] or 'Define the next concrete step.')}")
            lines.append(f"- **Caveat:** {_aymt_markdown_text(row['caveat'] or 'Confirm context before acting.')}")
            rendered_sources = []
            for source in row["sources"]:
                if source["kind"] == "vault":
                    destination = _aymt_relative_destination(AYMT_RELPATH, source["path"])
                    rendered_sources.append(f"[{_aymt_label(source['label'])}]({destination})")
                else:
                    rendered_sources.append(f"[{_aymt_label(source['label'])}]({source['url']})")
            lines.append("- **Sources:** " + (", ".join(rendered_sources) or "None"))
            lines.append("")
    env = payload["environment"]
    lines.extend(["## Context", ""])
    if env["state"] == "unconfigured":
        lines.append("- **Environment:** not configured; shared tracked sources only.")
    else:
        freshness = env["freshness"]
        lines.append(
            f"- **Environment:** `{env['slug']}` selected via `{env['source']}`; "
            f"metadata checked {freshness['checkedAt']}, expires {freshness['expiresAt']}."
        )
    lines.append("")
    provisional = ("\n".join(lines).rstrip("\n") + "\n").encode("utf-8")
    content_digest = _sha256_bytes(provisional.replace(b'content-digest: "PENDING"', b'content-digest: ""'))
    return provisional.replace(b'content-digest: "PENDING"', f'content-digest: "{content_digest}"'.encode())


# ---------------------------------------------------------------------------
# §24 Home


def _revalidate_action_context(root: Path, context: dict) -> None:
    """Refuse if the tracked universe or any consumed authority changed."""
    current_tracked = git_tracked(root)
    if current_tracked is None or current_tracked != context["tracked"]:
        raise AymtError("tracked action corpus changed")
    for rel, snapshot in sorted(context["authoritySnapshots"].items()):
        try:
            current = _read_nofollow_bytes(
                root, rel, max_bytes=snapshot["maxBytes"]
            )
        except OSError:
            raise AymtError("tracked action authority changed") from None
        if current != snapshot["bytes"]:
            raise AymtError("tracked action authority changed")
    for rel, expected in sorted(context["freshnessSnapshots"].items()):
        if expected is None:
            try:
                _read_nofollow_bytes(root, rel)
            except OSError:
                continue
            raise AymtError("tracked action source changed")
        try:
            current = _read_nofollow_bytes(root, rel)
        except OSError:
            raise AymtError("tracked action source changed") from None
        if current != expected:
            raise AymtError("tracked action source changed")


def _home_validation_summary(allowed: dict[str, dict]) -> dict:
    """Bounded rule/count signal over only safe authenticated note records."""
    counts: dict[tuple[str, str], int] = {}

    def add(severity: str, rule: str, amount: int = 1) -> None:
        counts[(severity, rule)] = counts.get((severity, rule), 0) + amount

    for rel, rec in allowed.items():
        fm = rec.get("frontmatter", {})
        frontmatter_errors = rec.get("frontmatterErrors", [])
        if rel != "CLAUDE.md":
            for finding in frontmatter_errors:
                rule = finding.split(":", 1)[0]
                add("warning" if rule in FM_WARNING_RULES or rule == "duplicate-key" else "error", rule)
            if not frontmatter_errors:
                if not fm:
                    add("error", "missing-frontmatter")
                else:
                    if rec.get("title") is None:
                        add("error", "missing-title")
                    tags = fm.get("tags")
                    if tags is None or tags == []:
                        add("error", "missing-tags")
                    if "updated" not in fm:
                        add("error", "missing-updated")
        for task in rec.get("tasks", []):
            if task.get("malformed"):
                add("warning", "task-invalid-date", len(task["malformed"]))
        for link in rec.get("links", []):
            if link.get("placeholder"):
                continue
            status = link.get("resolution", {}).get("status")
            if link.get("resolved") is None:
                add("error", "ambiguous-link" if status == "ambiguous" else "unresolved-link")
            if status == "unsupported-block-reference":
                add("warning", "unsupported-block-reference")
            if any(value in {"case-mismatch", "fragment-case-mismatch"} for value in link.get("warnings", [])):
                add("warning", "case-mismatch")
    rows = [
        {"count": count, "rule": rule, "severity": severity}
        for (severity, rule), count in sorted(counts.items())
    ]
    return {
        "errors": sum(row["count"] for row in rows if row["severity"] == "error"),
        "rules": rows[:12],
        "truncatedRules": max(0, len(rows) - 12),
        "warnings": sum(row["count"] for row in rows if row["severity"] == "warning"),
    }


def _home_safe_index_fresh(
    committed: bytes | None,
    freshness_index: dict,
) -> bool:
    """Compare the complete privacy-reduced tracked index by canonical bytes."""
    return (
        committed is not None
        and committed == serialize(reduce_restricted(freshness_index))
    )


def _build_action_context(root: Path, today_d: date, selection: dict) -> dict:
    """One authenticated tracked snapshot shared by AYMT and Home."""
    tracked_paths = git_tracked(root)
    if tracked_paths is None:
        raise AymtError("tracked action corpus is unavailable")
    tracked = frozenset(tracked_paths)
    if ADOPT_EXAMPLES_RELPATH not in tracked:
        raise AymtError("tracked seed inventory is unavailable")
    manifest_rel = None
    if selection["state"] == "selected":
        manifest_rel = f"{ENVIRONMENTS_RELPATH}/{selection['slug']}/{ENVIRONMENT_MANIFEST_NAME}"
        if manifest_rel not in tracked:
            raise AymtError("selected environment metadata is not tracked")
    authority_snapshots: dict[str, dict[str, object]] = {}

    def authority(rel: str, max_bytes: int) -> bytes:
        try:
            raw = _read_nofollow_bytes(root, rel, max_bytes=max_bytes)
        except OSError:
            raise AymtError("tracked action authority is unavailable") from None
        authority_snapshots[rel] = {"bytes": raw, "maxBytes": max_bytes}
        return raw

    try:
        seed_raw = authority(ADOPT_EXAMPLES_RELPATH, 64 * 1024)
        manifest_raw = (
            authority(manifest_rel, 64 * 1024) if manifest_rel is not None else None
        )
        environment = _aymt_environment(selection, manifest_raw)
        seed_paths = _aymt_seed_paths(seed_raw)
    except AymtError:
        raise
    notes, assets = walk_corpus(root, selected_environment=None)
    environment_prefix = ENVIRONMENTS_RELPATH + "/"
    # Keep every tracked pathname in the resolver universe so safe links to an
    # excluded target do not become false unresolved-health findings. Capture
    # the complete shared-note snapshot once for the generic committed-index
    # freshness bit, but decode only eligible bytes into the action context.
    notes = sorted(rel for rel in notes if rel in tracked)
    assets = sorted(
        rel for rel in assets
        if rel in tracked
    )
    snapshots: dict[str, bytes | None] = {}
    snapshot_texts: dict[str, str | None] = {}
    freshness_snapshots: dict[str, bytes | None] = {}
    for rel in notes:
        try:
            raw = _read_nofollow_bytes(root, rel)
        except OSError:
            raw = None
        freshness_snapshots[rel] = raw
        if (
            rel.startswith(environment_prefix)
            or rel in {AYMT_RELPATH, HOME_RELPATH}
            or _aymt_is_seed_path(rel, seed_paths)
        ):
            snapshots[rel] = None
            snapshot_texts[rel] = None
            continue
        snapshots[rel] = raw
        snapshot_texts[rel] = (
            None if snapshots[rel] is None else _decode_note_bytes(snapshots[rel])[0]
        )
    index = build_index(root, notes, assets, note_snapshots=snapshots)
    freshness_index = build_index(
        root, notes, assets, note_snapshots=freshness_snapshots
    )
    restricted = {rel for rel, rec in index["notes"].items() if is_restricted(rec)}
    allowed = {
        rel: rec
        for rel, rec in index["notes"].items()
        if snapshots.get(rel) is not None
        and _aymt_note_allowed(rel, rec, restricted)
    }
    safe_notes = {rel: {**rec, "backlinks": []} for rel, rec in allowed.items()}
    for source, rec in safe_notes.items():
        for link in rec.get("links", []):
            target = link.get("resolved")
            if target in safe_notes and source not in safe_notes[target]["backlinks"]:
                safe_notes[target]["backlinks"].append(source)
    for rec in safe_notes.values():
        rec["backlinks"].sort()
    if CONFIG_RELPATH in tracked:
        try:
            config_text = authority(CONFIG_RELPATH, 64 * 1024).decode("utf-8")
        except UnicodeError:
            raise AymtError("tracked action config is unavailable") from None
        config, _findings = parse_config(config_text)
    else:
        config, _findings = {}, []
    committed_index = (
        authority(INDEX_RELPATH, 4 * 1024 * 1024)
        if INDEX_RELPATH in tracked
        else None
    )
    report = compute_report(
        {**index, "notes": safe_notes}, today_d, report_thresholds(config), None
    )
    return {
        "allowed": allowed,
        "authoritySnapshots": authority_snapshots,
        "environment": environment,
        "index": index,
        "indexFresh": _home_safe_index_fresh(committed_index, freshness_index),
        "report": report,
        "freshnessSnapshots": freshness_snapshots,
        "snapshots": snapshots,
        "snapshotTexts": snapshot_texts,
        "tracked": tracked,
        "validation": _home_validation_summary(allowed),
    }


def _home_path_row(rel: str, rec: dict) -> dict:
    return {
        "path": rel,
        "title": _aymt_text(rec.get("title") or rel.rsplit("/", 1)[-1], limit=HOME_FIELD_LIMIT),
        "updated": rec.get("updated"),
    }


def _home_review_rows(today_d: date, allowed: dict[str, dict]) -> list[dict]:
    iso_year, iso_week, _iso_day = today_d.isocalendar()
    quarter = (today_d.month - 1) // 3 + 1
    current = (
        ("daily", f"03_Journal/periodic/daily/{today_d.isoformat()}.md", "Today's daily log"),
        ("weekly", f"03_Journal/periodic/weekly/{iso_year}-W{iso_week:02d}-review.md", "Current weekly review"),
        ("monthly", f"03_Journal/periodic/monthly/{today_d.year}-{today_d.month:02d}-review.md", "Current monthly review"),
        ("quarterly", f"03_Journal/periodic/quarterly/{today_d.year}-Q{quarter}-review.md", "Current quarterly review"),
        ("yearly", f"03_Journal/periodic/yearly/{today_d.year}-review.md", "Current yearly review"),
    )
    rows: list[dict] = []
    for cadence, rel, label in current:
        if rel not in allowed:
            continue
        rows.append(
            {
                "caveat": "This records the current period; inspect the note before treating it as complete.",
                "nextStep": "Open the tracked note and continue or review its recorded cadence.",
                "outcome": label,
                "sources": [_aymt_source(rel, label)],
                "state": "present",
                "whyNow": f"The safe tracked {cadence} note for the current period exists.",
            }
        )
    for row in _aymt_cadence_candidates(today_d, set(allowed)):
        rows.append(
            {
                "caveat": row["caveat"],
                "nextStep": row["nextStep"],
                "outcome": row["outcome"],
                "sources": row["sources"],
                "state": "due",
                "whyNow": row["whyNow"],
            }
        )
    return rows


def build_home(
    root: Path,
    *,
    today_d: date | None = None,
    selection: dict | None = None,
    github_input: str | None = None,
    stdin=None,
) -> dict:
    """Build Home from structured AYMT plus one safe tracked corpus snapshot."""
    today_d = today_d or today()
    stdin = stdin or sys.stdin
    try:
        selected = selection or select_aymt_environment(root)
        context = _build_action_context(root, today_d, selected)
        aymt = build_aymt(
            root,
            today_d=today_d,
            selection=selected,
            github_input=github_input,
            stdin=stdin,
            _context=context,
        )
    except (AymtError, EnvironmentSelectionError):
        raise HomeError("Home inputs are unavailable") from None
    allowed = context["allowed"]
    report = context["report"]

    global_actions = sorted(
        aymt["candidates"],
        key=lambda row: (
            -row["score"],
            -row["signals"]["urgency"],
            -row["signals"]["leverage"],
            row["signals"]["effort"],
            row["signals"]["dependency"],
            row["id"],
        ),
    )
    actions = global_actions[:3]

    overdue: list[dict] = []
    due: list[dict] = []
    for rel, rec in sorted(allowed.items()):
        for task in rec.get("tasks", []):
            if task.get("status") != "open" or task.get("malformed"):
                continue
            due_d = iso_date(task.get("due"))
            if due_d is None:
                continue
            row = {
                "due": due_d.isoformat(),
                "line": task["line"],
                "path": rel,
                "text": _aymt_text(task.get("text"), limit=HOME_FIELD_LIMIT),
            }
            (overdue if due_d < today_d else due).append(row)
    overdue.sort(key=lambda row: (row["due"], row["path"], row["line"]))
    due.sort(key=lambda row: (row["due"], row["path"], row["line"]))

    inbox_paths = [
        rel for rel in sorted(allowed)
        if rel.startswith(INBOX_PREFIX) and rel != "02_Inbox/README.md"
    ]
    inbox_rows = []
    for bucket in REPORT_BUCKET_LABELS:
        inbox_rows.extend(report["inboxAging"]["buckets"][bucket])
    inbox_rows.sort(
        key=lambda row: (
            -(row["ageDays"] if row["ageDays"] is not None else -1),
            row["path"],
        )
    )
    active_projects = [
        _home_path_row(rel, rec)
        for rel, rec in sorted(allowed.items())
        if rel.startswith("04_Projects/") and "status/active" in frontmatter_tags(rec)
    ][:HOME_ACTIVE_CAP]
    active_areas = [
        _home_path_row(rel, rec)
        for rel, rec in sorted(allowed.items())
        if rel.startswith("05_Areas/") and "status/active" in frontmatter_tags(rec)
    ][:HOME_ACTIVE_CAP]

    review_rows = _home_review_rows(today_d, allowed)

    current_paths = []
    for rel, label in (
        (CORE_FRAMEWORK_PATHS["now"], "Now"),
        (CORE_FRAMEWORK_PATHS["status"], "Status"),
        (CORE_FRAMEWORK_PATHS["changelog"], "Changelog"),
    ):
        if rel in allowed:
            current_paths.append({"label": label, "path": rel, "updated": allowed[rel].get("updated")})

    expired = []
    near_expiry = []
    for rel, rec in sorted(allowed.items()):
        expires_d = iso_date(rec.get("frontmatter", {}).get("expires"))
        if expires_d is None:
            continue
        row = {"expires": expires_d.isoformat(), "path": rel, "title": rec.get("title")}
        if expires_d < today_d:
            expired.append(row)
        elif (expires_d - today_d).days <= 14:
            near_expiry.append(row)
    expired.sort(key=lambda row: (row["expires"], row["path"]))
    near_expiry.sort(key=lambda row: (row["expires"], row["path"]))

    navigation = [
        {"label": "Vault index", "path": CORE_FRAMEWORK_PATHS["index"]},
        {"label": "Actions You May Take", "path": AYMT_RELPATH},
    ]
    for rel, label in (
        (CORE_FRAMEWORK_PATHS["now"], "Now"),
        ("02_Inbox/README.md", "Inbox"),
        ("04_Projects/README.md", "Projects"),
        ("05_Areas/README.md", "Areas"),
        (CORE_FRAMEWORK_PATHS["status"], "Status"),
        (CORE_FRAMEWORK_PATHS["changelog"], "Changelog"),
    ):
        if rel in allowed:
            navigation.append({"label": label, "path": rel})

    inputs = {
        "actions": actions,
        "active": {"areas": active_areas, "projects": active_projects},
        "aymt": {"inputDigest": aymt["inputDigest"], "summary": aymt["summary"]},
        "current": current_paths,
        "date": today_d.isoformat(),
        "environment": context["environment"],
        "health": {
            "expired": expired[:HOME_ACTIVE_CAP],
            "expiredCount": len(expired),
            "index": {"fresh": context["indexFresh"], "scope": "tracked-safe"},
            "nearExpiry": near_expiry[:HOME_ACTIVE_CAP],
            "nearExpiryCount": len(near_expiry),
            "orphanCount": len(report["orphans"]),
            "staleActive": report["staleActive"][:HOME_ACTIVE_CAP],
            "staleActiveCount": len(report["staleActive"]),
            "unresolvedLinkCount": report["unresolvedLinks"]["count"],
            "validation": context["validation"],
        },
        "inbox": {
            "count": len(inbox_paths),
            "oldest": inbox_rows[:HOME_TASK_CAP],
            "triageDebt": len(report["inboxAging"]["triageDebt"]),
        },
        "navigation": navigation,
        "reviews": review_rows,
        "schemaVersion": HOME_SCHEMA_VERSION,
        "tasks": {"due": due[:HOME_TASK_CAP], "overdue": overdue[:HOME_TASK_CAP]},
    }
    payload = {**inputs, "inputDigest": _sha256_bytes(_canonical_json(inputs))}
    try:
        _revalidate_action_context(root, context)
    except AymtError:
        raise HomeError("Home inputs are unavailable") from None
    return payload


def _home_link(source: str, target: str, label: str) -> str:
    destination = _aymt_relative_destination(source, target)
    return f"[{_aymt_label(label)}]({destination})"


def _home_sources(row: dict) -> str:
    rendered = []
    for source in row.get("sources", []):
        if source["kind"] == "vault":
            rendered.append(_home_link(HOME_RELPATH, source["path"], source["label"]))
        else:
            rendered.append(f"[{_aymt_label(source['label'])}]({source['url']})")
    return ", ".join(rendered) or "None"


def render_home(payload: dict) -> bytes:
    tomorrow = (date.fromisoformat(payload["date"]) + timedelta(days=1)).isoformat()
    lines = [
        "---",
        'title: "Home"',
        "tags:",
        "  - audience/agent",
        "  - audience/human",
        "  - type/meta",
        "  - workflow/canonical",
        f"updated: {payload['date']}",
        f"expires: {tomorrow}",
        "generated: brain-home-v1",
        f'input-digest: "{payload["inputDigest"]}"',
        'content-digest: "PENDING"',
        "---",
        "",
        HOME_MARKER,
        "",
        "# Home",
        "",
        "A deterministic, local navigation surface. Refresh it explicitly; it does not authorize external action.",
        "",
        "## Top actions",
        "",
    ]
    if not payload["actions"]:
        lines.extend(["_No safe, concrete action is currently selected._", ""])
    for row in payload["actions"]:
        lines.extend(
            [
                f"### {_aymt_markdown_text(row['outcome'])}",
                "",
                f"- **Why now:** {_aymt_markdown_text(row['whyNow'])}",
                f"- **Next step:** {_aymt_markdown_text(row['nextStep'])}",
                f"- **Sources:** {_home_sources(row)}",
                "",
            ]
        )

    lines.extend(["## Due and overdue", ""])
    if not payload["tasks"]["overdue"] and not payload["tasks"]["due"]:
        lines.extend(["_No tracked safe task has a machine-readable due date._", ""])
    for heading, rows in (("Overdue", payload["tasks"]["overdue"]), ("Due", payload["tasks"]["due"])):
        if rows:
            lines.extend([f"### {heading}", ""])
            for row in rows:
                source = _home_link(HOME_RELPATH, row["path"], f"{row['path']}:{row['line']}")
                lines.append(f"- **{row['due']}** — {_aymt_markdown_text(row['text'])} ({source})")
            lines.append("")

    inbox = payload["inbox"]
    lines.extend(["## Inbox", ""])
    lines.append(
        f"- **Tracked safe notes:** {inbox['count']}"
        f"; **triage debt:** {inbox['triageDebt']}"
    )
    for row in inbox["oldest"]:
        age = "age unknown" if row["ageDays"] is None else f"{row['ageDays']} days old"
        lines.append(f"- {_home_link(HOME_RELPATH, row['path'], row['path'])} — {age}")
    lines.append("")

    lines.extend(["## Active work", ""])
    for heading, rows in (("Projects", payload["active"]["projects"]), ("Areas", payload["active"]["areas"])):
        lines.extend([f"### {heading}", ""])
        if not rows:
            lines.append("_No safe tracked item is tagged active._")
        for row in rows:
            lines.append(f"- {_home_link(HOME_RELPATH, row['path'], row['title'])} — updated {row['updated']}")
        lines.append("")

    lines.extend(["## Cadence and reviews", ""])
    if not payload["reviews"]:
        lines.extend(["_No periodic review is due in today's exact cadence window._", ""])
    for row in payload["reviews"]:
        lines.append(f"- **{_aymt_markdown_text(row['outcome'])}:** {_aymt_markdown_text(row['nextStep'])} ({_home_sources(row)})")
    if payload["reviews"]:
        lines.append("")

    lines.extend(["## Current state", ""])
    for row in payload["current"]:
        lines.append(f"- {_home_link(HOME_RELPATH, row['path'], row['label'])} — updated {row['updated']}")
    if not payload["current"]:
        lines.append("_No safe current-state source is available._")
    lines.append("")

    health = payload["health"]
    lines.extend(["## Expiry and health", ""])
    lines.append(
        f"- **Expired:** {health['expiredCount']}; **near expiry:** {health['nearExpiryCount']}; "
        f"**stale active:** {health['staleActiveCount']}; **orphans:** {health['orphanCount']}; "
        f"**unresolved links:** {health['unresolvedLinkCount']}"
    )
    validation = health["validation"]
    index_state = "fresh" if health["index"]["fresh"] else "stale"
    lines.append(
        f"- **Safe validation:** {validation['errors']} errors, {validation['warnings']} warnings; "
        f"**tracked-safe index:** {index_state}."
    )
    for row in health["expired"]:
        lines.append(f"- Expired {row['expires']}: {_home_link(HOME_RELPATH, row['path'], row['title'] or row['path'])}")
    for row in health["nearExpiry"]:
        lines.append(f"- Expires {row['expires']}: {_home_link(HOME_RELPATH, row['path'], row['title'] or row['path'])}")
    for row in health["staleActive"]:
        lines.append(f"- Stale active ({row['daysOld']} days): {_home_link(HOME_RELPATH, row['path'], row['title'])}")
    lines.append("")

    environment = payload["environment"]
    lines.extend(["## Current environment", ""])
    if environment["state"] == "unconfigured":
        lines.append("- Not configured; Home used shared tracked sources only.")
    else:
        freshness = environment["freshness"]
        lines.append(
            f"- `{environment['slug']}` selected via `{environment['source']}`; "
            f"metadata checked {freshness['checkedAt']}, expires {freshness['expiresAt']}."
        )
    lines.extend(["", "## Navigate", ""])
    lines.append(" · ".join(_home_link(HOME_RELPATH, row["path"], row["label"]) for row in payload["navigation"]))
    lines.append("")
    provisional = ("\n".join(lines).rstrip("\n") + "\n").encode("utf-8")
    digest = _sha256_bytes(provisional.replace(b'content-digest: "PENDING"', b'content-digest: ""'))
    return provisional.replace(b'content-digest: "PENDING"', f'content-digest: "{digest}"'.encode())


def _aymt_mode_owned(mode: int) -> bool:
    # Windows exposes only the read-only bit through chmod/stat; a normal
    # writable file commonly reports 0666 rather than POSIX 0644. Mutation is
    # still disabled there, while portable freshness refuses read-only files.
    if os.name == "nt":
        return bool(mode & stat.S_IREAD) and bool(mode & stat.S_IWRITE)
    return mode == 0o644


def _aymt_owned(raw: bytes, mode: int, marker: str = AYMT_MARKER) -> bool:
    if not _aymt_mode_owned(mode) or marker.encode() not in raw:
        return False
    match = re.search(rb'^content-digest: "([0-9a-f]{64})"$', raw, re.MULTILINE)
    if match is None:
        return False
    expected = match.group(1).decode()
    neutral = re.sub(rb'^content-digest: "[0-9a-f]{64}"$', b'content-digest: ""', raw, count=1, flags=re.MULTILINE)
    return _sha256_bytes(neutral) == expected


def _aymt_casefold_collision(root: Path, relpath: str = AYMT_RELPATH) -> bool:
    """Portable read-only check for a sibling spelling of one generated file."""
    parent_path = root / posixpath.dirname(relpath)
    before = os.lstat(parent_path)
    if _link_like_stat(before) or not stat.S_ISDIR(before.st_mode):
        raise OSError("AYMT parent path is unsafe")
    with os.scandir(parent_path) as entries:
        names = sorted(entry.name for entry in entries)
    after = os.lstat(parent_path)
    if (
        _link_like_stat(after)
        or (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode))
        != (after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode))
    ):
        raise OSError("AYMT parent path changed during read")
    name = posixpath.basename(relpath)
    return any(candidate.casefold() == name.casefold() and candidate != name for candidate in names)


def _aymt_casefold_collision_at(parent: int, name: str) -> bool:
    """Held-parent equivalent used at each dedicated-writer commit boundary."""
    return any(
        candidate.casefold() == name.casefold() and candidate != name
        for candidate in os.listdir(parent)
    )


def _read_current_aymt(root: Path) -> tuple[bytes | None, int | None]:
    """Portable no-follow current-file reader for zero-write preview/check."""
    try:
        if _aymt_casefold_collision(root):
            raise AymtError("AYMT has a case-insensitive sibling collision")
        raw, info = _read_nofollow_file(root, AYMT_RELPATH, max_bytes=256 * 1024)
    except FileNotFoundError:
        return None, None
    except AymtError:
        raise
    except OSError:
        raise AymtError("existing AYMT is not a safe regular file") from None
    return raw, stat.S_IMODE(info.st_mode)


def _read_current_home(root: Path) -> tuple[bytes | None, int | None]:
    """Portable no-follow current-file reader for zero-write Home modes."""
    try:
        if _aymt_casefold_collision(root, HOME_RELPATH):
            raise HomeError("Home has a case-insensitive sibling collision")
        raw, info = _read_nofollow_file(root, HOME_RELPATH, max_bytes=512 * 1024)
    except FileNotFoundError:
        return None, None
    except HomeError:
        raise
    except OSError:
        raise HomeError("existing Home is not a safe regular file") from None
    return raw, stat.S_IMODE(info.st_mode)


def _write_generated_exact(
    root: Path,
    desired: bytes,
    *,
    relpath: str,
    marker: str,
) -> str:
    """Descriptor-bound writer allowlisted to the two generated exact paths."""
    if (relpath, marker) not in {
        (AYMT_RELPATH, AYMT_MARKER),
        (HOME_RELPATH, HOME_MARKER),
    }:
        raise AymtError("generated exact-file write authority is unavailable")
    if not _migration_mutation_supported():
        raise AymtError("safe AYMT writes are unavailable on this runtime; preview/check only")
    try:
        parent, name = _open_migration_parent(root, relpath)
    except (OSError, LinkMigrationError):
        raise AymtError("AYMT parent path is unsafe") from None
    try:
        case_collision = _aymt_casefold_collision_at(parent, name)
    except OSError:
        os.close(parent)
        raise AymtError("AYMT parent path is unsafe") from None
    if case_collision:
        os.close(parent)
        raise AymtError("AYMT has a case-insensitive sibling collision")
    item = {
        "desired": desired,
        "name": name,
        "new": None,
        "parent": parent,
        "stage_ownership": {},
    }
    prior: bytes | None = None
    prior_info: os.stat_result | None = None
    backup: str | None = None
    published = False
    committed = False
    previous_term = None
    result: str | None = None
    cleanup_error: AymtError | None = None

    def retire_owned_backup() -> None:
        nonlocal backup, committed
        if backup is None or prior is None or prior_info is None:
            return
        current_bytes, current_info = _read_migration_at(parent, name)
        if current_bytes != desired or stat.S_IMODE(current_info.st_mode) != 0o644:
            raise AymtError(
                "AYMT changed before backup retirement; recovery data preserved"
            )
        backup_bytes, backup_info = _read_migration_at(parent, backup)
        if (
            backup_bytes != prior
            or _link_migration_identity(backup_info) != _link_migration_identity(prior_info)
        ):
            raise AymtError("AYMT backup ownership changed; foreign backup preserved")
        os.unlink(backup, dir_fd=parent)
        # Removing the only prior copy is the commit point. A later directory
        # fsync or authenticated-stage cleanup error is reported, but must not
        # remove the installed exact result with no rollback source remaining.
        backup = None
        committed = True
        try:
            os.fsync(parent)
        except OSError:
            raise AymtError("AYMT commit durability could not be confirmed") from None

    try:
        try:
            prior, prior_info = _read_migration_at(parent, name)
        except FileNotFoundError:
            pass
        except (OSError, LinkMigrationError):
            raise AymtError("existing AYMT is not a safe regular file") from None
        if prior == desired and prior_info is not None and stat.S_IMODE(prior_info.st_mode) == 0o644:
            result = "unchanged"
            return result
        if prior is not None and (
            prior_info is None or not _aymt_owned(prior, stat.S_IMODE(prior_info.st_mode), marker)
        ):
            raise AymtError("existing AYMT is foreign or modified; preserved")
        if hasattr(signal, "SIGTERM"):
            try:
                previous_term = signal.getsignal(signal.SIGTERM)
                signal.signal(signal.SIGTERM, lambda _s, _f: (_ for _ in ()).throw(KeyboardInterrupt()))
            except (ValueError, OSError):
                previous_term = None
        item["new"] = _unused_migration_name(parent, name, "new")
        _stage_migration_at(
            parent,
            name,
            desired,
            0o644,
            ownership=item["stage_ownership"],
            reserved_name=item["new"],
        )
        if _aymt_casefold_collision_at(parent, name):
            raise AymtError("AYMT has a case-insensitive sibling collision")
        if prior is None:
            # Publication can complete before the helper's directory fsync
            # raises. Record intent first so rollback authenticates/removes it.
            published = True
            _install_migration_at(parent, item["new"], name)
        else:
            backup = _unused_migration_name(parent, name, "old")
            # Re-authenticate the held final immediately before quarantine.
            current, current_info = _read_migration_at(parent, name)
            if current != prior or _link_migration_identity(current_info) != _link_migration_identity(prior_info):
                raise AymtError("AYMT changed before replacement; preserved")
            _quarantine_migration_at(parent, name, backup)
            published = True
            _install_migration_at(parent, item["new"], name)
        actual, actual_info = _read_migration_at(parent, name)
        staged_info = os.stat(item["new"], dir_fd=parent, follow_symlinks=False)
        if (
            actual != desired
            or stat.S_IMODE(actual_info.st_mode) != 0o644
            or (actual_info.st_dev, actual_info.st_ino) != (staged_info.st_dev, staged_info.st_ino)
        ):
            raise AymtError("AYMT changed during replacement; recovery data preserved")
        if _aymt_casefold_collision_at(parent, name):
            raise AymtError("AYMT gained a case-insensitive sibling collision")
        # Authenticate the final result again immediately before the old
        # generated file becomes irrecoverable. An in-place write changes the
        # staged/final inode together; bytes are the authority here.
        final_before_retire, final_before_retire_info = _read_migration_at(parent, name)
        if final_before_retire != desired or stat.S_IMODE(final_before_retire_info.st_mode) != 0o644:
            raise AymtError("AYMT changed before backup retirement; recovery data preserved")
        if _aymt_casefold_collision_at(parent, name):
            raise AymtError("AYMT gained a case-insensitive sibling collision")
        if backup is not None:
            retire_owned_backup()
        else:
            committed = True
        result = "written"
        return result
    except BaseException as exc:
        if published and not committed:
            try:
                actual, actual_info = _read_migration_at(parent, name)
                staged_info = os.stat(item["new"], dir_fd=parent, follow_symlinks=False)
                if actual == desired and (actual_info.st_dev, actual_info.st_ino) == (
                    staged_info.st_dev, staged_info.st_ino
                ):
                    os.unlink(name, dir_fd=parent)
                    os.fsync(parent)
            except (OSError, LinkMigrationError, FileNotFoundError):
                pass
        recovery_collision = False
        if backup is not None and not committed:
            try:
                if _restore_quarantined_at(parent, backup, name):
                    os.unlink(backup, dir_fd=parent)
                    backup = None
                else:
                    recovery_collision = True
            except (OSError, LinkMigrationError):
                recovery_collision = True
        if recovery_collision:
            raise AymtError(
                f"AYMT replacement raced; foreign final preserved and prior retained at 00_Meta/{backup}"
            ) from None
        if isinstance(exc, (AymtError, KeyboardInterrupt)):
            raise
        raise AymtError("AYMT write failed; prior content preserved") from None
    finally:
        active_error = sys.exc_info()[0] is not None
        try:
            if previous_term is not None:
                try:
                    signal.signal(signal.SIGTERM, previous_term)
                except (ValueError, OSError):
                    cleanup_error = AymtError(
                        "AYMT signal cleanup failed safely"
                    )
            if item["new"] is not None:
                try:
                    _remove_owned_migration_stage(item)
                except (OSError, LinkMigrationError):
                    cleanup_error = AymtError(
                        "AYMT stage cleanup failed safely; foreign content preserved"
                    )
        finally:
            os.close(parent)
        if cleanup_error is not None and not active_error:
            raise cleanup_error


def write_aymt(root: Path, desired: bytes) -> str:
    """Dedicated AYMT-only writer; generic agent write rules stay closed."""
    return _write_generated_exact(
        root, desired, relpath=AYMT_RELPATH, marker=AYMT_MARKER
    )


def write_home(root: Path, desired: bytes) -> str:
    """Dedicated HOME-only wrapper around the proven descriptor-bound writer."""
    try:
        return _write_generated_exact(
            root, desired, relpath=HOME_RELPATH, marker=HOME_MARKER
        )
    except KeyboardInterrupt:
        raise
    except AymtError:
        raise HomeError("Home write failed safely") from None


def cmd_home(root: Path, args) -> int:
    try:
        payload = build_home(
            root,
            selection=getattr(args, "home_selection", None),
            github_input=args.github_input,
            stdin=sys.stdin,
        )
        rendered = render_home(payload)
        try:
            current, current_mode = _read_current_home(root)
        except HomeError:
            current, current_mode = None, None
        fresh = (
            current == rendered
            and current_mode is not None
            and _aymt_owned(current, current_mode, HOME_MARKER)
        )
        if args.write:
            outcome = write_home(root, rendered)
            payload = {**payload, "fresh": True, "write": outcome}
        else:
            payload = {**payload, "fresh": fresh}
    except (HomeError, KeyboardInterrupt):
        message = "Home generation failed safely"
        if args.json:
            print(json.dumps({"error": message}, indent=1, sort_keys=True))
        else:
            print(f"error: {message}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    elif args.write:
        print(f"{HOME_RELPATH}: {payload['write']}")
    else:
        sys.stdout.buffer.write(rendered)
    return 1 if args.check and not fresh else 0


def cmd_aymt(root: Path, args) -> int:
    try:
        payload = build_aymt(
            root,
            selection=getattr(args, "aymt_selection", None),
            github_input=args.github_input,
            stdin=sys.stdin,
        )
        rendered = render_aymt(payload)
        try:
            current, current_mode = _read_current_aymt(root)
        except AymtError:
            current, current_mode = None, None
        fresh = (
            current == rendered
            and current_mode is not None
            and _aymt_owned(current, current_mode)
        )
        if args.write:
            outcome = write_aymt(root, rendered)
            payload = {**payload, "fresh": True, "write": outcome}
        else:
            payload = {**payload, "fresh": fresh}
    except (AymtError, KeyboardInterrupt):
        message = "AYMT generation failed safely"
        if args.json:
            print(json.dumps({"error": message}, indent=1, sort_keys=True))
        else:
            print(f"error: {message}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    elif args.write:
        print(f"{AYMT_RELPATH}: {payload['write']}")
    else:
        sys.stdout.buffer.write(rendered)
    return 1 if args.check and not fresh else 0


def cmd_artifacts(root: Path, args) -> int:
    """Preview, check, write, or locally open the exact artifact inventory."""
    import artifacts as artifact_pipeline

    return artifact_pipeline.command(sys.modules[__name__], root, args)


def resolve_note_arg(index: dict, arg: str) -> str | None:
    # Index paths are /-separated (spec §2); accept OS-native separators from
    # callers like the VS Code ${relativeFile} task on Windows.
    target = nfc(arg.strip()).replace("\\", "/")
    if target.endswith(".md"):
        target = target[:-3]
    notes = sorted(index["notes"])
    resolver = Resolver(notes, index["assets"], {p: index["notes"][p]["title"] for p in notes})
    resolved, _ = resolver.resolve(target, target)
    return resolved if resolved in index["notes"] else None


def emit(payload, as_json: bool, human_lines):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        for line in human_lines:
            print(line)


def cmd_index(root: Path, args) -> int:
    notes, assets = index_corpus(root)
    data = serialize(reduce_restricted(build_index(root, notes, assets)))
    path = root / INDEX_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(INDEX_RELPATH)
    return 0


def cmd_list(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    filters = list(args.tag)
    if args.type:
        filters.append(f"type/{args.type}")
    rows = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if args.dir and not rel.startswith(args.dir):
            continue
        tags = effective_tags(rec)
        if not all(tag_matches(t, tags) for t in filters):
            continue
        rows.append({"path": rel, "title": rec["title"], "updated": rec["updated"]})
    emit(rows, args.json, (r["path"] for r in rows))
    return 0


def keyword_hits(root: Path, index: dict, query: str, tag_filters: list[str]) -> list[dict]:
    """§9 search: case-insensitive substring hits over title, headings, and
    body. Shared by plain search, semantic degradation, and the §18.4 keyword
    component."""
    query = query.lower()
    hits: list[dict] = []
    for rel in sorted(index["notes"]):
        rec = index["notes"][rel]
        if tag_filters and not all(tag_matches(t, effective_tags(rec)) for t in tag_filters):
            continue
        if rec["title"] and query in rec["title"].lower():
            hits.append({"field": "title", "line": None, "path": rel, "snippet": rec["title"]})
        heading_lines = set()
        for h in rec["headings"]:
            heading_lines.add(h["line"])
            if query in h["text"].lower():
                hits.append(
                    {"field": "heading", "line": h["line"], "path": rel, "snippet": h["text"]}
                )
        try:
            text, _ = load_text(root, rel)
        except OSError:  # §3 read failure: skip, best-effort
            continue
        if text is None:
            continue
        for i, line in enumerate(text.split("\n"), start=1):
            if i in heading_lines:
                continue
            if query in line.lower():
                hits.append({"field": "body", "line": i, "path": rel, "snippet": line.strip()})
    return hits


def emit_keyword_hits(hits: list[dict], as_json: bool) -> None:
    emit(
        hits,
        as_json,
        (
            f"{h['path']}: title: {h['snippet']}"
            if h["line"] is None
            else f"{h['path']}:{h['line']}: {h['snippet']}"
            for h in hits
        ),
    )


def cmd_search(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    if args.semantic:
        return semantic_search(root, index, args)
    emit_keyword_hits(keyword_hits(root, index, args.query, args.tag), args.json)
    return 0


def cmd_links(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    rel = resolve_note_arg(index, args.note)
    if rel is None:
        print(f"error: note not found: {args.note}", file=sys.stderr)
        return 1
    rec = index["notes"][rel]
    unresolved = sorted(
        {l["target"] for l in rec["links"] if l["resolved"] is None and not l["placeholder"]}
    )
    payload = {
        "backlinks": rec["backlinks"],
        "legacyCount": sum(1 for link in rec["links"] if link["format"] == "wikilink"),
        "outgoing": rec["links"],
        "path": rel,
        "placeholderCount": sum(1 for link in rec["links"] if link["placeholder"]),
        "unresolved": unresolved,
    }
    lines = [f"note: {rel}", "outgoing:"]
    for l in rec["links"]:
        state = l["resolved"] or l["resolution"]["status"].upper()
        lines.append(f"  {l['raw']} -> {state}")
    lines.append("backlinks:")
    lines.extend(f"  {b}" for b in rec["backlinks"])
    if unresolved:
        lines.append("unresolved: " + ", ".join(unresolved))
    emit(payload, args.json, lines)
    return 0


def cmd_tags(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    counts: dict[str, dict[str, int]] = {}
    for rec in index["notes"].values():
        for tag in effective_tags(rec):
            namespace, _, value = tag.partition("/")
            if not value:
                namespace, value = "(none)", tag
            counts.setdefault(namespace, {})
            counts[namespace][value] = counts[namespace].get(value, 0) + 1
    lines = []
    for namespace in sorted(counts):
        lines.append(f"{namespace}/")
        for value in sorted(counts[namespace]):
            lines.append(f"  {value} {counts[namespace][value]}")
    emit(counts, args.json, lines)
    return 0


def cmd_show(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    rel = resolve_note_arg(index, args.note)
    if rel is None:
        print(f"error: note not found: {args.note}", file=sys.stderr)
        return 1
    rec = index["notes"][rel]
    lines = [
        f"path: {rel}",
        f"title: {rec['title']}",
        f"updated: {rec['updated']}",
        f"tags: {', '.join(sorted(effective_tags(rec))) or '(none)'}",
        f"headings: {len(rec['headings'])}  links: {len(rec['links'])}  backlinks: {len(rec['backlinks'])}",
        f"sizeBytes: {rec['sizeBytes']}",
    ]
    if rec["frontmatterErrors"]:
        lines.append("frontmatterErrors: " + ", ".join(rec["frontmatterErrors"]))
    emit(rec, args.json, lines)
    return 0


def cmd_recent(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    entries = list(index["notes"].items())
    entries.sort(key=lambda kv: kv[0])

    def mtime(rel: str) -> float:
        try:
            return (root / rel).stat().st_mtime
        except OSError:  # §3 read failure (e.g. broken symlink): sort last
            return 0.0

    entries.sort(key=lambda kv: mtime(kv[0]), reverse=True)
    entries.sort(key=lambda kv: kv[1]["updated"] or "", reverse=True)
    entries = entries[: args.n]
    rows = [
        {"path": rel, "title": rec["title"], "updated": rec["updated"]}
        for rel, rec in entries
    ]
    emit(rows, args.json, (f"{r['updated'] or '----------'}  {r['path']}" for r in rows))
    return 0


def cmd_curate(root: Path, args) -> int:
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    cur = compute_curation(root, index, today())
    if args.check_urls:
        cur["deadUrls"] = check_urls(root, sorted(index["notes"]))
    lines: list[str] = []
    sections = [
        ("expired", "expired", lambda r: f"{r['path']}  (expired {r['expires']})"),
        ("missingExpires", "missing expires:", lambda r: r),
        ("beyondCap", "expires beyond the one-year cap", lambda r: f"{r['path']}  (updated {r['updated']}, expires {r['expires']})"),
        ("oversized", "oversized (split candidates)", lambda r: f"{r['path']}  ({r['sizeBytes']} bytes, {r['lines']} lines)"),
        ("stale", "stale (days old x inbound links)", lambda r: f"{r['path']}  (updated {r['updated']}, {r['daysOld']}d, {r['backlinks']} backlinks, score {r['score']})"),
        ("orphans", "orphans (no inbound links)", lambda r: r),
        ("unreferencedAssets", "unreferenced assets", lambda r: r),
        ("deadUrls", "dead source urls", lambda r: f"{r['url']}  ({r['error']}; first seen in {r['path']})"),
    ]
    flagged = 0
    for key_name, label, fmt in sections:
        rows = cur.get(key_name)
        if rows is None:
            continue
        lines.append(f"{label}: {len(rows)}")
        for row in rows:
            lines.append(f"  {fmt(row)}")
        flagged += len(rows)
    lines.append(f"total flagged: {flagged}")
    emit(cur, args.json, lines)
    return 0


def cmd_context(root: Path, args) -> int:
    ctx = context_report(root)
    lines = []
    for row in ctx["docs"]:
        if row["sizeBytes"] is None:
            lines.append(f"{row['path']}  missing  (budget {row['budget']})")
        else:
            pct = 100 * row["sizeBytes"] // row["budget"]
            over = "  OVER BUDGET" if row["sizeBytes"] > row["budget"] else ""
            lines.append(
                f"{row['path']}  {row['sizeBytes']} / {row['budget']} bytes ({pct}%){over}"
            )
    tpct = 100 * ctx["totalBytes"] // ctx["totalBudget"]
    over = "  OVER BUDGET" if ctx["totalBytes"] > ctx["totalBudget"] else ""
    lines.append(f"total  {ctx['totalBytes']} / {ctx['totalBudget']} bytes ({tpct}%){over}")
    emit(ctx, args.json, lines)
    return 0


def cmd_config(root: Path, args) -> int:
    """§15: effective vault config — defaults merged, findings included."""
    config, findings = load_config(root)
    cfg_errors, cfg_warnings = check_config(root, config, findings)
    payload = {
        "context": vault_context(config),
        "errors": cfg_errors,
        "extensionTrust": extension_trust(config),
        "path": CONFIG_RELPATH,
        "present": (root / CONFIG_RELPATH).exists(),
        "raw": config,
        "reservedKeys": sorted(CONFIG_RESERVED_KEYS),
        "tasksCarryOver": tasks_carry_over(config),
        "templateVersion": template_version(config),
        "warnings": cfg_warnings,
        "writeExceptions": list(write_exception_prefixes(config)),
    }
    lines = [
        f"config: {CONFIG_RELPATH} ({'present' if payload['present'] else 'absent — defaults'})",
        "write exceptions (agent-writable prefixes):",
        *(f"  {p}" for p in payload["writeExceptions"]),
        f"extension trust: {payload['extensionTrust']}",
        f"context: {payload['context']}",
        f"tasks carry-over: {'on' if payload['tasksCarryOver'] else 'off'}",
        f"template version: {payload['templateVersion'] or '(unset)'}",
    ]
    for f in cfg_errors:
        lines.append(f"ERROR {f['rule']}: {f['message']}")
    for f in cfg_warnings:
        lines.append(f"WARN {f['rule']}: {f['message']}")
    emit(payload, args.json, lines)
    return 0


def cmd_report(root: Path, args) -> int:
    """§16: the five-section vault-health report, most-actionable-first."""
    since_d = None
    if args.since is not None:
        since_d = iso_date(args.since)
        if since_d is None:
            print(
                f"error: --since must be a real YYYY-MM-DD date, got {args.since!r}",
                file=sys.stderr,
            )
            return 1
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    config, _findings = load_config(root)
    thresholds = report_thresholds(config)
    taxonomy = load_taxonomy(root)
    rep = compute_report(index, today(), thresholds, taxonomy, since_d)

    lines: list[str] = [
        "vault health report "
        f"(stale-active > {thresholds['staleDays']}d, "
        f"inbox triage > {thresholds['inboxDays']}d)"
    ]
    if rep["since"]:
        lines.append(
            f"since {rep['since']}: tag drift and unresolved links scoped to "
            "notes updated on/after this date"
        )
    lines.append(f"stale-active: {len(rep['staleActive'])}")
    for row in rep["staleActive"]:
        lines.append(f"  {row['path']}  (updated {row['updated']}, {row['daysOld']}d old)")
    lines.append(f"orphans (no links in or out): {len(rep['orphans'])}")
    for rel in rep["orphans"]:
        lines.append(f"  {rel}")
    inbox = rep["inboxAging"]
    total_inbox = sum(len(rows) for rows in inbox["buckets"].values())
    lines.append(
        f"inbox aging: {total_inbox} notes, {len(inbox['triageDebt'])} past "
        f"the {thresholds['inboxDays']}d triage threshold"
    )
    for label in REPORT_BUCKET_LABELS:
        rows = inbox["buckets"][label]
        if not rows:
            continue
        lines.append(f"  {label}: {len(rows)}")
        for row in rows:
            age = "?" if row["ageDays"] is None else f"{row['ageDays']}d"
            lines.append(f"    {row['path']}  ({age}, {row['source']})")
    drift = rep["tagDrift"]
    if not drift["taxonomyReadable"]:
        lines.append("tag drift: conventions taxonomy unreadable — not computed (see validate)")
    else:
        lines.append(
            "tag drift: "
            f"{len(drift['unknown'])} unknown, {len(drift['singleUse'])} single-use, "
            f"{len(drift['nearDuplicates'])} near-duplicate pairs"
        )
        for row in drift["unknown"]:
            lines.append(f"  {row['tag']}  ({row['reason']}, {row['count']} notes)")
        for tag in drift["singleUse"]:
            lines.append(f"  {tag}  (single-use)")
        for row in drift["nearDuplicates"]:
            lines.append(
                f"  {row['namespace']}/: {row['values'][0]} ~ {row['values'][1]}"
                "  (near-duplicate)"
            )
    lines.append(f"unresolved links: {rep['unresolvedLinks']['count']}")
    for row in rep["unresolvedLinks"]["links"]:
        lines.append(f"  {row['path']}:{row['line']}  -> {row['target']}")
    emit(rep, args.json, lines)
    return 0


def cmd_tasks(root: Path, args) -> int:
    """§17.3: query checkbox tasks from the in-memory index."""
    due_limit: date | None = None
    if args.due is not None:
        due_limit = today() if args.due == "today" else iso_date(args.due)
        if due_limit is None:
            print(
                f"error: --due must be 'today' or a real YYYY-MM-DD date, "
                f"got {args.due!r}",
                file=sys.stderr,
            )
            return 1
    today_iso = today().isoformat()
    notes, assets = walk_corpus(root)
    index = build_index(root, notes, assets)
    rows: list[dict] = []
    # Normalize like every other path input (§2): NFC, forward slashes,
    # no leading ./ — a macOS NFD prefix or backslash must still match.
    project = (
        nfc(args.project.strip()).replace("\\", "/").removeprefix("./")
        if args.project
        else None
    )
    for rel in sorted(index["notes"]):
        if project and not rel.startswith(project):
            continue
        for t in index["notes"][rel]["tasks"]:
            if args.open and t["status"] != "open":
                continue
            if due_limit is not None and (
                t["due"] is None or t["due"] > due_limit.isoformat()
            ):
                continue
            if args.overdue and not (
                t["status"] == "open" and t["due"] is not None and t["due"] < today_iso
            ):
                continue
            rows.append({**t, "path": rel})
    rows.sort(key=lambda r: (r["due"] is None, r["due"] or "", r["path"], r["line"]))
    lines = []
    for r in rows:
        box = "[ ]" if r["status"] == "open" else "[x]"
        extras = ", ".join(
            part
            for part in (
                f"due {r['due']}" if r["due"] else None,
                r["priority"],
                "malformed: " + ", ".join(r["malformed"]) if r["malformed"] else None,
            )
            if part
        )
        lines.append(
            f"{r['path']}:{r['line']}  {box} {r['text']}"
            + (f"  ({extras})" if extras else "")
        )
    emit(rows, args.json, lines)
    return 0


class InstallError(RuntimeError):
    """Stable installer refusal safe to render at the CLI boundary."""


def _install_platform() -> tuple[str, str]:
    return ("windows", "brain.cmd") if os.name == "nt" else ("posix", "brain")


def _installer_source(root: Path, filename: str) -> Path:
    source = root / filename
    if source.is_symlink() or not source.is_file():
        raise InstallError("repository launcher is missing or unsafe")
    return source


def _outside_vault(root: Path, path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise InstallError(f"{label} must be an absolute path")
    if path.is_symlink() or path.parent.is_symlink():
        raise InstallError(f"{label} must not be a symlink")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return resolved
    raise InstallError(f"{label} must be outside the vault")


def _install_state_path(root: Path, args, environ: dict[str, str]) -> Path:
    supplied = getattr(args, "state_file", None)
    if supplied is not None:
        raw = str(supplied)
    elif INSTALL_MANIFEST_ENV in environ:
        raw = environ[INSTALL_MANIFEST_ENV]
        if not raw:
            raise InstallError(f"{INSTALL_MANIFEST_ENV} is set but empty")
    elif os.name == "nt":
        local = environ.get("LOCALAPPDATA")
        if not local:
            raise InstallError("LOCALAPPDATA is unavailable; pass --state-file")
        raw = str(Path(local) / "second-brain" / "brain-install.json")
    else:
        state_home = environ.get("XDG_STATE_HOME")
        if state_home:
            raw = str(Path(state_home) / "second-brain" / "brain-install.json")
        else:
            raw = str(Path.home() / ".local/state/second-brain/brain-install.json")
    if any(ch in raw for ch in "\0\r\n"):
        raise InstallError("state-file path contains forbidden control characters")
    return _outside_vault(root, Path(raw).expanduser(), "state file")


def _empty_install_manifest() -> dict:
    return {"artifacts": [], "schemaVersion": INSTALL_MANIFEST_SCHEMA_VERSION}


def _capture_external_parent(root: Path, path: Path, label: str) -> dict:
    """Snapshot a non-link directory chain outside the vault."""
    parent = path.parent
    try:
        parent.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise InstallError(f"{label} must be outside the vault")
    chain = [*reversed(parent.parents), parent]
    snapshots = []
    try:
        for component in chain:
            info = os.lstat(component)
            if _link_like_stat(info) or not stat.S_ISDIR(info.st_mode):
                raise InstallError(f"{label} parent chain is unsafe")
            snapshots.append(
                (str(component), info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
            )
    except OSError:
        raise InstallError(f"{label} parent is unavailable") from None
    return {
        "created": (),
        "label": label,
        "parent": parent,
        "snapshots": tuple(snapshots),
    }


def _assert_external_parent(guard: dict) -> None:
    try:
        for raw, device, inode, kind in guard["snapshots"]:
            info = os.lstat(raw)
            current = (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
            if _link_like_stat(info) or current != (device, inode, kind):
                raise InstallError(f"{guard['label']} parent changed after preflight")
    except OSError:
        raise InstallError(f"{guard['label']} parent changed after preflight") from None


def _open_external_parent(guard: dict) -> int | None:
    """Open and identity-check the guarded directory when openat is available."""
    _assert_external_parent(guard)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not (nofollow and directory and os.open in getattr(os, "supports_dir_fd", set())):
        return None
    descriptor = os.open(
        guard["parent"], os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0)
    )
    info = os.fstat(descriptor)
    _raw, device, inode, kind = guard["snapshots"][-1]
    if (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)) != (
        device,
        inode,
        kind,
    ):
        os.close(descriptor)
        raise InstallError(f"{guard['label']} parent changed after preflight")
    return descriptor


def _win32_api():
    if os.name != "nt":
        raise InstallError("Windows filesystem primitives are unavailable")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.GetFileInformationByHandleEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    kernel32.GetFileSizeEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel32.SetFilePointerEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_longlong,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    kernel32.SetEndOfFile.argtypes = [ctypes.c_void_p]
    kernel32.ReadFile.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    kernel32.WriteFile.argtypes = kernel32.ReadFile.argtypes
    kernel32.FlushFileBuffers.argtypes = [ctypes.c_void_p]
    kernel32.SetFileInformationByHandle.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    return kernel32


def _win32_open_path(
    path: Path,
    access: int,
    creation: int,
    *,
    directory: bool,
    share_write: bool = True,
) -> int:
    kernel32 = _win32_api()
    flags = 0x00200000  # FILE_FLAG_OPEN_REPARSE_POINT
    if directory:
        flags |= 0x02000000  # FILE_FLAG_BACKUP_SEMANTICS
    share_mode = 0x1 | (0x2 if share_write else 0)
    handle = kernel32.CreateFileW(
        str(path), access, share_mode, None, creation, flags, None
    )
    if handle == ctypes.c_void_p(-1).value:
        raise InstallError("external path could not be opened safely")
    attributes = (ctypes.c_uint32 * 2)()
    if not kernel32.GetFileInformationByHandleEx(
        handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)
    ):
        kernel32.CloseHandle(handle)
        raise InstallError("external path attributes could not be verified")
    is_directory = bool(attributes[0] & 0x10)
    if attributes[0] & 0x400 or is_directory != directory:
        kernel32.CloseHandle(handle)
        raise InstallError("external path is a reparse point or has the wrong type")
    return int(handle)


def _win32_open_guard_chain(guard: dict) -> list[int]:
    _assert_external_parent(guard)
    handles = []
    try:
        for raw, _device, _inode, _kind in guard["snapshots"]:
            handles.append(_win32_open_path(Path(raw), 0, 3, directory=True))
        _assert_external_parent(guard)
        return handles
    except BaseException:
        _win32_close_handles(handles)
        raise


def _win32_close_handles(handles: list[int]) -> None:
    if os.name != "nt":
        return
    kernel32 = _win32_api()
    while handles:
        kernel32.CloseHandle(handles.pop())


def _win32_read_handle(handle: int, max_bytes: int) -> bytes:
    kernel32 = _win32_api()
    size = ctypes.c_longlong()
    if not kernel32.GetFileSizeEx(handle, ctypes.byref(size)) or size.value > max_bytes:
        raise InstallError("external artifact exceeds its read limit")
    if not kernel32.SetFilePointerEx(handle, 0, None, 0):
        raise InstallError("external artifact could not be read safely")
    output = bytearray()
    while len(output) < size.value:
        count = min(64 * 1024, size.value - len(output))
        buffer = ctypes.create_string_buffer(count)
        read = ctypes.c_uint32()
        if not kernel32.ReadFile(handle, buffer, count, ctypes.byref(read), None):
            raise InstallError("external artifact could not be read safely")
        if not read.value:
            break
        output.extend(buffer.raw[: read.value])
    if len(output) != size.value:
        raise InstallError("external artifact changed during read")
    return bytes(output)


def _win32_write_handle(handle: int, data: bytes) -> None:
    kernel32 = _win32_api()
    if not kernel32.SetFilePointerEx(handle, 0, None, 0) or not kernel32.SetEndOfFile(handle):
        raise InstallError("external artifact could not be updated safely")
    offset = 0
    while offset < len(data):
        chunk = data[offset : offset + 64 * 1024]
        buffer = ctypes.create_string_buffer(chunk)
        written = ctypes.c_uint32()
        if not kernel32.WriteFile(
            handle, buffer, len(chunk), ctypes.byref(written), None
        ) or written.value != len(chunk):
            raise InstallError("external artifact could not be updated safely")
        offset += written.value
    if not kernel32.FlushFileBuffers(handle):
        raise InstallError("external artifact could not be flushed safely")
    if _win32_read_handle(handle, max(1024 * 1024, len(data))) != data:
        raise InstallError("external artifact changed during bound write")


def _win32_mark_delete(handle: int) -> None:
    kernel32 = _win32_api()
    disposition = ctypes.c_ubyte(1)
    if not kernel32.SetFileInformationByHandle(
        handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)
    ):
        raise InstallError("external artifact could not be removed safely")


def _win32_ensure_external_parent(root: Path, path: Path, label: str) -> dict:
    parent = path.parent
    missing = []
    cursor = parent
    while not cursor.exists() and not cursor.is_symlink():
        missing.append(cursor)
        cursor = cursor.parent
    base_guard = _capture_external_parent(root, cursor / ".brain-anchor", label)
    handles = _win32_open_guard_chain(base_guard)
    created = []
    try:
        for directory_path in reversed(missing):
            os.mkdir(directory_path, 0o700)
            handles.append(
                _win32_open_path(directory_path, 0, 3, directory=True)
            )
            created.append(str(directory_path))
        guard = _capture_external_parent(root, path, label)
        guard["created_windows"] = tuple(created)
        guard["win_chain_handles"] = handles
        return guard
    except BaseException:
        cleanup_failed = False
        for directory_path in reversed(created):
            _win32_api().CloseHandle(handles.pop())
            try:
                os.rmdir(directory_path)
            except OSError:
                cleanup_failed = True
        _win32_close_handles(handles)
        if cleanup_failed:
            raise InstallError(
                "created state directories could not be rolled back safely"
            ) from None
        raise


def _ensure_external_parent(root: Path, path: Path, label: str) -> dict:
    """Create a missing private parent without traversing a link on POSIX."""
    parent = path.parent
    if parent.exists() or parent.is_symlink():
        return _capture_external_parent(root, path, label)
    if os.name == "nt":
        return _win32_ensure_external_parent(root, path, label)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    created: list[tuple[str, int, tuple[int, int, int]]] = []
    if nofollow and directory and os.open in getattr(os, "supports_dir_fd", set()):
        parts = parent.parts
        current_path = Path(parts[0])
        descriptor = os.open(
            current_path,
            os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0),
        )
        try:
            for part in parts[1:]:
                try:
                    child = os.open(
                        part,
                        os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=descriptor,
                    )
                except FileNotFoundError:
                    try:
                        os.mkdir(part, 0o700, dir_fd=descriptor)
                        child_info = os.stat(
                            part, dir_fd=descriptor, follow_symlinks=False
                        )
                        created.append(
                            (
                                str(current_path / part),
                                os.dup(descriptor),
                                (
                                    child_info.st_dev,
                                    child_info.st_ino,
                                    stat.S_IFMT(child_info.st_mode),
                                ),
                            )
                        )
                    except FileExistsError:
                        pass
                    child = os.open(
                        part,
                        os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=descriptor,
                    )
                os.close(descriptor)
                descriptor = child
                current_path = current_path / part
        except OSError:
            _cleanup_created_external_parents(created)
            raise InstallError(f"{label} parent could not be created safely") from None
        finally:
            os.close(descriptor)
    else:
        raise InstallError("safe parent-bound directory creation is unavailable")
    try:
        guard = _capture_external_parent(root, path, label)
    except BaseException:
        _cleanup_created_external_parents(created)
        raise
    guard["created"] = tuple(created)
    return guard


def _cleanup_created_external_parents(
    created: tuple[tuple[str, int, tuple[int, int, int]], ...]
    | list[tuple[str, int, tuple[int, int, int]]],
) -> None:
    """Remove exactly empty directories created by this transaction."""
    failure = False
    for raw, parent_descriptor, expected in reversed(created):
        try:
            name = Path(raw).name
            info = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            observed = (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
            if observed != expected or not stat.S_ISDIR(info.st_mode):
                failure = True
                continue
            os.rmdir(name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            pass
        except OSError:
            failure = True
        finally:
            os.close(parent_descriptor)
    if failure:
        raise InstallError("created state directories could not be rolled back safely")


def _release_created_external_parents(guard: dict | None) -> None:
    if guard is None:
        return
    for _raw, parent_descriptor, _expected in guard.get("created", ()):
        os.close(parent_descriptor)
    guard["created"] = ()
    _win32_close_handles(guard.get("win_chain_handles", []))
    guard["win_chain_handles"] = []


def _cleanup_external_parent_guard(guard: dict) -> None:
    _cleanup_created_external_parents(guard.get("created", ()))
    handles = guard.get("win_chain_handles", [])
    failure = False
    for raw in reversed(guard.get("created_windows", ())):
        if handles:
            _win32_api().CloseHandle(handles.pop())
        try:
            os.rmdir(raw)
        except FileNotFoundError:
            pass
        except OSError:
            failure = True
    _win32_close_handles(handles)
    guard["win_chain_handles"] = []
    if failure:
        raise InstallError("created state directories could not be rolled back safely")


def _external_lstat(path: Path, guard: dict) -> os.stat_result | None:
    descriptor = _open_external_parent(guard)
    if descriptor is not None:
        try:
            try:
                return os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                return None
        finally:
            os.close(descriptor)
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        _assert_external_parent(guard)
        return None
    _assert_external_parent(guard)
    return info


def _read_external_regular(
    path: Path, guard: dict, *, max_bytes: int
) -> tuple[bytes, int] | None:
    """Read an external regular file through its bound parent directory."""
    descriptor = _open_external_parent(guard)
    if descriptor is not None:
        opened = None
        try:
            try:
                opened = os.open(
                    path.name,
                    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                return None
            info = os.fstat(opened)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_size > max_bytes
                or _link_like_stat(info)
            ):
                raise InstallError("external artifact is not a safe regular file")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(opened, 64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise InstallError("external artifact exceeds its read limit")
                chunks.append(chunk)
            return b"".join(chunks), stat.S_IMODE(info.st_mode)
        except OSError:
            raise InstallError("external artifact changed during read") from None
        finally:
            if opened is not None:
                os.close(opened)
            os.close(descriptor)

    # Portable fallback: refuse redirects, compare lstat to the opened file,
    # then recheck both file and parent identities after reading.
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        _assert_external_parent(guard)
        return None
    if (
        _link_like_stat(before)
        or not stat.S_ISREG(before.st_mode)
        or before.st_size > max_bytes
    ):
        raise InstallError("external artifact is not a safe regular file")
    opened = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        info = os.fstat(opened)
        expected = (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode))
        actual = (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
        if actual != expected:
            raise InstallError("external artifact changed during read")
        chunks = []
        total = 0
        while True:
            chunk = os.read(opened, 64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise InstallError("external artifact exceeds its read limit")
            chunks.append(chunk)
    finally:
        os.close(opened)
    after = os.lstat(path)
    _assert_external_parent(guard)
    if _link_like_stat(after) or (
        after.st_dev,
        after.st_ino,
        stat.S_IFMT(after.st_mode),
    ) != expected:
        raise InstallError("external artifact changed during read")
    return b"".join(chunks), stat.S_IMODE(info.st_mode)


def _external_digest(path: Path, guard: dict) -> str | None:
    result = _read_external_regular(path, guard, max_bytes=1024 * 1024)
    return hashlib.sha256(result[0]).hexdigest() if result is not None else None


def _load_install_manifest(path: Path, guard: dict | None) -> tuple[dict, bool, bytes | None]:
    if guard is None:
        if path.parent.exists() or path.parent.is_symlink():
            raise InstallError("install manifest parent changed during preflight")
        return _empty_install_manifest(), False, None
    try:
        result = _read_external_regular(path, guard, max_bytes=64 * 1024)
        if result is None:
            return _empty_install_manifest(), False, None
        raw, mode = result
        if os.name != "nt" and mode & 0o077:
            raise InstallError("install manifest permissions are not private")
        data = json.loads(raw.decode("utf-8"))
    except InstallError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise InstallError("install manifest is unreadable or invalid") from None
    if not isinstance(data, dict) or set(data) != {"artifacts", "schemaVersion"}:
        raise InstallError("install manifest has an unsupported shape")
    if data.get("schemaVersion") != INSTALL_MANIFEST_SCHEMA_VERSION:
        raise InstallError("install manifest schema version is unsupported")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        raise InstallError("install manifest artifacts must be a list")
    seen_platforms: set[str] = set()
    for row in artifacts:
        if not isinstance(row, dict) or set(row) != {
            "installedDigest",
            "platform",
            "target",
        }:
            raise InstallError("install manifest contains an invalid artifact")
        if (
            row.get("platform") not in {"posix", "windows"}
            or row["platform"] in seen_platforms
            or not isinstance(row.get("target"), str)
            or not Path(row["target"]).is_absolute()
            or any(ch in row["target"] for ch in "\0\r\n")
            or not isinstance(row.get("installedDigest"), str)
            or not ENVIRONMENT_DIGEST_RE.fullmatch(row["installedDigest"])
        ):
            raise InstallError("install manifest contains an invalid artifact")
        seen_platforms.add(row["platform"])
    return data, True, raw


def _path_install_directory(
    root: Path, environ: dict[str, str], explicit: Path | None
) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        raw_candidates = [str(explicit)]
    else:
        raw_candidates = environ.get("PATH", "").split(os.pathsep)
    seen: set[str] = set()
    for raw in raw_candidates:
        if not raw or any(ch in raw for ch in "\0\r\n"):
            continue
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute() or candidate.is_symlink():
            continue
        resolved = candidate.resolve(strict=False)
        key = os.path.normcase(str(resolved))
        if key in seen:
            continue
        seen.add(key)
        try:
            info = resolved.stat()
            resolved.relative_to(root.resolve())
            inside = True
        except ValueError:
            inside = False
        except OSError:
            continue
        if inside or not stat.S_ISDIR(info.st_mode):
            continue
        if os.name != "nt" and info.st_mode & 0o022:
            continue
        if info.st_mode & 0o222 and os.access(resolved, os.W_OK | os.X_OK):
            candidates.append(resolved)
    if not candidates:
        if explicit is not None:
            raise InstallError("target directory is not an existing writable PATH directory")
        raise InstallError(
            "no existing writable PATH directory found; pass --target after choosing one"
        )
    return candidates[0]


def _rename_external_at(
    descriptor: int, source: str, target: str, *, exchange: bool = False
) -> None:
    """Atomic POSIX no-replace rename or exchange, never a clobbering rename."""
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)
    if sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        operation = libc.renameatx_np
        operation.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        operation.restype = ctypes.c_int
        flags = 0x00000002 if exchange else 0x00000004
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        operation = libc.renameat2
        operation.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        operation.restype = ctypes.c_int
        flags = 0x2 if exchange else 0x1
    else:
        raise InstallError("safe final-component mutation is unavailable")
    if operation(descriptor, source_bytes, descriptor, target_bytes, flags) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _external_name_digest(
    descriptor: int, name: str, *, max_bytes: int
) -> str:
    opened = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
        dir_fd=descriptor,
    )
    try:
        info = os.fstat(opened)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise InstallError("external artifact is not a safe regular file")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(opened, 64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise InstallError("external artifact exceeds its read limit")
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(opened)


def _atomic_external_write(
    path: Path,
    data: bytes,
    mode: int,
    guard: dict,
    expected_digest: object | str,
) -> None:
    if os.name == "nt":
        parent_handles = _win32_open_guard_chain(guard)
        handle = None
        created = expected_digest is _EXTERNAL_ABSENT
        prior = None
        try:
            if not created and not isinstance(expected_digest, str):
                raise InstallError("invalid external mutation expectation")
            handle = _win32_open_path(
                path,
                0x80000000 | 0x40000000 | 0x00010000,
                1 if created else 3,
                directory=False,
                share_write=False,
            )
            if not created:
                prior = _win32_read_handle(handle, 1024 * 1024)
                if hashlib.sha256(prior).hexdigest() != expected_digest:
                    raise InstallError(
                        "external artifact changed before bound replacement"
                    )
            _win32_write_handle(handle, data)
        except BaseException:
            if handle is not None:
                try:
                    if created:
                        _win32_mark_delete(handle)
                    elif prior is not None:
                        _win32_write_handle(handle, prior)
                except InstallError:
                    raise InstallError(
                        "bound replacement rollback could not restore the target"
                    ) from None
            raise
        finally:
            if handle is not None:
                _win32_api().CloseHandle(handle)
            _win32_close_handles(parent_handles)
        return
    descriptor = _open_external_parent(guard)
    if descriptor is not None:
        temporary = None
        file_descriptor = None
        exchanged = False
        try:
            for _attempt in range(20):
                candidate = ".brain-install-" + secrets.token_hex(12)
                try:
                    file_descriptor = os.open(
                        candidate,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                        0o600,
                        dir_fd=descriptor,
                    )
                    temporary = candidate
                    break
                except FileExistsError:
                    continue
            if file_descriptor is None or temporary is None:
                raise OSError("could not allocate temporary artifact")
            with os.fdopen(file_descriptor, "wb") as handle:
                file_descriptor = None
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
                os.fchmod(handle.fileno(), mode)
            if expected_digest is _EXTERNAL_ABSENT:
                # Hard-link publication is an atomic create-if-absent CAS.
                os.link(
                    temporary,
                    path.name,
                    src_dir_fd=descriptor,
                    dst_dir_fd=descriptor,
                    follow_symlinks=False,
                )
                os.unlink(temporary, dir_fd=descriptor)
                temporary = None
            elif isinstance(expected_digest, str):
                _rename_external_at(
                    descriptor, temporary, path.name, exchange=True
                )
                exchanged = True
                observed = _external_name_digest(
                    descriptor, temporary, max_bytes=1024 * 1024
                )
                if observed != expected_digest:
                    _rename_external_at(
                        descriptor, temporary, path.name, exchange=True
                    )
                    exchanged = False
                    raise InstallError(
                        "external artifact changed before atomic replacement"
                    )
                os.unlink(temporary, dir_fd=descriptor)
                temporary = None
                exchanged = False
            else:
                raise InstallError("invalid external mutation expectation")
        except BaseException:
            if exchanged and temporary is not None:
                try:
                    _rename_external_at(
                        descriptor, temporary, path.name, exchange=True
                    )
                    exchanged = False
                except (OSError, InstallError):
                    # The prior file remains at the private quarantine name;
                    # never unlink an object whose identity is now uncertain.
                    temporary = None
                    raise InstallError(
                        "atomic replacement rollback could not restore the target"
                    ) from None
            raise
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)
            if temporary is not None:
                try:
                    os.unlink(temporary, dir_fd=descriptor)
                except FileNotFoundError:
                    pass
            os.close(descriptor)
        return
    raise InstallError("safe parent-bound mutation is unavailable")


def _remove_external(
    path: Path,
    guard: dict,
    *,
    expected_digest: str,
    missing_ok: bool = False,
) -> None:
    if os.name == "nt":
        parent_handles = _win32_open_guard_chain(guard)
        handle = None
        try:
            try:
                handle = _win32_open_path(
                    path,
                    0x80000000 | 0x00010000,
                    3,
                    directory=False,
                    share_write=False,
                )
            except InstallError:
                if missing_ok and _external_lstat(path, guard) is None:
                    return
                raise
            observed = hashlib.sha256(
                _win32_read_handle(handle, 1024 * 1024)
            ).hexdigest()
            if observed != expected_digest:
                raise InstallError("external artifact changed before bound removal")
            _win32_mark_delete(handle)
        finally:
            if handle is not None:
                _win32_api().CloseHandle(handle)
            _win32_close_handles(parent_handles)
        return
    descriptor = _open_external_parent(guard)
    if descriptor is not None:
        quarantine = ".brain-remove-" + secrets.token_hex(12)
        moved = False
        try:
            try:
                _rename_external_at(descriptor, path.name, quarantine)
            except FileNotFoundError:
                if not missing_ok:
                    raise
                return
            moved = True
            observed = _external_name_digest(
                descriptor, quarantine, max_bytes=1024 * 1024
            )
            if observed != expected_digest:
                _rename_external_at(descriptor, quarantine, path.name)
                moved = False
                raise InstallError(
                    "external artifact changed before atomic removal"
                )
            os.unlink(quarantine, dir_fd=descriptor)
            moved = False
        except BaseException:
            if moved:
                try:
                    _rename_external_at(descriptor, quarantine, path.name)
                    moved = False
                except (OSError, InstallError):
                    # Preserve the quarantined object rather than deleting or
                    # overwriting an unrecognized final component.
                    raise InstallError(
                        "atomic removal rollback could not restore the target"
                    ) from None
            raise
        finally:
            os.close(descriptor)
        return
    raise InstallError("safe parent-bound removal is unavailable")


def _manifest_bytes(manifest: dict) -> bytes:
    return (
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")


def _target_state(
    target: Path, source_digest: str, artifact: dict | None, guard: dict
) -> str:
    info = _external_lstat(target, guard)
    if info is None:
        return "absent"
    if _link_like_stat(info) or not stat.S_ISREG(info.st_mode):
        return "foreign"
    digest = _external_digest(target, guard)
    if digest is None:
        return "foreign"
    if digest == source_digest:
        return "current"
    if artifact is not None and digest == artifact["installedDigest"]:
        return "managed-upgrade"
    return "foreign"


def _manifest_is_unchanged(
    path: Path, present: bool, snapshot: bytes | None, guard: dict
) -> bool:
    if not present:
        return _external_lstat(path, guard) is None
    try:
        result = _read_external_regular(path, guard, max_bytes=64 * 1024)
        return result is not None and result[0] == snapshot
    except (OSError, InstallError):
        return False


_EXTERNAL_ABSENT = object()


def _restore_external(
    path: Path,
    prior: tuple[bytes, int] | None,
    guard: dict,
    expected_current: object | str,
) -> None:
    if expected_current is _EXTERNAL_ABSENT:
        if _external_lstat(path, guard) is not None:
            raise InstallError("rollback refused because target is no longer absent")
    elif _external_digest(path, guard) != expected_current:
        raise InstallError("rollback refused because target changed")
    if prior is None:
        _remove_external(
            path,
            guard,
            expected_digest=expected_current,
            missing_ok=True,
        )
        return
    _atomic_external_write(
        path, prior[0], prior[1], guard, expected_current
    )


def cmd_install(root: Path, args) -> int:
    """§21: preview/apply/doctor/uninstall the resolver outside the vault."""
    environ = os.environ
    created_state_guard = None
    try:
        platform_name, filename = _install_platform()
        source = _installer_source(root, filename)
        source_bytes = source.read_bytes()
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        source_mode = stat.S_IMODE(source.stat().st_mode)
        state_file = _install_state_path(root, args, environ)
        state_guard = (
            _capture_external_parent(root, state_file, "state file")
            if state_file.parent.exists() or state_file.parent.is_symlink()
            else None
        )
        manifest, manifest_present, manifest_snapshot = _load_install_manifest(
            state_file, state_guard
        )
        artifact = next(
            (row for row in manifest["artifacts"] if row["platform"] == platform_name),
            None,
        )
        explicit_target = getattr(args, "target", None)
        if artifact is not None:
            if Path(artifact["target"]).name != filename:
                raise InstallError("managed target has an invalid launcher filename")
            recorded_target = _outside_vault(
                root, Path(artifact["target"]), "recorded target"
            )
            if explicit_target is not None:
                requested_dir = _path_install_directory(root, environ, explicit_target)
                if requested_dir / filename != recorded_target:
                    raise InstallError(
                        "--target differs from the managed target; uninstall first"
                    )
            target = recorded_target
        else:
            target_dir = _path_install_directory(root, environ, explicit_target)
            target = _outside_vault(root, target_dir / filename, "target")

        target_guard = _capture_external_parent(root, target, "target")
        state = _target_state(target, source_digest, artifact, target_guard)
        on_path = any(
            raw
            and Path(raw).is_absolute()
            and Path(raw).resolve(strict=False) == target.parent
            for raw in environ.get("PATH", "").split(os.pathsep)
        )
        mode = (
            "doctor"
            if args.doctor
            else "uninstall"
            if args.uninstall
            else "install"
        )
        payload = {
            "actions": [],
            "manifestPresent": manifest_present,
            "mode": mode,
            "onPath": on_path,
            "stateFile": str(state_file),
            "status": state,
            "target": str(target),
            "writesPerformed": False,
        }

        if args.doctor:
            if args.apply:
                raise InstallError("--doctor cannot be combined with --apply")
            payload["actions"] = ["none (diagnostic only)"]
            healthy = artifact is not None and state == "current" and on_path
            lines = [
                f"brain install doctor: {'healthy' if healthy else 'attention required'}",
                f"target: {target}",
                f"manifest: {state_file}",
                f"status: {state}",
                f"target directory on PATH: {'yes' if on_path else 'no'}",
            ]
            emit(payload, args.json, lines)
            return 0 if healthy else 1

        if args.uninstall:
            if artifact is None:
                raise InstallError("no managed launcher is recorded for this platform")
            if state not in {"current", "managed-upgrade", "absent"}:
                raise InstallError("installed launcher has drifted; refusing to remove it")
            payload["actions"] = [
                f"remove {target}" if state != "absent" else "target already absent",
                f"remove this platform record from {state_file}",
            ]
            if not args.apply:
                emit(
                    payload,
                    args.json,
                    ["brain uninstall preview:", *(f"  {a}" for a in payload["actions"]), "writes performed: no"],
                )
                return 0
            if state_guard is None:
                state_guard = _ensure_external_parent(root, state_file, "state file")
                created_state_guard = state_guard
            else:
                _assert_external_parent(state_guard)
            if not _manifest_is_unchanged(
                state_file, manifest_present, manifest_snapshot, state_guard
            ):
                raise InstallError("install manifest changed after preview; retry")
            prior = None
            if state != "absent":
                if _target_state(target, source_digest, artifact, target_guard) != state:
                    raise InstallError("installed launcher changed after preview; retry")
                current = _read_external_regular(
                    target, target_guard, max_bytes=1024 * 1024
                )
                if current is None:
                    raise InstallError("installed launcher changed after preview; retry")
                prior = current
            remaining = [
                row for row in manifest["artifacts"] if row["platform"] != platform_name
            ]
            updated = {
                "artifacts": remaining,
                "schemaVersion": INSTALL_MANIFEST_SCHEMA_VERSION,
            }
            try:
                if prior is not None:
                    _remove_external(
                        target,
                        target_guard,
                        expected_digest=hashlib.sha256(prior[0]).hexdigest(),
                    )
                if not _manifest_is_unchanged(
                    state_file, manifest_present, manifest_snapshot, state_guard
                ):
                    raise OSError("manifest changed")
                if remaining:
                    _atomic_external_write(
                        state_file,
                        _manifest_bytes(updated),
                        0o600,
                        state_guard,
                        hashlib.sha256(manifest_snapshot or b"").hexdigest(),
                    )
                else:
                    _remove_external(
                        state_file,
                        state_guard,
                        expected_digest=hashlib.sha256(
                            manifest_snapshot or b""
                        ).hexdigest(),
                    )
            except (OSError, InstallError, KeyboardInterrupt, SystemExit) as exc:
                manifest_committed = False
                try:
                    if remaining:
                        stored = _read_external_regular(
                            state_file, state_guard, max_bytes=64 * 1024
                        )
                        manifest_committed = (
                            stored is not None
                            and stored[0] == _manifest_bytes(updated)
                        )
                    else:
                        manifest_committed = (
                            _external_lstat(state_file, state_guard) is None
                        )
                except (OSError, InstallError):
                    pass
                if prior is not None:
                    if not manifest_committed:
                        current = _read_external_regular(
                            target, target_guard, max_bytes=1024 * 1024
                        )
                        if current is None:
                            _restore_external(
                                target, prior, target_guard, _EXTERNAL_ABSENT
                            )
                        elif current[0] != prior[0]:
                            raise InstallError(
                                "uninstall rollback refused because target changed"
                            ) from None
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    if created_state_guard is not None:
                        if manifest_committed:
                            _release_created_external_parents(created_state_guard)
                        else:
                            _cleanup_external_parent_guard(created_state_guard)
                        created_state_guard = None
                    raise
                raise InstallError(
                    "uninstall could not update its manifest; target restored"
                ) from None
            payload["writesPerformed"] = True
            if created_state_guard is not None:
                _release_created_external_parents(created_state_guard)
                created_state_guard = None
            emit(payload, args.json, [f"removed managed launcher: {target}"])
            return 0

        if state == "foreign":
            raise InstallError("target exists but is not a recognized managed launcher")
        payload["actions"] = [
            f"install resolver at {target}",
            f"record reversible ownership in {state_file}",
        ]
        if not args.apply:
            emit(
                payload,
                args.json,
                ["brain install preview:", *(f"  {a}" for a in payload["actions"]), "writes performed: no"],
            )
            return 0

        prior = None
        changed_target = state != "current"
        if state_guard is None:
            state_guard = _ensure_external_parent(root, state_file, "state file")
            created_state_guard = state_guard
        else:
            _assert_external_parent(state_guard)
        if not _manifest_is_unchanged(
            state_file, manifest_present, manifest_snapshot, state_guard
        ):
            raise InstallError("install manifest changed after preview; retry")
        if changed_target:
            if _target_state(target, source_digest, artifact, target_guard) != state:
                raise InstallError("target changed after preview; retry")
            if state == "managed-upgrade":
                prior = _read_external_regular(
                    target, target_guard, max_bytes=1024 * 1024
                )
                if prior is None:
                    raise InstallError("target changed after preview; retry")
        updated_artifact = {
            "installedDigest": source_digest,
            "platform": platform_name,
            "target": str(target),
        }
        updated_artifacts = [
            row for row in manifest["artifacts"] if row["platform"] != platform_name
        ] + [updated_artifact]
        updated_artifacts.sort(key=lambda row: row["platform"])
        updated = {
            "artifacts": updated_artifacts,
            "schemaVersion": INSTALL_MANIFEST_SCHEMA_VERSION,
        }
        try:
            if changed_target:
                _atomic_external_write(
                    target,
                    source_bytes,
                    source_mode,
                    target_guard,
                    _EXTERNAL_ABSENT
                    if state == "absent"
                    else artifact["installedDigest"],
                )
            if not _manifest_is_unchanged(
                state_file, manifest_present, manifest_snapshot, state_guard
            ):
                raise OSError("manifest changed")
            _atomic_external_write(
                state_file,
                _manifest_bytes(updated),
                0o600,
                state_guard,
                _EXTERNAL_ABSENT
                if not manifest_present
                else hashlib.sha256(manifest_snapshot or b"").hexdigest(),
            )
        except (OSError, InstallError, KeyboardInterrupt, SystemExit) as exc:
            manifest_committed = False
            try:
                stored = _read_external_regular(
                    state_file, state_guard, max_bytes=64 * 1024
                )
                manifest_committed = (
                    stored is not None and stored[0] == _manifest_bytes(updated)
                )
            except (OSError, InstallError):
                pass
            if changed_target and not manifest_committed:
                current = _read_external_regular(
                    target, target_guard, max_bytes=1024 * 1024
                )
                if current is not None and hashlib.sha256(current[0]).hexdigest() == source_digest:
                    _restore_external(
                        target, prior, target_guard, source_digest
                    )
                elif prior is None and current is None:
                    pass
                elif prior is not None and current is not None and current[0] == prior[0]:
                    pass
                else:
                    raise InstallError(
                        "install rollback refused because target changed"
                    ) from None
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                if created_state_guard is not None:
                    if manifest_committed:
                        _release_created_external_parents(created_state_guard)
                    else:
                        _cleanup_external_parent_guard(created_state_guard)
                    created_state_guard = None
                raise
            raise InstallError(
                "install could not write its manifest; target restored"
            ) from None
        payload["status"] = "current"
        payload["writesPerformed"] = True
        if created_state_guard is not None:
            _release_created_external_parents(created_state_guard)
            created_state_guard = None
        emit(payload, args.json, [f"installed managed launcher: {target}"])
        return 0
    except (InstallError, OSError) as exc:
        if created_state_guard is not None:
            try:
                _cleanup_external_parent_guard(created_state_guard)
            except InstallError as cleanup_exc:
                exc = cleanup_exc
            created_state_guard = None
        message = str(exc) if isinstance(exc, InstallError) else "external filesystem operation failed"
        print(f"error: brain install refused ({message})", file=sys.stderr)
        return 1


def _migration_identity(info: os.stat_result) -> tuple[int, int, int]:
    return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))


def _migration_source_files(source_dir: Path) -> list[str]:
    """List regular files while binding every traversed source directory."""
    try:
        initial = os.lstat(source_dir)
    except FileNotFoundError:
        raise EnvironmentSelectionError("migration-source-not-found") from None
    except OSError:
        raise EnvironmentSelectionError("unsafe-migration-path") from None
    if _link_like_stat(initial) or not stat.S_ISDIR(initial.st_mode):
        raise EnvironmentSelectionError("unsafe-migration-path")
    initial_identity = _migration_identity(initial)
    rows: list[str] = []
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)

    if nofollow and directory and os.open in getattr(os, "supports_dir_fd", set()):
        descriptors: list[int] = []

        def walk_descriptor(parent: int, prefix: tuple[str, ...]) -> None:
            try:
                with os.scandir(parent) as iterator:
                    entries = sorted(iterator, key=lambda entry: entry.name)
            except OSError:
                raise EnvironmentSelectionError("unsafe-migration-path") from None
            for entry in entries:
                name = entry.name
                try:
                    if entry.is_symlink():
                        raise EnvironmentSelectionError("unsafe-migration-path")
                    if entry.is_dir(follow_symlinks=False):
                        child = os.open(
                            name,
                            os.O_RDONLY
                            | directory
                            | nofollow
                            | getattr(os, "O_CLOEXEC", 0),
                            dir_fd=parent,
                        )
                        descriptors.append(child)
                        if not stat.S_ISDIR(os.fstat(child).st_mode):
                            raise EnvironmentSelectionError("unsafe-migration-path")
                        walk_descriptor(child, (*prefix, name))
                        descriptors.pop()
                        os.close(child)
                        continue
                    child = os.open(
                        name,
                        os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=parent,
                    )
                    try:
                        if not stat.S_ISREG(os.fstat(child).st_mode):
                            raise EnvironmentSelectionError("unsafe-migration-path")
                    finally:
                        os.close(child)
                    rows.append("/".join((*prefix, name)))
                except EnvironmentSelectionError:
                    raise
                except OSError:
                    raise EnvironmentSelectionError("unsafe-migration-path") from None

        try:
            source_fd = os.open(
                source_dir,
                os.O_RDONLY
                | directory
                | nofollow
                | getattr(os, "O_CLOEXEC", 0),
            )
            descriptors.append(source_fd)
            if _migration_identity(os.fstat(source_fd)) != initial_identity:
                raise EnvironmentSelectionError("unsafe-migration-path")
            walk_descriptor(source_fd, ())
        except EnvironmentSelectionError:
            raise
        except OSError:
            raise EnvironmentSelectionError("unsafe-migration-path") from None
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
    else:
        # Portable fallback: compare each entry's identity at discovery, on
        # entry, and again after traversal. Rows stay private until all checks
        # pass, so a race yields only a stable refusal code.
        snapshots: list[tuple[Path, tuple[int, int, int]]] = []

        def walk_path(
            directory_path: Path,
            prefix: tuple[str, ...],
            expected: tuple[int, int, int],
        ) -> None:
            try:
                before = os.lstat(directory_path)
                if (
                    _link_like_stat(before)
                    or not stat.S_ISDIR(before.st_mode)
                    or _migration_identity(before) != expected
                ):
                    raise EnvironmentSelectionError("unsafe-migration-path")
                names = sorted(os.listdir(directory_path))
                for name in names:
                    path = directory_path / name
                    info = os.lstat(path)
                    identity = _migration_identity(info)
                    if _link_like_stat(info):
                        raise EnvironmentSelectionError("unsafe-migration-path")
                    if stat.S_ISDIR(info.st_mode):
                        walk_path(path, (*prefix, name), identity)
                    elif stat.S_ISREG(info.st_mode):
                        snapshots.append((path, identity))
                        rows.append("/".join((*prefix, name)))
                    else:
                        raise EnvironmentSelectionError("unsafe-migration-path")
                after = os.lstat(directory_path)
                if _link_like_stat(after) or _migration_identity(after) != expected:
                    raise EnvironmentSelectionError("unsafe-migration-path")
            except EnvironmentSelectionError:
                raise
            except OSError:
                raise EnvironmentSelectionError("unsafe-migration-path") from None

        walk_path(source_dir, (), initial_identity)
        try:
            for path, expected in snapshots:
                info = os.lstat(path)
                if _link_like_stat(info) or _migration_identity(info) != expected:
                    raise EnvironmentSelectionError("unsafe-migration-path")
        except OSError:
            raise EnvironmentSelectionError("unsafe-migration-path") from None

    try:
        final = os.lstat(source_dir)
    except OSError:
        raise EnvironmentSelectionError("unsafe-migration-path") from None
    if _link_like_stat(final) or _migration_identity(final) != initial_identity:
        raise EnvironmentSelectionError("unsafe-migration-path")
    return rows


def _environment_migration_preview(root: Path, source: str, target: str) -> dict:
    if not _valid_environment_slug(source) or not _valid_environment_slug(target):
        raise EnvironmentSelectionError("invalid-migration-slug")
    if source == target:
        raise EnvironmentSelectionError("migration-slugs-equal")
    source_dir = _safe_environment_dir(root, source)
    target_dir = _safe_environment_dir(root, target)
    source_files = _migration_source_files(source_dir)
    if ENVIRONMENT_MANIFEST_NAME in source_files:
        raise EnvironmentSelectionError("migration-source-already-registered")
    if target_dir.exists() or target_dir.is_symlink():
        raise EnvironmentSelectionError("migration-target-exists")
    rows: list[dict[str, str]] = []
    for relative in source_files:
        destination = target_dir / relative
        if destination.exists() or destination.is_symlink():
            raise EnvironmentSelectionError("migration-target-collision")
        rows.append(
            {
                "from": f"{ENVIRONMENTS_RELPATH}/{source}/{relative}",
                "to": f"{ENVIRONMENTS_RELPATH}/{target}/{relative}",
            }
        )
    return {
        "applySupported": False,
        "files": rows,
        "source": source,
        "target": target,
        "writesPerformed": False,
    }


def cmd_env(root: Path, args) -> int:
    if args.env_command == "migrate":
        try:
            payload = _environment_migration_preview(root, args.source, args.target)
        except EnvironmentSelectionError as exc:
            print(f"error: environment migration refused ({exc.code})", file=sys.stderr)
            return 1
        lines = [
            f"environment migration preview: {payload['source']} -> {payload['target']}",
            *(f"  {row['from']} -> {row['to']}" for row in payload["files"]),
            "writes performed: no (preview-only; apply the reviewed move with version control)",
        ]
        emit(payload, args.json, lines)
        return 0

    manifests, findings = load_environment_manifests(root)
    if findings:
        payload = {
            "errors": [
                {"path": row["path"], "rule": row["rule"]} for row in findings
            ],
            "schemaVersion": ENVIRONMENT_SCHEMA_VERSION,
        }
        emit(
            payload,
            args.json,
            (f"ERROR {row['path']} {row['rule']}" for row in payload["errors"]),
        )
        return 1

    if args.env_command == "list":
        selected = None
        selection_state = "unconfigured"
        selection_source = "none"
        try:
            selection = select_environment(root, requested=args.requested_env)
            selected = selection["slug"]
            selection_state = selection["state"]
            selection_source = selection["source"]
        except EnvironmentSelectionError as exc:
            selection_state = exc.code
            selection_source = "error"
        rows = [environment_metadata(data, selected) for data in manifests.values()]
        payload = {
            "environments": rows,
            "schemaVersion": ENVIRONMENT_SCHEMA_VERSION,
            "selectionSource": selection_source,
            "selectionState": selection_state,
        }
        lines = [f"environment selection: {selection_state} ({selection_source})"]
        for row in rows:
            marker = "*" if row["status"] == "selected" else " "
            lines.append(f"{marker} {row['slug']}  {row['status']}")
        emit(payload, args.json, lines)
        return 0

    fingerprints = machine_fingerprints()
    try:
        selection = select_environment(
            root,
            requested=args.requested_env,
            fingerprints=fingerprints,
        )
        code = 0
        selection_error = None
    except EnvironmentSelectionError as exc:
        selection = {"slug": None, "source": "error", "state": "unmatched"}
        selection_error = exc.code
        code = 1
    payload = {
        "fingerprints": fingerprints,
        "schemaVersion": ENVIRONMENT_SCHEMA_VERSION,
        "selected": selection["slug"],
        "selectionError": selection_error,
        "selectionSource": selection["source"],
        "selectionState": selection["state"],
    }
    lines = [
        f"environment detection: {selection['state']}",
        f"selection source: {selection['source']}",
        f"selected slug: {selection['slug'] or '(none)'}",
        "fingerprint evidence: SHA-256 only (raw machine identity suppressed)",
    ]
    if selection_error:
        lines.append(f"selection error: {selection_error}")
    emit(payload, args.json, lines)
    return code


def cmd_remote_safety(root: Path, args) -> int:
    result = evaluate_remote_safety(
        root,
        metadata_provider=GitHubMetadataProvider(),
        acknowledge_unknown=args.acknowledge_unknown,
    )
    persistence_requested = bool(args.persist)
    operation_allowed = result["personalDataAllowed"] and (
        not persistence_requested or result["persistenceAllowed"]
    )
    result = {
        **result,
        "operationAllowed": operation_allowed,
        "persistenceRequested": persistence_requested,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        print(f"remote safety: {result['state'].upper()}")
        print(f"verified state: {result['verifiedState']}")
        print("reasons: " + ", ".join(result["reasonCodes"]))
        print(f"push targets: {len(result['targets'])} (identities redacted)")
        print(
            "personal-data reads: "
            + ("allowed" if result["personalDataAllowed"] else "blocked")
        )
        print(
            "connector-result persistence: "
            + ("allowed" if result["persistenceAllowed"] else "blocked")
        )
        print(
            "requested operation: "
            + ("allowed" if result["operationAllowed"] else "blocked")
        )
    return 0 if operation_allowed else 1


_NOTIFICATIONS_MODULE = None


def _load_notifications_module():
    global _NOTIFICATIONS_MODULE
    if _NOTIFICATIONS_MODULE is not None:
        return _NOTIFICATIONS_MODULE
    path = Path(__file__).with_name("notifications.py")
    spec = importlib.util.spec_from_file_location("brain_notifications", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("notification module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _NOTIFICATIONS_MODULE = module
    return module


def cmd_notify(root: Path, args) -> int:
    return _load_notifications_module().command(sys.modules[__name__], root, args)


def cmd_validate(root: Path, args) -> int:
    errors, warnings = run_validate(
        root,
        args.check_index,
        requested_environment=getattr(args, "requested_env", None),
    )
    if args.json:
        print(
            json.dumps(
                {"errors": errors, "warnings": warnings},
                ensure_ascii=False,
                indent=1,
                sort_keys=True,
            )
        )
    else:
        for f in errors + warnings:
            severity = "ERROR" if f in errors else "WARN"
            location = f["path"] + (f":{f['line']}" if f["line"] is not None else "")
            print(f"{severity} {location} {f['rule']}: {f['message']}")
        print(f"{len(errors)} errors, {len(warnings)} warnings")
    if errors:
        return 1
    if warnings:
        return 2
    return 0


# ---------------------------------------------------------------------------
# Entry point


def main(argv: list[str] | None = None) -> int:
    global _ACTIVE_ENVIRONMENT
    notifications_api = _load_notifications_module()
    parser = argparse.ArgumentParser(prog="brain", description=__doc__)
    parser.add_argument("--vault", type=Path, default=None, help="vault root override")
    parser.add_argument(
        "--env",
        dest="requested_env",
        default=None,
        metavar="current|SLUG",
        help="environment override (default: current selection precedence)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, **kwargs):
        p = sub.add_parser(name, **kwargs)
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.add_argument(
            "--vault",
            type=Path,
            default=argparse.SUPPRESS,
            help="vault root override",
        )
        p.add_argument(
            "--env",
            dest="requested_env",
            default=argparse.SUPPRESS,
            metavar="current|SLUG",
            help="environment override (default: current selection precedence)",
        )
        return p

    add("index", help="rebuild and write the committed vault index")
    p = add("list", help="list note paths")
    p.add_argument("--dir", default=None, help="path prefix filter")
    p.add_argument("--tag", action="append", default=[], help="effective-tag filter (repeatable; trailing /* matches a namespace)")
    p.add_argument("--type", default=None, help="shorthand for --tag type/X")
    p = add("search", help="substring search over title, headings, body")
    p.add_argument("query")
    p.add_argument("--tag", action="append", default=[], help="effective-tag filter")
    p.add_argument(
        "--semantic",
        action="store_true",
        help="rank notes by embedding similarity (spec §18.4), degrading to keyword search without vectors",
    )
    p.add_argument(
        "--top",
        type=int,
        default=SEMANTIC_TOP_DEFAULT,
        help="semantic mode: max ranked notes returned",
    )
    p.add_argument(
        "--query-vector",
        action="store_true",
        help="semantic mode: read the query embedding as a JSON array from stdin",
    )
    p = add("links", help="outgoing links, backlinks, unresolved targets")
    p.add_argument("note")
    p = add(
        "migrate-links",
        help="preview/check/write legacy wikilinks as relative Markdown",
    )
    migration_mode = p.add_mutually_exclusive_group()
    migration_mode.add_argument(
        "--check",
        action="store_true",
        help="exit 1 while any legacy link (including placeholders) remains",
    )
    migration_mode.add_argument(
        "--write",
        action="store_true",
        help="apply the source-hashed plan atomically (requires clean planned paths)",
    )
    p = add("aymt", help="preview/check/write the deterministic Actions You May Take brief")
    aymt_mode = p.add_mutually_exclusive_group()
    aymt_mode.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when 00_Meta/AYMT.md is absent or stale; never write",
    )
    aymt_mode.add_argument(
        "--write",
        action="store_true",
        help="write only the owned generated 00_Meta/AYMT.md",
    )
    p.add_argument(
        "--github-input",
        default=None,
        metavar="PATH|-",
        help="optional strict sanitized GitHub issue snapshot (brain never invokes GitHub)",
    )
    p = add("home", help="preview/check/write the deterministic local Home")
    home_mode = p.add_mutually_exclusive_group()
    home_mode.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when 00_Meta/HOME.md is absent or stale; never write",
    )
    home_mode.add_argument(
        "--write",
        action="store_true",
        help="write only the owned generated 00_Meta/HOME.md",
    )
    p.add_argument(
        "--github-input",
        default=None,
        metavar="PATH|-",
        help="optional strict sanitized GitHub issue snapshot for AYMT actions",
    )
    p = add(
        "artifacts",
        help="preview/check/write the deterministic local graph and health dashboard",
    )
    artifact_mode = p.add_mutually_exclusive_group()
    artifact_mode.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when any owned artifact is absent or stale; never write",
    )
    artifact_mode.add_argument(
        "--write",
        action="store_true",
        help="write only the exact owned files under 08_Assets/artifacts/",
    )
    p.add_argument(
        "--open",
        action="store_true",
        help="open both fresh local files in the default browser",
    )
    p.add_argument(
        "--as-of",
        default=None,
        metavar="YYYY-MM-DD",
        help="controlled snapshot date (default: latest safe source updated date)",
    )
    p = add(
        "notify",
        help="preview, check, set up, or explicitly write a local notification",
    )
    notify_mode = p.add_mutually_exclusive_group()
    notify_mode.add_argument(
        "--setup",
        action="store_true",
        help="write selected-environment notification setup (never sends)",
    )
    notify_mode.add_argument(
        "--check",
        action="store_true",
        help="verify selected-environment notification readiness; never writes",
    )
    notify_mode.add_argument(
        "--deliver-file",
        action="store_true",
        help="write one sanitized envelope locally; never uses a network",
    )
    notify_mode.add_argument(
        "--send-plan",
        action="store_true",
        help="preview the provider payload and policy without writes or network",
    )
    p.add_argument("--input", default=None, metavar="PATH|-", help="strict v1 envelope JSON")
    p.add_argument("--output", type=Path, default=None, metavar="PATH", help="file delivery path under the system temporary directory")
    p.add_argument("--provider", choices=notifications_api.PROVIDERS, default=None, help="setup only: fake, file, or a gated provider formatter")
    p.add_argument("--destination-label", default=None, help="setup only: non-secret private destination label")
    p.add_argument("--private-destination-ack", action="store_true", help="setup only: owner confirms the destination is private")
    p.add_argument("--enable-category", action="append", choices=notifications_api.CATEGORIES, default=[], help="setup only: enable one independent category (repeatable)")
    p.add_argument("--timezone", default="America/New_York", help="setup only: IANA timezone for quiet hours")
    p.add_argument("--quiet-start", default="22:00", help="setup only: quiet-hours start HH:MM")
    p.add_argument("--quiet-end", default="07:00", help="setup only: quiet-hours end HH:MM")
    p.add_argument("--rate-limit", type=int, default=6, help="setup only: deliveries per rolling hour")
    p.add_argument("--dedupe-hours", type=int, default=24, help="setup only: dedupe window in hours")
    p.add_argument("--secret-env", default=None, help="setup only: environment-variable name, never its value")
    p.add_argument("--allow-https-host", action="append", default=[], help="setup only: approved lowercase HTTPS host")
    p.add_argument("--approve-private-send", action="store_true", help="file delivery only: one-run owner approval")
    p.add_argument("--now", default=None, metavar="RFC3339", help="preview-only deterministic policy time override")
    add("tags", help="tag usage counts by namespace")
    p = add("show", help="full index record for one note")
    p.add_argument("note")
    p = add("recent", help="notes by updated date, newest first")
    p.add_argument("n", nargs="?", type=int, default=10)
    p = add("validate", help="check vault conventions; exit 0 clean / 1 errors / 2 warnings")
    p.add_argument("--check-index", action="store_true", help="also verify the committed index is fresh")
    p = add("curate", help="re-review signals: expired, missing/over-cap expires, oversized, stale, orphans, unreferenced assets")
    p.add_argument("--check-urls", action="store_true", help="also probe source URLs over the network (never pre-commit)")
    add("context", help="bootstrap docs' sizes against their context budgets")
    add("config", help="effective vault config (00_Meta/config.yaml merged over defaults)")
    p = add("tasks", help="checkbox tasks across the vault (spec §17)")
    p.add_argument("--open", action="store_true", help="open (unchecked) tasks only")
    p.add_argument(
        "--due",
        default=None,
        metavar="YYYY-MM-DD|today",
        help="tasks with a due date on or before this date",
    )
    p.add_argument(
        "--overdue", action="store_true", help="open tasks whose due date is past"
    )
    p.add_argument(
        "--project", default=None, metavar="PREFIX", help="note-path prefix filter"
    )
    p = add("report", help="vault health: stale-active, orphans, Inbox aging, tag drift, unresolved links")
    p.add_argument(
        "--since",
        default=None,
        metavar="YYYY-MM-DD",
        help="scope tag drift and unresolved links to notes updated on/after this date",
    )
    p = add("embed", help="maintain the semantic-search embeddings sidecar (spec §18.3)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--stdin-json",
        action="store_true",
        help="ingest precomputed vectors from stdin JSON ({model, vectors})",
    )
    mode.add_argument(
        "--local",
        action="store_true",
        help="embed changed notes with the optional local model (sentence-transformers)",
    )
    mode.add_argument("--status", action="store_true", help="report sidecar coverage; no writes")
    p.add_argument("--model", default=None, help="--local: embedding model name override")
    p = add(
        "remote-safety",
        help="fail-closed preflight before reading personal-data connectors",
    )
    p.add_argument(
        "--acknowledge-unknown",
        action="store_true",
        help="allow unknown state for this invocation only (never overrides public/template)",
    )
    p.add_argument(
        "--persist",
        action="store_true",
        help="require connector-result persistence to be safe for this invocation",
    )
    p = add(
        "install",
        help="preview/apply/doctor/uninstall the portable resolver on PATH",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="perform the previewed install or uninstall writes",
    )
    operation = p.add_mutually_exclusive_group()
    operation.add_argument("--doctor", action="store_true", help="diagnose installation")
    operation.add_argument(
        "--uninstall",
        action="store_true",
        help="preview removing the managed launcher (combine with --apply to write)",
    )
    p.add_argument(
        "--target",
        type=Path,
        default=None,
        metavar="DIRECTORY",
        help="existing writable install directory (default: first safe PATH directory)",
    )
    p.add_argument(
        "--state-file",
        type=Path,
        default=None,
        metavar="PATH",
        help="external ownership-manifest path override",
    )

    env_parser = sub.add_parser(
        "env", help="detect, list, or preview migration of environment identity"
    )
    env_sub = env_parser.add_subparsers(dest="env_command", required=True)

    def add_env(name: str, **kwargs):
        p = env_sub.add_parser(name, **kwargs)
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.add_argument(
            "--vault",
            type=Path,
            default=argparse.SUPPRESS,
            help="vault root override",
        )
        p.add_argument(
            "--env",
            dest="requested_env",
            default=argparse.SUPPRESS,
            metavar="current|SLUG",
            help="environment override",
        )
        return p

    add_env("detect", help="hash local evidence and resolve the current environment")
    add_env("list", help="show metadata-only records for every tracked environment")
    p = add_env("migrate", help="preview moving an unregistered legacy environment")
    p.add_argument("source")
    p.add_argument("target")

    args = parser.parse_args(argv)
    root = (getattr(args, "vault", None) or default_vault_root()).resolve()
    handlers = {
        "index": cmd_index,
        "list": cmd_list,
        "search": cmd_search,
        "links": cmd_links,
        "migrate-links": cmd_migrate_links,
        "aymt": cmd_aymt,
        "home": cmd_home,
        "artifacts": cmd_artifacts,
        "notify": cmd_notify,
        "tags": cmd_tags,
        "show": cmd_show,
        "recent": cmd_recent,
        "validate": cmd_validate,
        "curate": cmd_curate,
        "context": cmd_context,
        "config": cmd_config,
        "report": cmd_report,
        "tasks": cmd_tasks,
        "embed": cmd_embed,
        "remote-safety": cmd_remote_safety,
        "install": cmd_install,
        "env": cmd_env,
    }
    previous_environment = _ACTIVE_ENVIRONMENT
    try:
        if args.command not in {
            "env",
            "validate",
            "index",
            "context",
            "config",
            "remote-safety",
            "install",
            "artifacts",
            "notify",
        }:
            try:
                selector = (
                    select_aymt_environment
                    if args.command in {"aymt", "home"}
                    else select_environment
                )
                selection = selector(root, requested=getattr(args, "requested_env", None))
            except EnvironmentSelectionError as exc:
                if args.command in {"aymt", "home"}:
                    label = "AYMT" if args.command == "aymt" else "Home"
                    if args.json:
                        print(json.dumps({"error": f"{label} generation failed safely"}, indent=1, sort_keys=True))
                    else:
                        print(f"error: {label} generation failed safely", file=sys.stderr)
                    return 1
                print(
                    f"error: environment selection failed ({exc.code})",
                    file=sys.stderr,
                )
                return 1
            _ACTIVE_ENVIRONMENT = selection["slug"]
            if args.command == "aymt":
                args.aymt_selection = selection
            elif args.command == "home":
                args.home_selection = selection
        return handlers[args.command](root, args)
    finally:
        _ACTIVE_ENVIRONMENT = previous_environment


if __name__ == "__main__":
    sys.exit(main())
