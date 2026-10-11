---
name: legacy-discovery
description: Discover and resolve existing Codex Cloud LEGACY environments before any task is created. Use for Legacy environment IDs, old Codex Cloud selector, zero-task environments and Legacy GitHub repository associations. Do not use for current-generation Cloud configs.
---

# Codex Cloud Legacy environment discovery

Scope: LEGACY only. This skill is directly discoverable by ChatGPT Root. It needs no coordinating Root skill, running Child, Cloud task or Windows Bootstrap.

## Procedure

1. Determine the requested repository, account, environment ID or name. Without a repository, list the Legacy catalog rather than inferring GitHub associations from environment labels.
2. Prefer the authenticated native **codex cloud** selector, including its **o: Set Env** operation, when available through an authorized interactive terminal. It has enumerated Legacy environments with zero tasks. **codex cloud list --json enumerates tasks, not environments.**
3. Read only legitimate selector catalog evidence. Capture immutable ID, label, explicit GitHub association and observation time. A visible name without immutable ID is a candidate, not verified.
4. If the Root has a connected authorized Legacy catalog client, a controlled GET /backend-api/wham/environments is an optional version-sensitive fallback. Never extract auth.json, cookies or tokens. Stop on 401/403.
5. For a compatible connected local MCP runtime, call **list_legacy_environments**, **find_legacy_environments**, **get_legacy_environment** or **resolve_legacy_environment**. The packaged runtime has no credential acquisition and no default interactive selector reader; without authorized injection it returns unavailable.
6. Match repository ID first, then explicit owner/repo association. Environment-label similarity is a hint only. One repository can have multiple environments.
7. Resolve only a single **live verified** environment with complete requested Legacy coverage. Otherwise return candidates, catalog_complete=false, provenance and exact missing capability.
8. Return a normalized EnvironmentDescriptor to Root. Cloud task creation, provisioning and Windows Bootstrap are separate later operations.

## Invariants

- Read-only. No task creation, GitHub writes, configuration mutation or privilege escalation.
- Codex Tasks.list_environments is NOT the full hosted Cloud catalog. Empty, partial, stale, unauthorized and unavailable are different.
- This skill does not invoke the current Cloud provider. Root may independently invoke **legacy-discovery** and **current-discovery** for explicit requests concerning both generations.
- No security challenge bypass or conjectural immutable IDs.

See references/legacy-contract.md for Legacy evidence and error semantics.
