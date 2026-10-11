# Optional MCP server — v0.3.0 SDK profile

## Independence from skills and CLI

The default package contains **no root `mcp.json`**. Neither of the two domain skills nor the Python CLI requires an MCP process. The opt-in registration template remains `optional/mcp.json`.

The previous handwritten JSON-RPC loop has been replaced by the **official MCP Python SDK**, pinned to `mcp==1.30.0` in `optional/requirements-mcp.txt`. The core remains Python 3.9+ with standard-library dependencies. The optional server requires Python **3.10+**, and is tested with Python 3.12.

## Start only with explicit operator configuration

Select an interpreter of the supported version, preferably in a dedicated virtual environment, then install:

```sh
python -m pip install -r plugins/cloudcodex-environment-discovery/optional/requirements-mcp.txt
```

Configure a compatible MCP client to execute that interpreter with:

```text
<absolute-plugin-root>/runtime/server.py --config <absolute-operator-config.json>
```

Use `optional/mcp.json` as a template. Set its interpreter and `--config` arguments according to the real host; do not assume the current shell's `python` is the same interpreter used by the MCP client. If the local client discovers MCP through root `mcp.json`, explicitly copy the template in that **local installed copy** only. Do not commit a root MCP registration to this repository.

Only **stdio** is implemented and advertised for this package. There is no unauthenticated remote HTTP listener. Publishing a GitHub release does not attach a local stdio process or install skills into ChatGPT Chat.

## Implemented server profile

- Standard SDK initialization, protocol negotiation and initialized notification.
- Eight tools: list/find/get/resolve independently for Legacy and Current.
- Strict input schemas with no `cloud_type=all`, command, URL, credential or configuration-path arguments.
- Read-only, non-destructive, idempotent annotations.
- Structured output with explicit completeness, provenance and per-stage attempts.
- `isError=true` for unavailable/denied/invalid/deadline outcomes, rather than successful empty results.
- Sanitized validation and runtime errors; raw host output is not exposed.
- Progress notifications for escalation stages when the caller supplies a progress token.
- SDK cancellation propagated into the read operation; adapter child processes are bounded and terminated on cancellation/timeout.
- One whole-operation deadline plus bounded per-host execution/output.
- Reusable operator-configured runtime and lazy provider selection.
- Normal stdio closure handled by the SDK. Core result size is bounded before transmission.

The supported protocol versions are those of the pinned SDK. The tested session negotiated `2025-11-25`; the server no longer simply echoes an arbitrary client version.

Resources, prompts, task-augmented execution, credential-broker methods, environment creation and remote HTTP hosting are **not advertised capabilities** of this server.

## Authorization remains separate

The server uses the exact same `DiscoveryRuntime` as the CLI. An approved catalog host is still required for live reads. Starting MCP does not sign into Codex Cloud, acquire OAuth scopes, unwrap stored tokens or bypass a security interstitial. With no configured source, the tools return an explicit unavailable result and diagnostic trace.

The native-session adapter attempted during this implementation was blocked by a tool safety control and is not included. The server tests therefore do not imply that the actual OpenAI catalogs were reached.

## Test profiles

```sh
python -X utf8 tools/validate.py
python -X utf8 tools/validate.py --with-mcp
```

The first command runs the dependency-free core. The second requires the SDK and runs real stdio server/client tests, including all eight calls, invalid arguments, denied/empty catalogs, progress, timeout and cancellation. It fails if the SDK is missing or integration tests are skipped.

The backend catalogs in these tests are simulated host fixtures. This is a genuine MCP protocol/integration test, **not live provider authentication verification**.

## References

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP lifecycle: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- MCP stdio transport: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP tools: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
