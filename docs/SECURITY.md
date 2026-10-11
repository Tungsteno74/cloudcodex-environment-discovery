# Security and operational controls

Discovery is read-only. No write-capable operations are exported. The runtime intentionally does not parse, decrypt, copy, log or export ChatGPT/Codex authentication secrets.

Authorized network transports and native selector readers are **injected by the host**. The public runtime never auto-discovers credential files, cookies, account sessions or fallback identities. It does not use Cloudflare challenges as an automation mechanism. Failures such as 401, 403, unavailable and unknown schema are separate states, not zero results.

Imported JSON is explicitly labeled imported, never live or authoritative. Do not supply arbitrary credential files as snapshots; use sanitized catalog fixtures. Restrict host filesystem access and review plugins/connectors before enabling them.

Future Credential Broker development, if viable, must remain a separate security boundary. Its output should be authorized request execution or narrowly scoped capability handles; credentials should not appear in prompts, logs or agent outputs.

The corresponding marketplace entry belongs in a staging/private catalog while the plugin is experimental, or may be proposed on a branch of the family marketplace for review before promotion.
