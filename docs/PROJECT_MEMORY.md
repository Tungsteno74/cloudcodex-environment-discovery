# Project memory — implementation continuity

## Confirmed user decisions

- Canonical plugin/repository: **cloudcodex-environment-discovery**.
- Two directly invocable, independent skills: **legacy-discovery** and **current-discovery**. No mandatory Root dispatcher and no implicit mixed catalog.
- Keep providers and their tests isolated so Legacy can be retired without modifying Current's implementation.
- MCP is **optional**, never a prerequisite for skill/CLI use; no root mcp.json in source or release package.
- The Root must discover existing environments before creating any task. Runtime discovery is read-only and must not create environments, task probes or GitHub writes.
- Provisioning and the speculative Credential Broker are separate research tracks. CloudCodeX Windows Bootstrap 0.6.6 and its three E2E gates are unchanged by this project.
- Initial source authoring uses the user's local repository collection, with a dedicated GitHub repository and separate GSM marketplace reference.
- v0.4.2: user approved only an optional Root-facing structured recommendation
  to the independently published `cloudrepo-environment-direct` skill for
  explicit software validation after bounded trusted observation fails to
  resolve a viable, verified Cloud executor. Root independently preflights,
  reconciles provider references and authorizes any direct CI; Discovery does
  not import it, execute CI, create tasks/refs/PRs/workflows/environments or
  change permissions.

## Historical source evidence, not current live state

The original 10 October 2026 note recorded successful Legacy catalog discovery with zero tasks, one Current configuration-catalog GET 200 and a later 403. Current draft coverage was not tested because the successful query used omitDraft=true. Codex Tasks.list_environments was not the same inventory as hosted Cloud configurations.

Those historical outcomes do not validate the new adapters against today's account/session. Cached environment/configuration IDs must be revalidated, not shipped as default results.

## Observed in the v0.3.0 implementation session

- Baseline v0.2.1 had independent skills and an optional handwritten MCP server, but default CLI/MCP factories created providers without executable configured channels.
- Implemented startup-only operator configuration, integrity-pinned read-only host commands, ordered escalation, per-stage diagnostics and explicit AUTO/CONFIRM handling without permission expansion.
- Implemented authorized-host HTTP catalog reads including Legacy by-repository association and Current user/workspace pagination, draft/version preservation and account continuity.
- Replaced the handwritten MCP protocol with the official MCP Python SDK. The optional stdio profile is tested with a real SDK client/server, including schema validation, progress, cancellation, deadline handling and all eight tools.
- Core CLI/providers remain Python 3.9+ and do not import MCP. The optional server requires Python 3.10+ and uses mcp==1.30.0.
- Host-process and SDK integration tests use **simulated catalog data**. They are not proof of real OpenAI catalog access.

## Verified blockage — do not reinterpret as an authentication result

A write request implementing direct native-session automation was denied by an OpenAI tool safety control. The proposed native adapter file was confirmed absent afterward. The implementation did not retry that code through another tool/channel.

This proves a tool-policy block on that attempt, **not** that the user's credentials are wrong, that the native catalog is empty, or that a future independently supported catalog interface cannot work. Preserve the event and its scope; do not turn it into a user decision to abandon native discovery forever.

## Still unresolved

1. A permitted, actually connected native Legacy catalog host is not supplied by this release.
2. A permitted, actually connected Current authenticated catalog host is not available in the tested setup.
3. Therefore the user's first task—complete live discovery using the previous findings—is not fully achieved merely because the configurable adapters pass tests.
4. The optional MCP protocol implementation can be complete and tested independently of those missing catalog connections. Starting the server does not grant new authorization.
5. Skills are not automatically installed into ChatGPT Chat by committing code, tagging a release or opening the GSM marketplace PR.
6. Public marketplace PR remains draft until live acceptance/distribution criteria are met. Do not overwrite these unresolved states with fixture successes.
7. The v0.4.2 advisory behavior is offline/documentation-contract tested only.
   It has not validated Cloud executor absence, CI eligibility, a startup
   failure, or direct-CI authorization. Empty/partial/stale catalogs, pending
   work, test failures, inconclusive effects, 401/403 and elapsed time alone
   remain insufficient evidence.

## Resume procedure

Read AGENTS.md and the actual Git status first. Reuse the current repository and pending PRs; do not create duplicate projects or Cloud resources. Check the last validation report and SDK profile before broad testing. Investigate an independently supported, authorized catalog interface rather than routing around the recorded refusal. Once connected, test list/find/get/resolve read-only with real account/repository/scope evidence, then update this memory with observed results and provenance.

