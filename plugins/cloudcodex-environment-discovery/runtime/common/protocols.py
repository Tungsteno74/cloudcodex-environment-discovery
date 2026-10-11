"""Provider protocols and safe HTTP failure classification."""
from __future__ import annotations

from typing import Mapping, Optional, Protocol
from .models import HttpResponse, ProviderResult


class AuthorizedTransport(Protocol):
    """Injected transport; must already have legitimate authorization."""

    def __call__(
        self, url: str, parameters: Mapping[str, str]
    ) -> HttpResponse:
        ...


class EnvironmentProvider(Protocol):
    name: str

    def list_environments(
        self, account: Optional[str] = None, include_drafts: bool = False
    ) -> ProviderResult:
        ...


def _response_failure(
    provider: str, code: int, scope: str
) -> ProviderResult:
    if code == 401:
        status = "unauthorized"
    elif code == 403:
        status = "forbidden"
    elif code == 404:
        status = "not_found"
    else:
        status = "unavailable"
    return ProviderResult(
        provider=provider,
        status=status,
        scope=scope,
        warnings=[f"{provider}: HTTP {code}; catalog not authoritative"],
    )
