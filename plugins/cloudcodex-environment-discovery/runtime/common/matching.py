"""Repository association uses explicit IDs/names, not environment labels."""
from __future__ import annotations

from .models import EnvironmentDescriptor, normalize_repository


def repository_match(environment: EnvironmentDescriptor, repository: str) -> str:
    if not isinstance(repository, str) or not repository.strip():
        raise ValueError("Invalid repository identifier")
    requested = repository.strip()
    associations = list(environment.repositories) + [
        {"repository": environment.repository, "repository_id": environment.repository_id}
    ]
    if requested.isdecimal():
        return "verified" if any(a.get("repository_id") == requested for a in associations) else "none"
    normalized = normalize_repository(requested)
    if normalized is None:
        raise ValueError("Repository must be a numeric ID or GitHub owner/repo")
    if any(normalize_repository(a.get("repository")) == normalized for a in associations):
        return "verified"
    if environment.name.strip().casefold() in {normalized, normalized.split("/")[1]}:
        return "hint"
    return "none"
