"""Minimal service-boundary registry used for Phase 5 architecture hardening.

It is intentionally simple and dependency-free. It documents the intended
service ownership boundaries across the repo without changing the behavior of
existing action modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ServiceBoundary:
    name: str
    owner: str
    responsibilities: tuple[str, ...]
    boundaries: tuple[str, ...]


SERVICE_BOUNDARIES = {
    "audio": ServiceBoundary("audio", "core.tts + stt + ui", ("playback", "capture", "queue"), ("LLM", "file")),
    "llm": ServiceBoundary("llm", "core.llm_client", ("provider routing", "prompt shaping", "response formatting"), ("UI", "OS")),
    "search": ServiceBoundary("search", "actions.web_search", ("web providers", "ranking", "dedupe", "public URL checks"), ("file")),
    "file_document": ServiceBoundary("file_document", "actions.file_controller", ("safe artifact writes", "document conversions", "format validation"), ("UI", "network")),
    "memory": ServiceBoundary("memory", "memory.memory_manager", ("long-term recall", "session summaries", "turn memory"), ("search", "OS")),
    "ui": ServiceBoundary("ui", "ui.JarvisUI", ("rendering", "events", "sanitized feedback"), ("service startup")),
    "os_actions": ServiceBoundary("os_actions", "actions.*", ("launch", "desktop", "system", "message", "browser"), ("LLM", "search")),
}


def get_boundary(name: str) -> ServiceBoundary:
    return SERVICE_BOUNDARIES[name]


def registered_services() -> list[str]:
    return sorted(SERVICE_BOUNDARIES)
