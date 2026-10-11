"""Explicit, untrusted offline snapshots; never treated as live."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from .models import ProviderResult, extract_page, parse_environment


class SnapshotEnvironmentProvider:
    """Read-only imported evidence; never claims to be live or complete."""

    def __init__(
        self, cloud_type: str, payload: Any, source_name: str = "imported_snapshot"
    ) -> None:
        if not isinstance(cloud_type, str) or not cloud_type.strip():
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
        # Resolve aliases before opening an explicitly supplied catalog file.
        if path.exists():
            path = path.resolve(strict=True)
            parts |= {part.casefold() for part in path.parts}
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
                    evidence="imported", account=None,
                    observed_at=self._payload.get("observed_at") if isinstance(self._payload, dict) else None
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
