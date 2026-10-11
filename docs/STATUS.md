# Implementation status — v0.3.0 preview

## Requested work and actual result

| Area | Implemented | Verification / limitation |
|---|---|---|
| Independent Legacy and Current skills | Yes | Direct entry points; no mandatory Root skill or MCP |
| Executable configured adapters | Yes | Real host processes tested with simulated catalog data |
| Ordered escalation | Yes | Pre-approved primary / HTTP / auxiliary stages, trace and terminal denials |
| Legacy global and by-repository catalogs | Yes, through an approved GET host | No real authorized OpenAI host connected |
| Current scopes, pagination, versions and drafts | Yes, through an approved GET host | No real authorized OpenAI host connected |
| Native-session adapter | **Not shipped** | The implementation attempt was blocked by a tool safety control |
| Auxiliary Current onboarding and imported snapshots | Yes | Indirect/imported candidate evidence only |
| Optional MCP stdio server | Yes, official SDK | Real SDK client/server integration, strict schemas, progress, timeout and cancellation |
| Live OpenAI catalog acceptance | **Not completed** | Simulated tests do not establish real account authorization |
| Installation in ChatGPT Chat | Not performed | GitHub changes do not attach local MCP tools or install skills automatically |

The first requested task is therefore **partially complete**: executable adapters, skill workflows and escalation are implemented, but the actual native/Current live connections remain missing. The optional MCP server can be implemented and protocol-tested independently of those missing catalog hosts.

Core Python requirement: 3.9+. Optional MCP: Python 3.10+ with the declared SDK dependency, tested on Python 3.12. The canonical package has no root mcp.json, so MCP does not start implicitly.

## Delivery boundary

Work is kept on a dedicated implementation branch and reviewed separately from the stable v0.2.1 baseline. The GSM marketplace PR remains draft. No environment provisioning, Cloud task creation, token extraction or changes to the Bootstrap 0.6.6 three-gate workflow are part of this implementation.

## Evidence

Run `python -X utf8 tools/validate.py` for the dependency-free core and `python -X utf8 tools/validate.py --with-mcp` for the actual optional SDK profile. A missing SDK or skipped SDK tests cannot be reported as a complete MCP verification. Consult the validation report and CI for exact counts and revisions.

See ADAPTERS.md, MCP_OPTIONAL.md and PROJECT_MEMORY.md for resumable contracts and blockers.
