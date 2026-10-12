# CloudCodeX Environment Discovery 0.4.0 (preview)

Two independent read-only skills: legacy-discovery and current-discovery. No mandatory Root dispatcher, MCP server or provisioning operation.

Legacy now has a concrete isolated native CLI screen reader: two real IDs were returned repeatedly and through MCP on the reference Windows machine. Only CLI 0.162.0 is validated; optional native dependencies are in optional/requirements-native.txt. No private logs, credentials or primary-desktop input are accessed.

Current has a concrete same-origin browser-web GET adapter, but the actual catalog request returned HTTP 403. It stops; it does not solve challenges or claim an empty catalog. Desktop and web API surfaces are distinct.

CLI: runtime/cli.py legacy list --config <operator-config> --correlate-github. The optional owned GitHub catalog is joined by IDs/associations first, names as hints. Cloud completeness is separate from visible UI coverage and GitHub completeness.

Core Python3.9+, native profile tested on Python3.12, optional MCP Python3.10+ with optional/requirements-mcp.txt. No root mcp.json is shipped. The empty example configuration does not contain credentials or automatically connect personal accounts.

Source and operation guide: https://github.com/Tungsteno74/cloudcodex-environment-discovery/tree/v0.4.0
