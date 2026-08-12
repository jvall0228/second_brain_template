"""Provider-neutral notification schema, privacy, policy, and writer tests."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain
import notifications


NOW = datetime(2026, 8, 11, 16, 0, tzinfo=timezone.utc)


def envelope(**changes) -> dict:
    value = {
        "artifact": None,
        "category": "validation",
        "dedupeKey": "validation.2026-08-11",
        "event": "vault.validation",
        "occurredAt": NOW.isoformat(),
        "privacyClass": "operational",
        "schemaVersion": 1,
        "severity": "warning",
        "sources": [
            {"label": "Validation report", "link": "00_Meta/STATUS.md"},
            {"label": "Issue", "link": "https://github.com/acme/brain/issues/21"},
        ],
        "summary": "Two bounded checks need attention.",
        "title": "Vault validation needs attention",
    }
    value.update(changes)
    return value


def external_envelope() -> dict:
    return envelope(
        sources=[
            {"label": "Issue", "link": "https://github.com/acme/brain/issues/21"}
        ]
    )


def config(**changes) -> dict:
    value = notifications.default_config()
    value.update(
        {
            "destinationLabel": "Private operations room",
            "privateDestinationAcknowledged": True,
            "provider": "file",
        }
    )
    value["categories"]["validation"] = True
    value.update(changes)
    return notifications.validate_config(value)


def args(**changes):
    value = {
        "allow_https_host": [],
        "approve_private_send": False,
        "check": False,
        "dedupe_hours": 24,
        "deliver_file": False,
        "destination_label": None,
        "enable_category": [],
        "input": None,
        "json": True,
        "now": None,
        "output": None,
        "private_destination_ack": False,
        "provider": None,
        "quiet_end": "07:00",
        "quiet_start": "22:00",
        "rate_limit": 6,
        "requested_env": None,
        "secret_env": None,
        "send_plan": False,
        "setup": False,
        "timezone": "America/New_York",
    }
    value.update(changes)
    return SimpleNamespace(**value)


def write_private(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="notifications-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_setup(self, value: dict | None = None) -> tuple[dict, bytes]:
        value = value or config()
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        output = directory / notifications.OUTBOX_DIR
        output.mkdir(mode=0o700)
        raw = notifications.canonical_json(value) + b"\n"
        write_private(directory / notifications.CONFIG_NAME, raw)
        return value, raw

    def selected(self) -> dict:
        return {"slug": "desk", "source": "cli", "state": "selected"}

    def assert_delivery_state_retained(self, overlay: Path, safe: dict) -> None:
        state = notifications.validate_state(
            json.loads((overlay / notifications.STATE_NAME).read_text())
        )
        self.assertEqual(len(state["deliveries"]), 1)
        self.assertEqual(
            state["deliveries"][0]["dedupeDigest"],
            notifications.hashlib.sha256(safe["dedupeKey"].encode()).hexdigest(),
        )

    def test_versioned_fixture_is_canonical_and_byte_deterministic(self):
        fixture = Path(__file__).parent / "fixtures" / "notifications-envelope-v1.json"
        value = json.loads(fixture.read_text(encoding="utf-8"))
        first = notifications.canonical_json(
            notifications.validate_envelope(brain, value)
        )
        second = notifications.canonical_json(
            notifications.validate_envelope(brain, json.loads(first))
        )
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), notifications.validate_envelope(brain, envelope()))

    def test_envelope_is_exact_and_centrally_redacts_sensitive_content(self):
        safe = notifications.validate_envelope(brain, external_envelope())
        self.assertEqual(safe["title"], "Vault validation needs attention")
        for mutation in (
            {"summary": "token=supersecretvalue"},
            {"title": "See (/private/tmp/owner.txt)"},
            {"title": r"See C:\\Users\\Owner\\secret.txt"},
            {"summary": "Open [details](https://example.com/private)"},
            {"summary": "<b>provider markup</b>"},
            {"title": "hello\x00world"},
            {"summary": "hello\x01world"},
            {"dedupeKey": "ghp_AAAAAAAAAAAAAAAAAAAA"},
            {"event": "xoxb-aaaaaaaaaa"},
            {"privacyClass": "restricted/private"},
            {"summary": "line one\n/home/owner/secret"},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(notifications.NotificationError):
                notifications.validate_envelope(brain, envelope(**mutation))
        extra = envelope()
        extra["unknown"] = True
        with self.assertRaises(notifications.NotificationError):
            notifications.validate_envelope(brain, extra)

    def test_links_are_narrow_and_tracking_free(self):
        for link in (
            "../secret.md",
            "/tmp/secret.md",
            "https://github.com/acme/brain/issues/21?token=secret",
            "http://github.com/acme/brain/issues/21",
            "https://example.com/path",
        ):
            candidate = envelope(sources=[{"label": "Source", "link": link}])
            with self.subTest(link=link), self.assertRaises(notifications.NotificationError):
                notifications.validate_envelope(brain, candidate)
        allowed = notifications.validate_envelope(
            brain,
            envelope(sources=[{"label": "Runbook", "link": "https://docs.example.com/runbook"}]),
            allowed_hosts=frozenset({"docs.example.com"}),
        )
        self.assertEqual(allowed["sources"][0]["link"], "https://docs.example.com/runbook")

    def test_relative_sources_must_be_tracked_public_authenticated_notes(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        public = self.root / "06_Resources" / "public.md"
        public.parent.mkdir()
        public.write_text(
            "---\ntitle: Public\ntags:\n  - type/reference\nupdated: 2026-08-11\n---\n\n# Public\n",
            encoding="utf-8",
        )
        restricted = self.root / "07_Archives" / "private.md"
        restricted.parent.mkdir()
        restricted.write_text(
            "---\ntitle: Private\ntags:\n  - restricted/private\nupdated: 2026-08-11\n---\n\n# Private\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "06_Resources/public.md", "07_Archives/private.md"],
            check=True,
        )
        value = envelope(sources=[{"label": "Public", "link": "06_Resources/public.md"}])
        self.assertEqual(
            notifications.validate_envelope(brain, value, root=self.root)["sources"][0]["link"],
            "06_Resources/public.md",
        )
        for link in ("07_Archives/private.md", "06_Resources/untracked.md"):
            with self.subTest(link=link), self.assertRaises(notifications.NotificationError):
                notifications.validate_envelope(
                    brain,
                    envelope(sources=[{"label": "Source", "link": link}]),
                    root=self.root,
                )

    def test_pure_formatters_have_text_fallback_safe_links_and_no_callbacks(self):
        safe = notifications.validate_envelope(brain, external_envelope())
        for provider in notifications.PROVIDERS:
            payload = notifications.format_provider(provider, safe)
            serialized = notifications.canonical_json(payload)
            self.assertLess(len(serialized), notifications.MAX_OUTPUT_BYTES)
            self.assertIn(b"Vault validation", serialized)
            self.assertNotIn(b"callback", serialized.lower())
            self.assertNotIn(b"http://", serialized)
        slack = notifications.format_provider("slack", safe)
        actions = [block for block in slack["blocks"] if block["type"] == "actions"]
        self.assertEqual(len(actions), 1)
        self.assertTrue(all(item["url"].startswith("https://") for item in actions[0]["elements"]))

    def test_categories_default_off_and_policy_is_deterministic(self):
        disabled = config(categories={name: False for name in notifications.CATEGORIES})
        safe = notifications.validate_envelope(brain, external_envelope())
        decision = notifications.delivery_decision(disabled, notifications.empty_state(), safe, NOW)
        self.assertEqual(decision["reasonCodes"], ["category-disabled"])
        state = notifications.empty_state()
        state["deliveries"] = [{
            "category": "validation",
            "dedupeDigest": notifications.hashlib.sha256(safe["dedupeKey"].encode()).hexdigest(),
            "deliveredAt": NOW.isoformat(),
        }]
        self.assertIn("duplicate", notifications.delivery_decision(config(), state, safe, NOW)["reasonCodes"])
        self.assertEqual(notifications.retry_delay(0, transient=True), 5)
        self.assertIsNone(notifications.retry_delay(0, transient=False))
        self.assertIsNone(notifications.retry_delay(3, transient=True))

    def test_quiet_hours_obey_timezone_and_dst(self):
        quiet = config()["quietHours"]
        self.assertFalse(notifications.in_quiet_hours(datetime.fromisoformat("2026-03-08T12:00:00+00:00"), quiet))
        self.assertTrue(notifications.in_quiet_hours(datetime.fromisoformat("2026-11-01T06:30:00+00:00"), quiet))

    def test_strict_config_and_state_reject_bools_unknowns_and_corruption(self):
        bad = config()
        bad["rateLimitPerHour"] = True
        with self.assertRaises(notifications.NotificationError):
            notifications.validate_config(bad)
        bad = config()
        bad["endpoint"] = "https://example.com/hook"
        with self.assertRaises(notifications.NotificationError):
            notifications.validate_config(bad)
        bad_state = notifications.empty_state()
        bad_state["queue"] = []
        with self.assertRaises(notifications.NotificationError):
            notifications.validate_state(bad_state)
        with self.assertRaises(notifications.NotificationError):
            notifications.strict_json(b'{"schemaVersion":1,"schemaVersion":1}')

    def test_config_rejects_path_labels_bad_hosts_and_unsafe_timezones(self):
        for change in (
            {"destinationLabel": "Room /private/tmp/owner"},
            {"destinationLabel": "ghp_AAAAAAAAAAAAAAAAAAAA"},
            {"allowedHttpsHosts": ["a..example.com"]},
            {"quietHours": {"end": "07:00", "start": "22:00", "timezone": "../../etc/passwd"}},
        ):
            with self.subTest(change=change), self.assertRaises(notifications.NotificationError):
                notifications.validate_config(config(**change))

    def test_timestamps_are_strict_and_bounded(self):
        for value in (
            "0001-01-01T00:00:00+00:00",
            "+02026-08-11T16:00:00+00:00",
            "2026-08-11 16:00:00+00:00",
            "2026-08-11T16:00:00+15:00",
        ):
            with self.subTest(value=value), self.assertRaises(notifications.NotificationError):
                notifications.validate_envelope(brain, external_envelope() | {"occurredAt": value})

    def test_fake_preview_requires_no_environment_and_performs_zero_writes(self):
        input_path = self.root / "envelope.json"
        preview = envelope(
            sources=[
                {"label": "Issue", "link": "https://github.com/acme/brain/issues/21"}
            ]
        )
        input_path.write_text(json.dumps(preview), encoding="utf-8")
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        output = io.StringIO()
        safety = mock.Mock(side_effect=AssertionError("remote safety must not run"))
        with contextlib.redirect_stdout(output):
            rc = notifications.command(brain, self.root, args(input=str(input_path)), safety_guard=safety)
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertEqual(rc, 0)
        self.assertEqual(before, after)
        self.assertEqual(json.loads(output.getvalue())["provider"], "fake")
        safety.assert_not_called()

    def test_invalid_or_ambiguous_environment_never_degrades_to_fake_preview(self):
        input_path = self.root / "envelope.json"
        input_path.write_text(json.dumps(external_envelope()), encoding="utf-8")
        for code in ("invalid-explicit", "ambiguous-fingerprint", "selector-invalid"):
            with self.subTest(code=code), mock.patch.object(
                brain,
                "select_environment",
                side_effect=brain.EnvironmentSelectionError(code),
            ), contextlib.redirect_stdout(io.StringIO()):
                rc = notifications.command(
                    brain,
                    self.root,
                    args(input=str(input_path), requested_env="desk"),
                    safety_guard=mock.Mock(),
                )
                self.assertEqual(rc, 1)

    def test_delivery_policy_uses_current_time_not_envelope_time(self):
        old = notifications.validate_envelope(
            brain, external_envelope() | {"occurredAt": "2020-01-01T12:00:00+00:00"}
        )
        preview_time = notifications._now(None, old)
        delivery_time = notifications._now(None, old, delivery=True)
        self.assertEqual(preview_time.year, 2020)
        self.assertNotEqual(delivery_time.year, 2020)

    def test_setup_calls_remote_safety_before_any_write(self):
        calls = []
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        overlay.mkdir(parents=True, mode=0o700)
        setup_args = args(
            setup=True,
            requested_env="desk",
            provider="file",
            destination_label="Private room",
            private_destination_ack=True,
            enable_category=["validation"],
        )
        with mock.patch.object(brain, "select_environment", return_value=self.selected()), contextlib.redirect_stdout(io.StringIO()):
            rc = notifications.command(
                brain,
                self.root,
                setup_args,
                safety_guard=lambda root, persist: calls.append((persist, (root / ".second-brain").exists())),
            )
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [(True, True)])
        path = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.CONFIG_NAME
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_setup_can_compare_and_swap_an_existing_valid_config(self):
        self.write_setup()
        setup_args = args(
            setup=True,
            requested_env="desk",
            provider="file",
            destination_label="Replacement private room",
            private_destination_ack=True,
            enable_category=["maintenance"],
        )
        with mock.patch.object(brain, "select_environment", return_value=self.selected()), contextlib.redirect_stdout(io.StringIO()):
            rc = notifications.command(
                brain, self.root, setup_args,
                safety_guard=lambda *_args, **_kwargs: None,
            )
        self.assertEqual(rc, 0)
        path = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.CONFIG_NAME
        self.assertEqual(json.loads(path.read_text())["destinationLabel"], "Replacement private room")

    def test_machine_local_config_and_state_require_bounded_private_regular_files(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        cases = (
            (
                notifications.CONFIG_NAME,
                notifications.MAX_CONFIG_BYTES,
                notifications.canonical_json(config()) + b"\n",
            ),
            (
                notifications.STATE_NAME,
                notifications.MAX_STATE_BYTES,
                notifications.canonical_json(notifications.empty_state()) + b"\n",
            ),
        )
        for name, limit, valid in cases:
            rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{name}"
            path = directory / name
            with self.subTest(name=name, attack="mode"):
                path.write_bytes(valid)
                path.chmod(0o644)
                with self.assertRaises(notifications.NotificationError):
                    notifications._read_optional(brain, self.root, rel, limit=limit)
                path.unlink()
            with self.subTest(name=name, attack="fifo"):
                os.mkfifo(path, 0o600)
                with self.assertRaises(notifications.NotificationError):
                    notifications._read_optional(brain, self.root, rel, limit=limit)
                path.unlink()
            with self.subTest(name=name, attack="oversize"):
                write_private(path, b"x" * (limit + 1))
                with mock.patch.object(
                    notifications.os,
                    "read",
                    side_effect=AssertionError("oversized local state must not be read"),
                ):
                    with self.assertRaises(notifications.NotificationError):
                        notifications._read_optional(brain, self.root, rel, limit=limit)
                path.unlink()
            with self.subTest(name=name, attack="control"):
                write_private(path, valid)
                raw, value = notifications._read_optional(
                    brain, self.root, rel, limit=limit
                )
                self.assertEqual(raw, valid)
                self.assertIsInstance(value, dict)
                path.unlink()

    def test_private_state_and_directories_require_current_user_ownership(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.CONFIG_NAME}"
        raw = notifications.canonical_json(config()) + b"\n"
        write_private(directory / notifications.CONFIG_NAME, raw)
        with mock.patch.object(notifications, "_private_owned", return_value=False):
            with self.assertRaises(notifications.NotificationError):
                notifications._read_optional(
                    brain, self.root, rel, limit=notifications.MAX_CONFIG_BYTES
                )
            parent = os.open(
                directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            )
            try:
                with self.assertRaises(notifications.NotificationError):
                    notifications._open_child_directory(
                        parent, "missing", create=False, private=True
                    )
            finally:
                os.close(parent)
        if hasattr(os, "geteuid"):
            with mock.patch.object(os, "geteuid", return_value=1000):
                self.assertFalse(
                    notifications._private_owned(SimpleNamespace(st_uid=1001))
                )

    def test_private_directory_creation_is_never_attempted(self):
        directory = self.root / "directory-race"
        directory.mkdir()
        parent = os.open(
            directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            with mock.patch.object(
                notifications.os,
                "mkdir",
                side_effect=AssertionError("private directory must not be created"),
            ):
                with self.assertRaises(notifications.NotificationError):
                    notifications._open_child_directory(
                        parent, "private", create=True, private=True
                    )
        finally:
            os.close(parent)
        self.assertFalse((directory / "private").exists())

    def test_state_cas_refuses_fifo_and_oversize_without_staging(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        path = directory / notifications.STATE_NAME
        desired = notifications.canonical_json(notifications.empty_state()) + b"\n"
        os.mkfifo(path, 0o600)
        with self.assertRaises(notifications.NotificationError):
            notifications._write_json_cas(
                brain,
                self.root,
                rel,
                desired,
                None,
                notifications.validate_state,
            )
        path.unlink()
        write_private(path, b"x" * (notifications.MAX_STATE_BYTES + 1))
        real_read = notifications.os.read

        def reject_oversized_read(descriptor, size):
            if os.fstat(descriptor).st_size > notifications.MAX_STATE_BYTES:
                raise AssertionError("oversized state must not be read")
            return real_read(descriptor, size)

        with mock.patch.object(
            notifications.os, "read", side_effect=reject_oversized_read
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications._write_json_cas(
                    brain,
                    self.root,
                    rel,
                    desired,
                    None,
                    notifications.validate_state,
                )
        self.assertEqual(
            list(directory.glob(f".{notifications.STATE_NAME}.migrate-new-*")), []
        )

    def test_blocked_remote_safety_means_zero_file_and_state_writes(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        def blocked(_root, *, persist):
            self.assertTrue(persist)
            raise brain.RemoteSafetyError(
                {"reasonCodes": ["local-only"], "state": "blocked"}
            )
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(brain.RemoteSafetyError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=blocked,
                )
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assertEqual(
            sorted(path.name for path in overlay.iterdir()),
            [notifications.OUTBOX_DIR, notifications.CONFIG_NAME],
        )

    def test_file_delivery_is_local_private_and_deduplicated(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        guard = mock.Mock()
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            result = notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                envelope=safe, now=NOW, explicit_output=None, safety_guard=guard,
            )
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=guard,
                )
        self.assertEqual(result["output"], "selected-environment-overlay")
        guard.assert_called_once_with(self.root, persist=True)
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        serialized = output.read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("webhook", serialized.casefold())
        state = (overlay / notifications.STATE_NAME).read_text(encoding="utf-8")
        self.assertNotIn(safe["title"], state)
        self.assertNotIn(safe["summary"], state)
        self.assertNotIn(current["destinationLabel"], state)
        self.assertNotIn("queue", state)

    def test_repeat_delivery_after_dedupe_window_uses_a_new_output_name(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                envelope=safe, now=NOW, explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
            _selected, refreshed, refreshed_raw = notifications.load_setup(
                brain, self.root, "desk"
            )
            notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=refreshed, config_raw=refreshed_raw,
                envelope=safe, now=NOW + notifications.timedelta(hours=169), explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
            _selected, refreshed, refreshed_raw = notifications.load_setup(
                brain, self.root, "desk"
            )
            notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=refreshed, config_raw=refreshed_raw,
                envelope=safe, now=NOW + notifications.timedelta(hours=338), explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        self.assertEqual(len(list(output_dir.iterdir())), 3)

    def test_explicit_temporary_file_delivery_succeeds_without_repo_write(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with tempfile.TemporaryDirectory(prefix="notification-output-") as outdir, mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ):
            target = Path(outdir) / "notification.json"
            result = notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                envelope=safe, now=NOW, explicit_output=target,
                safety_guard=lambda *_args, **_kwargs: None,
            )
            self.assertEqual(result["output"], "external-temporary")
            self.assertTrue(target.is_file())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_explicit_temporary_output_failure_reserves_dedupe_before_retry(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with tempfile.TemporaryDirectory(prefix="notification-output-") as outdir:
            first = Path(outdir) / "one.json"
            second = Path(outdir) / "two.json"
            with mock.patch.object(
                brain, "select_environment", return_value=self.selected()
            ), mock.patch.object(
                notifications, "_create_exact_at", side_effect=KeyboardInterrupt
            ):
                with self.assertRaises(notifications.NotificationError):
                    notifications.deliver_file(
                        brain, self.root, selected=self.selected(), config=current,
                        config_raw=raw, envelope=safe, now=NOW,
                        explicit_output=first,
                        safety_guard=lambda *_args, **_kwargs: None,
                    )
            guard = mock.Mock()
            with mock.patch.object(
                brain, "select_environment", return_value=self.selected()
            ):
                with self.assertRaises(notifications.NotificationError):
                    notifications.deliver_file(
                        brain, self.root, selected=self.selected(), config=current,
                        config_raw=raw, envelope=safe,
                        now=NOW + notifications.timedelta(seconds=1),
                        explicit_output=second, safety_guard=guard,
                    )
            guard.assert_not_called()
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())

    def test_concurrent_same_dedupe_serializes_before_output_publication(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._write_json_cas
        barrier = threading.Barrier(2)
        outcomes = []

        def synchronized(*call_args, **call_kwargs):
            if call_args[2].endswith(notifications.STATE_NAME):
                barrier.wait(timeout=5)
            return real(*call_args, **call_kwargs)

        def deliver(offset):
            try:
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current,
                    config_raw=raw, envelope=safe,
                    now=NOW + notifications.timedelta(seconds=offset),
                    explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
                outcomes.append("success")
            except notifications.NotificationError:
                outcomes.append("blocked")

        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ), mock.patch.object(
            notifications, "_write_json_cas", side_effect=synchronized
        ):
            threads = [threading.Thread(target=deliver, args=(offset,)) for offset in (0, 1)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(outcomes), ["blocked", "success"])
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        output_dir = overlay / notifications.OUTBOX_DIR
        self.assertEqual(len(list(output_dir.iterdir())), 1)
        self.assertEqual(
            list(overlay.glob(f".{notifications.STATE_NAME}.migrate-new-*")), []
        )
        self.assertEqual(
            len(list(overlay.glob(f".{notifications.STATE_NAME}.migrate-old-*"))),
            1,
        )
        different = notifications.validate_envelope(
            brain,
            external_envelope()
            | {
                "dedupeKey": "validation.2026-08-11.followup",
                "event": "vault.validation.followup",
            },
        )
        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ):
            notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current,
                config_raw=raw, envelope=different,
                now=NOW + notifications.timedelta(seconds=2),
                explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
        self.assertEqual(len(list(output_dir.iterdir())), 2)

    def test_state_claim_serializes_burst_without_generation_overflow(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        desired = notifications.canonical_json(notifications.empty_state()) + b"\n"
        stage_entered = threading.Event()
        release_stage = threading.Event()
        real_stage = notifications._stage_exact
        outcomes = []

        def held_stage(*call_args, **call_kwargs):
            stage_entered.set()
            self.assertTrue(release_stage.wait(timeout=10))
            return real_stage(*call_args, **call_kwargs)

        def write_state():
            try:
                notifications._write_json_cas(
                    brain,
                    self.root,
                    rel,
                    desired,
                    None,
                    notifications.validate_state,
                )
                outcomes.append("success")
            except notifications.NotificationError:
                outcomes.append("blocked")

        with mock.patch.object(
            notifications, "_stage_exact", side_effect=held_stage
        ):
            winner = threading.Thread(target=write_state)
            winner.start()
            self.assertTrue(stage_entered.wait(timeout=10))
            contenders = [threading.Thread(target=write_state) for _ in range(33)]
            for contender in contenders:
                contender.start()
            for contender in contenders:
                contender.join(timeout=10)
            self.assertTrue(all(not contender.is_alive() for contender in contenders))
            release_stage.set()
            winner.join(timeout=10)
            self.assertFalse(winner.is_alive())

        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("blocked"), 33)
        self.assertEqual(
            list(directory.glob(f".{notifications.STATE_NAME}.migrate-new-*")),
            [],
        )
        self.assertFalse(
            (directory / f".{notifications.STATE_NAME}.notify-claim").exists()
        )
        self.assertEqual(
            len(list(directory.glob(f".{notifications.STATE_NAME}.migrate-old-*"))),
            1,
        )
        self.assertEqual(
            notifications.load_delivery_state(brain, self.root, "desk")[0],
            notifications.empty_state(),
        )

    def test_claim_retirement_failure_blocks_success_and_preserves_evidence(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        guard = mock.Mock()
        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ), mock.patch.object(
            notifications, "_retire_cas_claim", return_value=False
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain,
                    self.root,
                    selected=self.selected(),
                    config=current,
                    config_raw=raw,
                    envelope=safe,
                    now=NOW,
                    explicit_output=None,
                    safety_guard=guard,
                )
        guard.assert_called_once()
        self.assertEqual(
            list((overlay / notifications.OUTBOX_DIR).iterdir()), []
        )
        self.assertTrue(
            (overlay / f".{notifications.STATE_NAME}.notify-claim").is_file()
        )
        self.assert_delivery_state_retained(overlay, safe)

        later_guard = mock.Mock()
        different = notifications.validate_envelope(
            brain,
            external_envelope()
            | {
                "dedupeKey": "validation.2026-08-11.followup",
                "event": "vault.validation.followup",
            },
        )
        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain,
                    self.root,
                    selected=self.selected(),
                    config=current,
                    config_raw=raw,
                    envelope=different,
                    now=NOW + notifications.timedelta(seconds=1),
                    explicit_output=None,
                    safety_guard=later_guard,
                )
        later_guard.assert_not_called()

    def test_output_parent_rename_after_state_reservation_is_refused(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        output_dir = overlay / notifications.OUTBOX_DIR
        moved = overlay / "moved-output"
        real = notifications._write_json_cas
        swapped = False

        def reserve_then_swap(*call_args, **call_kwargs):
            nonlocal swapped
            result = real(*call_args, **call_kwargs)
            if call_args[2].endswith(notifications.STATE_NAME) and not swapped:
                output_dir.rename(moved)
                output_dir.mkdir(mode=0o700)
                swapped = True
            return result

        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ), mock.patch.object(
            notifications, "_write_json_cas", side_effect=reserve_then_swap
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current,
                    config_raw=raw, envelope=safe, now=NOW,
                    explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertTrue(swapped)
        self.assertEqual(list(output_dir.iterdir()), [])
        self.assertEqual(list(moved.iterdir()), [])
        self.assert_delivery_state_retained(overlay, safe)

    def test_output_parent_rename_after_creation_is_refused_with_evidence(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        output_dir = overlay / notifications.OUTBOX_DIR
        moved = overlay / "moved-output"
        real = notifications._create_exact_at

        def create_then_swap(parent, name, data):
            identity = real(parent, name, data)
            output_dir.rename(moved)
            output_dir.mkdir(mode=0o700)
            return identity

        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ), mock.patch.object(
            notifications, "_create_exact_at", side_effect=create_then_swap
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current,
                    config_raw=raw, envelope=safe, now=NOW,
                    explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertEqual(list(output_dir.iterdir()), [])
        self.assertEqual(len(list(moved.iterdir())), 1)
        self.assert_delivery_state_retained(overlay, safe)

    def test_output_creation_failure_preserves_state_reservation(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_create_exact_at", side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=lambda *_args, **_kwargs: None,
                )
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        self.assertEqual(list(output_dir.iterdir()), [])
        self.assert_delivery_state_retained(
            self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk", safe
        )

    def test_failed_delivery_blocks_later_automatic_retry_for_same_dedupe(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ), mock.patch.object(
            notifications, "_create_exact_at", side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain,
                    self.root,
                    selected=self.selected(),
                    config=current,
                    config_raw=raw,
                    envelope=safe,
                    now=NOW,
                    explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        guard = mock.Mock()
        with mock.patch.object(
            brain, "select_environment", return_value=self.selected()
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain,
                    self.root,
                    selected=self.selected(),
                    config=current,
                    config_raw=raw,
                    envelope=safe,
                    now=NOW + notifications.timedelta(seconds=1),
                    explicit_output=None,
                    safety_guard=guard,
                )
        guard.assert_not_called()
        output_dir = (
            self.root
            / brain.ENVIRONMENT_OVERLAYS_RELPATH
            / "desk"
            / notifications.OUTBOX_DIR
        )
        self.assertEqual(list(output_dir.iterdir()), [])
        self.assert_delivery_state_retained(
            self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk", safe
        )

    def test_late_same_inode_output_mutation_preserves_recovery_state(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._create_exact_at

        def create_then_mutate(parent, name, data):
            identity = real(parent, name, data)
            output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
            output = next(output_dir.iterdir())
            original_identity = (output.stat().st_dev, output.stat().st_ino)
            output.write_bytes(b"foreign-output")
            self.assertEqual(
                (output.stat().st_dev, output.stat().st_ino), original_identity
            )
            return identity

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_create_exact_at", side_effect=create_then_mutate
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertEqual(output.read_bytes(), b"foreign-output")

    def test_late_output_path_replacement_preserves_recovery_state(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._create_exact_at
        held = []

        def create_then_replace(parent, name, data):
            identity = real(parent, name, data)
            output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
            output = next(output_dir.iterdir())
            held.append(output.open("rb"))
            output.unlink()
            output.write_bytes(b"foreign-output")
            return identity

        try:
            with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
                notifications, "_create_exact_at", side_effect=create_then_replace
            ):
                with self.assertRaises(notifications.NotificationError):
                    notifications.deliver_file(
                        brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                        envelope=safe, now=NOW, explicit_output=None,
                        safety_guard=lambda *_args, **_kwargs: None,
                    )
        finally:
            for descriptor in held:
                descriptor.close()
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertEqual(output.read_bytes(), b"foreign-output")

    def test_late_output_symlink_preserves_state_and_target(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._create_exact_at
        foreign = self.root / "foreign-output"
        foreign.write_bytes(b"foreign-target")

        def create_then_replace(parent, name, data):
            identity = real(parent, name, data)
            output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
            output = next(output_dir.iterdir())
            output.unlink()
            output.symlink_to(foreign)
            return identity

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_create_exact_at", side_effect=create_then_replace
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertTrue(output.is_symlink())
        self.assertEqual(foreign.read_bytes(), b"foreign-target")

    def test_late_output_mode_change_preserves_recovery_state(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._create_exact_at

        def create_then_chmod(parent, name, data):
            identity = real(parent, name, data)
            output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
            next(output_dir.iterdir()).chmod(0o644)
            return identity

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_create_exact_at", side_effect=create_then_chmod
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertEqual(output.stat().st_mode & 0o777, 0o644)

    def test_late_output_fifo_preserves_recovery_state_without_blocking(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._create_exact_at

        def create_then_fifo(parent, name, data):
            identity = real(parent, name, data)
            output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
            output = next(output_dir.iterdir())
            output.unlink()
            os.mkfifo(output, 0o600)
            return identity

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_create_exact_at", side_effect=create_then_fifo
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertTrue(stat.S_ISFIFO(output.lstat().st_mode))

    def test_late_oversized_output_preserves_recovery_state_without_reading(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real_write = notifications._create_exact_at
        real_read = notifications.os.read
        foreign_descriptor = None

        def create_then_oversize(parent, name, data):
            identity = real_write(parent, name, data)
            output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
            output = next(output_dir.iterdir())
            output.unlink()
            output.write_bytes(b"x" * (notifications.MAX_OUTPUT_BYTES + 1))
            output.chmod(0o600)
            return identity

        def reject_oversized_read(descriptor, size):
            nonlocal foreign_descriptor
            info = os.fstat(descriptor)
            if info.st_size > notifications.MAX_OUTPUT_BYTES:
                foreign_descriptor = descriptor
                raise AssertionError("oversized foreign output must not be read")
            return real_read(descriptor, size)

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_create_exact_at", side_effect=create_then_oversize
        ), mock.patch.object(notifications.os, "read", side_effect=reject_oversized_read):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertIsNone(foreign_descriptor)
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertEqual(output.stat().st_size, notifications.MAX_OUTPUT_BYTES + 1)

    def test_missing_private_output_directory_fails_closed_without_creation(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        output_dir.rmdir()
        previous = os.umask(0o777)
        try:
            with mock.patch.object(brain, "select_environment", return_value=self.selected()):
                with self.assertRaises(notifications.NotificationError):
                    notifications.deliver_file(
                        brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                        envelope=safe, now=NOW, explicit_output=None,
                        safety_guard=lambda *_args, **_kwargs: None,
                    )
        finally:
            os.umask(previous)
        self.assertFalse(output_dir.exists())
        self.assertFalse(
            output_dir.parent.joinpath(notifications.STATE_NAME).exists()
        )

    def test_create_fsync_failure_preserves_same_inode_foreign_rewrite(self):
        directory = self.root / "create-failure"
        directory.mkdir()
        parent = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        output = directory / "notification.json"
        injected = False

        def mutate_then_fail(descriptor):
            nonlocal injected
            if descriptor != parent and not injected:
                injected = True
                identity = (output.stat().st_dev, output.stat().st_ino)
                output.write_bytes(b"foreign-during-create")
                self.assertEqual(
                    (output.stat().st_dev, output.stat().st_ino), identity
                )
                raise OSError("file durability failure")
            return None

        try:
            with mock.patch.object(
                notifications.os, "fsync", side_effect=mutate_then_fail
            ):
                with self.assertRaises(OSError):
                    notifications._create_exact_at(
                        parent, output.name, b"owned-output"
                    )
        finally:
            os.close(parent)
        self.assertEqual(output.read_bytes(), b"foreign-during-create")
        self.assertEqual([item.name for item in directory.iterdir()], [output.name])

    def test_output_parent_fsync_failure_preserves_output_and_state_reservation(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        real_fsync = notifications.os.fsync
        output_parent = None
        injected = False

        def fail_output_parent(descriptor):
            nonlocal output_parent, injected
            try:
                descriptor_info = os.fstat(descriptor)
                directory_info = output_dir.stat()
            except OSError:
                return real_fsync(descriptor)
            if (
                not injected
                and stat.S_ISDIR(descriptor_info.st_mode)
                and (descriptor_info.st_dev, descriptor_info.st_ino)
                == (directory_info.st_dev, directory_info.st_ino)
            ):
                output_parent = descriptor
                injected = True
                raise OSError("output-directory durability failure")
            return real_fsync(descriptor)

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications.os, "fsync", side_effect=fail_output_parent
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertTrue(injected)
        self.assertIsNotNone(output_parent)
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assert_delivery_state_retained(overlay, safe)
        outputs = list(output_dir.iterdir())
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].stat().st_mode & 0o777, 0o600)

    def test_state_stage_fsync_failure_preserves_recovery_evidence(self):
        directory = self.root / "stage-failure"
        directory.mkdir()
        parent = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        injected = False

        def mutate_then_fail(descriptor):
            nonlocal injected
            if descriptor != parent and not injected:
                injected = True
                stages = list(directory.iterdir())
                self.assertEqual(len(stages), 1)
                identity = (stages[0].stat().st_dev, stages[0].stat().st_ino)
                stages[0].write_bytes(b"foreign-during-stage")
                self.assertEqual(
                    (stages[0].stat().st_dev, stages[0].stat().st_ino), identity
                )
                raise OSError("stage durability failure")
            return None

        try:
            with mock.patch.object(
                notifications.os, "fsync", side_effect=mutate_then_fail
            ):
                with self.assertRaises(OSError):
                    notifications._stage_exact(
                        brain, parent, notifications.STATE_NAME, b"owned-state"
                    )
        finally:
            os.close(parent)
        stages = list(directory.iterdir())
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].read_bytes(), b"foreign-during-stage")

    def test_unfinished_update_stage_blocks_followup_operation(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        old = notifications.canonical_json(notifications.empty_state()) + b"\n"
        write_private(directory / notifications.STATE_NAME, old)
        desired_state = notifications.empty_state()
        desired_state["deliveries"] = [
            {
                "category": "validation",
                "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(),
                "deliveredAt": NOW.isoformat(),
            }
        ]
        desired = notifications.canonical_json(desired_state) + b"\n"
        real_fsync = notifications.os.fsync
        stage_fsync_seen = False

        def fail_stage_fsync(descriptor):
            nonlocal stage_fsync_seen
            info = os.fstat(descriptor)
            if stat.S_ISREG(info.st_mode) and info.st_size == len(desired):
                stage_fsync_seen = True
                raise OSError("stage durability failure")
            return real_fsync(descriptor)

        with mock.patch.object(
            notifications.os, "fsync", side_effect=fail_stage_fsync
        ):
            with self.assertRaises(OSError):
                notifications._write_json_cas(
                    brain,
                    self.root,
                    rel,
                    desired,
                    old,
                    notifications.validate_state,
                )
        self.assertTrue(stage_fsync_seen)
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), old)
        self.assertEqual(
            len(list(directory.glob(f".{notifications.STATE_NAME}.migrate-new-*"))),
            1,
        )
        with self.assertRaises(notifications.NotificationError):
            notifications.load_delivery_state(brain, self.root, "desk")
        with self.assertRaises(notifications.NotificationError):
            notifications._write_json_cas(
                brain,
                self.root,
                rel,
                desired,
                old,
                notifications.validate_state,
            )

    def test_recovery_authentication_is_bounded_and_refuses_fifo(self):
        directory = self.root / "output-auth"
        directory.mkdir()
        parent = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            fifo = directory / "foreign.fifo"
            os.mkfifo(fifo, 0o600)
            self.assertFalse(
                notifications._owned_output_at(
                    brain, parent, fifo.name, (fifo.stat().st_dev, fifo.stat().st_ino), b""
                )
            )
            large = directory / "foreign.json"
            large.write_bytes(b"x" * (notifications.MAX_OUTPUT_BYTES + 1))
            large.chmod(0o600)
            identity = (large.stat().st_dev, large.stat().st_ino)
            with mock.patch.object(
                notifications.os,
                "read",
                side_effect=AssertionError("oversized foreign content must not be read"),
            ):
                self.assertFalse(
                    notifications._owned_output_at(
                        brain, parent, large.name, identity, b"owned"
                    )
                )
        finally:
            os.close(parent)

    def test_output_symlink_and_casefold_occupants_are_preserved(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        foreign = self.root / "foreign"
        foreign.mkdir()
        (overlay / notifications.OUTBOX_DIR).rmdir()
        (overlay / notifications.OUTBOX_DIR).symlink_to(foreign, target_is_directory=True)
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertEqual(list(foreign.iterdir()), [])

    def test_casefold_output_occupant_blocks_without_overwrite(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        key = f"{safe['dedupeKey']}\0{NOW.isoformat()}".encode()
        dedupe = notifications.hashlib.sha256(safe["dedupeKey"].encode()).hexdigest()
        expected = f"{dedupe}-{notifications.hashlib.sha256(key).hexdigest()}.json"
        occupant = output_dir / expected.upper()
        occupant.write_bytes(b"foreign")
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertEqual(occupant.read_bytes(), b"foreign")

    def test_corrupt_state_fails_before_remote_guard_or_output(self):
        current, raw = self.write_setup()
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        write_private(overlay / notifications.STATE_NAME, b"{bad")
        safe = notifications.validate_envelope(brain, external_envelope())
        guard = mock.Mock()
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=guard,
                )
        guard.assert_not_called()
        self.assertEqual(list((overlay / notifications.OUTBOX_DIR).iterdir()), [])

    def test_generation_count_cap_blocks_before_remote_guard_or_output(self):
        current, raw = self.write_setup()
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        state_raw = notifications.canonical_json(notifications.empty_state()) + b"\n"
        write_private(overlay / notifications.STATE_NAME, state_raw)
        for index in range(notifications.MAX_TRANSACTION_GENERATIONS):
            generation = (
                overlay
                / f".{notifications.STATE_NAME}.migrate-old-{index:024x}"
            )
            write_private(generation, state_raw)
        guard = mock.Mock()
        safe = notifications.validate_envelope(brain, external_envelope())
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain,
                    self.root,
                    selected=self.selected(),
                    config=current,
                    config_raw=raw,
                    envelope=safe,
                    now=NOW,
                    explicit_output=None,
                    safety_guard=guard,
                )
        guard.assert_not_called()
        self.assertEqual(list((overlay / notifications.OUTBOX_DIR).iterdir()), [])

    def test_generation_byte_cap_accounts_for_pending_transaction(self):
        directory = self.root / "generation-cap"
        directory.mkdir()
        parent = os.open(
            directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            generation = (
                directory
                / f".{notifications.STATE_NAME}.migrate-old-{'0' * 24}"
            )
            generation_bytes = (
                notifications.canonical_json(notifications.empty_state()) + b"\n"
            )
            write_private(generation, generation_bytes)
            with mock.patch.object(
                notifications,
                "MAX_TRANSACTION_GENERATION_BYTES",
                len(generation_bytes) + 2,
            ):
                with self.assertRaises(notifications.NotificationError):
                    notifications._require_generation_capacity(
                        parent,
                        notifications.STATE_NAME,
                        limit=notifications.MAX_STATE_BYTES,
                        additional_count=1,
                        additional_bytes=3,
                    )
        finally:
            os.close(parent)

    def test_state_update_preserves_late_foreign_replacement(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        old = notifications.canonical_json(notifications.empty_state()) + b"\n"
        write_private(directory / notifications.STATE_NAME, old)
        desired_state = copy.deepcopy(notifications.empty_state())
        desired_state["deliveries"].append(
            {"category": "validation", "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(), "deliveredAt": NOW.isoformat()}
        )
        desired = notifications.canonical_json(desired_state) + b"\n"
        real = notifications._quarantine_no_replace
        def replace_then_quarantine(api, parent, name, backup):
            os.unlink(name, dir_fd=parent)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent)
            os.write(fd, b"foreign")
            os.close(fd)
            real(api, parent, name, backup)
        with mock.patch.object(notifications, "_quarantine_no_replace", side_effect=replace_then_quarantine):
            with self.assertRaises(notifications.NotificationError):
                notifications._write_json_cas(brain, self.root, rel, desired, old, notifications.validate_state)
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), b"foreign")
        stages = list(directory.glob(".notification-state.json.migrate-new-*"))
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].read_bytes(), desired)

    def test_state_quarantine_refuses_concurrent_backup_occupant(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        old = notifications.canonical_json(notifications.empty_state()) + b"\n"
        write_private(directory / notifications.STATE_NAME, old)
        desired_state = notifications.empty_state()
        desired_state["deliveries"].append(
            {
                "category": "validation",
                "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(),
                "deliveredAt": NOW.isoformat(),
            }
        )
        desired = notifications.canonical_json(desired_state) + b"\n"
        real = notifications._quarantine_no_replace
        inserted = []

        def occupy_then_quarantine(api, parent, name, backup):
            descriptor = os.open(
                backup,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=parent,
            )
            os.write(descriptor, b"foreign-backup")
            os.close(descriptor)
            inserted.append(backup)
            real(api, parent, name, backup)

        with mock.patch.object(
            notifications,
            "_quarantine_no_replace",
            side_effect=occupy_then_quarantine,
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications._write_json_cas(
                    brain,
                    self.root,
                    rel,
                    desired,
                    old,
                    notifications.validate_state,
                )
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), old)
        self.assertEqual(len(inserted), 1)
        self.assertEqual((directory / inserted[0]).read_bytes(), b"foreign-backup")
        stages = list(directory.glob(".notification-state.json.migrate-new-*"))
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].read_bytes(), desired)

    def test_successful_state_update_retains_prior_generation(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        old = notifications.canonical_json(notifications.empty_state()) + b"\n"
        write_private(directory / notifications.STATE_NAME, old)
        new_state = notifications.empty_state()
        new_state["deliveries"] = [
            {"category": "validation", "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(), "deliveredAt": NOW.isoformat()}
        ]
        desired = notifications.canonical_json(new_state) + b"\n"
        notifications._write_json_cas(
            brain, self.root, rel, desired, old, notifications.validate_state
        )
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), desired)
        backups = list(directory.glob(".notification-state.json.migrate-old-*"))
        self.assertEqual(len(backups), 2)
        self.assertTrue(all(path.read_bytes() == old for path in backups))
        self.assertEqual(
            notifications.load_delivery_state(brain, self.root, "desk")[0],
            notifications.validate_state(new_state),
        )

    def test_state_publish_fsync_failure_preserves_public_state(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        new_state = notifications.empty_state()
        new_state["deliveries"] = [
            {
                "category": "validation",
                "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(),
                "deliveredAt": NOW.isoformat(),
            }
        ]
        desired = notifications.canonical_json(new_state) + b"\n"
        real_rename = brain._rename_external_at
        real_fsync = notifications.os.fsync
        published = False
        injected = False

        def mark_publish(descriptor, source, target, *, exchange=False):
            nonlocal published
            result = real_rename(
                descriptor, source, target, exchange=exchange
            )
            if target == notifications.STATE_NAME:
                published = True
            return result

        def fail_after_publish(descriptor):
            nonlocal injected
            if published and not injected:
                injected = True
                raise OSError("state-directory durability failure")
            return real_fsync(descriptor)

        with mock.patch.object(
            brain, "_rename_external_at", side_effect=mark_publish
        ), mock.patch.object(
            notifications.os, "fsync", side_effect=fail_after_publish
        ):
            with self.assertRaises(OSError):
                notifications._write_json_cas(
                    brain,
                    self.root,
                    rel,
                    desired,
                    None,
                    notifications.validate_state,
                )
        self.assertTrue(injected)
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), desired)
        self.assertEqual(
            list(directory.glob(".notification-state.json.migrate-new-*")), []
        )

    def test_successful_delivery_consumes_stage_and_blocks_duplicate(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            result = notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                envelope=safe, now=NOW, explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertTrue(result["delivered"])
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assertEqual(len(list((overlay / notifications.OUTBOX_DIR).iterdir())), 1)
        self.assertEqual(
            list(overlay.glob(f".{notifications.STATE_NAME}.migrate-new-*")), []
        )
        state = notifications.validate_state(
            json.loads((overlay / notifications.STATE_NAME).read_text())
        )
        self.assertEqual(
            state["deliveries"][0]["dedupeDigest"],
            notifications.hashlib.sha256(safe["dedupeKey"].encode()).hexdigest(),
        )

    def test_orphan_transaction_evidence_blocks_missing_state_as_recovery(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        residue = directory / (
            f".{notifications.STATE_NAME}.migrate-old-{'d' * 24}"
        )
        write_private(
            residue,
            notifications.canonical_json(notifications.empty_state()) + b"\n",
        )
        with self.assertRaises(notifications.NotificationError):
            notifications.load_delivery_state(brain, self.root, "desk")
        self.assertTrue(residue.exists())

    def test_external_output_is_confined_to_real_temporary_parent(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        outside = self.root / "output.json"
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=outside,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        self.assertFalse(outside.exists())

    def test_symlinked_temporary_root_can_never_point_output_into_repository(self):
        alias = Path(tempfile.gettempdir()) / f"notify-temp-alias-{os.getpid()}"
        alias.symlink_to(self.root, target_is_directory=True)
        try:
            with mock.patch.object(notifications.tempfile, "gettempdir", return_value=str(alias)):
                with self.assertRaises(notifications.NotificationError):
                    notifications._output_target(
                        brain,
                        self.root,
                        "desk",
                        "key",
                        NOW,
                        alias / "escaped.json",
                    )
            self.assertFalse((self.root / "escaped.json").exists())
        finally:
            alias.unlink()

    def test_real_provider_remains_gated_and_check_is_nonzero(self):
        current = config(provider="slack", secretEnvironmentVariable="BRAIN_SLACK_WEBHOOK")
        self.write_setup(current)
        output = io.StringIO()
        with mock.patch.object(brain, "select_environment", return_value=self.selected()), contextlib.redirect_stdout(output):
            rc = notifications.command(brain, self.root, args(check=True, requested_env="desk"))
        self.assertEqual(rc, 1)
        result = json.loads(output.getvalue())
        self.assertFalse(result["ready"])
        self.assertTrue(result["testSendRequired"])

    def test_module_contains_no_network_transport_or_committed_queue(self):
        source = Path(notifications.__file__).read_text(encoding="utf-8")
        for forbidden in ("urllib.request", "http.client", "requests.", "urlopen(", "socket.", "WebSocket", "queue.json"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    @unittest.skip("requires an owner-selected provider, verified private destination, credential, and per-run approval")
    def test_owner_approved_real_provider_smoke(self):
        self.fail("real provider transport is intentionally not implemented")


if __name__ == "__main__":
    unittest.main()