## Observed in v0.3.1 continuation

- Reconciled the same local repository, implementation branch, source draft PR #1 and immutable v0.3.0 release. No duplicate project, new Cloud task or environment was created.
- Generated the official schema from installed Codex CLI 0.162.0: 447 schema files; environment/add, environment/info and environment/status do not supply a hosted catalog listing. No invented RPC calls or native-session retry followed.
- Retested Codex Tasks.list_tasks and read_task through the actual connected tool. Two relevant onboarding records were visible, but no explicit configuration ID was returned. Their prose was not converted into catalog truth.
- Added the optional native gh-based repository resolver originally envisaged by the note. A real lookup verified the sample repository and its numeric ID in 1.329 seconds; Cloud resolution correctly remained not_verifiable. The GitHub account is distinct from the ChatGPT account; default configuration does not enable the helper.
- Added a separate provider.hints channel for explicit onboarding connector exports. The live metadata test returned two hints and zero environments; its temporary export was deleted. The Python parser does not itself establish a connector connection.
- Added regression coverage for ID conflicts, changed accounts, hint retention, denied-stage stops and SDK transport of non-resolvable hints. Local core profile: 170 passed; core+SDK: 183 passed, zero skipped.
- Still unresolved: permitted complete Legacy/Current catalog hosts and actual installation into ChatGPT Chat. This continuation does not supersede the prior native-session refusal or promote fixture success to live acceptance.

## Observed v0.4.0 — live Legacy enumeration

- User reaffirmed that all provisioning/create/publish work belongs to a separate plugin. No such operation was added to discovery.
- The standard RDC stdin channel opened Codex CLI but did not open its selector. This was terminal-input behavior, not an authentication denial; only the owned diagnostic process tree was closed.
- A DIFFERENT native integration succeeded: ordinary rendered TUI rows through an isolated PTY and fixed read-only selector/navigation keys. No private log, auth.json, cookie/profile, memory or token was read. The previously refused log/session adapter remains absent; its refusal is not erased or treated as authorization to retry that mechanism.
- The concrete new Legacy adapter returned the two existing IDs repeatedly (~4s each), then through the real CLI and official SDK MCP server. Visible selector coverage is complete, but account-wide API completeness and state remain unknown. Preserve catalog_complete=false and separate coverage metadata instead of overstating success.
- Native GH pagination returned 33 owned repositories; name correlation found the sample fixture as a candidate association, not a verified one. The installed gh rejects --slurp with --jq, so native pagination/slurp is followed by bounded local normalization.
- Corrected the earlier over-broad rejection of the Current web proxy path: upstream issue50182 distinguishes it from the Desktop host route. The actual web read and production browser adapter still returned 403 HTML. They stopped and closed owned sessions; no checkbox/challenge, profile import or identity change followed.
- The v0.4.0 machine-local config under %LOCALAPPDATA%/CloudCodeX/environment-discovery/discovery-readonly.local.json contains only explicit adapter settings, executable pins and the existing browser ID. It is outside the repository and no global default was changed.
- A fresh check of the historical zero-task test environment returned a task. Keep the ORIGINAL zero-task observation as historical; do not claim a new zero-task live test merely from its old label.
- Superseded for Legacy only: the v0.3.0/v0.3.1 statements that no concrete native reader is shipped. Still unresolved: successful Current catalog access, unpublished-draft coverage and account-wide authoritative guarantees. No automatic skill installation or marketplace promotion is implied.

## v0.4.0 final review

- Reproduced and fixed native selector failure when the initial selection was already the last environment; Home anchoring preserves full visible-row traversal without task mutation keys.
- Browser ownership checks now forbid reads/closure of reused or unidentified sessions. The prior Current 403 was not retried.
- Final local validation: 224 core and 238 core+SDK tests, zero skips. Fresh Legacy CLI and SDK reads returned two real IDs plus 33 owned repositories. See the final section of VALIDATION_0.4.0.md for measured timings and coverage.

## Icon source decision - 12 October 2026

