# Changelog

## 0.4.3 - Valid skill frontmatter

- Quote both skill description scalars so the advisory colon remains text, not a YAML mapping delimiter.
- Add a failing-first regression for JSON-quoted YAML scalars without adding runtime dependencies.
- Preserve all read-only discovery and optional fallback semantics; this fixes loading, not Cloud authorization.

## 0.4.2 - Optional Root-facing CloudRepo Direct advisory

- Added an optional structured advisory in both independently callable skills
  for explicit software-validation requests after bounded trusted observation
  cannot resolve a viable, verified Cloud executor. The advisory names
  `cloudrepo-environment-direct` and retains source, repository, full SHA,
  check-plan and decision evidence as unknown unless actually observed.
- Preserved Root preflight and authorization: `fallback_eligibility` defaults to
  `candidate_requires_root_preflight`; this package neither imports the other
  plugin nor executes CI, creates Cloud tasks/refs/PRs/workflows/environments,
  or changes permissions.
- Documented guards: incomplete catalogs, pending work, failed tests,
  inconclusive side effects, 401/403 and elapsed time alone do not prove Cloud
  absence, eligibility or failed startup; denial still stops Cloud escalation.

## 0.4.1 - Independent GitHub fallback and Current repository counterpart

- Implemented Current direct lookup by known immutable Configuration ID (`GET /v1/environment-configs/{configId}`) on approved Webcmd and Desktop HTTP transports. Safe URL-only single segment, strict 200 JSON/ID/account matching, explicit `point_verified` distinct from `catalog_complete`, and no catalog enumeration requirement for point-aware providers.
- `get_current_environment` now selects direct point reads within approved escalation stages. Missing/recoverable stages may proceed, but 401/403/429 and security denials remain terminal. Catalog-only providers preserve conservative fallback semantics; Legacy is unchanged.
- Current skill/manifest/MCP descriptions explicitly label the operational state **available, live access pending**: observed point and catalog Webcmd reads still return 401 JSON; anonymous HTTP returned a Cloudflare 403 HTML. No OpenAI fix date is asserted and historical IDs are never promoted to fresh current proof.


- Added optional, hash-pinned Webcmd as a native Current discovery escalation stage before BrowserAct, using a preexisting isolated browser and profile, the original backend GET, explicit user/workspace pagination, and owned-session cleanup. No account/profile creation, cookie/token inspection or challenge automation.
- Real reference-host v0.4.1 test: Webcmd 0.8.4 returned HTTP 401 JSON (unauthorized), no environment IDs, one terminal stage and confirmed cleanup with zero leftover sessions. This is working transport, NOT authenticated Current discovery. 401/403 still terminates Cloud escalation.

- GitHub inventory is now an independent read path: Current 401/403/rate-limit stops the Cloud provider but no longer suppresses an explicitly requested GitHub read.
- `find_current_environments(repository)` now returns `repository_counterpart` with `verified`, `candidate`, `not_found` or `not_verifiable` semantics.
- Current counterpart verification prioritizes `repository_id`, then an explicit canonical repository association. Environment-name equality remains a hint and never invents a Configuration ID.
- Inspection of installed Current Desktop 26.1007.2314.0 confirmed catalog/cache `repository_ids[]` plus detailed `repositories[].repository_id`/`repositoryId` forms; the parser now preserves those IDs and Current version ID/revision fields.
- Desktop Current published-config reads use client-observed `view=picker` first; only HTTP 400 falls back once to the same-surface standard list. Picker-only coverage is explicitly partial and cannot prove absence; the standard fallback retains all revisions (no GUI-only filtering). The Web proxy keeps its standard GET, and draft-inclusive queries skip picker.
- Fixed BrowserAct session ownership: `browser open` can report browser alias `workbench` or reuse the persistent browser. Only a session absent before open and verified after open in `session list` grants read/cleanup ownership. A failed open is reconciled and only owned sessions are closed. Live Web GET reached HTTP 403 with zero leftover sessions.
- No dedicated Current by-repository GET endpoint was validated or invented. Cloud denial still forbids alternate Cloud-surface/account retry, challenge bypass, provisioning or credential extraction.

