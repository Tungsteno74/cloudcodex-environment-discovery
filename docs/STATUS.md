# Implementation status — v0.4.0 preview

| Capability | Implemented | Actual validation |
|---|---|---|
| Independent Legacy/Current skills | Yes | No mandatory Root dispatcher |
| Legacy native screen-only reader | Yes | Two actual existing IDs, repeatable through CLI and optional MCP |
| Legacy account-wide completeness/publication state | Not attested by UI | Returned as unknown/incomplete, not guessed |
| Full owned GitHub inventory and correlation | Yes | 33 repositories read; name match preserved as a hint |
| Current BrowserAct web GET adapter | Yes | Actual 403 HTML; terminal failure, session closed |
| Current Desktop approved GET host | Yes | No connected direct host validated |
| Current successful catalog and unpublished drafts | Not verified live | Still blocked; no bypass or creation attempted |
| Optional MCP SDK server | Yes | Existing eight tools; optional list correlation argument |
| Provisioning/Credential Broker | Excluded | No implementation or live writes in discovery |

The major change from v0.3.1 is that Legacy is no longer a callback-only integration: it actually returns a live observed list on the reference machine. Current still does not return a usable live list, despite having a concrete tested browser transport. Neither result changes authorization automatically.

The screen reader uses ordinary TUI input/output and never reads the private logs/session stores targeted by the older refused attempt. That historic refusal is preserved in Project Memory, not rerouted.

Code and machine-local read configuration are ready for the existing source branch. The local config is outside the repository; default distributed settings are disabled. MCP remains optional and skills are not automatically installed into ChatGPT Chat by a GitHub release.

See OPERATIONS_0.4.0.md and VALIDATION_0.4.0.md for exact commands, evidence, cleanup and limits. Stable main and the marketplace PR remain separate from this preview until promotion is explicitly appropriate.

## v0.4.1 repository-aware Current behavior

A Current catalog denial no longer prevents a separately authorized GitHub inventory. The Cloud result remains denied/incomplete; GitHub success cannot change it to a Cloud success. `find_current_environments` reports whether the requested repository has a verified observed counterpart (explicit repository ID/name), only a name candidate, verified absence from a complete Cloud catalog, or an unverifiable state.

Installed Desktop 26.1007.2314.0 inspection confirmed Current catalog/cache `repository_ids[]`, detailed `repositories[].repository_id` and client-normalized `repositoryId` forms. The parser preserves these explicit IDs instead of degrading them to name hints.

A live v0.4.1 repository lookup verified GitHub repository ID `1408634524` for `Tungsteno74/cloudcodex-windows-bootstrap-e2e-cloud-auto`. Current remained `forbidden` because BrowserAct did not prove ownership of a fresh session, so no catalog GET or close was performed. The result correctly remained `repository_counterpart.status=not_verifiable` and returned only the candidate names `cloudcodex-windows-bootstrap-e2e-cloud-auto` and the canonical `owner/repo`.


### v0.4.1 BrowserAct follow-up

A direct browser-open test showed a valid new BrowserAct session can carry `browser_id=workbench` in the open result even though the authoritative `session list` reports the configured isolated Chrome ID. Ownership is now verified by comparing `session list` before and after opening a unique name; only such a session is eligible for the GET and close.

The next live Current attempt reached the authorized Web GET and returned **HTTP 403**, replacing the earlier preflight-only `unexpected_browser_session` outcome. GitHub still verified repository ID `1408634524`; the Cloud counterpart remained `not_verifiable`. Session cleanup was confirmed and no `cloudcodex-catalog-*` sessions remained.

Desktop `view=picker` and 400-only standard-list fallback are implemented separately from the Web proxy. Neither method has yet returned a successful Current catalog on the reference machine.


### v0.4.1 picker coverage semantics

A successful Desktop `view=picker` response no longer implies complete Current Cloud coverage: the saved-configuration selector can omit configurations. It is reported as partial even when picker pages are exhausted. A same-surface standard list obtained after HTTP 400 keeps **all revisions**; the plugin does not apply the GUI's revision filter because it could conceal existing environments. Published-only and include-drafts coverage remain distinct.


### v0.4.1 Current Webcmd escalation

The optional Webcmd Current stage has been added before BrowserAct, after an
optional approved primary. It accesses the original Current backend via
already installed Webcmd 0.8.4 and an existing isolated CloakBrowser profile.
There is no automatic browser/profile installation, login, challenge solving
or account switching. 401/403 still ends Cloud escalation.

One actual run using the v0.4.1 CLI and a temporary approved Webcmd-only
configuration returned 401 JSON (provider.reason=http_401), zero environments,
catalog_complete=false, and session_cleanup_confirmed=true. The temporary
operator config was removed and zero Webcmd adapter sessions remained. This
is working read-only transport, **not** successful Current discovery.


### Current point-by-Configuration-ID path: implemented, live access on hold

Current `get_current_environment(ID)` now invokes the client-observed
`GET /v1/environment-configs/{configId}` via an already-approved Webcmd or
Desktop HTTP transport instead of requiring full catalog enumeration first.
A valid exact 200 JSON can verify one ID (`point_verified`), without
establishing `catalog_complete`. Catalog-only stages remain compatible.
Unsafe IDs and mismatched JSON/account fail closed. A 401/403 prevents
additional Cloud stages. No new Current environment has been verified live:
12 Oct 2026 single-ID Webcmd GET returned 401 JSON; anonymous GET returned
403 HTML. **Current skill remains usable, but live API-dependent results are
pending authorized OpenAI Current access**, with no confirmed fix schedule.
Legacy and independent GitHub repository identification remain available.
