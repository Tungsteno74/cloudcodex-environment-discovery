"""Common GitHub repository association: explicit IDs/names outrank hints."""
from __future__ import annotations

from .models import EnvironmentDescriptor, normalize_repository


def repository_match(
    environment: EnvironmentDescriptor, repository: str
) -> str:
    """Return verified, hint or none; never infer an association from a label."""
    requested = repository.strip()
    if requested.isdecimal() and environment.repository_id == requested:
        return "verified"
    normalized = normalize_repository(requested)
    if normalized is None:
        raise ValueError("repository must be owner/repo, GitHub URL or numeric repository ID")
    if environment.repository == normalized:
        return "verified"
    # Label matching is an explicit, low-confidence hint, not verification.
    if environment.name.lower().strip() in {normalized, normalized.split("/")[1]}:
        return "hint"
    return "none"
