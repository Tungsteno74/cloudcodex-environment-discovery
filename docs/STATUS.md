# Implementation status — v0.2.0 (preview)

| Component | Source implemented | Live E2E |
|---|---|---|
| Direct Legacy skill | Yes | Requires installation and authorized Legacy integration |
| Direct Current skill | Yes | Requires installation and authorized Current integration |
| Mandatory Root dispatch skill | **None** | Not applicable |
| Domain-specific MCP tools (4+4) | Yes | Offline protocol/dispatch tests |
| Legacy provider + Legacy tests | Yes | TUI selector/authorized transport not attached |
| Current provider + Current tests | Yes | Authorized catalog transport not attached |
| Domain-neutral common types/resolver | Yes | Offline tests |
| Root automatic skill choice | Manifest hints available | Model routing not guaranteed |
| Credential Broker/provisioning | Outside plugin | Not part of scope |

The source plugin and Git-backed marketplace registration remain separate. Marketplace PR is deliberately draft pending live acceptance. Current integration remains viable if Legacy is retired. No task/environment creation or login credential extraction is performed by discovery.

See README.md and docs/MIGRATION_0.2.0.md.
