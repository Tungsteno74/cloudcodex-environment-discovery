# Current Cloud — optional Webcmd escalation (v0.4.1)

## Verified behavior

Webcmd is an optional, preapproved read-only Current catalog source using the
**original backend**:
    GET https://codex-cloud-backend.chatgpt.com/v1/environment-configs

It runs JavaScript in an existing isolated browser profile. It does not fake
JavaScript, handle Cloudflare challenges, import other browser profiles,
read cookies/tokens, change accounts or create/publish environments.

Real test on the reference Windows PC using Webcmd 0.8.4 and CloakBrowser
0.4.5: the v0.4.1 discovery CLI returned HTTP **401 JSON**, status
unauthorized, reason http_401, zero Current configurations and incomplete
coverage. The newly created Webcmd session was closed, with zero leftovers.
This reproduces the earlier Webcmd result, **not** an authenticated Current
catalog success.

## Escalation position

Current: optional approved primary -> webcmd -> browser_web (BrowserAct) ->
approved http -> onboarding evidence -> imported snapshot.

Stages are optional and require explicit prior approval. With no primary,
Webcmd is the first Current browser route, since it returned an application
401 JSON while BrowserAct returned Cloudflare 403 HTML.

**401/403, rate limits, identity/integrity mismatch, cancellation or a timeout
stop Cloud escalation.** This order is not permission to retry another
transport after a denial. Only unavailable, partial or stale results can
proceed to the next independently approved stage. Legacy is unaffected.

## Prerequisites

- Webcmd CLI already installed and reviewed by the operator; tested version:
  @agentrhq/webcmd 0.8.4.
- Isolated CloakBrowser runtime already installed. The adapter checks for its
  configured executable and never downloads or installs a browser.
- The selected Webcmd profile must already exist. Use Webcmd's own doctor
  command beforehand if appropriate; it may initialize a browser when absent.
  The discovery plugin never runs doctor, creates/imports a profile or logs in.
- Operator-supplied Node executable and Webcmd main.js are both SHA-256 pinned.
  The profile alias is restricted and no model tool can choose its own binary,
  URL or credentials. Save user-specific configuration outside the repository.

Example stage inside the Current stages array (placeholder paths and hashes):

    {
      "kind": "webcmd",
      "approved": true,
      "webcmd": {
        "command": {
          "argv": ["C:\\path\\node.exe",
                   "C:\\path\\node_modules\\@agentrhq\\webcmd\\dist\\src\\main.js"],
          "sha256": {
            "C:\\path\\node.exe": "<node-sha256>",
            "C:\\path\\node_modules\\@agentrhq\\webcmd\\dist\\src\\main.js":
              "<webcmd-entrypoint-sha256>"
          },
          "cwd": "C:\\existing\\directory",
          "timeout": 28
        },
        "browser_binary": "C:\\existing\\cloakbrowser\\chrome.exe",
        "profile": "default"
      }
    }

Hashes can be calculated using PowerShell Get-FileHash -Algorithm SHA256,
after reviewing both executable and CLI. File hashes do not verify all
transitive dependencies: assess the Webcmd package separately.

## Read and cleanup contract

The adapter:
1. Checks the installed browser binary and configured existing profile.
2. Checks the session inventory, creates one unique temporary Webcmd session
   and verifies it belongs to the chosen profile.
3. Navigates to the fixed Current endpoint using browser run --stdin and
   standard GET. It reads status and MIME; only a 200 JSON response is parsed.
4. Applies existing bounded pagination and draft/scope semantics.
5. Reconciles and closes only its own session; unsafe or unconfirmed cleanup
   is reported and cannot yield complete success.

The Desktop picker is a UI selection view and is not used for Webcmd's
original standard GET. A missing row from an incomplete catalog never proves
that an environment does not exist. Webcmd does not inherit Codex CLI login.

Use the regular Current skill or CLI with an explicitly selected config:

    python <plugin-root>/runtime/cli.py current doctor --config <operator-config>
    python <plugin-root>/runtime/cli.py current list --config <operator-config>
    python <plugin-root>/runtime/cli.py current find --repository owner/repo --config <operator-config>

Doctor reports setup only, not authorization. CLI and optional MCP use the
same provider. No provisioning, publication or browser authentication change
is performed by the plugin.


## Exact-ID point lookup — waiting for authorized Current API access

For `current get --environment-id <known-configId>`, the same previously
approved Webcmd CLI/profile can issue a fixed GET to
`https://codex-cloud-backend.chatgpt.com/v1/environment-configs/{configId}`.
Unlike the catalog, this has **no** `scope`, `limit`, `cursor` or `view=picker`.
The Configuration ID must be a safe, known, single opaque path segment.
The Webcmd session is opened, identity-verified and closed using the existing
owned-session lifecycle. No automatic login, new profile or challenge solving.

A verified 200 JSON record with exactly matching ID establishes only
`point_verified=true`, **not** `catalog_complete=true`. A denied 401/403 is
terminal and remains visible as the underlying provider reason.
The live Webcmd point test of 12 October 2026 returned **401 JSON**.
The Current skill is functionally available but live detail/catalog discovery
is awaiting a supported authorized backend path. This is not proof of
environment absence or a scheduled OpenAI patch.
