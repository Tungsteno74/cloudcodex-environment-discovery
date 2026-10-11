# Codex Cloud Environment Discovery

Independent, **read-only** plugin for discovering existing Codex Cloud **Legacy** and **Current** environments **from the Root Orchestrator before any task exists**.

**Status:** 0.1.1 prototype with tested contracts and runtime; live provider integration is not complete. The package never creates tasks or environments and never accesses stored authentication secrets.

## Why a separate plugin?

The GSM architecture separates each plugin's source, tests, releases and GitHub history. This repository is intentionally independent of [CloudCodeX Windows Bootstrap](https://github.com/Tungsteno74/cloudcodex-windows-bootstrap). The family catalog is [CloudCodeX Helpers Marketplace](https://github.com/Tungsteno74/cloudcodex-helpers-marketplace), which contains only Git-backed plugin references.

In a future fully automated workflow, *optional provisioning* precedes **Discovery**, which resolves a verified environment and supplies its descriptor to a separate, subsequently authorized **Bootstrap/Cloud task**. Discovery itself is **read-only**.

## Available features

- Typed providers for Legacy and Current catalogs with injectable **already authorized** transports.
- Normalized EnvironmentDescriptor, account/scope, repository associations and explicit provenance.
- Four stable operations: list_environments, find_environments, get_environment and resolve_environment.
- Repository ID matching first, explicit owner/repo matching second; name similarity is an unverified hint.
- Draft visibility, user/workspace scopes, bounded pagination and cursor-loop handling for Current Cloud.
- Fail-closed status distinctions: unavailable, unauthorized, forbidden, not_found, invalid_response, partial and empty.
- Read-only imported catalog snapshots for offline diagnostics; imported data is **never live verified**.
- Local MCP stdio server implementing the four tools, a CLI and offline tests.

## Actual limits (do not skip)

- The native authenticated Legacy CLI selector is interactive. The skill can guide Root terminal tooling to use `codex cloud` and its environment selector, but the packaged local MCP runtime **does not silently scrape that TUI or extract Codex credentials**. Its Legacy live provider requires an externally injected authorized selector reader or transport.
- Current Cloud GET is an internal client contract, not a public stable API. The local MCP runtime has **no Credential Broker**. Unless an authorized Current transport is injected, it returns unavailable, not an empty catalog. It never retries around Cloudflare or HTTP 401/403.
- ChatGPT Chat web/mobile does not automatically launch a local stdio MCP process from a marketplace installation. Use an authorized host which supports local plugin processes, or use the skill from the Root with available connectors.
- Codex Tasks.list_environments is **not** the same as a hosted Cloud environment catalog. Task onboarding messages and cache data are auxiliary hints only.

## Layout

```text
plugins/cloudcodex-environment-discovery/
  plugin.json, .codex-plugin/plugin.json, mcp.json, .app.json
  skills/cloudcodex-environment-discovery/{SKILL.md,agents/,references/}
  runtime/{cli.py,server.py,discovery/}
tests/
tools/{validate.py,build_release.py}
docs/
.github/workflows/validate.yml
```

## Development and verification

Requires Python **3.9+**, no third-party runtime dependencies:

```sh
python -X utf8 tools/validate.py
python -X utf8 tools/build_release.py
python plugins/cloudcodex-environment-discovery/runtime/cli.py list --pretty
```

To inspect **explicitly supplied** offline catalog snapshots, not login state:

```sh
python plugins/cloudcodex-environment-discovery/runtime/cli.py find --cloud-type legacy --repository owner/repo --snapshot-legacy path/to/catalog-example.json --pretty
```

The local MCP server can be started by a compatible host using the distributable package's `mcp.json`. It does not obtain authorization by itself.

## Installation and distribution

Canonical source: `Tungsteno74/cloudcodex-environment-discovery`. The distributable package is under `./plugins/cloudcodex-environment-discovery`. The family marketplace is kept separate according to the existing GSM lifecycle: experimental plugins should be staged privately or as a proposed catalog change until intentionally approved for public distribution.

The package supports a Git-backed marketplace entry using `source=git-subdir`, its canonical repository URL, `path=./plugins/cloudcodex-environment-discovery`, `ref=main`.

## License

MIT. See [LICENSE](LICENSE).
