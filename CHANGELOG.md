# Changelog

## 0.2.1 — Optional MCP adapter

- Removed root `mcp.json` automatic registration from the standard plugin.
- Preserved the tested local MCP server and eight tools behind `optional/mcp.json` for explicit opt-in.
- Kept both skills and the read-only CLI independent from server startup.
- Added regression checks and guidance for optional activation.

## 0.2.0 — Two independent discovery skills

- Replaced one Root-only skill with **legacy-discovery** and **current-discovery**.
- Added eight namespaced read-only MCP operations, four per Cloud generation.
- Removed the implicit all-types catalog and requirement for a Root dispatch step.
- Split Legacy/Current Python providers, APIs and test suites; shared code is cloud-agnostic.
- Lazy provider import for MCP and CLI, allowing Current to function independently if Legacy is retired.
- Preserved fail-closed evidence, account, repository and authorization semantics.
- Documented intentional pre-1.0 API/CLI/skill migration.

## 0.1.1 — Canonical CloudCodeX name

- Renamed package, repository and local skill identity.
- Corrected MCP stdio JSON-RPC transport framing.

## 0.1.0 — Initial read-only prototype

- Typed provider contracts, normalized catalog and resolver, local CLI/MCP, offline tests.
