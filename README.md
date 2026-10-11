# CloudCodeX Environment Discovery

An independent **read-only Codex Cloud environment discovery plugin**, designed for the ChatGPT Root **before** starting Cloud tasks. This repository is separate from [CloudCodeX Windows Bootstrap](https://github.com/Tungsteno74/cloudcodex-windows-bootstrap), which consumes verified environment descriptors only in later, separately authorized workflows.

**Status:** v0.2.0 preview. Domain architecture and offline contracts are implemented and tested; live authenticated catalog integrations remain pending.

## Independent skills

The plugin contains exactly **two directly discoverable skills**:

| Skill | Scope | Main catalog source |
|---|---|---|
| **legacy-discovery** | Codex Cloud Legacy | Authenticated native Codex CLI selector; controlled authorized HTTP fallback |
| **current-discovery** | Current-generation Codex Cloud | Authorized environment-configs catalog with scopes/drafts/pagination |

There is **no mandatory third Root skill**. The plugin entry-point metadata suggests the correct skill based on intent. This is advisory: installing the plugin and providing the right capabilities does not guarantee model routing.

A request for both generations requires the Root to call **both skills independently** and report the two statuses separately; no implicit mixed catalog is exposed. The Root must preserve read-only constraints.

## Architecture

Source code and tests are also independently organized:

- plugins/cloudcodex-environment-discovery/runtime/legacy/provider.py
- plugins/cloudcodex-environment-discovery/runtime/current/provider.py
- plugins/cloudcodex-environment-discovery/runtime/common/{models,protocols,matching,snapshot,service}.py
- tests/test_legacy.py and tests/test_current.py, alongside common and MCP regression suites

Legacy retirement therefore only affects its skill, provider, tests, MCP registration and packaging metadata. It **does not require modifying Current's provider or tests**. Shared types, repository association and response semantics are cloud-generation agnostic.

## Eight read-only MCP operations

| Legacy | Current |
|---|---|
| list_legacy_environments | list_current_environments |
| find_legacy_environments | find_current_environments |
| get_legacy_environment | get_current_environment |
| resolve_legacy_environment | resolve_current_environment |

No operation has cloud_type=all or creates tasks/environments. A connected local MCP host invokes only the corresponding provider through lazy imports.

The equivalent CLI requires an **explicit first positional type**:

~~~shell
python plugins/cloudcodex-environment-discovery/runtime/cli.py legacy list --pretty
python plugins/cloudcodex-environment-discovery/runtime/cli.py current list --pretty
python plugins/cloudcodex-environment-discovery/runtime/cli.py current find --repository owner/repo --pretty
python plugins/cloudcodex-environment-discovery/runtime/cli.py legacy find --repository owner/repo --snapshot path/to/sanitized-catalog.json
~~~

Imported snapshots are unverified candidates and never replace live evidence.

## Authorization and current limitations

- The local MCP runtime **does not** obtain credentials or silently access auth.json, cookies, Chrome profiles or account tokens.
- The Legacy provider accepts an authorized native-selector reader or authorized HTTP transport. The interactive TUI reader is **not yet integrated by default**.
- The Current provider implements bounded user/workspace pagination and draft handling, but its live transport must be injected by an authorized host.
- An unavailable, denied or partial catalog is **never** represented as a verified empty inventory.
- Local MCP stdio is not automatically available in ChatGPT web/mobile merely by publishing or linking this GitHub repository. This plugin is not yet attached as a live tool to the Root Chat.
- Codex Tasks.list_environments is not an authoritative complete hosted Cloud environment catalog.

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SECURITY.md](docs/SECURITY.md) for evidence and security details.

## Development

Python **3.9+**, standard-library runtime; no live token or Cloud call required by tests.

~~~shell
python -X utf8 tools/validate.py
python -X utf8 tools/build_release.py
python -m unittest discover -s tests -p test_legacy.py -v
python -m unittest discover -s tests -p test_current.py -v
~~~

The package is produced at dist/cloudcodex-environment-discovery-0.2.0.zip and contains only the one standalone plugin directory.

## Distribution

Canonical source: [Tungsteno74/cloudcodex-environment-discovery](https://github.com/Tungsteno74/cloudcodex-environment-discovery).

Its [GSM family marketplace](https://github.com/Tungsteno74/cloudcodex-helpers-marketplace) references source with git-subdir and does not embed implementation code. The marketplace inclusion is staged in a **draft PR**, pending authorized live acceptance before public merge.

Version **0.2.0** replaces the v0.1.1 single Root skill and four mixed tools with two domain skills and eight domain-specific tools; see [migration notes](docs/MIGRATION_0.2.0.md).

Licensed under MIT.
