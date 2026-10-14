"""Central, typed configuration defaults for Phase 5 hardening.

This module intentionally avoids persisting secrets in repository files. It reads
from environment variables first and falls back to local safe-in-repo defaults.
The goal is a single typed contract the rest of the system can import instead of
reaching into config/api_keys.json or process-wide globals.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppSettings:
    """Typed configuration contract used by the service layer.

    Secrets are never stored in the source tree; callers can read them from the
    environment or a local .env file kept outside version control.
    """

    gemini_api_key: str | None = None
    gemini_model: str = "models/gemini-2.5-flash-native-audio-preview-12-2025"
    search_mode: str = "search"
    cache_ttl_seconds: int = 30
    log_level: str = "INFO"
    timeout_seconds: float = 60.0
    allow_background_tasks: bool = True
    allow_windows_subprocess_hide: bool = True
    safe_home: str = str(Path.home())
    manifest_path: str = "config/api_keys.json"


class Settings:
    """Tiny environment-backed configuration registry.

    Supported environment variables:
      MARK_L_GEMINI_API_KEY
      MARK_L_GEMINI_MODEL
      MARK_L_SEARCH_MODE
      MARK_L_CACHE_TTL_SECONDS
      MARK_L_LOG_LEVEL
      MARK_L_TIMEOUT_SECONDS
      MARK_L_ALLOW_BACKGROUND_TASKS
      MARK_L_ALLOW_WINDOWS_SUBPROCESS_HIDE
      MARK_L_SAFE_HOME
      MARK_L_MANIFEST_PATH
    """

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> AppSettings:
        env = env or os.environ
        def as_bool(value: str | None, default: bool) -> bool:
            if value is None:
                return default
            text = value.strip().lower()
            return text in {"1", "true", "yes", "on"}

        cache_ttl = int(env.get("MARK_L_CACHE_TTL_SECONDS", "30"))
        timeout = float(env.get("MARK_L_TIMEOUT_SECONDS", "60.0"))
        allow_background = as_bool(env.get("MARK_L_ALLOW_BACKGROUND_TASKS"), True)
        allow_windows_hide = as_bool(env.get("MARK_L_ALLOW_WINDOWS_SUBPROCESS_HIDE"), True)

        return AppSettings(
            gemini_api_key=env.get("MARK_L_GEMINI_API_KEY") or env.get("GEMINI_API_KEY") or None,
            gemini_model=env.get("MARK_L_GEMINI_MODEL", "models/gemini-2.5-flash-native-audio-preview-12-2025"),
            search_mode=env.get("MARK_L_SEARCH_MODE", "search"),
            cache_ttl_seconds=cache_ttl,
            log_level=env.get("MARK_L_LOG_LEVEL", "INFO"),
            timeout_seconds=timeout,
            allow_background_tasks=allow_background,
            allow_windows_subprocess_hide=allow_windows_hide,
            safe_home=env.get("MARK_L_SAFE_HOME", str(Path.home())),
            manifest_path=env.get("MARK_L_MANIFEST_PATH", "config/api_keys.json"),
        )

    @staticmethod
    def validate(settings: AppSettings) -> list[str]:
        """Return a list of configuration warnings without exposing secrets."""
        warnings: list[str] = []
        if settings.gemini_api_key:
            warnings.append("gemini_api_key: configured via environment")
        else:
            warnings.append("gemini_api_key: not configured; provider calls will fail safely")
        if settings.timeout_seconds <= 0:
            warnings.append("timeout_seconds must be positive")
        if settings.cache_ttl_seconds < 0:
            warnings.append("cache_ttl_seconds must be non-negative")
        return warnings

    @staticmethod
    def require_safe_layout(root: Path | str = ".") -> None:
        """Ensure the repo is not accidentally committed with secrets and cert files."""
        root = Path(root)
        ignored = root / ".gitignore"
        if ignored.exists():
            return
        raise RuntimeError("Missing .gitignore; repository must define safe ignore rules")


def get_settings(env: dict[str, str] | None = None) -> AppSettings:
    return Settings.from_env(env)


def startup_validation() -> tuple[bool, list[str]]:
    """Soft validation of presence of the repository's safety files.

    Returns (ok, warnings) and keeps diagnostics separate from user-facing output.
    """
    root = Path(__file__).resolve().parent.parent
    warnings: list[str] = []
    for required in (root / ".gitignore", root / ".env.example"):
        if not required.exists():
            warnings.append(f"missing required safety file: {required.name}")
    if not (root / "core").exists():
        warnings.append("missing core package")
    return len(warnings) == 0, warnings
