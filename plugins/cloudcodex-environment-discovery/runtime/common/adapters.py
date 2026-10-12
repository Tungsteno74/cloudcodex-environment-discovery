"""Bounded host-command adapters; authentication stays in the approved host.

Commands are configured by the operator at startup, never by a model tool call.
The executable and script files are hash-pinned. Only GET/catalog-read requests
are sent; neither credentials nor arbitrary command strings are accepted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
from typing import Any, Mapping, Tuple

from .models import (
    HttpResponse,
    ProviderResult,
    extract_page,
    parse_environment,
    normalize_repository,
)
from .operation import active_operation, checkpoint

MAX_BYTES = 8 * 1024 * 1024
CURRENT_CATALOG_SURFACES = {
    "desktop": "https://codex-cloud-backend.chatgpt.com/v1/environment-configs",
    "web": "https://chatgpt.com/api/codex-cloud/v1/environment-configs",
}

CATALOG_URLS = {
    "legacy": "https://chatgpt.com/backend-api/wham/environments",
    "current": "https://codex-cloud-backend.chatgpt.com/v1/environment-configs",
}


class AdapterError(RuntimeError):
    """Public error codes deliberately exclude raw command output."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class CommandSpec:
    argv: Tuple[str, ...]
    pins: Tuple[Tuple[str, str], ...]
    cwd: str
    timeout: float = 20.0

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CommandSpec":
        if not isinstance(data, dict) or set(data) - {"argv", "sha256", "cwd", "timeout"}:
            raise ValueError("Invalid host-command configuration")
        argv = data.get("argv")
        pins = data.get("sha256")
        cwd = data.get("cwd")
        timeout = data.get("timeout", 20.0)
        if (
            not isinstance(argv, list)
            or not argv
            or len(argv) > 32
            or not all(isinstance(arg, str) and 0 < len(arg) <= 4096 for arg in argv)
        ):
            raise ValueError("Host command must be a bounded argv array")
        if not Path(argv[0]).is_absolute() or Path(argv[0]).suffix.lower() in {
            ".cmd",
            ".bat",
            ".ps1",
        }:
            raise ValueError("Host executable must be absolute and not a shell script")
        if any(
            arg.lower() in {"-c", "-command", "/c", "-encodedcommand", "--eval", "-e"}
            for arg in argv[1:]
        ):
            raise ValueError("Inline shell/code arguments are not permitted")
        if any(
            any(
                secret in arg.lower()
                for secret in ("--token", "--password", "--secret", "--cookie", "authorization:")
            )
            for arg in argv[1:]
        ):
            raise ValueError("Credentials must not be supplied in command arguments")
        if not isinstance(cwd, str) or not Path(cwd).is_absolute():
            raise ValueError("Host working directory must be explicit and absolute")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0.1 <= timeout <= 120
        ):
            raise ValueError("Invalid host timeout")
        if not isinstance(pins, dict) or str(Path(argv[0])) not in pins:
            raise ValueError("Host executable requires an explicit SHA-256 pin")
        for path, digest in pins.items():
            if (
                not isinstance(path, str)
                or not isinstance(digest, str)
                or not Path(path).is_absolute()
                or not re.fullmatch(r"[a-fA-F0-9]{64}", digest)
            ):
                raise ValueError("Invalid file integrity pin")
        for arg in argv[1:]:
            if Path(arg).suffix.lower() in {".py", ".js", ".mjs"} and str(Path(arg)) not in pins:
                raise ValueError("Host script also requires an integrity pin")
        return cls(tuple(argv), tuple(pins.items()), cwd, float(timeout))

    def verify(self) -> None:
        for filename, expected in self.pins:
            path = Path(filename)
            try:
                with path.open("rb") as stream:
                    digest = hashlib.sha256()
                    for chunk in iter(lambda: stream.read(128 * 1024), b""):
                        checkpoint()
                        digest.update(chunk)
                if digest.hexdigest().lower() != expected.lower():
                    raise AdapterError("host_integrity_mismatch")
            except OSError:
                raise AdapterError("host_file_unavailable") from None


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate host JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON number")


