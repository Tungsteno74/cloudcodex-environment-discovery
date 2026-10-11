"""Current-generation-only provider tests; no Legacy dependency."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "plugins/cloudcodex-environment-discovery/runtime"
sys.path.insert(0, str(RUNTIME))

from common.models import HttpResponse  # noqa: E402
from current.api import build_current_service  # noqa: E402
from current.provider import CurrentCloudEnvironmentProvider  # noqa: E402


def current_provider(transport, **kwargs):
    return CurrentCloudEnvironmentProvider(transport=transport, **kwargs)


class CurrentProviderTests(unittest.TestCase):
    def test_missing_authorized_transport_is_unavailable(self):
        result = CurrentCloudEnvironmentProvider().list_environments()
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.catalog_complete)

    def test_current_service_never_lists_legacy_by_default(self):
        result = build_current_service().list_environments()
        self.assertEqual(result["cloud_type"], "current")
        self.assertEqual(result["provider"]["provider"], "current")

    def test_current_service_has_no_cloud_type_parameter(self):
        service = build_current_service()
        with self.assertRaises(TypeError):
            service.list_environments(cloud_type="all")

    def test_explicit_user_workspace_scopes(self):
        seen = []
        def request(url, args):
            seen.append(dict(args))
            return HttpResponse(200, {"items": []})
        result = current_provider(request).list_environments()
        self.assertEqual([x["scope"] for x in seen], ["user", "workspace"])
        self.assertTrue(result.catalog_complete)

    def test_query_is_current_catalog_endpoint_only(self):
        urls = []
        def request(url, args):
            urls.append(url)
            return HttpResponse(200, {"items": []})
        current_provider(request).list_environments()
        self.assertEqual(urls, [
            "https://codex-cloud-backend.chatgpt.com/v1/environment-configs"
        ] * 2)

    def test_omit_draft_true_by_default(self):
        seen = []
        def request(url, args):
            seen.append(args["omitDraft"])
            return HttpResponse(200, {"items": []})
        current_provider(request).list_environments()
        self.assertEqual(seen, ["true", "true"])

    def test_include_drafts_explicit(self):
        seen = []
        def request(url, args):
            seen.append(args["omitDraft"])
            return HttpResponse(200, {"items": []})
        current_provider(request).list_environments(include_drafts=True)
        self.assertEqual(seen, ["false", "false"])

    def test_scope_empty_complete(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {"items": []})
        ).list_environments()
        self.assertEqual(result.status, "empty")
        self.assertTrue(result.catalog_complete)

    def test_current_normalizes_config_id(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {
                "items": [{
                    "configId": "cfg-1", "name": "Config",
                    "repositories": [{"repository_id": 8,
                                      "full_name": "Owner/Repo"}],
                    "published": True,
                }]
            }), scopes=("user",)
        ).list_environments()
        self.assertEqual(result.environments[0].environment_id, "cfg-1")
        self.assertEqual(result.environments[0].cloud_type, "current")
        self.assertEqual(result.environments[0].repository_id, "8")
        self.assertEqual(result.environments[0].configuration_state, "published")

    def test_unauthorized_stops_other_scopes(self):
        seen = []
        def request(url, args):
            seen.append(args["scope"])
            return HttpResponse(401, {"secret": "DO_NOT_REPORT"})
        result = current_provider(request).list_environments()
        self.assertEqual(result.status, "unauthorized")
        self.assertEqual(seen, ["user"])
        self.assertNotIn("DO_NOT_REPORT", repr(result.to_dict()))

    def test_forbidden_workspace_keeps_partial_user(self):
        def request(url, args):
            return (
                HttpResponse(200, {"items": [{"id": "cfg-1"}]})
                if args["scope"] == "user"
                else HttpResponse(403, {})
            )
        result = current_provider(request).list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(len(result.environments), 1)
        self.assertFalse(result.catalog_complete)

    def test_404_not_authoritative_empty(self):
        result = current_provider(
            lambda url, args: HttpResponse(404, {})
        ).list_environments()
        self.assertEqual(result.status, "not_found")
        self.assertFalse(result.catalog_complete)

    def test_unknown_shape_invalid(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {"unknown": []})
        ).list_environments()
        self.assertEqual(result.status, "invalid_response")

    def test_cursor_loop_partial(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {
                "items": [], "next_cursor": "same",
            }), scopes=("user",)
        ).list_environments()
        self.assertEqual(result.status, "partial")

    def test_pagination_limit_stops_loop(self):
        def request(url, args):
            return HttpResponse(200, {
                "items": [], "next_cursor": "cursor-" + args.get("cursor", "start"),
            })
        result = current_provider(
            request, scopes=("user",), page_limit=2,
        ).list_environments()
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.catalog_complete)

    def test_successful_pagination(self):
        def request(url, args):
            return (
                HttpResponse(200, {"items": [{"id": "cfg-2"}]})
                if args.get("cursor") == "page2"
                else HttpResponse(
                    200, {"items": [{"id": "cfg-1"}], "next_cursor": "page2"}
                )
            )
        result = current_provider(
            request, scopes=("user",)
        ).list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual(len(result.environments), 2)

    def test_duplicate_id_deduplicated(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {
                "items": [{"id": "cfg-1"}, {"id": "cfg-1"}]
            }), scopes=("user",)
        ).list_environments()
        self.assertEqual(len(result.environments), 1)

    def test_invalid_scope_rejected(self):
        with self.assertRaises(ValueError):
            CurrentCloudEnvironmentProvider(scopes=("admin",))

    def test_invalid_page_limit_rejected(self):
        with self.assertRaises(ValueError):
            CurrentCloudEnvironmentProvider(page_limit=0)

    def test_transport_error_fails_closed(self):
        def broken(url, args):
            raise OSError("offline")
        result = current_provider(broken).list_environments()
        self.assertEqual(result.status, "unavailable")

    def test_current_service_verified_resolution(self):
        provider = current_provider(
            lambda url, args: HttpResponse(200, {
                "items": [{
                    "id": "cfg-1", "name": "Independent Current",
                    "repository": {"full_name": "Owner/Repo"},
                }]
            }), scopes=("user",)
        )
        result = build_current_service(provider).resolve_environment(
            repository="owner/repo"
        )
        self.assertEqual(result["status"], "resolved")

    def test_current_does_not_import_legacy(self):
        text = (RUNTIME / "current/provider.py").read_text(encoding="utf-8")
        self.assertNotIn("from legacy", text)
        api = (RUNTIME / "current/api.py").read_text(encoding="utf-8")
        self.assertNotIn("from legacy", api)


if __name__ == "__main__":
    unittest.main()
