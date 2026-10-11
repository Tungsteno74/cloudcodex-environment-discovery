"""Join an observed Cloud catalog to the same operator's GitHub inventory.

Names are candidate links, not proof of environment existence or association.
Repository enumeration never creates Cloud rows or promotes completeness.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .github import match_verified_repository
from .models import EnvironmentDescriptor


def correlate_repositories(environments: Sequence[Mapping], inventory: Mapping) -> list:
    if inventory.get("status") != "ok" or not inventory.get("catalog_complete"):
        return []
    correlations = []
    for record in environments:
        environment = EnvironmentDescriptor(**record)
        candidates = []
        for repository in inventory.get("repositories", []):
            evidence = dict(repository, status="verified")
            matched = match_verified_repository(environment, evidence)
            if matched != "none":
                candidates.append(
                    {
                        "repository": repository["repository"],
                        "repository_id": repository["repository_id"],
                        "association": "explicit" if matched == "verified" else "name_candidate",
                        "confidence": matched,
                    }
                )
        verified = [row for row in candidates if row["confidence"] == "verified"]
        correlations.append(
            {
                "cloud_type": environment.cloud_type,
                "environment_id": environment.environment_id,
                "environment_name": environment.name,
                "repositories": verified or candidates,
                "association_verified": bool(verified),
                "environment_created_from_repository_name": False,
            }
        )
    return correlations
