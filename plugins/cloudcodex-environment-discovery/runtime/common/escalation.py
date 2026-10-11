"""Explicit, auditable escalation among pre-authorized read-only sources."""
from __future__ import annotations

from dataclasses import dataclass, replace
from time import monotonic
from typing import Optional, Sequence

from .adapters import AdapterError
from .models import ProviderResult
from .operation import OperationCancelled, OperationTimedOut, active_operation, operation_scope
from .protocols import EnvironmentProvider

TERMINAL = frozenset({"unauthorized", "forbidden", "approval_required", "cancelled", "timeout", "rate_limited"})
RECOVERABLE = frozenset({"unavailable", "partial", "stale", "invalid_response", "not_found"})


@dataclass(frozen=True)
class Stage:
    name: str
    provider: EnvironmentProvider
    approved: bool = True


class EscalatingProvider:
    """Runs only configured, approved stages. A denial is never bypassed.

    In CONFIRM mode an unapproved stage returns approval_required. In AUTO it
    is skipped, never approved implicitly. A previous partial result may be
    retained as candidate evidence but is never promoted to a complete catalog.
    """

    def __init__(self, cloud_type: str, stages: Sequence[Stage], mode: str = "AUTO"):
        if mode not in {"AUTO", "CONFIRM"}:
            raise ValueError("Invalid escalation mode")
        if any(stage.provider.name != cloud_type for stage in stages):
            raise ValueError("Cannot escalate between different Cloud generations")
        if len({stage.name for stage in stages}) != len(stages):
            raise ValueError("Duplicate escalation stage")
        self.name, self.stages, self.mode = cloud_type, tuple(stages), mode

    def list_environments(self, account: Optional[str] = None,
                          include_drafts: bool = False) -> ProviderResult:
        return self._query(account, include_drafts)

    def find_environments(self, repository, account=None, include_drafts=False):
        return self._query(account, include_drafts, repository)

    def _query(self, account, include_drafts, repository=None):
        operation = active_operation()
        with operation_scope(operation):
            return self._run(operation, account, include_drafts, repository)

    def _run(self, operation, account, include_drafts, repository):
        attempts = []
        best: Optional[ProviderResult] = None
        verified_account = account
        last = ProviderResult(provider=self.name, reason="no_authorized_source_configured")
        for stage in self.stages:
            operation.report(stage.name)
            if not stage.approved:
                attempts.append({"stage": stage.name, "status": "approval_required",
                                 "reason": "stage_not_pre_authorized", "elapsed_ms": 0})
                if self.mode == "CONFIRM":
                    return ProviderResult(provider=self.name, status="approval_required",
                                          attempts=attempts, reason="stage_not_pre_authorized")
                continue
            started = monotonic()
            try:
                finder = getattr(stage.provider, "find_environments", None)
                result = (finder(repository=repository, account=verified_account, include_drafts=include_drafts)
                          if repository is not None and callable(finder)
                          else stage.provider.list_environments(account=verified_account, include_drafts=include_drafts))
                if result.provider != self.name:
                    raise AdapterError("host_identity_mismatch")
            except (OperationCancelled, OperationTimedOut):
                raise
            except AdapterError as error:
                if error.reason in {"host_integrity_mismatch", "host_identity_mismatch",
                                    "unapproved_catalog_destination", "catalog_not_json"}:
                    status = "forbidden"
                elif error.reason == "host_timeout":
                    status = "timeout"
                elif error.reason == "stale_observation":
                    status = "stale"
                elif error.reason in {"host_invalid_json", "host_invalid_envelope", "invalid_http_status",
                                      "invalid_catalog_status", "invalid_observation_time", "catalog_schema_mismatch"}:
                    status = "invalid_response"
                else:
                    status = "unavailable"
                result = ProviderResult(provider=self.name, status=status, reason=error.reason)
            except (OSError, ValueError, RuntimeError, TypeError):
                result = ProviderResult(provider=self.name, status="unavailable",
                                        reason="source_read_failed")
            operation.check()
            if verified_account is not None and result.evidence == "live" and not result.account_verified:
                result = ProviderResult(provider=self.name, status="forbidden",
                                        reason="account_unverified_during_escalation")
            if result.account_verified:
                if verified_account is not None and result.account != verified_account:
                    result = ProviderResult(provider=self.name, status="forbidden",
                                            reason="account_changed_during_escalation")
                else:
                    verified_account = result.account
            attempts.append({"stage": stage.name, "status": result.status,
                             "reason": result.reason,
                             "catalog_complete": result.catalog_complete,
                             "count": len(result.environments),
                             "elapsed_ms": round((monotonic() - started) * 1000, 1)})
            result.source = result.source or stage.name
            result.attempts = list(attempts)
            last = result
            if result.status in TERMINAL:
                if best is not None and not result.environments:
                    result.environments = list(best.environments)
                    result.evidence = best.evidence
                    result.warnings = list(best.warnings) + ["Candidate evidence predates the blocked stage"]
                result.catalog_complete = False
                return result
            if (result.status in {"ok", "empty"} and result.catalog_complete
                    and result.evidence == "live"):
                return result  # Also stop on a VERIFIED empty catalog.
            if result.environments:
                if best is None or (best.evidence != "live" and result.evidence == "live"):
                    best = result
            if result.status not in RECOVERABLE and result.status not in {"ok", "empty"}:
                result.catalog_complete = False
                result.reason = "unrecognized_source_status"
                return result
        final = replace(best if best is not None else last, attempts=list(attempts), catalog_complete=False)
        if final.status in {"ok", "empty"}:
            final.status = "partial"
        if not attempts:
            final.warnings.append("No connected read-only source is configured for this Cloud generation")
        return final
