# Optional MCP adapter — manual opt-in

## Default installation: skills without a server

CloudCodeX Environment Discovery is a **skills-first plugin**. Its standard package includes two directly discoverable skills, `legacy-discovery` and `current-discovery`, and their shared reference contracts.

The standard package intentionally has **no root `mcp.json`**. Installing the skill package does not launch `runtime/server.py`, require a local MCP connection, or make a Python server process a prerequisite for skill discovery. The Root uses already-connected, authorized tools or explicitly invoked CLI operations whenever available.

The Python providers and read-only CLI remain reusable, but do not automatically inherit ChatGPT/Codex authentication. Missing authorized transports must be reported as **unavailable**, never as a verified empty catalog.

## Optional adapter

The code for the eight provider-specific read-only MCP tools is retained in:

`plugins/cloudcodex-environment-discovery/runtime/server.py`

An opt-in server configuration is stored at:

`plugins/cloudcodex-environment-discovery/optional/mcp.json`

That nested file is **not** the plugin's standard MCP entry point. It is provided solely as a template for an explicitly requested integration.

## Enable it when useful

For a **local host that explicitly supports stdio MCP**:

1. Install Python 3.9+ and make sure the complete plugin directory is available to the host.
2. Choose the host's supported, authorized MCP installation mechanism. Point it to `runtime/server.py` using the verified paths and working directory for that host. The included `optional/mcp.json` may be used as a template.
3. If the host uses the Agent Plugins root `mcp.json` discovery convention and the user explicitly wants the MCP server enabled, copy `optional/mcp.json` to the package root `mcp.json` in that host's **local installed copy**, then reload the host. Do not commit the copied root file to the canonical source.
4. Check tool registration (`list_legacy_environments`, `list_current_environments`, and their find/get/resolve counterparts), then run a harmless read-only test.
5. An **authorized provider/transport** is independently required for live catalog access; installing the optional MCP process does not grant access to Codex Cloud.

To disable the integration, remove the local MCP registration (or the manually copied root config) and reload the host. The skills continue to work without it.

## Security and scope

- The optional MCP adapter is **not** a Credential Broker.
- It never searches `auth.json`, cookies, browser sessions or secrets.
- It never creates Cloud tasks or environments and cannot bypass HTTP 401/403.
- Its absence is not a failure of the two independent skills.
- ChatGPT web/mobile does not automatically attach local stdio MCP tools when a GitHub plugin or marketplace entry is installed.
- This is an opt-in integration. Its source and tests remain available even while the default install is skill-only.

## Verification

`python -X utf8 tools/validate.py` verifies the two skills, the absence of root `mcp.json`, the opt-in template, the provider code and the optional MCP protocol tests. `python -X utf8 tools/build_release.py` builds the standalone archive without automatically enabling MCP.
