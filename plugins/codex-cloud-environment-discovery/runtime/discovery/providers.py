"""Interchangeable, read-only Codex environment catalog providers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence

from .models import (
    EnvironmentDescriptor,
    HttpResponse,
    ProviderResult,
    extract_page,
    parse_environment,
)


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


class CurrentCloudEnvironmentProvider:
    """Current Cloud catalog across user and workspace scopes.

    The current endpoint is an observed internal client contract, not a
    stable public API. No credentials are obtained or stored here.
    """

    name = "current"

    def __init__(
        self,
        transport: Optional[AuthorizedTransport] = None,
        *,
        scopes: Sequence[str] = ("user", "workspace"),
        page_limit: int = 12,
        page_size: int = 100,
    ) -> None:
        self._transport = transport
        if not scopes or any(scope not in {"user", "workspace"} for scope in scopes):
            raise ValueError("scopes must be user and/or workspace")
        if not 1 <= page_limit <= 100 or not 1 <= page_size <= 100:
            raise ValueError("invalid pagination limits")
        self._scopes = tuple(scopes)
        self._page_limit = page_limit
        self._page_size = page_size

    def list_environments(
        self, account: Optional[str] = None, include_drafts: bool = False
    ) -> ProviderResult:
        if self._transport is None:
            return ProviderResult(
                provider=self.name,
                status="unavailable",
                warnings=["Current Cloud has no injected authorized catalog transport"],
            )

        items: List[EnvironmentDescriptor] = []
        completed: List[str] = []
        warnings: List[str] = []
        failure: Optional[str] = None
        for scope in self._scopes:
            cursor: Optional[str] = None
            visited = set()
            for page_number in range(self._page_limit):
                parameters = {
                    "scope": scope,
                    "limit": str(self._page_size),
                    "omitDraft": "false" if include_drafts else "true",
                }
                if cursor is not None:
                    parameters["cursor"] = cursor
                try:
                    response = self._transport(
                        "https://codex-cloud-backend.chatgpt.com/v1/environment-configs",
                        parameters,
                    )
                except (OSError, RuntimeError, ValueError, TimeoutError):
                    failure = "unavailable"
                    warnings.append(f"Current Cloud {scope}: transport failed")
                    break
                if response.status != 200:
                    failed = _response_failure(
                        self.name, response.status, scope
                    )
                    failure = failed.status
                    warnings.extend(failed.warnings)
                    break
                try:
                    page_items, next_cursor = extract_page(response.body)
                    items.extend(
                        parse_environment(
                            value, "current", scope, "current_authorized_http",
                            account=None
                        )
                        for value in page_items
                    )
                except (ValueError, TypeError, KeyError):
                    failure = "invalid_response"
                    warnings.append(
                        f"Current Cloud {scope}: unrecognized schema, not an empty catalog"
                    )
                    break

                if next_cursor is None:
                    completed.append(scope)
                    break
                if next_cursor in visited:
                    failure = "partial"
                    warnings.append(f"Current Cloud {scope}: cursor loop detected")
                    break
                visited.add(next_cursor)
                cursor = next_cursor
            else:
                failure = "partial"
                warnings.append(f"Current Cloud {scope}: page limit reached")

            if failure is not None:
                # Fail closed. Never switch identities, bypass 401/403, or retry
                # with a different user scope after an authorization denial.
                break

        unique: Dict[str, EnvironmentDescriptor] = {}
        for item in items:
            unique.setdefault(item.environment_id, item)
        environments = sorted(
            unique.values(), key=lambda x: (x.name.lower(), x.environment_id)
        )
        is_complete = failure is None and len(completed) == len(self._scopes)
        status = (
            failure or ("ok" if environments else "empty")
        )
        if failure is not None and environments:
            # Partial data is useful but must never look exhaustive.
            warnings.append("Results before the failed scope are partial")
        return ProviderResult(
            provider=self.name,
            status=status,
            environments=environments,
            catalog_complete=is_complete,
            scope=",".join(self._scopes),
            evidence="live" if completed else "indirect",
            warnings=warnings,
        )


class SnapshotEnvironmentProvider:
    """Read-only imported evidence; never claims to be live or complete."""

    def __init__(
        self, cloud_type: str, payload: Any, source_name: str = "imported_snapshot"
    ) -> None:
        if cloud_type not in {"legacy", "current"}:
            raise ValueError("invalid snapshot cloud type")
        self.name = cloud_type
        self._payload = payload
        self._source = source_name

    @classmethod
    def from_file(
        cls, cloud_type: str, path: Path
    ) -> "SnapshotEnvironmentProvider":
        # The CLI opts into catalog snapshots explicitly, never credential files.
        parts = {part.casefold() for part in path.parts}
        if (path.name.casefold() in {"auth.json", "credentials.json", ".env"}
                or ".codex" in parts):
            raise ValueError("credential paths cannot be used as catalogs")
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("catalog snapshot exceeds size limit")
        return cls(
            cloud_type=cloud_type,
            payload=json.loads(path.read_text(encoding="utf-8")),
        )

    def list_environments(
        self, account: Optional[str] = None, include_drafts: bool = False
    ) -> ProviderResult:
        try:
            entries, cursor = extract_page(self._payload)
            parsed = [
                parse_environment(
                    item, self.name, "imported", self._source,
                    evidence="imported", account=account
                )
                for item in entries
            ]
        except (ValueError, TypeError, KeyError):
            return ProviderResult(
                provider=self.name,
                status="invalid_response",
                warnings=["Imported snapshot is not a recognized catalog"],
            )
        if not include_drafts:
            parsed = [
                item for item in parsed
                if item.configuration_state != "draft"
            ]
        return ProviderResult(
            provider=self.name,
            status="partial",
            environments=parsed,
            catalog_complete=False,
            scope="imported",
            evidence="imported",
            warnings=[
                "Imported snapshots are candidate evidence, not a live catalog",
                *(
                    ["Imported snapshot contains an unconsumed cursor"]
                    if cursor else []
                ),
            ],
        )
