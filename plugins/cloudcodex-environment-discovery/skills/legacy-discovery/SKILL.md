---
name: legacy-discovery
description: Discover existing Codex Cloud LEGACY environments and immutable IDs before creating tasks. Use Legacy native catalog evidence or an approved Legacy GET host, with explicit read-only escalation and repository matching. Not for current-generation configs or provisioning.
---

# Legacy discovery — independent Root procedure

Use directly from ChatGPT Root. Neither a Root dispatcher skill, a running Child, Windows Bootstrap nor MCP is required. Never create a task merely to obtain an environment ID.

## Establish the authorized read path

1. Resolve the actual installed plugin/repository path; do not guess private cache paths. Read `references/legacy-contract.md`.
2. Determine the requested account and repository/name/ID. Reuse only current, scoped consent; do not reinterpret plugin installation or AUTO as permission to acquire credentials.
3. Discover already-connected native catalog tools. The historical `codex cloud` selector displayed immutable IDs, including zero-task environments; **`codex cloud list --json` is a task list, not a catalog**. A matching environment label is insufficient evidence.
4. Use an existing authorized native catalog tool only if it exposes the needed data. The integrated native-session reader was blocked during implementation and is **not bundled**. Do not recreate it through another channel or invent a JSON CLI subcommand.

## Execute the implemented adapters

When a compatible local executor is available, the standard path is the CLI, with no MCP process:

```text
python <plugin-root>/runtime/cli.py legacy doctor --config <operator-config.json>
python <plugin-root>/runtime/cli.py legacy list --config <operator-config.json>
python <plugin-root>/runtime/cli.py legacy find --repository owner/repo --config <operator-config.json>
python <plugin-root>/runtime/cli.py legacy resolve --repository owner/repo --config <operator-config.json>
```

The startup configuration names and hash-pins a separately approved catalog host; it contains no credentials. `doctor` checks configuration, not authentication. A raw interactive CLI is not a JSON host. If no authorized host exists, report the missing capability instead of claiming successful discovery.

## Ordered escalation

- **Primary:** approved native catalog host (`kind: primary`). Prefer it and stop on complete, verified success, including a verified empty catalog.
- **HTTP fallback:** only an independently approved `kind: http` host, issuing GET to the known Legacy catalog. Repository searches may use the validated by-repository route; this proves association without guessing from a label.
- **Snapshot:** explicitly supplied sanitized catalog (`kind: snapshot`) is imported candidate evidence only. It never becomes live or complete.

`AUTO` may proceed only through approved stages. `CONFIRM` returns `approval_required` at an unapproved stage. **401/403, rate limiting, host policy denial, identity/integrity mismatch, cancellation or timeout stop the sequence.** Do not search for tokens, switch accounts or bypass a challenge to continue.

## Return and optional MCP

Return the exact ID, explicit repository association, account/scope, source, observation time, completeness and stage trace. Resolve only one live, fresh verified candidate in a complete requested catalog; otherwise retain ambiguity or a precise blocker. Cached IDs and Codex Tasks inventories do not establish absence or live truth.

If the optional SDK server is already enabled, equivalent tools are `list_legacy_environments`, `find_legacy_environments`, `get_legacy_environment`, `resolve_legacy_environment`. Do not enable MCP merely to execute this skill.

This skill never invokes Current or performs provisioning. Root may invoke the independent Current skill separately when both generations are explicitly requested.
