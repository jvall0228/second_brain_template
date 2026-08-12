"""Provider-neutral, push-only notification planning and local file delivery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
STATE_SCHEMA_VERSION = 1
OWNER = "brain-notifications"
CONFIG_NAME = "notifications.json"
STATE_NAME = "notification-state.json"
OUTBOX_DIR = "notification-output"
CATEGORIES = (
    "automation",
    "inbox-review",
    "maintenance",
    "pr-review",
    "validation",
)
SEVERITIES = ("info", "warning", "error", "critical")
PRIVACY_CLASSES = ("operational", "private-owner", "restricted/private")
PROVIDERS = ("fake", "file", "slack", "google-chat", "teams")
REAL_PROVIDERS = ("slack", "google-chat", "teams")
EVENT_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
DEDUPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()/-]{0,79}$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$")
RFC3339_RE = re.compile(
    r"^(?:20[0-9]{2}|2100)-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
    r"[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
VAULT_LINK_RE = re.compile(
    r"^(?:00_Meta|01_Profile|02_Inbox|02_Outbox|03_Journal|04_Projects|"
    r"05_Areas|06_Resources|07_Archives|08_Assets|09_Templates|10_Agents)/"
    r"[A-Za-z0-9][A-Za-z0-9_./%() +-]{0,510}$"
)
ABSOLUTE_PATH_RE = re.compile(
    r"(?:(?<![A-Za-z0-9._-])/(?!/)[^\s<>()\[\]{}\"']+|"
    r"(?<![A-Za-z0-9._-])[A-Za-z]:[\\/][^\s<>()\[\]{}\"']*|"
    r"\\\\[^\\\s]+\\[^\s<>()\[\]{}\"']*)"
)
TRACKING_QUERY_RE = re.compile(r"(?i)(?:token|secret|key|signature|sig|auth|utm_)\s*=")
INLINE_LINK_RE = re.compile(r"(?i)(?:https?://|<[^>]*>|\]\s*\()")
SENSITIVE_LABEL_RE = re.compile(
    r"(?i)(?:\bAKIA[0-9A-Z]{16}\b|\b(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{20,}\b|"
    r"\bxox[a-z]-[A-Za-z0-9-]{10,}\b)"
)
RETRY_DELAYS_SECONDS = (5, 30, 120)
MAX_STATE_ROWS = 256
MAX_INPUT_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 128 * 1024


class NotificationError(RuntimeError):
    """Stable, redacted notification-boundary refusal."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def strict_json(raw: bytes) -> object:
    def exact_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise NotificationError("notification JSON is invalid")
            value[key] = item
        return value

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=exact_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise NotificationError("notification JSON is invalid") from None


def _strict_int(value: object, expected: int) -> bool:
    return type(value) is int and value == expected


