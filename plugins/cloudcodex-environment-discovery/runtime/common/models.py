"""Typed catalog contracts; provenance and configuration state are independent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_repository(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    name = value.strip().rstrip("/")
    if name.startswith("git@github.com:"):
        name = name[len("git@github.com:") :]
    elif "://" in name:
        parsed = urlsplit(name)
        if (
            parsed.scheme not in {"https", "ssh"}
            or parsed.hostname != "github.com"
            or parsed.query
            or parsed.fragment
            or parsed.password
        ):
            return None
        name = parsed.path.lstrip("/")
    if name.lower().endswith(".git"):
        name = name[:-4]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", name):
        return None
    owner, repository = name.split("/")
    if repository in {".", ".."}:
        return None
    return (owner + "/" + repository).lower()


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
    repositories: Tuple[Mapping[str, Optional[str]], ...] = ()
    configuration_version: Optional[str] = None

    def __post_init__(self) -> None:
        for label, value in (
            ("cloud_type", self.cloud_type),
            ("environment_id", self.environment_id),
            ("name", self.name),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 4096:
                raise ValueError("Invalid descriptor field: " + label)
        if self.evidence not in {"live", "imported", "indirect", "cache"}:
            raise ValueError("Invalid evidence category")
        if self.configuration_state not in {"draft", "published", "unknown"}:
            raise ValueError("Invalid configuration state")

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
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    account: Optional[str] = None
    account_verified: bool = False
    reason: Optional[str] = None
    source: Optional[str] = None
    hints: List[Dict[str, Any]] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        output = asdict(self)
        output.pop("environments")
        output["count"] = len(self.environments)
        return output


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: Any = None
    account: Optional[str] = None
    account_verified: bool = False
    observed_at: Optional[str] = None
    content_type: str = "application/json"


def _associations(item: Mapping[str, Any]) -> Tuple[Mapping[str, Optional[str]], ...]:
    found = []
    values = (
        list(item.get("repositories", [])) if isinstance(item.get("repositories"), list) else []
    )
    values.append(item.get("repository"))
    values.append(
        {
            "full_name": item.get("repository_full_name") or item.get("repo"),
            "id": item.get("repository_id") or item.get("repositoryId"),
        }
    )
    for value in values:
        if isinstance(value, str):
            name, identifier = normalize_repository(value), None
        elif isinstance(value, dict):
            name = normalize_repository(
                value.get("full_name")
                or value.get("name_with_owner")
                or value.get("repository_full_name")
            )
            identifier = value.get("repository_id") or value.get("id")
            identifier = (
                str(identifier)
                if isinstance(identifier, (str, int)) and not isinstance(identifier, bool)
                else None
            )
            if (
                not name
                and isinstance(value.get("owner"), str)
                and isinstance(value.get("name"), str)
            ):
                name = normalize_repository(value["owner"] + "/" + value["name"])
        else:
            continue
        association = {"repository": name, "repository_id": identifier}
        if (name or identifier) and association not in found:
            found.append(association)
    return tuple(found)


def parse_environment(
    item: Mapping[str, Any],
    cloud_type: str,
    scope: str,
    source: str,
    evidence: str = "live",
    account: Optional[str] = None,
    observed_at: Optional[str] = None,
) -> EnvironmentDescriptor:
    if not isinstance(item, dict):
        raise ValueError("Environment record is not an object")
    identifier = (
        item.get("environment_id")
        or item.get("environmentId")
        or item.get("configId")
        or item.get("configuration_id")
        or item.get("id")
    )
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("Environment record has no immutable ID")
    name = item.get("name") or item.get("label") or item.get("display_name") or identifier
    associations = _associations(item)
    primary = associations[0] if len(associations) == 1 else {}
    state = item.get("configuration_state") or item.get("state") or item.get("status")
    state = state.lower() if isinstance(state, str) else "unknown"
    if item.get("is_draft") is True or item.get("draft") is True:
        state = "draft"
    elif item.get("published") is True or item.get("is_published") is True:
        state = "published"
    if state not in {"draft", "published"}:
        state = "unknown"
    version = item.get("configuration_version") or item.get("version")
    if not isinstance(version, (str, int)) or isinstance(version, bool):
        version = None
    observed_account = item.get("account") if isinstance(item.get("account"), str) else None
    return EnvironmentDescriptor(
        cloud_type=cloud_type,
        environment_id=identifier,
        name=name,
        repository=primary.get("repository"),
        repository_id=primary.get("repository_id"),
        repositories=associations,
        account=account or observed_account,
        scope=scope,
        configuration_state=state,
        configuration_version=str(version) if version is not None else None,
        discovery_source=source,
        evidence=evidence,
        observed_at=observed_at or now_utc(),
    )


def extract_page(body: Any) -> Tuple[List[Mapping[str, Any]], Optional[str]]:
    """Accept known envelopes only. Conflicting/unfinished cursors fail closed."""
    if isinstance(body, list):
        items, cursor = body, None
    elif isinstance(body, dict):
        keys = (
            "environment_configs",
            "environmentConfigs",
            "environments",
            "configs",
            "items",
            "results",
            "data",
        )
        containers = [body[key] for key in keys if isinstance(body.get(key), list)]
        if len(containers) != 1:
            raise ValueError("Unknown or ambiguous catalog envelope")
        items = containers[0]
        cursors = [body[k] for k in ("next_cursor", "nextCursor") if body.get(k) not in (None, "")]
        paging = body.get("pagination")
        if isinstance(paging, dict):
            cursors.extend(
                paging[k] for k in ("next_cursor", "nextCursor") if paging.get(k) not in (None, "")
            )
        if any(not isinstance(c, str) or len(c) > 4096 for c in cursors) or len(set(cursors)) > 1:
            raise ValueError("Invalid or conflicting pagination cursor")
        cursor = cursors[0] if cursors else None
        has_more = body.get("has_more", body.get("hasMore"))
        if isinstance(paging, dict):
            has_more = paging.get("has_more", paging.get("hasMore", has_more))
        if has_more is True and not cursor or has_more is False and cursor:
            raise ValueError("Inconsistent pagination state")
    else:
        raise ValueError("Catalog is neither an array nor an object")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError("Catalog contains non-object records")
    return list(items), cursor
