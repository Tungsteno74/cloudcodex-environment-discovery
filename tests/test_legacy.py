"""Legacy-only discovery provider regression suite."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "plugins/cloudcodex-environment-discovery/runtime"
sys.path.insert(0, str(RUNTIME))

from common.models import EnvironmentDescriptor, HttpResponse, ProviderResult  # noqa: E402
from legacy.api import build_legacy_service, build_legacy_snapshot_service  # noqa: E402
from legacy.provider import LegacyEnvironmentProvider  # noqa: E402


def transport_result(status=200, body=None):
    if body is None:
        body = {"environments": [{"id": "old-1", "label": "Old Cloud"}]}
    return lambda url, params: HttpResponse(status, body)


class LegacyProviderTests(unittest.TestCase):
    def test_unconfigured_provider_explicitly_unavailable(self):
        result = LegacyEnvironmentProvider().list_environments()
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.catalog_complete)

    def test_unavailable_does_not_mean_empty(self):
        output = build_legacy_service().list_environments()
        self.assertNotEqual(output["status"], "empty")
        self.assertFalse(output["catalog_complete"])

    def test_missing_native_selector_mentions_zero_task_semantics(self):
        result = LegacyEnvironmentProvider().list_environments()
        self.assertTrue(any("lists tasks" in x for x in result.warnings))

    def test_legacy_selector_used_before_http(self):
        calls = []
        def selector(account):
            calls.append(account)
            return ProviderResult(
                provider="legacy", status="ok", catalog_complete=True,
                evidence="live", environments=[
                    EnvironmentDescriptor(
                        cloud_type="legacy", environment_id="old-1",
                        name="Old Cloud", evidence="live",
                    )
                ],
            )
        provider = LegacyEnvironmentProvider(
            selector_reader=selector,
            transport=lambda url, params: self.fail(
                "native selector should take priority"
            ),
        )
        result = provider.list_environments(account="account")
        self.assertEqual(calls, ["account"])
        self.assertEqual(result.environments[0].environment_id, "old-1")

    def test_native_selector_wrong_type_fails_closed(self):
        provider = LegacyEnvironmentProvider(
            selector_reader=lambda account: ProviderResult(provider="other")
        )
        self.assertEqual(provider.list_environments().status, "unavailable")

    def test_native_selector_error_fails_closed(self):
        def failing(account):
            raise ValueError("read failed")
        provider = LegacyEnvironmentProvider(selector_reader=failing)
        self.assertEqual(provider.list_environments().status, "unavailable")

    def test_http_get_uses_legacy_endpoint_only(self):
        urls = []
        def request(url, params):
            urls.append(url)
            return HttpResponse(200, {"environments": []})
        result = LegacyEnvironmentProvider(transport=request).list_environments()
        self.assertEqual(len(urls), 1)
        self.assertEqual(
            urls[0], "https://chatgpt.com/backend-api/wham/environments"
        )
        self.assertEqual(result.status, "empty")
        self.assertTrue(result.catalog_complete)

    def test_http_200_normalizes_label_and_id(self):
        result = LegacyEnvironmentProvider(
            transport=transport_result()
        ).list_environments()
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.catalog_complete)
        self.assertEqual(result.environments[0].environment_id, "old-1")
        self.assertEqual(result.environments[0].cloud_type, "legacy")

    def test_http_401_blocks(self):
        result = LegacyEnvironmentProvider(
            transport=transport_result(401, {"token": "DO_NOT_EXPOSE"})
        ).list_environments()
        self.assertEqual(result.status, "unauthorized")
        self.assertNotIn("DO_NOT_EXPOSE", repr(result.to_dict()))

    def test_http_403_blocks(self):
        result = LegacyEnvironmentProvider(
            transport=transport_result(403, {})
        ).list_environments()
        self.assertEqual(result.status, "forbidden")

    def test_http_404_not_reported_as_empty(self):
        result = LegacyEnvironmentProvider(
            transport=transport_result(404, {})
        ).list_environments()
        self.assertEqual(result.status, "not_found")
        self.assertFalse(result.catalog_complete)

    def test_unknown_schema_is_invalid(self):
        result = LegacyEnvironmentProvider(
            transport=transport_result(200, {"message": "success"})
        ).list_environments()
        self.assertEqual(result.status, "invalid_response")

    def test_unexpected_cursor_yields_partial(self):
        result = LegacyEnvironmentProvider(
            transport=transport_result(
                200, {"environments": [{"id": "old-1"}], "next_cursor": "next"}
            )
        ).list_environments()
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.catalog_complete)

    def test_transport_failure_yields_unavailable(self):
        def broken(url, params):
            raise OSError("offline")
        result = LegacyEnvironmentProvider(transport=broken).list_environments()
        self.assertEqual(result.status, "unavailable")

    def test_legacy_service_finds_explicit_repo(self):
        provider = LegacyEnvironmentProvider(
            transport=transport_result(200, {
                "environments": [{
                    "id": "old-1", "name": "Arbitrary Label",
                    "repository": {"full_name": "Owner/Repo", "id": "12"},
                }]
            })
        )
        service = build_legacy_service(provider)
        self.assertEqual(
            service.resolve_environment(repository="owner/repo")["status"],
            "resolved",
        )

    def test_legacy_service_does_not_require_current(self):
        service = build_legacy_service()
        self.assertEqual(service.cloud_type, "legacy")
        source = (RUNTIME / "legacy/provider.py").read_text(encoding="utf-8")
        self.assertNotIn("from current", source)

    def test_legacy_snapshot_not_live(self):
        from common.snapshot import SnapshotEnvironmentProvider
        from common.service import EnvironmentDiscoveryService
        service = EnvironmentDiscoveryService(
            "legacy", SnapshotEnvironmentProvider("legacy", {
                "items": [{
                    "id": "old-1", "repository": "owner/repo",
                    "name": "Old Cloud",
                }]
            })
        )
        self.assertEqual(
            service.resolve_environment(repository="owner/repo")["status"],
            "unverified",
        )


if __name__ == "__main__":
    unittest.main()
