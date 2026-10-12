"""Concrete GitHub identity flow and read-only onboarding evidence regressions."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'plugins/cloudcodex-environment-discovery/runtime'
sys.path.insert(0, str(RUNTIME))
from common.adapters import AdapterError
from common.configuration import DiscoveryRuntime, validate_configuration
from common.escalation import EscalatingProvider, Stage
from common.github import GitHubSettings, NativeGitHubRepositoryResolver, match_verified_repository
from common.models import EnvironmentDescriptor, ProviderResult, now_utc
from common.service import EnvironmentDiscoveryService
from current.onboarding import OnboardingEvidenceProvider, OnboardingEvidenceFile


class FakeCloud:
    name = 'current'

    def __init__(self, items=None, status='ok', complete=True):
        self.items = items or []
        self.status, self.complete, self.calls = status, complete, 0
        self.repository = None

    def list_environments(self, account=None, include_drafts=False):
        self.calls += 1
        return ProviderResult(provider=self.name, status=self.status, environments=self.items,
                              catalog_complete=self.complete, evidence='live')

    def find_environments(self, repository, **kwargs):
        self.repository = repository
        return self.list_environments(**kwargs)


class FakeGitHub:
    def __init__(self, status='verified'):
        self.status, self.calls = status, 0

    def resolve(self, repository):
        self.calls += 1
        return {'status': self.status, 'repository': 'owner/canonical', 'repository_id': '7',
                'cloud_environment_verified': False}


def descriptor(repository='owner/canonical', repository_id='7'):
    return EnvironmentDescriptor(cloud_type='current', environment_id='config-real-id',
                                 name='Arbitrary label', repository=repository,
                                 repository_id=repository_id, evidence='live')


def task_document(tasks=None):
    return {'schema_version': 1, 'source': 'codex_tasks', 'observed_at': now_utc(),
            'payload': {'tasks': tasks if tasks is not None else [
                {'id': 'onboarding-thread', 'title': 'Configure sample project'}], 'nextCursor': None}}


class GitHubTests(unittest.TestCase):
    def fake_resolver(self, responses):
        captured = []
        class Client:
            def __init__(self, spec):
                captured.append(spec)
            def request(self, body):
                response = responses.pop(0)
                if isinstance(response, Exception):
                    raise response
                return response
        path = str(Path(tempfile.gettempdir()) / ('gh.exe' if sys.platform == 'win32' else 'gh'))
        settings = GitHubSettings(path, 'a' * 64, account='operator')
        return NativeGitHubRepositoryResolver(settings, Client), captured

    def test_native_calls_are_fixed_gets_to_github_not_cloud(self):
        resolver, calls = self.fake_resolver([
            {'login': 'operator', 'id': 10},
            {'id': 7, 'full_name': 'owner/canonical', 'private': False},
            {'login': 'operator', 'id': 10}])
        output = resolver.resolve('Owner/old-name')
        self.assertEqual(output['status'], 'verified')
        self.assertEqual(output['repository_id'], '7')
        self.assertFalse(output['cloud_environment_verified'])
        self.assertEqual([s.argv[6] for s in calls], ['user', 'repos/owner/old-name', 'user'])
        for command in calls:
            self.assertEqual(command.argv[1:6], ('api', '--method', 'GET', '--hostname', 'github.com'))

    def test_numeric_id_lookup_not_guessed_from_name(self):
        resolver, calls = self.fake_resolver([
            {'login': 'operator', 'id': 10}, {'id': 7, 'full_name': 'owner/canonical', 'private': False},
            {'login': 'operator', 'id': 10}])
        self.assertEqual(resolver.resolve('7')['status'], 'verified')
        self.assertEqual(calls[1].argv[6], 'repositories/7')

    def test_account_change_rejected(self):
        resolver, _ = self.fake_resolver([
            {'login': 'operator', 'id': 10}, {'id': 7, 'full_name': 'owner/canonical', 'private': False},
            {'login': 'other', 'id': 20}])
        output = resolver.resolve('owner/canonical')
        self.assertEqual(output['status'], 'not_verifiable')
        self.assertEqual(output['reason'], 'github_account_changed')

    def test_requested_account_mismatch_stops_before_repository(self):
        resolver, calls = self.fake_resolver([{'login': 'other', 'id': 20}])
        self.assertEqual(resolver.resolve('owner/canonical')['reason'], 'github_account_mismatch')
        self.assertEqual(len(calls), 1)

    def test_denial_is_not_nonexistent_repo(self):
        resolver, _ = self.fake_resolver([AdapterError('host_exit_failure')])
        self.assertEqual(resolver.resolve('owner/private')['status'], 'not_verifiable')

    def test_invalid_endpoint_components_rejected_before_execution(self):
        resolver, calls = self.fake_resolver([])
        for value in ('../user', 'owner/repo?scope=all', '--help', 'https://evil.invalid/owner/repo'):
            with self.assertRaises(ValueError):
                resolver.resolve(value)
        self.assertEqual(calls, [])

    def test_github_opt_in_requires_pinned_native_gh(self):
        with self.assertRaises(ValueError):
            GitHubSettings.from_mapping({'enabled': True, 'executable': 'gh'})
        with self.assertRaises(ValueError):
            GitHubSettings.from_mapping({'enabled': False})

    def test_unknown_disabled_configuration_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            validate_configuration({'schema_version': 1, 'github': {'enabled': False, 'secret': 'x'}})

    def test_id_has_priority_over_same_name(self):
        item = descriptor(repository_id='8')
        evidence = FakeGitHub().resolve('owner/canonical')
        self.assertEqual(match_verified_repository(item, evidence), 'none')

    def test_matching_id_survives_repository_rename(self):
        item = descriptor(repository='owner/old-name')
        self.assertEqual(match_verified_repository(item, FakeGitHub().resolve('owner/canonical')), 'verified')

    def test_verified_lookup_routes_canonical_name_to_cloud(self):
        cloud, github = FakeCloud([descriptor()]), FakeGitHub()
        result = EnvironmentDiscoveryService('current', cloud, github).resolve_environment(repository='owner/old')
        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(cloud.repository, 'owner/canonical')
        self.assertEqual(result['repository_evidence']['repository_id'], '7')

    def test_github_success_does_not_prove_cloud_environment(self):
        cloud = FakeCloud(status='unavailable', complete=False)
        result = EnvironmentDiscoveryService('current', cloud, FakeGitHub()).resolve_environment(repository='owner/canonical')
        self.assertEqual(result['status'], 'not_verifiable')
        self.assertIsNone(result['selected'])
        self.assertEqual(result['repository_evidence']['status'], 'verified')

    def test_github_failure_stops_configured_lookup_without_cloud_calls(self):
        cloud = FakeCloud([descriptor()])
        result = EnvironmentDiscoveryService('current', cloud, FakeGitHub('not_verifiable')).find_environments('owner/canonical')
        self.assertEqual(result['status'], 'not_verifiable')
        self.assertEqual(cloud.calls, 0)

    def test_list_and_get_do_not_require_optional_github_lookup(self):
        cloud, github = FakeCloud([descriptor()]), FakeGitHub()
        service = EnvironmentDiscoveryService('current', cloud, github)
        service.list_environments()
        service.get_environment('config-real-id')
        self.assertEqual(github.calls, 0)


class OnboardingTests(unittest.TestCase):
    def test_task_without_configuration_id_is_a_hint_not_an_environment(self):
        result = OnboardingEvidenceProvider(task_document()).list_environments()
        self.assertEqual(result.environments, [])
        self.assertFalse(result.catalog_complete)
        self.assertEqual(result.hints[0]['task_id'], 'onboarding-thread')
        self.assertIsNone(result.hints[0]['configuration_id'])

    def test_explicit_configuration_id_remains_indirect(self):
        data = task_document([{'id': 'thread', 'title': 'A config', 'configuration_id': 'cfg-1'}])
        result = OnboardingEvidenceProvider(data).list_environments()
        self.assertEqual(result.environments[0].environment_id, 'cfg-1')
        self.assertEqual(result.environments[0].evidence, 'indirect')
        self.assertFalse(result.catalog_complete)

    def test_same_task_and_configuration_id_is_rejected(self):
        data = task_document([{'id': 'thread', 'configuration_id': 'thread'}])
        self.assertEqual(OnboardingEvidenceProvider(data).list_environments().status, 'invalid_response')

    def test_free_text_claims_are_never_parsed_or_exposed(self):
        document = {'schema_version': 1, 'source': 'codex_tasks', 'observed_at': now_utc(),
                    'payload': {'task': {'id': 'thread', 'title': 'Configure'}, 'turns': [
                        {'messages': [{'text': 'configuration_id=FAKE; published=true; SECRET_TEXT'}]}]}}
        result = OnboardingEvidenceProvider(document).list_environments()
        self.assertEqual(result.environments, [])
        self.assertNotIn('SECRET_TEXT', str(result.to_dict()))

    def test_task_title_is_not_repository_association(self):
        data = task_document([{'id': 'thread', 'title': 'Configura owner/repo'}])
        self.assertIsNone(OnboardingEvidenceProvider(data).list_environments().hints[0]['repository'])

    def test_task_read_and_task_list_envelopes_are_separate(self):
        document = task_document()
        document['payload']['task'] = {'id': 'thread'}
        self.assertEqual(OnboardingEvidenceProvider(document).list_environments().status, 'invalid_response')

    def test_invalid_timestamp_is_not_refreshed_silently(self):
        document = task_document()
        document['observed_at'] = '2026-10-11T10:00:00'
        self.assertEqual(OnboardingEvidenceProvider(document).list_environments().status, 'invalid_response')

    def test_duplicate_task_ids_do_not_inflate_evidence(self):
        data = task_document([{'id': 'same'}, {'id': 'same'}])
        self.assertEqual(OnboardingEvidenceProvider(data).list_environments().status, 'invalid_response')

    def test_hints_survive_a_later_unavailable_stage(self):
        onboarding = OnboardingEvidenceProvider(task_document())
        chain = EscalatingProvider('current', [Stage('onboarding', onboarding),
                                               Stage('snapshot', FakeCloud(status='unavailable', complete=False))])
        result = chain.list_environments()
        self.assertEqual(len(result.hints), 1)
        self.assertFalse(result.catalog_complete)

    def test_onboarding_path_is_lazy_and_gated_by_approval(self):
        nonexistent = str(Path(tempfile.gettempdir()) / 'no-discovery-evidence-file.json')
        config = {'schema_version': 1, 'mode': 'CONFIRM', 'domains': {'current': {'stages': [
            {'kind': 'onboarding', 'approved': False, 'path': nonexistent}]}}}
        result = DiscoveryRuntime(config).service('current').list_environments()
        self.assertEqual(result['status'], 'approval_required')

    def test_file_evidence_flows_through_service_without_resolving(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connector-export.json'
            path.write_text(json.dumps(task_document()), encoding='utf-8')
            config = {'schema_version': 1, 'domains': {'current': {'stages': [
                {'kind': 'onboarding', 'approved': True, 'path': str(path)}]}}}
            output = DiscoveryRuntime(config).service('current').resolve_environment()
            self.assertEqual(output['status'], 'not_verifiable')
            self.assertEqual(len(output['provider']['hints']), 1)
            self.assertIsNone(output['selected'])

    def test_blocked_primary_cannot_be_bypassed_by_onboarding(self):
        class Never(OnboardingEvidenceProvider):
            def list_environments(self, **kwargs):
                raise AssertionError('Denied primary must stop all later stages')
        chain = EscalatingProvider('current', [Stage('primary', FakeCloud(status='forbidden', complete=False)),
                                               Stage('onboarding', Never(task_document()))])
        result = chain.list_environments()
        self.assertEqual(result.status, 'forbidden')
        self.assertEqual(len(result.attempts), 1)

    def test_evidence_reader_rejects_credential_paths(self):
        with self.assertRaises(ValueError):
            OnboardingEvidenceFile(Path('.codex/auth.json')).list_environments()



class HintContinuityTests(unittest.TestCase):
    def test_missing_later_consent_keeps_earlier_hints(self):
        chain = EscalatingProvider('current', [
            Stage('onboarding', OnboardingEvidenceProvider(task_document())),
            Stage('snapshot', FakeCloud(), False)], mode='CONFIRM')
        result = chain.list_environments()
        self.assertEqual(result.status, 'approval_required')
        self.assertEqual(len(result.hints), 1)
        self.assertFalse(result.catalog_complete)

    def test_account_verification_failure_does_not_discard_hints(self):
        chain = EscalatingProvider('current', [
            Stage('onboarding', OnboardingEvidenceProvider(task_document())),
            Stage('snapshot', FakeCloud())])
        result = chain.list_environments(account='expected-account')
        self.assertEqual(result.status, 'forbidden')
        self.assertEqual(len(result.hints), 1)
        self.assertFalse(result.catalog_complete)

if __name__ == '__main__':
    unittest.main()
