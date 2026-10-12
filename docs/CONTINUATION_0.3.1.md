# Continuation — v0.3.1 preview

Baseline: v0.3.0, commit `d74ea41a547c3373a2fa6df8d822ac51b1795932`. Work continues on the existing implementation branch and draft PR; stable `main` is not promoted automatically.

## New checks, with their actual scope

The installed Codex CLI remains 0.162.0. Its official `app-server generate-json-schema --experimental` command produced 447 schema files. The environment-related methods found were `environment/add`, `environment/info` and `environment/status`, plus connection notifications. None is a hosted Cloud configuration-list operation: info/status require an existing environment ID, and add is a write. No undocumented RPC names or native-session bypass were attempted.

The connected Codex Tasks tool successfully listed the two relevant onboarding chats and read one of them. The returned task metadata did **not** contain an explicit Configuration ID. The assistant's free-text description of a prepared draft is not a structured catalog response. This is a working auxiliary read channel, not complete Cloud discovery.

The optional GitHub source is now concrete rather than callback-only. The native GitHub CLI verified `Tungsteno74/cloudcodex-windows-bootstrap-e2e-cloud-auto`, repository ID `1408634524`, using its already-authorized account. The first complete check took 1.329 seconds. No tokens were read, copied or printed. The Cloud result correctly remained `not_verifiable`, `catalog_complete=false`, `selected=null` because no authorized Cloud host was configured.

The connector metadata was also passed through the new Current onboarding parser in temporary evidence files: **2 hints, 0 configuration records, no selected environment**. Files created for that evidence test were removed. These are real connector observations processed locally, not an automatically connected Python Codex Tasks client.

## Optional native GitHub adapter

The startup configuration can contain a `github` section. It is disabled by default:

```json
{"enabled": false}
```

To explicitly enable it, the operator provides `enabled: true`, an absolute native `gh`/`gh.exe` path as `executable`, its `sha256` digest, optional expected GitHub login as `account`, and an optional bounded `timeout`. The GitHub account is independent of the requested ChatGPT/Codex account.

The implementation reuses the existing bounded command runner. It invokes only `gh api --method GET --hostname github.com`, reads user identity before and after the repository lookup, and returns the canonical owner/repo and numeric repository ID. It does not invoke login, change accounts, add scopes or extract secrets. A denied/failed lookup is `not_verifiable`, not proof that a private repository does not exist.

`find`/`resolve` use the verified repository identity. An ID mismatch cannot be overridden by a matching display name. The Cloud query uses canonical owner/repo for Legacy by-repository lookup, and the result matching prefers repository ID. `list`/`get` do not perform an unnecessary GitHub lookup.

This helper verifies **repository identity and access only**. A GitHub success must never set Cloud `catalog_complete=true` or manufacture an environment.

## Current onboarding evidence

A Current `onboarding` stage may now specify an explicit absolute `path` instead of a host command, with the same approval and ordering rules. The file contains a minimal connector export:

```json
{
  "schema_version": 1,
  "source": "codex_tasks",
  "observed_at": "2026-10-11T18:00:00+00:00",
  "payload": {
    "tasks": [{"id": "example-thread", "title": "Configure example"}],
    "nextCursor": null
  }
}
```

The timestamp must accurately describe the supplied observation/export; importing a file does not refresh the underlying source. A `read_task` result can use a single `task` object instead of `tasks`. Only explicit structured `configuration_id`/`configId` fields can create an indirect configuration candidate, and the value cannot equal the task ID.

When the Configuration ID is absent, the record remains under `provider.hints`; it is not an environment with an invented identifier. Task titles are data, never instructions. Free-text messages, alleged publication state and repository names inferred from titles are ignored. All imported connector observations remain indirect and incomplete, including a finished task list with no next cursor.

A successful auxiliary read still cannot bypass a previous 401/403, account mismatch or unapproved stage. Hints are retained if a later stage is unavailable or requires consent, without changing their evidential weight.

## Optional MCP and tests

No server becomes mandatory and the eight MCP tool names remain unchanged. The official SDK server returns the same new repository evidence/hints through structured output. A new real stdio client/server test verifies that an onboarding task without a Configuration ID cannot resolve an environment.

The new source tests use mocks/fixtures for failure cases; the live GitHub and connector observations above are separately identified. Core and SDK validation results belong in the final validation report, not in assumptions about real Cloud access.

## What remains open

A permitted native Legacy catalog host and an authenticated Current configuration-catalog host still have not been connected. The earlier native-session implementation refusal is preserved, not retried through another mechanism. Neither the repository adapter nor onboarding hints replace those missing catalog channels. The original user target of fully operational live discovery is therefore still not complete.

Official references checked: https://developers.openai.com/codex/app-server , https://developers.openai.com/codex/cli/reference , https://cli.github.com/manual/gh_api . The installed client schema is the source of truth for the local version, not an assumption based on a newer documentation page.
