"""Domain-independent models, evidence matching and conservative resolution."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "plugins/cloudcodex-environment-discovery/runtime"
sys.path.insert(0, str(RUNTIME))

from common.matching import repository_match  # noqa: E402
from common.models import (  # noqa: E402
    EnvironmentDescriptor, ProviderResult, extract_page, normalize_repository,
    parse_environment,
)
from common.service import EnvironmentDiscoveryService  # noqa: E402
from common.snapshot import SnapshotEnvironmentProvider  # noqa: E402


def environment(
    identifier="e-1", name="Example", repository="owner/repo",
    evidence="live", repo_id="123", cloud_type="sample", account=None
):
    return EnvironmentDescriptor(
        cloud_type=cloud_type, environment_id=identifier, name=name,
        repository=repository, repository_id=repo_id, evidence=evidence,
        account=account, discovery_source="test",
    )


class StaticProvider:
    def __init__(
        self, name="sample", items=None, complete=True, status="ok",
        evidence="live", warnings=None,
    ):
        self.name = name
        self.items = [] if items is None else list(items)
        self.complete = complete
        self.status = status
        self.evidence = evidence
        self.warnings = warnings or []

    def list_environments(self, account=None, include_drafts=False):
        return ProviderResult(
            provider=self.name, status=self.status,
            environments=self.items, catalog_complete=self.complete,
            evidence=self.evidence, warnings=list(self.warnings),
        )


class ModelTests(unittest.TestCase):
    def test_normalize_owner_repo(self):
        self.assertEqual(normalize_repository("OWNER/Repo"), "owner/repo")

    def test_normalize_github_url(self):
        self.assertEqual(
            normalize_repository("https://github.com/OWNER/Repo.git"),
            "owner/repo",
        )

    def test_normalize_trailing_slash(self):
        self.assertEqual(normalize_repository("owner/repo/"), "owner/repo")

    def test_invalid_repo_has_no_owner(self):
        self.assertIsNone(normalize_repository("justrepo"))

    def test_invalid_repo_has_extra_components(self):
        self.assertIsNone(normalize_repository("owner/repo/branch"))

    def test_environment_requires_nonempty_id(self):
        with self.assertRaises(ValueError):
            environment(identifier="")

    def test_environment_requires_type(self):
        with self.assertRaises(ValueError):
            environment(cloud_type="")

    def test_environment_rejects_unknown_evidence(self):
        with self.assertRaises(ValueError):
            environment(evidence="forged")

    def test_environment_rejects_unknown_config_state(self):
        with self.assertRaises(ValueError):
            EnvironmentDescriptor(
                cloud_type="sample", environment_id="123",
                name="Example", configuration_state="deployed",
            )

    def test_descriptor_copy_does_not_mutate_source(self):
        entry = environment()
        matched = entry.with_match("verified")
        self.assertEqual(entry.repository_match, "not_evaluated")
        self.assertEqual(matched.repository_match, "verified")

    def test_explicit_numeric_repo_id_is_verified(self):
        self.assertEqual(repository_match(environment(), "123"), "verified")

    def test_explicit_repo_owner_name_is_verified(self):
        self.assertEqual(repository_match(environment(), "OWNER/Repo"), "verified")

    def test_matching_environment_label_is_hint_not_verified(self):
        entry = environment(name="repo", repository=None)
        self.assertEqual(repository_match(entry, "owner/repo"), "hint")

    def test_mismatch_is_none(self):
        self.assertEqual(repository_match(environment(), "someone/else"), "none")

    def test_invalid_match_input_raises(self):
        with self.assertRaises(ValueError):
            repository_match(environment(), "bad")

    def test_parse_explicit_repo_association(self):
        entry = parse_environment(
            {"id": "known-id", "repository": {"full_name": "Team/Repo", "id": 4}},
            "sample", "user", "provider",
        )
        self.assertEqual(entry.repository, "team/repo")
        self.assertEqual(entry.repository_id, "4")

    def test_parse_current_detailed_repository_id_shape(self):
        entry = parse_environment(
            {
                "id": "cfg-current",
                "name": "Current config",
                "repositories": [{"repositoryId": "1408634524", "ref": "main"}],
                "versionRevision": 3,
            },
            "current",
            "user",
            "desktop_catalog",
        )
        self.assertEqual(entry.repository_id, "1408634524")
        self.assertEqual(
            entry.repositories,
            ({"repository": None, "repository_id": "1408634524"},),
        )
        self.assertEqual(entry.configuration_version, "3")

    def test_parse_current_catalog_repository_ids_shape(self):
        entry = parse_environment(
            {
                "id": "cfg-current",
                "name": "Current config",
                "repository_ids": ["1408634524", 99],
            },
            "current",
            "user",
            "desktop_catalog_cache",
        )
        self.assertEqual(
            entry.repositories,
            (
                {"repository": None, "repository_id": "1408634524"},
                {"repository": None, "repository_id": "99"},
            ),
        )
        self.assertIsNone(entry.repository_id)

    def test_parse_current_camel_catalog_repository_ids_shape(self):
        entry = parse_environment(
            {
                "id": "cfg-current",
                "repositoryIds": ["7"],
                "versionId": "v-current",
            },
            "current",
            "workspace",
            "desktop_catalog_cache",
        )
        self.assertEqual(entry.repository_id, "7")
        self.assertEqual(entry.configuration_version, "v-current")

    def test_parse_legacy_repo_map_shape(self):
        entry = parse_environment(
            {
                "id": "legacy-id",
                "label": "Legacy",
                "repos": ["7"],
                "repo_map": {"7": {"repository_full_name": "Owner/Repo"}},
            },
            "legacy",
            "user",
            "codex_client",
        )
        self.assertEqual(entry.repository, "owner/repo")
        self.assertEqual(entry.repository_id, "7")

    def test_malformed_current_repository_ids_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_environment(
                {"id": "cfg", "repository_ids": "7"},
                "current",
                "user",
                "desktop_catalog_cache",
            )
        with self.assertRaises(ValueError):
            parse_environment(
                {"id": "cfg", "repositories": [{"repositoryId": True}]},
                "current",
                "user",
                "desktop_catalog",
            )

    def test_parse_name_does_not_infer_repository(self):
        entry = parse_environment(
            {"id": "x", "name": "owner/repo"}, "sample", "user", "provider",
        )
        self.assertIsNone(entry.repository)

    def test_parse_unknown_status_is_unknown(self):
        entry = parse_environment(
            {"id": "x", "status": "pending"}, "sample", "user", "provider",
        )
        self.assertEqual(entry.configuration_state, "unknown")

    def test_missing_id_is_invalid(self):
        with self.assertRaises(ValueError):
            parse_environment({"name": "anything"}, "sample", "user", "provider")

    def test_list_envelope(self):
        items, cursor = extract_page([{"id": "one"}])
        self.assertEqual(len(items), 1)
        self.assertIsNone(cursor)

    def test_known_envelope(self):
        items, cursor = extract_page({"items": [{"id": "one"}]})
        self.assertEqual(len(items), 1)
        self.assertIsNone(cursor)

    def test_unknown_envelope_not_empty(self):
        with self.assertRaises(ValueError):
            extract_page({"message": "ok"})

    def test_pagination_cursor_nested(self):
        _, cursor = extract_page({
            "items": [], "pagination": {"nextCursor": "next"}
        })
        self.assertEqual(cursor, "next")

    def test_has_more_without_cursor_raises(self):
        with self.assertRaises(ValueError):
            extract_page({"items": [], "has_more": True})

    def test_nonobject_entry_raises(self):
        with self.assertRaises(ValueError):
            extract_page({"items": ["oops"]})


class ServiceTests(unittest.TestCase):
    def test_service_rejects_wrong_provider_identity(self):
        with self.assertRaises(ValueError):
            EnvironmentDiscoveryService("sample", StaticProvider("foreign"))

    def test_one_live_item_resolves(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment()])
        ).resolve_environment(repository="owner/repo")
        self.assertEqual(result["status"], "resolved")

    def test_empty_complete_catalog_means_not_found(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[], status="empty")
        ).resolve_environment(name="anything")
        self.assertEqual(result["status"], "not_found")

    def test_unavailable_catalog_is_not_verifiable(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(complete=False, status="unavailable")
        ).resolve_environment(name="anything")
        self.assertEqual(result["status"], "not_verifiable")

    def test_two_environments_are_ambiguous(self):
        entries = [environment(identifier="one"), environment(identifier="two")]
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=entries)
        ).resolve_environment(repository="owner/repo")
        self.assertEqual(result["status"], "ambiguous")

    def test_name_hint_cannot_resolve(self):
        entry = environment(name="repo", repository=None)
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[entry])
        ).resolve_environment(repository="owner/repo")
        self.assertEqual(result["status"], "unverified")

    def test_incomplete_catalog_never_resolves(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment()], complete=False)
        ).resolve_environment(repository="owner/repo")
        self.assertEqual(result["status"], "unverified")

    def test_imported_entry_never_resolves(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(
                items=[environment(evidence="imported")], evidence="imported"
            )
        ).resolve_environment(repository="owner/repo")
        self.assertEqual(result["status"], "unverified")

    def test_get_exact_id_in_complete_catalog(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment()])
        ).get_environment("e-1")
        self.assertEqual(result["status"], "found")

    def test_get_unknown_id_in_incomplete_catalog(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(complete=False, status="unavailable")
        ).get_environment("missing")
        self.assertEqual(result["status"], "not_verifiable")

    def test_requested_account_not_assumed_from_request(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment(account=None)])
        ).list_environments(account="some-account")
        self.assertFalse(result["catalog_complete"])

    def test_different_account_filtered(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment(account="Alice")])
        ).list_environments(account="Bob")
        self.assertEqual(result["environments"], [])
        self.assertFalse(result["catalog_complete"])

    def test_account_match_can_be_verified(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment(account="Alice")])
        ).list_environments(account="Alice")
        self.assertTrue(result["catalog_complete"])

    def test_wrong_cloud_type_item_not_accepted(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment(cloud_type="other")])
        ).list_environments()
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["catalog_complete"])

    def test_duplicate_ids_are_deduplicated_within_domain(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment(), environment()])
        ).list_environments()
        self.assertEqual(len(result["environments"]), 1)

    def test_no_mixed_cloud_type_parameter(self):
        service = EnvironmentDiscoveryService("sample", StaticProvider())
        with self.assertRaises(TypeError):
            service.list_environments(cloud_type="all")

    def test_repo_numeric_id_match(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(items=[environment()])
        ).find_environments("123")
        self.assertEqual(result["count"], 1)
        self.assertEqual(
            result["environments"][0]["repository_match"], "verified"
        )

    def test_invalid_repository_rejected(self):
        with self.assertRaises(ValueError):
            EnvironmentDiscoveryService(
                "sample", StaticProvider()
            ).find_environments("bad")

    def test_provider_unavailability_retained(self):
        result = EnvironmentDiscoveryService(
            "sample", StaticProvider(
                status="forbidden", complete=False,
                warnings=["HTTP 403; not authoritative"]
            )
        ).list_environments()
        self.assertEqual(result["provider"]["status"], "forbidden")
        self.assertIn("HTTP 403", result["warnings"][0])


class SnapshotTests(unittest.TestCase):
    def test_snapshot_always_unverified(self):
        provider = SnapshotEnvironmentProvider(
            "sample", {"items": [{"id": "x", "name": "Example"}]}
        )
        result = provider.list_environments()
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.catalog_complete)
        self.assertEqual(result.environments[0].evidence, "imported")

    def test_snapshot_filters_drafts_by_default(self):
        provider = SnapshotEnvironmentProvider("sample", {"items": [
            {"id": "one", "draft": True},
            {"id": "two", "published": True},
        ]})
        self.assertEqual(len(provider.list_environments().environments), 1)

    def test_snapshot_can_include_drafts_explicitly(self):
        provider = SnapshotEnvironmentProvider("sample", {"items": [
            {"id": "one", "draft": True},
            {"id": "two", "published": True},
        ]})
        self.assertEqual(
            len(provider.list_environments(include_drafts=True).environments), 2
        )

    def test_snapshot_rejects_credential_paths(self):
        with self.assertRaises(ValueError):
            SnapshotEnvironmentProvider.from_file(
                "sample", Path(".codex") / "auth.json"
            )

    def test_snapshot_unknown_schema_invalid(self):
        provider = SnapshotEnvironmentProvider("sample", {"error": "invalid"})
        self.assertEqual(provider.list_environments().status, "invalid_response")


if __name__ == "__main__":
    unittest.main()
