"""Optional read-only Current catalog reader using an existing Webcmd profile.

Webcmd supplies a real JavaScript-capable browser for an ordinary GET on the
original Current backend. This module never imports profiles, reads credentials,
changes browser settings or attempts to solve security challenges.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Mapping, Optional, Sequence
from urllib.parse import urlencode
from uuid import uuid4

from common.adapters import AdapterError, CommandSpec, MAX_BYTES
from common.models import HttpResponse, ProviderResult, now_utc
from common.operation import Operation, active_operation, operation_scope
from .detail import valid_configuration_id
from .provider import CurrentCloudEnvironmentProvider

CURRENT_URL = "https://codex-cloud-backend.chatgpt.com/v1/environment-configs"
_SESSION_PREFIX = "cloudcodex-webcmd-"
_ALLOWED_QUERY = frozenset({"scope", "limit", "cursor", "omitDraft"})
_SAFE_ENVIRONMENT = frozenset({
    "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
    "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
    "LANG", "PATHEXT",
})


@dataclass(frozen=True)
class WebcmdSettings:
    """Pin the Webcmd CLI and require a pre-installed isolated browser runtime."""

    command: CommandSpec
    browser_binary: str
    profile: str = "default"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WebcmdSettings":
        if not isinstance(value, dict) or set(value) != {"command", "browser_binary", "profile"}:
            raise ValueError("Webcmd requires command, browser_binary and profile")
        command = CommandSpec.from_mapping(value["command"])
        if (
            len(command.argv) != 2
            or Path(command.argv[0]).name.lower() not in {"node.exe", "node"}
            or Path(command.argv[1]).name.lower() != "main.js"
            or tuple(p.lower() for p in Path(command.argv[1]).parts[-5:])
            != ("@agentrhq", "webcmd", "dist", "src", "main.js")
        ):
            raise ValueError("Expected pinned Node and @agentrhq/webcmd CLI entrypoint")
        browser_binary, profile = value["browser_binary"], value["profile"]
        if (
            not isinstance(browser_binary, str)
            or not Path(browser_binary).is_absolute()
            or Path(browser_binary).name.lower() not in {"chrome", "chrome.exe"}
            or not isinstance(profile, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", profile)
        ):
            raise ValueError("Invalid isolated Webcmd browser or profile")
        return cls(command, browser_binary, profile)


class WebcmdCli:
    """Execute only fixed Webcmd operations, without shell or ambient secrets."""

    def __init__(self, settings: WebcmdSettings):
        self.settings = settings

    def run(self, arguments: tuple, program: Optional[str] = None) -> Any:
        operation = active_operation(self.settings.command.timeout)
        operation.check()
        specification = replace(
            self.settings.command,
            argv=self.settings.command.argv + ("--profile", self.settings.profile) + arguments,
        )
        specification.verify()
        environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in _SAFE_ENVIRONMENT
        }
        environment["PYTHONUTF8"] = "1"
        timeout = min(operation.remaining(), specification.timeout)
        try:
            completed = subprocess.run(
                list(specification.argv),
                input=(program or "").encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=specification.cwd,
                env=environment,
                shell=False,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise AdapterError("host_timeout") from None
        except OSError:
            raise AdapterError("webcmd_cli_unavailable") from None
        operation.check()
        if completed.returncode != 0:
            raise AdapterError("webcmd_command_failed")
        if len(completed.stdout) > MAX_BYTES:
            raise AdapterError("host_output_too_large")
        try:
            return json.loads(
                completed.stdout.decode("utf-8"),
                object_pairs_hook=self._reject_duplicate_keys,
                parse_constant=self._reject_nonfinite,
            )
        except (UnicodeError, ValueError):
            raise AdapterError("webcmd_invalid_json") from None

    @staticmethod
    def _reject_nonfinite(value: str) -> None:
        raise ValueError("Non-finite Webcmd JSON value")

    @staticmethod
    def _reject_duplicate_keys(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate Webcmd JSON key")
            result[key] = value
        return result


class WebcmdCatalogProvider:
    """Escalation adapter with bounded session ownership and cleanup."""

    name = "current"

    def __init__(
        self,
        settings: WebcmdSettings,
        scopes: Sequence[str] = ("user", "workspace"),
        page_limit: int = 12,
        page_size: int = 100,
        cli_factory: Callable = WebcmdCli,
    ):
        self.settings = settings
        self.scopes, self.page_limit, self.page_size = scopes, page_limit, page_size
        self.cli = cli_factory(settings)

    def _sessions(self) -> dict:
        rows = self.cli.run(("session", "list", "-f", "json"))
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not isinstance(row.get("profileId"), str)
            for row in rows
        ):
            raise AdapterError("webcmd_session_inventory_invalid")
        if len({row["id"] for row in rows}) != len(rows):
            raise AdapterError("webcmd_session_inventory_ambiguous")
        return {row["id"]: row for row in rows}

    def _owned(self, rows: dict, before: set, prefix: str) -> list:
        return [
            identifier for identifier, row in rows.items()
            if identifier.startswith(prefix + "-")
            and identifier not in before
            and row.get("profileId") == self.settings.profile
            and row.get("kind") == "explicit"
        ]

    def _read(self, session: str, url: str, query: Mapping[str, str]) -> HttpResponse:
        catalog = (
            url == CURRENT_URL
            and not set(query) - _ALLOWED_QUERY
            and all(isinstance(value, str) for value in query.values())
            and query.get("scope") in {"user", "workspace"}
            and query.get("omitDraft") in {"true", "false"}
        )
        detail = (
            url.startswith(CURRENT_URL + "/")
            and valid_configuration_id(url[len(CURRENT_URL) + 1:])
            and not query
        )
        if not (catalog or detail):
            raise AdapterError("unapproved_catalog_destination")
        target = url + ("?" + urlencode(query) if query else "")
        timeout_ms = max(1, int(min(active_operation().remaining(), 20) * 1000))
        program = (
            "const r=await page.goto(" + json.dumps(target) +
            ",{waitUntil:'domcontentloaded',timeout:" + str(timeout_ms) + "});\n"
            "if(!r) return {status:502,content_type:'',body:null};\n"
            "const type=r.headers()['content-type']||'';\n"
            "const out={status:r.status(),content_type:type,body:null};\n"
            "if(out.status===200 && type.split(';')[0].trim().toLowerCase()==='application/json'){\n"
            " const text=await r.text();\n"
            " if(text.length>8000000) return {status:502,content_type:'',body:null};\n"
            " out.body=JSON.parse(text);\n"
            "}\n"
            "return out;\n"
        )
        result = self.cli.run(
            (
                "--session", session, "browser", "run", "--stdin",
                "--timeout", str(max(1, (timeout_ms + 999) // 1000)),
                "--max-output", "8000000", "--no-snapshot-diff",
                "--format", "json",
            ),
            program=program,
        )
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise AdapterError("webcmd_browser_run_failed")
        data = result.get("result")
        if (
            not isinstance(data, dict)
            or type(data.get("status")) is not int
            or not 100 <= data["status"] <= 599
            or not isinstance(data.get("content_type"), str)
        ):
            raise AdapterError("webcmd_response_invalid")
        return HttpResponse(
            data["status"],
            data.get("body") if data["status"] == 200 else None,
            observed_at=now_utc(),
            content_type=data["content_type"],
        )

    def _provider(self, session: str) -> CurrentCloudEnvironmentProvider:
        return CurrentCloudEnvironmentProvider(
            transport=lambda url, query: self._read(session, url, query),
            scopes=self.scopes,
            page_limit=self.page_limit,
            page_size=self.page_size,
            api_surface="desktop",
            use_picker=False,
        )

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        def read(session: str) -> ProviderResult:
            result = self._provider(session).list_environments(account, include_drafts)
            result.source = "webcmd_current_catalog"
            return result

        return self._run_session(read)

    def get_environment(self, environment_id: str, account=None) -> ProviderResult:
        """Read one known ID on the same preapproved Webcmd browser session."""
        if not valid_configuration_id(environment_id):
            raise ValueError("A safe immutable Current Configuration ID is required")

        def read(session: str) -> ProviderResult:
            result = self._provider(session).get_environment(environment_id, account)
            result.source = "webcmd_current_detail"
            return result

        return self._run_session(read)

    def _run_session(self, read: Callable[[str], ProviderResult]) -> ProviderResult:
        operation = active_operation(60)
        with operation_scope(operation):
            if not Path(self.settings.browser_binary).is_file():
                return ProviderResult(
                    provider=self.name, status="unavailable",
                    reason="webcmd_browser_runtime_missing",
                )
            profiles = self.cli.run(("profile", "list", "-f", "json"))
            if (
                not isinstance(profiles, list)
                or any(not isinstance(row, dict) for row in profiles)
            ):
                raise AdapterError("webcmd_profile_inventory_invalid")
            if not any(
                row.get("contextId") == self.settings.profile
                or row.get("alias") == self.settings.profile
                for row in profiles
            ):
                return ProviderResult(
                    provider=self.name, status="unavailable",
                    reason="webcmd_profile_not_initialized",
                )
            before = self._sessions()
            prefix = _SESSION_PREFIX + uuid4().hex
            if any(identifier.startswith(prefix + "-") for identifier in before):
                return ProviderResult(
                    provider=self.name, status="forbidden",
                    reason="webcmd_session_name_collision",
                )
            created = False
            response: Optional[ProviderResult] = None
            try:
                created = True  # A failed session-create may still have side effects.
                receipt = self.cli.run(("session", "create", prefix, "-f", "json"))
                session_id = receipt.get("id") if isinstance(receipt, dict) else None
                after = self._sessions()
                owned = self._owned(after, set(before), prefix)
                if (
                    not isinstance(session_id, str)
                    or owned != [session_id]
                ):
                    response = ProviderResult(
                        provider=self.name, status="forbidden",
                        reason="webcmd_session_ownership_unverified",
                    )
                    return response
                response = read(session_id)
                return response
            finally:
                if created:
                    # Cleanup uses an independent budget, even after an exception.
                    cleanup_ok = False
                    try:
                        with operation_scope(Operation(12)):
                            rows = self._sessions()
                            new_ids = [
                                identifier for identifier in rows
                                if identifier.startswith(prefix + "-")
                                and identifier not in before
                            ]
                            candidates = self._owned(rows, set(before), prefix)
                            if not new_ids:
                                cleanup_ok = True
                            elif len(new_ids) == 1 and candidates == new_ids:
                                self.cli.run(
                                    ("session", "close", candidates[0],
                                     "--force", "-f", "json")
                                )
                                cleanup_ok = candidates[0] not in self._sessions()
                            # An unexpected/new session on another profile
                            # cannot be closed and is NOT a successful cleanup.
                    except (AdapterError, OSError, RuntimeError):
                        cleanup_ok = False
                    if response is not None:
                        response.coverage["session_cleanup_confirmed"] = cleanup_ok
                        if not cleanup_ok:
                            response.warnings.append(
                                "Webcmd owned session cleanup could not be confirmed"
                            )
                            response.catalog_complete = False
                            if response.status in {"ok", "empty"}:
                                response.status = "partial"
