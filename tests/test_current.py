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
        self.assertFalse(result.catalog_complete)
        self.assertEqual(result.status, "partial")
        self.assertTrue(result.coverage["picker_view_only"])

    def test_query_is_current_catalog_endpoint_only(self):
        urls = []
        def request(url, args):
            urls.append(url)
            return HttpResponse(200, {"items": []})
        current_provider(request).list_environments()
        self.assertEqual(urls, [
            "https://codex-cloud-backend.chatgpt.com/v1/environment-configs"
        ] * 2)

    def test_published_catalog_prefers_picker_view(self):
        seen = []

        def request(url, args):
            seen.append(dict(args))
            return HttpResponse(200, {"items": []})

        result = current_provider(request, scopes=("user",)).list_environments()
        self.assertEqual(len(seen), 1)
        self.assertFalse(result.catalog_complete)
        self.assertTrue(result.coverage["picker_view_only"])
        self.assertEqual(seen[0]["view"], "picker")
        self.assertEqual(seen[0]["omitDraft"], "true")

    def test_picker_http_400_falls_back_once_to_standard_list(self):
        seen = []

        def request(url, args):
            seen.append(dict(args))
            if args.get("view") == "picker":
                return HttpResponse(400, {})
            return HttpResponse(
                200,
                {
                    "data": [
                        {
                            "id": "cfg-fallback",
                            "name": "Fallback",
                            "repository_ids": ["7"],
                            "versionRevision": 2,
                        }
                    ]
                },
            )

        result = current_provider(request, scopes=("user",)).list_environments()
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.catalog_complete)
        self.assertNotIn("picker_view_only", result.coverage)
        self.assertEqual(result.environments[0].environment_id, "cfg-fallback")
        self.assertEqual([query.get("view") for query in seen], ["picker", None])

    def test_picker_400_full_standard_list_keeps_all_existing_revisions(self):
        def request(url, args):
            if args.get("view") == "picker":
                return HttpResponse(400, {})
            return HttpResponse(
                200,
                {
                    "data": [
                        {"id": "old", "name": "Old", "versionRevision": 1},
                        {
                            "id": "saved",
                            "name": "Saved",
                            "version_revision": 2,
                            "repository_ids": ["7"],
                        },
                    ]
                },
            )

        result = current_provider(request, scopes=("user",)).list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual(
            [item.environment_id for item in result.environments],
            ["old", "saved"],
        )
        self.assertEqual(result.environments[1].repository_id, "7")

    def test_picker_denial_never_falls_back_to_standard_list(self):
        for code, status in ((401, "unauthorized"), (403, "forbidden"), (429, "rate_limited")):
            seen = []

            def request(url, args, response_code=code):
                seen.append(dict(args))
                return HttpResponse(response_code, {})

            result = current_provider(request, scopes=("user",)).list_environments()
            self.assertEqual(result.status, status)
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0].get("view"), "picker")

    def test_include_drafts_skips_picker_view(self):
        seen = []

        def request(url, args):
            seen.append(dict(args))
            return HttpResponse(200, {"items": []})

        current_provider(request, scopes=("user",)).list_environments(include_drafts=True)
        self.assertEqual(len(seen), 1)
        self.assertNotIn("view", seen[0])
        self.assertEqual(seen[0]["omitDraft"], "false")

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

    def test_standard_web_scope_empty_complete(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {"items": []}),
            api_surface="web",
        ).list_environments()
        self.assertEqual(result.status, "empty")
        self.assertTrue(result.catalog_complete)

    def test_picker_empty_cannot_prove_no_current_environments(self):
        result = current_provider(
            lambda url, args: HttpResponse(200, {"items": []})
        ).list_environments()
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.catalog_complete)
        self.assertEqual(result.environments, [])
        self.assertTrue(result.coverage["picker_view_only"])

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

    def test_current_catalog_cache_repository_ids_are_preserved(self):
        result = current_provider(
            lambda url, args: HttpResponse(
                200,
                {
                    "data": [
                        {
                            "id": "cfg-cache",
                            "name": "cloudcodex-windows-bootstrap-e2e-cloud-auto",
                            "repository_ids": ["1408634524"],
                        }
                    ],
                    "next_cursor": None,
                },
            ),
            scopes=("user",),
        ).list_environments()
        entry = result.environments[0]
        self.assertEqual(entry.environment_id, "cfg-cache")
        self.assertEqual(entry.repository_id, "1408634524")
        self.assertEqual(
            entry.repositories,
            ({"repository": None, "repository_id": "1408634524"},),
        )

    def test_current_normalized_catalog_repositoryId_is_preserved(self):
        result = current_provider(
            lambda url, args: HttpResponse(
                200,
                {
                    "data": [
                        {
                            "id": "cfg-normalized",
                            "name": "Current config",
                            "repositories": [
                                {"repositoryId": "1408634524", "ref": "main"}
                            ],
                            "versionRevision": 4,
                        }
                    ]
                },
            ),
            scopes=("user",),
        ).list_environments()
        entry = result.environments[0]
        self.assertEqual(entry.repository_id, "1408634524")
        self.assertEqual(entry.configuration_version, "4")

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
            request, scopes=("user",), api_surface="web"
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
            }), scopes=("user",), api_surface="web"
        )
        result = build_current_service(provider).resolve_environment(
            repository="owner/repo"
        )
        self.assertEqual(result["status"], "resolved")

    def test_picker_only_exact_match_remains_unverified(self):
        provider = current_provider(
            lambda url, args: HttpResponse(200, {
                "items": [{
                    "id": "cfg-picker",
                    "name": "Selected Current",
                    "repositories": [{"repository_id": "7"}],
                }]
            }),
            scopes=("user",),
        )
        result = build_current_service(provider).resolve_environment(repository="7")
        self.assertEqual(result["status"], "unverified")
        self.assertIsNone(result["selected"])
        self.assertFalse(result["catalog_complete"])

    def test_picker_positive_repository_counterpart_without_full_coverage(self):
        provider = current_provider(
            lambda url, args: HttpResponse(
                200,
                {"data": [
                    {
                        "id": "cfg-picker-known",
                        "name": "Current config",
                        "repository_ids": ["1408634524"],
                    }
                ]},
            ),
            scopes=("user",),
        )
        service = build_current_service(provider)
        result = service.find_environments("1408634524")
        self.assertFalse(result["catalog_complete"])
        self.assertEqual(result["repository_counterpart"]["status"], "verified")
        self.assertEqual(result["environments"][0]["environment_id"], "cfg-picker-known")
        self.assertEqual(
            service.resolve_environment(name="not-in-picker")["status"],
            "not_verifiable",
        )

    def test_current_does_not_import_legacy(self):
        text = (RUNTIME / "current/provider.py").read_text(encoding="utf-8")
        self.assertNotIn("from legacy", text)
        api = (RUNTIME / "current/api.py").read_text(encoding="utf-8")
        self.assertNotIn("from legacy", api)


if __name__ == "__main__":
    unittest.main()
