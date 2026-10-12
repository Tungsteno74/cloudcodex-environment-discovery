"""Real Legacy discovery using only the ordinary native selector screen.

The earlier refused log/session adapter is not used. This implementation reads
rendered TUI rows through standard terminal I/O, never private logs or secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Callable, Mapping

from common.adapters import CommandSpec
from common.models import ProviderResult
from common.operation import (
    OperationCancelled,
    OperationTimedOut,
    active_operation,
    operation_scope,
)
from .selector import parse_selector


@dataclass(frozen=True)
class NativeCliSettings:
    executable: str
    sha256: str
    max_pages: int = 50

    @classmethod
    def from_mapping(cls, data: Mapping) -> "NativeCliSettings":
        if not isinstance(data, dict) or set(data) - {"executable", "sha256", "max_pages"}:
            raise ValueError("Invalid native selector settings")
        executable, digest = data.get("executable"), data.get("sha256")
        if (
            not isinstance(executable, str)
            or not Path(executable).is_absolute()
            or Path(executable).name.lower() not in {"codex.exe", "codex"}
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
        ):
            raise ValueError("Native Codex executable must be absolute and hash-pinned")
        pages = data.get("max_pages", 50)
        if type(pages) is not int or not 1 <= pages <= 100:
            raise ValueError("Invalid selector page bound")
        return cls(executable, digest, pages)


def _production_terminal(executable, directory, operation):
    from .terminal import NativeTerminal

    return NativeTerminal(executable, directory, operation)


class NativeCliEnvironmentProvider:
    name = "legacy"

    def __init__(
        self,
        settings: NativeCliSettings,
        terminal_factory: Callable = _production_terminal,
        version_reader: Callable = None,
    ):
        self.settings = settings
        self._terminal_factory = terminal_factory
        self._version_reader = version_reader

    def _version(self, operation) -> str:
        executable = Path(self.settings.executable)
        CommandSpec(
            (str(executable), "cloud"),
            ((str(executable), self.settings.sha256),),
            str(executable.parent),
        ).verify()
        if self._version_reader is not None:
            return self._version_reader()
        try:
            version = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                timeout=min(5, operation.remaining()),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except subprocess.TimeoutExpired:
            raise OperationTimedOut("Native CLI version read exceeded its bound") from None
        if version.returncode != 0:
            raise RuntimeError("native_cli_version_unavailable")
        return version.stdout.decode("utf-8", errors="replace").strip()

    @staticmethod
    def _selected(lines, different=None):
        page = parse_selector(lines)
        if page is not None and page.selected is not None and page.selected != different:
            return page
        return None

    def list_environments(self, account=None, include_drafts=False) -> ProviderResult:
        if type(include_drafts) is not bool or account is not None and not isinstance(account, str):
            raise ValueError("Invalid native discovery arguments")
        operation = active_operation(30)
        entries = {}
        enumerated = False
        pages = 0
        with operation_scope(operation):
            version = self._version(operation)
            if version != "codex-cli 0.162.0":
                return ProviderResult(
                    provider=self.name,
                    status="unavailable",
                    reason="native_cli_version_not_validated",
                )
            terminal = None
            # A fresh, non-repository cwd requests the native global selector.
            # Native-created temporary files are removed unread on exit.
            with tempfile.TemporaryDirectory(prefix="cloudcodex-selector-") as folder:
                try:
                    terminal = self._terminal_factory(
                        Path(self.settings.executable), Path(folder), operation
                    )
                    terminal.wait(
                        lambda lines: True if any("Set Env" in row for row in lines) else None
                    )
                    terminal.send("selector")
                    first = terminal.wait(self._selected)
                    if first.selected != "__global__":
                        # Native modal may preserve its selected environment.
                        # Anchor at Home before assuming the first visible
                        # page starts at the beginning of the catalog.
                        terminal.send("home")
                        first = terminal.wait(
                            lambda lines: page
                            if (page := self._selected(lines)) is not None
                            and page.selected == "__global__"
                            and page.global_visible
                            else None
                        )
                    for item in first.environments:
                        entries[item.environment_id] = item
                    terminal.send("end")
                    if not first.environments:
                        # UI may hide an unavailable backend behind an empty picker.
                        # Never turn an empty visual list into authoritative absence.
                        return ProviderResult(
                            provider=self.name,
                            status="partial",
                            evidence="live",
                            reason="native_selector_empty_not_authoritative",
                            coverage={
                                "surface": "native_tui",
                                "visible_rows_complete": True,
                                "account_catalog_complete": False,
                            },
                        )
                    end = terminal.wait(lambda lines: self._selected(lines, first.selected))
                    target = end.selected
                    enumerated = target in entries
                    for item in end.environments:
                        entries[item.environment_id] = item
                    if not enumerated:
                        terminal.send("home")
                        previous = terminal.wait(lambda lines: self._selected(lines, target))
                        while pages < self.settings.max_pages:
                            operation.check()
                            terminal.send("next_page")
                            page = terminal.wait(
                                lambda lines: self._selected(lines, previous.selected)
                            )
                            pages += 1
                            for item in page.environments:
                                entries[item.environment_id] = item
                            if page.selected == target:
                                enumerated = True
                                break
                            previous = page
                    return ProviderResult(
                        provider=self.name,
                        status="partial",
                        environments=list(entries.values()),
                        evidence="live",
                        scope="native_global_selector",
                        catalog_complete=False,
                        source="codex_tui_screen",
                        reason="native_selector_rows_enumerated"
                        if enumerated
                        else "native_selector_page_limit",
                        coverage={
                            "surface": "native_tui",
                            "visible_rows_complete": enumerated,
                            "account_catalog_complete": False,
                            "client_version": version,
                        },
                        warnings=[
                            "The native selector returned real IDs; it does not expose account identity or authoritative API completeness",
                            "Publication/draft state is not supplied by this Legacy selector",
                        ],
                    )
                except (OperationCancelled, OperationTimedOut):
                    raise
                except ImportError:
                    return ProviderResult(
                        provider=self.name,
                        status="unavailable",
                        reason="native_terminal_optional_dependencies_missing",
                    )
                except PermissionError:
                    return ProviderResult(
                        provider=self.name,
                        status="unauthorized",
                        reason="native_cli_login_required",
                    )
                except (OSError, ValueError, RuntimeError):
                    return ProviderResult(
                        provider=self.name,
                        status="invalid_response",
                        environments=list(entries.values()),
                        catalog_complete=False,
                        reason="native_selector_read_or_layout_failed",
                    )
                finally:
                    if terminal is not None:
                        terminal.close()
