"""Provider-neutral notification schema, privacy, policy, and writer tests."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
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
        raw = notifications.canonical_json(value) + b"\n"
        (directory / notifications.CONFIG_NAME).write_bytes(raw)
        return value, raw

    def selected(self) -> dict:
        return {"slug": "desk", "source": "cli", "state": "selected"}

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
        self.assertEqual(calls, [(True, False)])
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
        self.assertEqual(sorted(path.name for path in overlay.iterdir()), [notifications.CONFIG_NAME])

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
                envelope=safe, now=NOW + notifications.timedelta(hours=25), explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        self.assertEqual(len(list(output_dir.iterdir())), 2)

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

    def test_file_failure_rolls_back_owned_output_exactly(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_write_json_cas", side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(KeyboardInterrupt):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=lambda *_args, **_kwargs: None,
                )
        output_dir = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
        self.assertEqual(list(output_dir.iterdir()), [])

    def test_late_output_replacement_is_preserved_and_state_rolls_back(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real = notifications._write_json_cas

        def commit_then_replace(api, root, rel, desired, expected, validator):
            real(api, root, rel, desired, expected, validator)
            if rel.endswith(notifications.STATE_NAME):
                output_dir = root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk" / notifications.OUTBOX_DIR
                output = next(output_dir.iterdir())
                output.unlink()
                output.write_bytes(b"foreign-output")

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications, "_write_json_cas", side_effect=commit_then_replace
        ):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None,
                    safety_guard=lambda *_args, **_kwargs: None,
                )
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assertFalse((overlay / notifications.STATE_NAME).exists())
        output = next((overlay / notifications.OUTBOX_DIR).iterdir())
        self.assertEqual(output.read_bytes(), b"foreign-output")

    def test_output_symlink_and_casefold_occupants_are_preserved(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        foreign = self.root / "foreign"
        foreign.mkdir()
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
        output_dir.mkdir()
        key = f"{safe['dedupeKey']}\0{NOW.isoformat()}".encode()
        expected = f"{notifications.hashlib.sha256(key).hexdigest()}.json"
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
        (overlay / notifications.STATE_NAME).write_bytes(b"{bad")
        safe = notifications.validate_envelope(brain, external_envelope())
        guard = mock.Mock()
        with mock.patch.object(brain, "select_environment", return_value=self.selected()):
            with self.assertRaises(notifications.NotificationError):
                notifications.deliver_file(
                    brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                    envelope=safe, now=NOW, explicit_output=None, safety_guard=guard,
                )
        guard.assert_not_called()
        self.assertFalse((overlay / notifications.OUTBOX_DIR).exists())

    def test_state_update_preserves_late_foreign_replacement(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        old = notifications.canonical_json(notifications.empty_state()) + b"\n"
        (directory / notifications.STATE_NAME).write_bytes(old)
        desired_state = copy.deepcopy(notifications.empty_state())
        desired_state["deliveries"].append(
            {"category": "validation", "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(), "deliveredAt": NOW.isoformat()}
        )
        desired = notifications.canonical_json(desired_state) + b"\n"
        real = brain._quarantine_migration_at
        def replace_then_quarantine(parent, name, backup):
            os.unlink(name, dir_fd=parent)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent)
            os.write(fd, b"foreign")
            os.close(fd)
            real(parent, name, backup)
        with mock.patch.object(brain, "_quarantine_migration_at", side_effect=replace_then_quarantine):
            with self.assertRaises(notifications.NotificationError):
                notifications._write_json_cas(brain, self.root, rel, desired, old, notifications.validate_state)
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), b"foreign")
        self.assertEqual(sorted(path.name for path in directory.iterdir()), [notifications.STATE_NAME])

    def test_post_commit_directory_fsync_failure_never_removes_new_state(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        rel = f"{brain.ENVIRONMENT_OVERLAYS_RELPATH}/desk/{notifications.STATE_NAME}"
        old = notifications.canonical_json(notifications.empty_state()) + b"\n"
        (directory / notifications.STATE_NAME).write_bytes(old)
        new_state = notifications.empty_state()
        new_state["deliveries"] = [
            {"category": "validation", "dedupeDigest": notifications.hashlib.sha256(b"new").hexdigest(), "deliveredAt": NOW.isoformat()}
        ]
        desired = notifications.canonical_json(new_state) + b"\n"
        real_fsync = notifications.os.fsync
        calls = 0

        def fail_fourth(descriptor):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("simulated directory fsync failure")
            return real_fsync(descriptor)

        with mock.patch.object(notifications.os, "fsync", side_effect=fail_fourth):
            notifications._write_json_cas(
                brain, self.root, rel, desired, old, notifications.validate_state
            )
        self.assertEqual((directory / notifications.STATE_NAME).read_bytes(), desired)
        self.assertEqual(sorted(path.name for path in directory.iterdir()), [notifications.STATE_NAME])

    def test_post_commit_fsync_failure_keeps_output_and_delivery_state_together(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real_fsync = notifications.os.fsync
        calls = 0

        def fail_fifth(descriptor):
            nonlocal calls
            calls += 1
            if calls == 5:
                raise OSError("simulated post-commit fsync failure")
            return real_fsync(descriptor)

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            notifications.os, "fsync", side_effect=fail_fifth
        ):
            result = notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                envelope=safe, now=NOW, explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
        self.assertTrue(result["delivered"])
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assertEqual(len(list((overlay / notifications.OUTBOX_DIR).iterdir())), 1)
        state = notifications.validate_state(
            json.loads((overlay / notifications.STATE_NAME).read_text())
        )
        self.assertEqual(
            state["deliveries"][0]["dedupeDigest"],
            notifications.hashlib.sha256(safe["dedupeKey"].encode()).hexdigest(),
        )

    def test_post_commit_foreign_stage_is_preserved_without_output_rollback(self):
        current, raw = self.write_setup()
        safe = notifications.validate_envelope(brain, external_envelope())
        real_remove = brain._remove_owned_migration_stage

        def replace_stage_then_remove(item):
            os.unlink(item["new"], dir_fd=item["parent"])
            descriptor = os.open(
                item["new"],
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=item["parent"],
            )
            try:
                os.write(descriptor, b"foreign-stage")
            finally:
                os.close(descriptor)
            real_remove(item)

        with mock.patch.object(brain, "select_environment", return_value=self.selected()), mock.patch.object(
            brain, "_remove_owned_migration_stage", side_effect=replace_stage_then_remove
        ):
            result = notifications.deliver_file(
                brain, self.root, selected=self.selected(), config=current, config_raw=raw,
                envelope=safe, now=NOW, explicit_output=None,
                safety_guard=lambda *_args, **_kwargs: None,
            )
        self.assertTrue(result["delivered"])
        overlay = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        self.assertEqual(len(list((overlay / notifications.OUTBOX_DIR).iterdir())), 1)
        state = notifications.validate_state(
            json.loads((overlay / notifications.STATE_NAME).read_text())
        )
        self.assertEqual(len(state["deliveries"]), 1)
        residue = list(overlay.glob(f".{notifications.STATE_NAME}.migrate-new-*"))
        self.assertEqual(len(residue), 1)
        self.assertEqual(residue[0].read_bytes(), b"foreign-stage")

    def test_orphan_transaction_evidence_blocks_missing_state_as_recovery(self):
        directory = self.root / brain.ENVIRONMENT_OVERLAYS_RELPATH / "desk"
        directory.mkdir(parents=True)
        residue = directory / f".{notifications.STATE_NAME}.migrate-old-deadbeef"
        residue.write_bytes(notifications.canonical_json(notifications.empty_state()) + b"\n")
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
