# CloudCodeX Environment Discovery

Read-only recovery of **existing** Codex Cloud environments. Two independent skills, `legacy-discovery` and `current-discovery`, are directly available to the Root when installed. No mandatory Root dispatcher, mixed catalog, provisioning, task creation or environment publication is included.

## v0.4.0 — actual operational result

| Path | Implementation | Observed result on the reference machine |
|---|---|---|
| Legacy native CLI selector | Complete screen-only adapter, isolated terminal | **Two real environment IDs returned repeatedly**, also through CLI and optional MCP |
| Owned GitHub repository catalog | Native `gh api` pagination and account continuity | **33 repositories enumerated**, correlated to the observed Legacy rows |
| Current web catalog | Built-in BrowserAct read-only GET adapter | **HTTP 403**, reported as `forbidden`; the Cloud path stops, while explicitly requested GitHub discovery remains independent |
| Current Desktop catalog | Approved HTTP host adapter, separately configured endpoint | No connected authorized direct host validated in this release |
| Current onboarding | Existing connector exports or approved host | Indirect hints only, not a substitute for configuration IDs |
| Optional MCP | Official SDK, eight tools, cancellation/progress/schema validation | Actual live Legacy catalog call succeeded; no automatic MCP registration |

**Current discovery is not claimed to return a live environment list yet.** Repository-centric discovery is nevertheless usable under that blocker: an explicitly authorized GitHub read can verify the requested repository independently, while `find_current_environments` returns `repository_counterpart`. A counterpart is `verified` only when an observed Current configuration carries the same `repository_id` or explicit repository association; environment-name equality is only a `candidate`. A 403 therefore remains a Cloud denial, not a false empty result.

## Native Legacy, without credentials or private logs

`runtime/legacy/native_cli.py` starts the ordinary authenticated Codex CLI in a separate pseudoterminal. It reads only the rendered **Select Environment** screen using `o`, End/Home/PageDown; it never sends New Task, Enter or Apply. It does not read client logs, auth.json, browser profiles or process memory.

The tested client is **codex-cli 0.162.0 on Windows**. Unknown versions fail closed. The native interpreter profile needs `optional/requirements-native.txt`; Python 3.12 was used for the live tests. Core parsers and non-native CLI usage remain Python 3.9+.

The selector exposes real IDs but not an account ID or proof of server-wide completeness. Results therefore distinguish:

```json
{"status":"partial","catalog_complete":false,"provider":{"coverage":{"surface":"native_tui","visible_rows_complete":true,"account_catalog_complete":false}}}
```

`partial` here **does not mean an empty or simulated list**. It means the visible native list was read, while undisclosed account/scope/draft guarantees were not fabricated. `resolve` remains conservative.

## Execute through the CLI

```sh
python plugins/cloudcodex-environment-discovery/runtime/cli.py legacy list --config /absolute/discovery.json --pretty
python plugins/cloudcodex-environment-discovery/runtime/cli.py legacy list --config /absolute/discovery.json --correlate-github --pretty
python plugins/cloudcodex-environment-discovery/runtime/cli.py current list --config /absolute/discovery.json --pretty
```

Configuration is operator-owned and selected at startup. It contains paths, integrity pins and approved read stages, **not credentials**. `doctor` reports setup, not proof of access. The distributed example has no enabled account-specific adapters.

The reference machine now has a non-secret local configuration under `%LOCALAPPDATA%\CloudCodeX\environment-discovery\discovery-readonly.local.json`. This file is **not** part of the public package. See [operation/setup details](docs/OPERATIONS_0.4.0.md).

## Current web and Desktop are distinct surfaces

- Desktop: `https://codex-cloud-backend.chatgpt.com/v1/environment-configs`.
- Web same-origin proxy: `https://chatgpt.com/api/codex-cloud/v1/environment-configs`.

The earlier blanket statement that the web-prefixed route was wrong conflated two client surfaces. This release keeps them separate and explicitly configured; a denial on one is not a reason to switch automatically to the other. `browser_web` always uses the web surface and an existing isolated Chrome browser. It does not create/import profiles, extract cookies, alter proxies or solve challenges.

Draft inclusion, scopes and pagination remain explicit. `omitDraft=false` is implemented, but successful live retrieval of unpublished Current drafts is **not verified**.

## GitHub correlation, not fabrication

