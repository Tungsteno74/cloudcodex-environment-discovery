---
name: current-discovery
description: Read-only Current Cloud catalog and point-by-Configuration-ID lookup; functionality available but live catalog/detail currently blocked by API authorization (401/403) pending supported OpenAI access. Never claim a successful empty catalog.
---

# Current discovery — direct Root entry point

Use independently of Legacy, any running Child, Windows Bootstrap or a mandatory MCP server. The target is existing configurations, never task/environment creation or publication. Read `references/current-contract.md`.

## Operational status — available, awaiting authorized Current access

**ON HOLD FOR LIVE CURRENT DATA, NOT DISABLED.** The skill, CLI and optional MCP tools are usable, but live Current catalog and single-ID GET have not returned authorized environment records on the reference machines. Last verified requests: Webcmd **HTTP 401 JSON**, anonymous HTTP **403 HTML Cloudflare challenge**. This is an observed access limitation, not proof that an OpenAI fix has been scheduled or that any environment is absent. Legacy discovery is independently operational. Indirect Current onboarding and GitHub candidates may still be reported, but never as current verified Configuration IDs.

For a known immutable Current Configuration ID use the single-item GET path first. 401/403/429 stop Current escalation, including attempts via another account/surface. A supported authorized transport must become available before this skill can validate Current IDs live.

## Select an existing authorized source

1. Determine requested account, repository/name/ID, user/workspace scopes and draft inclusion. Reuse current scoped consent only.
2. Prefer a supported, already-authorized Current catalog connector when present. Codex Tasks.list_environments is not the complete hosted catalog.
3. When configured, the optional Webcmd adapter uses the original Current backend through the operator's already installed, hash-pinned Webcmd CLI, preexisting isolated browser runtime and existing profile. It runs ordinary JavaScript/GET and closes only the temporary session it created. It cannot create/import a browser profile, inspect cookies or tokens, automate a challenge or acquire Codex credentials. Read references/webcmd-current.md for configuration and the live result.
4. The existing browser_web adapter remains available for a separately approved isolated BrowserAct Chrome browser. It uses the distinct Web route, retains existing ownership checks and never acts on the main user browser.
5. An approved primary JSON host is an alternative first stage, followed where appropriate by Webcmd. A separately approved http host can query the selected API surface; none inherits Codex credentials automatically.

## Execute without MCP

```text
python <plugin-root>/runtime/cli.py current doctor --config <operator-config.json>
python <plugin-root>/runtime/cli.py current list --config <operator-config.json> --pretty
python <plugin-root>/runtime/cli.py current list --config <operator-config.json> --include-drafts --pretty
python <plugin-root>/runtime/cli.py current list --config <operator-config.json> --correlate-github --pretty
python <plugin-root>/runtime/cli.py current find --repository owner/repo --config <operator-config.json> --pretty
python <plugin-root>/runtime/cli.py current get --environment-id <known-configId> --config <operator-config.json> --pretty
```

`doctor` verifies setup, not authorization. BrowserAct's reference-machine Web route returned **403 HTML**. The newly integrated Webcmd 0.8.4 adapter reached the original Current backend with **401 JSON**, without an authorized Current catalog. Neither response is a successful empty catalog. Legacy's working native selector does not supply Current configurations.

## Keep web and Desktop contracts distinct

- Desktop: `https://codex-cloud-backend.chatgpt.com/v1/environment-configs`.
- Web: `https://chatgpt.com/api/codex-cloud/v1/environment-configs`.

`api_surface` is an operator configuration choice, never an automatic retry after denial. The dedicated BrowserAct adapter uses the web surface only. Webcmd uses the original Desktop backend URL with the standard GET, without the Desktop-only view=picker selector. The earlier blanket assertion that the web prefix was wrong was too broad; matching the Desktop implementation alone did not invalidate the separate web route.

