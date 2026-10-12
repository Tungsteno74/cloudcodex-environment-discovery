"""Current BrowserAct adapter contract without network, credentials or GUI."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/cloudcodex-environment-discovery/runtime"))
from current.browser import BrowserSettings, BrowserActCatalogProvider
from common.adapters import AdapterError
from common.configuration import validate_configuration

BROWSER = "chrome_local_12345"


class BrowserTests(unittest.TestCase):
    def provider(
        self,
        status=200,
        mime="application/json",
        metadata_type="chrome",
        confirm=False,
        reused=False,
        returned_id=BROWSER,
        open_browser_id="workbench",
        open_session_name_matches=True,
        register_session=True,
        preexisting=False,
        fail_after_open=False,
    ):
        calls = []
        fixed_session = "cloudcodex-catalog-" + "0" * 32
        sessions = {}
        if preexisting:
            sessions[fixed_session] = {
                "session_name": fixed_session,
                "browser_type": "chrome",
                "browser_id": returned_id,
            }

        class Client:
            def __init__(self, spec):
                self.args = spec.argv
                calls.append(self.args)

            def request(self, payload):
                args = self.args
                if args[-3:-1] == ("browser", "list"):
                    return {
                        "ok": True,
                        "browsers": [
                            {"id": BROWSER, "type": metadata_type, "confirm_before_use": confirm}
                        ],
                    }
                if args[-2:] == ("session", "list"):
                    return {"ok": True, "sessions": list(sessions.values())}
                if "open" in args:
                    name = args[args.index("--session") + 1]
                    if register_session:
                        sessions[name] = {
                            "session_name": name,
                            "browser_type": "chrome",
                            "browser_id": returned_id,
                        }
                    if fail_after_open:
                        raise AdapterError("simulated_open_response_lost")
                    return {
                        "ok": True,
                        "reused": reused,
                        "browser_type": "chrome",
                        "browser_id": open_browser_id,
                        "session_name": name if open_session_name_matches else "unexpected-session",
                    }
                if args[-3:-1] == ("session", "close"):
                    sessions.pop(args[-1], None)
                    return {"ok": True}
                if "eval" in args:
                    return {
                        "ok": True,
                        "result": {
                            "status": status,
                            "content_type": mime,
                            "body": {
                                "items": [
                                    {
                                        "id": "current-config",
                                        "name": "Existing config",
                                        "published": True,
                                    }
                                ]
                            },
                        },
                    }
                raise AssertionError("Unexpected browser command: " + repr(args))

        settings = BrowserSettings(
            str(Path(tempfile.gettempdir()) / "browser-act.exe"), "a" * 64, BROWSER
        )
        return BrowserActCatalogProvider(settings, client_factory=Client), calls

    def test_success_uses_two_scopes_and_closes_owned_session(self):
        provider, calls = self.provider()
        result = provider.list_environments()
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.catalog_complete)
        self.assertEqual(len(result.environments), 1)
        self.assertEqual(sum("eval" in c for c in calls), 2)
        self.assertIn("close", calls[-2])
        self.assertTrue(all("--no-auto-dialog" in c for c in calls))

    def test_forbidden_stops_before_second_scope_and_closes(self):
        provider, calls = self.provider(status=403, mime="text/html")
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(sum("eval" in c for c in calls), 1)
        self.assertIn("close", calls[-2])

    def test_nonjson_200_is_not_catalog(self):
        provider, calls = self.provider(mime="text/html")
        self.assertEqual(provider.list_environments().status, "forbidden")
        self.assertIn("close", calls[-2])

    def test_no_primary_browser_direct_mode(self):
        provider, calls = self.provider(metadata_type="chrome-direct")
        self.assertEqual(provider.list_environments().status, "forbidden")
        self.assertFalse(any("open" in c for c in calls))

    def test_existing_browser_confirmation_not_auto_accepted(self):
        provider, calls = self.provider(confirm=True)
        self.assertEqual(provider.list_environments().status, "approval_required")
        self.assertFalse(any("open" in c for c in calls))

    def test_script_does_not_read_credentials_or_mutate_resources(self):
        provider, calls = self.provider()
        provider.list_environments(include_drafts=True)
        scripts = [c[-1] for c in calls if "eval" in c]
        for script in scripts:
            self.assertIn("method:'GET'", script)
            self.assertIn("omitDraft=false", script)
            for forbidden in (
                "document.cookie",
                "localStorage",
                "sessionStorage",
                "Authorization",
                "POST",
                "PUT",
                "DELETE",
            ):
                self.assertNotIn(forbidden, script)
        self.assertFalse(
            any("create" in c or "import-profile" in c or "solve-captcha" in c for c in calls)
        )

    def test_session_names_are_unique_and_only_ours_are_closed(self):
        provider, calls = self.provider()
        provider.list_environments()
        provider.list_environments()
        opened = [c[c.index("--session") + 1] for c in calls if "open" in c]
        closed = [c[-1] for c in calls if "close" in c]
        self.assertEqual(opened, closed)
        self.assertEqual(len(set(opened)), 2)

    def test_reused_persistent_browser_allows_newly_verified_session(self):
        provider, calls = self.provider(reused=True)
        result = provider.list_environments()
        self.assertEqual(result.status, "ok")
        self.assertEqual(sum("eval" in call for call in calls), 2)
        self.assertIn("close", calls[-2])
        self.assertTrue(result.coverage["session_cleanup_confirmed"])

    def test_missing_reuse_flag_does_not_override_session_inventory(self):
        provider, calls = self.provider(reused=None)
        result = provider.list_environments()
        self.assertEqual(result.status, "ok")
        self.assertTrue(any("eval" in call for call in calls))
        self.assertTrue(result.coverage["session_cleanup_confirmed"])

    def test_browser_open_alias_is_not_an_environment_or_browser_identity(self):
        provider, calls = self.provider(open_browser_id="workbench")
        result = provider.list_environments()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.environments), 1)
        self.assertIn("close", calls[-2])

    def test_other_browser_in_session_inventory_is_not_operated_on(self):
        provider, calls = self.provider(returned_id="chrome_local_999")
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "unexpected_browser_session")
        self.assertTrue(result.warnings)
        self.assertFalse(any("eval" in call or "close" in call for call in calls))
        self.assertFalse(result.coverage["session_cleanup_confirmed"])

    def test_preexisting_session_collision_must_not_be_reused_or_closed(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        provider, calls = self.provider(preexisting=True)
        with patch(
            "current.browser.uuid4",
            return_value=SimpleNamespace(hex="0" * 32),
        ):
            result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "browser_session_name_collision")
        self.assertFalse(any("open" in c or "close" in c or "eval" in c for c in calls))

    def test_mismatched_open_session_metadata_closes_only_verified_new_session(self):
        provider, calls = self.provider(open_session_name_matches=False)
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "unexpected_browser_session")
        self.assertFalse(any("eval" in call for call in calls))
        self.assertEqual(sum("close" in call for call in calls), 1)
        self.assertTrue(result.coverage["session_cleanup_confirmed"])

    def test_open_without_new_named_session_does_not_read_or_close(self):
        provider, calls = self.provider(register_session=False)
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertFalse(any("eval" in call or "close" in call for call in calls))
        self.assertTrue(result.coverage["session_cleanup_confirmed"])

    def test_open_response_failure_still_reconciles_and_closes_owned_session(self):
        provider, calls = self.provider(fail_after_open=True)
        with self.assertRaisesRegex(AdapterError, "simulated_open_response_lost"):
            provider.list_environments()
        self.assertFalse(any("eval" in call for call in calls))
        self.assertEqual(sum("close" in call for call in calls), 1)
        self.assertIn("close", calls[-2])

    def test_invalid_browser_type_identifier_is_rejected(self):
        for identifier in ("chrome-direct", "other", "chrome_local_12; echo bad"):
            with self.assertRaises(ValueError):
                BrowserSettings.from_mapping(
                    {
                        "executable": str(Path(tempfile.gettempdir()) / "browser-act.exe"),
                        "sha256": "a" * 64,
                        "browser_id": identifier,
                    }
                )

    def test_browser_stage_only_current_and_explicit_configuration(self):
        native = {
            "executable": str(Path(tempfile.gettempdir()) / "browser-act.exe"),
            "sha256": "a" * 64,
            "browser_id": BROWSER,
        }
        config = {
            "schema_version": 1,
            "domains": {
                "current": {
                    "stages": [{"kind": "browser_web", "approved": True, "browser": native}]
                }
            },
        }
        validate_configuration(config)
        config["domains"]["legacy"] = config["domains"].pop("current")
        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_builtin_web_surface_cannot_take_user_url(self):
        provider, _ = self.provider()
        from common.adapters import AdapterError

        with self.assertRaises(AdapterError):
            provider._transport("session", "https://example.org", {})


if __name__ == "__main__":
    unittest.main()