- Confirmed user instruction: reuse the original Windows Bootstrap cloud and replace only the Windows emblem with a magnifier. Earlier independently generated white-cloud/blue-disc icons were rejected. Work directly in the local repository before any further distribution.
- Original asset: plugins/cloudcodex-windows-bootstrap/assets/icon.png; Git blob 90f40edf8326fa3f6aab967af186badd17f86dff. The Bootstrap source repository/icon is not modified.
- Observed local change: assets/icon.png is derived from that exact source. The complete original alpha channel and every pixel outside the central edit rectangle are identical. Behind the removed emblem, the obscured cloud fill/highlight bands are reconstructed; they are not claimed to be original hidden pixels.
- Both plugin manifests register logo and composerIcon against the new asset. Rebuild procedure and source/image integrity checks are recorded in tools/build_discovery_icon.py and assets/icon-origin.json.
- Status: local artwork candidate, not yet visually accepted by the user and not published or installed over the official v0.4.0. No runtime/provider, skill, MCP or authorization behavior changes.


## v0.4.1 Current repository discovery findings

- Revisited the original 10 October architecture note before implementation. The plugin continues to follow its core rules: Current `environment-configs` is authoritative when available, Codex Tasks is auxiliary, 401/403 stops the Current Cloud path, and GitHub evidence is independent and must be reconciled rather than promoted to a Cloud ID.
- Corrected the v0.4.0 orchestration error where an explicitly requested GitHub inventory could be suppressed by a terminal Current Cloud status. Only cancellation/whole-operation timeout prevents the independent read from starting.
- Inspected installed Codex Desktop 26.1007.2314.0. Current cache/catalog records expose `repository_ids[]`; detailed configurations expose `repositories[].repository_id`, normalized client-side as `repositoryId`. The client uses `environmentConfigs.catalog()`, `refreshCatalog()`, and detailed GET-by-`configId`.
- No dedicated Current by-repository HTTP endpoint was observed. Legacy still has the explicit `/wham/environments/by-repo/...` route; Current counterpart verification instead joins verified GitHub repository IDs to explicit repository IDs in observed configuration rows.
- Updated parser compatibility for `repository_ids`, `repositoryIds`, `repository_id`, `repositoryId`, `repos/repo_map`, and Current version ID/revision variants. Malformed explicit IDs fail closed.
- Live v0.4.1 acceptance on the sample repository verified GitHub repository ID 1408634524. Current remained forbidden because a fresh BrowserAct session could not be proven owned; the adapter therefore performed no catalog eval/close. Counterpart remained not_verifiable with candidate names only. No Cloud ID was fabricated and no provisioning occurred.


## v0.4.1 browser-owned session reconciliation

- Confirmed by an isolated live BrowserAct open/read-list/close probe that the open response's `browser_id` may be the alias `workbench` while the session inventory carries the actual configured `chrome_local_...` ID. `reused` describes browser reuse and must not be treated as ownership of the named session.
- Corrected the Current BrowserAct adapter to require a unique absent-before / present-after named session matched by the actual session inventory, including cleanup after an interrupted open. The two previously leaked `cloudcodex-catalog-*` sessions were separately identified and closed; no other sessions were touched.
- One post-fix live Current lookup actually reached the Web GET and received HTTP 403, while independently confirming GitHub ID `1408634524`. Provider reason `http_403`, `catalog_complete=false`, counterpart `not_verifiable`, `session_cleanup_confirmed=true`, and zero leaked owned sessions. No retries, identity switching or challenge handling after the denial.
- Desktop's main-process catalog flow uses `view=picker` first, with a same-surface standard-list fallback only on HTTP 400. This picker route is Desktop-specific; Web retains its separately observed standard GET. Current live success and unpublished draft coverage remain unverified.


## v0.4.1 picker completeness design

- The installed Desktop GUI's `view=picker` returns a selection-oriented catalog. Even after exhausting picker pages, that is not sufficient proof that every published Current configuration is represented. Its provider result is therefore partial and cannot prove absence.
- The Desktop's 400-only fallback calls the standard list. The GUI filters version revisions older than 2 for its selector, but Discovery deliberately preserves all full-list rows and versions to avoid false negatives. Complete standard user/workspace coverage can be authoritative for its requested draft policy.
- The Web route remains standard-list only; the Desktop picker query is never silently applied to it. Tests cover complete Web/standard catalogs, partial Desktop picker-only catalogs, 400 fallback, and terminal 401/403/429.


## 12 October 2026: Current Webcmd escalation adapter

- The user requested Webcmd as an optional Current Cloud escalation route.
- Chosen position: after optional primary and before BrowserAct, approved HTTP,
  onboarding and snapshot. A terminal 401/403/rate-limit never triggers
  another Cloud read source; the only allowed progression is after a
  recoverable result.
- Added startup-only WebcmdSettings, bounded pinned Node/entrypoint CLI,
  preinstalled CloakBrowser and existing-profile checks, owned transient
  session creation/cleanup, fixed original Current backend and standard GET.
  No browser profile import, credential reads, browser installation or UI
  challenge solving.
