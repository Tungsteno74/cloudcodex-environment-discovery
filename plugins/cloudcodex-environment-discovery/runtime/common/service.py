"""Single-type discovery service. No mixed Legacy/Current catalog path."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .matching import repository_match
from .models import EnvironmentDescriptor, ProviderResult, normalize_repository, now_utc
from .protocols import EnvironmentProvider


class EnvironmentDiscoveryService:
    """Typed boundary for one provider and its read-only operations.

    A service never imports the other provider or merges catalog namespaces.
    Removing Legacy therefore does not require touching Current's service.
    """

    def __init__(self, cloud_type: str, provider: EnvironmentProvider) -> None:
        if not isinstance(cloud_type, str) or not cloud_type.strip():
            raise ValueError("cloud_type is required")
        if provider.name != cloud_type:
            raise ValueError("provider and cloud type mismatch")
        self.cloud_type = cloud_type
        self._provider = provider

    def list_environments(
        self, account: Optional[str] = None, include_drafts: bool = False
    ) -> Dict[str, Any]:
        try:
            result = self._provider.list_environments(
                account=account, include_drafts=include_drafts
            )
            if result.provider != self.cloud_type:
                raise ValueError("provider reported a different cloud type")
            if any(
                item.cloud_type != self.cloud_type
                for item in result.environments
            ):
                raise ValueError("catalog returned an item from another cloud type")
        except (ValueError, OSError, RuntimeError, TypeError):
            result = ProviderResult(
                provider=self.cloud_type,
                status="unavailable",
                warnings=[f"{self.cloud_type}: provider failure or invalid data"],
            )

        # In a single-domain service there is no hidden other-provider failure.
        unique: Dict[str, EnvironmentDescriptor] = {}
        for item in result.environments:
            if account and item.account and item.account != account:
                continue
            unique.setdefault(item.environment_id, item)

        items = sorted(
            unique.values(), key=lambda item: (item.name.casefold(), item.environment_id)
        )
        complete = (
            result.catalog_complete
            and result.evidence == "live"
            and result.status in {"ok", "empty"}
        )
        warnings = list(result.warnings)
        if account and (not items or any(item.account is None for item in items)):
            complete = False
            warnings.append("Requested account identity was not verified by this provider")

        return {
            "cloud_type": self.cloud_type,
            "account": account,
            "include_drafts": include_drafts,
            "catalog_complete": complete,
            "status": result.status if complete else (
                result.status if result.status not in {"ok", "empty"} else "partial"
            ),
            "observed_at": now_utc(),
            "environments": [item.to_dict() for item in items],
            "provider": result.to_dict(),
            "warnings": warnings,
        }

    def find_environments(
        self, repository: str, account: Optional[str] = None,
        include_drafts: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(repository, str) or (
            not repository.strip().isdecimal()
            and normalize_repository(repository) is None
        ):
            raise ValueError("repository must be a GitHub ID or owner/repo")
        result = self.list_environments(
            account=account, include_drafts=include_drafts
        )
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
        self, environment_id: str, account: Optional[str] = None
    ) -> Dict[str, Any]:
        if not isinstance(environment_id, str) or not environment_id.strip():
            raise ValueError("environment_id is required")
        catalog = self.list_environments(account=account, include_drafts=True)
        matches = [
            item for item in catalog["environments"]
            if item["environment_id"] == environment_id
        ]
        if len(matches) == 1 and matches[0]["evidence"] == "live" and (
            catalog["catalog_complete"]
        ):
            status = "found"
        elif matches:
            status = "unverified"
        else:
            status = "not_found" if catalog["catalog_complete"] else "not_verifiable"
        return {
            "cloud_type": self.cloud_type,
            "status": status,
            "environment": matches[0] if len(matches) == 1 else None,
            "catalog_complete": catalog["catalog_complete"],
            "provider": catalog["provider"],
            "warnings": catalog["warnings"],
        }

    def resolve_environment(
        self, repository: Optional[str] = None,
        name: Optional[str] = None,
        account: Optional[str] = None,
        include_drafts: bool = False,
    ) -> Dict[str, Any]:
        if repository is not None:
            catalog = self.find_environments(
                repository=repository, account=account,
                include_drafts=include_drafts,
            )
        else:
            catalog = self.list_environments(
                account=account, include_drafts=include_drafts
            )
        candidates = catalog["environments"]
        if name is not None:
            candidates = [
                item for item in candidates
                if item["name"].casefold() == name.casefold()
            ]
        unique = len(candidates) == 1
        verified = unique and candidates[0]["evidence"] == "live" and (
            repository is None
            or candidates[0]["repository_match"] == "verified"
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
            "cloud_type": self.cloud_type,
            "status": status,
            "selected": selected,
            "candidates": candidates,
            "catalog_complete": catalog["catalog_complete"],
            "provider": catalog["provider"],
            "warnings": catalog["warnings"],
            "observed_at": catalog["observed_at"],
        }
