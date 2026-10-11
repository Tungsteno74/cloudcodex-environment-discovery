# Implementation status — v0.2.1 (preview)

| Component | Source implemented | Live E2E |
|---|---|---|
| Direct Legacy skill | Yes | Requires installation and authorized Legacy integration |
| Direct Current skill | Yes | Requires installation and authorized Current integration |
| Mandatory Root dispatch skill | **None** | Not applicable |
| Default MCP server registration | **None** (root `mcp.json` absent) | Skills and CLI need no MCP process |
| Optional domain-specific MCP tools (4+4) | Yes, opt-in only | Offline protocol/dispatch tests; no skill dependency |
| Legacy provider + Legacy tests | Yes | TUI selector/authorized transport not attached |
| Current provider + Current tests | Yes | Authorized catalog transport not attached |
| Domain-neutral common types/resolver | Yes | Offline tests |
| Root automatic skill choice | Manifest hints available | Model routing not guaranteed |
| Credential Broker/provisioning | Outside plugin | Not part of scope |

The source plugin and Git-backed marketplace registration remain separate. Marketplace PR is deliberately draft pending live acceptance. Current integration remains viable if Legacy is retired. No task/environment creation or login credential extraction is performed by discovery.

See README.md, docs/MIGRATION_0.2.0.md and docs/MCP_OPTIONAL.md.
