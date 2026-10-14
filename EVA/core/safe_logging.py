"""Structured, sanitized logging helpers for Phase 5.

The design is intentionally dependency-light: log with task_id and turn_id
fields when present, and strip sensitive keys or values from the record before
emitting them.
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from collections.abc import Mapping
from contextvars import ContextVar
from typing import Any


_task_id: ContextVar[str | None] = ContextVar("task_id", default=None)
_turn_id: ContextVar[str | None] = ContextVar("turn_id", default=None)


def set_task_id(task_id: str | None) -> None:
    _task_id.set(task_id)


def set_turn_id(turn_id: str | None) -> None:
    _turn_id.set(turn_id)


def sanitized_record(message: str, **extra: Any) -> dict[str, Any]:
    """Return a logging payload that drops known secret or cert material.

    The payload only keeps timing and IDs; secrets are never kept in logs.
    """
    clean = {key: value for key, value in extra.items() if value is not None}
    # scrub obvious secret and certificate fields
    for key in list(clean):
        lowered = key.lower()
        if any(token in lowered for token in ("key", "secret", "token", "password", "cert", "pem")):
            clean[key] = "<redacted>"
    # scrub values that are big blobs
    for key, value in list(clean.items()):
        if isinstance(value, str) and len(value) > 400:
            clean[key] = value[:300] + "...<truncated>"
    payload = {
        "message": re.sub(r"(?i)(api[_-]?key|token|secret|password|cert|pem)", "<redacted>", message),
        "task_id": _task_id.get(),
        "turn_id": _turn_id.get(),
        "timestamp_ms": round(time.monotonic() * 1000.0, 3),
    }
    payload.update(clean)
    return payload


class SanitizedLogger:
    """Adapter with environment-safe structured logging semantics."""

    def __init__(self, name: str = "markl"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, os.getenv("MARK_L_LOG_LEVEL", "INFO").upper(), logging.INFO))

    def info(self, message: str, **extra: Any) -> None:
        self.logger.info("%s", sanitized_record(message, **extra))

    def warning(self, message: str, **extra: Any) -> None:
        self.logger.warning("%s", sanitized_record(message, **extra))

    def error(self, message: str, **extra: Any) -> None:
        self.logger.error("%s", sanitized_record(message, **extra))

    def exception(self, message: str, **extra: Any) -> None:
        self.logger.exception("%s", sanitized_record(message, **extra))


def get_logger(name: str = "markl") -> SanitizedLogger:
    return SanitizedLogger(name)
