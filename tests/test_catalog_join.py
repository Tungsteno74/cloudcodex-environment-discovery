"""Complete GitHub inventory, Cloud correlations and explicit Current routes."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/cloudcodex-environment-discovery/runtime"))
from common.github import GitHubSettings, NativeGitHubRepositoryResolver
from common.correlation import correlate_repositories
from common.models import EnvironmentDescriptor, ProviderResult, HttpResponse
from common.service import EnvironmentDiscoveryService
from common.adapters import CommandReadTransport, AdapterError
from current.provider import CurrentCloudEnvironmentProvider


class InventoryTests(unittest.TestCase):
    def resolver(self, replies):
        captured = []

        class Client:
            def __init__(self, spec):
                captured.append(spec)

            def request(self, payload, **kwargs):
                return replies.pop(0)

        path = str(Path(tempfile.gettempdir()) / "gh.exe")
        return NativeGitHubRepositoryResolver(
            GitHubSettings(path, "a" * 64, account="owner"), Client
        ), captured

    def test_native_pagination_enumerates_all_pages_without_jq_conflict(self):
        provider, calls = self.resolver(
            [
                {"id": 1, "login": "owner"},
                [
                    [{"id": 7, "full_name": "Owner/One", "private": False}],
                    [{"id": 8, "full_name": "Owner/Two", "private": True}],
                ],
                {"id": 1, "login": "owner"},
            ]
        )
        result = provider.list_repositories()
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["catalog_complete"])
        self.assertIn("--paginate", calls[1].argv)
        self.assertIn("--slurp", calls[1].argv)
        self.assertNotIn("--jq", calls[1].argv)
        self.assertFalse(result["cloud_environment_verified"])

    def test_empty_owned_catalog_does_not_prove_empty_cloud(self):
        provider, _ = self.resolver(
            [{"id": 1, "login": "owner"}, [[]], {"id": 1, "login": "owner"}]
        )
        result = provider.list_repositories()
        self.assertEqual(result["count"], 0)
        self.assertTrue(result["catalog_complete"])
        self.assertFalse(result["cloud_environment_verified"])

    def test_account_switch_during_enumeration_is_rejected(self):
        provider, _ = self.resolver(
            [{"id": 1, "login": "owner"}, [[]], {"id": 2, "login": "other"}]
        )
        result = provider.list_repositories()
        self.assertFalse(result["catalog_complete"])
        self.assertEqual(result["reason"], "github_account_changed")

    def test_duplicate_ids_across_pages_are_not_claimed_complete(self):
        row = {"id": 7, "full_name": "owner/one", "private": False}
        provider, _ = self.resolver(
            [{"id": 1, "login": "owner"}, [[row], [row]], {"id": 1, "login": "owner"}]
        )
        result = provider.list_repositories()
        self.assertFalse(result["catalog_complete"])
        self.assertIn("pagination", result["reason"])

    def test_unknown_slurp_envelope_rejected(self):
        provider, _ = self.resolver([{"id": 1, "login": "owner"}, {"items": []}])
        result = provider.list_repositories()
        self.assertFalse(result["catalog_complete"])
        self.assertEqual(result["reason"], "github_pagination_envelope_invalid")

    def test_unapproved_account_never_enumerates_repositories(self):
        provider, calls = self.resolver([{"id": 2, "login": "other"}])
        self.assertFalse(provider.list_repositories()["catalog_complete"])
        self.assertEqual(len(calls), 1)


class CorrelationTests(unittest.TestCase):
    def inventory(self):
        return {
            "status": "ok",
            "catalog_complete": True,
            "repositories": [
                {"repository_id": "7", "repository": "owner/demo"},
                {"repository_id": "8", "repository": "another/demo"},
            ],
        }

    def row(self, **values):
        return EnvironmentDescriptor(
            cloud_type="legacy",
            environment_id="a" * 32,
            name=values.pop("name", "demo"),
            evidence="live",
            **values,
        ).to_dict()

    def test_same_name_is_a_candidate_not_a_verified_join(self):
        result = correlate_repositories([self.row()], self.inventory())
        self.assertFalse(result[0]["association_verified"])
        self.assertEqual(len(result[0]["repositories"]), 2)
        self.assertTrue(all(i["confidence"] == "hint" for i in result[0]["repositories"]))

    def test_matching_id_outweighs_name_candidates(self):
        result = correlate_repositories([self.row(repository_id="7")], self.inventory())
        self.assertTrue(result[0]["association_verified"])
        self.assertEqual(len(result[0]["repositories"]), 1)
        self.assertEqual(result[0]["repositories"][0]["repository_id"], "7")

    def test_repositories_cannot_create_missing_environment_ids(self):
        self.assertEqual(correlate_repositories([], self.inventory()), [])

    def test_partial_github_catalog_is_not_used_as_verified_join(self):
        inventory = self.inventory()
        inventory["catalog_complete"] = False
        self.assertEqual(correlate_repositories([self.row()], inventory), [])

    def test_correlation_does_not_promote_cloud_completeness(self):
        class Cloud:
            name = "legacy"

            def list_environments(inner, **kwargs):
                return ProviderResult(
                    provider="legacy",
                    status="partial",
                    evidence="live",
                    environments=[EnvironmentDescriptor(**self.row())],
                )

        class GitHub:
            def list_repositories(inner):
                return self.inventory()

        result = EnvironmentDiscoveryService("legacy", Cloud(), GitHub()).list_environments(
            correlate_github=True
        )
        self.assertFalse(result["catalog_complete"])
        self.assertEqual(len(result["environments"]), 1)
        self.assertEqual(len(result["repository_correlations"]), 1)

    def test_cloud_denial_does_not_block_independent_github_inventory(self):
        class Cloud:
            name = "current"

            def list_environments(inner, **kwargs):
                return ProviderResult(provider="current", status="forbidden")

        class GitHub:
            def list_repositories(inner):
                return {
                    "status": "ok",
                    "catalog_complete": True,
                    "count": 1,
                    "repositories": [
                        {
                            "repository_id": "7",
                            "repository": "owner/demo",
                            "private": False,
                        }
                    ],
                }

        result = EnvironmentDiscoveryService("current", Cloud(), GitHub()).list_environments(
            correlate_github=True
        )
        self.assertEqual(result["status"], "forbidden")
        self.assertEqual(result["repository_inventory"]["status"], "ok")
        self.assertEqual(result["repository_inventory"]["count"], 1)
        self.assertEqual(result["repository_candidates"][0]["repository_id"], "7")
        self.assertIn("independently", " ".join(result["warnings"]))

    def test_cancelled_operation_still_stops_optional_correlation(self):
        class Cloud:
            name = "current"

            def list_environments(inner, **kwargs):
                return ProviderResult(provider="current", status="cancelled")

        class GitHub:
            def list_repositories(inner):
                raise AssertionError("Cancelled operation must not start another read")

        result = EnvironmentDiscoveryService("current", Cloud(), GitHub()).list_environments(
            correlate_github=True
        )
        self.assertEqual(result["repository_inventory"]["status"], "not_attempted")
        self.assertIn("terminated", result["repository_inventory"]["reason"])


class RepositoryCounterpartTests(unittest.TestCase):
    class GitHub:
        def __init__(self, status="verified"):
            self.status = status

        def resolve(self, repository):
            return {
                "status": self.status,
                "repository_id": "7",
                "repository": "owner/demo",
                "source": "fixture",
                "cloud_environment_verified": False,
            }

    class Cloud:
        name = "current"

        def __init__(self, result):
            self.result = result

        def list_environments(self, **kwargs):
            return self.result

    def service(self, result, github_status="verified"):
        return EnvironmentDiscoveryService(
            "current", self.Cloud(result), self.GitHub(github_status)
        )

    def descriptor(self, **values):
        return EnvironmentDescriptor(
            cloud_type="current",
            environment_id=values.pop("environment_id", "cfg-1"),
            name=values.pop("name", "Current config"),
            evidence="live",
            **values,
        )

    def test_exact_current_repository_id_verifies_counterpart(self):
        env = self.descriptor(
            repositories=({"repository": None, "repository_id": "7"},)
        )
        result = self.service(
            ProviderResult(
                provider="current",
                status="partial",
                environments=[env],
                evidence="live",
                catalog_complete=False,
            )
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(counterpart["status"], "verified")
        self.assertTrue(counterpart["cloud_environment_verified"])
        self.assertEqual(counterpart["verified_matches"][0]["matching_basis"], "repository_id")
        self.assertEqual(result["environments"][0]["repository_match"], "verified")

    def test_current_explicit_repository_name_verifies_counterpart(self):
        env = self.descriptor(repository="owner/demo")
        result = self.service(
            ProviderResult(
                provider="current",
                status="ok",
                environments=[env],
                evidence="live",
                catalog_complete=True,
            )
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(counterpart["status"], "verified")
        self.assertEqual(
            counterpart["verified_matches"][0]["matching_basis"], "repository_name"
        )

    def test_environment_name_only_is_candidate_not_verified(self):
        env = self.descriptor(name="demo")
        result = self.service(
            ProviderResult(
                provider="current",
                status="partial",
                environments=[env],
                evidence="live",
                catalog_complete=False,
            )
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(counterpart["status"], "candidate")
        self.assertFalse(counterpart["cloud_environment_verified"])
        self.assertEqual(
            counterpart["candidate_matches"][0]["matching_basis"], "environment_name"
        )

    def test_imported_explicit_repository_id_is_candidate_until_live(self):
        env = EnvironmentDescriptor(
            cloud_type="current",
            environment_id="cfg-imported",
            name="Current config",
            repositories=({"repository": None, "repository_id": "7"},),
            evidence="imported",
        )
        result = self.service(
            ProviderResult(
                provider="current",
                status="partial",
                environments=[env],
                evidence="imported",
                catalog_complete=False,
            )
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(counterpart["status"], "candidate")
        self.assertFalse(counterpart["cloud_environment_verified"])
        self.assertIn(
            "fresh_live",
            counterpart["candidate_matches"][0]["verification_reason"],
        )

    def test_stale_live_repository_id_is_candidate_until_revalidated(self):
        env = EnvironmentDescriptor(
            cloud_type="current",
            environment_id="cfg-stale",
            name="Current config",
            repositories=({"repository": None, "repository_id": "7"},),
            evidence="live",
            observed_at="2000-01-01T00:00:00+00:00",
        )
        result = self.service(
            ProviderResult(
                provider="current",
                status="partial",
                environments=[env],
                evidence="live",
                catalog_complete=False,
            )
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(counterpart["status"], "candidate")
        self.assertFalse(counterpart["cloud_environment_verified"])

    def test_complete_current_catalog_can_verify_absence(self):
        result = self.service(
            ProviderResult(
                provider="current",
                status="empty",
                environments=[],
                evidence="live",
                catalog_complete=True,
            )
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(counterpart["status"], "not_found")
        self.assertTrue(counterpart["absence_verified"])

    def test_forbidden_current_catalog_keeps_repository_candidate(self):
        result = self.service(
            ProviderResult(provider="current", status="forbidden")
        ).find_environments("owner/demo")
        counterpart = result["repository_counterpart"]
        self.assertEqual(result["status"], "forbidden")
        self.assertEqual(counterpart["status"], "not_verifiable")
        self.assertTrue(counterpart["repository_verified"])
        self.assertFalse(counterpart["cloud_environment_verified"])
        self.assertEqual(
            counterpart["candidate_environment_names"],
            ["demo", "owner/demo"],
        )

    def test_failed_github_verification_prevents_cloud_probe(self):
        class NeverCloud:
            name = "current"

            def list_environments(self, **kwargs):
                raise AssertionError("Cloud lookup must not start with invalid repo identity")

        result = EnvironmentDiscoveryService(
            "current", NeverCloud(), self.GitHub("not_verifiable")
        ).find_environments("owner/demo")
        self.assertEqual(result["status"], "not_verifiable")
        self.assertEqual(result["repository_counterpart"]["status"], "not_verifiable")
        self.assertEqual(result["provider"]["status"], "not_attempted")


class CurrentSurfaceTests(unittest.TestCase):
    def test_web_proxy_is_explicitly_distinct_from_desktop_backend(self):
        calls = []

        def transport(url, query):
            calls.append(url)
            return HttpResponse(200, {"items": []})

        result = CurrentCloudEnvironmentProvider(transport, api_surface="web").list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual(set(calls), {"https://chatgpt.com/api/codex-cloud/v1/environment-configs"})

    def test_web_proxy_uses_its_observed_list_contract_not_desktop_picker(self):
        queries = []

        def transport(url, query):
            queries.append(dict(query))
            return HttpResponse(200, {"items": []})

        provider = CurrentCloudEnvironmentProvider(transport, api_surface="web")
        self.assertTrue(provider.list_environments().catalog_complete)
        self.assertEqual(len(queries), 2)
        self.assertTrue(all("view" not in query for query in queries))

    def test_denial_never_switches_surface_automatically(self):
        calls = []

        def transport(url, query):
            calls.append(url)
            return HttpResponse(403)

        result = CurrentCloudEnvironmentProvider(transport, api_surface="web").list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(len(calls), 1)

    def test_unknown_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            CurrentCloudEnvironmentProvider(api_surface="other")

    def test_host_transport_cannot_redirect_to_another_surface(self):
        relay = CommandReadTransport("current", object(), api_surface="web")
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_destination"):
            relay("https://codex-cloud-backend.chatgpt.com/v1/environment-configs", {})


if __name__ == "__main__":
    unittest.main()
