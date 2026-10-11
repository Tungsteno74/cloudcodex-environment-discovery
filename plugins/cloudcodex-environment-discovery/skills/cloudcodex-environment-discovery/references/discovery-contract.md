# Root discovery contract

## Logical operations

- list_environments(account?, cloud_type='all', include_drafts=false)
- find_environments(repository, account?, cloud_type='all')
- get_environment(cloud_type, environment_id)
- resolve_environment(repository?, name?, cloud_type?, account?)

These operations are strictly read-only. The implementation may return partial catalogs, but must never replace an inaccessible catalog with an empty authoritative result.

## Descriptor

An EnvironmentDescriptor includes cloud_type, environment_id, name, repository, repository_id, account, scope, configuration_state (draft, published, unknown), execution_ready (unknown unless tested separately), discovery_source, evidence (live, imported, indirect or cache), observed_at and repository_match.

ProviderStatus includes provider, status (ok, empty, unavailable, unauthorized, forbidden, invalid_response, partial, stale), catalog_complete, requested_scope, provenance and warnings.

catalog_complete=true means every requested provider and scope was verified complete via trusted live data. Importing a snapshot never proves live catalog completeness.

## Legacy

Native Codex CLI selector via 'codex cloud' is the preferred authorized route. Interactive TUI snapshots alone can show names but may not provide verified immutable IDs. Do not treat 'codex cloud list --json' as an environment list. A direct GET /backend-api/wham/environments may be implemented behind an injected explicitly authorized transport, not by extracting local session files.

## Current

Current Cloud catalog GET /v1/environment-configs may require user/workspace scopes, pagination and draft-specific queries. Query only through an authorized transport and stop on 401/403. Published configurations and drafts have different states. The catalog endpoint is internal, versioned and not a documented stable public API.

## GitHub matching

Join using verified repository ID first, then explicit normalized owner/repo. A repository name matching the environment label is not proof. Return all matching environments; selection is only for a unique verified live descriptor.

## Security and compatibility

- No task creation, provisioning, GitHub writes, browser automation or token retrieval in discovery.
- No raw secrets in diagnostics. No logging of raw error response bodies.
- For old/new clients, treat missing operations as provider unavailability rather than fabricated empty inventories.
- Reconcile old IDs/cache against live provider data before delegating.
