# Contributor instructions — Codex Cloud Environment Discovery

This repository is the independent lifecycle boundary for the read-only Codex Cloud environment discovery plugin. Its family marketplace is `Tungsteno74/cloudcodex-helpers-marketplace`; do not embed a marketplace manifest here.

## Non-negotiable boundaries
- Discovery runs at the ChatGPT Root level, **before any cloud task exists**. Do not require a running Child/task or bootstrap invocation.
- Never create cloud tasks, configure/publish environments, mutate GitHub or adjust authentication in list/find/get/resolve.
- Do not access, parse or copy `~/.codex/auth.json`, Chrome cookies, browser profiles, stored credentials or any secrets. Do not attempt to bypass 401, 403 or security challenges.
- Legacy Cloud and current-generation Cloud are independent providers. `Codex Tasks.list_environments` is NOT an exhaustive Cloud environment list.
- Empty/stale/partial/unauthorized/unavailable are distinct outcomes. Return uncertainty explicitly; do not silently declare absence.
- Use trusted live evidence for IDs. Cache matches, task titles and repository names are hints, not authoritative identities.
- Keep this plugin independent of `cloudcodex-windows-bootstrap` version 0.6.6 and of provisioning/credential-broker projects. Integrate via an optional descriptor only.

## Engineering guidelines
- Apply Clean Code, SOLID pragmatically, explicit interfaces, stable types and dependency injection for provider/transport adapters.
- Python 3.9+ standard library preferred; PEP 8, type hints, small testable units, no network at import time.
- Build portable Agent Plugins 1.0 `plugin.json` under `plugins/cloudcodex-environment-discovery/`; include two independently discoverable provider skills (`legacy-discovery` and `current-discovery`) without a mandatory Root dispatcher skill. Preserve the compatibility overlay.
- Keep MCP optional: no root `plugins/cloudcodex-environment-discovery/mcp.json` in source or release ZIP. The opt-in template belongs under `optional/mcp.json`; neither skill nor CLI may require server startup.
- Any MCP runtime/tool must run read-only, expose stable structured data and fail closed. Never print credentials or raw HTTP response bodies on error.
- Include offline regression tests, repository validator, CI and package instructions. Clearly document limitations and missing authenticated Current/Legacy capabilities.
- Do not silently turn absence of an interactive TTY/authorized connector into an empty catalog.

## Workflow
- Perform repository-first inspection; preserve user changes.
- Implement only the requested plugin and tests. No automatic GitHub repo creation, pushes, marketplace edits or plugin account publication from a coding agent: the parent Root owns these effects.
- Run relevant tests and package validation. Return compact status, changed paths and verified limitations.

## v0.3.0 continuation
- Read docs/PROJECT_MEMORY.md before significant changes; retain the distinction between historical evidence, simulated tests and live acceptance.
- The optional MCP server uses the official Python SDK. Do not reintroduce a custom JSON-RPC lifecycle or require MCP for CLI/skills.
- Operator host commands require approval and integrity pins; tool arguments must never select executables, tokens, arbitrary URLs or configuration files.
- Run the core test profile first, then tools/validate.py --with-mcp with its declared optional dependencies. Fixture success is not Cloud authorization.
- The native-session implementation attempt was blocked and did not land. Do not reroute that same attempt through another tool/channel.

## v0.4.0 verified read paths
- Preserve the successful screen-only native CLI reader. It is ordinary isolated terminal I/O, not the previously blocked private log/session reader; do not conflate those mechanisms or remove their historical distinction.
- Do not add Enter/New Task/Apply, credential reads or log parsing to native selector navigation. Keep visible-row coverage separate from account-wide completeness.
- Keep Current browser reads limited to an existing isolated Chrome browser and fixed GETs. No profile imports, primary-browser control, proxy changes, dialog auto-approval or challenge solving. A 403 stops the sequence.
- Repository name equality is a candidate join. Never generate environment IDs from GitHub names or promote GitHub catalog completeness to Cloud completeness.


## v0.4.1 point-by-ID Current (authorized access pending)
- A known, validated Configuration ID may be checked through the exact
  Desktop GET /v1/environment-configs/{configId} on an existing approved
  read-only transport; do not build by-name, by-repo or unobserved draft URLs.
- A 200 matching JSON verifies that single ID only (point_verified), never
  the complete catalog; 401/403 and authorization/security challenges stop
  Cloud escalation. Catalog-only configured stages remain read-only.
- Current's skill and tool descriptions must acknowledge that live Current
  API reads currently return 401 JSON/403 challenge, while remaining
  available without claiming a scheduled OpenAI fix. Legacy remains operational.
- Do not import identities or browser profiles, read credentials, create
  environments, or mutate the plugin's account installation while paused.

## v0.4.1 optional Webcmd constraints
- Current Webcmd is only a separately approved, read-only source. It uses an
  already installed/pinned Webcmd CLI, preexisting isolated browser and
  existing profile, not credential extraction or profile bootstrap.
- Keep the URL fixed to the original Current backend, preserve scope/draft
  pagination and stop at the first 401/403/rate-limit. Do not use another
  browser or account as a fallback after a denial.
- Every transient Webcmd session must be identified in the before/after
  inventory and cleaned without touching user sessions. A missing profile,
  malformed catalog, ambiguous ownership or cleanup failure must not be
  converted into a successful complete result.
