"""Isolated terminal screen reader for the standard Codex CLI.

Only fixed read-only navigation is supported. This module never opens client
logs, authentication files, browser profiles or process memory. Native client
output is rendered in memory and discarded when the terminal is closed.
"""

from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import threading
from typing import Callable, Optional

from common.operation import Operation

KEYS = {
    "selector": "o",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "next_page": "\x1b[6~",
    "escape": "\x1b",
    "quit": "q",
}
MAX_OUTPUT = 8 * 1024 * 1024


class NativeTerminal:
    def __init__(self, executable: Path, cwd: Path, operation: Operation):
        import pyte

        self.operation = operation
        self.queue: queue.Queue = queue.Queue(maxsize=128)
        self.stop = threading.Event()
        self.failure: Optional[str] = None
        self.screen = pyte.Screen(300, 80)
        self.stream = pyte.Stream(self.screen)
        self._pending = ""
        self.fd = None
        self.windows = os.name == "nt"
        names = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "HOMEDRIVE",
            "HOMEPATH",
            "COMSPEC",
            "PATHEXT",
        }
        environment = {name: value for name, value in os.environ.items() if name.upper() in names}
        environment["TERM"] = "xterm-256color"
        if self.windows:
            from winpty import PtyProcess

            self.process = PtyProcess.spawn(
                [str(executable), "cloud"], cwd=str(cwd), env=environment, dimensions=(80, 300)
            )
        else:
            import fcntl
            import pty
            import struct
            import termios

            master, slave = pty.openpty()
            self.fd = master
            try:
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 80, 300, 0, 0))
                self.process = subprocess.Popen(
                    [str(executable), "cloud"],
                    cwd=str(cwd),
                    env=environment,
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                    start_new_session=True,
                )
            except BaseException:
                os.close(master)
                raise
            finally:
                os.close(slave)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        total = 0
        try:
            while not self.stop.is_set():
                raw = self.process.read(8192) if self.windows else os.read(self.fd, 8192)
                if not raw:
                    break
                text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
                total += len(text.encode("utf-8"))
                if total > MAX_OUTPUT:
                    self.failure = "native_terminal_output_limit"
                    break
                self.queue.put(text, timeout=1)
        except queue.Full:
            self.failure = "native_terminal_output_backpressure"
        except (EOFError, OSError, RuntimeError):
            pass
        finally:
            self.stop.set()

    def send(self, key: str) -> None:
        self.operation.check()
        if key not in KEYS:
            raise ValueError("Native terminal action is not read-only navigation")
        value = KEYS[key]
        if self.windows:
            self.process.write(value)
        else:
            os.write(self.fd, value.encode("ascii"))

    def wait(self, predicate: Callable) -> object:
        """Wait for rendered-state events, not a fixed sleep or primary keyboard."""
        while True:
            self.operation.check()
            if self.failure:
                raise RuntimeError(self.failure)
            if self.stop.is_set() and self.queue.empty():
                raise RuntimeError("native_terminal_exited_before_catalog")
            try:
                text = self.queue.get(timeout=min(0.1, self.operation.remaining()))
            except queue.Empty:
                continue
            self._pending += text
            # Ratatui/crossterm ends a rendered frame by hiding the cursor.
            # PTY reads split arbitrarily: do not parse half-drawn borders/IDs.
            marker = "\x1b[?25l"
            end = self._pending.rfind(marker)
            if end < 0:
                continue
            end += len(marker)
            self.stream.feed(self._pending[:end])
            self._pending = self._pending[end:]
            lines = tuple(self.screen.display)
            if any("Not signed in" in line for line in lines):
                raise PermissionError("native_cli_login_required")
            result = predicate(lines)
            if result is not None:
                return result

    def close(self) -> None:
        self.stop.set()
        try:
            if self.windows:
                if self.process.isalive():
                    # Closing our own PTY process is not a task/environment mutation.
                    self.process.close(force=True)
            else:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
                if self.fd is not None:
                    os.close(self.fd)
        finally:
            self.reader.join(timeout=1)
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break
