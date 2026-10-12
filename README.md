# CloudCodeX Environment Discovery

Read-only recovery of **existing** Codex Cloud environments. Two independent skills, `legacy-discovery` and `current-discovery`, are directly available to the Root when installed. No mandatory Root dispatcher, mixed catalog, provisioning, task creation or environment publication is included.

## v0.4.0 — actual operational result

| Path | Implementation | Observed result on the reference machine |
|---|---|---|
| Legacy native CLI selector | Complete screen-only adapter, isolated terminal | **Two real environment IDs returned repeatedly**, also through CLI and optional MCP |
| Owned GitHub repository catalog | Native `gh api` pagination and account continuity | **33 repositories enumerated**, correlated to the observed Legacy rows |
| Current web catalog | Built-in BrowserAct read-only GET adapter | **HTTP 403**, reported as `forbidden`; no challenge bypass or second-scope retry |
| Current Desktop catalog | Approved HTTP host adapter, separately configured endpoint | No connected authorized direct host validated in this release |
| Current onboarding | Existing connector exports or approved host | Indirect hints only, not a substitute for configuration IDs |
| Optional MCP | Official SDK, eight tools, cancellation/progress/schema validation | Actual live Legacy catalog call succeeded; no automatic MCP registration |

**Current discovery is not claimed to return a live environment list yet.** Its executable browser adapter now reaches the catalog route and returns the actual authorization blocker instead of requiring an unspecified host implementation. An authentication/Cloudflare denial cannot be fixed by declaring a test fixture successful.

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
