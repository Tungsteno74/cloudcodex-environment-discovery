"""Current-generation catalog adapter, independent of Legacy implementation."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Mapping, Optional, Sequence

from common.adapters import CURRENT_CATALOG_SURFACES
from common.catalog import PagedCatalogProvider
from common.models import HttpResponse, ProviderResult
from common.protocols import AuthorizedTransport
from .detail import read_current_detail


class CurrentCloudEnvironmentProvider(PagedCatalogProvider):
    """Current catalog using the client-observed picker/list sequence.

    For published configurations the installed Desktop client first requests
    ``view=picker``. Only HTTP 400 means "picker contract unsupported" and
    permits one fallback to the standard list on the same endpoint/identity.
    Authentication/authorization failures are returned unchanged.

    Explicit draft inclusion skips picker view because the observed picker
    contract always uses ``omitDraft=true`` and therefore cannot attest draft
    coverage.
    """

    name = "current"

    def __init__(
        self,
        transport: Optional[AuthorizedTransport] = None,
        *,
        scopes: Sequence[str] = ("user", "workspace"),
        page_limit: int = 12,
        page_size: int = 100,
        api_surface: str = "desktop",
        use_picker: bool = True,
    ):
        if api_surface not in CURRENT_CATALOG_SURFACES or type(use_picker) is not bool:
            raise ValueError("Unknown Current catalog surface or picker setting")
        self._authorized_transport = transport
        self._base_url = CURRENT_CATALOG_SURFACES[api_surface]
        # Per-call indicator: ContextVar keeps shared provider use isolated
        # across threads/async operations without widening transport schemas.
        self._picker_seen = ContextVar("current_picker_seen", default=False)
        # The picker contract was observed on Desktop only. Keep the web
        # proxy on its independently observed standard-list GET surface.
        wrapped = (
            self._picker_transport
            if transport is not None and api_surface == "desktop" and use_picker
            else transport
        )
        super().__init__(
            "current",
            CURRENT_CATALOG_SURFACES[api_surface],
            wrapped,
            scopes,
            page_limit,
            page_size,
            current_query=True,
        )

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        """Distinguish picker-page completion from complete Cloud coverage."""
        token = self._picker_seen.set(False)
        try:
            result = super().list_environments(
                account=account, include_drafts=include_drafts
            )
            if self._picker_seen.get():
                # Picker is a published saved-config selection view, not a
                # guarantee that all configurations are represented.
                result.catalog_complete = False
                result.coverage["picker_view_only"] = True
                if result.status in {"ok", "empty"}:
                    result.status = "partial"
                result.warnings.append(
                    "Current picker coverage cannot prove absence from the full catalog"
                )
            return result
        finally:
            self._picker_seen.reset(token)

    def get_environment(self, environment_id: str, account=None) -> ProviderResult:
        """Read one exact ID before catalog fallback; never imply catalog completeness."""
        if self._base_url != CURRENT_CATALOG_SURFACES["desktop"]:
            return ProviderResult(
                provider=self.name, status="unavailable",
                reason="point_route_not_observed_on_web",
                coverage={"point_verified": False},
            )
        return read_current_detail(
            self._authorized_transport, self._base_url, environment_id, account,
        )

    def _picker_transport(self, url: str, query: Mapping[str, str]) -> HttpResponse:
        if self._authorized_transport is None:
            raise RuntimeError("Current authorized transport is unavailable")
        if query.get("omitDraft") != "true":
            return self._authorized_transport(url, query)

        picker_query = dict(query)
        picker_query["view"] = "picker"
        response = self._authorized_transport(url, picker_query)
        if response.status == 200:
            self._picker_seen.set(True)
            return response
        if response.status != 400:
            return response

        # Exact installed-client retry condition: HTTP 400 only, same host,
        # account and scope. Unlike the UI picker, full discovery must not
        # discard standard-list rows whose versionRevision is <= 1.
        # Filtering those rows could falsely prove a missing environment.
        return self._authorized_transport(url, query)
