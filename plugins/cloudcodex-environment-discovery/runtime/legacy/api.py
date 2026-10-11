"""Legacy-only discovery entry points; never initializes the current provider."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from common.service import EnvironmentDiscoveryService
from common.snapshot import SnapshotEnvironmentProvider
from .provider import LegacyEnvironmentProvider


def build_legacy_service(
    provider: Optional[LegacyEnvironmentProvider] = None,
) -> EnvironmentDiscoveryService:
    return EnvironmentDiscoveryService(
        "legacy", provider if provider is not None else LegacyEnvironmentProvider()
    )


def build_legacy_snapshot_service(path: Path) -> EnvironmentDiscoveryService:
    return EnvironmentDiscoveryService(
        "legacy", SnapshotEnvironmentProvider.from_file("legacy", path)
    )
