"""Single-generation discovery, evidence validation and conservative resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .catalog import merge_records
from .matching import repository_match
from .github import RepositoryResolver, match_verified_repository
from .models import EnvironmentDescriptor, ProviderResult, normalize_repository, now_utc
from .operation import OperationCancelled, OperationTimedOut, checkpoint
from .protocols import EnvironmentProvider


class EnvironmentDiscoveryService:
    def __init__(
        self,
        cloud_type: str,
        provider: EnvironmentProvider,
        repository_resolver: Optional[RepositoryResolver] = None,
    ):
        if not isinstance(cloud_type, str) or not cloud_type.strip() or provider.name != cloud_type:
            raise ValueError("Provider and cloud generation must match")
        self.cloud_type, self._provider = cloud_type, provider
        self._repository_resolver = repository_resolver

    def list_environments(
        self,
        account: Optional[str] = None,
        include_drafts: bool = False,
        correlate_github: bool = False,
    ) -> Dict[str, Any]:
        if type(correlate_github) is not bool:
            raise ValueError("correlate_github must be boolean")
        result = self._catalog(account, include_drafts)
        if not correlate_github:
            return result
        if result["status"] in {"timeout", "cancelled"}:
            result["repository_inventory"] = {
                "status": "not_attempted",
                "catalog_complete": False,
                "reason": "operation_terminated_before_optional_correlation",
            }
            return result
        method = getattr(self._repository_resolver, "list_repositories", None)
        if not callable(method):
            result["repository_inventory"] = {
                "status": "unavailable",
                "catalog_complete": False,
                "reason": "github_catalog_not_configured",
            }
            return result
        from .correlation import correlate_repositories

        inventory = method()
        result["repository_correlations"] = correlate_repositories(
            result["environments"], inventory
        )
        result["repository_inventory"] = {
            key: value for key, value in inventory.items() if key != "repositories"
        }
        # GitHub is an independent read source. A Cloud 401/403/rate-limit
        # remains terminal for the Cloud provider, but does not invalidate an
        # explicitly requested GitHub inventory.
        if result["status"] in {
            "unauthorized",
            "forbidden",
            "approval_required",
            "rate_limited",
        }:
            result["warnings"].append(
                "Cloud discovery stopped at "
                + result["status"]
                + "; GitHub inventory was read independently and does not override that Cloud status"
            )
        # GitHub alone supplies candidate repository names, NEVER Cloud IDs.
        if not result["environments"]:
            result["repository_candidates"] = inventory.get("repositories", [])
        return result

    def _catalog(self, account=None, include_drafts=False, repository=None, environment_id=None):
        if not isinstance(include_drafts, bool) or (
            account is not None and (not isinstance(account, str) or not account)
        ):
            raise ValueError("Invalid discovery arguments")
        checkpoint()
        try:
            finder = getattr(self._provider, "find_environments", None)
            direct = getattr(self._provider, "get_environment", None)
            if environment_id is not None and callable(direct):
                result = direct(environment_id, account=account)
            elif repository is not None and callable(finder):
                result = finder(
                    repository=repository, account=account, include_drafts=include_drafts
                )
            else:
                result = self._provider.list_environments(
                    account=account, include_drafts=include_drafts
                )
            if result.provider != self.cloud_type or any(
                i.cloud_type != self.cloud_type for i in result.environments
            ):
                raise ValueError("Catalog contains a different Cloud generation")
            entries = merge_records(result.environments)
        except (OperationCancelled, OperationTimedOut):
            raise
        except (ValueError, OSError, RuntimeError, TypeError):
            result = ProviderResult(
                provider=self.cloud_type,
                status="unavailable",
                reason="provider_failure_or_invalid_data",
            )
            entries = []
        checkpoint()
        warnings = list(result.warnings)
        complete = (
            result.catalog_complete
            and result.evidence == "live"
            and result.status in {"ok", "empty"}
            and all(i.evidence == "live" for i in entries)
        )
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
        fresh = True
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
                    fresh = False
                    warnings.append("Stale live evidence must be revalidated")
            except (ValueError, TypeError, AttributeError):
                complete = False
                fresh = False
                warnings.append("Invalid observation timestamp")
        point_verified = (
            environment_id is not None
            and result.coverage.get("point_verified") is True
            and result.status == "ok"
            and fresh
            and len(entries) == 1
            and entries[0].environment_id == environment_id
            and entries[0].evidence == "live"
            and (account is None or (result.account_verified and result.account == account))
        )
        status = (
            result.status
            if complete or point_verified or result.status not in {"ok", "empty"}
            else "partial"
        )
        metadata = result.to_dict()
        metadata["catalog_complete"] = complete
        if environment_id is not None:
            metadata["coverage"] = dict(metadata["coverage"], point_verified=point_verified)
        return {
            "cloud_type": self.cloud_type,
            "account": account,
            "include_drafts": include_drafts,
            "catalog_complete": complete,
            "status": status,
            "observed_at": now_utc(),
            "environments": [i.to_dict() for i in entries],
            "provider": metadata,
            "warnings": warnings,
        }

    def find_environments(
        self, repository: str, account: Optional[str] = None, include_drafts: bool = False
    ) -> Dict[str, Any]:
        if (
            not isinstance(repository, str)
            or not repository.strip()
            or not repository.strip().isdecimal()
            and normalize_repository(repository) is None
        ):
            raise ValueError("Repository must be a numeric ID or owner/repo")
        repository_evidence = None
        query = repository
        if self._repository_resolver is not None:
            repository_evidence = self._repository_resolver.resolve(repository)
            if repository_evidence.get("status") != "verified":
                from .correlation import repository_counterpart

                counterpart = repository_counterpart(
                    [],
                    repository,
                    repository_evidence,
                    cloud_catalog_status="not_attempted",
                    cloud_catalog_complete=False,
                )
                return {
                    "cloud_type": self.cloud_type,
                    "repository": repository,
                    "count": 0,
                    "status": "not_verifiable",
                    "catalog_complete": False,
                    "environments": [],
                    "observed_at": now_utc(),
                    "repository_evidence": repository_evidence,
                    "repository_counterpart": counterpart,
                    "provider": {
                        "provider": self.cloud_type,
                        "status": "not_attempted",
                        "catalog_complete": False,
                        "attempts": [],
                    },
                    "warnings": [
                        "Configured GitHub identity verification failed; Cloud reads were not attempted"
                    ],
                }
            query = repository_evidence["repository"]
        result = self._catalog(account, include_drafts, repository=query)
        if repository_evidence is not None:
            result["repository_evidence"] = repository_evidence
        matches = []
        for item in result["environments"]:
            descriptor = EnvironmentDescriptor(**item)
            match = (
                match_verified_repository(descriptor, repository_evidence)
                if repository_evidence is not None
                else repository_match(descriptor, repository)
            )
            if match != "none":
                matches.append(descriptor.with_match(match).to_dict())
        from .correlation import repository_counterpart

        counterpart = repository_counterpart(
            result["environments"],
            repository,
            repository_evidence,
            cloud_catalog_status=result["status"],
            cloud_catalog_complete=result["catalog_complete"],
        )
        result.update(
            repository=repository,
            environments=matches,
            count=len(matches),
            repository_counterpart=counterpart,
        )
        return result

    def get_environment(self, environment_id: str, account: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(environment_id, str) or not environment_id.strip():
            raise ValueError("Immutable environment ID required")
        if self.cloud_type == "current":
            from current.detail import valid_configuration_id

            if not valid_configuration_id(environment_id):
                raise ValueError("Invalid Current Configuration ID")
            catalog = self._catalog(
                account=account, include_drafts=True, environment_id=environment_id
            )
        else:
            catalog = self.list_environments(account=account, include_drafts=True)
        candidates = [
            item for item in catalog["environments"]
            if item["environment_id"] == environment_id
        ]
        point_verified = (
            self.cloud_type == "current"
            and catalog["provider"].get("coverage", {}).get("point_verified") is True
        )
        if self.cloud_type == "current" and catalog["status"] in {
            "unauthorized", "forbidden", "rate_limited", "approval_required",
            "cancelled", "timeout",
        }:
            # A denial takes precedence over earlier imported/partial candidates.
            # Keep those as candidates only, never claim one as a current result.
            status = catalog["status"]
        elif len(candidates) > 1:
            status = "ambiguous"
        elif candidates:
            status = (
                "found"
                if (catalog["catalog_complete"] or point_verified)
                and candidates[0]["evidence"] == "live"
                else "unverified"
            )
        else:
            status = "not_found" if catalog["catalog_complete"] else "not_verifiable"
        return {
            "cloud_type": self.cloud_type,
            "status": status,
            "environment": candidates[0] if len(candidates) == 1 else None,
            "candidates": candidates,
            "catalog_complete": catalog["catalog_complete"],
            "point_verified": point_verified,
            "provider": catalog["provider"],
            "warnings": catalog["warnings"],
        }

    def resolve_environment(
        self,
        repository: Optional[str] = None,
        name: Optional[str] = None,
        account: Optional[str] = None,
        include_drafts: bool = False,
    ) -> Dict[str, Any]:
        if name is not None and not isinstance(name, str):
            raise ValueError("Name must be a string")
        catalog = (
            self.find_environments(repository, account, include_drafts)
            if repository is not None
            else self.list_environments(account, include_drafts)
        )
        candidates = catalog["environments"]
        if name is not None:
            candidates = [i for i in candidates if i["name"].casefold() == name.casefold()]
        selected = None
        if len(candidates) > 1:
            status = "ambiguous"
        elif candidates:
            candidate = candidates[0]
            if (
                catalog["catalog_complete"]
                and candidate["evidence"] == "live"
                and (repository is None or candidate["repository_match"] == "verified")
            ):
                status, selected = "resolved", candidate
            else:
                status = "unverified"
        else:
            status = "not_found" if catalog["catalog_complete"] else "not_verifiable"
        return {
            "cloud_type": self.cloud_type,
            "status": status,
            "selected": selected,
            "candidates": candidates,
            "catalog_complete": catalog["catalog_complete"],
            "provider": catalog["provider"],
            "warnings": catalog["warnings"],
            "observed_at": catalog["observed_at"],
            "repository_evidence": catalog.get("repository_evidence"),
            "repository_counterpart": catalog.get("repository_counterpart"),
        }
