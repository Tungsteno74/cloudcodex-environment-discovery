# Validation — v0.4.0 discovery-only implementation

Baseline: v0.3.1 commit `5dd725c69cb3c5cfe81bd88f4c14acd369b4705b`. Same implementation branch and draft source PR, no replacement project or changes to stable main. Observations were recorded on 11 October 2026 (UTC).

## Local automated profiles

| Profile | Interpreter | Passed | Skipped |
|---|---|---:|---:|
| Core, including parser/adapter contracts | Python 3.9.13 | 219 | 0 |
| Core plus official SDK stdio client/server | Python 3.12.15 | 233 | 0 |

Breakdown: common49, Legacy19, Current22, adapters39, sources29, native-selector23, catalog-join16, browser-catalog10, interface12, MCP14. Core tests do not require native UI dependencies or contact OpenAI. The optional SDK suite uses actual client/server processes with simulated catalogs and is not counted as proof of live Cloud access.

New tests cover native selector row parsing, partial rendering boundaries, no task-mutation keys, isolated cleanup, bounded traversal, unsupported client versions, real IDs versus label hints, GitHub all-page enumeration, account continuity, correlations without fabricated environments, explicit web/Desktop API surfaces, and Current browser authorization stops/owned-session cleanup.

## Real Legacy catalogue read

The standard native `codex cloud` process was started in an isolated PTY. The adapter opened the ordinary environment picker with `o` and read only its rendered screen. It did not read `error.log`, auth.json, browser profiles, token stores or process memory. Its approved keyboard actions do not include Enter, New Task or Apply.

Two existing environments were returned repeatedly:

| Label | Legacy Environment ID |
|---|---|
| codex-provisioning-test-legacy-20261010 | `6aca91fe4db881918c4ae1df05817ede` |
| Tungsteno74/cloudcodex-windows-bootstrap-e2e-cloud-auto | `6ac958a3f7108191821335628d25b4b5` |

Two consecutive production-adapter reads took 4.000 and 3.985 seconds and returned the same IDs. The first end-to-end CLI plus GitHub correlation took 6.953 seconds. The result remained `status=partial`, `catalog_complete=false`, with `provider.coverage.visible_rows_complete=true`: screen enumeration succeeded, but the native UI does not attest account-wide API coverage or draft/publication state.

An additional **real SDK MCP** call to `list_legacy_environments(correlate_github=true)` returned both IDs, `isError=false`, the same coverage and the GitHub correlation in 6.047 seconds. The session negotiated protocol `2025-11-25`; the server answered a subsequent ping and shut down normally.

The old discovery experiment had verified an environment with zero tasks. A present-day read of the historical test environment returned at least one task, so this release does not claim a newly confirmed live zero-task case. The native catalog enumeration does not depend on parsing tasks, and no new task was created for testing.

## GitHub cross-reference

Native `gh api --method GET ... --paginate --slurp` enumerated **33 owned repositories** under the already-authorized account. An attempted combination with `--jq` was rejected by the installed CLI; the implementation now uses native all-page wrapping and normalizes bounded data locally.

The observed Legacy fixture matched repository `Tungsteno74/cloudcodex-windows-bootstrap-e2e-cloud-auto`, GitHub ID `1408634524`, by name. The output correctly marked it `name_candidate`/`hint`, not a verified Codex association. The other environment had no name match. GitHub completeness was not promoted to Cloud completeness.

## Current outcomes — actual blocker, not successful catalogue

1. Existing independent BrowserAct Chrome opened the official Codex web UI and encountered a Cloudflare security interstitial before the application. No checkbox was operated and the owned session was closed.
2. A same-origin GET to `/api/codex-cloud/v1/environment-configs?scope=user&limit=100&omitDraft=true` returned **403 HTML**. No token was read, no identity changed, and no request for the next scope/drafts was used to bypass the result.
3. The production `browser_web` adapter was then exercised using the native CLI's verified JSON output contract. It returned `forbidden`, reason `http_403`, source `browseract_web_catalog`, zero rows, and one terminal stage in 11.063 seconds. Its owned browser session was closed. No follow-up scope was attempted.

The web-prefixed route and the Desktop host route are separate client surfaces. Upstream issue #50182 reports the web path; matching the Desktop path alone did not justify the earlier blanket rejection of that web route. This correction does not prove a successful Current catalog response.

Current authentication and draft enumeration remain unverified beyond the blocker. A future authorized successful response may require additional legitimate application authorization; 403 does not establish that cookies alone will suffice.

## Persistence, cleanup and limits

A non-secret, machine-local configuration was saved under `%LOCALAPPDATA%\CloudCodeX\environment-discovery\discovery-readonly.local.json`, containing reviewed paths, executable hashes, existing browser ID and scoped read approval. It is not committed or packaged. No global default or credentials were changed.

All owned test terminals/browser sessions were closed. No environment/task creation, publication, POST provisioning, Credential Broker, primary-desktop input, or Bootstrap gate execution was introduced. MCP remains optional; root mcp.json is absent.

CI must be checked against the exact resulting commit. These are local measured results, not a prediction of a later CI outcome.

Final review added a reproducible stalled-version regression: a native CLI version timeout now becomes the same structured operation-timeout outcome used by CLI/MCP, rather than an uncaught subprocess exception. The failure was reproduced before the fix.

## Final reconciliation and regression closure

The interrupted work was reconciled against actual local source before further changes. A reproducible failure remained when the native picker opened with its last environment already selected: End did not change selection, so the reader could misreport a layout failure. It now anchors the picker at Home first when needed, with separate regressions for initially-last and initially-scrolled catalogs. No Enter, creation or apply action was introduced.

Three additional browser ownership tests enforce that a reused, unidentified or different-browser session is neither queried nor closed. This strengthens the existing no-interference requirement. No new Current network request was made after the previously recorded 403.

Final local profiles: **224 core tests on Python 3.9.13; 238 core+SDK tests on Python 3.12.15; zero skips**. Breakdown: common49, Legacy19, Current22, adapters39, sources29, native25, catalog-join16, browser-catalog13, interface12, MCP14.

A fresh CLI+GitHub check at 2026-10-11T22:24:57+00:00 returned the same two Legacy IDs and 33 owned repositories in 5.548 seconds. A fresh actual SDK call at 2026-10-11T22:27:15+00:00 returned the same IDs, `isError=false`, protocol `2025-11-25`, and answered a follow-up ping before closing normally (6.047 seconds). Both retain `catalog_complete=false` with `visible_rows_complete=true`; neither claims unpublished-draft or account-wide API coverage.
