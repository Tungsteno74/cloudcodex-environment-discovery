# CloudCodeX Environment Discovery 0.3.1 (preview)

Two independent read-only skills: legacy-discovery and current-discovery. No Root dispatcher or mandatory MCP server.

Core CLI: Python 3.9+, runtime/cli.py. Supply operator configuration via --config or CLOUDCODEX_DISCOVERY_CONFIG. The safe optional/discovery.example.json contains no connected sources; it intentionally returns unavailable, not a verified empty catalog.

Optional MCP: Python 3.10+ and optional/requirements-mcp.txt. Start runtime/server.py from a compatible stdio MCP client only after explicit opt-in; optional/mcp.json is a template, not automatic root registration.

The SDK server and executable host adapter contracts are tested. A working authenticated OpenAI catalog host is NOT bundled. Native-session automation was blocked during implementation, so this preview must not be claimed to have completed live Legacy/Current discovery. No task creation, credential extraction or provisioning is included.

Full documentation and source: https://github.com/Tungsteno74/cloudcodex-environment-discovery

Optional native GitHub repository verification and explicit Codex Tasks onboarding evidence are supported. Neither establishes a complete live OpenAI Cloud catalog; absent Configuration IDs remain hints.
