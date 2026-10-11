"""Read-only Legacy Codex Cloud catalog provider."""
from __future__ import annotations

from typing import Callable, Optional
from common.models import EnvironmentDescriptor, ProviderResult, extract_page, parse_environment
from common.protocols import AuthorizedTransport, _response_failure


class LegacyEnvironmentProvider:
    """Native selector or authorized Legacy HTTP fallback.

    A text-only CLI 'codex cloud list --json' is explicitly NOT a valid
    environment inventory. The native interactive selector integration can be
    injected by a privileged host without extracting authentication secrets.
    """

    name = "legacy"

    def __init__(
        self,
        selector_reader: Optional[Callable[[Optional[str]], ProviderResult]] = None,
        transport: Optional[AuthorizedTransport] = None,
    ) -> None:
        self._selector_reader = selector_reader
        self._transport = transport

    def list_environments(
        self, account: Optional[str] = None, include_drafts: bool = False
    ) -> ProviderResult:
        if self._selector_reader is not None:
            try:
                result = self._selector_reader(account)
                if result.provider != "legacy":
                    raise ValueError("selector reader returned wrong provider")
                return result
            except (ValueError, OSError, RuntimeError, TypeError):
                return ProviderResult(
                    provider=self.name,
                    status="unavailable",
                    warnings=["Legacy selector read failed; no write fallback allowed"],
                )

        if self._transport is None:
            return ProviderResult(
                provider=self.name,
                status="unavailable",
                warnings=[
                    "Legacy native Codex selector requires an authorized host; "
                    "'codex cloud list --json' lists tasks, not environments"
                ],
            )

        try:
            response = self._transport(
                "https://chatgpt.com/backend-api/wham/environments", {}
            )
        except (OSError, RuntimeError, ValueError, TimeoutError):
            return ProviderResult(
                provider=self.name,
                status="unavailable",
                warnings=["Legacy authenticated transport unavailable"],
            )

        if response.status != 200:
            return _response_failure(self.name, response.status, "user")

        try:
            items, cursor = extract_page(response.body)
            entries = [
                parse_environment(
                    item, "legacy", "user", "legacy_authorized_http",
                    account=None
                )
                for item in items
            ]
        except (ValueError, TypeError, KeyError):
            return ProviderResult(
                provider=self.name,
                status="invalid_response",
                warnings=["Legacy catalog schema unknown; no empty result inferred"],
            )

        if cursor is not None:
            return ProviderResult(
                provider=self.name,
                status="partial",
                environments=entries,
                scope="user",
                evidence="live",
                warnings=["Legacy catalog pagination not implemented for this endpoint"],
            )

        return ProviderResult(
            provider=self.name,
            status="ok" if entries else "empty",
            environments=entries,
            catalog_complete=True,
            scope="user",
            evidence="live",
        )
