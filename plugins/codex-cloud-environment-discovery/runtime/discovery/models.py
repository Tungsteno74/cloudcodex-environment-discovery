"""Normalized data contracts for Root-level Cloud environment discovery."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_repository(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip().rstrip("/")
    if normalized.lower().startswith("https://github.com/"):
        normalized = normalized[len("https://github.com/"):]
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    parts = normalized.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return f"{parts[0].lower()}/{parts[1].lower()}"


def require_cloud_type(cloud_type: str, allow_all: bool = True) -> str:
    allowed = {"legacy", "current"}
    if allow_all:
        allowed.add("all")
    if cloud_type not in allowed:
        raise ValueError("cloud_type must be legacy, current or all")
    return cloud_type


@dataclass(frozen=True)
class EnvironmentDescriptor:
    cloud_type: str
    environment_id: str
    name: str
    repository: Optional[str] = None
    repository_id: Optional[str] = None
    account: Optional[str] = None
    scope: str = "unknown"
    configuration_state: str = "unknown"
    execution_ready: str = "not_tested"
    discovery_source: str = "unknown"
    evidence: str = "indirect"
    observed_at: str = field(default_factory=now_utc)
    repository_match: str = "not_evaluated"

    def __post_init__(self) -> None:
        require_cloud_type(self.cloud_type, allow_all=False)
        if not self.environment_id.strip():
            raise ValueError("environment_id is required")
        if self.evidence not in {"live", "imported", "indirect", "cache"}:
            raise ValueError("evidence must be live/imported/indirect/cache")
        if self.configuration_state not in {"draft", "published", "unknown"}:
            raise ValueError("invalid configuration_state")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def with_match(self, value: str) -> "EnvironmentDescriptor":
        return replace(self, repository_match=value)


@dataclass
class ProviderResult:
    provider: str
    status: str = "unavailable"
    environments: List[EnvironmentDescriptor] = field(default_factory=list)
    catalog_complete: bool = False
    scope: str = "unknown"
    evidence: str = "indirect"
    warnings: List[str] = field(default_factory=list)
    observed_at: str = field(default_factory=now_utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "catalog_complete": self.catalog_complete,
            "scope": self.scope,
            "evidence": self.evidence,
            "warnings": list(self.warnings),
            "observed_at": self.observed_at,
            "count": len(self.environments),
        }


@dataclass(frozen=True)
class HttpResponse:
    """Sanitized HTTP response.

    Caller-owned transport must ensure authentication and never log secrets.
    Only the JSON-decoded body is passed here. Error bodies are never reported.
    """

    status: int
    body: Any = None


def parse_environment(
    item: Mapping[str, Any],
    cloud_type: str,
    scope: str,
    source: str,
    evidence: str = "live",
    account: Optional[str] = None,
) -> EnvironmentDescriptor:
    """Parse known endpoint variants without inventing IDs or repository associations."""
    environment_id = (
        item.get("environment_id")
        or item.get("environmentId")
        or item.get("configId")
        or item.get("id")
    )
    if not isinstance(environment_id, str) or not environment_id.strip():
        raise ValueError("item lacks a string environment/configuration ID")

    name = item.get("name") or item.get("label") or item.get("display_name")
    if not isinstance(name, str) or not name.strip():
        name = environment_id

    repo_name: Optional[str] = None
    repo_id: Optional[str] = None

    repository = item.get("repository")
    if isinstance(repository, dict):
        candidate = repository.get("full_name") or repository.get("name_with_owner")
        repo_name = normalize_repository(candidate)
        raw_id = repository.get("id") or repository.get("repository_id")
        repo_id = str(raw_id) if raw_id is not None else None
    elif isinstance(repository, str):
        repo_name = normalize_repository(repository)

    repositories = item.get("repositories")
    if isinstance(repositories, list) and len(repositories) == 1:
        association = repositories[0]
        if isinstance(association, dict):
            repo_name = repo_name or normalize_repository(
                association.get("full_name")
                or association.get("repository_full_name")
                or association.get("name_with_owner")
            )
            raw_id = association.get("repository_id") or association.get("id")
            repo_id = repo_id or (str(raw_id) if raw_id is not None else None)

    repo_name = repo_name or normalize_repository(
        item.get("repository_full_name") or item.get("repo")
    )
    raw_id = item.get("repository_id") or item.get("repositoryId")
    repo_id = repo_id or (str(raw_id) if raw_id is not None else None)

    state = item.get("configuration_state") or item.get("state") or item.get("status")
    if item.get("is_draft") is True or item.get("draft") is True:
        config_state = "draft"
    elif item.get("published") is True or item.get("is_published") is True:
        config_state = "published"
    elif isinstance(state, str) and state.lower() in {"draft", "published"}:
        config_state = state.lower()
    else:
        config_state = "unknown"

    return EnvironmentDescriptor(
        cloud_type=cloud_type,
        environment_id=environment_id,
        name=name,
        repository=repo_name,
        repository_id=repo_id,
        account=account or (
            item.get("account") if isinstance(item.get("account"), str) else None
        ),
        scope=scope,
        configuration_state=config_state,
        discovery_source=source,
        evidence=evidence,
    )


def extract_page(body: Any) -> Tuple[List[Mapping[str, Any]], Optional[str]]:
    """Parse known catalog response envelopes. Unknown shapes raise, never mean empty."""
    if isinstance(body, list):
        raw_items = body
        cursor = None
    elif isinstance(body, dict):
        keys = ("environment_configs", "environmentConfigs", "environments",
                "configs", "items", "results", "data")
        found = next((key for key in keys if isinstance(body.get(key), list)), None)
        if found is None:
            raise ValueError("unrecognized catalog response envelope")
        raw_items = body[found]
        cursor = body.get("next_cursor") or body.get("nextCursor")
        if cursor is None:
            pagination = body.get("pagination")
            if isinstance(pagination, dict):
                cursor = pagination.get("next_cursor") or pagination.get("nextCursor")
        if body.get("has_more") is True or body.get("hasMore") is True:
            if cursor is None:
                raise ValueError("has_more true without next cursor")
    else:
        raise ValueError("catalog response must be a mapping or array")

    if not all(isinstance(item, dict) for item in raw_items):
        raise ValueError("catalog contains non-object items")
    if cursor is not None and not isinstance(cursor, str):
        raise ValueError("catalog next cursor is not a string")
    return list(raw_items), cursor
