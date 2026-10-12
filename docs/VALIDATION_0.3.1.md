# Validation report — v0.3.1 preview

Date: 11 October 2026. Baseline: v0.3.0 commit `d74ea41a547c3373a2fa6df8d822ac51b1795932`. Continuation uses the same implementation branch and source draft PR #1; stable main remains v0.2.1.

## Automated local profiles actually executed

| Profile | Interpreter | Passed | Skipped |
|---|---|---:|---:|
| Dependency-free core | Python 3.9.13 | 170 | 0 |
| Core plus official MCP SDK stdio integration | Python 3.12.15 | 183 | 0 |

Core suite breakdown: common 49, Legacy 19, Current 22, configured adapters 39, concrete sources/evidence 29, interface/package 12. SDK integration adds 13 tests, including an actual stdio client/server request carrying non-resolvable onboarding hints.

The 29 new source/evidence regressions cover fixed native GitHub GET arguments, account continuity, denied reads, startup opt-in/pinning, numeric repository identity, canonical-name routing, name/ID conflicts, and preservation of task hints without Configuration IDs. They also verify that denied earlier stages prevent auxiliary reads and that hints survive a later consent or identity failure.

## Separately verified operational reads

- Native GitHub adapter: the real repository `Tungsteno74/cloudcodex-windows-bootstrap-e2e-cloud-auto` was verified as repository ID `1408634524`; first complete lookup took 1.329 seconds. The adapter did not extract or print credentials.
- The same configured service correctly returned Cloud `not_verifiable`, `catalog_complete=false`, `selected=null`: repository access alone did not become a Cloud environment.
- Connected Codex Tasks: the two relevant onboarding metadata records were listed, and one task was read. No structured Configuration ID appeared in the returned metadata.
- Passing those metadata records through the Current evidence stage produced **2 hints, 0 environment records, no selection**. Only an ephemeral sanitized export was used; it was removed after the check. This does not claim a Python-native Codex Tasks connector exists.
- Installed Codex CLI 0.162.0 generated 447 protocol schemas. Its environment/info and environment/status require an existing ID; environment/add is a mutation. No hosted catalog-list operation was identified in that generated surface.

## Not verified or not performed

Real authenticated Legacy and Current catalog access remains unresolved. No native-session bypass, credential extraction, environment/task creation, or modification of the Bootstrap three-gate workflow was performed. Test fixtures and imported task metadata cannot establish live catalog completeness.

Both skills remain independent; MCP remains optional and uses the official SDK. There is no root mcp.json and no installation into ChatGPT Chat is implied by this source update.

Remote CI results must be associated with the exact commit that includes this report. The local test results above are observations, not predictions of a future CI run.
