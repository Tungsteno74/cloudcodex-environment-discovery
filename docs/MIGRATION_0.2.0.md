# Upgrade from v0.1.1 to v0.2.0

This release changes **plugin instructions and local MCP tool contracts**. It is an intentional pre-1.0 incompatible interface change.

## Skills

Previous: a single Root skill called cloudcodex-environment-discovery.

New: **legacy-discovery** and **current-discovery**, both selectable directly. The plugin name is unchanged. No mandatory Root-level dispatcher skill exists. The package manifest provides routing hints.

## MCP tools

Previous generic names (removed):
- list_environments
- find_environments
- get_environment
- resolve_environment

New Legacy names:
- list_legacy_environments
- find_legacy_environments
- get_legacy_environment
- resolve_legacy_environment

New Current names:
- list_current_environments
- find_current_environments
- get_current_environment
- resolve_current_environment

No tool accepts cloud_type=all. Calling an old name returns an unknown-tool error. Update host automation explicitly.

## CLI

Previous: python runtime/cli.py list --cloud-type legacy

New: python runtime/cli.py legacy list

Snapshot flag is now a single domain-scoped --snapshot. The CLI requires an explicit Cloud generation and cannot silently fall back to a mixed inventory.

## Modules

Previous: runtime/discovery/{models,providers,service,api}.py

New: runtime/common (domain-neutral), runtime/legacy and runtime/current. Consumers using private internal Python imports must migrate.

## Preserved limitations

Neither provider acquires credentials automatically. The Legacy native CLI TUI reader and Current authenticated catalog transport remain integration tasks. Neither a GitHub release nor the marketplace draft PR attaches local MCP tools to ChatGPT web automatically.
