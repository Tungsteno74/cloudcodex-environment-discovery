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
- Build portable Agent Plugins 1.0 `plugin.json` under `plugins/codex-cloud-environment-discovery/`; include independently discoverable Root skill and compatibility overlay if useful.
- Any MCP runtime/tool must run read-only, expose stable structured data and fail closed. Never print credentials or raw HTTP response bodies on error.
- Include offline regression tests, repository validator, CI and package instructions. Clearly document limitations and missing authenticated Current/Legacy capabilities.
- Do not silently turn absence of an interactive TTY/authorized connector into an empty catalog.

## Workflow
- Perform repository-first inspection; preserve user changes.
- Implement only the requested plugin and tests. No automatic GitHub repo creation, pushes, marketplace edits or plugin account publication from a coding agent: the parent Root owns these effects.
- Run relevant tests and package validation. Return compact status, changed paths and verified limitations.
