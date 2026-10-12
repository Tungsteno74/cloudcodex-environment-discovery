"""Current catalog via an approved, existing isolated BrowserAct Chrome session.

Uses the ordinary same-origin web GET and lets the browser authenticate itself.
No cookie/token reads, imports, profile cloning, challenge solving, proxy changes
or primary-desktop input are available through this adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Callable, Mapping, Optional
from urllib.parse import urlencode
from uuid import uuid4

from common.adapters import AdapterError, CommandClient, CommandSpec
from common.models import HttpResponse, ProviderResult, now_utc
from common.operation import Operation, active_operation, operation_scope
from .provider import CurrentCloudEnvironmentProvider


@dataclass(frozen=True)
class BrowserSettings:
    executable: str
    sha256: str
    browser_id: str
    timeout: float = 15.0

    @classmethod
    def from_mapping(cls, value: Mapping) -> "BrowserSettings":
        if not isinstance(value, dict) or set(value) - {
            "executable",
            "sha256",
            "browser_id",
            "timeout",
        }:
            raise ValueError("Invalid Current browser settings")
        exe, digest, browser_id = (
            value.get("executable"),
            value.get("sha256"),
            value.get("browser_id"),
        )
        if (
            not isinstance(exe, str)
            or not Path(exe).is_absolute()
            or Path(exe).name.lower() not in {"browser-act", "browser-act.exe"}
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
            or not isinstance(browser_id, str)
            or not re.fullmatch(r"chrome_local_[0-9]+", browser_id)
        ):
            raise ValueError(
                "Only a pinned native CLI and an existing isolated Chrome browser are supported"
            )
        timeout = value.get("timeout", 15)
        if type(timeout) not in {int, float} or not 1 <= timeout <= 60:
            raise ValueError("Invalid browser read timeout")
        return cls(exe, digest, browser_id, float(timeout))


class BrowserActCatalogProvider:
    name = "current"

    def __init__(
        self,
        settings: BrowserSettings,
        scopes=("user", "workspace"),
        page_limit=12,
        page_size=100,
        client_factory: Callable = CommandClient,
    ):
        self.settings, self.scopes = settings, scopes
        self.page_limit, self.page_size = page_limit, page_size
        self._client_factory = client_factory

    def _command(self, arguments: tuple) -> dict:
        spec = CommandSpec(
            (self.settings.executable, "--format", "json", "--no-auto-dialog") + arguments,
            ((self.settings.executable, self.settings.sha256),),
            str(Path(self.settings.executable).parent),
            self.settings.timeout,
        )
        response = self._client_factory(spec).request({})
        if response.get("ok") is not True:
            raise AdapterError("browser_command_failed_or_confirmation_required")
        return response

    def _transport(self, session: str, url: str, parameters: Mapping[str, str]) -> HttpResponse:
        if url != "https://chatgpt.com/api/codex-cloud/v1/environment-configs":
            raise AdapterError("unapproved_catalog_destination")
        relative = "/api/codex-cloud/v1/environment-configs?" + urlencode(parameters)
        timeout_ms = max(1, int(min(active_operation().remaining(), self.settings.timeout) * 1000))
        # Only ordinary same-origin GET. Browser handles existing session state;
        # the JS does not inspect document.cookie, storage or application tokens.
        script = """(async()=>{
 const abort=new AbortController();
 const timer=setTimeout(()=>abort.abort(),TIMEOUT);
 try {
  const r=await fetch(PATH,{method:'GET',credentials:'include',redirect:'error',
   headers:{Accept:'application/json'},signal:abort.signal});
  const type=r.headers.get('content-type')||'';
  const out={status:r.status,content_type:type,body:null};
  if(r.ok && type.split(';')[0].trim()==='application/json'){
   const text=await r.text();
   if(text.length>8388608) return {status:502,content_type:'application/json',body:null};
   out.body=JSON.parse(text);
  }
  return out;
 } finally { clearTimeout(timer); }
})()""".replace("TIMEOUT", str(timeout_ms)).replace("PATH", json.dumps(relative))
        response = self._command(("--session", session, "eval", script))
        data = response.get("result")
        if not isinstance(data, dict):
            raise AdapterError("browser_eval_envelope_unknown")
        status, content_type = data.get("status"), data.get("content_type")
        if type(status) is not int or not isinstance(content_type, str):
            raise AdapterError("browser_catalog_response_invalid")
        return HttpResponse(
            status,
            data.get("body") if status == 200 else None,
            observed_at=now_utc(),
            content_type=content_type,
        )

    def _session_record(self, session: str) -> Optional[Mapping]:
        """Find one named session using BrowserAct's authoritative session list.

        The "reused" field returned by browser open describes reuse of the
        persistent browser, not ownership of a freshly named session.
        """
        response = self._command(("session", "list"))
        sessions = response.get("sessions")
        if not isinstance(sessions, list):
            raise AdapterError("browser_session_inventory_invalid")
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("session_name"), str)
            for item in sessions
        ):
            raise AdapterError("browser_session_inventory_invalid")
        matches = [item for item in sessions if item["session_name"] == session]
        if len(matches) > 1:
            raise AdapterError("browser_session_identity_ambiguous")
        return matches[0] if matches else None

    def _owns_session(self, session: str) -> bool:
        record = self._session_record(session)
        return record is not None and self._owns_record(record)

    def _close_owned_session(self, session: str) -> bool:
        """Close only a uniquely named session verified on the target browser."""
        record = self._session_record(session)
        if record is None:
            return True
        if not self._owns_record(record):
            return False
        self._command(("session", "close", session))
        return self._session_record(session) is None

    def _owns_record(self, record: Mapping) -> bool:
        return (
            record.get("browser_id") == self.settings.browser_id
            and record.get("browser_type") == "chrome"
        )

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        operation = active_operation(45)
        with operation_scope(operation):
            metadata = self._command(("browser", "list", self.settings.browser_id))
            browsers = metadata.get("browsers", [])
            if (
                len(browsers) != 1
                or browsers[0].get("id") != self.settings.browser_id
                or browsers[0].get("type") != "chrome"
            ):
                return ProviderResult(
                    provider=self.name,
                    status="forbidden",
                    reason="isolated_browser_identity_not_verified",
                )
            if browsers[0].get("confirm_before_use") is True:
                return ProviderResult(
                    provider=self.name,
                    status="approval_required",
                    reason="browser_confirmation_required",
                )
            session = "cloudcodex-catalog-" + uuid4().hex
            created_after_precheck = False
            result = None
            try:
                # A random name alone is not sufficient ownership proof.
                # Check that no pre-existing session has our chosen identity.
                if self._session_record(session) is not None:
                    return ProviderResult(
                        provider=self.name,
                        status="forbidden",
                        reason="browser_session_name_collision",
                    )
                created_after_precheck = True
                response = self._command(
                    (
                        "--session",
                        session,
                        "browser",
                        "open",
                        self.settings.browser_id,
                        "https://chatgpt.com/",
                    )
                )

                # BrowserAct may report the persistent browser as "workbench"
                # or mark it reused. Neither describes ownership of the newly
                # named session. The session inventory supplies its real ID.
                owned = self._owns_session(session)
                if (
                    not owned
                    or response.get("session_name") != session
                    or response.get("browser_type") != "chrome"
                ):
                    result = ProviderResult(
                        provider=self.name,
                        status="forbidden",
                        reason="unexpected_browser_session",
                        warnings=[
                            "Catalog GET skipped: new session ownership was not confirmed"
                        ],
                    )
                    return result
                provider = CurrentCloudEnvironmentProvider(
                    transport=lambda url, query: self._transport(session, url, query),
                    scopes=self.scopes,
                    page_limit=self.page_limit,
                    page_size=self.page_size,
                    api_surface="web",
                )
                result = provider.list_environments(account=account, include_drafts=include_drafts)
                result.source = "browseract_web_catalog"
                return result
            finally:
                if created_after_precheck:
                    # Even a failed open may have created our session: reconcile
                    # real state before cleanup. Never close other sessions or
                    # the persistent browser. Cleanup has an independent budget.
                    try:
                        with operation_scope(Operation(12)):
                            cleanup_ok = self._close_owned_session(session)
                    except (AdapterError, OSError, RuntimeError):
                        cleanup_ok = False
                        if result is None:
                            raise
                    if result is not None:
                        result.coverage["session_cleanup_confirmed"] = cleanup_ok
                        if not cleanup_ok:
                            result.warnings.append(
                                "Owned browser session cleanup was not confirmed"
                            )
