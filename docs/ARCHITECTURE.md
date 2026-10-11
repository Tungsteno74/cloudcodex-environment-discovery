# Architecture — Codex Cloud Environment Discovery

## Scope

This project implements the separate Root-facing discovery component defined in the 10 October 2026 research note. No modifications to CloudCodeX Windows Bootstrap 0.6.6 Gate 1-2-3 E2E are permitted or necessary.

## Workflow order

```text
Optional environment provisioning (separate, future)
                   |
                   v
Codex Cloud Environment Discovery (read-only)
  +- Legacy provider: native selector / authorized HTTP fallback
  +- Current provider: authorized catalog / scoped pagination
  +- GitHub repository matching (optional Root connector)
                   |
             verified descriptor?
                  / \\
                yes  no
                 |    +--> candidate set + evidence/authorization gaps
                 v
Root selects executor and authorizes a separate task
                 |
                 v
CloudCodeX Windows Bootstrap -> GitHub Actions Windows (when applicable)
```

The discovery process runs before tasks, so it cannot assume a Child task already exists. A raw task ID, onboarding chat, a zero-task catalog or a cached configuration ID cannot automatically be interpreted as a valid environment descriptor.

## Provider contracts

Provider.list_environments(account, include_drafts) -> ProviderResult. The facade normalizes account, cloud_type, environment_id, repository identity and explicit evidence. Environment statuses (`execution_ready`) and configuration statuses (`configuration_state`) are distinct.

- **Legacy:** authenticated Codex CLI selector is preferred. A typed live provider may be injected by a host capable of safely obtaining catalog records and immutable IDs. HTTP GET fallback requires an explicitly authorized injected transport.
- **Current:** injected transport performs GET `/v1/environment-configs` using user/workspace scopes, explicit omitDraft flag and bounded cursor pagination. The plugin never obtains or refreshes auth itself.
- **GitHub:** Root uses its existing GitHub connector when available. ID and explicit owner/repo associations are authoritative; labels can only produce hints. One repository may correspond to many environments.

## Completeness and selection invariant

`catalog_complete=true` if and only if every requested provider/scope is complete **and** live. Imported snapshots and unavailable catalog integrations never set this flag. `resolve_environment` selects only a unique live descriptor, an explicitly verified repository match when requested, and complete catalog evidence. Otherwise it returns candidates with unverified/ambiguous/not_verifiable states.

## Architectural boundaries

- No environment/task creation or GitHub mutations.
- No direct access to `~/.codex/auth.json`, browser cookies or stored tokens.
- No silent fallback from 401/403 to another identity, bypass or scraped cookie.
- No declared absence without catalog completeness proof.
- Endpoint adapters remain replaceable as internal Codex APIs evolve.
- Local MCP runtime requires installation/host capability; skill-only discovery remains possible in Root Chat using already connected authorized tools.

## Project acceptance criteria

Offline: provider adapters, repository matching, ambiguity, failure semantics, MCP framing and package format must pass automated tests.

Live acceptance **pending**: discover a zero-task Legacy environment through an authorized native client; obtain a complete Current catalog with user/workspace scopes and drafts correctly reported; verify actual immutable IDs; confirm persistence and resolution without creating a task or writing externally.
