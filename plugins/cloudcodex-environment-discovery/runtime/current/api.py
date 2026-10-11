"""Current-only discovery entry points; never initializes Legacy."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from common.service import EnvironmentDiscoveryService
from common.snapshot import SnapshotEnvironmentProvider
from .provider import CurrentCloudEnvironmentProvider


def build_current_service(
    provider: Optional[CurrentCloudEnvironmentProvider] = None,
) -> EnvironmentDiscoveryService:
    return EnvironmentDiscoveryService(
        "current", provider if provider is not None else CurrentCloudEnvironmentProvider()
    )


def build_current_snapshot_service(path: Path) -> EnvironmentDiscoveryService:
    return EnvironmentDiscoveryService(
        "current", SnapshotEnvironmentProvider.from_file("current", path)
    )
