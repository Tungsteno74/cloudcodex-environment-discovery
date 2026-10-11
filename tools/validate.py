"""Run either the dependency-free core profile or core + real SDK MCP tests."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/cloudcodex-environment-discovery'
CORE_SUITES = ('common', 'legacy', 'current', 'adapters', 'interface')


def validate_structure():
    portable = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
    compatibility = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    if portable['name'] != PLUGIN.name or (portable['name'], portable['version']) != (compatibility['name'], compatibility['version']):
        raise ValueError('Plugin identity/version mismatch')
    if 'skills' in portable or 'mcpServers' in portable:
        raise ValueError('Non-portable top-level manifest fields')
    presentation = portable['extensions']['com.openai']['interface']
    if len(presentation['shortDescription']) > 30:
        raise ValueError('Listing subtitle too long')
    for skill in ('legacy-discovery', 'current-discovery'):
        root = PLUGIN / 'skills' / skill
        if 'name: ' + skill not in (root / 'SKILL.md').read_text(encoding='utf-8'):
            raise ValueError('Skill identity mismatch')
        if not (root / 'agents/openai.yaml').is_file() or not list((root / 'references').glob('*.md')):
            raise ValueError('Missing standalone skill resources')
        if '$' + skill not in presentation['defaultPrompt']:
            raise ValueError('Missing direct skill routing hint')
    if sorted(p.parent.name for p in (PLUGIN / 'skills').glob('*/SKILL.md')) != ['current-discovery', 'legacy-discovery']:
        raise ValueError('Only the two independent skills may be bundled')
    if (PLUGIN / 'mcp.json').exists():
        raise ValueError('MCP must remain opt-in')
    required = ('optional/mcp.json', 'optional/requirements-mcp.txt', 'optional/discovery.example.json',
                'runtime/server.py', 'runtime/cli.py', 'runtime/common/operation.py',
                'runtime/common/configuration.py', 'runtime/common/adapters.py',
                'runtime/common/escalation.py', 'runtime/common/catalog.py',
                'runtime/common/models.py', 'runtime/common/service.py',
                'runtime/current/provider.py', 'runtime/legacy/provider.py', '.app.json')
    for relative in required:
        if not (PLUGIN / relative).is_file():
            raise ValueError('Required resource missing: ' + relative)
    template = json.loads((PLUGIN / 'optional/mcp.json').read_text(encoding='utf-8'))
    entry = next(iter(template['mcpServers'].values()))
    if entry.get('type') != 'stdio' or 'runtime/server.py' not in ' '.join(entry.get('args', [])):
        raise ValueError('Invalid optional MCP template')
    for domain, other in (('legacy', 'current'), ('current', 'legacy')):
        for source in ('provider.py', 'api.py'):
            text = (PLUGIN / 'runtime' / domain / source).read_text(encoding='utf-8')
            if 'from ' + other in text:
                raise ValueError('Providers may not import each other')
    for path in PLUGIN.rglob('*'):
        if path.name.casefold() in {'.env', 'auth.json', 'credentials.json'}:
            raise ValueError('Credential-like file in distributable package')
    if (PLUGIN / 'runtime/discovery').exists() or (ROOT / '.agents').exists():
        raise ValueError('Obsolete mixed catalog or embedded marketplace')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-mcp', action='store_true', help='Require and test the real MCP SDK profile')
    args = parser.parse_args(argv)
    if args.with_mcp and (sys.version_info < (3, 10) or importlib.util.find_spec('mcp') is None):
        parser.error('--with-mcp requires Python >=3.10 and optional/requirements-mcp.txt')
    validate_structure()
    suites = CORE_SUITES + (('mcp',) if args.with_mcp else ())
    total, passed = 0, True
    for name in suites:
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_' + name + '.py')
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        suite_ok = result.wasSuccessful() and not result.skipped and result.testsRun > 0
        total += result.testsRun
        passed = passed and suite_ok
        print('suite=%s tests=%s passed=%s skipped=%s' % (name, result.testsRun, suite_ok, len(result.skipped)))
    print('profile=%s package_structure=ok tests_run=%s success=%s' %
          ('core+mcp' if args.with_mcp else 'core', total, passed))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
