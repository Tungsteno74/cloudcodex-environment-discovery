# Current Cloud execution contract — v0.4.1

This skill reads existing current-generation configurations. It does not create environments/tasks, publish drafts, broker credentials or invoke Legacy implicitly.

## Distinct catalog surfaces

Desktop host: `https://codex-cloud-backend.chatgpt.com/v1/environment-configs`.

Web proxy: `https://chatgpt.com/api/codex-cloud/v1/environment-configs`.

These are observed internal client routes. The web route is also reported by upstream Codex issue50182; neither is a guaranteed public API. The earlier rejection of the web prefix was over-broad when based only on the Desktop implementation. Configuration selects the surface explicitly; denial must not cause automatic surface/account switching.

## Dedicated browser_web adapter

An optional first stage can be `browser_web`, approved explicitly, with `browser` fields:

- Absolute native browser-act/browser-act.exe executable and SHA-256 pin.
- Existing `chrome_local_<id>` browser identifier.
- Bounded timeout, default15seconds.

Only an existing isolated `chrome` browser is accepted. `chrome-direct`, creating/importing profiles, proxy changes, cookie/token reading, auto-dialog acceptance and CAPTCHA solving are excluded. The adapter creates its own unique session, issues only the fixed web GET using the browser's normal existing session, and closes that session. It never controls the primary desktop.

The CLI JSON mode and adapter path were tested. Actual Current catalog GETs returned 403 HTML, so no successful Current list or unpublished draft retrieval is claimed. A 403 does not establish that existing browser cookies alone would authorize the API after the interstitial is cleared.

## Approved HTTP host alternative

`primary` is an alternative first-stage approved catalog host. A later `http` host can read the configured Desktop/web API only if already authorized and no prior terminal denial occurred. It receives fixed GET destinations/query parameters, not arbitrary URLs or credentials. Current relays include the observed product-SKU header without fabricating account authorization.

Installed Desktop catalog refresh calls its Current list for both scopes with `limit=100&omitDraft=true&view=picker`. If and only if that picker-shaped request returns HTTP 400, the client retries the standard list and reduces it to configuration IDs, names and repository IDs. The plugin mirrors this **Desktop-only retry condition** but intentionally preserves all standard-list records and revisions: a GUI selection filter cannot establish environment absence. A successful picker-only result remains `catalog_complete=false` (partial coverage), even if its pages were exhausted. The Web proxy retains its separate standard GET; authorization failures are terminal and never trigger another Current request.

Scope user/workspace, pagination, cursor loops, duplicate versions and `omitDraft` must be handled explicitly. `omitDraft=true` excludes drafts rather than proving none exist. `omitDraft=false` is implemented but not yet validated by a successful live response containing an unpublished draft.

## Auxiliary evidence and correlation

If reached before any terminal denial, an onboarding host or supplied Codex Tasks export may supply explicit Configuration IDs as indirect candidates. Missing IDs remain `provider.hints`; task IDs, titles and prose are not configuration identities. Snapshots remain imported/incomplete. Never use these paths to bypass 401/403 or a security control.

Optional GitHub discovery is an independent read source. A Cloud 401/403/rate-limit still terminates the Cloud provider path, but does not suppress an explicitly requested, already-authorized GitHub inventory. IDs/explicit associations outrank name hints; no missing Cloud environments are fabricated. Cloud/GitHub completeness is kept separate.

Installed Desktop 26.1007.2314.0 exposes two compatible repository-bearing read shapes: catalog/cache rows with `repository_ids[]` and detailed configuration rows with `repositories[].repository_id`; the latter is normalized client-side as `repositoryId`. The settings flow reads `environmentConfigs.catalog()`, invokes `refreshCatalog()`, and reads the catalog again. A detailed GET by known `configId` returns the explicit repository associations. The plugin normalizes these snake_case/camelCase repository-ID and version fields but does not read Desktop private cache/authentication state.

For repository-centric lookup, `find_current_environments(repository)` reports `repository_counterpart`: `verified` when a fresh live Current configuration carries the same GitHub repository ID or explicit canonical repository; `candidate` for name equality or stale/imported associations; `not_found` only after a complete Cloud catalog proves absence; and `not_verifiable` when the Cloud catalog is denied/partial. No dedicated Current by-repository GET/filter was validated, so none is invented.

