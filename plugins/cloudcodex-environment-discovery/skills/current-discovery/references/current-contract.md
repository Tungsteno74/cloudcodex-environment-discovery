# Current-generation execution contract

## Scope and evidence

Only current-generation Codex Cloud configurations are in scope. The original 10 October research reported one successful catalog GET followed by a later 403. The successful query used `omitDraft=true`; it did not validate unpublished-draft coverage or permanent authorization. Do not present historical IDs, onboarding chats or a cached 200 response as current operational access.

## Execution without MCP

Use the verified plugin path and a permitted executor:

`python <plugin-root>/runtime/cli.py current <doctor|list|find|get|resolve> --config <absolute-operator-config>`

The operator configuration uses schema_version=1, mode=AUTO|CONFIRM, an operation timeout, and `domains.current` with explicit scopes, pagination bounds and ordered stages. Supported stages are `primary`, `http`, `onboarding`, `snapshot`. Each requires `approved: true` before running.

A live stage names an absolute executable/script, explicit working directory and SHA-256 file pins under `command`; no shell, inline code or credentials are accepted. Pins establish file integrity, not approval or host safety. The package includes a working host adapter protocol, **not an automatically authenticated OpenAI host**. Raw Codex Tasks commands or an interactive browser do not implement this protocol.

## Primary and HTTP protocols

Primary request: schema_version=1, operation=catalog_read, cloud_type=current, requested account, include_drafts and requested scopes. The host must return matching schema/domain, fresh observed_at, explicit account provenance, catalog records and truthful completeness with echoed scopes/draft flags.

HTTP request: operation=http_get, method=GET, cloud_type=current, allowlisted `/v1/environment-configs` URL and scope/limit/cursor/omitDraft query. Response: integer HTTP status, real content_type, fresh observed_at, account provenance and JSON body only on HTTP 200. HTML interstitials cannot masquerade as catalog success. A denial remains terminal even if its timestamp is absent.

The runtime checks every page before accepting it, limits pagination, rejects cursor loops, preserves drafts and versions with the same ID, and rejects conflicting records. The relevant catalog coverage is the explicitly configured scope, not an assumed complete account inventory.

## Auxiliary evidence

An `onboarding` host reads already-authorized configuration/onboarding data using operation=onboarding_read and supplies explicit configuration identifiers. These results remain indirect and incomplete regardless of the host's claims. A task ID or display title is not a configuration ID.

A `snapshot` stage reads an explicitly supplied sanitized catalog file. It is imported candidate evidence, never live. Neither auxiliary channel can be used to bypass a 401/403 from an earlier stage.

## Stop and resolution rules

Complete live success, including a verified empty result, ends escalation. Missing/partial sources may proceed only to another already-approved stage. AUTO cannot grant consent; CONFIRM returns approval_required. Stop on authentication/policy denial, rate limiting, identity/integrity mismatch, cancellation or timeout.

Keep configuration publication state separate from execution readiness. `omitDraft=true` excludes drafts rather than proving no drafts exist. Match explicit GitHub IDs before owner/repo, never labels alone. Resolve only one fresh, live verified candidate with complete requested coverage; return ambiguity or the precise blocker otherwise.

Optional MCP equivalents: list_current_environments, find_current_environments, get_current_environment, resolve_current_environment. MCP is optional and does not supply authentication. No Legacy calls, provisioning, Cloud task creation or credential-broker behavior belong in this skill.
