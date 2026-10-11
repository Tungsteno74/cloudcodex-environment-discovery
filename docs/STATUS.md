# Implementation status — 0.1.1

| Component | Implemented? | Live E2E validated? |
|---|---|---|
| Root-level skill | Yes | Not yet |
| Local MCP four read-only tools | Yes | Offline protocol tests only |
| Normalized descriptor + resolver | Yes | Offline tests only |
| Legacy authorized HTTP adapter | Yes (injection) | Prior historical GET 200; current plugin not live tested |
| Legacy native TUI reader | Host injection contract only | Native selector previously observed; programmatic extraction not implemented |
| Current authorized HTTP catalog | Yes (injection) | Historical 200 followed by 403; plugin not live tested |
| GitHub repository matching | Yes (normalized identity) | No live connector join E2E yet |
| Credential Broker / provisioning | Not part of this plugin | No |

The **no task creation** property is intentionally stronger than the current discovery coverage. Do not elevate imported snapshots to live evidence. Run `python -X utf8 tools/validate.py` and confirm CI on each change.

## Next engineering milestones

1. Integrate a supported native Legacy selector reader that can return immutable IDs without interactive user input.
2. Integrate a supported, expressly authorized Current environment-configs catalog transport without handling credentials in the model.
3. Exercise the live Root-facing skill with user/workspace scopes and multiple environments per repo.
4. Promote the Git-backed plugin into the public GSM marketplace only after it is intentionally ready for family distribution.
