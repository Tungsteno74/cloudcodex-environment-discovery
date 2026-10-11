"""Read-only Codex Cloud environment discovery.

The package never accesses stored credentials or creates Cloud tasks.
"""
from .models import EnvironmentDescriptor, ProviderResult, HttpResponse
from .providers import CurrentCloudEnvironmentProvider, LegacyEnvironmentProvider, SnapshotEnvironmentProvider
from .service import DiscoveryFacade

__all__ = [
    "EnvironmentDescriptor",
    "ProviderResult",
    "HttpResponse",
    "CurrentCloudEnvironmentProvider",
    "LegacyEnvironmentProvider",
    "SnapshotEnvironmentProvider",
    "DiscoveryFacade",
]
