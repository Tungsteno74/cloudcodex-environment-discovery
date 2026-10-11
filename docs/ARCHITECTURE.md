# Architecture — CloudCodeX Environment Discovery

## Position in the CloudCodeX ecosystem

The plugin belongs to ChatGPT Chat's **Root Orchestrator** before any Cloud task exists. It is not a Child skill and is independent of the Windows Bootstrap 0.6.6 Gate 1–2–3 validation pipeline.

~~~text
Optional independent provisioning workflow (future, outside plugin)
                   |
            Root chooses target type
              /              \
    Legacy skill           Current skill
        |                      |
  Legacy provider        Current provider
        |                      |
  read-only Legacy        read-only Current
     catalog                  catalog
        \                      /
         Root interprets independent descriptors
                   |
          selected verified environment
                   |
       Separate task / Windows Bootstrap workflow
~~~

There is **no Root dispatcher skill** and no shared all-types listing. The plugin manifest's defaultPrompt is advisory only; model routing is not a deterministic startup callback.

## Ownership boundaries

| Component | Responsibility | Dependencies |
|---|---|---|
| skills/legacy-discovery | Legacy access procedure, CLI selector, zero-task coverage | Legacy tools/provider only |
| skills/current-discovery | Current catalog, scopes, drafts and onboarding hints | Current tools/provider only |
| runtime/legacy/provider.py | Authorized Legacy selector/HTTP GET adapter | Generic common protocols/model |
| runtime/current/provider.py | Authorized Current configuration catalog | Generic common protocols/model |
| runtime/common | Generic descriptor, provenance, matching, service and snapshots | No Legacy/Current provider |
| runtime/server.py (optional) | MCP JSON-lines protocol + namespaced tools | Only when explicitly enabled in a local host |
| runtime/cli.py | Requires explicit domain and operation | Loads chosen domain lazily |

The standard package intentionally has **no root `mcp.json`**. The Root skills can use authorized connected tools without starting a server; the read-only CLI can run through an authorized executor. The server and eight MCP tools are optional and may be enabled with the template under `optional/mcp.json` in an explicitly compatible local host. See [optional MCP integration](MCP_OPTIONAL.md). Neither access path automatically grants Codex Cloud catalog authorization.

The model types do not hardcode the supported set of Cloud generations; the target domain is bound by each provider/service instance. No Current source file imports Legacy.

## Operations

Each domain offers list/find/get/resolve:
- `list_legacy_environments` / `list_current_environments`
- `find_legacy_environments` / `find_current_environments`
- `get_legacy_environment` / `get_current_environment`
- `resolve_legacy_environment` / `resolve_current_environment`

A request covering both generations is handled by two independent calls with separate coverage and error reports. No implicit cloud_type=all parameter exists.

An EnvironmentDescriptor includes cloud_type, immutable ID, account/scope, explicit repository association, draft/publication state, execution-readiness distinct from configuration-state, source/evidence, observation time and matching confidence.

## Fail-closed behavior

- A match based solely on a display name is an unverified candidate.
- Account name supplied by the caller is not proof that the catalog was read under that account.
- A missing provider returns unavailable/partial coverage, **not zero verified environments**.
- Complete + live + unique + verified repository association is required before returning a resolved descriptor.
- Imported snapshots, onboarding task hints, stale caches and non-authoritative Codex Tasks lists cannot become live evidence.
- 401/403, pagination loops, schema mismatches and unavailable transports block resolution, never cause privilege escalation.

## Retirement boundary

When Legacy becomes obsolete:
1. Delete legacy-discovery skill and runtime/legacy module.
2. Remove Legacy-only CLI options and, **if the optional MCP adapter is used**, its Legacy tool registrations.
3. Remove tests/test_legacy.py and Legacy release documentation.
4. Keep runtime/current, tests/test_current.py and common model/service unchanged.

Current live transport will be implemented independently as soon as an officially authorized method is available.

## Validation

Offline provider behavior, tool dispatch, framing, account identity, repository matching and release structure are tested without live Cloud writes. CI runs Python 3.9, 3.12 and 3.13, including **independent Legacy and Current test suites**.

## v0.3.0 execution wiring

Both CLI and optional MCP now build a startup-configured DiscoveryRuntime. Operator-approved host commands provide primary catalog or GET transport boundaries. EscalatingProvider runs only approved stages, records outcomes and stops on denials, rate limits, identity conflicts and operation cancellation/deadlines. Snapshot and onboarding stages remain non-authoritative.

The core catalog reader preserves repository associations, versions, drafts, source scope and account continuity. Native/direct provider code remains isolated by generation. The integrated native-session adapter was blocked by a tool safety control; it is not an available default implementation.

The optional server delegates the MCP protocol to the official SDK, while retaining application-level schemas, sanitized errors, read-only annotations, bounded results and progress. No remote HTTP listener or credential broker is exposed. See ADAPTERS.md, MCP_OPTIONAL.md and PROJECT_MEMORY.md for current contracts and observed limitations.

## v0.4.0 concrete execution paths

Legacy first stage may now be native_cli: a pinned executable, isolated PTY, completed-frame renderer and native selector parser. It yields actual visible rows without private log/session access. Current first stage may be browser_web: a pinned BrowserAct CLI and an existing isolated Chrome browser issue the ordinary web catalog GET. Both preserve the existing common services, consent gates and optional MCP.

The list operation optionally enumerates the complete owned GitHub catalog and returns a separate correlation structure. It does not change Cloud identity or coverage. Desktop and web Current API destinations are explicitly distinguished, never automatically interchanged after a denial. See OPERATIONS_0.4.0.md for the current executed architecture and its real limits.
