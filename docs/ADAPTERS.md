# Adapter contracts and escalation — v0.3.0

## What is actually implemented

The CLI and optional MCP server now instantiate configured adapters, rather than requiring a Python caller to inject callbacks manually. Both share `DiscoveryRuntime` and the same domain-specific service contracts.

A **host command** is an operator-provided program that already has legitimate access to the selected source and implements the JSON protocol below. **No official Codex CLI subcommand was found that directly implements this protocol.** Do not configure an interactive `codex cloud` invocation as if it were a JSON catalog host. A configured command is not itself evidence of authentication.

The attempted integrated native-session adapter was blocked by a tool security control and is **not shipped**. Current Cloud's authorized host is likewise not available in the tested setup. This limitation is separate from the executable adapters and simulated integration tests.

## Operator configuration

The configuration is loaded once at process startup from `--config` or `CLOUDCODEX_DISCOVERY_CONFIG`; no MCP tool accepts a configuration path, arbitrary URL, command or token. Store operator-specific configuration outside version control.

Root fields: `schema_version: 1`, `mode: AUTO|CONFIRM`, `timeout` (0.1–180 seconds), `domains` with independent `legacy` and `current` settings.

Each domain has an ordered `stages` array. Permitted order:

| Order | Kind | Legacy | Current |
|---|---|---|---|
| 1 | `primary` | Native authorized catalog host | Official/current authorized catalog host |
| 2 | `http` | Authorized Legacy GET relay | Authorized current GET relay |
| 3 | `onboarding` | Not applicable | Indirect onboarding/configuration hints only |
| 4 | `snapshot` | Imported sanitized catalog | Imported sanitized catalog |

A stage requires explicit `approved: true` to run. `AUTO` skips an unapproved stage; it does not approve it. `CONFIRM` returns `approval_required`, allowing the Root to resolve consent outside the read operation. A denial from a source is not a request to widen permissions.

Command-stage fields:

- `kind`, `approved`.
- `command.argv`: absolute executable, optional absolute script and fixed arguments. No shell, inline code or credential arguments.
- `command.sha256`: mapping from the executable and any script paths to their exact SHA-256 digests. Hashes verify specified-file integrity; they **do not certify that a host program is safe**. Review and approve the complete host implementation and its dependencies separately.
- `command.cwd`: explicit absolute working directory.
- `command.timeout`: bounded request timeout (0.1–120 seconds).

Snapshot stages use `path` instead of `command`; the file must be a sanitized catalog, not a credentials file. Importing a snapshot never supplies live evidence.

Current domain settings also accept `scopes` (`user`, `workspace`), `page_limit` and `page_size`. Legacy accepts only user scope. Configuration rejects unknown/duplicate keys and unexpected ordering. Start from the safe empty `optional/discovery.example.json`.

## Host wire protocol

One UTF-8 JSON request is written to stdin, followed by a newline and EOF. The host writes **one JSON object** to stdout and exits. The library enforces deadlines, cancellation, integrity pins, output bounds, JSON validity and source identity; raw host diagnostics are not exposed. Ambient secret environment variables are not forwarded.

### Primary catalog request

```json
{"schema_version":1,"operation":"catalog_read","cloud_type":"current","account":null,"include_drafts":false,"scopes":["user","workspace"]}
```

Successful response must include `schema_version`, matching `cloud_type`, a fresh timezone-aware `observed_at`, status `ok|empty|partial`, `catalog`, `catalog_complete`, echoed `include_drafts`, echoed `scopes`, and source `scope`. `account_verified: true` requires an actual observed account identifier, not the caller's desired identity.

`catalog` is a recognized environment array/envelope. Rows must carry immutable environment/configuration IDs. Repository associations must be explicit; a display name is not an association. If the host returns a cursor rather than a complete catalog, completeness remains false.

### Authorized HTTP relay

```json
{"schema_version":1,"operation":"http_get","method":"GET","cloud_type":"current","url":"https://codex-cloud-backend.chatgpt.com/v1/environment-configs","query":{"scope":"user","limit":"100","omitDraft":"true"}}
```

The response includes matching schema/domain identity, integer HTTP `status`, actual `content_type`, fresh `observed_at`, account provenance and decoded JSON `body` for HTTP 200. Error bodies are not retained. HTML challenges cannot count as a successful JSON catalog. **401/403 remains terminal even if the error response lacks a timestamp**.

The runtime permits only the observed catalog destinations:

- Legacy global: `GET https://chatgpt.com/backend-api/wham/environments`.
- Legacy association lookup: `GET .../wham/environments/by-repo/github/{owner}/{repo}` with validated GitHub owner/repo components.
- Current: `GET https://codex-cloud-backend.chatgpt.com/v1/environment-configs` with explicit scope, pagination and draft parameters.

These are observed internal client routes, not a stable public API guarantee. The relay does not acquire, export or refresh credentials.

### Onboarding hints

Uses `operation: onboarding_read`, with the same catalog response shape. A host may normalize explicit configuration IDs and repository evidence from authorized onboarding reads. **Task IDs and titles must not be transformed into environment IDs.** The adapter always labels results `indirect` and incomplete, irrespective of the host's claimed completeness.

## Evidence and stopping rules

- A complete, live success—including a genuinely empty catalog—ends escalation.
- Missing capability, partial reads and stale evidence may proceed to the next already-approved stage.
- HTTP 401/403, rate limiting, identity/integrity mismatch, cancellation or deadline expiry stop execution. No change of account, no new token search, no challenge bypass.
- Account identity observed in a primary source must not silently change or disappear at a later stage.
- Versions/drafts with the same ID remain distinct. Conflicting immutable records fail closed.
- Pagination is bounded, cursor loops are rejected, and malformed pages are not partially committed.
- Resolve returns one environment only with unique, fresh, verified evidence and complete requested coverage. Otherwise it returns candidates and stage diagnostics.

## Testing versus live acceptance

`tests/fixtures/catalog_host.py` is a **simulated host**. Tests run it as a real process and exercise the complete command → provider → service → MCP/CLI route. This validates integration behavior, not OpenAI authorization.

Live acceptance still requires a permitted native/official catalog host for the actual account, followed by read-only verification of IDs, repository associations, user/workspace scope and draft coverage. No test is allowed to create a Cloud environment or task to manufacture discovery evidence.

## Research basis

Original note: `Codex_Cloud_Environment_Discovery_Nota_Architetturale_plugin.md`, 10 October 2026. Official client source inspected at OpenAI Codex commit `4aa94dce270de668eff6e2fa8585c82385e84455`, especially `codex-rs/cloud-tasks/src/env_detect.rs`, `util.rs` and `ui.rs`. Historical GET 200 evidence does not establish current operational access from this plugin.

## v0.3.1 concrete optional sources

The optional github startup section enables a reviewed, pinned native gh repository reader; it is not a Cloud catalog host. The same find/resolve functions carry repository_evidence separately from provider completeness. An enabled helper uses its own observed GitHub identity, never an inferred mapping from the ChatGPT account.

Current onboarding can also use an approved path containing an explicit Codex Tasks connector export. This route does not require a custom host implementation, but evidence remains indirect; tasks without Configuration IDs are returned under provider.hints and are not environment records. Complete/denied-stage decisions are unchanged. See CONTINUATION_0.3.1.md for the schema and tested live observations.
