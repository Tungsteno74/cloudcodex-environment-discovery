"""Preserve authorized Codex Tasks observations without inventing Cloud IDs.

This parser consumes an explicit operator/Root-supplied connector export. It
never calls an unavailable connector, interprets prose as authority, or treats
a task ID as an environment/configuration ID. Evidence is always indirect.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from common.models import ProviderResult, normalize_repository, parse_environment
from common.snapshot import read_evidence_file


class OnboardingEvidenceProvider:
    name = "current"

    def __init__(self, document: Mapping[str, Any]):
        self.document = document

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        try:
            document = self.document
            if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
                    or document["schema_version"] != 1 or document.get("source") != "codex_tasks"):
                raise ValueError("Unknown connector evidence envelope")
            observed = document.get("observed_at")
            when = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if when.tzinfo is None:
                raise ValueError("Evidence timestamp requires timezone")
            payload = document.get("payload")
            if not isinstance(payload, dict):
                raise ValueError("Missing connector output")
            if isinstance(payload.get("tasks"), list) and "task" not in payload:
                tasks = payload["tasks"]
            elif isinstance(payload.get("task"), dict) and "tasks" not in payload:
                tasks = [payload["task"]]
            else:
                raise ValueError("Not a task-list or task-read response")
            if len(tasks) > 100:
                raise ValueError("Evidence batch exceeds maximum size")
            hints, environments, seen = [], [], set()
            for task in tasks:
                if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                    raise ValueError("Missing task identity")
                task_id = task["id"]
                if not task_id or len(task_id) > 256 or task_id in seen:
                    raise ValueError("Invalid or duplicate task identity")
                seen.add(task_id)
                title = task.get("title", "")
                if not isinstance(title, str) or len(title) > 4096:
                    raise ValueError("Invalid task title")
                explicit_id = task.get("configuration_id") or task.get("configId")
                if explicit_id is not None and (not isinstance(explicit_id, str) or not explicit_id
                                               or len(explicit_id) > 4096 or explicit_id == task_id):
                    raise ValueError("Invalid or task-equivalent configuration identity")
                repository = normalize_repository(task.get("repository_full_name"))
                hints.append({"task_id": task_id, "title": title,
                              "configuration_id": explicit_id, "repository": repository,
                              "evidence": "indirect", "observed_at": observed,
                              "requires_catalog_confirmation": True})
                if explicit_id:
                    # Ignore free-text assistant messages, lifecycle status and
                    # alleged draft/publication state. The catalog must confirm.
                    environments.append(parse_environment(
                        {"configuration_id": explicit_id, "name": title or explicit_id,
                         "repository_full_name": repository}, "current", "onboarding",
                        "codex_tasks_export", evidence="indirect", observed_at=observed))
            return ProviderResult(
                provider="current", status="partial", environments=environments,
                catalog_complete=False, scope="onboarding", evidence="indirect",
                observed_at=observed, source="codex_tasks_export", hints=hints,
                reason="onboarding_requires_catalog_confirmation",
                warnings=["Task observations are hints, not a complete Cloud configuration catalog"],
            )
        except (ValueError, TypeError, AttributeError):
            return ProviderResult(provider="current", status="invalid_response",
                                  reason="invalid_onboarding_evidence", catalog_complete=False)


class OnboardingEvidenceFile:
    name = "current"

    def __init__(self, path: Path):
        self.path = path

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        return OnboardingEvidenceProvider(read_evidence_file(self.path)).list_environments(
            account=account, include_drafts=include_drafts)
