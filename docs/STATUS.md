# Implementation status — v0.4.0 preview

| Capability | Implemented | Actual validation |
|---|---|---|
| Independent Legacy/Current skills | Yes | No mandatory Root dispatcher |
| Legacy native screen-only reader | Yes | Two actual existing IDs, repeatable through CLI and optional MCP |
| Legacy account-wide completeness/publication state | Not attested by UI | Returned as unknown/incomplete, not guessed |
| Full owned GitHub inventory and correlation | Yes | 33 repositories read; name match preserved as a hint |
| Current BrowserAct web GET adapter | Yes | Actual 403 HTML; terminal failure, session closed |
| Current Desktop approved GET host | Yes | No connected direct host validated |
| Current successful catalog and unpublished drafts | Not verified live | Still blocked; no bypass or creation attempted |
| Optional MCP SDK server | Yes | Existing eight tools; optional list correlation argument |
| Provisioning/Credential Broker | Excluded | No implementation or live writes in discovery |

The major change from v0.3.1 is that Legacy is no longer a callback-only integration: it actually returns a live observed list on the reference machine. Current still does not return a usable live list, despite having a concrete tested browser transport. Neither result changes authorization automatically.

The screen reader uses ordinary TUI input/output and never reads the private logs/session stores targeted by the older refused attempt. That historic refusal is preserved in Project Memory, not rerouted.

Code and machine-local read configuration are ready for the existing source branch. The local config is outside the repository; default distributed settings are disabled. MCP remains optional and skills are not automatically installed into ChatGPT Chat by a GitHub release.

See OPERATIONS_0.4.0.md and VALIDATION_0.4.0.md for exact commands, evidence, cleanup and limits. Stable main and the marketplace PR remain separate from this preview until promotion is explicitly appropriate.
