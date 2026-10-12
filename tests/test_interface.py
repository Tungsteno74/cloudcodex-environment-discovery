"""Skill/package/CLI regressions; no MCP dependency is needed for this suite."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/cloudcodex-environment-discovery'
RUNTIME = PLUGIN / 'runtime'
sys.path.insert(0, str(RUNTIME))
import server


class InterfaceTests(unittest.TestCase):
    def test_exactly_two_direct_domain_skills(self):
        self.assertEqual(sorted(p.parent.name for p in (PLUGIN / 'skills').glob('*/SKILL.md')),
                         ['current-discovery', 'legacy-discovery'])

    def test_no_mandatory_root_skill(self):
        self.assertFalse((PLUGIN / 'skills/cloudcodex-environment-discovery').exists())

    def test_skill_frontmatter_and_local_references(self):
        for name in ('current-discovery', 'legacy-discovery'):
            root = PLUGIN / 'skills' / name
            self.assertIn('name: ' + name, (root / 'SKILL.md').read_text(encoding='utf-8'))
            self.assertTrue((root / 'agents/openai.yaml').is_file())
            self.assertTrue(list((root / 'references').glob('*.md')))

    def test_portable_and_compatibility_versions_match_runtime(self):
        a = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
        b = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertEqual((a['name'], a['version']), (b['name'], b['version']))
        self.assertEqual(a['version'], server.VERSION)
        self.assertNotIn('skills', a)
        self.assertNotIn('mcpServers', a)

    def test_manifest_routes_without_extra_skill(self):
        manifest = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
        prompt = manifest['extensions']['com.openai']['interface']['defaultPrompt']
        self.assertIn('$legacy-discovery', prompt)
        self.assertIn('$current-discovery', prompt)

    def test_eight_strict_readonly_tools_not_mixed(self):
        specifications = server.tool_specs()
        self.assertEqual(len(specifications), 8)
        self.assertEqual(set(server.TOOLS), {s['name'] for s in specifications})
        for specification in specifications:
            self.assertNotIn('cloud_type', specification['inputSchema']['properties'])
            self.assertFalse(specification['inputSchema']['additionalProperties'])
            self.assertTrue(specification['annotations']['readOnlyHint'])
            self.assertFalse(specification['annotations']['destructiveHint'])
            self.assertIn('outputSchema', specification)
        self.assertNotIn('list_environments', server.TOOLS)

    def test_plugin_cannot_start_mcp_implicitly(self):
        self.assertFalse((PLUGIN / 'mcp.json').exists())
        optional = json.loads((PLUGIN / 'optional/mcp.json').read_text(encoding='utf-8'))
        entry = next(iter(optional['mcpServers'].values()))
        self.assertEqual(entry['type'], 'stdio')
        self.assertIn('PLUGIN_ROOT', ' '.join(entry['args']))

    def test_cli_requires_explicit_type(self):
        result = subprocess.run([sys.executable, str(RUNTIME / 'cli.py'), 'list'],
                                capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)

    def test_cli_returns_isolated_provider_status(self):
        for domain in ('legacy', 'current'):
            result = subprocess.run([sys.executable, str(RUNTIME / 'cli.py'), domain, 'list'],
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            body = json.loads(result.stdout)
            self.assertEqual(body['cloud_type'], domain)
            self.assertFalse(body['catalog_complete'])
            self.assertEqual(body['provider']['provider'], domain)

    def test_doctor_never_claims_live_coverage(self):
        result = subprocess.run([sys.executable, str(RUNTIME / 'cli.py'), 'current', 'doctor'],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['live_tested'])

    def test_source_modules_are_independent(self):
        for domain, other in (('current', 'legacy'), ('legacy', 'current')):
            for name in ('provider.py', 'api.py'):
                text = (RUNTIME / domain / name).read_text(encoding='utf-8')
                self.assertNotIn('from ' + other, text)
        self.assertFalse((RUNTIME / 'discovery').exists())

    def test_no_credentials_or_marketplace_embedded(self):
        names = {p.name.lower() for p in PLUGIN.rglob('*') if p.is_file()}
        self.assertFalse(names & {'.env', 'auth.json', 'credentials.json'})
        self.assertFalse((ROOT / '.agents/plugins/marketplace.json').exists())


class BrandingTests(unittest.TestCase):
    def test_both_manifests_share_the_actual_local_icon(self):
        portable = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
        compatibility = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        for view in (portable['extensions']['com.openai']['interface'], compatibility['interface']):
            self.assertEqual(view['logo'], './assets/icon.png')
            self.assertEqual(view['composerIcon'], './assets/icon.png')
            self.assertTrue((PLUGIN / view['logo']).is_file())

    def test_icon_is_square_rgba_png(self):
        import struct
        data = (PLUGIN / 'assets/icon.png').read_bytes()
        self.assertEqual(data[:8], bytes([137, 80, 78, 71, 13, 10, 26, 10]))
        self.assertEqual(data[12:16], b'IHDR')
        width, height, depth, color = struct.unpack('>IIBB', data[16:26])
        self.assertEqual((width, height, depth, color), (1254, 1254, 8, 6))

    def test_provenance_and_packaged_icon_are_consistent(self):
        import hashlib
        provenance = json.loads((PLUGIN / 'assets/icon-origin.json').read_text(encoding='utf-8'))
        self.assertEqual(provenance['source_git_blob'], '90f40edf8326fa3f6aab967af186badd17f86dff')
        self.assertEqual(provenance['source_repository'], 'Tungsteno74/cloudcodex-windows-bootstrap')
        self.assertEqual(provenance['output_sha256'], hashlib.sha256((PLUGIN / 'assets/icon.png').read_bytes()).hexdigest())
        source = ROOT / provenance['approved_source_path']
        self.assertTrue(source.is_file())
        self.assertEqual(provenance['approved_source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(provenance['background_transparent'])
        self.assertTrue(provenance['foreground_rgb_preserved'])
        self.assertFalse(provenance['alpha_unchanged'])
        self.assertFalse(provenance['outside_region_unchanged'])


if __name__ == '__main__':
    unittest.main()
