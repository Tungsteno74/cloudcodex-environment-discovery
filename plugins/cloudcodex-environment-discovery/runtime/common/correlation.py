"""Repository correlation and repository-to-environment counterpart evidence.

GitHub identity is an independent read source. It never creates Cloud rows and a
successful GitHub lookup never overrides a denied/incomplete Cloud catalog.
Current configurations can be verified by their explicit repository_id, matching
the relationship used by the installed Current client.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from .github import match_verified_repository
from .models import EnvironmentDescriptor, normalize_repository


_VERIFIED_BASES = frozenset({"repository_id", "repository_name"})


def _fresh_live(environment: EnvironmentDescriptor, max_age_seconds: float = 60.0) -> bool:
    if environment.evidence != "live":
        return False
    try:
        observed = datetime.fromisoformat(environment.observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        return -5 <= age <= max_age_seconds
    except (AttributeError, TypeError, ValueError):
        return False


def repository_match_basis(
    environment: EnvironmentDescriptor,
    repository: str,
    repository_evidence: Optional[Mapping] = None,
) -> str:
    """Return the strongest observed association without upgrading name hints."""

    associations = list(environment.repositories) + [
        {"repository": environment.repository, "repository_id": environment.repository_id}
    ]
    if repository_evidence is not None and repository_evidence.get("status") == "verified":
        identifier = repository_evidence.get("repository_id")
        canonical = normalize_repository(repository_evidence.get("repository"))
        if isinstance(identifier, str) and any(
            item.get("repository_id") == identifier for item in associations
        ):
            return "repository_id"
        if canonical is not None:
            named = [
                item
                for item in associations
                if normalize_repository(item.get("repository")) == canonical
            ]
            if named:
                if any(item.get("repository_id") not in (None, identifier) for item in named):
                    return "none"
                return "repository_name"
            if environment.name.strip().casefold() in {
                canonical,
                canonical.split("/")[1],
            }:
                return "environment_name"
        return "none"

    requested = repository.strip()
    if requested.isdecimal():
        if any(item.get("repository_id") == requested for item in associations):
            return "repository_id"
        return "none"
    canonical = normalize_repository(requested)
    if canonical is None:
        raise ValueError("Repository must be a numeric ID or GitHub owner/repo")
    if any(normalize_repository(item.get("repository")) == canonical for item in associations):
        return "repository_name"
    if environment.name.strip().casefold() in {canonical, canonical.split("/")[1]}:
        return "environment_name"
    return "none"


def repository_counterpart(
    environments: Sequence[Mapping],
    repository: str,
    repository_evidence: Optional[Mapping],
    *,
    cloud_catalog_status: str,
    cloud_catalog_complete: bool,
) -> dict:
    """Classify whether a repository has an observed Cloud counterpart.

    A verified explicit repository ID/name proves existence of the returned
    configuration even if the larger catalog is partial. Absence is provable
    only from a complete Cloud catalog. Environment-name equality is only a
    candidate and never yields a Configuration/Environment ID by inference.
    """

    canonical = (
        normalize_repository(repository_evidence.get("repository"))
        if repository_evidence is not None
        else normalize_repository(repository)
    )
    repository_id = (
        repository_evidence.get("repository_id")
        if repository_evidence is not None
        and repository_evidence.get("status") == "verified"
        else repository.strip()
        if repository.strip().isdecimal()
        else None
    )
    verified, candidates = [], []
    for record in environments:
        environment = EnvironmentDescriptor(**record)
        basis = repository_match_basis(environment, repository, repository_evidence)
        if basis == "none":
            continue
        item = {
            "environment_id": environment.environment_id,
            "environment_name": environment.name,
            "matching_basis": basis,
            "configuration_state": environment.configuration_state,
            "evidence": environment.evidence,
        }
        if basis in _VERIFIED_BASES and _fresh_live(environment):
            verified.append(item)
        else:
            if basis in _VERIFIED_BASES:
                item["verification_reason"] = "explicit_association_requires_fresh_live_evidence"
            candidates.append(item)

    if verified:
        status = "verified"
    elif candidates:
        status = "candidate"
    elif cloud_catalog_complete:
        status = "not_found"
    else:
        status = "not_verifiable"

    expected_names = []
    if canonical is not None:
        # Historical Current observations used the repo basename, while Legacy
        # frequently exposed owner/repo. Both are hints only.
        expected_names = [canonical.split("/")[1], canonical]

    return {
        "status": status,
        "repository": canonical or repository,
        "repository_id": repository_id,
        "repository_verified": bool(
            repository_evidence is not None
            and repository_evidence.get("status") == "verified"
        ),
        "cloud_environment_verified": bool(verified),
        "absence_verified": status == "not_found",
        "verified_matches": verified,
        "candidate_matches": candidates,
        "candidate_environment_names": expected_names if not verified else [],
        "cloud_catalog_status": cloud_catalog_status,
        "cloud_catalog_complete": cloud_catalog_complete,
        "rule": "repository_id > explicit repository name > environment-name hint",
    }


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
