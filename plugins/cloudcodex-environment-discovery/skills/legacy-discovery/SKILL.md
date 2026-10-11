---
name: legacy-discovery
description: Read existing Codex Cloud LEGACY environments before task creation. Use the implemented isolated native CLI selector or an approved read-only API host; return real IDs, coverage and optional GitHub correlations. Not for Current configs or provisioning.
---

# Legacy discovery — direct Root entry point

This skill requires neither a coordinating Root skill, a running Child, Windows Bootstrap nor MCP. Its only target is **reading existing environments**. Do not create tasks, environments or publication actions as discovery probes.

## Choose the implemented read path

1. Resolve the installed plugin/source path and the operator's approved discovery configuration. Read `references/legacy-contract.md`. Do not search credential stores.
2. Prefer `native_cli` when the reviewed, hash-pinned native Codex 0.162.0 executable and optional terminal dependencies are available. This is an implemented screen-only reader, not the earlier refused log/session extraction proposal.
3. Invoke the CLI through an authorized local executor such as RDC:

```text
python <plugin-root>/runtime/cli.py legacy list --config <operator-config.json> --pretty
python <plugin-root>/runtime/cli.py legacy list --config <operator-config.json> --correlate-github --pretty
python <plugin-root>/runtime/cli.py legacy find --repository owner/repo --config <operator-config.json>
```

The native adapter opens a separate terminal, sends only standard selector/navigation actions, and reads the ordinary rendered environment list. It does not control the user's primary mouse/keyboard or read private logs, tokens, cookies, profile files or process memory. `codex cloud list --json` still lists **tasks**, not environments.

## Coverage and identity

A live native result can contain real IDs with `status=partial` and `catalog_complete=false`. Inspect `provider.coverage.visible_rows_complete`: it states whether all visible picker rows were traversed. The selector does not attest the exact account identity, API-wide completeness or draft/publication state, so these must remain unknown. Never reinterpret a visual empty list as proof that the account has no environments.

The reader is version-gated, handles complete terminal frames and bounded scrolling, and closes only its own process. A changed/truncated layout, failure or cancellation must remain an explicit blocker. No Enter/New Task/Apply action is permitted.

## API fallback and escalation

An existing approved `primary` host is an alternative to `native_cli`; the two are not mandatory chained steps. A separately approved `http` host may query the global Legacy catalog or the validated by-repository GET route. This host must already have authorization; this plugin does not acquire or export credentials.

`AUTO` runs only approved stages. `CONFIRM` returns `approval_required` rather than granting consent. On 401/403, rate limiting, account/integrity mismatch, security challenge, cancellation or deadline expiry, stop the affected sequence. No identity switching or transport retry around a denial. Imported snapshots are optional candidate evidence only.

## GitHub cross-reference

With GitHub enabled in operator configuration, `--correlate-github` enumerates all owned repositories using the existing native gh account and its pagination. It joins those records with actual observed environment rows. Numeric repository IDs and explicit associations outrank name matches. A matching owner/repo or short environment label remains a `name_candidate` when no association was supplied by Codex.

GitHub repository existence cannot create an Environment ID. The inventory completeness refers to GitHub only and must not promote Cloud coverage. For a single repository, find/resolve retain the already-implemented verified ID lookup.

## Return or optional MCP

Return ID, label, source, observation time, coverage and ordered attempts. Preserve unknown account/state, multiple candidates and incomplete catalogs. Automatic resolve remains restricted to unique, fresh, live, verified identities with required coverage.

When the optional MCP server is already connected, use list_legacy_environments, find_legacy_environments, get_legacy_environment or resolve_legacy_environment. The list tool supports `correlate_github: true`. Do not enable MCP simply to run this skill.

This skill never invokes Current implicitly. Provisioning belongs to the separate creation plugin, not to a fallback here.
