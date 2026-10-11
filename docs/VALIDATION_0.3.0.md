# Validation report — v0.3.0 preview

Date: 11 October 2026. Baseline: v0.2.1, commit `5cde0d80e01551a05fc9742c586adfcfd6e49f69`. Changes are developed on `feature/live-adapters-mcp-v030` rather than silently promoting live-discovery claims to main.

## Local tests actually executed

| Profile | Interpreter | Tests passed | Skipped |
|---|---|---:|---:|
| Core | Python 3.9.13 | 141 | 0 |
| Core plus official MCP SDK | Python 3.12.15 | 153 | 0 |

Suite breakdown: common 49, Legacy 19, Current 22, configured adapters 39, interface/package 12, SDK stdio integration 12.

The SDK integration tests launch the real server process and use the official MCP client. They cover initialization and negotiated protocol, all eight tool calls, typed input validation, structured results, read-only annotations, unavailable/denied/empty catalog behavior, progress notifications, operation deadlines and cancellation while keeping the server usable.

The adapter tests launch real child processes but supply **simulated catalog responses**. They cover command integrity pins, rejected destinations/arguments, bounded output, secret-environment isolation, failure sanitization, timeout/cancellation, explicit scopes/pagination, primary-to-HTTP escalation, terminal 401/403/rate limits, account continuity, typed repository associations, multiple repositories and preservation of versions/drafts.

The dependency-free core continues to run without MCP installed. The SDK profile requires its explicitly declared optional dependency; a missing SDK or skipped integration tests cause that profile to fail rather than appear green.

## Additional checks

- Ruff F-category lint checks passed for changed/new Python files; unused imports were removed.
- Git diff whitespace checks passed.
- Exactly two skills remain, with no mandatory Root dispatcher.
- No root mcp.json is present; MCP remains optional.
- No credential files, native-session reader, Cloud IDs as default results, or simulated test hosts are included as production connections.
- Both default `legacy doctor` and `current doctor` correctly report `configured=false` and `live_tested=false`.

## What this does not prove

These tests do **not** demonstrate authenticated access to OpenAI's real Legacy or Current catalogs. The direct native-session implementation attempt was blocked by a tool safety control and its file was confirmed absent. An authorized Current catalog host was not available either. Neither task/environment creation nor provisioning was used as a substitute.

The original user target of fully operational live discovery therefore remains open, even though the configured adapter layer, escalation and optional MCP profile are implemented and tested.

GitHub Actions is configured to run the core on Python 3.9/3.12/3.13 and the optional SDK profile on Python 3.12 for Linux and Windows. Remote CI results must be checked against the exact branch/PR revision; local results above are not a prediction of CI success.