class CommandClient:
    """One bounded process per host request; no shell, no automatic retries."""

    def __init__(self, specification: CommandSpec):
        self.specification = specification

    def request(self, payload: Mapping[str, Any], *, allow_array: bool = False) -> Any:
        operation = active_operation(self.specification.timeout)
        operation.check()
        self.specification.verify()
        encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        if len(encoded) > 65536:
            raise AdapterError("request_too_large")
        # Do not pass ambient secret variables. A host needing auth uses its own
        # already-authorized connection; no token extraction is implemented here.
        keys = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "LANG",
            "PATHEXT",
        }
        environment = {key: value for key, value in os.environ.items() if key.upper() in keys}
        environment["PYTHONUTF8"] = "1"
        process = subprocess.Popen(
            list(self.specification.argv),
            cwd=self.specification.cwd,
            env=environment,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        buffer = bytearray()
        finished, oversized = threading.Event(), threading.Event()

        def drain() -> None:
            try:
                while True:
                    chunk = process.stdout.read(65536)
                    if not chunk:
                        break
                    if len(buffer) + len(chunk) > MAX_BYTES:
                        oversized.set()
                        break
                    buffer.extend(chunk)
            finally:
                finished.set()

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()

        def send_request():
            try:
                process.stdin.write(encoded)
                process.stdin.close()
            except (OSError, BrokenPipeError, ValueError):
                pass

        writer = threading.Thread(target=send_request, daemon=True)
        writer.start()
        try:
            from time import monotonic

            deadline = monotonic() + min(operation.remaining(), self.specification.timeout)
            while not finished.wait(0.05):
                operation.check()
                if monotonic() >= deadline:
                    raise AdapterError("host_timeout")
            if oversized.is_set():
                raise AdapterError("host_output_too_large")
            operation.check()
            try:
                code = process.wait(
                    timeout=max(0.01, min(operation.remaining(), deadline - monotonic()))
                )
            except subprocess.TimeoutExpired:
                raise AdapterError("host_timeout") from None
            if code != 0:
                raise AdapterError("host_exit_failure")
            try:
                response = json.loads(
                    buffer.decode("utf-8"),
                    object_pairs_hook=_unique_pairs,
                    parse_constant=_reject_constant,
                )
            except (UnicodeError, ValueError):
                raise AdapterError("host_invalid_json") from None
            if not isinstance(response, dict) and not (allow_array and isinstance(response, list)):
                raise AdapterError("host_invalid_envelope")
            return response
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            reader.join(timeout=1)
            writer.join(timeout=1)
            if not process.stdin.closed:
                process.stdin.close()
            process.stdout.close()


def validate_observation(
    envelope: Mapping[str, Any], cloud_type: str, max_age: float = 60.0
) -> str:
    if envelope.get("cloud_type") != cloud_type or envelope.get("schema_version") != 1:
        raise AdapterError("host_identity_mismatch")
    value = envelope.get("observed_at")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError()
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        if age < -5 or age > max_age:
            raise AdapterError("stale_observation")
    except (AttributeError, TypeError, ValueError):
        raise AdapterError("invalid_observation_time") from None
    return value


class CommandReadTransport:
    """GET relay to an operator-approved, already authorized external host."""

    def __init__(self, cloud_type: str, client: CommandClient, api_surface: str = "desktop"):
        if (
            api_surface not in CURRENT_CATALOG_SURFACES
            or cloud_type == "legacy"
            and api_surface != "desktop"
        ):
            raise ValueError("Invalid catalog surface")
        self.cloud_type = cloud_type
        self.client = client
        self.catalog_url = (
            CURRENT_CATALOG_SURFACES[api_surface]
            if cloud_type == "current"
            else CATALOG_URLS[cloud_type]
        )

    def __call__(self, url: str, parameters: Mapping[str, str]) -> HttpResponse:
        allowed = url == self.catalog_url
        # Current Desktop's client exposes a read-only GET by exact configId.
        # A single path segment is allowed only on the observed Desktop host.
        detail_prefix = CURRENT_CATALOG_SURFACES["desktop"] + "/"
        is_current_detail = (
            self.cloud_type == "current"
            and self.catalog_url == CURRENT_CATALOG_SURFACES["desktop"]
            and url.startswith(detail_prefix)
            and bool(re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}", url[len(detail_prefix):]
            ))
        )
        allowed = allowed or is_current_detail
        prefix = CATALOG_URLS["legacy"] + "/by-repo/github/"
        if self.cloud_type == "legacy" and url.startswith(prefix):
            candidate = url[len(prefix) :]
            allowed = normalize_repository(candidate) == candidate and ":" not in candidate
        if not allowed:
            raise AdapterError("unapproved_catalog_destination")
        if is_current_detail and parameters:
            raise AdapterError("unapproved_catalog_query")
        permitted = {"scope", "limit", "cursor", "omitDraft", "view"}
        if set(parameters) - permitted or not all(isinstance(v, str) for v in parameters.values()):
            raise AdapterError("unapproved_catalog_query")
        if "view" in parameters and (
            self.cloud_type != "current" or parameters["view"] != "picker"
        ):
            raise AdapterError("unapproved_catalog_query")
        result = self.client.request(
            {
                "schema_version": 1,
                "operation": "http_get",
                "method": "GET",
                "cloud_type": self.cloud_type,
                "url": url,
                "query": dict(parameters),
                "headers": {
                    "Accept": "application/json",
                    **({"X-OpenAI-Product-Sku": "codex"} if self.cloud_type == "current" else {}),
                },
            }
        )
        if result.get("cloud_type") != self.cloud_type or result.get("schema_version") != 1:
            raise AdapterError("host_identity_mismatch")
        status = result.get("status")
        if type(status) is int and status in {401, 403}:
            return HttpResponse(status)
        observed = validate_observation(result, self.cloud_type)
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise AdapterError("invalid_http_status")
        account = result.get("account")
        verified = result.get("account_verified") is True and isinstance(account, str)
        content_type = result.get("content_type", "")
        if not isinstance(content_type, str):
            raise AdapterError("catalog_not_json")
        # Reject HTML challenges even when the host reports HTTP 200.
        if status == 200 and content_type.split(";")[0].strip().lower() != "application/json":
            raise AdapterError("catalog_not_json")
        return HttpResponse(
            status,
            result.get("body") if status == 200 else None,
            account if verified else None,
            verified,
            observed,
            content_type,
        )


