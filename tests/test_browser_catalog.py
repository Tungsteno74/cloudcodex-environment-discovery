"""Current BrowserAct adapter contract without network, credentials or GUI."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/cloudcodex-environment-discovery/runtime"))
from current.browser import BrowserSettings, BrowserActCatalogProvider
from common.configuration import validate_configuration

BROWSER = "chrome_local_12345"


class BrowserTests(unittest.TestCase):
    def provider(self, status=200, mime="application/json", metadata_type="chrome", confirm=False,
                 reused=False, returned_id=BROWSER):
        calls = []

        class Client:
            def __init__(self, spec):
                self.args = spec.argv
                calls.append(self.args)

            def request(self, payload):
                args = self.args
                if "list" in args:
                    return {
                        "ok": True,
                        "browsers": [
                            {"id": BROWSER, "type": metadata_type, "confirm_before_use": confirm}
                        ],
                    }
                if "open" in args:
                    return {
                        "ok": True,
                        "reused": reused,
                        "browser_type": "chrome",
                        "browser_id": returned_id,
                    }
                if "close" in args:
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
        self.assertIn("close", calls[-1])
        self.assertTrue(all("--no-auto-dialog" in c for c in calls))

    def test_forbidden_stops_before_second_scope_and_closes(self):
        provider, calls = self.provider(status=403, mime="text/html")
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(sum("eval" in c for c in calls), 1)
        self.assertIn("close", calls[-1])

    def test_nonjson_200_is_not_catalog(self):
        provider, calls = self.provider(mime="text/html")
        self.assertEqual(provider.list_environments().status, "forbidden")
        self.assertIn("close", calls[-1])

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

    def test_reused_browser_session_is_neither_read_nor_closed(self):
        provider, calls = self.provider(reused=True)
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "unexpected_browser_session")
        self.assertFalse(any("eval" in call or "close" in call for call in calls))

    def test_missing_fresh_session_claim_does_not_grant_ownership(self):
        provider, calls = self.provider(reused=None)
        self.assertEqual(provider.list_environments().status, "forbidden")
        self.assertFalse(any("eval" in call or "close" in call for call in calls))

    def test_other_browser_returned_is_not_operated_on(self):
        provider, calls = self.provider(returned_id="chrome_local_999")
        result = provider.list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertTrue(result.warnings)
        self.assertFalse(any("eval" in call or "close" in call for call in calls))

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
