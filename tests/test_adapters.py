"""Adapters run real child processes, but all remote catalog data is simulated."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from time import monotonic
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "plugins/cloudcodex-environment-discovery/runtime"
sys.path.insert(0, str(RUNTIME))
from common.adapters import AdapterError, CommandClient, CommandSpec, CommandReadTransport, CommandCatalogProvider
from common.configuration import DiscoveryRuntime, validate_configuration
from common.escalation import EscalatingProvider, Stage
from common.models import ProviderResult, HttpResponse, extract_page, parse_environment
from common.operation import Operation, OperationCancelled, OperationTimedOut, operation_scope
from common.service import EnvironmentDiscoveryService
from common.matching import repository_match
from current.provider import CurrentCloudEnvironmentProvider

HOST = ROOT / "tests/fixtures/catalog_host.py"


def specification(mode="catalog_ok", timeout=3.0):
    executable = str(Path(sys.executable).resolve())
    script = str(HOST.resolve())
    return {"argv": [executable, script, mode], "cwd": str(ROOT), "timeout": timeout,
            "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (executable, script)}}


def configuration(domain="current", stages=None, mode="AUTO"):
    return {"schema_version": 1, "mode": mode, "timeout": 10,
            "domains": {domain: {"stages": stages if stages is not None else [
                {"kind": "primary", "approved": True, "command": specification()}]}}}


class FakeProvider:
    name = "current"
    def __init__(self, status="unavailable", complete=False, items=None):
        self.status, self.complete, self.items, self.calls = status, complete, items or [], 0
    def list_environments(self, **kwargs):
        self.calls += 1
        return ProviderResult(provider="current", status=self.status, environments=list(self.items),
                              evidence="live", catalog_complete=self.complete)


class AdapterTests(unittest.TestCase):
    def test_command_catalog_real_process_normalization(self):
        provider = CommandCatalogProvider("current", CommandClient(CommandSpec.from_mapping(specification())), "fixture")
        output = provider.list_environments()
        self.assertTrue(output.catalog_complete)
        self.assertEqual(output.environments[0].repository, "fixtures/demo")
        self.assertEqual(output.account, "fixture-account")

    def test_configured_cli_path_resolves_from_simulated_primary(self):
        runtime = DiscoveryRuntime(configuration())
        with operation_scope(Operation(10)):
            result = runtime.service("current").resolve_environment(repository="fixtures/demo")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual([a["stage"] for a in result["provider"]["attempts"]], ["primary"])

    def test_actual_http_host_adapter_paginates_both_scopes(self):
        spec = CommandSpec.from_mapping(specification("http_pages"))
        transport = CommandReadTransport("current", CommandClient(spec))
        result = CurrentCloudEnvironmentProvider(transport).list_environments(
            include_drafts=True
        )
        self.assertTrue(result.catalog_complete)
        self.assertEqual(len(result.environments), 2)
        self.assertTrue(all(i.scope == "user,workspace" for i in result.environments))

    def test_403_without_observation_is_terminal(self):
        transport = CommandReadTransport("current", CommandClient(CommandSpec.from_mapping(specification("deny"))))
        result = CurrentCloudEnvironmentProvider(transport).list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertFalse(result.catalog_complete)

    def test_primary_denial_without_timestamp_is_terminal(self):
        provider = CommandCatalogProvider("current", CommandClient(CommandSpec.from_mapping(specification("deny"))), "fixture")
        self.assertEqual(provider.list_environments().status, "forbidden")

    def test_html_http_200_cannot_be_treated_as_authenticated_catalog(self):
        config = configuration(stages=[{"kind": "http", "approved": True, "command": specification("html")}])
        result = DiscoveryRuntime(config).service("current").list_environments()
        self.assertEqual(result["status"], "forbidden")
        self.assertFalse(result["catalog_complete"])

    def test_pin_mismatch_never_executes_host(self):
        spec = specification()
        spec["sha256"][spec["argv"][0]] = "0" * 64
        with self.assertRaisesRegex(AdapterError, "host_integrity_mismatch"):
            CommandClient(CommandSpec.from_mapping(spec)).request({})

    def test_model_cannot_choose_arbitrary_destination(self):
        transport = CommandReadTransport("current", CommandClient(CommandSpec.from_mapping(specification())))
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_destination"):
            transport("https://example.org", {})

    def test_model_cannot_choose_arbitrary_query_parameter(self):
        transport = CommandReadTransport("current", CommandClient(CommandSpec.from_mapping(specification())))
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_query"):
            transport("https://codex-cloud-backend.chatgpt.com/v1/environment-configs", {"token": "hidden"})

    def test_current_picker_view_is_the_only_approved_view(self):
        transport = CommandReadTransport(
            "current", CommandClient(CommandSpec.from_mapping(specification()))
        )
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_query"):
            transport(
                "https://codex-cloud-backend.chatgpt.com/v1/environment-configs",
                {"scope": "user", "view": "admin"},
            )

    def test_legacy_transport_rejects_picker_view(self):
        transport = CommandReadTransport(
            "legacy", CommandClient(CommandSpec.from_mapping(specification()))
        )
        with self.assertRaisesRegex(AdapterError, "unapproved_catalog_query"):
            transport(
                "https://chatgpt.com/backend-api/wham/environments",
                {"view": "picker"},
            )

    def test_host_stderr_and_failure_output_not_exposed(self):
        client = CommandClient(CommandSpec.from_mapping(specification("failed")))
        with self.assertRaises(AdapterError) as result:
            client.request({"cloud_type": "current"})
        self.assertNotIn("SENSITIVE_RAW_OUTPUT", str(result.exception))

    def test_bounded_host_output(self):
        client = CommandClient(CommandSpec.from_mapping(specification("oversized")))
        with self.assertRaisesRegex(AdapterError, "host_output_too_large"):
            client.request({"cloud_type": "current"})

    def test_host_timeout_terminates_child(self):
        client = CommandClient(CommandSpec.from_mapping(specification("delay", 0.2)))
        started = monotonic()
        with self.assertRaises((AdapterError, OperationTimedOut)):
            client.request({"cloud_type": "current"})
        self.assertLess(monotonic() - started, 3)

    def test_cancellation_terminates_host(self):
        client = CommandClient(CommandSpec.from_mapping(specification("delay", 5)))
        operation = Operation(5)
        timer = threading.Timer(0.2, operation.cancelled.set)
        timer.start()
        started = monotonic()
        try:
            with operation_scope(operation), self.assertRaises(OperationCancelled):
                client.request({"cloud_type": "current"})
        finally:
            timer.cancel()
        self.assertLess(monotonic() - started, 3)

    def test_ambient_secret_not_inherited(self):
        client = CommandClient(CommandSpec.from_mapping(specification("check_environment")))
        with patch.dict(os.environ, {"TEST_AUTH_TOKEN": "do-not-inherit"}):
            self.assertFalse(client.request({})["secret_inherited"])

    def test_malformed_host_json_is_sanitized(self):
        client = CommandClient(CommandSpec.from_mapping(specification("invalid")))
        with self.assertRaisesRegex(AdapterError, "host_invalid_json"):
            client.request({})

    def test_observation_staleness_is_preserved(self):
        config = configuration(stages=[{"kind": "primary", "approved": True, "command": specification("stale")}])
        output = DiscoveryRuntime(config).service("current").list_environments()
        self.assertEqual(output["status"], "stale")
        self.assertFalse(output["catalog_complete"])

    def test_onboarding_evidence_cannot_resolve(self):
        config = configuration(stages=[{"kind": "onboarding", "approved": True, "command": specification()}])
        output = DiscoveryRuntime(config).service("current").resolve_environment(repository="fixtures/demo")
        self.assertEqual(output["status"], "unverified")
        self.assertEqual(output["candidates"][0]["evidence"], "indirect")

    def test_wrong_cloud_identity_is_forbidden(self):
        config = configuration(stages=[{"kind": "primary", "approved": True, "command": specification("mismatch")}])
        output = DiscoveryRuntime(config).service("current").list_environments()
        self.assertEqual(output["status"], "forbidden")


class EscalationTests(unittest.TestCase):
    def test_ordered_fallback_stops_after_authoritative_success(self):
        providers = [FakeProvider(), FakeProvider("empty", True), FakeProvider()]
        chain = EscalatingProvider("current", [Stage(str(i), p) for i, p in enumerate(providers)])
        result = chain.list_environments()
        self.assertTrue(result.catalog_complete)
        self.assertEqual([p.calls for p in providers], [1, 1, 0])
        self.assertEqual(len(result.attempts), 2)

    def test_401_or_403_never_falls_through(self):
        for status in ("forbidden", "unauthorized", "rate_limited"):
            first, second = FakeProvider(status), FakeProvider("ok", True)
            result = EscalatingProvider("current", [Stage("first", first), Stage("second", second)]).list_environments()
            self.assertEqual(result.status, status)
            self.assertEqual(second.calls, 0)

    def test_confirm_requires_missing_stage_approval(self):
        provider = FakeProvider("ok", True)
        result = EscalatingProvider("current", [Stage("http", provider, False)], "CONFIRM").list_environments()
        self.assertEqual(result.status, "approval_required")
        self.assertEqual(provider.calls, 0)

    def test_auto_does_not_grant_approval(self):
        provider = FakeProvider("ok", True)
        result = EscalatingProvider("current", [Stage("http", provider, False)], "AUTO").list_environments()
        self.assertEqual(provider.calls, 0)
        self.assertFalse(result.catalog_complete)

    def test_configured_primary_to_http_escalation_real_processes(self):
        stages = [{"kind": "primary", "approved": True, "command": specification("unavailable")},
                  {"kind": "http", "approved": True, "command": specification("http_pages")}]
        output = DiscoveryRuntime(configuration(stages=stages)).service("current").list_environments(
            include_drafts=True
        )
        self.assertTrue(output["catalog_complete"])
        self.assertEqual([a["stage"] for a in output["provider"]["attempts"]], ["primary", "http"])

    def test_config_is_not_a_credentials_container(self):
        config = configuration()
        config["token"] = "not-permitted"
        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_stage_cannot_silently_reorder_escalation(self):
        with self.assertRaises(ValueError):
            validate_configuration(configuration(stages=[
                {"kind": "http", "command": specification()},
                {"kind": "primary", "command": specification()}]))

    def test_command_must_pin_both_interpreter_and_script(self):
        spec = specification()
        spec["sha256"].pop(spec["argv"][1])
        with self.assertRaises(ValueError):
            CommandSpec.from_mapping(spec)

    def test_no_inline_code_or_shell(self):
        spec = specification()
        spec["argv"] = [spec["argv"][0], "-c", "print('no')"]
        with self.assertRaises(ValueError):
            CommandSpec.from_mapping(spec)

    def test_doctor_does_not_execute_a_configured_host(self):
        config = configuration(stages=[{"kind": "primary", "approved": True, "command": specification("delay")}])
        started = monotonic()
        self.assertTrue(DiscoveryRuntime(config).doctor("current")["configured"])
        self.assertLess(monotonic() - started, 1)

    def test_unconfigured_runtime_explains_gap(self):
        output = DiscoveryRuntime({"schema_version": 1, "domains": {}}).service("current").list_environments()
        self.assertEqual(output["provider"]["reason"], "no_authorized_source_configured")
        self.assertFalse(output["catalog_complete"])


class CatalogRegressionTests(unittest.TestCase):
    def test_multiple_repository_associations(self):
        item = parse_environment({"id": "cfg", "repositories": [
            {"id": 1, "full_name": "owner/one"}, {"id": 2, "full_name": "owner/two"}]},
            "current", "user", "test")
        self.assertEqual(repository_match(item, "owner/two"), "verified")
        self.assertEqual(repository_match(item, "2"), "verified")
        self.assertEqual(repository_match(item, "3"), "none")

    def test_drafts_and_published_versions_not_silently_deduplicated(self):
        provider = CurrentCloudEnvironmentProvider(lambda u, p: HttpResponse(200, {"items": [
            {"id": "cfg", "version": 1, "published": True},
            {"id": "cfg", "version": 2, "draft": True}]}), scopes=("user",))
        result = provider.list_environments(include_drafts=True)
        self.assertEqual(len(result.environments), 2)

        class CatalogOnly:
            name = "current"

            def list_environments(self, **kwargs):
                return provider.list_environments(**kwargs)

        # Ambiguity still applies to a full catalog with two revisions.
        # A direct get-by-ID instead returns one explicitly identified record.
        result = EnvironmentDiscoveryService("current", CatalogOnly()).get_environment("cfg")
        self.assertEqual(result["status"], "ambiguous")

    def test_known_verified_account_can_have_empty_catalog(self):
        provider = CurrentCloudEnvironmentProvider(lambda u, p: HttpResponse(
            200, {"items": []}, account="account", account_verified=True), scopes=("user",))
        output = EnvironmentDiscoveryService("current", provider).list_environments(
            account="account", include_drafts=True
        )
        self.assertTrue(output["catalog_complete"])
        self.assertEqual(output["status"], "empty")

    def test_account_change_between_pages_stops_read(self):
        seen = []
        def request(u, p):
            seen.append(p)
            return HttpResponse(200, {"items": [], "next_cursor": "next"},
                                account="A" if len(seen) == 1 else "B", account_verified=True)
        result = CurrentCloudEnvironmentProvider(request).list_environments()
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(len(seen), 2)

    def test_malformed_page_is_atomic(self):
        result = CurrentCloudEnvironmentProvider(lambda u, p: HttpResponse(200, {
            "items": [{"id": "good"}, {"name": "missing ID"}]})).list_environments()
        self.assertEqual(result.status, "invalid_response")
        self.assertEqual(result.environments, [])

    def test_conflicting_cursor_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            extract_page({"items": [], "next_cursor": "a", "nextCursor": "b"})

    def test_conflicting_duplicate_ids_not_arbitrary_first(self):
        provider = CurrentCloudEnvironmentProvider(lambda u, p: HttpResponse(200, {"items": [
            {"id": "same", "name": "A"}, {"id": "same", "name": "B"}]}))
        self.assertEqual(provider.list_environments().status, "invalid_response")



class AdditionalWireGuards(unittest.TestCase):
    def test_duplicate_host_keys_rejected(self):
        from common.adapters import _unique_pairs
        with self.assertRaises(ValueError):
            json.loads('{"status":403,"status":200}', object_pairs_hook=_unique_pairs)

    def test_known_account_cannot_disappear_during_escalation(self):
        class First(FakeProvider):
            def list_environments(self, **kwargs):
                return ProviderResult(provider="current", status="partial", account="A",
                                      account_verified=True, evidence="live")
        first,second=First(),FakeProvider("empty", True)
        result=EscalatingProvider("current", [Stage("primary",first),Stage("http",second)]).list_environments()
        self.assertEqual(result.status,"forbidden")
        self.assertEqual(result.reason,"account_unverified_during_escalation")

    def test_nonreading_host_cannot_block_stdin_forever(self):
        client=CommandClient(CommandSpec.from_mapping(specification("no_read", 0.2)))
        start=monotonic()
        with self.assertRaises((AdapterError,OperationTimedOut)):
            client.request({"payload":"x"*60000})
        self.assertLess(monotonic()-start,3)

if __name__ == "__main__":
    unittest.main()
