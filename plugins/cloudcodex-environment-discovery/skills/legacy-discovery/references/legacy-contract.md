# Legacy execution contract

## Scope and research

Only existing Legacy Codex Cloud environments are in scope. The 10 October research verified discovery of a zero-task environment through the native client. The source inspected at OpenAI Codex commit `4aa94dce270de668eff6e2fa8585c82385e84455` uses the global `/backend-api/wham/environments` GET and the GitHub by-repository route. Those are internal client contracts, not guaranteed public APIs.

The integrated native-session adapter attempted in v0.3.0 was blocked by a tool security control; no such reader is shipped. The executable primary adapter therefore requires a separately approved host implementing the catalog protocol. **Do not route around a host/tool refusal.**

## Startup configuration and execution

CLI form: `python <plugin-root>/runtime/cli.py legacy <doctor|list|find|get|resolve> --config <absolute-config-path>`.

Configuration schema version 1 contains `mode` (AUTO or CONFIRM), a bounded operation `timeout`, and `domains.legacy.stages`. Legacy stages are ordered `primary`, `http`, `snapshot`, each explicitly `approved: true` before execution. Source configuration and commands are never accepted as MCP tool parameters.

A live host stage contains `command.argv` (absolute executable/script plus fixed arguments), `command.sha256` (integrity pins for those files), `command.cwd`, and a bounded request timeout. No shell, inline code or credential arguments are supported. A snapshot stage instead contains an absolute catalog `path`. File hashes verify identity, not host safety or permission.

## Host protocols

Primary request: schema_version=1, operation=catalog_read, cloud_type=legacy, account, include_drafts, scopes=[user]. The host returns matching schema/domain, status, catalog records, fresh observed_at, account provenance, echoed scopes/draft flags and truthful completeness. A raw interactive Codex invocation does not implement this JSON protocol.

HTTP request: operation=http_get, method=GET, cloud_type=legacy, an allowlisted URL and query. The relay returns integer status, actual content_type, observed_at, observed account metadata and JSON body only for HTTP 200. Native authentication stays inside the approved host; this package never extracts it.

Allowed routes:
- Global catalog: `https://chatgpt.com/backend-api/wham/environments`.
- Explicit repository association: `.../environments/by-repo/github/{owner}/{repo}`.

Only a validated by-repository response can supply an otherwise missing association; a matching display label cannot. Numeric repository IDs are matched explicitly against catalog data rather than guessed from names.

## Escalation and result

Complete live success—including an empty catalog—stops. Missing/partial sources may proceed only to the next pre-approved stage. AUTO cannot approve a stage. CONFIRM returns approval_required if consent is missing. A 401/403, rate limit, integrity/account mismatch, policy denial, cancellation or timeout ends the sequence.

Each result includes status, catalog_complete, source/evidence, observed_at and ordered attempts with timings/reasons. Snapshots remain imported candidates. Resolve requires one fresh, live verified identity and complete relevant coverage. Version/draft ambiguity is preserved; cached IDs are not current truth.

Optional MCP equivalents: list_legacy_environments, find_legacy_environments, get_legacy_environment, resolve_legacy_environment. MCP is not an authentication mechanism or a prerequisite. No Current lookup, task creation, provisioning, browser control or GitHub writes are part of this skill.

## Optional GitHub identity verification (v0.3.1)

When already enabled in startup configuration, the native GitHub adapter verifies repository identity through the existing gh account. It uses only fixed GET operations and does not read credentials. Configuration uses github.enabled, an absolute gh executable path and SHA-256 pin, and an optional expected GitHub account (not the ChatGPT account). The default is disabled. Root can alternatively use its existing authorized GitHub connector.

find/resolve prefer the verified numeric repository ID, then canonical owner/repo; a matching name cannot override an ID conflict. GitHub success is repository evidence only and must not be described as an existing Cloud environment. A configured GitHub verification failure stops the dependent lookup rather than broadening access.
