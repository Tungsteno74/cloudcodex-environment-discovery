"""Explicit, untrusted offline snapshots; never treated as live."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from .models import ProviderResult, extract_page, parse_environment


def read_evidence_file(path: Path) -> Any:
    """Read only explicit bounded evidence, never session/credential paths."""
    path = Path(path)
    names = {part.casefold() for part in path.parts}
    if path.exists():
        path = path.resolve(strict=True)
        names |= {part.casefold() for part in path.parts}
    if path.name.casefold() in {"auth.json", "credentials.json", ".env"} or ".codex" in names:
        raise ValueError("Credential paths cannot be used as evidence")
    maximum = 8 * 1024 * 1024
    if path.stat().st_size > maximum:
        raise ValueError("Evidence file exceeds size limit")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Evidence file exceeds size limit")
    return json.loads(data.decode("utf-8"))


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
        return cls(cloud_type=cloud_type, payload=read_evidence_file(path))

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
