"""Bounded, cancellable read operations shared by CLI, adapters and MCP."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Event
from time import monotonic
from typing import Callable, Iterator, Optional


class OperationCancelled(RuntimeError):
    """The caller cancelled the active read; no further stage may run."""


class OperationTimedOut(TimeoutError):
    """The complete operation exhausted its budget."""


@dataclass
class Operation:
    timeout: float = 30.0
    cancelled: Event = field(default_factory=Event)
    progress: Optional[Callable[[str], None]] = None
    started: float = field(default_factory=monotonic)

    def check(self) -> None:
        if self.cancelled.is_set():
            raise OperationCancelled("Discovery cancelled")
        if monotonic() - self.started >= self.timeout:
            raise OperationTimedOut("Discovery deadline reached")

    def remaining(self) -> float:
        self.check()
        return max(0.01, self.timeout - (monotonic() - self.started))

    def report(self, stage: str) -> None:
        self.check()
        if self.progress is not None:
            self.progress(stage)


_ACTIVE: ContextVar[Optional[Operation]] = ContextVar("discovery_operation", default=None)


@contextmanager
def operation_scope(operation: Operation) -> Iterator[Operation]:
    token = _ACTIVE.set(operation)
    try:
        operation.check()
        yield operation
    finally:
        _ACTIVE.reset(token)


def checkpoint() -> None:
    operation = _ACTIVE.get()
    if operation is not None:
        operation.check()


def active_operation(default_timeout: float = 30.0) -> Operation:
    return _ACTIVE.get() or Operation(timeout=default_timeout)