def _text(api, value: object, *, limit: int) -> str:
    if not isinstance(value, str):
        raise NotificationError("notification envelope is invalid")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise NotificationError("notification content is not safe")
    normalized = api.nfc(" ".join(value.split()))
    if not normalized or len(normalized) > limit:
        raise NotificationError("notification envelope is invalid")
    if (
        ABSOLUTE_PATH_RE.search(normalized)
        or TRACKING_QUERY_RE.search(normalized)
        or INLINE_LINK_RE.search(normalized)
        or any(pattern.search(normalized) for _name, pattern in api.SECRET_RULES)
    ):
        raise NotificationError("notification content is not safe")
    return normalized


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not RFC3339_RE.fullmatch(value):
        raise NotificationError("notification envelope is invalid")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        raise NotificationError("notification envelope is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NotificationError("notification envelope is invalid")
    offset = parsed.utcoffset()
    if offset is None or abs(offset) > timedelta(hours=14):
        raise NotificationError("notification envelope is invalid")
    return parsed


def _vault_link(value: str) -> bool:
    if not VAULT_LINK_RE.fullmatch(value) or "\\" in value or ":" in value:
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _https_link(value: str, allowed_hosts: frozenset[str]) -> bool:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        return False
    host = parsed.hostname.casefold()
    if host == "github.com":
        pieces = [piece for piece in parsed.path.split("/") if piece]
        return (
            len(pieces) == 4
            and all(re.fullmatch(r"[A-Za-z0-9_.-]+", piece) for piece in pieces[:2])
            and pieces[2] in {"issues", "pull"}
            and pieces[3].isascii()
            and pieces[3].isdigit()
        )
    return host in allowed_hosts and parsed.path.startswith("/")


def safe_link(api, value: object, allowed_hosts: frozenset[str]) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise NotificationError("notification source link is invalid")
    if (
        any(character < " " or character == "\x7f" for character in value)
        or any(pattern.search(value) for _name, pattern in api.SECRET_RULES)
    ):
        raise NotificationError("notification source link is invalid")
    if _vault_link(value) and not ABSOLUTE_PATH_RE.search(value):
        return value
    if _https_link(value, allowed_hosts):
        return value
    raise NotificationError("notification source link is invalid")


def validate_envelope(
    api,
    value: object,
    *,
    allowed_hosts: frozenset[str] = frozenset(),
    root: Path | None = None,
) -> dict:
    """Validate and centrally privacy-filter the exact version-1 envelope."""
    if not isinstance(value, dict):
        raise NotificationError("notification envelope is invalid")
    required = {
        "artifact",
        "category",
        "dedupeKey",
        "event",
        "occurredAt",
        "privacyClass",
        "schemaVersion",
        "severity",
        "sources",
        "summary",
        "title",
    }
    if set(value) != required or not _strict_int(value.get("schemaVersion"), 1):
        raise NotificationError("notification envelope is invalid")
    event = value["event"]
    category = value["category"]
    severity = value["severity"]
    privacy = value["privacyClass"]
    dedupe = value["dedupeKey"]
    if not isinstance(event, str) or not EVENT_RE.fullmatch(event) or len(event) > 80:
        raise NotificationError("notification envelope is invalid")
    if category not in CATEGORIES or severity not in SEVERITIES:
        raise NotificationError("notification envelope is invalid")
    if privacy not in PRIVACY_CLASSES or privacy == "restricted/private":
        raise NotificationError("notification privacy class is not deliverable")
    if not isinstance(dedupe, str) or not DEDUPE_RE.fullmatch(dedupe):
        raise NotificationError("notification envelope is invalid")
    for bounded in (event, dedupe):
        if (
            any(ord(character) < 32 or ord(character) == 127 for character in bounded)
            or ABSOLUTE_PATH_RE.search(bounded)
            or TRACKING_QUERY_RE.search(bounded)
            or any(pattern.search(bounded) for _name, pattern in api.SECRET_RULES)
        ):
            raise NotificationError("notification content is not safe")
    sources = value["sources"]
    if not isinstance(sources, list) or len(sources) > 5:
        raise NotificationError("notification envelope is invalid")
    normalized_sources = []
    for row in sources:
        if not isinstance(row, dict) or set(row) != {"label", "link"}:
            raise NotificationError("notification envelope is invalid")
        normalized_sources.append(
            {
                "label": _text(api, row["label"], limit=80),
                "link": safe_link(api, row["link"], allowed_hosts),
            }
        )
    artifact = value["artifact"]
    normalized_artifact = None
    if artifact is not None:
        if not isinstance(artifact, dict) or set(artifact) != {"label", "link"}:
            raise NotificationError("notification envelope is invalid")
        normalized_artifact = {
            "label": _text(api, artifact["label"], limit=80),
            "link": safe_link(api, artifact["link"], allowed_hosts),
        }
    bounded_links = normalized_sources + (
        [] if normalized_artifact is None else [normalized_artifact]
    )
    if root is not None and any(_vault_link(row["link"]) for row in bounded_links):
        tracked = api.git_tracked(root)
        if tracked is None:
            raise NotificationError("notification source authority is unavailable")
        for row in bounded_links:
            link = row["link"]
            if not _vault_link(link):
                continue
            if link not in tracked or link.startswith(f"{api.ENVIRONMENTS_RELPATH}/"):
                raise NotificationError("notification source link is not deliverable")
            try:
                raw = api._read_nofollow_bytes(root, link, max_bytes=256 * 1024)
                record = api.build_index(
                    root, [link], [], note_snapshots={link: raw}
                )["notes"][link]
            except OSError:
                raise NotificationError("notification source authority is unavailable") from None
            if api.is_restricted(record) or any(
                pattern.search(raw.decode("utf-8", "ignore"))
                for _name, pattern in api.SECRET_RULES
            ):
                raise NotificationError("notification source link is not deliverable")
    parsed_time = _timestamp(value["occurredAt"])
    return {
        "artifact": normalized_artifact,
        "category": category,
        "dedupeKey": dedupe,
        "event": event,
        "occurredAt": parsed_time.isoformat(),
        "privacyClass": privacy,
        "schemaVersion": SCHEMA_VERSION,
        "severity": severity,
        "sources": normalized_sources,
        "summary": _text(api, value["summary"], limit=1000),
        "title": _text(api, value["title"], limit=120),
    }


def default_config() -> dict:
    return {
        "allowedHttpsHosts": [],
        "categories": {category: False for category in CATEGORIES},
        "dedupeHours": 24,
        "destinationLabel": None,
        "privateDestinationAcknowledged": False,
        "provider": None,
        "quietHours": {
            "end": "07:00",
            "start": "22:00",
            "timezone": "America/New_York",
        },
        "rateLimitPerHour": 6,
        "schemaVersion": CONFIG_SCHEMA_VERSION,
        "secretEnvironmentVariable": None,
    }


def validate_config(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != set(default_config()):
        raise NotificationError("notification setup is invalid")
    if not _strict_int(value.get("schemaVersion"), CONFIG_SCHEMA_VERSION):
        raise NotificationError("notification setup is invalid")
    provider = value["provider"]
    label = value["destinationLabel"]
    acknowledged = value["privateDestinationAcknowledged"]
    if (
        provider not in PROVIDERS
        or not isinstance(label, str)
        or not LABEL_RE.fullmatch(label)
        or ABSOLUTE_PATH_RE.search(label)
        or any(ord(character) < 32 or ord(character) == 127 for character in label)
        or TRACKING_QUERY_RE.search(label)
        or SENSITIVE_LABEL_RE.search(label)
    ):
        raise NotificationError("notification setup is invalid")
    if type(acknowledged) is not bool:
        raise NotificationError("notification setup is invalid")
    categories = value["categories"]
    if not isinstance(categories, dict) or set(categories) != set(CATEGORIES):
        raise NotificationError("notification setup is invalid")
    if any(type(categories[name]) is not bool for name in CATEGORIES):
        raise NotificationError("notification setup is invalid")
    quiet = value["quietHours"]
    if not isinstance(quiet, dict) or set(quiet) != {"end", "start", "timezone"}:
        raise NotificationError("notification setup is invalid")
    for name in ("start", "end"):
        if not isinstance(quiet[name], str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", quiet[name]):
            raise NotificationError("notification setup is invalid")
    if (
        not isinstance(quiet["timezone"], str)
        or len(quiet["timezone"]) > 64
        or not re.fullmatch(r"[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)+", quiet["timezone"])
    ):
        raise NotificationError("notification setup is invalid")
    try:
        ZoneInfo(quiet["timezone"])
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise NotificationError("notification setup is invalid") from None
    if type(value["rateLimitPerHour"]) is not int or not 1 <= value["rateLimitPerHour"] <= 60:
        raise NotificationError("notification setup is invalid")
    if type(value["dedupeHours"]) is not int or not 1 <= value["dedupeHours"] <= 168:
        raise NotificationError("notification setup is invalid")
    hosts = value["allowedHttpsHosts"]
    if not isinstance(hosts, list) or len(hosts) > 10:
        raise NotificationError("notification setup is invalid")
    normalized_hosts = []
    for host in hosts:
        labels = host.split(".") if isinstance(host, str) else []
        if (
            not isinstance(host, str)
            or not HOST_RE.fullmatch(host)
            or host != host.casefold()
            or any(
                not label
                or len(label) > 63
                or label.startswith("-")
                or label.endswith("-")
                for label in labels
            )
        ):
            raise NotificationError("notification setup is invalid")
        normalized_hosts.append(host)
    if len(set(normalized_hosts)) != len(normalized_hosts):
        raise NotificationError("notification setup is invalid")
    secret_name = value["secretEnvironmentVariable"]
    if provider in REAL_PROVIDERS:
        if not isinstance(secret_name, str) or not ENV_NAME_RE.fullmatch(secret_name):
            raise NotificationError("notification setup is invalid")
    elif secret_name is not None:
        raise NotificationError("notification setup is invalid")
    return {
        **value,
        "allowedHttpsHosts": sorted(normalized_hosts),
        "categories": {key: categories[key] for key in CATEGORIES},
    }


def empty_state() -> dict:
    return {"deliveries": [], "owner": OWNER, "schemaVersion": STATE_SCHEMA_VERSION}


def validate_state(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {"deliveries", "owner", "schemaVersion"}:
        raise NotificationError("notification delivery state needs recovery")
    if value["owner"] != OWNER or not _strict_int(value["schemaVersion"], STATE_SCHEMA_VERSION):
        raise NotificationError("notification delivery state needs recovery")
    rows = value["deliveries"]
    if not isinstance(rows, list) or len(rows) > MAX_STATE_ROWS:
        raise NotificationError("notification delivery state needs recovery")
    normalized = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"category", "dedupeDigest", "deliveredAt"}:
            raise NotificationError("notification delivery state needs recovery")
        if (
            row["category"] not in CATEGORIES
            or not isinstance(row["dedupeDigest"], str)
            or not DIGEST_RE.fullmatch(row["dedupeDigest"])
        ):
            raise NotificationError("notification delivery state needs recovery")
        delivered = _timestamp(row["deliveredAt"])
        normalized.append({**row, "deliveredAt": delivered.isoformat()})
    return {"deliveries": normalized, "owner": OWNER, "schemaVersion": STATE_SCHEMA_VERSION}


def _hm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def in_quiet_hours(now: datetime, quiet: dict) -> bool:
    local = now.astimezone(ZoneInfo(quiet["timezone"]))
    current = (local.hour, local.minute)
    start, end = _hm(quiet["start"]), _hm(quiet["end"])
    if start == end:
        return False
    return start <= current < end if start < end else current >= start or current < end


def delivery_decision(config: dict, state: dict, envelope: dict, now: datetime) -> dict:
    reasons = []
    if not config["privateDestinationAcknowledged"]:
        reasons.append("private-destination-unverified")
    if not config["categories"][envelope["category"]]:
        reasons.append("category-disabled")
    if in_quiet_hours(now, config["quietHours"]):
        reasons.append("quiet-hours")
    cutoff = now - timedelta(hours=config["dedupeHours"])
    dedupe_digest = hashlib.sha256(envelope["dedupeKey"].encode()).hexdigest()
    if any(row["dedupeDigest"] == dedupe_digest and _timestamp(row["deliveredAt"]) >= cutoff for row in state["deliveries"]):
        reasons.append("duplicate")
    hour_cutoff = now - timedelta(hours=1)
    if sum(_timestamp(row["deliveredAt"]) >= hour_cutoff for row in state["deliveries"]) >= config["rateLimitPerHour"]:
        reasons.append("rate-limited")
    return {
        "allowed": not reasons,
        "reasonCodes": sorted(set(reasons)),
        "retryDelaysSeconds": list(RETRY_DELAYS_SECONDS),
    }


def retry_delay(attempt: int, *, transient: bool) -> int | None:
    if type(attempt) is not int or attempt < 0 or not transient:
        return None
    return RETRY_DELAYS_SECONDS[attempt] if attempt < len(RETRY_DELAYS_SECONDS) else None


def fallback_text(envelope: dict) -> str:
    lines = [
        f"[{envelope['severity'].upper()}] {envelope['title']}",
        envelope["summary"],
    ]
    for row in envelope["sources"]:
        lines.append(f"{row['label']}: {row['link']}")
    if envelope["artifact"]:
        lines.append(f"{envelope['artifact']['label']}: {envelope['artifact']['link']}")
    return "\n".join(lines)[:4000]


def _links(envelope: dict) -> list[dict]:
    rows = list(envelope["sources"])
    if envelope["artifact"]:
        rows.append(envelope["artifact"])
    return rows


def format_provider(provider: str, envelope: dict) -> dict:
    """Pure payload formatting only; this module intentionally has no HTTP client."""
    text = fallback_text(envelope)
    links = _links(envelope)
    if provider == "fake" or provider == "file":
        return {"envelope": envelope, "text": text}
    if provider == "slack":
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": envelope["title"][:150]}},
            {"type": "section", "text": {"type": "plain_text", "text": envelope["summary"][:3000]}},
        ]
        buttons = [
                {"type": "button", "text": {"type": "plain_text", "text": row["label"][:75]}, "url": row["link"]}
                for row in links[:5] if row["link"].startswith("https://")
        ]
        if buttons:
            blocks.append({"type": "actions", "elements": buttons})
        return {"blocks": blocks, "text": text}
    if provider == "google-chat":
        buttons = [
            {"text": row["label"][:40], "onClick": {"openLink": {"url": row["link"]}}}
            for row in links[:5] if row["link"].startswith("https://")
        ]
        widgets = [{"textParagraph": {"text": envelope["summary"]}}]
        if buttons:
            widgets.append({"buttonList": {"buttons": buttons}})
        return {"cardsV2": [{"cardId": envelope["dedupeKey"][:64], "card": {
            "header": {"title": envelope["title"]}, "sections": [{"widgets": widgets}]
        }}], "text": text}
    if provider == "teams":
        actions = [
            {"type": "Action.OpenUrl", "title": row["label"][:60], "url": row["link"]}
            for row in links[:5] if row["link"].startswith("https://")
        ]
        card = {
            "actions": actions,
            "body": [
                {"type": "TextBlock", "text": envelope["title"], "weight": "Bolder", "wrap": True},
                {"type": "TextBlock", "text": envelope["summary"], "wrap": True},
            ],
            "type": "AdaptiveCard",
            "version": "1.4",
        }
        return {"attachments": [{"content": card, "contentType": "application/vnd.microsoft.card.adaptive"}], "text": text, "type": "message"}
    raise NotificationError("notification provider is unavailable")


def _overlay_rel(api, slug: str, name: str) -> str:
    return f"{api.ENVIRONMENT_OVERLAYS_RELPATH}/{slug}/{name}"


def _safe_selected(api, root: Path, requested: str | None) -> dict:
    try:
        selected = api.select_environment(root, requested=requested)
    except api.EnvironmentSelectionError:
        raise NotificationError("notification environment is unavailable") from None
    if selected["state"] != "selected" or not selected["slug"]:
        raise NotificationError("notification environment is unavailable")
    return selected


def _optional_selected(api, root: Path, requested: str | None) -> dict | None:
    try:
        selected = api.select_environment(root, requested=requested)
    except api.EnvironmentSelectionError:
        raise NotificationError("notification environment is unavailable") from None
    if selected["state"] == "unconfigured" and selected.get("slug") is None:
        return None
    if selected["state"] != "selected" or not selected.get("slug"):
        raise NotificationError("notification environment is unavailable")
    return selected


def _read_optional(api, root: Path, rel: str, *, limit: int) -> tuple[bytes | None, dict | None]:
    try:
        raw = api._read_nofollow_bytes(root, rel, max_bytes=limit)
    except FileNotFoundError:
        try:
            parent, name = api._open_migration_parent(root, rel)
        except (FileNotFoundError, OSError, api.LinkMigrationError):
            return None, None
        try:
            prefix = f".{name}.migrate-"
            if any(entry.startswith(prefix) for entry in os.listdir(parent)):
                raise NotificationError("notification local state needs recovery")
        finally:
            os.close(parent)
        return None, None
    except OSError:
        raise NotificationError("notification local state is unsafe") from None
    try:
        value = strict_json(raw)
    except NotificationError:
        raise NotificationError("notification local state needs recovery") from None
    return raw, value


def load_setup(api, root: Path, requested: str | None) -> tuple[dict, dict | None, bytes | None]:
    selected = _safe_selected(api, root, requested)
    rel = _overlay_rel(api, selected["slug"], CONFIG_NAME)
    raw, value = _read_optional(api, root, rel, limit=64 * 1024)
    return selected, None if value is None else validate_config(value), raw


def load_delivery_state(api, root: Path, slug: str) -> tuple[dict, bytes | None]:
    rel = _overlay_rel(api, slug, STATE_NAME)
    raw, value = _read_optional(api, root, rel, limit=256 * 1024)
    return (empty_state() if value is None else validate_state(value)), raw


def setup_payload(args) -> dict:
    if not args.provider or not args.destination_label or not args.private_destination_ack:
        raise NotificationError("notification setup requires an acknowledged private destination")
    categories = {category: category in set(args.enable_category or []) for category in CATEGORIES}
    hosts = sorted(set(args.allow_https_host or []))
    value = {
        "allowedHttpsHosts": hosts,
        "categories": categories,
        "dedupeHours": args.dedupe_hours,
        "destinationLabel": args.destination_label,
        "privateDestinationAcknowledged": True,
        "provider": args.provider,
        "quietHours": {"end": args.quiet_end, "start": args.quiet_start, "timezone": args.timezone},
        "rateLimitPerHour": args.rate_limit,
        "schemaVersion": CONFIG_SCHEMA_VERSION,
        "secretEnvironmentVariable": args.secret_env,
    }
    return validate_config(value)


def _require_mutation(api) -> None:
    if not api._migration_mutation_supported():
        raise NotificationError("safe notification writes are unavailable")


def _casefold_conflict(parent: int, name: str) -> bool:
    folded = name.casefold()
    return any(entry.casefold() == folded and entry != name for entry in os.listdir(parent))


def _open_child_directory(parent: int, name: str, *, create: bool) -> int:
    if _casefold_conflict(parent, name):
        raise NotificationError("notification local state is unsafe")
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
            os.fsync(parent)
        except FileExistsError:
            pass
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        child = os.open(name, flags, dir_fd=parent)
    except OSError:
        raise NotificationError("notification local state is unsafe") from None
    if not stat.S_ISDIR(os.fstat(child).st_mode):
        os.close(child)
        raise NotificationError("notification local state is unsafe")
    return child


def _open_overlay_directory(api, root: Path, slug: str, *, output: bool) -> int:
    _require_mutation(api)
    if not api._valid_environment_slug(slug):
        raise NotificationError("notification environment is unavailable")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(root, flags)
    try:
        components = [*Path(api.ENVIRONMENT_OVERLAYS_RELPATH).parts, slug]
        if output:
            components.append(OUTBOX_DIR)
        for component in components:
            child = _open_child_directory(descriptor, component, create=True)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _stage_exact(api, parent: int, basename: str, data: bytes) -> tuple[str, dict]:
    name = api._unused_migration_name(parent, basename, "new")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(name, flags, 0o600, dir_fd=parent)
    identity = api._link_migration_identity(os.fstat(descriptor))
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
    except BaseException:
        try:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if api._link_migration_identity(current) == identity:
                os.unlink(name, dir_fd=parent)
                os.fsync(parent)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(descriptor)
    return name, {"identity": identity}


def _create_exact_at(parent: int, name: str, data: bytes) -> tuple[int, int]:
    if len(data) > MAX_OUTPUT_BYTES:
        raise NotificationError("notification output is too large")
    if _casefold_conflict(parent, name):
        raise NotificationError("notification output is occupied")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, 0o600, dir_fd=parent)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        return info.st_dev, info.st_ino
    except BaseException:
        try:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            opened = os.fstat(descriptor)
            if (info.st_dev, info.st_ino) == (opened.st_dev, opened.st_ino):
                os.unlink(name, dir_fd=parent)
                os.fsync(parent)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def _remove_created_at(parent: int, name: str, identity: tuple[int, int]) -> bool:
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (info.st_dev, info.st_ino) != identity or not stat.S_ISREG(info.st_mode):
            return False
        os.unlink(name, dir_fd=parent)
        os.fsync(parent)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def _write_json_cas(
    api,
    root: Path,
    rel: str,
    desired: bytes,
    expected: bytes | None,
    validator,
) -> None:
    _require_mutation(api)
    parent, name = api._open_migration_parent(root, rel)
    item = {"desired": desired, "name": name, "new": None, "parent": parent, "stage_ownership": {}}
    backup = None
    installed = False
    committed = False
    try:
        try:
            current, current_info = api._read_migration_at(parent, name)
        except FileNotFoundError:
            current = current_info = None
        if current != expected:
            raise NotificationError("notification delivery state changed; preserved")
        if current is not None:
            try:
                validator(strict_json(current))
            except NotificationError:
                raise NotificationError("notification delivery state needs recovery") from None
        item["new"], item["stage_ownership"] = _stage_exact(api, parent, name, desired)
        if current is not None:
            again, again_info = api._read_migration_at(parent, name)
            if again != current or api._link_migration_identity(again_info) != api._link_migration_identity(current_info):
                raise NotificationError("notification delivery state changed; preserved")
            backup = api._unused_migration_name(parent, name, "old")
            # Register the rollback name before rename so caught interruption can restore it.
            api._quarantine_migration_at(parent, name, backup)
            try:
                backup_raw, backup_info = api._read_migration_at(parent, backup)
            except FileNotFoundError:
                backup_raw = backup_info = None
            if (
                backup_raw != current
                or backup_info is None
                or api._link_migration_identity(backup_info)
                != api._link_migration_identity(current_info)
            ):
                if backup_raw is not None:
                    if api._restore_quarantined_at(parent, backup, name):
                        os.unlink(backup, dir_fd=parent)
                        backup = None
                        os.fsync(parent)
                raise NotificationError("notification local state changed; preserved")
        if _casefold_conflict(parent, name):
            raise NotificationError("notification local state changed; preserved")
        staged_raw, staged_info = api._read_migration_at(parent, item["new"])
        if (
            staged_raw != desired
            or api._link_migration_identity(staged_info)
            != item["stage_ownership"]["identity"]
        ):
            raise NotificationError("notification local state changed; preserved")
        api._install_migration_at(parent, item["new"], name)
        installed = True
        actual, actual_info = api._read_migration_at(parent, name)
        stage_info = os.stat(item["new"], dir_fd=parent, follow_symlinks=False)
        if actual != desired or stat.S_IMODE(actual_info.st_mode) != 0o600 or (actual_info.st_dev, actual_info.st_ino) != (stage_info.st_dev, stage_info.st_ino):
            raise NotificationError("notification delivery state changed; preserved")
        if backup is not None:
            backup_raw, backup_info = api._read_migration_at(parent, backup)
            if (
                backup_raw != current
                or api._link_migration_identity(backup_info)
                != api._link_migration_identity(current_info)
            ):
                raise NotificationError("notification delivery state changed; preserved")
        committed = True
        if backup is not None:
            os.unlink(backup, dir_fd=parent)
            backup = None
            os.fsync(parent)
    except BaseException:
        if committed:
            try:
                final_raw, final_info = api._read_migration_at(parent, name)
                stage_info = os.stat(
                    item["new"], dir_fd=parent, follow_symlinks=False
                )
            except OSError:
                pass
            else:
                if (
                    final_raw == desired
                    and (final_info.st_dev, final_info.st_ino)
                    == (stage_info.st_dev, stage_info.st_ino)
                ):
                    return
        if installed and not committed:
            try:
                _actual, actual_info = api._read_migration_at(parent, name)
                stage_info = os.stat(item["new"], dir_fd=parent, follow_symlinks=False)
                if (actual_info.st_dev, actual_info.st_ino) == (stage_info.st_dev, stage_info.st_ino):
                    os.unlink(name, dir_fd=parent)
            except OSError:
                pass
        if backup is not None and not committed:
            try:
                if api._restore_quarantined_at(parent, backup, name):
                    os.unlink(backup, dir_fd=parent)
                    backup = None
            except OSError:
                pass
        raise
    finally:
        try:
            if item["new"] is not None:
                try:
                    api._remove_owned_migration_stage(item)
                except (OSError, api.LinkMigrationError):
                    try:
                        final_raw, final_info = api._read_migration_at(
                            parent, name
                        )
                    except OSError:
                        final_raw = None
                        final_info = None
                    if not (
                        committed
                        and final_raw == desired
                        and final_info is not None
                        and stat.S_IMODE(final_info.st_mode) == 0o600
                    ):
                        raise
        finally:
            os.close(parent)


def _delete_json_cas(api, root: Path, rel: str, expected: bytes) -> None:
    """Delete only an authenticated current JSON file, preserving any replacement."""
    parent, name = api._open_migration_parent(root, rel)
    backup = None
    current_info = None
    try:
        current, current_info = api._read_migration_at(parent, name)
        if current != expected:
            raise NotificationError("notification delivery state changed; preserved")
        backup = api._unused_migration_name(parent, name, "old")
        api._quarantine_migration_at(parent, name, backup)
        backup_raw, backup_info = api._read_migration_at(parent, backup)
        if (
            backup_raw != expected
            or api._link_migration_identity(backup_info)
            != api._link_migration_identity(current_info)
        ):
            if api._restore_quarantined_at(parent, backup, name):
                os.unlink(backup, dir_fd=parent)
                backup = None
                os.fsync(parent)
            raise NotificationError("notification delivery state changed; preserved")
        os.unlink(backup, dir_fd=parent)
        backup = None
        os.fsync(parent)
    except BaseException:
        if backup is not None:
            try:
                if api._restore_quarantined_at(parent, backup, name):
                    os.unlink(backup, dir_fd=parent)
                    backup = None
                    os.fsync(parent)
            except OSError:
                pass
        raise
    finally:
        os.close(parent)


def write_setup(api, root: Path, selected: dict, payload: dict, prior: bytes | None) -> None:
    parent = _open_overlay_directory(api, root, selected["slug"], output=False)
    os.close(parent)
    rel = _overlay_rel(api, selected["slug"], CONFIG_NAME)
    desired = canonical_json(payload) + b"\n"
    _write_json_cas(api, root, rel, desired, prior, validate_config)


def _output_target(
    api,
    root: Path,
    slug: str,
    dedupe: str,
    occurred: datetime,
    explicit: Path | None,
) -> tuple[int, str, str]:
    if explicit is not None:
        target = Path(os.path.abspath(explicit))
        # The system may expose its temp root through a stable platform alias
        # (for example macOS /var -> /private/var). Trust only that root path;
        # every caller-supplied descendant is opened component-wise no-follow.
        temp_alias = Path(os.path.abspath(tempfile.gettempdir()))
        try:
            relative_parent = target.parent.relative_to(temp_alias)
        except ValueError:
            raise NotificationError("notification output must be under the system temporary directory")
        try:
            temp_root = temp_alias.resolve(strict=True)
            root_resolved = root.resolve(strict=True)
        except OSError:
            raise NotificationError("notification output parent is unavailable") from None
        if (
            temp_root == root_resolved
            or root_resolved in temp_root.parents
        ):
            raise NotificationError("notification output must be outside the repository")
        try:
            root_relative = root_resolved.relative_to(temp_root)
        except ValueError:
            root_relative = None
        if root_relative is not None and (
            relative_parent == root_relative or root_relative in relative_parent.parents
        ):
            raise NotificationError("notification output must be outside the repository")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(temp_root, flags)
        try:
            for component in relative_parent.parts:
                child = _open_child_directory(descriptor, component, create=False)
                os.close(descriptor)
                descriptor = child
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor, target.name, "external-temporary"
    descriptor = _open_overlay_directory(api, root, slug, output=True)
    output_key = f"{dedupe}\0{occurred.isoformat()}".encode()
    name = f"{hashlib.sha256(output_key).hexdigest()}.json"
    return descriptor, name, "selected-environment-overlay"


def deliver_file(
    api,
    root: Path,
    *,
    selected: dict,
    config: dict,
    config_raw: bytes,
    envelope: dict,
    now: datetime,
    explicit_output: Path | None,
    safety_guard,
) -> dict:
    if config["provider"] != "file":
        raise NotificationError("notification file delivery is not configured")
    state, state_raw = load_delivery_state(api, root, selected["slug"])
    decision = delivery_decision(config, state, envelope, now)
    if not decision["allowed"]:
        raise NotificationError("notification delivery is not allowed")
    safety_guard(root, persist=True)
    selected_again, config_again, config_raw_again = load_setup(api, root, selected["slug"])
    if selected_again["slug"] != selected["slug"] or config_again != config or config_raw_again != config_raw:
        raise NotificationError("notification setup changed; preserved")
    current_state, current_state_raw = load_delivery_state(api, root, selected["slug"])
    if current_state_raw != state_raw or current_state != state:
        raise NotificationError("notification delivery state changed; preserved")
    envelope_again = validate_envelope(
        api,
        envelope,
        allowed_hosts=frozenset(config["allowedHttpsHosts"]),
        root=root,
    )
    if envelope_again != envelope:
        raise NotificationError("notification source authority changed; preserved")
    output_parent, output_name, output_scope = _output_target(
        api,
        root,
        selected["slug"],
        envelope["dedupeKey"],
        now,
        explicit_output,
    )
    payload = {
        "destinationLabel": config["destinationLabel"],
        "owner": OWNER,
        "payload": format_provider("file", envelope),
        "provider": "file",
        "schemaVersion": SCHEMA_VERSION,
    }
    output_bytes = canonical_json(payload) + b"\n"
    try:
        identity = _create_exact_at(output_parent, output_name, output_bytes)
        try:
            rows = [
                row for row in state["deliveries"]
                if _timestamp(row["deliveredAt"]) >= now - timedelta(hours=168)
            ]
            rows.append({
                "category": envelope["category"],
                "dedupeDigest": hashlib.sha256(
                    envelope["dedupeKey"].encode()
                ).hexdigest(),
                "deliveredAt": now.isoformat(),
            })
            desired_state = canonical_json({"deliveries": rows[-MAX_STATE_ROWS:], "owner": OWNER, "schemaVersion": STATE_SCHEMA_VERSION}) + b"\n"
            state_rel = _overlay_rel(api, selected["slug"], STATE_NAME)
            _write_json_cas(api, root, state_rel, desired_state, state_raw, validate_state)
            try:
                output_again, output_info = api._read_migration_at(
                    output_parent, output_name
                )
            except FileNotFoundError:
                output_again = None
                output_info = None
            if (
                output_again != output_bytes
                or output_info is None
                or (output_info.st_dev, output_info.st_ino) != identity
            ):
                if state_raw is None:
                    _delete_json_cas(api, root, state_rel, desired_state)
                else:
                    _write_json_cas(
                        api,
                        root,
                        state_rel,
                        state_raw,
                        desired_state,
                        validate_state,
                    )
                raise NotificationError("notification output changed; preserved")
        except BaseException:
            if not _remove_created_at(output_parent, output_name, identity):
                raise NotificationError("notification transaction needs recovery") from None
            raise
    finally:
        os.close(output_parent)
    return {"delivered": True, "output": output_scope, "provider": "file"}


def read_input(path: str | None, stdin) -> object | None:
    if path is None:
        return None
    try:
        raw = stdin.buffer.read(MAX_INPUT_BYTES + 1) if path == "-" else Path(path).read_bytes()
    except OSError:
        raise NotificationError("notification input is unavailable") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise NotificationError("notification input is unavailable")
    try:
        return strict_json(raw)
    except NotificationError:
        raise NotificationError("notification input is invalid") from None


def _now(
    value: str | None, envelope: dict | None, *, delivery: bool = False
) -> datetime:
    if value is not None:
        return _timestamp(value)
    if delivery:
        return datetime.now(timezone.utc)
    if envelope is not None:
        return _timestamp(envelope["occurredAt"])
    return datetime.now(timezone.utc)


def command(api, root: Path, args, *, safety_guard=None, stdin=None) -> int:
    """CLI boundary. All errors are stable and redact payload/provider details."""
    stdin = stdin or __import__("sys").stdin
    safety_guard = safety_guard or api.require_remote_safety
    try:
        if args.setup:
            selected = _safe_selected(api, root, args.requested_env)
            rel = _overlay_rel(api, selected["slug"], CONFIG_NAME)
            prior, current = _read_optional(api, root, rel, limit=64 * 1024)
            if current is not None:
                validate_config(current)
            payload = setup_payload(args)
            safety_guard(root, persist=True)
            write_setup(api, root, selected, payload, prior)
            result = {"ready": True, "setup": "written", "testSendRequired": payload["provider"] in REAL_PROVIDERS}
        else:
            selected = _optional_selected(api, root, args.requested_env)
            if selected is None:
                config, config_raw = None, None
                if args.check or args.deliver_file:
                    raise NotificationError("notification environment is unavailable")
            else:
                rel = _overlay_rel(api, selected["slug"], CONFIG_NAME)
                config_raw, config_value = _read_optional(api, root, rel, limit=64 * 1024)
                config = None if config_value is None else validate_config(config_value)
            if args.check:
                if config is None:
                    raise NotificationError("notification setup is incomplete")
                state, _raw = load_delivery_state(api, root, selected["slug"])
                result = {
                    "categoriesEnabled": sorted(name for name, enabled in config["categories"].items() if enabled),
                    "destinationPrivate": config["privateDestinationAcknowledged"],
                    "provider": config["provider"],
                    "ready": (
                        config["privateDestinationAcknowledged"]
                        and config["provider"] not in REAL_PROVIDERS
                    ),
                    "stateRows": len(state["deliveries"]),
                    "testSendRequired": config["provider"] in REAL_PROVIDERS,
                }
            else:
                value = read_input(args.input, stdin)
                if value is None:
                    raise NotificationError("notification input is required")
                hosts = frozenset(config["allowedHttpsHosts"] if config else [])
                envelope = validate_envelope(api, value, allowed_hosts=hosts, root=root)
                provider = config["provider"] if config else "fake"
                state = empty_state()
                if config is not None:
                    state, _raw = load_delivery_state(api, root, selected["slug"])
                if args.deliver_file and args.now is not None:
                    raise NotificationError("notification delivery time cannot be overridden")
                policy_now = _now(
                    args.now, envelope, delivery=bool(args.deliver_file)
                )
                decision = (
                    delivery_decision(config, state, envelope, policy_now)
                    if config is not None
                    else {"allowed": False, "reasonCodes": ["setup-incomplete"], "retryDelaysSeconds": list(RETRY_DELAYS_SECONDS)}
                )
                result = {
                    "deliveryAvailable": provider in {"fake", "file"},
                    "direction": "push-only",
                    "envelope": envelope,
                    "inboundCallbacks": False,
                    "payload": format_provider(provider, envelope),
                    "policy": decision,
                    "provider": provider,
                    "schemaVersion": SCHEMA_VERSION,
                    "writesPerformed": False,
                }
                if args.deliver_file:
                    if selected is None or config is None or config_raw is None:
                        raise NotificationError("notification setup is incomplete")
                    if not args.approve_private_send:
                        raise NotificationError("notification delivery approval is required")
                    delivered = deliver_file(
                        api,
                        root,
                        selected=selected,
                        config=config,
                        config_raw=config_raw,
                        envelope=envelope,
                        now=policy_now,
                        explicit_output=args.output,
                        safety_guard=safety_guard,
                    )
                    result = {**result, **delivered, "writesPerformed": True}
    except (
        NotificationError,
        api.LinkMigrationError,
        api.RemoteSafetyError,
        OSError,
        KeyboardInterrupt,
    ):
        message = "notification operation failed safely"
        if args.json:
            print(json.dumps({"error": message}, indent=1, sort_keys=True))
        else:
            print(f"error: {message}", file=__import__("sys").stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        if args.setup:
            print("notification setup: written (no test sent)")
        elif args.check:
            print("notification setup: ready")
        else:
            print(f"notification plan: {result['provider']} ({'allowed' if result['policy']['allowed'] else 'blocked'})")
            if args.deliver_file:
                print("notification file delivery: written")
    if args.check and not result["ready"]:
        return 1
    return 0
