---
name: current-discovery
description: Discover and resolve CURRENT-GENERATION Codex Cloud environment configurations before task creation. Use for current Cloud config IDs, published configurations, drafts, user/workspace scopes and environment-configs catalogs. Do not use for Legacy environments.
---

# Current-generation Codex Cloud discovery

Scope: CURRENT only. Directly invocable by ChatGPT Root. Independent of Legacy, any running Child and Windows Bootstrap.

## Procedure

1. Identify the requested account, current-generation environment, repository, desired scope and whether drafts must be included.
2. Prefer a supported current-generation catalog connector already authorized for this account. The tool must return verifiable immutable IDs; never infer existence or absence from Codex Tasks.list_environments.
3. Where permitted, the observed internal client GET /v1/environment-configs requires an **authorized injected transport**; request explicit user/workspace scopes, bounded pagination and draft flags. Client internals are version-sensitive, not public API contracts.
4. **omitDraft=true excludes drafts**; it does not prove they are absent. Keep draft/published/unknown configuration status separate from execution readiness.
5. Codex Tasks.list_tasks or read_task may contain onboarding chat hints, but do not establish catalog completeness or a valid configuration ID.
6. With a compatible connected MCP runtime, call **list_current_environments**, **find_current_environments**, **get_current_environment** or **resolve_current_environment**. No credentials are acquired by this package; without an authorized transport it returns unavailable, never an authoritative empty catalog.
7. Match verified repository IDs first, then explicit normalized owner/repo. Preserve all ambiguous candidates.
8. Resolve only a unique live verified configuration with complete requested catalog coverage; otherwise report evidence and missing authorizations.

## Invariants

- Read-only. No environment/task creation, GitHub write, credential extraction, token switching or Cloudflare challenge bypass.
- Stop on HTTP 401/403 and distinguish denied, unavailable, empty and partial catalogs.
- The skill never loads Legacy. For both generations the Root can call current-discovery and legacy-discovery independently; no mandatory third Root skill exists.
- Metadata guidance is advisory, not a deterministic automatic dispatcher.

See references/current-contract.md for scope and pagination details.