- Live test using temporary approved config and Webcmd 0.8.4 on HOME:
  returned 401 JSON, not an environment list. Provider reason http_401,
  zero rows, one terminal stage, session_cleanup_confirmed=true, zero new
  lingering sessions. Source and service semantics are preserved.
- CLI profile 'default' initially reported missing; running the operator's
  existing 'webcmd doctor' restored/connected it without importing a login.
  The adapter itself does not run doctor or change the profile.
- No official Current API key/authorization was obtained, and no successful
  Current Configuration ID was recovered. No provisioning/PR/push or merge.

## 12 October 2026: single Current Configuration ID research

- Observed in installed Desktop 26.1007.2314.0 static code: pS builds GET /v1/environment-configs/{encodeURIComponent(configId)}. A known draftId selects /drafts/{draftId}; no draftId is currently verified, so that route was not exercised.
- New read-only single-ID tests used the Configuration ID already documented in the 10 October architecture note. Anonymous HttpClient returned 403 text/html with cf-mitigated=challenge; Webcmd 0.8.4 on the existing isolated runtime returned 401 application/json and no record. Neither result proves the ID is nonexistent.
- Static evidence: list, refresh and detail requests share the Desktop xS/yS authentication service, including account/user checks. An exact Configuration ID does not replace that authentication; no token or private client cache was accessed.
- Connected Codex Tasks list returned 8 tasks without another page. Both known onboarding threads remain readable but returned no explicit Configuration ID, so they do not prove two different environments or a fresh ID association.
- Public openai/codex cloud-client README (current main and cited revision cedb4fd...) still documents Resume/Attach only, with caller-supplied gRPC origin and identity; not a Current configuration catalog. It was inspected, not invoked.
- Current get_environment(ID) still calls list_environments then filters; this is an observed implementation gap, not a direct-read implementation. No runtime changes were made during this research.
- Webcmd probe cleanup confirmed zero owned sessions left and the one preexisting diagnostic session preserved. No provisioning, primary input, authentication changes, merge or publication.
- Result: no new live Current configuration recovered. The historical note supplies one unverified-now candidate; onboarding supplies indirect evidence only. Detailed report and JSON were delivered separately, without marking history as a live catalog.

## 12 October 2026: exact-ID Current GET and on-hold skill status

- User explicitly requested implementing single-ID Current lookup as an
  alternative/escalation before placing the still-usable skill on hold for
  Current API authorization support. Never treat 401/403 as an invitation
  to switch identity, profile, API surface or bypass a challenge.
- Added `runtime/current/detail.py`: fixed original Current Desktop GET
  by known safe immutable Configuration ID, single JSON record parsing,
  exact ID/account checks and separate `point_verified` flag, not a
  globally complete catalog. No unknown draft GET, arbitrary URL,
  by-name or by-repository guesswork.
- Wired Current provider, approved HTTP relay allowlist, Webcmd existing
  owned-session reader, EscalatingProvider and `get_current_environment`
  service. Catalog-only stages and Legacy behavior are preserved; 401/403
  remain terminal, single success stops with catalog_complete=false.
- Current frontmatter, agent instructions, MCP tool descriptions, manifests
  and README explicitly say: feature **available**, Current live config
  catalog/detail **on hold pending supported authorization**; previous
  Current point Webcmd 401 JSON and anonymous HTTP 403 HTML remain factual
  evidence, not success. No OpenAI fix or ETA is claimed.
- Offline validation: 298 core and 313 core+SDK MCP tests passed, zero
  skipped; Ruff F and package audit passed. v0.4.1 local ZIP contains
  46 files (including current/detail.py), SHA-256
  95db40007ea71daf6be031d0bc37c398507afe7e1a6ebddb8d2214054fe0b672.
- No new Cloud requests, session/profile mutations, credential reads,
  provisioning, release, merge, push or plugin publication in this phase.
  Remain on existing feature/current-repository-discovery-v041 branch.

## 14 October 2026: observed frontmatter import regression

- Observed: release 0.4.2 contains an unquoted colon-space in both SKILL.md descriptions; a real YAML parser rejects both. Prior literal-marker tests missed this loading defect.
- Fixed in 0.4.3: preserve exact descriptions as JSON-quoted YAML scalars, synchronize package/runtime version and add a failing-first regression. No discovery transport, authorization or fallback semantics changed.
- User requested completing private-account import and local deployment from the supplied release archives; publication is owned by Root, not by a discovery operation. Native Cloud runtime injection remains separately unverified.
