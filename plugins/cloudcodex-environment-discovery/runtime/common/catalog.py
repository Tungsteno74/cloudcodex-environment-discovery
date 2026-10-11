"""Complete bounded catalog reads through an already-authorized GET transport."""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, Optional, Sequence

from .adapters import AdapterError
from .models import EnvironmentDescriptor, ProviderResult, extract_page, parse_environment
from .operation import OperationCancelled, OperationTimedOut, checkpoint
from .protocols import AuthorizedTransport, _response_failure


def descriptor_key(item: EnvironmentDescriptor) -> tuple:
    return (item.environment_id, item.configuration_version, item.configuration_state, item.account)


def merge_records(items: Sequence[EnvironmentDescriptor]) -> list:
    """Merge scopes, not different drafts/versions; refuse conflicting IDs."""
    unique: Dict[tuple, EnvironmentDescriptor] = {}
    for item in items:
        key = descriptor_key(item)
        if key not in unique:
            unique[key] = item
            continue
        existing = unique[key]
        # Timestamps and scope can legitimately vary across catalog pages.
        a, b = existing.to_dict(), item.to_dict()
        for field in ("observed_at", "scope", "discovery_source"):
            a.pop(field, None)
            b.pop(field, None)
        if a != b:
            raise ValueError("Conflicting records for one immutable identity")
        scopes = sorted(set(existing.scope.split(",")) | set(item.scope.split(",")))
        unique[key] = replace(existing, scope=",".join(scopes))
    return sorted(unique.values(), key=lambda x: (x.name.casefold(), x.environment_id,
                                                  x.configuration_version or "", x.configuration_state))


class PagedCatalogProvider:
    def __init__(self, cloud_type: str, url: str, transport: Optional[AuthorizedTransport],
                 scopes: Sequence[str], page_limit: int = 12, page_size: int = 100,
                 current_query: bool = False):
        if (isinstance(page_limit, bool) or not isinstance(page_limit, int) or not 1 <= page_limit <= 100
                or isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100):
            raise ValueError("Invalid catalog pagination bounds")
        if not scopes or len(scopes) != len(set(scopes)) or any(s not in {"user", "workspace"} for s in scopes):
            raise ValueError("Invalid catalog scopes")
        self.name, self.url, self.transport = cloud_type, url, transport
        self.scopes = tuple(scopes)
        self.page_limit, self.page_size, self.current_query = page_limit, page_size, current_query

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        if not isinstance(include_drafts, bool) or account is not None and not isinstance(account, str):
            raise ValueError("Invalid catalog request")
        if self.transport is None:
            return ProviderResult(provider=self.name, status="unavailable", reason="transport_not_configured")
        entries, completed, warnings = [], [], []
        observed_account = None
        account_verified = False
        status, reason = None, None
        for scope in self.scopes:
            cursor = None
            visited = set()
            for page in range(self.page_limit):
                checkpoint()
                query = {"scope": scope, "limit": str(self.page_size),
                         "omitDraft": "false" if include_drafts else "true"} if self.current_query else {}
                if cursor is not None:
                    query["cursor"] = cursor
                try:
                    response = self.transport(self.url, query)
                    checkpoint()
                except (OperationCancelled, OperationTimedOut, AdapterError):
                    raise
                except (ValueError, OSError, RuntimeError, TimeoutError):
                    status, reason = "unavailable", "transport_failed"
                    break
                if response.status != 200:
                    failed = _response_failure(self.name, response.status, scope)
                    status, reason = failed.status, "http_" + str(response.status)
                    warnings.extend(failed.warnings)
                    break
                if response.content_type.split(";")[0].strip().lower() != "application/json":
                    status, reason = "forbidden", "security_interstitial_or_non_json"
                    break
                if response.account_verified:
                    if (account is not None and response.account != account
                            or account_verified and response.account != observed_account):
                        status, reason = "forbidden", "account_mismatch"
                        break
                    observed_account, account_verified = response.account, True
                elif account_verified:
                    status, reason = "invalid_response", "lost_account_provenance"
                    break
                try:
                    values, next_cursor = extract_page(response.body)
                    parsed = [parse_environment(
                        value, self.name, scope, self.name + "_authorized_http",
                        account=response.account if response.account_verified else None,
                        observed_at=response.observed_at,
                    ) for value in values]
                    # Commit a page atomically: a malformed item cannot leave
                    # a partial valid-looking page appended to the catalog.
                    entries.extend(parsed)
                except (ValueError, TypeError, KeyError):
                    status, reason = "invalid_response", "catalog_schema_mismatch"
                    break
                if next_cursor is None:
                    completed.append(scope)
                    break
                if next_cursor in visited:
                    status, reason = "partial", "cursor_loop"
                    break
                visited.add(next_cursor)
                cursor = next_cursor
            else:
                status, reason = "partial", "page_limit"
            if status is not None:
                break
        try:
            entries = merge_records(entries)
        except ValueError:
            entries = []
            status, reason = "invalid_response", "conflicting_immutable_identity"
        # Do not discard published/draft versions with the same configuration ID.
        if not include_drafts:
            entries = [item for item in entries if item.configuration_state != "draft"]
        complete = status is None and len(completed) == len(self.scopes)
        if reason:
            warnings.append("Catalog incomplete: " + reason)
        return ProviderResult(
            provider=self.name, status=status or ("ok" if entries else "empty"),
            environments=entries, catalog_complete=complete, scope=",".join(self.scopes),
            evidence="live" if entries or complete else "indirect", warnings=warnings,
            account=observed_account, account_verified=account_verified, reason=reason,
            source=self.name + "_authorized_http",
        )
