# Current repository discovery - v0.4.1

## Relationship to the 10 October architecture note

The implementation remains based on `Codex_Cloud_Environment_Discovery_Nota_Architetturale_plugin.md`, especially sections 2 and 3.

Source-derived decisions retained by the plugin:

- Legacy discovery is independent from task enumeration and prefers the native Codex catalog.
- Current discovery targets `environment-configs` with explicit user/workspace coverage, pagination and draft semantics.
- Codex Tasks is auxiliary evidence, not an exhaustive environment catalog.
- A Current 401/403 terminates that Cloud provider path; no account switching, credential extraction, challenge bypass or provisioning is allowed.
- GitHub is an independent repository-evidence source. Repository ID or an explicit provider association is stronger than name equality; GitHub by itself must not fabricate a Cloud environment or Configuration ID.

The v0.4.0 implementation diverged from that last rule in one place: `--correlate-github` returned before reading GitHub whenever Current ended with 401/403/rate-limit. v0.4.1 corrects the orchestration bug. The denied Current provider remains denied, while the separately authorized GitHub inventory may still complete.

## Newly verified Current Desktop contract

This section is based on direct inspection of the installed Codex Desktop `26.1007.2314.0`, not on assumptions added to the original note.

Current configuration data exposes repository identity in multiple compatible read shapes:

```text
catalog/cache row:
  { id, name, repository_ids: [...] }

detailed configuration:
  { id, name, repositories: [{ repository_id, ref }], ... }

client-normalized detailed form:
  { ..., repositories: [{ repositoryId, ref }] }
```

The installed client also exposes these logical operations:

```text
environmentConfigs.catalog({accountId, userId})
environmentConfigs.refreshCatalog({accountId, userId})
environmentConfigs.request({
    accountId,
    userId,
    configId,
    method: "GET"
})
```

The settings flow reads `catalog()`, performs `refreshCatalog()`, and reads `catalog()` again. A detailed GET by known `configId` returns the configuration and its explicit repository associations.

The plugin does **not** read the Desktop application's private cache or authentication state. These observations define compatible data contracts for approved Current providers.

No dedicated Current equivalent of Legacy's `/environments/by-repo/...` route was observed or validated. The plugin therefore does not invent one.

## Repository counterpart mechanism

A repository-centric lookup starts from a GitHub `owner/repo` or numeric repository ID.

When an authorized GitHub resolver is configured, the plugin first verifies the repository identity and obtains its canonical name and immutable GitHub repository ID. Current evidence is then classified in this order:

1. Matching explicit `repository_id` / `repositoryId` / `repository_ids[]` -> verified association when the Current observation is fresh and live.
2. Matching explicit canonical repository association -> verified association when fresh/live and not contradicted by another repository ID.
3. Configuration/environment name equal to repository basename or `owner/repo` -> candidate only.
4. No match in a complete Current catalog -> verified absence.
5. No match while Current is denied, partial or stale -> not verifiable.

The parser accepts the Current snake_case and camelCase shapes observed in the installed client:

- `repositories[].repository_id`
- `repositories[].repositoryId`
- `repository_ids[]`
- `repositoryIds[]`

It also preserves observed `version_id` / `versionId` and `version_revision` / `versionRevision` values.

A name match never creates a Configuration ID.

## Independent GitHub semantics after Cloud denial

A Current 401/403/rate-limit remains terminal for that Current Cloud provider and is reported unchanged.

If the caller explicitly requested GitHub correlation and GitHub is independently configured and authorized, the plugin may still enumerate repositories because this is not a retry of the denied Cloud request.

Therefore a denied Current catalog can legitimately return:

```text
cloud status: forbidden
Cloud Configuration ID: not verified by this attempt
GitHub repository inventory: available
repository candidate names: available as hints
repository_counterpart: not_verifiable
```

Cancellation and the whole-operation timeout remain global stops and prevent the independent read from starting.

## What is verified

Covered by implementation and tests:

- Current Cloud denial does not suppress explicitly requested independent GitHub discovery.
- Timeout/cancellation still stops subsequent reads.
- Repository IDs survive all Current catalog shapes observed in the installed Desktop client.
- Repository-ID evidence outranks canonical-name evidence; both outrank environment-name hints.
- Imported or stale explicit associations remain candidates until refreshed.
- A complete Current catalog may prove absence; a denied/partial catalog may not.
- Malformed repository-ID envelopes fail closed.

## What remains open

Not established by the source note or the current live machine:

- a presently authorized successful Current catalog refresh on the reference machine;
- live `omitDraft=false` output containing an unpublished draft;
- a supported Root-facing connector exposing the Desktop Current catalog without reading private client state.

Provisioning, publication and environment creation remain outside this plugin.


## BrowserAct owned-session correction and live acceptance

The previous browser adapter assumed `browser open` must return the configured numeric browser ID and `reused=false`. A controlled BrowserAct observation on 12 October 2026 contradicted that assumption: the open response contained `browser_id="workbench"` while `session list` correctly reported the intended `chrome_local_...` ID for the freshly created named session. The browser `reused` flag is not an ownership assertion for the named session.

The updated adapter now verifies session absence before opening, checks exact session name, browser ID and browser type via `session list` after opening, and reconciles any created session in `finally`. It closes only the newly verified named session, never the persistent browser or another user's session. A lost/invalid open response still triggers ownership-aware cleanup.

The web and Desktop contracts are distinct: `view=picker` was observed in the installed **Desktop** main process; the **Web** BrowserAct transport continues using its already observed standard GET. For Desktop's published-config path, the only automatic query-shape fallback is from picker to standard list after HTTP 400 on the same authorized surface. HTTP 401/403/429 never trigger that retry.

A new live Current repository-centric read used the verified GitHub ID `1408634524`. The Web GET was actually attempted and returned HTTP 403; the provider reported `reason=http_403`, `catalog_complete=false`, and the repository counterpart remained `not_verifiable`. The adapter reported `session_cleanup_confirmed=true`, and a separate BrowserAct session inventory showed zero remaining `cloudcodex-catalog-*` sessions. No challenge handling, token/profile access or provisioning was performed.


## Catalog completeness boundary for the Desktop picker

The Desktop's picker is a **selection view**, not guaranteed to be the full hosted Current catalog. Even a successful, fully paginated `view=picker` read therefore produces observed Configuration IDs but is reported as `status=partial`, `catalog_complete=false`, `provider.coverage.picker_view_only=true`. A missing row from that view does not prove absence.

When the picker returns HTTP 400, the plugin retries the **standard list on the same Desktop surface** and preserves every returned revision. The Desktop GUI filters older revisions for its saved-config selection UI; the Discovery plugin deliberately does not copy that filter because the goal is to discover all existing environments. A complete, authoritative standard response can establish completeness for the requested scopes/draft policy.

The separate Web GET does not use `view=picker`, because that query was observed only on the installed Desktop route.
