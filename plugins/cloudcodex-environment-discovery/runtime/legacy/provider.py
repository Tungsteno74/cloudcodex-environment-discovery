"""Legacy catalog provider; it never imports the current-generation provider."""
from __future__ import annotations

from typing import Callable, Optional

from common.catalog import PagedCatalogProvider
from common.models import ProviderResult
from common.operation import OperationCancelled, OperationTimedOut, checkpoint
from common.protocols import AuthorizedTransport


class LegacyEnvironmentProvider:
    """Native reader preferred; HTTP is an explicitly supplied read-only fallback."""

    name = "legacy"

    def __init__(self, selector_reader: Optional[Callable[[Optional[str]], ProviderResult]] = None,
                 transport: Optional[AuthorizedTransport] = None, *, page_limit: int = 12):
        self._selector_reader = selector_reader
        self._transport = transport
        self._http = PagedCatalogProvider(
            "legacy", "https://chatgpt.com/backend-api/wham/environments",
            transport, ("user",), page_limit=page_limit,
        )

    def list_environments(self, account: Optional[str] = None,
                          include_drafts: bool = False) -> ProviderResult:
        checkpoint()
        if self._selector_reader is not None:
            try:
                result = self._selector_reader(account)
                if result.provider != self.name:
                    raise ValueError("Native reader returned a different provider")
                # Configurable escalation is handled outside this adapter. The
                # native result is not silently replaced or broadened here.
                return result
            except (OperationCancelled, OperationTimedOut):
                raise
            except (ValueError, OSError, RuntimeError, TypeError):
                return ProviderResult(provider=self.name, status="unavailable",
                                      reason="native_reader_failed",
                                      warnings=["Native selector read failed"])
        if self._transport is None:
            return ProviderResult(
                provider=self.name, status="unavailable", reason="native_adapter_not_connected",
                warnings=["An authorized Legacy catalog adapter is required; codex cloud list --json lists tasks, not environments"],
            )
        return self._http.list_environments(account=account, include_drafts=include_drafts)

    def find_environments(self, repository, account=None, include_drafts=False):
        """By-repository GET proves association without guessing from labels."""
        from dataclasses import replace
        from common.models import normalize_repository
        from common.matching import repository_match
        normalized = normalize_repository(repository)
        if normalized is None or self._transport is None or self._selector_reader is not None:
            return self.list_environments(account=account, include_drafts=include_drafts)
        reader = PagedCatalogProvider(
            "legacy", "https://chatgpt.com/backend-api/wham/environments/by-repo/github/" + normalized,
            self._transport, ("user",), page_limit=self._http.page_limit,
        )
        result = reader.list_environments(account=account, include_drafts=include_drafts)
        associated = []
        for item in result.environments:
            if item.repository or item.repositories:
                if repository_match(item, normalized) != "verified":
                    return ProviderResult(provider="legacy", status="invalid_response",
                                          reason="by_repo_association_conflict")
                associated.append(item)
            else:
                associated.append(replace(item, repository=normalized,
                                          discovery_source="legacy_authorized_by_repo"))
        result.environments = associated
        result.scope = "repository:" + normalized
        return result
