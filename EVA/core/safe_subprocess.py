"""Safe subprocess wrappers for Phase 5 hardening.

The module provides a typed, list-based subprocess API and a background-task
context guard that prevents broad subprocess leaks and blocks on Windows
implementation differences.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterable


class SafeSubprocessError(RuntimeError):
    """User-friendly, diagnostic-safe wrapper for subprocess errors."""


class SafeBackgroundTask:
    """A tiny lifecycle guard for background activities.

    It is intentionally dependency-free and allows tests to exercise safe
    cancellation without touching the rest of the workflow.
    """

    def __init__(self, task_name: str = "task"):
        self.task_name = task_name
        self.cancel_event = threading.Event()
        self.started = time.monotonic()
        self.thread = None
        self.closed = False

    def cancel(self) -> None:
        self.cancel_event.set()
        self.closed = True

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def join(self, timeout: float | None = None) -> bool:
        if self.thread is None:
            return True
        self.thread.join(timeout=timeout)
        return not self.thread.is_alive()


def safe_run(args: list[str] | tuple[str, ...], *, cwd: str | Path | None = None,
             timeout: float | None = 30.0, env: dict[str, str] | None = None,
             text: bool = True, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Safe subprocess wrapper with typed list arguments and timeout guard.

    It avoids broad shell=True usage and never accepts a raw string command.
    """
    if isinstance(args, str):
        raise TypeError("safe_run expects an argument list, not a raw shell string")
    if not isinstance(args, (list, tuple)) or not args:
        raise TypeError("safe_run requires a non-empty list or tuple of arguments")
    parsed = [str(item) for item in args]
    safe_env = os.environ.copy()
    if env:
        safe_env.update(env)
    try:
        proc = subprocess.run(
            parsed,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            env=safe_env,
            text=text,
            capture_output=True,
            check=check,
            shell=False,
        )
        return proc
    except subprocess.TimeoutExpired as exc:
        raise SafeSubprocessError("The requested subprocess exceeded the safe timeout window.") from exc
    except OSError as exc:
        raise SafeSubprocessError("The requested subprocess could not be started safely.") from exc


def safe_background(task: Any, *, name: str = "background") -> SafeBackgroundTask:
    """Create a cancellable background lifecycle object without spawning shell jobs."""
    guard = SafeBackgroundTask(name)
    def _runner() -> None:
        try:
            if task:
                task()
        finally:
            guard.closed = True
    import threading as _threading
    guard.thread = _threading.Thread(target=_runner, name=name, daemon=True)
    guard.thread.start()
    return guard
