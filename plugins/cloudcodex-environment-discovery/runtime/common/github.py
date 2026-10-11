"""Optional concrete GitHub adapter using the installed, authorized GitHub CLI.

Only native `gh api --method GET --hostname github.com` is invoked. GitHub
manages its own existing authentication; this module never reads token files.
Repository access does not establish that a Codex Cloud environment exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Mapping, Optional, Protocol

from .adapters import AdapterError, CommandClient, CommandSpec
from .models import EnvironmentDescriptor, normalize_repository, now_utc
from .operation import active_operation, operation_scope


class RepositoryResolver(Protocol):
    def resolve(self, repository: str) -> dict: ...


@dataclass(frozen=True)
class GitHubSettings:
    executable: str
    sha256: str
    account: Optional[str] = None
    timeout: float = 15.0

    @classmethod
    def from_mapping(cls, value: Mapping) -> "GitHubSettings":
        if not isinstance(value, dict) or set(value) - {
            "enabled",
            "executable",
            "sha256",
            "account",
            "timeout",
        }:
            raise ValueError("Invalid GitHub adapter settings")
        if value.get("enabled") is not True:
            raise ValueError("GitHub reads require explicit startup opt-in")
        executable = value.get("executable")
        digest = value.get("sha256")
        if (
            not isinstance(executable, str)
            or not Path(executable).is_absolute()
            or Path(executable).name.lower() not in {"gh", "gh.exe"}
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
        ):
            raise ValueError("GitHub CLI must be an absolute, hash-pinned native executable")
        account = value.get("account")
        if account is not None and (
            not isinstance(account, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", account)
        ):
            raise ValueError("Invalid expected GitHub account")
        timeout = value.get("timeout", 15)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0.1 <= timeout <= 60
        ):
            raise ValueError("Invalid GitHub read timeout")
        return cls(executable, digest, account, float(timeout))


class NativeGitHubRepositoryResolver:
    def __init__(
        self,
        settings: GitHubSettings,
        client_factory: Callable[[CommandSpec], CommandClient] = CommandClient,
    ):
        self.settings = settings
        self._client_factory = client_factory

    def _get(self, endpoint: str, projection: str, paginate: bool = False) -> dict:
        argv = (
            self.settings.executable,
            "api",
            "--method",
            "GET",
            "--hostname",
            "github.com",
            endpoint,
        ) + (("--paginate", "--slurp") if paginate else ("--jq", projection))
        spec = CommandSpec(
            argv=argv,
            pins=((self.settings.executable, self.settings.sha256),),
            cwd=str(Path(self.settings.executable).parent),
            timeout=self.settings.timeout,
        )
        if not paginate:
            return self._client_factory(spec).request({})
        pages = self._client_factory(spec).request({}, allow_array=True)
        if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
            raise AdapterError("github_pagination_envelope_invalid")
        return {"repositories": [record for page in pages for record in page]}

    @staticmethod
    def _identity(payload: dict) -> tuple:
        login, identifier = payload.get("login"), payload.get("id")
        if (
            not isinstance(login, str)
            or not login
            or type(identifier) is not int
            or identifier <= 0
        ):
            raise AdapterError("github_identity_unverified")
        return str(identifier), login.lower()

    def list_repositories(self) -> dict:
        """Enumerate all owned repositories with the native CLI's Link pagination.

        The process runner bounds duration and output. No manual page loop or
        assumed first-page completeness is used. GitHub and Cloud coverage are
        reported independently.
        """
        with operation_scope(active_operation(self.settings.timeout)) as operation:
            operation.report("github_repository_catalog")
            try:
                before = self._identity(self._get("user", "{id,login}"))
                if self.settings.account is not None and before[1] != self.settings.account.lower():
                    raise AdapterError("github_account_mismatch")
                response = self._get(
                    "user/repos?affiliation=owner&sort=full_name&direction=asc&per_page=100",
                    "{repositories:[.[][]|{id,full_name,private}]}",
                    paginate=True,
                )
                after = self._identity(self._get("user", "{id,login}"))
                if before != after:
                    raise AdapterError("github_account_changed")
                raw = response.get("repositories")
                if not isinstance(raw, list) or len(raw) > 10000:
                    raise AdapterError("github_repository_catalog_invalid")
                repositories, seen = [], set()
                for row in raw:
                    if not isinstance(row, dict):
                        raise AdapterError("github_repository_catalog_invalid")
                    identifier = row.get("id")
                    name = normalize_repository(row.get("full_name"))
                    if (
                        type(identifier) is not int
                        or identifier <= 0
                        or name is None
                        or type(row.get("private")) is not bool
                    ):
                        raise AdapterError("github_repository_catalog_invalid")
                    if identifier in seen:
                        raise AdapterError("github_repository_catalog_changed_during_pagination")
                    seen.add(identifier)
                    repositories.append(
                        {
                            "repository_id": str(identifier),
                            "repository": name,
                            "private": row["private"],
                        }
                    )
                return {
                    "status": "ok",
                    "catalog_complete": True,
                    "repositories": repositories,
                    "count": len(repositories),
                    "scope": "affiliation=owner",
                    "source": "github_cli",
                    "github_account": before[1],
                    "github_account_id": before[0],
                    "observed_at": now_utc(),
                    "cloud_environment_verified": False,
                }
            except AdapterError as error:
                return {
                    "status": "not_verifiable",
                    "catalog_complete": False,
                    "repositories": [],
                    "reason": error.reason,
                    "scope": "affiliation=owner",
                    "source": "github_cli",
                    "observed_at": now_utc(),
                    "cloud_environment_verified": False,
                }

    def resolve(self, repository: str) -> dict:
        if not isinstance(repository, str):
            raise ValueError("Repository must be a numeric ID or GitHub owner/repo")
        requested = repository.strip()
        numeric = bool(re.fullmatch(r"[1-9][0-9]{0,19}", requested))
        normalized = normalize_repository(requested)
        if not numeric and normalized is None:
            raise ValueError("Invalid repository identity")
        endpoint = "repositories/" + requested if numeric else "repos/" + normalized
        with operation_scope(active_operation(self.settings.timeout)) as operation:
            operation.report("github_repository")
            try:
                before = self._identity(self._get("user", "{id,login}"))
                if self.settings.account is not None and before[1] != self.settings.account.lower():
                    raise AdapterError("github_account_mismatch")
                raw = self._get(endpoint, "{id,full_name,private,default_branch}")
                after = self._identity(self._get("user", "{id,login}"))
                if before != after:
                    raise AdapterError("github_account_changed")
                identifier, full_name = raw.get("id"), raw.get("full_name")
                canonical = normalize_repository(full_name)
                if type(identifier) is not int or identifier <= 0 or canonical is None:
                    raise AdapterError("github_repository_invalid")
                if numeric and str(identifier) != requested:
                    raise AdapterError("github_repository_id_mismatch")
                if not isinstance(raw.get("private"), bool):
                    raise AdapterError("github_repository_invalid")
                return {
                    "status": "verified",
                    "repository_id": str(identifier),
                    "repository": canonical,
                    "requested": requested,
                    "github_account": before[1],
                    "github_account_id": before[0],
                    "source": "github_cli",
                    "observed_at": now_utc(),
                    "private": raw["private"],
                    "cloud_environment_verified": False,
                }
            except AdapterError as error:
                return {
                    "status": "not_verifiable",
                    "requested": requested,
                    "reason": error.reason,
                    "source": "github_cli",
                    "observed_at": now_utc(),
                    "cloud_environment_verified": False,
                }


def match_verified_repository(environment: EnvironmentDescriptor, evidence: Mapping) -> str:
    """An ID conflict cannot be overridden by a coincidentally matching name."""
    if evidence.get("status") != "verified":
        return "none"
    identifier, name = evidence["repository_id"], evidence["repository"]
    associations = list(environment.repositories) + [
        {"repository_id": environment.repository_id, "repository": environment.repository}
    ]
    if any(item.get("repository_id") == identifier for item in associations):
        return "verified"
    for item in associations:
        if normalize_repository(item.get("repository")) == name:
            return "none" if item.get("repository_id") not in (None, identifier) else "verified"
    if environment.name.strip().casefold() in {name, name.split("/")[1]}:
        return "hint"
    return "none"
