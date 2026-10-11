"""Real stdio MCP integration using the official SDK client and server.

Catalog responses come from an explicitly simulated host process, not OpenAI.
Run with Python 3.10+ and optional/requirements-mcp.txt. Core tests remain separate.
"""
from __future__ import annotations

from datetime import timedelta
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'plugins/cloudcodex-environment-discovery/runtime'
sys.path.insert(0, str(RUNTIME))
from test_adapters import specification

SDK_PRESENT = importlib.util.find_spec('mcp') is not None


@unittest.skipUnless(SDK_PRESENT, 'Optional MCP SDK is not installed; core suite is independent')
class McpIntegrationTests(unittest.TestCase):
    def interact(self, action, mode='catalog_ok', configuration=None):
        import anyio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def scenario():
            with tempfile.TemporaryDirectory(prefix='discovery-sdk-test-') as folder:
                path = Path(folder) / 'adapter-config.json'
                config = configuration if configuration is not None else {
                    'schema_version': 1, 'timeout': 4, 'domains': {
                        domain: {'stages': [{'kind': 'primary', 'approved': True,
                                             'command': specification(mode, timeout=3)}]}
                        for domain in ('legacy', 'current')
                    }
                }
                path.write_text(json.dumps(config), encoding='utf-8')
                params = StdioServerParameters(command=sys.executable,
                    args=[str(RUNTIME / 'server.py'), '--config', str(path)], cwd=str(ROOT))
                with open(os.devnull, 'w') as error_log:
                    async with stdio_client(params, errlog=error_log) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session:
                            initialization = await session.initialize()
                            return await action(session, initialization)
        return anyio.run(scenario)

    def test_sdk_initializes_negotiated_stdio_session(self):
        async def action(session, initialization):
            from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS
            self.assertIn(initialization.protocolVersion, SUPPORTED_PROTOCOL_VERSIONS)
            self.assertEqual(initialization.serverInfo.name, 'cloudcodex-environment-discovery')
            self.assertIsNotNone(initialization.capabilities.tools)
            await session.send_ping()
        self.interact(action)

    def test_all_eight_tools_are_registered_readonly_and_structured(self):
        async def action(session, initialization):
            from server import TOOLS
            listing = await session.list_tools()
            self.assertEqual({t.name for t in listing.tools}, set(TOOLS))
            for tool in listing.tools:
                self.assertTrue(tool.annotations.readOnlyHint)
                self.assertFalse(tool.annotations.destructiveHint)
                self.assertIsNotNone(tool.outputSchema)
                self.assertNotIn('cloud_type', tool.inputSchema['properties'])
        self.interact(action)

    def test_all_eight_calls_use_the_correct_simulated_domain(self):
        async def action(session, initialization):
            for domain in ('legacy', 'current'):
                cases = [('list_' + domain + '_environments', {}),
                         ('find_' + domain + '_environments', {'repository': 'fixtures/demo'}),
                         ('get_' + domain + '_environment', {'environment_id': 'fixture-' + domain}),
                         ('resolve_' + domain + '_environment', {'repository': 'fixtures/demo'})]
                for name, args in cases:
                    result = await session.call_tool(name, args)
                    self.assertFalse(result.isError, result.content)
                    self.assertEqual(result.structuredContent['cloud_type'], domain)
                    self.assertTrue(result.structuredContent['catalog_complete'])
        self.interact(action)

    def test_bad_argument_types_are_rejected_without_echo(self):
        async def action(session, initialization):
            for args in ({'include_drafts': 'true'}, {'account': 17}, {'config': 'secret-value'},
                         {'cloud_type': 'all'}, {'token': 'secret-value'}):
                result = await session.call_tool('list_current_environments', args)
                self.assertTrue(result.isError)
                self.assertNotIn('secret-value', str(result.content))
                self.assertFalse(result.structuredContent['catalog_complete'])
        self.interact(action)

    def test_unknown_and_write_tools_are_not_invocable(self):
        async def action(session, initialization):
            for name in ('create_environment', 'list_environments', 'resolve_environment'):
                result = await session.call_tool(name, {})
                self.assertTrue(result.isError)
        self.interact(action)

    def test_required_repository_id_and_names_are_validated(self):
        async def action(session, initialization):
            for name, args in [('find_current_environments', {}),
                               ('get_legacy_environment', {}),
                               ('get_current_environment', {'environment_id': ''}),
                               ('resolve_current_environment', {'name': 42})]:
                result = await session.call_tool(name, args)
                self.assertTrue(result.isError)
        self.interact(action)

    def test_denied_catalog_is_error_not_successful_empty(self):
        async def action(session, initialization):
            result = await session.call_tool('list_current_environments', {})
            self.assertTrue(result.isError)
            self.assertEqual(result.structuredContent['status'], 'forbidden')
            self.assertFalse(result.structuredContent['catalog_complete'])
        self.interact(action, mode='deny')

    def test_no_configuration_produces_explicit_unavailable(self):
        async def action(session, initialization):
            result = await session.call_tool('list_legacy_environments', {})
            self.assertTrue(result.isError)
            self.assertEqual(result.structuredContent['provider']['reason'], 'no_authorized_source_configured')
        self.interact(action, configuration={'schema_version': 1, 'domains': {}})

    def test_empty_authoritative_catalog_is_valid_read(self):
        async def action(session, initialization):
            result = await session.call_tool('list_legacy_environments', {})
            self.assertFalse(result.isError)
            self.assertEqual(result.structuredContent['status'], 'empty')
            self.assertTrue(result.structuredContent['catalog_complete'])
        self.interact(action, mode='empty')

    def test_progress_reports_escalation_stages(self):
        messages = []
        async def action(session, initialization):
            async def progress(value, total, message):
                messages.append(message)
            result = await session.call_tool('list_current_environments', {}, progress_callback=progress)
            self.assertFalse(result.isError)
            self.assertIn('primary', messages)
        self.interact(action)

    def test_deadline_reports_tool_error_and_session_remains_usable(self):
        config = {'schema_version': 1, 'timeout': 0.3, 'domains': {
            'current': {'stages': [{'kind': 'primary', 'approved': True, 'command': specification('delay', 2)}]}}}
        async def action(session, initialization):
            result = await session.call_tool('list_current_environments', {})
            self.assertTrue(result.isError)
            self.assertEqual(result.structuredContent['status'], 'timeout')
            await session.send_ping()
        self.interact(action, configuration=config)

    def test_sdk_cancellation_is_not_fallback_or_server_shutdown(self):
        import anyio
        async def action(session, initialization):
            started = anyio.Event()
            async def progress(value, total, message):
                started.set()
            async def slow_call():
                await session.call_tool('list_current_environments', {}, progress_callback=progress)
            async with anyio.create_task_group() as group:
                group.start_soon(slow_call)
                with anyio.fail_after(5):
                    await started.wait()
                await anyio.sleep(0.1)
                group.cancel_scope.cancel()
            await session.send_ping()
            listing = await session.list_tools()
            self.assertEqual(len(listing.tools), 8)
        self.interact(action, mode='delay')



    def test_connector_hints_use_sdk_without_fabricating_cloud_ids(self):
        from common.models import now_utc
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'task-evidence.json'
            path.write_text(json.dumps({
                'schema_version': 1, 'source': 'codex_tasks', 'observed_at': now_utc(),
                'payload': {'tasks': [{'id': 'thread-id', 'title': 'Configure sample'}]}
            }), encoding='utf-8')
            config = {'schema_version': 1, 'domains': {'current': {'stages': [
                {'kind': 'onboarding', 'approved': True, 'path': str(path)}]}}}
            async def action(session, initialization):
                listing = await session.call_tool('list_current_environments', {})
                data = listing.structuredContent
                self.assertFalse(data['catalog_complete'])
                self.assertEqual(data['environments'], [])
                self.assertEqual(data['provider']['hints'][0]['task_id'], 'thread-id')
                self.assertIsNone(data['provider']['hints'][0]['configuration_id'])
                resolved = await session.call_tool('resolve_current_environment', {})
                self.assertTrue(resolved.isError)
                self.assertIsNone(resolved.structuredContent['selected'])
            self.interact(action, configuration=config)


if __name__ == '__main__':
    unittest.main()