For published configurations on the **Desktop surface**, the installed client builds its saved-config catalog with `view=picker`, `omitDraft=true`, both `user` and `workspace` scopes, and bounded cursors. The plugin follows this sequence only on Desktop, and falls back to the standard list on the same identity/surface **only when picker returns HTTP 400**. The separate Web proxy retains its observed standard GET. 401/403/rate-limit never trigger fallback; explicit draft discovery skips picker because the observed picker contract omits drafts. **Picker-only results are partial, even when all picker pages were fetched:** they cannot prove the absence of an environment. When HTTP 400 triggers the standard-list fallback, preserve all returned revisions rather than silently applying the GUI's saved-config filter.

Explicit `scope`, `limit`, `cursor` and `omitDraft` are required. `omitDraft=true` excludes drafts; it does not prove no drafts exist. Versions/drafts sharing an ID must not be silently collapsed. Successful live retrieval of unpublished drafts remains unverified.

## Direct single-ID Current lookup

The installed Desktop client uses `GET https://codex-cloud-backend.chatgpt.com/v1/environment-configs/{configId}`. Current `get_current_environment(environment_id)` tries the exact-ID GET on an approved Desktop HTTP or Webcmd transport instead of first enumerating the catalog. Catalog-only stages retain their existing read behavior when they do not implement the point contract. BrowserAct's unverified Web point URL is **not** assumed to exist. IDs are restricted to safe opaque single segments; no lookup by arbitrary URL, repository name or guessed draft ID is performed.

A valid HTTP 200 JSON with matching immutable ID and adequate account provenance can set `point_verified=true` and `status=found` while **`catalog_complete=false`**. HTTP 401/403 are terminal, 404 without full trusted coverage is not a claim of global absence. There is no successful authorized Current point GET to date; simulated regression tests do not change that. `list/find/resolve` continue to require appropriate Current catalog evidence.

## Escalation and indirect evidence

Approved primary → optional Webcmd → optional browser_web → approved http → approved onboarding → supplied snapshot. Not all stages need to be present. AUTO cannot grant consent; CONFIRM returns approval_required when needed. **401/403, rate limiting, account/integrity mismatch, security challenge, cancellation or timeout stop the sequence.** Do not switch identities, extract tokens or attempt provisioning to get around a read failure.

If reached without an earlier denial, onboarding can use authorized Codex Tasks list/read metadata through a host or a supplied sanitized export. Missing Configuration IDs remain `provider.hints`, not invented environments. Ignore prose, task IDs as environment IDs, alleged publication status and title-derived associations. Snapshots are imported candidates only.

Optional GitHub discovery enumerates the owned repository catalog independently, then uses explicit IDs/associations before name candidates. A Cloud 401/403/rate-limit still stops Cloud escalation, but does **not** cancel this separately authorized GitHub read when it was explicitly requested. GitHub success never changes the Cloud provider status, never creates a missing Cloud record and never changes Cloud completeness.

Installed Current Desktop 26.1007.2314.0 exposes repository identity in two read shapes: cached/catalog rows carry `repository_ids[]`, while detailed configurations carry `repositories[].repository_id` (normalized client-side as `repositoryId`). The settings UI reads its local catalog, invokes a separate `refreshCatalog()`, then rereads the catalog; search is performed over those catalog rows. The plugin normalizes all of these repository-ID forms. This is evidence for repository-to-configuration matching, not permission to read Desktop private state or bypass a denied refresh.

For `find_current_environments(repository)`, pass either GitHub `owner/repo` or numeric repository ID. The result includes `repository_counterpart`: `verified` only when an observed Current configuration carries that repository ID or explicit association; `candidate` when only the configuration/environment name matches; `not_found` only from a complete Cloud catalog; otherwise `not_verifiable`. The installed Current client also models configurations with `repositories[].repository_id`, which is why ID matching is authoritative. There is no validated Current by-repo endpoint, so do not invent one.

## Result and optional MCP

Return actual IDs, account/scope when observed, configuration state, evidence/time, completeness and per-stage outcomes. Resolve only one fresh live verified candidate with complete requested coverage. Return ambiguity or the precise blocker otherwise.

When already connected, optional MCP tools are list_current_environments, find_current_environments, get_current_environment and resolve_current_environment. The list tool supports correlate_github. MCP does not authenticate the catalog and need not be enabled to run this skill. Do not invoke Legacy implicitly.
