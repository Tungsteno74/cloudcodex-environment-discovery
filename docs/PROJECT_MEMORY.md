# Project memory — implementation continuity

## Confirmed user decisions

- Canonical plugin/repository: **cloudcodex-environment-discovery**.
- Two directly invocable, independent skills: **legacy-discovery** and **current-discovery**. No mandatory Root dispatcher and no implicit mixed catalog.
- Keep providers and their tests isolated so Legacy can be retired without modifying Current's implementation.
- MCP is **optional**, never a prerequisite for skill/CLI use; no root mcp.json in source or release package.
- The Root must discover existing environments before creating any task. Runtime discovery is read-only and must not create environments, task probes or GitHub writes.
- Provisioning and the speculative Credential Broker are separate research tracks. CloudCodeX Windows Bootstrap 0.6.6 and its three E2E gates are unchanged by this project.
- Initial source authoring uses the user's local repository collection, with a dedicated GitHub repository and separate GSM marketplace reference.

## Historical source evidence, not current live state

The original 10 October 2026 note recorded successful Legacy catalog discovery with zero tasks, one Current configuration-catalog GET 200 and a later 403. Current draft coverage was not tested because the successful query used omitDraft=true. Codex Tasks.list_environments was not the same inventory as hosted Cloud configurations.

Those historical outcomes do not validate the new adapters against today's account/session. Cached environment/configuration IDs must be revalidated, not shipped as default results.

## Observed in the v0.3.0 implementation session

- Baseline v0.2.1 had independent skills and an optional handwritten MCP server, but default CLI/MCP factories created providers without executable configured channels.
- Implemented startup-only operator configuration, integrity-pinned read-only host commands, ordered escalation, per-stage diagnostics and explicit AUTO/CONFIRM handling without permission expansion.
- Implemented authorized-host HTTP catalog reads including Legacy by-repository association and Current user/workspace pagination, draft/version preservation and account continuity.
- Replaced the handwritten MCP protocol with the official MCP Python SDK. The optional stdio profile is tested with a real SDK client/server, including schema validation, progress, cancellation, deadline handling and all eight tools.
- Core CLI/providers remain Python 3.9+ and do not import MCP. The optional server requires Python 3.10+ and uses mcp==1.30.0.
- Host-process and SDK integration tests use **simulated catalog data**. They are not proof of real OpenAI catalog access.

## Verified blockage — do not reinterpret as an authentication result

A write request implementing direct native-session automation was denied by an OpenAI tool safety control. The proposed native adapter file was confirmed absent afterward. The implementation did not retry that code through another tool/channel.

This proves a tool-policy block on that attempt, **not** that the user's credentials are wrong, that the native catalog is empty, or that a future independently supported catalog interface cannot work. Preserve the event and its scope; do not turn it into a user decision to abandon native discovery forever.

## Still unresolved

1. A permitted, actually connected native Legacy catalog host is not supplied by this release.
2. A permitted, actually connected Current authenticated catalog host is not available in the tested setup.
3. Therefore the user's first task—complete live discovery using the previous findings—is not fully achieved merely because the configurable adapters pass tests.
4. The optional MCP protocol implementation can be complete and tested independently of those missing catalog connections. Starting the server does not grant new authorization.
5. Skills are not automatically installed into ChatGPT Chat by committing code, tagging a release or opening the GSM marketplace PR.
6. Public marketplace PR remains draft until live acceptance/distribution criteria are met. Do not overwrite these unresolved states with fixture successes.

## Resume procedure

Read AGENTS.md and the actual Git status first. Reuse the current repository and pending PRs; do not create duplicate projects or Cloud resources. Check the last validation report and SDK profile before broad testing. Investigate an independently supported, authorized catalog interface rather than routing around the recorded refusal. Once connected, test list/find/get/resolve read-only with real account/repository/scope evidence, then update this memory with observed results and provenance.
