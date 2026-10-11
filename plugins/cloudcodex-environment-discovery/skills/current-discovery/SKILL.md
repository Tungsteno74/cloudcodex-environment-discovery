---
name: current-discovery
description: Read existing CURRENT-GENERATION Codex Cloud configurations, IDs, drafts and versions. Use the dedicated existing-browser web GET adapter or approved API host with explicit scope, pagination and authorization stops. Not for Legacy or provisioning.
---

# Current discovery — direct Root entry point

Use independently of Legacy, any running Child, Windows Bootstrap or a mandatory MCP server. The target is existing configurations, never task/environment creation or publication. Read `references/current-contract.md`.

## Select an existing authorized source

1. Determine requested account, repository/name/ID, user/workspace scopes and draft inclusion. Reuse current scoped consent only.
2. Prefer a supported, already-authorized Current catalog connector when present. Codex Tasks.list_environments is not the complete hosted catalog.
3. The plugin also implements `browser_web`: the operator selects an existing isolated BrowserAct `chrome` browser and hash-pinned native CLI. It opens a unique owned session, issues a fixed same-origin catalog GET and closes that session. No profile creation/import, cookie/token inspection, proxy changes, auto-dialog acceptance or challenge solving exists in this adapter.
4. An approved `primary` JSON host is an alternative first stage. An independently approved `http` host can query the explicitly selected API surface. It does not inherit credentials magically.

## Execute without MCP

```text
python <plugin-root>/runtime/cli.py current doctor --config <operator-config.json>
python <plugin-root>/runtime/cli.py current list --config <operator-config.json> --pretty
python <plugin-root>/runtime/cli.py current list --config <operator-config.json> --include-drafts --pretty
python <plugin-root>/runtime/cli.py current list --config <operator-config.json> --correlate-github --pretty
```

`doctor` verifies setup, not authorization. The reference-machine browser route has been invoked and returned **403 HTML**, so its current list is blocked. Do not call that outcome a successful empty catalog. Legacy's working native selector does not supply Current configurations.

## Keep web and Desktop contracts distinct

- Desktop: `https://codex-cloud-backend.chatgpt.com/v1/environment-configs`.
- Web: `https://chatgpt.com/api/codex-cloud/v1/environment-configs`.

`api_surface` is an operator configuration choice, never an automatic retry after denial. The dedicated browser adapter uses the web surface only. The earlier blanket assertion that the web prefix was wrong was too broad; matching the Desktop implementation alone did not invalidate the separate web route.

Explicit `scope`, `limit`, `cursor` and `omitDraft` are required. `omitDraft=true` excludes drafts; it does not prove no drafts exist. Versions/drafts sharing an ID must not be silently collapsed. Successful live retrieval of unpublished drafts remains unverified.

## Escalation and indirect evidence

`browser_web` or `primary` → approved `http` → approved `onboarding` → supplied `snapshot`. Not all stages need to be present. AUTO cannot grant consent; CONFIRM returns approval_required when needed. **401/403, rate limiting, account/integrity mismatch, security challenge, cancellation or timeout stop the sequence.** Do not switch identities, extract tokens or attempt provisioning to get around a read failure.

If reached without an earlier denial, onboarding can use authorized Codex Tasks list/read metadata through a host or a supplied sanitized export. Missing Configuration IDs remain `provider.hints`, not invented environments. Ignore prose, task IDs as environment IDs, alleged publication status and title-derived associations. Snapshots are imported candidates only.

Optional GitHub correlation enumerates the owned repository catalog, then uses explicit IDs/associations before name candidates. It never creates a missing Cloud record or changes catalog completeness. A source failure must not be concealed by a successful GitHub lookup.

## Result and optional MCP

Return actual IDs, account/scope when observed, configuration state, evidence/time, completeness and per-stage outcomes. Resolve only one fresh live verified candidate with complete requested coverage. Return ambiguity or the precise blocker otherwise.

When already connected, optional MCP tools are list_current_environments, find_current_environments, get_current_environment and resolve_current_environment. The list tool supports correlate_github. MCP does not authenticate the catalog and need not be enabled to run this skill. Do not invoke Legacy implicitly.
