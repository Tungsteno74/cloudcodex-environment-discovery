"""Offline validation of read-only provider behavior and Root resolution."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-cloud-environment-discovery"
sys.path.insert(0, str(PLUGIN / "runtime"))

from discovery.models import (  # noqa: E402
    EnvironmentDescriptor, HttpResponse, ProviderResult, extract_page,
    normalize_repository, parse_environment,
)
from discovery.providers import (  # noqa: E402
    CurrentCloudEnvironmentProvider, LegacyEnvironmentProvider,
    SnapshotEnvironmentProvider,
)
from discovery.service import DiscoveryFacade, repository_match  # noqa: E402


class StaticProvider:
    def __init__(self, name: str, descriptors: List[EnvironmentDescriptor],
                 complete: bool = True, status: str = "ok"):
        self.name = name
        self._descriptors = descriptors
        self._complete = complete
        self._status = status

    def list_environments(self, account=None, include_drafts=False):
        return ProviderResult(
            provider=self.name, status=self._status,
            catalog_complete=self._complete,
            environments=self._descriptors, evidence="live",
        )


def environment(identifier="legacy-1", name="Alpha", repo="example/demo",
                evidence="live", cloud_type="legacy", repo_id="17"):
    return EnvironmentDescriptor(
        cloud_type=cloud_type, environment_id=identifier, name=name,
        repository=repo, repository_id=repo_id, evidence=evidence,
        discovery_source="test_live",
    )


class ContractsTests(unittest.TestCase):
    def test_normalize_full_name(self):
        self.assertEqual(normalize_repository("Example/Demo"), "example/demo")

    def test_normalize_github_url(self):
        self.assertEqual(normalize_repository("https://github.com/Example/Demo.git"),
                         "example/demo")

    def test_invalid_repository(self):
        self.assertIsNone(normalize_repository("one-component"))

    def test_descriptor_requires_identifier(self):
        with self.assertRaises(ValueError):
            environment(identifier="")

    def test_descriptor_rejects_evidence_outside_contract(self):
        with self.assertRaises(ValueError):
            environment(evidence="fabricated")

    def test_repository_id_verifies_first(self):
        self.assertEqual(repository_match(environment(), "17"), "verified")

    def test_explicit_repository_association_verifies(self):
        self.assertEqual(repository_match(environment(), "Example/Demo"), "verified")

    def test_environment_name_is_only_hint(self):
        entry = environment(repo=None, name="demo")
        self.assertEqual(repository_match(entry, "example/demo"), "hint")

    def test_other_repository_is_no_match(self):
        self.assertEqual(repository_match(environment(), "other/repo"), "none")

    def test_parse_environment_does_not_infer_repo_from_name(self):
        d = parse_environment(
            {"id": "abc", "name": "owner/repo"}, "legacy", "user",
            "native_cli",
        )
        self.assertIsNone(d.repository)

    def test_parse_known_current_repository_association(self):
        d = parse_environment({
            "configId": "cfg-1", "name": "Config",
            "repositories": [{"repository_id": 123,
                              "full_name": "Owner/Repo"}],
            "draft": True,
        }, "current", "workspace", "catalog")
        self.assertEqual(d.repository_id, "123")
        self.assertEqual(d.repository, "owner/repo")
        self.assertEqual(d.configuration_state, "draft")

    def test_parse_unknown_configuration_state(self):
        d = parse_environment({"id": "abc", "status": "queued"},
                              "current", "user", "catalog")
        self.assertEqual(d.configuration_state, "unknown")

    def test_unknown_envelope_never_empty(self):
        with self.assertRaises(ValueError):
            extract_page({"message": "okay"})

    def test_has_more_without_cursor_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_page({"items": [], "has_more": True})

    def test_nested_pagination_is_supported(self):
        items, cursor = extract_page({
            "items": [], "pagination": {"nextCursor": "opaque"}
        })
        self.assertEqual(items, [])
        self.assertEqual(cursor, "opaque")


class ProviderTests(unittest.TestCase):
    def test_legacy_without_native_reader_or_transport_is_unavailable(self):
        result = LegacyEnvironmentProvider().list_environments()
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.catalog_complete)

    def test_legacy_401_is_unauthorized_not_empty(self):
        provider = LegacyEnvironmentProvider(
            transport=lambda url, params: HttpResponse(401, {"error": "secret"}),
        )
        result = provider.list_environments()
        self.assertEqual(result.status, "unauthorized")
        self.assertNotIn("secret", repr(result.to_dict()))

    def test_legacy_valid_authorized_get(self):
        provider = LegacyEnvironmentProvider(
            transport=lambda url, params: HttpResponse(
                200, {"environments": [{"id": "leg-1", "label": "demo"}]}
            )
        )
        result = provider.list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual(result.environments[0].environment_id, "leg-1")

    def test_legacy_selector_preferred_to_transport(self):
        invoked = []
        def selector(account):
            invoked.append(account)
            return ProviderResult(provider="legacy", status="ok", evidence="live",
                                  catalog_complete=True,
                                  environments=[environment()])
        provider = LegacyEnvironmentProvider(
            selector_reader=selector,
            transport=lambda url, params: self.fail("HTTP fallback must not run"),
        )
        self.assertEqual(provider.list_environments(account="test").status, "ok")
        self.assertEqual(invoked, ["test"])

    def test_current_without_authorized_transport_unavailable(self):
        result = CurrentCloudEnvironmentProvider().list_environments()
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.catalog_complete)

    def test_current_authorized_scopes_complete(self):
        calls = []
        def request(url, params):
            calls.append(dict(params))
            return HttpResponse(200, {"items": [
                {"id": "cfg-1", "name": "Current", "published": True}
            ]})
        result = CurrentCloudEnvironmentProvider(transport=request).list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual(len(result.environments), 1)
        self.assertEqual([x["scope"] for x in calls], ["user", "workspace"])
        self.assertEqual(calls[0]["omitDraft"], "true")

    def test_include_drafts_sets_explicit_parameter(self):
        parameters = []
        def request(url, params):
            parameters.append(params)
            return HttpResponse(200, {"items": []})
        CurrentCloudEnvironmentProvider(
            transport=request, scopes=("user",)
        ).list_environments(include_drafts=True)
        self.assertEqual(parameters[0]["omitDraft"], "false")

    def test_current_401_does_not_retry_other_scope(self):
        calls = []
        def request(url, params):
            calls.append(params)
            return HttpResponse(401, {})
        result = CurrentCloudEnvironmentProvider(transport=request).list_environments()
        self.assertEqual(result.status, "unauthorized")
        self.assertEqual(len(calls), 1)
        self.assertFalse(result.catalog_complete)

    def test_current_403_after_user_scope_keeps_partial_evidence(self):
        def request(url, params):
            if params["scope"] == "user":
                return HttpResponse(200, {"items": [
                    {"id": "cfg-1", "name": "Config"}
                ]})
            return HttpResponse(403, {})
        result = CurrentCloudEnvironmentProvider(transport=request).list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(len(result.environments), 1)
        self.assertFalse(result.catalog_complete)

    def test_current_unknown_schema_is_not_empty(self):
        result = CurrentCloudEnvironmentProvider(
            transport=lambda url, params: HttpResponse(200, {"bad": []}),
            scopes=("user",),
        ).list_environments()
        self.assertEqual(result.status, "invalid_response")

    def test_current_cursor_loop_detected(self):
        result = CurrentCloudEnvironmentProvider(
            transport=lambda url, params: HttpResponse(
                200, {"items": [], "next_cursor": "same"}
            ),
            scopes=("user",),
        ).list_environments()
        self.assertEqual(result.status, "partial")

    def test_current_page_limit_cannot_claim_completeness(self):
        result = CurrentCloudEnvironmentProvider(
            transport=lambda url, params: HttpResponse(
                200, {"items": [], "next_cursor": "cursor-"+str(
                    params.get("cursor", "begin")
                )}
            ),
            scopes=("user",), page_limit=2,
        ).list_environments()
        self.assertFalse(result.catalog_complete)

    def test_current_pagination_can_complete(self):
        def request(url, params):
            if params.get("cursor") == "page2":
                return HttpResponse(200, {"items": [
                    {"id": "cfg-2", "name": "B"}
                ]})
            return HttpResponse(200, {"items": [
                {"id": "cfg-1", "name": "A"}
            ], "next_cursor": "page2"})
        result = CurrentCloudEnvironmentProvider(
            transport=request, scopes=("user",)
        ).list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual(len(result.environments), 2)

    def test_invalid_scope_rejected(self):
        with self.assertRaises(ValueError):
            CurrentCloudEnvironmentProvider(scopes=("admin",))

    def test_legacy_unknown_schema_not_an_empty_catalog(self):
        result = LegacyEnvironmentProvider(
            transport=lambda url, params: HttpResponse(200, {"error": "wrong"}),
        ).list_environments()
        self.assertEqual(result.status, "invalid_response")

    def test_imported_snapshot_never_becomes_live(self):
        result = SnapshotEnvironmentProvider(
            "legacy", {"items": [
                {"id": "import-1", "name": "Saved", "evidence": "live"}
            ]}
        ).list_environments()
        self.assertFalse(result.catalog_complete)
        self.assertEqual(result.environments[0].evidence, "imported")
        self.assertEqual(result.status, "partial")

    def test_snapshot_excludes_drafts_by_default(self):
        result = SnapshotEnvironmentProvider(
            "current", {"items": [
                {"id": "cfg-draft", "name": "D", "draft": True},
                {"id": "cfg-published", "name": "P", "published": True},
            ]}
        ).list_environments()
        self.assertEqual(len(result.environments), 1)

    def test_imported_unknown_envelope_invalid(self):
        result = SnapshotEnvironmentProvider("legacy", {"other": "value"}).list_environments()
        self.assertEqual(result.status, "invalid_response")


class FacadeTests(unittest.TestCase):
    def test_default_unavailable_does_not_claim_absence(self):
        from discovery.api import build_default_facade
        result = build_default_facade().list_environments()
        self.assertFalse(result["catalog_complete"])
        self.assertEqual(len(result["providers"]), 2)

    def test_single_live_provider_can_resolve_uniquely(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider("legacy", [environment()])
        })
        result = facade.resolve_environment(
            repository="example/demo", cloud_type="legacy"
        )
        self.assertEqual(result["status"], "resolved")

    def test_all_cloud_requires_all_requested_providers(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider("legacy", [environment()])
        })
        result = facade.resolve_environment(repository="example/demo")
        self.assertEqual(result["status"], "unverified")

    def test_two_live_matches_are_ambiguous(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider(
                "legacy", [environment("1"), environment("2")]
            )
        })
        result = facade.resolve_environment(
            repository="example/demo", cloud_type="legacy"
        )
        self.assertEqual(result["status"], "ambiguous")

    def test_heuristic_name_match_is_not_verified(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider("legacy", [
                environment(name="demo", repo=None)
            ])
        })
        result = facade.resolve_environment(
            repository="example/demo", cloud_type="legacy"
        )
        self.assertEqual(result["status"], "unverified")

    def test_imported_snapshot_cannot_resolve(self):
        facade = DiscoveryFacade({
            "legacy": SnapshotEnvironmentProvider(
                "legacy", {"items": [
                    {"id": "s", "name": "demo", "repository": "example/demo"}
                ]}
            )
        })
        result = facade.resolve_environment(
            repository="example/demo", cloud_type="legacy"
        )
        self.assertEqual(result["status"], "unverified")

    def test_get_missing_in_complete_catalog_is_not_found(self):
        facade = DiscoveryFacade({"legacy": StaticProvider("legacy", [])})
        result = facade.get_environment("legacy", "missing")
        self.assertEqual(result["status"], "not_found")

    def test_get_missing_in_partial_catalog_not_verifiable(self):
        facade = DiscoveryFacade({})
        result = facade.get_environment("legacy", "missing")
        self.assertEqual(result["status"], "not_verifiable")

    def test_identical_ids_in_different_types_remain_separate(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider("legacy", [environment("same")]),
            "current": StaticProvider("current", [
                environment("same", cloud_type="current")
            ]),
        })
        result = facade.list_environments()
        self.assertEqual(len(result["environments"]), 2)

    def test_invalid_repo_rejected(self):
        facade = DiscoveryFacade({})
        with self.assertRaises(ValueError):
            facade.find_environments("invalid")

    def test_filter_matches_repository_id(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider("legacy", [environment(repo_id="17")])
        })
        result = facade.find_environments("17", cloud_type="legacy")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["environments"][0]["repository_match"], "verified")

    def test_requested_account_requires_observed_identity(self):
        facade = DiscoveryFacade({
            "legacy": StaticProvider("legacy", [environment()])
        })
        result = facade.resolve_environment(
            repository="example/demo", cloud_type="legacy", account="named-account"
        )
        self.assertEqual(result["status"], "unverified")
        self.assertFalse(result["catalog_complete"])

    def test_snapshots_reject_credential_file_paths(self):
        with self.assertRaises(ValueError):
            SnapshotEnvironmentProvider.from_file(
                "legacy", Path(".codex") / "auth.json"
            )


if __name__ == "__main__":
    unittest.main()
