"""Remote-safety gate tests (#83).

All repositories and providers are disposable fakes. No test performs a network
request or reads a real personal-data connector.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]


PRIVATE = {
    "visibility": "PRIVATE",
    "isPrivate": True,
    "isTemplate": False,
    "templateRepository": None,
}
PUBLIC = {
    "visibility": "PUBLIC",
    "isPrivate": False,
    "isTemplate": False,
    "templateRepository": None,
}
TEMPLATE = {
    "visibility": "PUBLIC",
    "isPrivate": False,
    "isTemplate": True,
    "templateRepository": None,
}


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def init_repo(root: Path) -> Path:
    git(root, "init", "--quiet")
    return root


class FakeProvider:
    def __init__(self, records=None, error=None):
        self.records = records or {}
        self.error = error
        self.calls = []

    def __call__(self, owner: str, repo: str):
        self.calls.append((owner, repo))
        if self.error:
            raise self.error
        return self.records.get((owner.casefold(), repo.casefold()), PRIVATE)


class UrlNormalizationTests(unittest.TestCase):
    def test_supported_github_url_forms_share_one_key(self):
        forms = [
            "https://github.com/Owner/Repo.git",
            "ssh://git@github.com/Owner/Repo.git",
            "git@github.com:Owner/Repo.git",
        ]
        normalized = [brain.normalize_push_url(url) for url in forms]
        self.assertEqual({row["key"] for row in normalized}, {"github.com/owner/repo"})
        self.assertTrue(all(row["provider"] == "github" for row in normalized))

    def test_insecure_transport_and_nonstandard_port_fail_closed(self):
        for url, reason in [
            ("http://github.com/Owner/Repo.git", "unsupported-push-transport"),
            ("git://github.com/Owner/Repo.git", "unsupported-push-transport"),
            ("https://github.com:444/Owner/Repo.git", "nonstandard-push-port"),
            ("ssh://git@github.com:2222/Owner/Repo.git", "nonstandard-push-port"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(brain.normalize_push_url(url)["reasonCode"], reason)

    def test_credentials_and_identity_are_absent_from_public_summary(self):
        row = brain.normalize_push_url(
            "https://secret-user:secret-token@github.com/PrivateOwner/SecretRepo.git"
        )
        visible = json.dumps(brain.public_remote_target(row), sort_keys=True)
        for secret in ("secret-user", "secret-token", "PrivateOwner", "SecretRepo"):
            self.assertNotIn(secret, visible)
        self.assertEqual(row["summary"], "github.com/<redacted>")

    def test_malformed_and_unsupported_urls_have_no_identity_in_summary(self):
        for url, reason in [
            ("https://git.example.internal/acme/brain.git", "unsupported-push-host"),
            ("https://github.com/only-owner", "malformed-push-url"),
            ("not a remote URL", "malformed-push-url"),
        ]:
            with self.subTest(url=url):
                row = brain.normalize_push_url(url)
                self.assertEqual(row["reasonCode"], reason)
                self.assertNotIn("example.internal", json.dumps(brain.public_remote_target(row)))
                self.assertNotIn("acme", json.dumps(brain.public_remote_target(row)))


class EvaluationTests(unittest.TestCase):
    def evaluate(self, root: Path, provider=None, acknowledge=False):
        return brain.evaluate_remote_safety(
            root,
            metadata_provider=provider or FakeProvider(),
            acknowledge_unknown=acknowledge,
        )

    def test_no_push_repository_is_local_only_and_cannot_persist(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            provider = FakeProvider()
            result = self.evaluate(root, provider)
        self.assertEqual(result["state"], "pass")
        self.assertEqual(result["verifiedState"], "pass")
        self.assertTrue(result["localOnly"])
        self.assertTrue(result["personalDataAllowed"])
        self.assertFalse(result["persistenceAllowed"])
        self.assertEqual(provider.calls, [])

    def test_fetch_only_public_upstream_does_not_override_private_origin(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(root, "remote", "add", "origin", "https://github.com/acme/private.git")
            git(root, "remote", "add", "upstream", "https://github.com/open/template.git")
            git(root, "config", "remote.upstream.pushurl", "NO_PUSH")
            provider = FakeProvider({("acme", "private"): PRIVATE})
            result = self.evaluate(root, provider)
        self.assertEqual(result["state"], "pass")
        self.assertEqual(provider.calls, [("acme", "private")])
        self.assertEqual(len(result["targets"]), 1)

    def test_every_push_url_is_checked_and_one_public_target_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(root, "remote", "add", "origin", "https://github.com/acme/private.git")
            git(root, "config", "--add", "remote.origin.pushurl", "git@github.com:acme/private.git")
            git(root, "config", "--add", "remote.origin.pushurl", "https://github.com/acme/public.git")
            provider = FakeProvider(
                {("acme", "private"): PRIVATE, ("acme", "public"): PUBLIC}
            )
            result = self.evaluate(root, provider)
        self.assertEqual(result["state"], "block")
        self.assertIn("repository-public", result["reasonCodes"])
        self.assertEqual(provider.calls, [("acme", "private"), ("acme", "public")])

    def test_template_and_non_private_states_are_unoverrideable(self):
        cases = [
            (
                {
                    "visibility": "PRIVATE",
                    "isPrivate": True,
                    "isTemplate": True,
                    "templateRepository": None,
                },
                "repository-template",
            ),
            (
                {
                    "visibility": "INTERNAL",
                    "isPrivate": False,
                    "isTemplate": False,
                    "templateRepository": None,
                },
                "repository-not-private",
            ),
        ]
        for metadata, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as td:
                root = init_repo(Path(td))
                git(root, "remote", "add", "origin", "https://github.com/acme/brain.git")
                result = self.evaluate(
                    root,
                    FakeProvider({("acme", "brain"): metadata}),
                    acknowledge=True,
                )
                self.assertEqual(result["state"], "block")
                self.assertFalse(result["personalDataAllowed"])
                self.assertFalse(result["unknownAcknowledged"])
                self.assertIn(reason, result["reasonCodes"])

    def test_unknown_auth_provider_and_malformed_metadata_fail_closed(self):
        cases = [
            (
                FakeProvider(error=brain.MetadataProviderError("provider-query-failed")),
                "provider-query-failed",
            ),
            (FakeProvider({("acme", "brain"): {"visibility": "PRIVATE"}}), "provider-response-invalid"),
        ]
        for provider, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as td:
                root = init_repo(Path(td))
                git(root, "remote", "add", "origin", "https://github.com/acme/brain.git")
                result = self.evaluate(root, provider)
                self.assertEqual(result["state"], "unknown")
                self.assertFalse(result["personalDataAllowed"])
                self.assertIn(reason, result["reasonCodes"])

    def test_unknown_acknowledgment_is_effective_for_one_call_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(root, "remote", "add", "origin", "https://unknown.example/owner/repo.git")
            acknowledged = self.evaluate(root, FakeProvider(), acknowledge=True)
            next_call = self.evaluate(root, FakeProvider(), acknowledge=False)
        self.assertEqual(acknowledged["state"], "pass")
        self.assertEqual(acknowledged["verifiedState"], "unknown")
        self.assertTrue(acknowledged["unknownAcknowledged"])
        self.assertEqual(next_call["state"], "unknown")
        self.assertFalse(next_call["unknownAcknowledged"])

    def test_unknown_targets_are_not_collapsed_or_credential_fingerprinted(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(root, "remote", "add", "origin", "https://one:secret@host-one/a/b.git")
            git(root, "config", "--add", "remote.origin.pushurl", "https://one:secret@host-one/a/b.git")
            git(root, "config", "--add", "remote.origin.pushurl", "https://two:secret@host-two/a/b.git")
            result = self.evaluate(root, FakeProvider())
        self.assertEqual([t["id"] for t in result["targets"]], ["target-001", "target-002"])
        visible = json.dumps(result, sort_keys=True)
        for secret in ("one", "two", "secret", "host-one", "host-two"):
            self.assertNotIn(secret, visible)

    def test_git_unavailable_is_unknown_and_does_not_query_provider(self):
        provider = FakeProvider()
        with mock.patch.object(brain.subprocess, "run", side_effect=FileNotFoundError):
            result = brain.evaluate_remote_safety(Path("/redacted"), provider)
        self.assertEqual(result["state"], "unknown")
        self.assertIn("git-unavailable", result["reasonCodes"])
        self.assertEqual(provider.calls, [])

    def test_non_repository_is_unknown_not_local_only(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.evaluate(Path(td), FakeProvider())
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["localOnly"])
        self.assertIn("not-git-repository", result["reasonCodes"])

    def test_inherited_git_config_cannot_replace_public_push_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(root, "remote", "add", "origin", "https://github.com/acme/public.git")
            provider = FakeProvider(
                {
                    ("acme", "public"): PUBLIC,
                    ("acme", "private"): PRIVATE,
                }
            )
            hostile = {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "remote.origin.pushurl",
                "GIT_CONFIG_VALUE_0": "https://github.com/acme/private.git",
                "GIT_CONFIG_PARAMETERS": "'remote.origin.pushurl=https://github.com/acme/private.git'",
            }
            connector = mock.Mock()
            with mock.patch.dict(os.environ, hostile, clear=False):
                result = self.evaluate(root, provider)
                with self.assertRaises(brain.RemoteSafetyError):
                    brain.guarded_personal_data_call(
                        root,
                        connector,
                        metadata_provider=provider,
                        persist=True,
                    )
        self.assertEqual(result["state"], "block")
        self.assertIn(("acme", "public"), provider.calls)
        self.assertIn(("acme", "private"), provider.calls)
        connector.assert_not_called()

    def test_local_include_cannot_substitute_push_target_through_home(self):
        cases = [
            ("public", "private", PUBLIC),
            ("private", "public", PRIVATE),
        ]
        for configured, included, configured_metadata in cases:
            with self.subTest(configured=configured, included=included), tempfile.TemporaryDirectory() as td:
                base = Path(td)
                root = base / "repo"
                root.mkdir()
                root = init_repo(root)
                hostile_home = base / "hostile-home"
                hostile_home.mkdir()
                git(
                    root,
                    "remote",
                    "add",
                    "origin",
                    f"https://github.com/acme/{configured}.git",
                )
                git(root, "config", "include.path", "~/remote-safety.inc")
                (hostile_home / "remote-safety.inc").write_text(
                    "[remote \"origin\"]\n"
                    f"\tpushurl = https://github.com/acme/{included}.git\n",
                    encoding="utf-8",
                )
                provider = FakeProvider(
                    {
                        ("acme", configured): configured_metadata,
                        ("acme", included): PRIVATE if included == "private" else PUBLIC,
                    }
                )
                connector = mock.Mock()
                with mock.patch.dict(os.environ, {"HOME": str(hostile_home)}):
                    result = self.evaluate(root, provider)
                    with self.assertRaises(brain.RemoteSafetyError):
                        brain.guarded_personal_data_call(
                            root,
                            connector,
                            metadata_provider=provider,
                            persist=True,
                        )
                self.assertEqual(result["state"], "unknown")
                self.assertIn("unsafe-local-config-include", result["reasonCodes"])
                self.assertEqual(provider.calls, [])
                connector.assert_not_called()

    def test_ambient_global_targets_are_unioned_with_local_targets(self):
        global_configs = {
            "pushurl": (
                '[remote "origin"]\n'
                "\tpushurl = https://github.com/acme/public.git\n"
            ),
            "pushInsteadOf": (
                '[url "https://github.com/acme/public.git"]\n'
                "\tpushInsteadOf = https://github.com/acme/private.git\n"
            ),
            "insteadOf": (
                '[url "https://github.com/acme/public.git"]\n'
                "\tinsteadOf = https://github.com/acme/private.git\n"
            ),
        }
        for mode, config in global_configs.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                base = Path(td)
                root = base / "repo"
                home = base / "home"
                root.mkdir()
                home.mkdir()
                init_repo(root)
                git(
                    root,
                    "remote",
                    "add",
                    "origin",
                    "https://github.com/acme/private.git",
                )
                (home / ".gitconfig").write_text(config, encoding="utf-8")
                provider = FakeProvider(
                    {
                        ("acme", "private"): PRIVATE,
                        ("acme", "public"): PUBLIC,
                    }
                )
                connector = mock.Mock()
                with mock.patch.dict(os.environ, {"HOME": str(home)}):
                    result = self.evaluate(root, provider)
                    with self.assertRaises(brain.RemoteSafetyError):
                        brain.guarded_personal_data_call(
                            root,
                            connector,
                            metadata_provider=provider,
                            persist=True,
                        )
                self.assertEqual(result["state"], "block")
                self.assertIn("repository-public", result["reasonCodes"])
                self.assertIn(("acme", "private"), provider.calls)
                self.assertIn(("acme", "public"), provider.calls)
                connector.assert_not_called()


class GuardTests(unittest.TestCase):
    def repo(self, td: str, url: str | None) -> Path:
        root = init_repo(Path(td))
        if url:
            git(root, "remote", "add", "origin", url)
        return root

    def test_block_and_unknown_make_zero_connector_calls(self):
        for metadata in (PUBLIC, None):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as td:
                root = self.repo(td, "https://github.com/acme/brain.git")
                provider = (
                    FakeProvider({("acme", "brain"): metadata})
                    if metadata is not None
                    else FakeProvider(error=brain.MetadataProviderError("provider-query-failed"))
                )
                connector = mock.Mock(return_value="personal data")
                with self.assertRaises(brain.RemoteSafetyError):
                    brain.guarded_personal_data_call(root, connector, metadata_provider=provider)
                connector.assert_not_called()

    def test_public_block_cannot_be_acknowledged(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.repo(td, "https://github.com/acme/brain.git")
            connector = mock.Mock()
            with self.assertRaises(brain.RemoteSafetyError):
                brain.guarded_personal_data_call(
                    root,
                    connector,
                    metadata_provider=FakeProvider({("acme", "brain"): PUBLIC}),
                    acknowledge_unknown=True,
                )
            connector.assert_not_called()

    def test_mixed_public_and_unknown_still_cannot_be_acknowledged(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.repo(td, "https://github.com/acme/public.git")
            git(root, "config", "--add", "remote.origin.pushurl", "https://github.com/acme/public.git")
            git(root, "config", "--add", "remote.origin.pushurl", "https://unknown.invalid/acme/brain.git")
            connector = mock.Mock()
            with self.assertRaises(brain.RemoteSafetyError):
                brain.guarded_personal_data_call(
                    root,
                    connector,
                    metadata_provider=FakeProvider({("acme", "public"): PUBLIC}),
                    acknowledge_unknown=True,
                )
            connector.assert_not_called()

    def test_local_only_persistence_is_stopped_before_connector(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.repo(td, None)
            connector = mock.Mock()
            with self.assertRaises(brain.RemoteSafetyError):
                brain.guarded_personal_data_call(root, connector, persist=True)
            connector.assert_not_called()

    def test_private_and_acknowledged_unknown_can_call_connector(self):
        cases = [
            ("https://github.com/acme/brain.git", FakeProvider(), False),
            ("https://unknown.example/acme/brain.git", FakeProvider(), True),
        ]
        for url, provider, acknowledge in cases:
            with self.subTest(url=url), tempfile.TemporaryDirectory() as td:
                root = self.repo(td, url)
                connector = mock.Mock(return_value="ok")
                value = brain.guarded_personal_data_call(
                    root,
                    connector,
                    metadata_provider=provider,
                    acknowledge_unknown=acknowledge,
                )
                self.assertEqual(value, "ok")
                connector.assert_called_once_with()


class ProviderAndCliTests(unittest.TestCase):
    def test_default_provider_uses_bounded_noninteractive_subprocess(self):
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(PRIVATE), stderr="")
        with mock.patch.object(brain.subprocess, "run", return_value=completed) as run:
            result = brain.GitHubMetadataProvider(timeout=7)("owner", "repo")
        self.assertEqual(result, PRIVATE)
        args, kwargs = run.call_args
        self.assertEqual(args[0][:3], ["gh", "repo", "view"])
        self.assertEqual(kwargs["timeout"], 7)
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["env"]["GH_PROMPT_DISABLED"], "1")
        self.assertEqual(kwargs["env"]["GH_HOST"], "github.com")
        self.assertTrue(kwargs["capture_output"])

    def test_subprocess_environment_drops_repo_overrides_and_trace_sinks(self):
        hostile = {
            "GIT_DIR": "/wrong/repo",
            "GIT_WORK_TREE": "/private/worktree",
            "GIT_TRACE": "/private/trace.log",
            "GIT_TRACE2_EVENT": "/private/events.json",
            "GIT_CURL_VERBOSE": "1",
            "GH_DEBUG": "api",
            "GH_FORCE_TTY": "1",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "remote.origin.pushurl",
            "GIT_CONFIG_VALUE_0": "https://github.com/acme/private.git",
            "GIT_CONFIG_PARAMETERS": "'remote.origin.pushurl=x'",
            "GIT_CONFIG_GLOBAL": "/private/global-config",
            "GIT_CONFIG_SYSTEM": "/private/system-config",
        }
        with mock.patch.dict(brain.os.environ, hostile, clear=False):
            env = brain._safe_subprocess_env()
        for key in hostile:
            if key.startswith("GIT_CONFIG"):
                continue
            self.assertNotIn(key, env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(env["GIT_CONFIG_SYSTEM"], os.devnull)
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")

    def test_ambient_git_environment_drops_windows_stdio_redirects(self):
        hostile = {
            "GIT_REDIRECT_STDIN": "\\\\.\\pipe\\secret-input",
            "GIT_REDIRECT_STDOUT": "C:\\private\\stdout.txt",
            "GIT_REDIRECT_STDERR": "C:\\private\\stderr.txt",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "remote.origin.pushurl",
            "GIT_CONFIG_VALUE_0": "https://github.com/acme/public.git",
        }
        with mock.patch.dict(brain.os.environ, hostile, clear=False):
            env = brain._ambient_git_subprocess_env()
        for key in (
            "GIT_REDIRECT_STDIN",
            "GIT_REDIRECT_STDOUT",
            "GIT_REDIRECT_STDERR",
        ):
            self.assertNotIn(key, env)
        # Target-affecting configuration remains present for the ambient union.
        self.assertEqual(env["GIT_CONFIG_COUNT"], "1")

    def test_default_provider_maps_failures_without_forwarding_details(self):
        failures = [
            (FileNotFoundError("/private/path"), "provider-unavailable"),
            (subprocess.TimeoutExpired(["gh"], 10, stderr="secret"), "provider-timeout"),
            (subprocess.CalledProcessError(1, ["gh"], stderr="secret"), "provider-query-failed"),
        ]
        for failure, reason in failures:
            with self.subTest(reason=reason), mock.patch.object(
                brain.subprocess, "run", side_effect=failure
            ):
                with self.assertRaisesRegex(brain.MetadataProviderError, f"^{reason}$"):
                    brain.GitHubMetadataProvider()("private-owner", "private-repo")

    def test_injected_provider_error_text_is_replaced_at_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(root, "remote", "add", "origin", "https://github.com/acme/brain.git")
            provider = FakeProvider(
                error=brain.MetadataProviderError("token-value /private/path")
            )
            result = brain.evaluate_remote_safety(root, provider)
        visible = json.dumps(result, sort_keys=True)
        self.assertNotIn("token-value", visible)
        self.assertNotIn("/private/path", visible)
        self.assertIn("provider-query-failed", result["reasonCodes"])

    def test_cli_json_and_human_output_are_redacted(self):
        with tempfile.TemporaryDirectory() as td:
            root = init_repo(Path(td))
            git(
                root,
                "remote",
                "add",
                "origin",
                "https://token-user:token-value@github.com/PrivateOwner/SecretRepo.git",
            )
            provider = FakeProvider({("privateowner", "secretrepo"): PRIVATE})
            for as_json in (False, True):
                with self.subTest(as_json=as_json), mock.patch.object(
                    brain, "GitHubMetadataProvider", return_value=provider
                ), contextlib.redirect_stdout(io.StringIO()) as output:
                    argv = ["remote-safety", "--vault", str(root)]
                    if as_json:
                        argv.append("--json")
                    self.assertEqual(brain.main(argv), 0)
                visible = output.getvalue()
                for secret in (
                    "token-user",
                    "token-value",
                    "PrivateOwner",
                    "SecretRepo",
                    str(root),
                ):
                    self.assertNotIn(secret, visible)

    def test_cli_persist_blocks_local_only_before_connector_or_output(self):
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(
            io.StringIO()
        ) as output:
            root = init_repo(Path(td))
            self.assertEqual(
                brain.main(
                    ["remote-safety", "--vault", str(root), "--persist", "--json"]
                ),
                1,
            )
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["personalDataAllowed"])
        self.assertFalse(payload["persistenceAllowed"])
        self.assertTrue(payload["persistenceRequested"])
        self.assertFalse(payload["operationAllowed"])
        connector = mock.Mock()
        output_open = mock.Mock()
        if payload["operationAllowed"]:
            connector()
            output_open()
        connector.assert_not_called()
        output_open.assert_not_called()


class DocumentationContractTests(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_orientation_separates_capability_inventory_and_guarded_reads(self):
        text = self.read("10_Agents/skills/agent-orientation/SKILL.md")
        self.assertIn("## Remote-safety boundary", text)
        self.assertIn("capability inventory", text.lower())
        self.assertIn("require_remote_safety", text)
        self.assertIn("zero calls", text)

    def test_onboarding_requests_persistence_before_connector(self):
        text = self.read("10_Agents/skills/onboard-owner/SKILL.md")
        self.assertIn("## Remote-safety boundary", text)
        self.assertIn("`persist=True`", text)
        self.assertIn("never\noverrideable", text)

    def test_operating_rules_make_unknown_session_only(self):
        text = self.read("10_Agents/docs/operating-rules.md")
        self.assertIn("## Personal-data remote safety", text)
        self.assertIn("`--acknowledge-unknown`", text)
        self.assertIn("current invocation only", text)

    def test_scheduled_inbound_automations_require_persistence_gate(self):
        text = self.read("10_Agents/skills/recommended-automations/SKILL.md")
        self.assertIn("remote-safety --persist --json", text)
        self.assertIn("operationAllowed: true", text)
        self.assertIn("zero connector calls", text)
        self.assertIn("open zero output files", text)
        self.assertIn("never use `--acknowledge-unknown`", text)


if __name__ == "__main__":
    unittest.main()
