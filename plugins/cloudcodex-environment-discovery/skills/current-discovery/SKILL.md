---
name: current-discovery
description: Discover CURRENT-GENERATION Codex Cloud configurations, immutable IDs, repository associations, drafts and versions before task creation. Use approved catalog sources with scoped pagination and auditable escalation. Not for Legacy catalogs or provisioning.
---

# Current Cloud discovery — independent Root procedure

Invoke directly from ChatGPT Root. No Legacy dependency, Root dispatcher, running Child, Windows Bootstrap or mandatory MCP process exists. Read `references/current-contract.md`.

## Establish scope and capability

1. Determine account, repository/name/ID, user/workspace scope and whether drafts are needed. Reuse valid, scoped authorization; AUTO never supplies new credentials or permissions.
2. Discover an already-authorized official current-generation catalog connector. Verify the actual capability rather than assuming Codex Tasks.list_environments is the hosted catalog. That inventory previously returned empty while real Cloud configurations existed.
3. If a compatible local executor is available, resolve the actual plugin path and use its executable configured adapters:

```text
python <plugin-root>/runtime/cli.py current doctor --config <operator-config.json>
python <plugin-root>/runtime/cli.py current list --include-drafts --config <operator-config.json>
python <plugin-root>/runtime/cli.py current find --repository owner/repo --config <operator-config.json>
python <plugin-root>/runtime/cli.py current resolve --repository owner/repo --config <operator-config.json>
```

`doctor` is a configuration check, not proof of authorization. Configuration is operator-controlled and names hash-pinned host programs. The plugin does not bundle a working authenticated OpenAI host or obtain session credentials; report that gap precisely when no permitted source exists.

## Ordered escalation

- **Primary (`primary`)**: existing authorized official/current catalog host. Stop at complete live success, including a verified empty result.
- **HTTP (`http`)**: an independently approved GET host for `/v1/environment-configs`, using explicit user/workspace scopes, bounded cursor pagination and `omitDraft` flags. A historical GET 200 does not guarantee this channel is usable now.
- **Onboarding hints (`onboarding`)**: authorized configuration/onboarding reads may provide explicit configuration IDs as indirect candidates. Task IDs, titles and chat timestamps are not environment identities. Completeness and readiness are not inferred.
- **Snapshot (`snapshot`)**: a supplied sanitized catalog is imported evidence only; it cannot complete live discovery.

Only pre-approved stages execute. `CONFIRM` returns `approval_required` at an unapproved stage; `AUTO` skips it. **Stop on 401/403, rate limiting, host policy denial, account/integrity mismatch, cancellation or deadline expiry.** No token search, account switching, challenge bypass or task creation is an escalation option.

## Validate and report

Distinguish published, draft and unknown configuration state from execution readiness. `omitDraft=true` excludes drafts; it does not prove their absence. Keep configurations/versions distinct and reject conflicting immutable records. Check explicit repository IDs first, then owner/repo associations; display names alone are hints.

Return the selected generation, IDs, associations, account/scope, observation time, completeness and stage trace. Resolve only one fresh, live verified candidate with complete requested coverage. Preserve ambiguity and incomplete catalogs rather than guessing.

When the optional MCP SDK server is already connected, equivalent tools are `list_current_environments`, `find_current_environments`, `get_current_environment`, `resolve_current_environment`. Enabling MCP is not an authentication fix and is not a prerequisite for this skill.

Never invoke Legacy implicitly. A request covering both generations requires two independent Root invocations and separate results. The original Bootstrap three-gate tests and provisioning workflow remain outside this skill.
