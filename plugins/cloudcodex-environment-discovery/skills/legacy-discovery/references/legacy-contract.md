# Legacy discovery contract

This skill exclusively handles Legacy hosted Codex Cloud.

Preferred source: authenticated native **codex cloud** environment selector, including zero-task environments. **codex cloud list --json lists TASKS** and cannot replace the environment catalog.

Use only authorized native client evidence, or an explicitly authorized read-only GET /backend-api/wham/environments adapter.

Connected local MCP names:
- list_legacy_environments(account?, include_drafts?)
- find_legacy_environments(repository, account?, include_drafts?)
- get_legacy_environment(environment_id, account?)
- resolve_legacy_environment(repository?, name?, account?, include_drafts?)

Implementation is runtime/legacy/provider.py; independent tests are tests/test_legacy.py. Shared types and matching rules are in runtime/common. Current Cloud need not load Legacy and does not require it to pass tests.

A live immutable ID and complete relevant catalog are necessary for an automatic selection. Cached or imported catalog records are candidates. Stop on 401/403 and never auto-create a Cloud task merely to discover IDs.
