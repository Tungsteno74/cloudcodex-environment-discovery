"""Public logical operations and restricted offline evidence fixtures."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .providers import (
    CurrentCloudEnvironmentProvider, LegacyEnvironmentProvider,
    SnapshotEnvironmentProvider,
)
from .service import DiscoveryFacade


def build_default_facade() -> DiscoveryFacade:
    """No implicit credentials, network calls or browser automation."""
    return DiscoveryFacade({
        "legacy": LegacyEnvironmentProvider(),
        "current": CurrentCloudEnvironmentProvider(),
    })


def build_snapshot_facade(
    legacy: Optional[Path] = None, current: Optional[Path] = None
) -> DiscoveryFacade:
    """Explicit CLI-only imported evidence; never claims live verification."""
    providers = {}
    if legacy is not None:
        providers["legacy"] = SnapshotEnvironmentProvider.from_file(
            "legacy", legacy
        )
    if current is not None:
        providers["current"] = SnapshotEnvironmentProvider.from_file(
            "current", current
        )
    return DiscoveryFacade(providers)
