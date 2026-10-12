"""Optional Webcmd Current discovery: offline protocol, identity and cleanup tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/cloudcodex-environment-discovery/runtime"))

from common.adapters import AdapterError
from common.configuration import DiscoveryRuntime, validate_configuration
from common.escalation import EscalatingProvider, Stage
from common.models import ProviderResult
from current.webcmd import (
    CURRENT_URL, WebcmdCatalogProvider, WebcmdCli, WebcmdSettings,
)


class FakeWebcmdCli:
    """No external process or network; records exact Webcmd subcommands."""

    def __init__(self, settings, status=200, mime="application/json",
                 fail_create=False, wrong_profile=False, refuse_close=False,
                 missing_profile=False):
        self.settings = settings
        self.status = status
        self.mime = mime
        self.fail_create = fail_create
        self.wrong_profile = wrong_profile
        self.refuse_close = refuse_close
        self.missing_profile = missing_profile
        self.sessions = {}
        self.calls = []
        self.programs = []

    def run(self, arguments, program=None):
        self.calls.append(arguments)
        if arguments[:2] == ("profile", "list"):
            return [] if self.missing_profile else [
                {"contextId": self.settings.profile, "alias": "", "connected": True}
            ]
        if arguments[:2] == ("session", "list"):
            return list(self.sessions.values())
        if arguments[:2] == ("session", "create"):
            prefix = arguments[2]
            identifier = prefix + "-ji"
            self.sessions[identifier] = {
                "id": identifier,
                "profileId": "other" if self.wrong_profile else self.settings.profile,
                "kind": "explicit",
            }
            if self.fail_create:
                raise AdapterError("simulated_lost_create_receipt")
            return {"id": identifier}
        if arguments[:2] == ("session", "close"):
            if not self.refuse_close:
                self.sessions.pop(arguments[2], None)
            return {"closed": not self.refuse_close}
        if "browser" in arguments and "run" in arguments:
            self.programs.append(program)
            assert "--stdin" in arguments
            record = {
                "id": "cfg-webcmd",
                "name": "Current fixture",
                "repository_ids": ["1408634524"],
                "published": True,
            }
            is_detail = "/v1/environment-configs/cfg-webcmd" in program
            body = {"config": record} if is_detail else {"items": [record]}
            return {
                "ok": True,
                "result": {
                    "status": self.status,
                    "content_type": self.mime,
                    "body": body if self.status == 200 else None,
                },
            }
        raise AssertionError("Unexpected CLI command: " + repr(arguments))


class WebcmdTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        node = root / "node.exe"
        entry = root / "node_modules" / "@agentrhq" / "webcmd" / "dist" / "src" / "main.js"
        browser = root / "CloakRuntime" / "chrome.exe"
        for file in (node, entry, browser):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"offline-test-fixture")
        self.config = {
            "command": {
                "argv": [str(node), str(entry)],
                "sha256": {
                    str(node): hashlib.sha256(node.read_bytes()).hexdigest(),
                    str(entry): hashlib.sha256(entry.read_bytes()).hexdigest(),
                },
                "cwd": str(root),
                "timeout": 10,
            },
            "browser_binary": str(browser),
            "profile": "default",
        }
        self.settings = WebcmdSettings.from_mapping(self.config)

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, **fake_options):
        fake = FakeWebcmdCli(self.settings, **fake_options)
        return WebcmdCatalogProvider(
            self.settings,
            cli_factory=lambda settings: fake,
        ), fake

    def test_settings_require_pins_and_existing_runtime_metadata(self):
        self.assertEqual(self.settings.profile, "default")
        for field, value in (
            ("profile", "../outside"),
            ("browser_binary", "relative/chrome.exe"),
            ("browser_binary", "/bin/bash"),
        ):
            config = dict(self.config)
            config[field] = value
            with self.assertRaises(ValueError):
                WebcmdSettings.from_mapping(config)
        config = dict(self.config)
        config["command"] = dict(config["command"])
        config["command"]["sha256"] = {}
        with self.assertRaises(ValueError):
            WebcmdSettings.from_mapping(config)

    def test_config_validates_webcmd_and_integrity_pins(self):
        configuration = {
            "schema_version": 1,
            "mode": "AUTO",
            "timeout": 30,
            "domains": {
                "current": {
                    "stages": [
                        {"kind": "webcmd", "approved": True, "webcmd": self.config},
                    ],
                },
            },
        }
        validated = validate_configuration(configuration)
        self.assertEqual(validated["domains"]["current"]["stages"][0]["kind"], "webcmd")
        self.assertEqual(
            DiscoveryRuntime(validated).doctor("current")["stages"][0]["kind"],
            "webcmd",
        )
        with self.assertRaises(ValueError):
            validate_configuration({
                **configuration, "domains": {"legacy": configuration["domains"]["current"]}
            })

    def test_current_escalation_order_supports_primary_and_webcmd(self):
        # Every entry is startup configuration only; no host is started.
        browser_cli = str(Path(self.temp.name) / "browser-act.exe")
        configuration = {
            "schema_version": 1,
            "domains": {
                "current": {
                    "stages": [
                        {
                            "kind": "primary",
                            "approved": False,
                            "command": self.config["command"],
                        },
                        {"kind": "webcmd", "approved": True, "webcmd": self.config},
                        {
                            "kind": "browser_web",
                            "approved": False,
                            "browser": {
                                "executable": browser_cli,
                                "sha256": "a" * 64,
                                "browser_id": "chrome_local_123",
                            },
                        },
                    ]
                }
            },
        }
        self.assertEqual(
            len(validate_configuration(configuration)["domains"]["current"]["stages"]),
            3,
        )
        configuration["domains"]["current"]["stages"].reverse()
        with self.assertRaises(ValueError):
            validate_configuration(configuration)

    def test_success_two_scopes_provenance_and_owned_cleanup(self):
        provider, fake = self.provider()
        result = provider.list_environments()
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.catalog_complete)
        self.assertEqual(len(result.environments), 1)
        self.assertEqual(result.environments[0].repository_id, "1408634524")
        self.assertEqual(result.source, "webcmd_current_catalog")
        self.assertEqual(len(fake.programs), 2)
        self.assertTrue(result.coverage["session_cleanup_confirmed"])
        self.assertFalse(fake.sessions)

    def test_fixed_original_endpoint_and_no_cookie_or_challenge_logic(self):
        provider, fake = self.provider()
        provider.list_environments(include_drafts=True)
        self.assertEqual(len(fake.programs), 2)
        for script in fake.programs:
            self.assertIn(CURRENT_URL, script)
            self.assertIn("omitDraft=false", script)
            self.assertIn("page.goto(", script)
            for forbidden in (
                "document.cookie", "localStorage", "sessionStorage",
                "Authorization", "POST", "PUT", "DELETE",
                "solve", "captcha", "cloudflare", "token",
            ):
                self.assertNotIn(forbidden, script)
        self.assertFalse(any("profile" in a and "import" in a for a in fake.calls))

    def test_401_json_is_terminal_and_no_second_scope(self):
        provider, fake = self.provider(status=401)
        result = provider.list_environments()
        self.assertEqual(result.status, "unauthorized")
        self.assertEqual(result.reason, "http_401")
        self.assertEqual(len(fake.programs), 1)
        self.assertTrue(result.coverage["session_cleanup_confirmed"])
        self.assertFalse(fake.sessions)

    def test_403_html_is_terminal_and_not_fallback(self):
        provider, fake = self.provider(status=403, mime="text/html")
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "http_403")
        self.assertEqual(len(fake.programs), 1)
        self.assertFalse(fake.sessions)

    def test_missing_preexisting_profile_never_creates_session(self):
        provider, fake = self.provider(missing_profile=True)
        result = provider.list_environments()
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "webcmd_profile_not_initialized")
        self.assertEqual([c[:2] for c in fake.calls], [("profile", "list")])

    def test_missing_preinstalled_browser_never_starts_cli(self):
        provider, fake = self.provider()
        with patch("current.webcmd.Path.is_file", return_value=False):
            result = provider.list_environments()
        self.assertEqual(result.reason, "webcmd_browser_runtime_missing")
        self.assertFalse(fake.calls)

    def test_invalid_session_ownership_does_not_read_another_profile(self):
        provider, fake = self.provider(wrong_profile=True)
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "webcmd_session_ownership_unverified")
        self.assertEqual(len(fake.programs), 0)
        self.assertFalse(result.coverage["session_cleanup_confirmed"])
        self.assertEqual(len(fake.sessions), 1)  # Never close an unverified profile.

    def test_failed_create_receipt_is_reconciled_before_cleanup(self):
        provider, fake = self.provider(fail_create=True)
        with self.assertRaisesRegex(AdapterError, "simulated_lost_create_receipt"):
            provider.list_environments()
        self.assertFalse(fake.sessions)
        self.assertFalse(fake.programs)

    def test_cleanup_failure_never_claims_complete_success(self):
        provider, fake = self.provider(refuse_close=True)
        result = provider.list_environments()
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.catalog_complete)
        self.assertFalse(result.coverage["session_cleanup_confirmed"])
        self.assertEqual(len(fake.sessions), 1)

    def test_arbitrary_catalog_destination_is_rejected(self):
        provider, fake = self.provider()
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_destination"):
            provider._read("our-session", "https://example.com", {})
        self.assertFalse(fake.calls)

    def test_recoverable_primary_failure_escalates_to_webcmd(self):
        provider, fake = self.provider()

        class Primary:
            name = "current"

            def list_environments(self, **kwargs):
                return ProviderResult(
                    provider="current", status="unavailable",
                    reason="source_not_available",
                )

        stages = [
            Stage("primary", Primary()),
            Stage("webcmd", provider),
        ]
        result = EscalatingProvider("current", stages).list_environments()
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.catalog_complete)
        self.assertEqual(
            [item["stage"] for item in result.attempts],
            ["primary", "webcmd"],
        )
        self.assertTrue(result.coverage["session_cleanup_confirmed"])
        self.assertFalse(fake.sessions)

    def test_terminal_denial_prevents_other_cloud_escalation(self):
        provider, fake = self.provider(status=401)

        class OtherSource:
            name = "current"
            called = False

            def list_environments(self, **kwargs):
                self.called = True
                return ProviderResult(provider="current", status="ok")

        other = OtherSource()
        escalation = EscalatingProvider(
            "current",
            [Stage("webcmd", provider), Stage("browser_web", other)],
        )
        result = escalation.list_environments()
        self.assertEqual(result.status, "unauthorized")
        self.assertFalse(other.called)
        self.assertEqual([i["stage"] for i in result.attempts], ["webcmd"])

    def test_current_point_get_reads_only_exact_id_and_cleans_owned_session(self):
        provider, fake = self.provider()
        result = provider.get_environment("cfg-webcmd")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.source, "webcmd_current_detail")
        self.assertFalse(result.catalog_complete)
        self.assertTrue(result.coverage["point_verified"])
        self.assertTrue(result.coverage["session_cleanup_confirmed"])
        self.assertEqual(len(fake.programs), 1)
        self.assertIn("/v1/environment-configs/cfg-webcmd", fake.programs[0])
        self.assertNotIn("scope=user", fake.programs[0])
        self.assertFalse(fake.sessions)

    def test_current_point_401_stops_without_catalog_retry(self):
        provider, fake = self.provider(status=401)
        result = provider.get_environment("cfg-webcmd")
        self.assertEqual(result.status, "unauthorized")
        self.assertEqual(result.reason, "http_401")
        self.assertEqual(len(fake.programs), 1)
        self.assertTrue(result.coverage["session_cleanup_confirmed"])
        self.assertFalse(fake.sessions)

    def test_invalid_point_id_rejected_before_any_webcmd_action(self):
        provider, fake = self.provider()
        with self.assertRaises(ValueError):
            provider.get_environment("../unapproved-path")
        self.assertFalse(fake.calls)
        self.assertFalse(fake.sessions)

    def test_point_cleanup_failure_cannot_claim_verified_result(self):
        provider, fake = self.provider(refuse_close=True)
        result = provider.get_environment("cfg-webcmd")
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.coverage["session_cleanup_confirmed"])
        self.assertFalse(result.catalog_complete)

    def test_pin_integrity_verification_applies_to_webcmd_cli(self):
        runner = WebcmdCli(self.settings)
        node = Path(self.settings.command.argv[0])
        node.write_bytes(b"modified fixture")
        with self.assertRaisesRegex(AdapterError, "host_integrity_mismatch"):
            runner.run(("session", "list", "-f", "json"))


if __name__ == "__main__":
    unittest.main()
