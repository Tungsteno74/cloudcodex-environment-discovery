"""Read-only current-generation Codex Cloud catalog provider."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence
from common.models import EnvironmentDescriptor, ProviderResult, extract_page, parse_environment
from common.protocols import AuthorizedTransport, _response_failure


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