## Outputs and read-only controls

Return IDs, observed account/scope, publication state distinct from readiness, provenance/time, coverage and stage attempts. Resolve only a unique, fresh, live verified identity with required complete coverage. Preserve candidates or the exact blocker otherwise.

AUTO cannot grant permissions. CONFIRM requires preapproval. Authentication/authorization denial, rate limits, integrity/account mismatch, cancellation and timeout stop the sequence. Optional MCP exposes the same list/find/get/resolve methods as CLI, and list optionally accepts correlate_github. MCP is not an authentication mechanism or a required entry point.


## Optional Webcmd Current escalation (v0.4.1)

An additional operator-approved stage named webcmd invokes pinned Node.js plus
@agentrhq/webcmd CLI on an already prepared isolated CloakBrowser and profile.
It performs a normal JavaScript-capable navigation to the *original* Current
backend (codex-cloud-backend.chatgpt.com/v1/environment-configs), using the
existing standard-list scope/limit/cursor/omitDraft contract. It does not use
the Desktop UI-only picker view, the BrowserAct Web proxy, or Codex CLI
credentials. Missing browser binaries/profiles fail unavailable; it neither
installs dependencies nor initializes/imports profiles.

The stage is after an optional primary and before browser_web/http/onboarding/
snapshot. Missing/partial sources may escalate; 401/403 and security/identity
denials remain terminal. Session names and profile identity are verified by
before/after Webcmd inventory; only a newly owned session can be closed.
Cleanup must be reconciled and incomplete cleanup downgrades completeness.

Real reference-machine probe (Webcmd 0.8.4, CloakBrowser 0.4.5) returned a
single-stage 401 JSON unauthorized; user/workspace enumeration did not proceed
after the first denial. Zero Current environments were confirmed, cleanup
succeeded and no adapter sessions remained. See docs/WEBCMD_CURRENT_ESCALATION.md.


## Single Configuration ID without a catalog — operational limitation

The installed Current Desktop client supports GET
`/v1/environment-configs/{configId}`; a known immutable ID is enough to
construct this one read, not to authorize it. The Current-only
`get_current_environment(environment_id)` contract now tries the single-ID
GET via approved Desktop HTTP or Webcmd transports, before a catalog-only
source could enumerate the entire account. No unverified Web proxy point
endpoint, by-repository or by-name URL is invented. A valid HTTP 200 with
matching ID and sufficient account provenance sets `point_verified=true`,
while `catalog_complete=false`. HTTP 401/403/429 stop the configured Cloud
stage chain. On missing live access, return a denial/not-verifiable result,
never `not_found` solely because a request was unauthorized.

As of 12 October 2026, live Current point and catalog reads are still blocked
(401 JSON with Webcmd; anonymous HTTP receives a 403 HTML Cloudflare
challenge). **The Current skill is usable but its expected live IDs remain
pending supported authorized access.** This is not an OpenAI commitment to
a fix date. Draft reads for unknown IDs and new environments are not attempted.

## Optional Root-facing software-validation advisory (v0.4.2)

Only for explicit software-validation intent, after bounded trusted observation
cannot resolve a viable, verified Cloud executor, the skill may return the
structured advisory `recommended_fallback: cloudrepo-environment-direct`. Its
`fallback_evidence` carries `source`, `repository`, `full_sha`, `check_plan` and
`decision_evidence` only when observed; every other value is `unknown`.
Default `fallback_eligibility` is `candidate_requires_root_preflight`; no
discovery outcome authorizes direct CI. Root alone reconciles Cloud task/CI
references and chooses/authorizes the independent
`cloudrepo-environment-direct:cloudrepo-environment-direct` skill.

Partial, empty or stale catalogs do not prove absence. Pending/active tasks or
CI, test failure, inconclusive remote side effects, denial (401/403), and slow
wall-clock alone do not establish eligibility or failed startup. A denial still
stops Cloud escalation and is never bypassed through another identity/provider.
The advisory never creates tasks, refs, PRs, workflows or environments, nor
changes permissions.
