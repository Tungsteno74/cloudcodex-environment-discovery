# Legacy discovery execution contract — v0.4.0

Only existing Legacy environments are read. No Current lookup, task creation, environment publishing or provisioning belongs to this skill.

## Native first stage

`kind: native_cli`, explicit `approved: true`, and `native` settings:

- `executable`: absolute reviewed native codex/codex.exe path, not a .cmd launcher.
- `sha256`: verified executable digest.
- `max_pages`: traversal bound, default50, range1–100.

The tested screen contract is Codex CLI 0.162.0. Native terminal dependencies are in `optional/requirements-native.txt`; live Windows checks used Python3.12. Core parsing/tests require no MCP.

The reader invokes ordinary `codex cloud` in an isolated non-repository working directory. It renders completed terminal frames, opens the environment selector using `o`, and enumerates rows with End/Home/PageDown. It never sends Enter/New Task/Apply. Only the rendered selector is parsed; files/logs/authentication stores/process memory are not read. It closes its own PTY and removes native-created temporary files unread.

This accepted screen-only implementation is **different from the previously refused log/session reader**. Preserve that historical refusal; do not revive the old mechanism.

## Result semantics

Each parsed row contains a real native ID, label and, only when explicitly displayed as a separate native hint, repository association. A label that happens to equal owner/repo does not establish an association.

The native result is `partial` with `catalog_complete=false`; `provider.coverage.visible_rows_complete` independently records full visible traversal. The UI supplies neither account-identity proof nor a guarantee of API-wide completeness/draft status. Empty/filtered/truncated or changed layouts must not become a verified empty account catalog.

## Authorized API host alternatives

`primary` is an alternative first-stage host, not an obligatory prerequisite for native CLI. A configured `http` host may follow a partial native result only when already authorized and not blocked by a terminal denial.

Allowed Legacy GETs:

- `/backend-api/wham/environments`.
- `/backend-api/wham/environments/by-repo/github/{owner}/{repo}`.

By-repository responses can prove association; names alone cannot. The plugin does not acquire tokens. Operator host commands and scripts are fixed/hash-pinned at startup; arbitrary commands and URLs are not tool inputs.

## GitHub correlation and optional MCP

`list --correlate-github` enumerates all owned GitHub repositories through native gh pagination and joins them to actual environment rows. ID/explicit association yields a verified join; names yield hints. GitHub success never manufactures missing Environment IDs or changes Cloud completeness.

MCP list/find/get/resolve names remain `list_legacy_environments`, `find_legacy_environments`, `get_legacy_environment`, `resolve_legacy_environment`. The list operation optionally accepts `correlate_github`. MCP is not required to run the CLI or skill.

Stop escalation on 401/403, rate limiting, identity/integrity conflicts, unapproved CONFIRM stages, cancellation and deadlines. No account switching, challenge bypass or provisioning fallback. Return candidates when coverage/identity is insufficient for automatic selection.

## Optional Root-facing software-validation advisory (v0.4.2)

Only for explicit software-validation intent, after bounded trusted observation
cannot resolve a viable, verified Cloud executor, the skill may return the
structured advisory `recommended_fallback: cloudrepo-environment-direct`. Its
`fallback_evidence` carries `source`, `repository`, `full_sha`, `check_plan` and
`decision_evidence` only when observed; every other value is `unknown`.
Default `fallback_eligibility` is `candidate_requires_root_preflight`; no
discovery outcome authorizes direct CI. Root alone reconciles Cloud task/CI
references and chooses/authorizes the independent
`cloudrepo-environment-direct:cloudrepo-environment-direct` skill.

Partial, empty or stale catalogs do not prove absence. Pending/active tasks or
CI, test failure, inconclusive remote side effects, denial (401/403), and slow
wall-clock alone do not establish eligibility or failed startup. A denial still
stops Cloud escalation and is never bypassed through another identity/provider.
The advisory never creates tasks, refs, PRs, workflows or environments, nor
changes permissions.
