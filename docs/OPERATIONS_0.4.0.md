# Discovery-only operation — v0.4.0

## Scope and real outcomes

This plugin reads existing Legacy/Current configurations. It contains no environment creation, publishing, Cloud-task probes, Credential Broker or other provisioning operation. Reading an existing environment whose name contains `provisioning-test` is not a new provisioning action.

The Windows reference machine now has a working **Legacy native list**. The same source was exercised through the Python CLI and through the optional official MCP SDK server. The native screen returned two existing IDs repeatedly. The Current browser adapter issued its actual catalog GET, received HTTP 403 and stopped before the second scope; no challenge was solved and no account/session was changed.

## Ready-to-run command on the reference machine

From `D:\Repos\personali\cloudcodex-environment-discovery` in PowerShell:

```powershell
& .\.venv\Scripts\python.exe -X utf8 .\plugins\cloudcodex-environment-discovery\runtime\cli.py legacy list --config "$env:LOCALAPPDATA\CloudCodeX\environment-discovery\discovery-readonly.local.json" --correlate-github --pretty
```

Use `current list` to invoke the already-configured Current web read. Its last observed result was `forbidden/http_403`; do not repeatedly invoke it to bypass the same denial.

The machine-local configuration was created outside the repository. It stores the reviewed executable paths, SHA-256 pins, existing independent BrowserAct browser ID, explicit read approval and expected GitHub login. It does **not** contain token/cookie values. No global environment variable or default Codex configuration was changed.

## Setup on another authorized machine

Core: Python 3.9+. Optional native terminal profile: install `optional/requirements-native.txt` with a compatible interpreter; Python 3.12 was tested. Optional MCP profile: Python 3.10+ and `optional/requirements-mcp.txt`. Neither optional dependency is required merely to load the skills.

Find the actual native `codex` executable, rather than treating a `.cmd`/PowerShell launcher as a binary. The npm Windows package tested here places it under `vendor/x86_64-pc-windows-msvc/bin/codex.exe`. Review the executable and pin its SHA-256. CLI 0.162.0 is the only screen contract currently accepted. Do not silently enable untested versions.

Example structure, with placeholders replaced by the operator:

```json
{
  "schema_version": 1,
  "mode": "AUTO",
  "timeout": 30,
  "domains": {
    "legacy": {
      "stages": [{
        "kind": "native_cli",
        "approved": true,
        "native": {"executable": "<absolute native Codex path>", "sha256": "<verified digest>", "max_pages": 50}
      }]
    },
    "current": {
      "api_surface": "web",
      "scopes": ["user", "workspace"],
      "stages": [{
        "kind": "browser_web",
        "approved": true,
        "browser": {"executable": "<absolute browser-act path>", "sha256": "<verified digest>", "browser_id": "<existing chrome_local_ID>", "timeout": 15}
      }]
    }
  },
  "github": {"enabled": false}
}
```

`native_cli` and `primary` are alternative first stages for Legacy. `browser_web` and `primary` are alternative first stages for Current. The native options do not introduce arbitrary commands into tool arguments. Existing approved HTTP/auxiliary/snapshot stages retain their ordering. No stage can bypass an earlier explicit denial.

## Legacy screen-only adapter

The implementation is split into:

- `legacy/native_cli.py`: pinned native process, version gate and bounded enumeration.
- `legacy/terminal.py`: isolated PTY, streaming terminal rendering and owned-process cleanup.
- `legacy/selector.py`: parsing of the visible native selector only.

The reader waits for completed terminal frames rather than parsing a half-drawn screen. It opens the standard selector with `o`, uses End to identify the last row and Home/PageDown when needed, and closes its own process without selecting/submitting anything. The keyboard allowlist contains no Enter, New Task or Apply action. This does not use the user's primary mouse/keyboard.

Only rendered screen output is inspected. Native-created temporary files are removed unread. No `error.log`, auth.json, browser profile, cookie, secret store or process memory is read. The previous refused log/session implementation remains absent and historically documented.

The returned IDs are live screen observations. The UI does not attest the account identity, API completeness or publication/draft state. Therefore `catalog_complete=false` coexists with a non-empty real list and `provider.coverage.visible_rows_complete=true`. An empty visual selector does not prove no environments exist. Automatic resolution remains conservative.

## Complete GitHub cross-reference

The optional GitHub reader enumerates owned repositories using native `gh api --method GET --hostname github.com ... --paginate --slurp`. The installed CLI does not permit `--slurp` together with `--jq`; pagination is native, then bounded results are normalized locally. Account identity is checked before and after enumeration.

`--correlate-github` adds a separate repository inventory and a per-environment correlation list. Explicit IDs/associations are verified links; equal names remain hints. A repository without an observed environment never becomes a fabricated Cloud row. The reference read found 33 repositories and one name-based match to the sample environment.

## Current web versus Desktop

The two observed routes are deliberately distinct:

- Desktop host: `https://codex-cloud-backend.chatgpt.com/v1/environment-configs`.
- Web proxy: `https://chatgpt.com/api/codex-cloud/v1/environment-configs`.

The earlier statement that the web prefix was universally wrong applied the Desktop finding too broadly. The web route is described in the original upstream discovery issue and was separately tested here. No successful Current catalogue is inferred from that route correction.

`current/browser.py` uses only an existing isolated `chrome` BrowserAct instance, a unique owned session and a fixed same-origin GET. `chrome-direct`, profile creation/import, proxy changes, cookie/token inspection, auto-dialog acceptance and challenge solving are not exposed. API content is normalized without logging raw errors. Session cleanup runs even after a denial or cancelled read.

The adapter is implemented and its command format is verified; the live catalog response is still **403 HTML**. This does not establish what further authentication would be required after that block is resolved. Unpublished-draft retrieval via `omitDraft=false` remains unverified live.

## MCP and stable integration

The eight MCP names remain unchanged. `list_legacy_environments` / `list_current_environments` accept optional `correlate_github`; both use the same configured runtime as CLI. Keep root `mcp.json` absent. A successful live MCP call returned the same two Legacy IDs and 33-repository correlation.

The implementation branch and source PR are reused. Stable main and the marketplace reference must not be promoted as a complete Current solution while Current still returns 403. GitHub preview publication does not install skills into ChatGPT Chat.

## References and provenance

- Native UI/key contract: OpenAI Codex `ui.rs` and `lib.rs` at `4aa94dce270de668eff6e2fa8585c82385e84455`.
- Web/Legacy distinction: https://github.com/openai/codex/issues/50182 and https://github.com/openai/codex/issues/51585 (upstream user reports, not a stable API guarantee).
- Native GitHub pagination: https://cli.github.com/manual/gh_api .
- All new network probes in this release were reads. Historical zero-task discovery is retained; a present-day check of the old test environment returned at least one task, so no fresh zero-task live claim is made.
