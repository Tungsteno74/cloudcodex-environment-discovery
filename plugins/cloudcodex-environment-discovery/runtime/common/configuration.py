"""Startup-only configuration for independent read-only discovery channels.

No tool accepts executables, credentials, URLs or configuration paths. This file
is selected by the operator when starting the CLI/MCP process, never by a tool
call. A configured host command must be independently approved and hash-pinned.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .adapters import CommandCatalogProvider, CommandClient, CommandReadTransport, CommandSpec
from .escalation import EscalatingProvider, Stage
from .github import GitHubSettings, NativeGitHubRepositoryResolver
from .service import EnvironmentDiscoveryService
from .snapshot import SnapshotEnvironmentProvider

MAX_CONFIG_BYTES = 1024 * 1024
ORDER = {"primary": 0, "http": 1, "onboarding": 2, "snapshot": 3}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate configuration key")
        result[key] = value
    return result


def load_configuration(path: Optional[Path] = None) -> dict:
    configured = path or (Path(os.environ["CLOUDCODEX_DISCOVERY_CONFIG"])
                          if os.environ.get("CLOUDCODEX_DISCOVERY_CONFIG") else None)
    if configured is None:
        return {"schema_version": 1, "mode": "AUTO", "timeout": 30, "domains": {}}
    configured = Path(configured).resolve()
    if configured.name.lower() in {"auth.json", "credentials.json", ".env"}:
        raise ValueError("Credential files are not discovery configuration")
    if configured.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError("Discovery configuration exceeds maximum size")
    content = json.loads(configured.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    return validate_configuration(content)


def validate_configuration(content: Mapping[str, Any]) -> dict:
    if not isinstance(content, dict) or set(content) - {"schema_version", "mode", "timeout", "domains", "github"}:
        raise ValueError("Unknown discovery configuration fields")
    if type(content.get("schema_version")) is not int or content["schema_version"] != 1:
        raise ValueError("Unsupported discovery configuration version")
    if content.get("mode", "AUTO") not in {"AUTO", "CONFIRM"}:
        raise ValueError("Invalid escalation mode")
    timeout = content.get("timeout", 30)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 180:
        raise ValueError("Invalid discovery operation timeout")
    github = content.get("github", {"enabled": False})
    if not isinstance(github, dict) or type(github.get("enabled")) is not bool:
        raise ValueError("GitHub requires explicit enabled true/false")
    if github["enabled"]:
        GitHubSettings.from_mapping(github)
    elif set(github) != {"enabled"}:
        raise ValueError("Disabled GitHub settings must contain only enabled")
    domains = content.get("domains", {})
    if not isinstance(domains, dict) or set(domains) - {"legacy", "current"}:
        raise ValueError("Unknown cloud generation")
    for domain, settings in domains.items():
        if (not isinstance(settings, dict)
                or set(settings) - {"stages", "scopes", "page_limit", "page_size"}):
            raise ValueError("Unknown provider configuration fields")
        scopes = settings.get("scopes", ["user"] if domain == "legacy" else ["user", "workspace"])
        if (not isinstance(scopes, list) or not scopes or len(scopes) != len(set(scopes))
                or any(s not in {"user", "workspace"} for s in scopes)
                or domain == "legacy" and scopes != ["user"]):
            raise ValueError("Invalid provider scopes")
        for field, default in (("page_limit", 12), ("page_size", 100)):
            value = settings.get(field, default)
            if type(value) is not int or not 1 <= value <= 100:
                raise ValueError("Invalid pagination configuration")
        stages = settings.get("stages", [])
        if not isinstance(stages, list) or len(stages) > 4:
            raise ValueError("Invalid escalation stage list")
        seen, previous = set(), -1
        for stage in stages:
            if not isinstance(stage, dict) or set(stage) - {"kind", "approved", "command", "path"}:
                raise ValueError("Invalid stage configuration")
            kind = stage.get("kind")
            if kind not in ORDER or kind in seen or ORDER[kind] <= previous:
                raise ValueError("Escalation order must be primary, http, onboarding, snapshot")
            if domain == "legacy" and kind == "onboarding":
                raise ValueError("Onboarding hints apply only to Current")
            seen.add(kind)
            previous = ORDER[kind]
            if type(stage.get("approved", False)) is not bool:
                raise ValueError("Stage approval must be explicit boolean")
            if kind == "snapshot" or kind == "onboarding" and "path" in stage:
                if "command" in stage or not isinstance(stage.get("path"), str) or not Path(stage["path"]).is_absolute():
                    raise ValueError("Snapshot path must be explicit and absolute")
            else:
                if "path" in stage:
                    raise ValueError("Live stages cannot use snapshot files")
                CommandSpec.from_mapping(stage.get("command"))
    return dict(content)


class DeferredSnapshot:
    """Read explicit catalog evidence only when the configured stage is reached."""

    def __init__(self, domain: str, path: Path):
        self.name, self.path = domain, path

    def list_environments(self, account=None, include_drafts=False):
        return SnapshotEnvironmentProvider.from_file(self.name, self.path).list_environments(
            account=account, include_drafts=include_drafts,
        )


class DiscoveryRuntime:
    """Reusable configured service factory shared by CLI and optional MCP."""

    def __init__(self, configuration: Optional[dict] = None):
        self.configuration = validate_configuration(configuration) if configuration is not None else load_configuration()
        self.timeout = float(self.configuration.get("timeout", 30))
        self._services: Dict[str, EnvironmentDiscoveryService] = {}
        github = self.configuration.get("github", {"enabled": False})
        self._repository_resolver = (NativeGitHubRepositoryResolver(GitHubSettings.from_mapping(github))
                                     if github["enabled"] else None)

    def service(self, domain: str) -> EnvironmentDiscoveryService:
        if domain not in {"legacy", "current"}:
            raise ValueError("A single Cloud generation is required")
        if domain in self._services:
            return self._services[domain]
        settings = self.configuration.get("domains", {}).get(domain, {})
        stages = []
        for spec in settings.get("stages", []):
            kind = spec["kind"]
            if kind == "snapshot":
                provider = DeferredSnapshot(domain, Path(spec["path"]))
            elif kind == "onboarding" and "path" in spec:
                from current.onboarding import OnboardingEvidenceFile
                provider = OnboardingEvidenceFile(Path(spec["path"]))
            else:
                client = CommandClient(CommandSpec.from_mapping(spec["command"]))
                if kind == "http":
                    transport = CommandReadTransport(domain, client)
                    if domain == "legacy":
                        from legacy.provider import LegacyEnvironmentProvider
                        provider = LegacyEnvironmentProvider(transport=transport,
                                                             page_limit=settings.get("page_limit", 12))
                    else:
                        from current.provider import CurrentCloudEnvironmentProvider
                        provider = CurrentCloudEnvironmentProvider(
                            transport=transport, scopes=settings.get("scopes", ("user", "workspace")),
                            page_limit=settings.get("page_limit", 12), page_size=settings.get("page_size", 100),
                        )
                else:
                    provider = CommandCatalogProvider(domain, client,
                                                      source=domain + "_" + kind,
                                                      indirect=kind == "onboarding",
                                                      scopes=settings.get("scopes"))
            stages.append(Stage(kind, provider, spec.get("approved", False)))
        service = EnvironmentDiscoveryService(
            domain, EscalatingProvider(domain, stages, self.configuration.get("mode", "AUTO")),
            repository_resolver=self._repository_resolver,
        )
        self._services[domain] = service
        return service

    def doctor(self, domain: str) -> dict:
        """Static local capability report; does not start hosts or query Cloud."""
        self.service(domain)
        stages = self.configuration.get("domains", {}).get(domain, {}).get("stages", [])
        return {"cloud_type": domain, "configured": bool(stages), "live_tested": False,
                "github_enabled": self._repository_resolver is not None,
                "mode": self.configuration.get("mode", "AUTO"), "timeout": self.timeout,
                "stages": [{"kind": s["kind"], "approved": s.get("approved", False)} for s in stages],
                "warning": "Configured host adapters do not establish provider authorization or live coverage"}