class CommandCatalogProvider:
    """Native/official catalog handoff from an operator-approved host command."""

    def __init__(
        self,
        cloud_type: str,
        client: CommandClient,
        source: str,
        indirect: bool = False,
        scopes=None,
    ):
        self.name, self.client, self.source, self.indirect = cloud_type, client, source, indirect
        self.scopes = tuple(
            scopes or (("user",) if cloud_type == "legacy" else ("user", "workspace"))
        )

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        result = self.client.request(
            {
                "schema_version": 1,
                "operation": "onboarding_read" if self.indirect else "catalog_read",
                "cloud_type": self.name,
                "account": account,
                "include_drafts": include_drafts,
                "scopes": list(self.scopes),
            }
        )
        if result.get("cloud_type") != self.name or result.get("schema_version") != 1:
            raise AdapterError("host_identity_mismatch")
        status = result.get("status")
        if status in {"unauthorized", "forbidden"}:
            return ProviderResult(
                provider=self.name, status=status, reason="host_catalog_" + status
            )
        observed = validate_observation(result, self.name)
        if status not in {
            "ok",
            "empty",
            "partial",
            "unavailable",
            "unauthorized",
            "forbidden",
            "stale",
        }:
            raise AdapterError("invalid_catalog_status")
        if status in {"unauthorized", "forbidden", "unavailable", "stale"}:
            return ProviderResult(
                provider=self.name,
                status=status,
                source=self.source,
                reason="host_catalog_" + status,
            )
        evidence = "indirect" if self.indirect else "live"
        verified_account = result.get("account") if result.get("account_verified") is True else None
        if account is not None and verified_account != account:
            return ProviderResult(provider=self.name, status="forbidden", reason="account_mismatch")
        try:
            items, cursor = extract_page(result.get("catalog"))
            if self.indirect:
                explicit = []
                for item in items:
                    identifier = item.get("configuration_id") or item.get("configId")
                    if not isinstance(identifier, str) or not identifier:
                        raise ValueError("Onboarding evidence has no explicit configuration ID")
                    clean = dict(item)
                    clean["environment_id"] = identifier
                    explicit.append(clean)
                items = explicit
            if status == "empty" and items:
                raise ValueError("Inconsistent empty catalog")
            entries = [
                parse_environment(
                    item,
                    self.name,
                    str(result.get("scope", "unknown")),
                    self.source,
                    evidence,
                    verified_account,
                    observed,
                )
                for item in items
            ]
        except (ValueError, TypeError):
            raise AdapterError("catalog_schema_mismatch") from None
        complete = (
            not self.indirect
            and result.get("catalog_complete") is True
            and cursor is None
            and result.get("include_drafts") is include_drafts
            and status in {"ok", "empty"}
            and result.get("scopes") == list(self.scopes)
        )
        return ProviderResult(
            provider=self.name,
            status=status if complete else "partial",
            environments=entries,
            catalog_complete=complete,
            evidence=evidence,
            observed_at=observed,
            source=self.source,
            scope=str(result.get("scope", "unknown")),
            account=verified_account,
            account_verified=isinstance(verified_account, str),
        )