## 0.4.0 — Live Legacy list and concrete Current web adapter

- Implemented the isolated screen-only native Legacy selector reader. Real IDs now return through CLI and optional MCP without reading private logs or credentials.
- Added version-gated parsing, completed-frame rendering, bounded read-only traversal and owned-process cleanup; native dependencies remain optional.
- Implemented full owned GitHub repository enumeration with native pagination and explicit optional correlation. Names remain candidates, not fabricated Cloud identities.
- Distinguished Desktop and web Current catalog surfaces and added the concrete BrowserAct web GET adapter using an existing isolated browser. The actual read returned HTTP 403; no successful Current list or draft coverage is claimed.
- Preserved the historical refusal of the different log/session reader, strict authorization stops, independent skills and optional MCP.
- Added native/parser/browser/catalog correlation regressions and live evidence documentation. No provisioning or new Cloud tasks/environments.

## 0.3.1 — Concrete GitHub verification and onboarding hints

- Added startup-opt-in native GitHub CLI repository verification with account continuity, fixed read-only routes and executable pinning.
- Wired verified repository IDs into find/resolve without converting GitHub access into Cloud existence.
- Added explicit Codex Tasks connector evidence import for Current onboarding; task IDs without Configuration IDs remain separate hints.
- Preserved hints across later missing consent/authorization failure, without permitting fallback around a denial.
- Verified the real repository lookup and current connector observations; complete live Cloud catalog access remains unresolved.

## 0.3.0 — Configured adapters and official SDK MCP profile

- Added executable operator-approved command adapters and startup-only configuration shared by CLI and MCP.
- Added explicit per-generation escalation, consent gating, audit traces, cancellation and whole-operation deadlines.
- Added Legacy repository-scoped GET matching and bounded catalog pagination; preserved Current drafts/versions and account continuity.
- Hardened MIME/schema/cursor/identity validation and kept indirect/snapshot evidence non-authoritative.
- Replaced the hand-written MCP protocol with official SDK lifecycle, strict schemas, read-only annotations, progress and cancellation; retained all eight tool names.
- Core remains dependency-free Python 3.9+. Optional MCP profile requires Python 3.10+ and pinned mcp==1.30.0.
- Replaced protocol self-tests with real SDK client/server integration tests; host catalogs are explicitly simulated.
- Native-session automation was blocked by a tool safety control and is not shipped. Real Legacy/Current OpenAI catalog acceptance remains pending; configured host contracts must not be presented as successful live discovery.

## 0.2.1 — Optional MCP adapter

- Removed root `mcp.json` automatic registration from the standard plugin.
- Preserved the tested local MCP server and eight tools behind `optional/mcp.json` for explicit opt-in.
- Kept both skills and the read-only CLI independent from server startup.
- Added regression checks and guidance for optional activation.

## 0.2.0 — Two independent discovery skills

- Replaced one Root-only skill with **legacy-discovery** and **current-discovery**.
- Added eight namespaced read-only MCP operations, four per Cloud generation.
- Removed the implicit all-types catalog and requirement for a Root dispatch step.
- Split Legacy/Current Python providers, APIs and test suites; shared code is cloud-agnostic.
- Lazy provider import for MCP and CLI, allowing Current to function independently if Legacy is retired.
- Preserved fail-closed evidence, account, repository and authorization semantics.
- Documented intentional pre-1.0 API/CLI/skill migration.

## 0.1.1 — Canonical CloudCodeX name

- Renamed package, repository and local skill identity.
- Corrected MCP stdio JSON-RPC transport framing.

## 0.1.0 — Initial read-only prototype

- Typed provider contracts, normalized catalog and resolver, local CLI/MCP, offline tests.
