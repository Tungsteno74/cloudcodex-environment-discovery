# Current Cloud discovery contract

Scope: current-generation Codex Cloud only.

Only an already authorized transport may perform GET /v1/environment-configs with explicit scope=user/workspace, limit, cursor and omitDraft. This is an observed internal endpoint, not a stable public contract. Never infer draft absence from omitDraft=true, retry authentication with another identity, or bypass 401/403.

Connected MCP names:
- list_current_environments(account?, include_drafts?)
- find_current_environments(repository, account?, include_drafts?)
- get_current_environment(environment_id, account?)
- resolve_current_environment(repository?, name?, account?, include_drafts?)

Implementation is runtime/current/provider.py; independent tests are tests/test_current.py. Shared generic type models and repository matching are in runtime/common.

No dependency on Legacy. ChatGPT Root can use either skill directly or call both separately for an explicitly dual-generation request; this skill does not produce a mixed catalog.

States: draft/published/unknown configuration status, execution readiness independently, partial or unverified catalog evidence. Onboarding chats are auxiliary, never evidence of full inventory.
