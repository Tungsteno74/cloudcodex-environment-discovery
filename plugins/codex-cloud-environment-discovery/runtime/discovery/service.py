"""Read-only facade, repository matching and conservative environment resolution."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .models import (
    EnvironmentDescriptor,
    ProviderResult,
    normalize_repository,
    now_utc,
    require_cloud_type,
)
from .providers import EnvironmentProvider


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


class DiscoveryFacade:
    """Combines providers without elevating stale or incomplete evidence."""

    def __init__(self, providers: Mapping[str, EnvironmentProvider]) -> None:
        self._providers = dict(providers)
        if any(key not in {"legacy", "current"} for key in providers):
            raise ValueError("only legacy/current providers are supported")

    def list_environments(
        self,
        account: Optional[str] = None,
        cloud_type: str = "all",
        include_drafts: bool = False,
    ) -> Dict[str, Any]:
        require_cloud_type(cloud_type)
        requested = ["legacy", "current"] if cloud_type == "all" else [cloud_type]
        results: List[ProviderResult] = []
        for key in requested:
            provider = self._providers.get(key)
            if provider is None:
                results.append(ProviderResult(
                    provider=key, status="unavailable",
                    warnings=[f"{key}: no authorized provider registered"],
                ))
                continue
            try:
                result = provider.list_environments(
                    account=account, include_drafts=include_drafts
                )
                if result.provider != key:
                    raise ValueError("provider returned wrong cloud type")
                results.append(result)
            except (ValueError, OSError, RuntimeError, TypeError):
                results.append(ProviderResult(
                    provider=key,
                    status="unavailable",
                    warnings=[f"{key}: provider unavailable or invalid"],
                ))

        # Deduplicate only inside the same cloud type. IDs from Legacy and
        # Current are different namespaces, even when textually identical.
        unique: Dict[Tuple[str, str], EnvironmentDescriptor] = {}
        for result in results:
            for item in result.environments:
                if account and item.account and item.account != account:
                    continue
                unique.setdefault((item.cloud_type, item.environment_id), item)

        entries = sorted(
            unique.values(),
            key=lambda item: (item.cloud_type, item.name.casefold(), item.environment_id),
        )
        complete = bool(results) and all(
            result.catalog_complete
            and result.evidence == "live"
            and result.status in {"ok", "empty"}
            for result in results
        )
        warnings = [w for result in results for w in result.warnings]
        if account and (not entries or any(item.account is None for item in entries)):
            # A requested identity cannot be verified merely by labelling a
            # request with the desired account name.
            complete = False
            warnings.append("Requested account identity has not been verified by the provider")
        return {
            "cloud_type": cloud_type,
            "account": account,
            "include_drafts": include_drafts,
            "catalog_complete": complete,
            "status": "ok" if complete else "partial",
            "observed_at": now_utc(),
            "environments": [item.to_dict() for item in entries],
            "providers": [result.to_dict() for result in results],
            "warnings": warnings,
        }

    def find_environments(
        self,
        repository: str,
        account: Optional[str] = None,
        cloud_type: str = "all",
        include_drafts: bool = False,
    ) -> Dict[str, Any]:
        if not repository or (
            not repository.strip().isdecimal()
            and normalize_repository(repository) is None
        ):
            raise ValueError("invalid GitHub repository identifier")
        result = self.list_environments(account, cloud_type, include_drafts)
        matches: List[Dict[str, Any]] = []
        for item in result["environments"]:
            descriptor = EnvironmentDescriptor(**item)
            match = repository_match(descriptor, repository)
            if match != "none":
                matches.append(descriptor.with_match(match).to_dict())
        result["repository"] = repository
        result["environments"] = matches
        result["count"] = len(matches)
        return result

    def get_environment(
        self, cloud_type: str, environment_id: str,
        account: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_cloud_type(cloud_type, allow_all=False)
        if not isinstance(environment_id, str) or not environment_id.strip():
            raise ValueError("environment_id is required")
        catalog = self.list_environments(account=account, cloud_type=cloud_type,
                                         include_drafts=True)
        matches = [
            item for item in catalog["environments"]
            if item["environment_id"] == environment_id
        ]
        if len(matches) == 1 and matches[0]["evidence"] == "live":
            status = "found"
        elif matches:
            status = "unverified"
        else:
            status = "not_found" if catalog["catalog_complete"] else "not_verifiable"
        return {
            "status": status,
            "environment": matches[0] if len(matches) == 1 else None,
            "catalog_complete": catalog["catalog_complete"],
            "providers": catalog["providers"],
            "warnings": catalog["warnings"],
        }

    def resolve_environment(
        self, repository: Optional[str] = None,
        name: Optional[str] = None,
        cloud_type: str = "all",
        account: Optional[str] = None,
        include_drafts: bool = False,
    ) -> Dict[str, Any]:
        if repository:
            catalog = self.find_environments(
                repository, account, cloud_type, include_drafts
            )
        else:
            catalog = self.list_environments(account, cloud_type, include_drafts)
        candidates = catalog["environments"]
        if name is not None:
            candidates = [
                item for item in candidates
                if item["name"].casefold() == name.casefold()
            ]
        # A repository name match is a hint, never enough for auto-selection.
        unique = len(candidates) == 1
        verified = unique and candidates[0]["evidence"] == "live" and (
            not repository or candidates[0]["repository_match"] == "verified"
        )
        if unique and verified and catalog["catalog_complete"]:
            status, selected = "resolved", candidates[0]
        elif len(candidates) > 1:
            status, selected = "ambiguous", None
        elif candidates:
            status, selected = "unverified", None
        elif catalog["catalog_complete"]:
            status, selected = "not_found", None
        else:
            status, selected = "not_verifiable", None

        return {
            "status": status,
            "selected": selected,
            "candidates": candidates,
            "catalog_complete": catalog["catalog_complete"],
            "providers": catalog["providers"],
            "warnings": catalog["warnings"],
            "observed_at": catalog["observed_at"],
        }
