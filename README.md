# CloudCodeX Environment Discovery

Read-only discovery of existing Codex Cloud environments **before any Cloud task exists**. The plugin stays independent of CloudCodeX Windows Bootstrap and of environment provisioning.

## Two independent skills

- **legacy-discovery**: Legacy catalog and repository associations.
- **current-discovery**: current-generation configurations, user/workspace scopes, drafts and versions.

The Root chooses a generation directly. There is no mandatory Root dispatcher, implicit mixed catalog, or required MCP server.

## v0.3.0 preview — implemented and not yet verified live

| Component | This release |
|---|---|
| Skills and escalation procedures | Independent per generation; explicit stop/consent rules |
| Executable adapter configuration | Operator-approved, integrity-pinned command hosts; no Python callback injection needed |
| Legacy HTTP catalog / by-repository adapter | Implemented over an approved GET host; no label-to-repository guessing |
| Current catalog adapter | Implemented scoped pagination, drafts, versions and account continuity |
| Primary native/official source | Host-command contract implemented; **a working authenticated host is not bundled** |
| Current onboarding hints | Separate indirect-evidence host stage; never enough for automatic resolution |
| Snapshot fallback | Explicit imported evidence, never a live catalog |
| Optional MCP | Official MCP Python SDK, eight read-only tools; real stdio client/server tests |
| Native-session automation | **Not shipped**: its attempted implementation was blocked by tool safety controls |
| Live OpenAI catalog acceptance | **Not completed in this release**; no new Cloud resources were created |

This is not a claim that the missing authorized catalog host now exists. The command adapters are working integration boundaries, not a credential broker and not a substitute for authorization.

## Use without MCP

Python **3.9+** is sufficient for the core and CLI. No third-party core dependencies are needed.

```sh
python plugins/cloudcodex-environment-discovery/runtime/cli.py legacy doctor
python plugins/cloudcodex-environment-discovery/runtime/cli.py current list --config /absolute/operator/discovery.json --pretty
python plugins/cloudcodex-environment-discovery/runtime/cli.py legacy find --repository owner/repo --config /absolute/operator/discovery.json
python plugins/cloudcodex-environment-discovery/runtime/cli.py current resolve --repository owner/repo --include-drafts --config /absolute/operator/discovery.json
```

`doctor` reports configuration only: it does not start hosts or claim live access. Without configured sources, reads return `unavailable` and `catalog_complete=false`, never a verified empty catalog.

Configuration is selected at process startup by `--config` or `CLOUDCODEX_DISCOVERY_CONFIG`. It cannot be supplied through an MCP tool call. Use the empty, safe `optional/discovery.example.json` as a starting point and read [ADAPTERS.md](docs/ADAPTERS.md) before enabling a host.

## Escalation

Legacy: primary native catalog host → explicitly approved HTTP catalog host → imported snapshot.

Current: primary official catalog host → explicitly approved HTTP catalog host → onboarding hints → imported snapshot.

Only configured and approved stages run. `AUTO` does not grant consent; `CONFIRM` returns `approval_required` for an unapproved stage. An authoritative empty catalog terminates successfully. **401, 403, rate limiting, identity mismatch, cancellation and deadline expiry stop the sequence**, rather than retrying through a different identity.

Every read returns a stage trace, timing, status and completeness. Partial and indirect records remain candidates. A unique resolution requires live, fresh, verified evidence and complete requested coverage. Different drafts/versions are not silently discarded as duplicate IDs.

## Optional MCP

Python **3.10+** is required for the optional SDK profile; Python 3.12 is tested. Installation is explicit:

```sh
python -m pip install -r plugins/cloudcodex-environment-discovery/optional/requirements-mcp.txt
python plugins/cloudcodex-environment-discovery/runtime/server.py --config /absolute/operator/discovery.json
```

The process speaks **stdio only** and should normally be started by an MCP client. It exports list/find/get/resolve for each generation, eight tools in total. The official SDK handles lifecycle, version negotiation, framing and cancellation; the application adds strict sanitized schemas, read-only annotations, progress and bounded results. See [MCP_OPTIONAL.md](docs/MCP_OPTIONAL.md).

There is **no root `mcp.json`**. GitHub publishing does not install the skills into ChatGPT Chat or attach a local MCP process to it.

## Validation

```sh
python -X utf8 tools/validate.py
python -X utf8 tools/validate.py --with-mcp
python -X utf8 tools/build_release.py
```

The core profile keeps the provider suites independent. The MCP profile requires the SDK and fails if SDK tests cannot run; skipped tests are not reported as verified. Host fixtures simulate catalogs, but execute as real child processes. SDK tests use a real server process and SDK client. **Neither test category is proof of live OpenAI authorization.**

## Distribution and continuity

Canonical repository: `Tungsteno74/cloudcodex-environment-discovery`. The standalone package is under `plugins/cloudcodex-environment-discovery`; the GSM family marketplace remains catalog-only and its integration PR is still draft. The original provisioning experiment and the Bootstrap 0.6.6 three-gate pipeline are not changed.

Read [PROJECT_MEMORY.md](docs/PROJECT_MEMORY.md), [ADAPTERS.md](docs/ADAPTERS.md), [MCP_OPTIONAL.md](docs/MCP_OPTIONAL.md) and the [changelog](CHANGELOG.md). Licensed under MIT.
