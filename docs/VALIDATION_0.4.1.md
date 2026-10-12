# Validation report — v0.4.1 local candidate

## Source and scope

- Source repository: `Tungsteno74/cloudcodex-environment-discovery`.
- Local branch: `feature/current-repository-discovery-v041`, based on official `main` commit `28d524c8a1d204896e802c11c899645392096e6f`.
- Scope: read-only Cloud environment discovery. Provisioning, task creation, environment changes, authentication changes, profile access and challenge bypass remain excluded.
- The working tree also contains an independent **unapproved icon/branding candidate**. It is preserved but this preview has **not** been released or installed in the existing local/Cloud installations.

## Code changes verified

1. Independent GitHub correlation no longer stops merely because Current Cloud returned 401, 403 or rate limiting. The Cloud result remains terminal for that Cloud provider and its completeness remains false.
2. `find_current_environments(repository)` reports `repository_counterpart` with explicit repository ID/canonical-name evidence prioritized over name hints. No missing Configuration IDs are generated.
3. Current parser handles installed Desktop's catalog/cache `repository_ids[]`, detailed `repositories[].repository_id` and normalized `repositoryId`, plus observed version ID/revision variants.
4. Desktop published-config retrieval follows `view=picker`. A standard-list retry occurs **only after HTTP 400**, on the same surface and identity. Explicit draft inclusion and the separate Web route use standard-list GET. HTTP 401/403/429 never trigger another Current Cloud query.
5. A fully paginated picker view is explicitly **partial evidence** and cannot prove environment absence. The standard-list fallback preserves all rows and revisions instead of applying the GUI's saved-config filter.
6. BrowserAct session ownership is proved by a fresh unique name absent from `session list` before opening and present afterward on the configured isolated Chrome browser. The `open` response can use browser alias `workbench` or report persistent-browser reuse; neither grants ownership. Interrupted opens are reconciled before closing only an owned session.

## Actual authorized reads (not test fixtures)

A controlled BrowserAct open on the existing isolated browser returned a fresh named session with `browser_id="workbench"` in the open reply; the normal `session list` simultaneously associated it with the approved `chrome_local_...` browser. The disposable session was closed by its exact name.

A later v0.4.1 `current find` for `Tungsteno74/cloudcodex-windows-bootstrap-e2e-cloud-auto`:

- verified GitHub repository ID `1408634524` through the already-authorized GitHub account;
- reached the actual Current Web GET, which returned **HTTP 403** (`provider.reason=http_403`);
- returned `catalog_complete=false`, `repository_counterpart.status=not_verifiable`, no confirmed Current Configuration IDs, and name candidates only;
- reported `session_cleanup_confirmed=true` and a subsequent BrowserAct `session list` showed **zero** `cloudcodex-catalog-*` sessions remaining.

There was **no** replay on another Current URL/account or retry after that denial. The installed Desktop's main-process code was inspected statically to verify `view=picker` and cache contracts; it was not used as an unauthorized live-session source.

## Automated validation — historical pre-Webcmd baseline

Before adding the optional Webcmd stage: **259 core** and **274 core+MCP**
tests passed, with Ruff and diff checks passing. The historical archive then
contained 43 entries; that artifact has since been superseded by the build
including Webcmd.

Current v0.4.1 preview verification is recorded in the Webcmd acceptance
section below. Latest local package (not published):

```text
dist/cloudcodex-environment-discovery-0.4.1.zip
SHA256 87661d81aae3d5e3416386e306959c3bc0bd320bdd802e1b368c1b291feb8fc6
Size 1048554 bytes
ZIP entries 45; two domain skills; optional MCP only
```

## Remaining limitations

- A successful, presently authorized Current live catalog and real unpublished-draft coverage are **not verified**.
- GitHub names alone never establish an actual Current Cloud environment. Exact Configuration IDs are confirmed only when provided by a fresh authorized Codex source.
- No release, PR merge/push, Cloud plugin update or office workstation deployment has been performed for v0.4.1; the official v0.4.0 remains installed.
- The local feature branch still contains uncommitted work, including separate unapproved artwork; do not automatically promote its entire contents.


