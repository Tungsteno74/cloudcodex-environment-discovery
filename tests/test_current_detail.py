"""Single-ID Current GET: tested offline, with no account or Cloud mutations."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/cloudcodex-environment-discovery/runtime"))

from common.adapters import AdapterError, CommandReadTransport, CURRENT_CATALOG_SURFACES
from common.escalation import EscalatingProvider, Stage
from common.models import HttpResponse, ProviderResult
from common.service import EnvironmentDiscoveryService
from current.detail import direct_configuration_url, valid_configuration_id
from current.provider import CurrentCloudEnvironmentProvider

BASE = CURRENT_CATALOG_SURFACES["desktop"]
IDENTIFIER = "57292482-425b-4aaa-b7a5-cca86a030164~asenvcfg_f2f66481850c819190537a16ecf5a7e0"


class RecordingTransport:
    def __init__(self, status=200, body=None, mime="application/json", account=None,
                 verified=False):
        self.status, self.body, self.mime = status, body, mime
        self.account, self.verified = account, verified
        self.calls = []

    def __call__(self, url, query):
        self.calls.append((url, dict(query)))
        return HttpResponse(
            self.status, self.body, self.account, self.verified,
            content_type=self.mime,
        )


class CurrentDetailTests(unittest.TestCase):
    def record(self, **overrides):
        return {
            "id": IDENTIFIER, "name": "Fixture current config",
            "repository_ids": [1408634524], "published": True,
            **overrides,
        }

    def reader(self, **options):
        payload = options.pop("body", {"config": self.record()})
        transport = RecordingTransport(body=payload, **options)
        return CurrentCloudEnvironmentProvider(transport, use_picker=True), transport

    def test_known_config_id_uses_one_desktop_get_without_catalog_or_picker(self):
        provider, transport = self.reader()
        result = provider.get_environment(IDENTIFIER)
        self.assertEqual(transport.calls, [(BASE + "/" + IDENTIFIER, {})])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.environments), 1)
        self.assertEqual(result.environments[0].repository_id, "1408634524")
        self.assertFalse(result.catalog_complete)
        self.assertTrue(result.coverage["point_verified"])
        self.assertEqual(result.source, "current_direct_detail")

    def test_service_confirms_single_configuration_without_full_catalog(self):
        provider, transport = self.reader()
        result = EnvironmentDiscoveryService("current", provider).get_environment(IDENTIFIER)
        self.assertEqual(result["status"], "found")
        self.assertTrue(result["point_verified"])
        self.assertFalse(result["catalog_complete"])
        self.assertEqual(result["environment"]["environment_id"], IDENTIFIER)
        self.assertEqual(len(transport.calls), 1)

    def test_plain_detail_and_data_envelope_are_supported(self):
        for body in (self.record(), {"data": self.record()},
                     {"configuration": self.record()}):
            provider, _ = self.reader(body=body)
            self.assertEqual(provider.get_environment(IDENTIFIER).status, "ok")

    def test_mismatched_configuration_identity_is_not_a_valid_point(self):
        provider, _ = self.reader(body={"config": self.record(id="wrong-id")})
        result = provider.get_environment(IDENTIFIER)
        self.assertEqual(result.status, "invalid_response")
        self.assertFalse(result.coverage["point_verified"])
        self.assertEqual(len(result.environments), 0)

    def test_invalid_or_ambiguous_json_envelopes_fail_closed(self):
        for body in (
            [], {"config": None}, {"config": self.record(), "data": self.record()},
            {"items": [self.record()]},
        ):
            provider, _ = self.reader(body=body)
            self.assertEqual(provider.get_environment(IDENTIFIER).status, "invalid_response")

    def test_html_200_is_security_interstitial_not_single_record(self):
        provider, _ = self.reader(mime="text/html")
        result = provider.get_environment(IDENTIFIER)
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "security_interstitial_or_non_json")

    def test_http_401_403_404_429_are_not_success_or_global_absence(self):
        expected = {401: "unauthorized", 403: "forbidden",
                    404: "not_found", 429: "rate_limited"}
        for code, status in expected.items():
            provider, transport = self.reader(status=code, body=None)
            result = provider.get_environment(IDENTIFIER)
            self.assertEqual(result.status, status)
            self.assertEqual(result.reason, "http_" + str(code))
            self.assertFalse(result.coverage["point_verified"])
            self.assertFalse(result.catalog_complete)
            self.assertEqual(len(transport.calls), 1)

    def test_explicit_account_requires_provenance_not_trust_in_request(self):
        provider, transport = self.reader()
        result = provider.get_environment(IDENTIFIER, account="requester")
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.reason, "point_account_unverified_or_mismatch")
        self.assertEqual(len(transport.calls), 1)

    def test_verified_account_accepts_match_rejects_conflict(self):
        provider, _ = self.reader(account="account-1", verified=True)
        self.assertEqual(provider.get_environment(IDENTIFIER, account="account-1").status, "ok")
        self.assertEqual(provider.get_environment(IDENTIFIER, account="account-2").status, "forbidden")
        provider, _ = self.reader(
            account="account-1", verified=True,
            body={"config": self.record(account="other")},
        )
        self.assertEqual(provider.get_environment(IDENTIFIER).status, "forbidden")

    def test_invalid_paths_rejected_before_transport(self):
        for value in (None, "", "foo/bar", "?bad", "../escape", "a#b",
                      "a%2Fb", "."):
            self.assertFalse(valid_configuration_id(value))
            provider, transport = self.reader()
            with self.assertRaises(ValueError):
                provider.get_environment(value)
            self.assertFalse(transport.calls)
        self.assertTrue(valid_configuration_id(IDENTIFIER))
        self.assertEqual(direct_configuration_url(BASE, IDENTIFIER), BASE + "/" + IDENTIFIER)

    def test_web_surface_does_not_invent_a_point_route(self):
        provider, transport = self.reader()
        provider = CurrentCloudEnvironmentProvider(transport, api_surface="web")
        result = provider.get_environment(IDENTIFIER)
        self.assertEqual(result.reason, "point_route_not_observed_on_web")
        self.assertFalse(transport.calls)

    def test_no_transport_is_not_a_verified_empty_catalog(self):
        provider = CurrentCloudEnvironmentProvider()
        result = provider.get_environment(IDENTIFIER)
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.catalog_complete)

    def test_service_exposes_denial_without_stale_historical_id(self):
        provider, _ = self.reader(status=401, body=None)
        result = EnvironmentDiscoveryService("current", provider).get_environment(IDENTIFIER)
        self.assertEqual(result["status"], "unauthorized")
        self.assertEqual(result["provider"]["reason"], "http_401")
        self.assertIsNone(result["environment"])
        self.assertFalse(result["point_verified"])
        self.assertFalse(result["catalog_complete"])

    def test_http_relay_accepts_only_desktop_point_get(self):
        class Host:
            def __init__(self):
                self.requests = []

            def request(self, data):
                self.requests.append(data)
                return {
                    "schema_version": 1, "cloud_type": "current",
                    "status": 401,
                }

        host = Host()
        relay = CommandReadTransport("current", host, "desktop")
        response = relay(BASE + "/" + IDENTIFIER, {})
        self.assertEqual(response.status, 401)
        self.assertEqual(host.requests[0]["method"], "GET")
        self.assertEqual(host.requests[0]["query"], {})
        for url, query in (
            (BASE + "/" + IDENTIFIER + "/drafts/unknown", {}),
            (BASE + "/../arbitrary", {}),
            (BASE + "/" + IDENTIFIER, {"token": "not-allowed"}),
        ):
            with self.assertRaisesRegex(AdapterError, "unapproved_catalog"):
                relay(url, query)
        self.assertEqual(len(host.requests), 1)
        web_relay = CommandReadTransport("current", host, "web")
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_destination"):
            web_relay(BASE + "/" + IDENTIFIER, {})

    def test_escalation_stops_on_one_verified_point_without_catalog(self):
        primary, calls = self.reader()

        class Later:
            name = "current"
            touched = False

            def list_environments(self, **kwargs):
                self.touched = True
                return ProviderResult(provider=self.name, status="ok")

        later = Later()
        chain = EscalatingProvider(
            "current", [Stage("http", primary), Stage("snapshot", later)]
        )
        output = EnvironmentDiscoveryService("current", chain).get_environment(IDENTIFIER)
        self.assertEqual(output["status"], "found")
        self.assertTrue(output["point_verified"])
        self.assertFalse(output["catalog_complete"])
        self.assertEqual(len(output["provider"]["attempts"]), 1)
        self.assertFalse(later.touched)
        self.assertEqual(len(calls.calls), 1)

    def test_escalation_401_is_terminal_even_with_a_later_valid_source(self):
        first, _ = self.reader(status=401, body=None)
        later, second_transport = self.reader()
        chain = EscalatingProvider(
            "current", [Stage("webcmd", first), Stage("http", later)]
        )
        output = EnvironmentDiscoveryService("current", chain).get_environment(IDENTIFIER)
        self.assertEqual(output["status"], "unauthorized")
        self.assertFalse(output["point_verified"])
        self.assertEqual([a["stage"] for a in output["provider"]["attempts"]], ["webcmd"])
        self.assertFalse(second_transport.calls)

    def test_recoverable_missing_transport_may_escalate_to_other_preapproved_source(self):
        first = CurrentCloudEnvironmentProvider()
        second, transport = self.reader()
        chain = EscalatingProvider("current", [
            Stage("webcmd", first), Stage("http", second),
        ])
        output = EnvironmentDiscoveryService("current", chain).get_environment(IDENTIFIER)
        self.assertEqual(output["status"], "found")
        self.assertEqual([a["stage"] for a in output["provider"]["attempts"]],
                         ["webcmd", "http"])
        self.assertEqual(len(transport.calls), 1)

    def test_successful_point_cannot_resolve_repository_without_complete_catalog(self):
        provider, _ = self.reader()
        # The exact ID is confirmable, but the repository->environment lookup
        # still needs a catalog and must not assert absence or completeness.
        result = EnvironmentDiscoveryService("current", provider).get_environment(IDENTIFIER)
        self.assertTrue(result["point_verified"])
        self.assertFalse(result["catalog_complete"])


if __name__ == "__main__":
    unittest.main()
