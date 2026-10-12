# Current Cloud execution contract — v0.4.0

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

Scope user/workspace, pagination, cursor loops, duplicate versions and `omitDraft` must be handled explicitly. `omitDraft=true` excludes drafts rather than proving none exist. `omitDraft=false` is implemented but not yet validated by a successful live response containing an unpublished draft.

## Auxiliary evidence and correlation

If reached before any terminal denial, an onboarding host or supplied Codex Tasks export may supply explicit Configuration IDs as indirect candidates. Missing IDs remain `provider.hints`; task IDs, titles and prose are not configuration identities. Snapshots remain imported/incomplete. Never use these paths to bypass 401/403 or a security control.

Optional GitHub inventory correlation uses complete native owned-repository pagination. IDs/explicit associations outrank name hints; no missing Cloud environments are fabricated. Cloud/GitHub completeness is kept separate.

## Outputs and read-only controls

Return IDs, observed account/scope, publication state distinct from readiness, provenance/time, coverage and stage attempts. Resolve only a unique, fresh, live verified identity with required complete coverage. Preserve candidates or the exact blocker otherwise.

AUTO cannot grant permissions. CONFIRM requires preapproval. Authentication/authorization denial, rate limits, integrity/account mismatch, cancellation and timeout stop the sequence. Optional MCP exposes the same list/find/get/resolve methods as CLI, and list optionally accepts correlate_github. MCP is not an authentication mechanism or a required entry point.