`--correlate-github` on `list` obtains the complete owned-repository inventory through native `gh --paginate --slurp`, then joins it with observed environment rows. Explicit repository IDs/associations outrank names; equal names are `name_candidate` hints. A repository without an observed Cloud row never becomes an invented environment. Cloud and GitHub completeness are independent.

## Optional MCP

MCP is an optional adapter, not a prerequisite. Install the declared SDK profile on Python 3.10+ and configure `runtime/server.py --config ...` in a compatible stdio host. The standard package intentionally has **no root `mcp.json`**.

The eight existing list/find/get/resolve tools retain their names. The two list tools additionally accept `correlate_github: true`. No tool accepts a token, executable, arbitrary URL, profile path or approval escalation. See [MCP_OPTIONAL.md](docs/MCP_OPTIONAL.md).

## Validation and release

```sh
python -X utf8 tools/validate.py
python -X utf8 tools/validate.py --with-mcp
python -X utf8 tools/build_release.py
```

Core tests are offline; optional SDK tests run real stdio client/server processes with fixtures. Separately recorded live reads validate the native Legacy and GitHub paths and the Current 403 response. See [VALIDATION_0.4.0.md](docs/VALIDATION_0.4.0.md), [PROJECT_MEMORY.md](docs/PROJECT_MEMORY.md) and [CHANGELOG.md](CHANGELOG.md).

Canonical source: `Tungsteno74/cloudcodex-environment-discovery`. The separate GSM marketplace PR remains draft; publication of a GitHub preview does not install this plugin into ChatGPT Chat. CloudCodeX Windows Bootstrap 0.6.6 and its three gates are unchanged. MIT license.


## v0.4.1 — Current status: usable, live access pending

The Current skill is **implemented but on hold for live environment identification** until an authorized and supported Current Cloud backend access path becomes available. This is an observed authorization issue, not a confirmed OpenAI fix schedule. Live Current catalog and exact-ID requests have returned **401 JSON via Webcmd** or **403 Cloudflare HTML via anonymous HTTP**; neither is a verified empty catalog. Legacy discovery stays independently operational.

A known immutable Current Configuration ID now uses the documented Desktop point route `GET /v1/environment-configs/{configId}` through a configured, already-approved Desktop HTTP or Webcmd adapter. CLI example:

```sh
python plugins/cloudcodex-environment-discovery/runtime/cli.py current get --environment-id '<known-current-config-id>' --config /absolute/discovery.json --pretty
```

A successful 200 JSON with a matching ID verifies *one configuration*, reported as `point_verified=true` with `catalog_complete=false`; it does not prove all environments, revisions or drafts have been enumerated. For a configured catalog-only stage, `get` retains its conservative catalog matching behavior. 401/403/429 terminate Cloud escalation; no automatic browser/account switching, profile imports, credential extraction or challenge handling. Current `list/find/resolve` remain catalog-dependent and may return blockers plus independently sourced repository/onboarding hints.

See [Current point-read and pending status](docs/CURRENT_POINT_LOOKUP_0.4.1.md) and [Current skill](plugins/cloudcodex-environment-discovery/skills/current-discovery/SKILL.md). No release/merge/publication is implied by the local v0.4.1 preview.

## v0.4.2 — optional Root-facing direct-CI recommendation

The user approved a narrowly bounded fallback recommendation to the independently
published `cloudrepo-environment-direct` skill. This is **not** direct CI
execution, a plugin import, an authorization grant, or a mandatory dispatcher.
For explicit software-validation intent, each independent discovery skill may
return `recommended_fallback: cloudrepo-environment-direct` only after bounded
trusted observation cannot resolve a viable, verified Cloud executor. Its
structured evidence fields are `source`, `repository`, `full_sha`, `check_plan`
and `decision_evidence`; unknown evidence stays `unknown`.

The default `fallback_eligibility` is `candidate_requires_root_preflight`. Root
independently reconciles Cloud task/CI provider references and chooses and
authorizes any direct CI. A partial, empty or stale catalog never proves Cloud
absence. Pending/active tasks or CI, test failures, inconclusive remote side
effects, 401/403 denial, and slow wall-clock alone neither establish eligibility
nor prove a failed startup. A denial stops Cloud escalation and is not bypassed
through another identity/provider. The recommender creates no tasks, refs, PRs,
workflows or environments and changes no permission.
