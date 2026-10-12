# v0.4.1 — Current point GET and live-access holding status

## Result

The Current skill remains **available** through its independent CLI/skill and
optional MCP contracts. Live Current configuration discovery is **on hold
pending a supported authorized OpenAI Current Cloud API path**. This is a
status of the local integration, NOT an official announcement of a scheduled
OpenAI fix. Legacy continues to work independently.

The repository source, installed Desktop code and earlier read-only probes
confirm a single-item endpoint distinct from the full catalog:

    GET https://codex-cloud-backend.chatgpt.com/v1/environment-configs/{configId}

The optional draft-specific variant exists in the Desktop code, but no draft
ID is verified and no draft detail route is implemented or probed.

## Operation routing

- Current `list`, `find`, `resolve`: catalog-driven, unchanged.
- Current `get --environment-id <known-configId>`: try single-ID GET on a
  configured, approved Current Desktop HTTP or Webcmd stage, not an
  exhaustive catalog request. If the provider is catalog-only, use its
  existing read-only catalog and filter the exact ID.
- Legacy `list/find/get/resolve`: unchanged.

Stages remain ordered and operator-approved: primary → Webcmd → BrowserAct →
HTTP relay → onboarding → snapshot. For a known ID, stages capable of a
single GET use that rather than listing first. Only a missing or recoverable
source can continue to another already-approved source. **401/403, rate
limits, identity/approval failures, cancellation and timeouts stop Cloud
escalation.** No profile, account or API surface switching is authorized by
a denial. The BrowserAct Web-proxy point endpoint was not observed in the
installed client and is not fabricated.

## Exact single-item contract

- Configuration ID must be one safe opaque path segment; no slash, query,
  percent escapes, URL fragments, arbitrary URL, name or guessed draft ID.
- Fixed `GET`, exact Desktop host, no extra query parameters.
- Only HTTP 200 with JSON MIME and exactly matching response ID can establish
  an observed configuration. Unrecognized or ambiguous JSON records fail
  closed. An explicitly requested account must be verified by the transport.
- Such a result is `point_verified=true` and may produce `status=found`,
  **while `catalog_complete=false`**: it proves only one ID, not all
  scopes, versions or other environments.
- HTTP 401/403/429 remain explicit denials. HTTP 404 does not prove
  account-wide or repository-wide absence. Historic Configuration IDs and
  onboarding messages remain candidates, not current confirmations.
- Webcmd uses the existing isolated browser, profile and single-session
  ownership/cleanup checks. The relay reuses existing SHA-256-pinned commands.
  No tokens, cookies, profile imports, challenge handling or provisioning.

## Runtime evidence and tests

The previous live diagnostics on 12 October 2026 (before this code change)
returned **401 JSON** for the single-ID Webcmd GET and **403 HTML** with
Cloudflare challenge from anonymous HTTP. Neither returned a record.
The implementation has **not** been proved able to read Current live data;
the waiting status is intentional and visible in skill/tool descriptions.

New offline regression cases cover known-ID request shape, direct GET without
catalog, 200 exact ID vs mismatched/ambiguous data, account provenance,
non-JSON content, 401/403/404/429, unsafe path rejection, Desktop-only relay
allowlist, verified single-item completeness, terminal escalation, recoverable
escalation, and Webcmd owned-session cleanup. No external Cloud resources
were created or modified. The validation report records the exact test count
and ZIP build for the local preview.

CLI:

    python <plugin-root>/runtime/cli.py current doctor --config <operator-config>
    python <plugin-root>/runtime/cli.py current get --environment-id <known-configId> --config <operator-config>

`doctor` checks configuration only. Unknown Current Config IDs cannot be
discovered by this point route alone; list/find/resolve still need an
authorized catalog or only return non-authoritative evidence.

## Release boundary

This is work on the uncommitted local v0.4.1 feature branch only. It is not
merged, pushed, published, installed over v0.4.0, or a change to the
independent Windows Bootstrap project.
