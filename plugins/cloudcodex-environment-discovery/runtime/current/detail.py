"""Read one known Current Configuration ID without enumerating the catalog.

The route is observed in the installed Codex Desktop client. A successful
point read verifies only that object, NEVER the whole Current Cloud inventory.
Current API access remains authorization-dependent; 401/403 are terminal.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional
from urllib.parse import quote

from common.models import HttpResponse, ProviderResult, now_utc, parse_environment
from common.protocols import AuthorizedTransport, _response_failure

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")
_WRAPPERS = ("config", "configuration", "data")


def valid_configuration_id(value: Any) -> bool:
    """Accept only one encoded-safe opaque path segment, never a guessed name."""
    return isinstance(value, str) and bool(_ID.fullmatch(value)) and value not in {".", ".."}


def direct_configuration_url(base_url: str, configuration_id: str) -> str:
    if not valid_configuration_id(configuration_id):
        raise ValueError("A safe immutable Current Configuration ID is required")
    return base_url + "/" + quote(configuration_id, safe="")


def _record_from_body(body: Any) -> Mapping[str, Any]:
    """Handle observed detail envelopes, rejecting competing record shapes."""
    if not isinstance(body, dict):
        raise ValueError("Current detail is not a JSON object")
    present = [key for key in _WRAPPERS if key in body]
    if len(present) > 1:
        raise ValueError("Ambiguous Current detail envelope")
    if present:
        record = body[present[0]]
        if not isinstance(record, dict):
            raise ValueError("Current detail record is not an object")
        return record
    return body


def read_current_detail(
    transport: Optional[AuthorizedTransport],
    base_url: str,
    configuration_id: str,
    account: Optional[str] = None,
) -> ProviderResult:
    """Use the same authorized transport as list, with strict point semantics."""
    url = direct_configuration_url(base_url, configuration_id)
    if account is not None and (not isinstance(account, str) or not account):
        raise ValueError("Invalid account identity")
    if transport is None:
        return ProviderResult(
            provider="current", status="unavailable", reason="transport_not_configured",
            coverage={"point_verified": False},
        )
    response: HttpResponse = transport(url, {})
    if response.status != 200:
        failed = _response_failure("current", response.status, "point")
        failed.reason = "http_" + str(response.status)
        failed.coverage["point_verified"] = False
        failed.catalog_complete = False
        return failed
    if response.content_type.split(";")[0].strip().lower() != "application/json":
        return ProviderResult(
            provider="current", status="forbidden",
            reason="security_interstitial_or_non_json",
            coverage={"point_verified": False},
        )
    if account is not None and (
        not response.account_verified or response.account != account
    ):
        return ProviderResult(
            provider="current", status="forbidden",
            reason="point_account_unverified_or_mismatch",
            coverage={"point_verified": False},
        )
    try:
        record = _record_from_body(response.body)
        record_account = record.get("account")
        if (
            response.account_verified
            and record_account is not None
            and record_account != response.account
        ):
            return ProviderResult(
                provider="current", status="forbidden",
                reason="point_account_mismatch",
                coverage={"point_verified": False},
            )
        entry = parse_environment(
            record, "current", "point", "current_direct_detail",
            account=response.account if response.account_verified else None,
            observed_at=response.observed_at or now_utc(),
        )
        if entry.environment_id != configuration_id:
            raise ValueError("Current response has a different Configuration ID")
    except (ValueError, KeyError, TypeError, AttributeError):
        return ProviderResult(
            provider="current", status="invalid_response",
            reason="point_identity_or_schema_mismatch",
            coverage={"point_verified": False},
        )
    return ProviderResult(
        provider="current", status="ok", environments=[entry],
        catalog_complete=False, evidence="live", scope="point",
        account=response.account if response.account_verified else None,
        account_verified=response.account_verified,
        reason=None, source="current_direct_detail",
        coverage={"point_verified": True, "point_only": True},
        warnings=["One Current Configuration ID verified; complete catalog not established"],
    )