## Webcmd Current escalation — acceptance (12 October 2026)

Added optional, operator-approved Webcmd stage, placed after an optional
primary and before BrowserAct, approved HTTP, onboarding and snapshot.
Requires preexisting isolated Webcmd profile and browser runtime plus SHA-256
pins for Node and @agentrhq/webcmd entrypoint. No credentials, browser
profiles or Cloud environments are created/modified by the adapter.
An unauthorized 401/403 remains terminal.

Live read-only CLI probe on HOME (Webcmd 0.8.4, CloakBrowser 0.4.5):
- Current backend: original codex-cloud-backend.chatgpt.com/v1/environment-configs.
- Response: HTTP 401 application/json; status=unauthorized,
  reason=http_401, source=webcmd_current_catalog.
- Environments returned: zero; catalog_complete=false.
- Attempt sequence: only webcmd. No fallback to BrowserAct after 401.
- Temporary session cleanup: confirmed; zero leftover sessions.
- Temporary operator configuration removed; no Cloud resource mutations.
- This does **not** demonstrate authorized Current catalog listing.

Initial live probe returned unavailable due to Webcmd profile default not
currently initialized. Operator-run webcmd doctor showed/connected an
existing default profile, after which the adapter completed the 401 probe.
The adapter itself does not run doctor or bootstrap a profile.

Final offline validation after including the new suite in tools/validate.py:
- Core: 275 tests, 0 skipped, all passed.
- Core + optional MCP SDK: 290 tests, 0 skipped, all passed.
- New Webcmd suite: 16 tests, covering stage order, escalation on
  recoverable failure, terminal 401/403, fixed destination, sandboxed
  invocation, SHA-256 pins, profile prerequisites, session ownership and
  cleanup, and malformed or unavailable sources.
- Ruff select F and git diff --check: clean.
- Deterministic release-preview ZIP built with runtime/current/webcmd.py,
  current-discovery/references/webcmd-current.md and optional/mcp.json;
  no mandatory root MCP manifest. Not published.


## Current exact Configuration-ID GET: final local acceptance (12 October 2026)

Implemented independently of Current catalog pagination:
`GET /v1/environment-configs/{configId}` on explicitly approved Desktop
HTTP relay and Webcmd 0.8.4. Known immutable IDs are validated before access;
200 JSON requires exact response-ID match and verified requested-account
provenance, and returns `point_verified=true` without catalog completeness.
Catalog-only configured sources retain their read behavior. 401/403/429
are terminal for the Current Cloud path; no profile switching or challenge
handling is performed. The Web proxy's unobserved point route is not invented.

**Operational state: available but live Current API results on hold.**
Historical read-only point diagnostics (before this implementation) returned
**401 JSON** via Webcmd and **403 Cloudflare HTML** on anonymous HTTP.
This release was validated offline and is NOT evidence of an authorized
Current Configuration ID. Await supported API access; no OpenAI fix ETA
is asserted. Legacy is unaffected.

Final local checks:
- Core: **298 tests passed**, zero skipped.
- Core + official SDK MCP: **313 tests passed**, zero skipped.
- New `test_current_detail.py`: 18 tests (path, ID, account,
  content-type, API 401/403/404/429, single-ID coverage, escalation).
- Webcmd suite: 20 tests, including direct GET/cleanup and terminal 401.
- Ruff F on changed Python code: passed.
- Release preview ZIP: 46 entries, exactly two skills, optional MCP
  manifest only, no credential files or root MCP manifest. SHA-256:
  `95db40007ea71daf6be031d0bc37c398507afe7e1a6ebddb8d2214054fe0b672`.
- Preview package: `dist/cloudcodex-environment-discovery-0.4.1.zip`,
  1054468 bytes, **not published**.
- Full code/documented acceptance: `docs/CURRENT_POINT_LOOKUP_0.4.1.md`.
