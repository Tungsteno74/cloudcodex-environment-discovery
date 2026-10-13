# CloudCodeX Environment Discovery 0.4.2

Two independent read-only skills: legacy-discovery and current-discovery. No mandatory Root dispatcher, MCP server or provisioning operation.

Legacy now has a concrete isolated native CLI screen reader: two real IDs were returned repeatedly and through MCP on the reference Windows machine. Only CLI 0.162.0 is validated; optional native dependencies are in optional/requirements-native.txt. No private logs, credentials or primary-desktop input are accessed.

Current has a concrete same-origin browser-web GET adapter, but the actual catalog request returned HTTP 403. It stops; it does not solve challenges or claim an empty catalog. Desktop and web API surfaces are distinct.

CLI: runtime/cli.py legacy list --config <operator-config> --correlate-github. The optional owned GitHub catalog is joined by IDs/associations first, names as hints. Cloud completeness is separate from visible UI coverage and GitHub completeness.

Core Python3.9+, native profile tested on Python3.12, optional MCP Python3.10+ with optional/requirements-mcp.txt. No root mcp.json is shipped. The empty example configuration does not contain credentials or automatically connect personal accounts.

Source and operation guide: https://github.com/Tungsteno74/cloudcodex-environment-discovery/tree/v0.4.0

Current repository lookup remains useful after a Cloud 401/403: an explicitly configured GitHub source can still verify repository identity and return candidates. `find_current_environments` marks a counterpart verified only from an observed configuration's repository ID or explicit association; names remain hints. GitHub cannot manufacture a Configuration ID.


## Current v0.4.1: point GET implemented, awaiting live authorization

Current `get` attempts the official Desktop-client-observed `GET /v1/environment-configs/{configId}` via an explicitly authorized Webcmd or Desktop HTTP stage. Catalog-only stages remain available where configured. Exact ID is validated and response ID/account checked; successful point proof is distinct from catalog completeness. Real Current requests are still returning 401 JSON (Webcmd) or 403 HTML (anonymous HTTP). The Current skill stays installed/usable, but live environment identification is on hold pending supported access. Do not equate authorization failure to an empty catalog, claim an OpenAI fix schedule or retry through another identity. Use `runtime/cli.py current get --environment-id <ID> --config <operator-config>`. Legacy remains unaffected.

## v0.4.2: optional Root advisory only

For explicit software-validation intent, either independent skill may return a
structured recommendation for `cloudrepo-environment-direct` only after bounded
trusted observation cannot resolve a viable, verified Cloud executor. Evidence
fields (`source`, `repository`, `full_sha`, `check_plan`, `decision_evidence`)
remain `unknown` unless observed. The default eligibility is
`candidate_requires_root_preflight`; Root independently reconciles Cloud/CI
references and decides whether to authorize direct CI. This plugin never imports
the other plugin, executes CI, or creates tasks, refs, PRs, workflows,
environments or permissions. Empty/partial/stale catalogs, pending work, test
failures, inconclusive effects, 401/403 and elapsed time alone are not proof of
Cloud absence, eligibility or failed startup.
