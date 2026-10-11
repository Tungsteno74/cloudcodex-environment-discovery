"""Single-generation discovery, evidence validation and conservative resolution."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .catalog import merge_records
from .matching import repository_match
from .models import EnvironmentDescriptor, ProviderResult, normalize_repository, now_utc
from .operation import OperationCancelled, OperationTimedOut, checkpoint
from .protocols import EnvironmentProvider


class EnvironmentDiscoveryService:
    def __init__(self, cloud_type: str, provider: EnvironmentProvider):
        if not isinstance(cloud_type, str) or not cloud_type.strip() or provider.name != cloud_type:
            raise ValueError("Provider and cloud generation must match")
        self.cloud_type, self._provider = cloud_type, provider

    def list_environments(self, account: Optional[str] = None,
                          include_drafts: bool = False) -> Dict[str, Any]:
        return self._catalog(account, include_drafts)

    def _catalog(self, account=None, include_drafts=False, repository=None):
        if not isinstance(include_drafts, bool) or (account is not None and (not isinstance(account, str) or not account)):
            raise ValueError("Invalid discovery arguments")
        checkpoint()
        try:
            finder = getattr(self._provider, "find_environments", None)
            result = (finder(repository=repository, account=account, include_drafts=include_drafts)
                      if repository is not None and callable(finder)
                      else self._provider.list_environments(account=account, include_drafts=include_drafts))
            if result.provider != self.cloud_type or any(i.cloud_type != self.cloud_type for i in result.environments):
                raise ValueError("Catalog contains a different Cloud generation")
            entries = merge_records(result.environments)
        except (OperationCancelled, OperationTimedOut):
            raise
        except (ValueError, OSError, RuntimeError, TypeError):
            result = ProviderResult(provider=self.cloud_type, status="unavailable",
                                    reason="provider_failure_or_invalid_data")
            entries = []
        checkpoint()
        warnings = list(result.warnings)
        complete = (result.catalog_complete and result.evidence == "live"
                    and result.status in {"ok", "empty"}
                    and all(i.evidence == "live" for i in entries))
        if not include_drafts:
            entries = [i for i in entries if i.configuration_state != "draft"]
        # Preserve versions and drafts. Duplicate IDs are not arbitrary winners.
        if account is not None:
            entries = [i for i in entries if i.account in (None, account)]
            if result.account_verified:
                if result.account != account:
                    entries = []
                    complete = False
                    result.status, result.reason = "forbidden", "account_mismatch"
            elif not entries or any(i.account != account for i in entries):
                complete = False
                warnings.append("Requested account identity was not verified by this provider")
        for entry in entries:
            if entry.evidence != "live":
                continue
            try:
                when = datetime.fromisoformat(entry.observed_at.replace("Z", "+00:00"))
                if when.tzinfo is None:
                    raise ValueError()
                age = (datetime.now(timezone.utc) - when).total_seconds()
                if age < -5 or age > 60:
                    complete = False
                    warnings.append("Stale live evidence must be revalidated")
            except (ValueError, TypeError, AttributeError):
                complete = False
                warnings.append("Invalid observation timestamp")
        status = result.status if complete or result.status not in {"ok", "empty"} else "partial"
        metadata = result.to_dict()
        metadata["catalog_complete"] = complete
        return {
            "cloud_type": self.cloud_type, "account": account, "include_drafts": include_drafts,
            "catalog_complete": complete, "status": status, "observed_at": now_utc(),
            "environments": [i.to_dict() for i in entries], "provider": metadata,
            "warnings": warnings,
        }

    def find_environments(self, repository: str, account: Optional[str] = None,
                          include_drafts: bool = False) -> Dict[str, Any]:
        if (not isinstance(repository, str) or not repository.strip()
                or not repository.strip().isdecimal() and normalize_repository(repository) is None):
            raise ValueError("Repository must be a numeric ID or owner/repo")
        result = self._catalog(account, include_drafts, repository=repository)
        matches = []
        for item in result["environments"]:
            descriptor = EnvironmentDescriptor(**item)
            match = repository_match(descriptor, repository)
            if match != "none":
                matches.append(descriptor.with_match(match).to_dict())
        result.update(repository=repository, environments=matches, count=len(matches))
        return result

    def get_environment(self, environment_id: str, account: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(environment_id, str) or not environment_id.strip():
            raise ValueError("Immutable environment ID required")
        catalog = self.list_environments(account=account, include_drafts=True)
        candidates = [i for i in catalog["environments"] if i["environment_id"] == environment_id]
        if len(candidates) > 1:
            status = "ambiguous"
        elif candidates:
            status = "found" if catalog["catalog_complete"] and candidates[0]["evidence"] == "live" else "unverified"
        else:
            status = "not_found" if catalog["catalog_complete"] else "not_verifiable"
        return {"cloud_type": self.cloud_type, "status": status,
                "environment": candidates[0] if len(candidates) == 1 else None,
                "candidates": candidates, "catalog_complete": catalog["catalog_complete"],
                "provider": catalog["provider"], "warnings": catalog["warnings"]}

    def resolve_environment(self, repository: Optional[str] = None, name: Optional[str] = None,
                            account: Optional[str] = None, include_drafts: bool = False) -> Dict[str, Any]:
        if name is not None and not isinstance(name, str):
            raise ValueError("Name must be a string")
        catalog = (self.find_environments(repository, account, include_drafts) if repository is not None
                   else self.list_environments(account, include_drafts))
        candidates = catalog["environments"]
        if name is not None:
            candidates = [i for i in candidates if i["name"].casefold() == name.casefold()]
        selected = None
        if len(candidates) > 1:
            status = "ambiguous"
        elif candidates:
            candidate = candidates[0]
            if (catalog["catalog_complete"] and candidate["evidence"] == "live"
                    and (repository is None or candidate["repository_match"] == "verified")):
                status, selected = "resolved", candidate
            else:
                status = "unverified"
        else:
            status = "not_found" if catalog["catalog_complete"] else "not_verifiable"
        return {"cloud_type": self.cloud_type, "status": status, "selected": selected,
                "candidates": candidates, "catalog_complete": catalog["catalog_complete"],
                "provider": catalog["provider"], "warnings": catalog["warnings"],
                "observed_at": catalog["observed_at"]}
