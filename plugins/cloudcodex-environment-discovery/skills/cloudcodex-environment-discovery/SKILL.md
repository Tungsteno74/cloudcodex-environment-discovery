---
name: cloudcodex-environment-discovery
description: Root-level read-only discovery and resolution of existing Codex Cloud Legacy and current environments before task creation. Use to find environment IDs, match repositories, assess drafts and catalog completeness, and avoid choosing an environment from an empty Codex Tasks inventory.
---

# Codex Cloud Environment Discovery

This skill runs from the **Root Orchestrator**, before any Cloud task exists. It is independent of CloudCodeX Windows Bootstrap and of any provisioning or credential broker.

## Rules

1. Treat a native hosted Cloud environment catalog as authoritative only when obtained from an **already authorized** session and with live evidence. An empty Codex Tasks.list_environments inventory is never proof that hosted environments do not exist.
2. For Legacy, prefer the authenticated **codex cloud** native environment selector (the interactive TUI key 'o: Set Env'), which can enumerate environments with zero tasks. The command **codex cloud list --json lists tasks**, not environments. Do not infer an environment ID from a task ID or repository name.
3. For Current, prefer a supported native catalog connector if available. Only through an explicitly authorized transport, GET the current environment-configs catalog with user/workspace scopes and correct pagination. The query omitDraft=true deliberately excludes drafts. Never infer draft absence from it.
4. The packaged MCP server exposes list_environments, find_environments, get_environment, resolve_environment, but **does not discover credentials**. It can accept imported read-only catalog snapshots as evidence, always marked imported/unverified. Its live provider adapters require explicitly authorized injection/integration; local Python MCP servers are not automatically available in ChatGPT web/mobile.
5. If the native selector is available to the Root through a terminal tool, use it read-only and obtain IDs by verified client evidence. A visible name alone is not a verified ID. Do not launch tasks, approve mutations or create environments to discover identifiers.
6. If repository metadata is accessible through the existing GitHub plugin, match repository ID first, then a normalized explicit owner/repo association; names alone are only hints. Multiple environments per repo are valid.
7. Distinguish unauthorized, forbidden, not found, empty complete, partial, stale, unavailable, and invalid responses. On 401/403 stop the affected provider without changing identities or retrying through challenge bypass.
8. A unique resolution requires a live, verified identity; imported data, onboarding chats and cache hints can support candidate presentation only. Revalidate before selecting an executor.
9. Return provider statuses, warnings, catalog_complete, observation time, candidate count, and a concise next supported step. Never disclose tokens, cookies, account secrets or raw HTTP error bodies.

## Root workflow

- Determine requested account, cloud type, repository and draft inclusion. If missing, default to all cloud types and published-only discovery.
- Discover available authorized channels and actual runtime capabilities. The packaged skill is **instructions**; an MCP tool is available only if a host has connected its local runtime.
- Query available providers in read-only mode; keep scopes and pagination explicit; treat denial as a blocker rather than no matches.
- Optionally use GitHub to verify repository identity without writes.
- Resolve only when evidence is live and unambiguous; otherwise present candidates and precise gap.
- Pass a resolved EnvironmentDescriptor to CloudCodeX Windows Bootstrap only through a later, separately authorized workflow. This skill never starts that workflow.

See references/discovery-contract.md for normalised data contracts, status semantics and fallback requirements.
