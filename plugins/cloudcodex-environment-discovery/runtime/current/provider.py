"""Current-generation catalog adapter, independent of Legacy implementation."""

from __future__ import annotations

from typing import Optional, Sequence

from common.catalog import PagedCatalogProvider
from common.adapters import CURRENT_CATALOG_SURFACES
from common.protocols import AuthorizedTransport


class CurrentCloudEnvironmentProvider(PagedCatalogProvider):
    """User/workspace pagination and drafts over an authorized read-only transport.

    The observed endpoint is an internal client contract, not a stable public API.
    Authentication must remain in an explicitly approved host or connector.
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
    ):
        if api_surface not in CURRENT_CATALOG_SURFACES:
            raise ValueError("Unknown Current catalog surface")
        super().__init__(
            "current",
            CURRENT_CATALOG_SURFACES[api_surface],
            transport,
            scopes,
            page_limit,
            page_size,
            current_query=True,
        )
