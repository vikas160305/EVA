import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import screen_reader_app
from core.config import Settings, get_settings
from core.safe_logging import sanitized_record, set_task_id, set_turn_id
from core.safe_subprocess import SafeBackgroundTask, safe_run, SafeSubprocessError
from core.service_boundaries import SERVICE_BOUNDARIES, registered_services


def test_settings_reads_safe_env_defaults(monkeypatch):
    monkeypatch.delenv("MARK_L_GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("MARK_L_LOG_LEVEL", "DEBUG")
    settings = get_settings()
    assert settings.log_level == "DEBUG"
    assert settings.safe_home == str(Path.home())
    assert settings.timeout_seconds == 60.0


def test_sanitized_logging_redacts_secrets_and_stores_ids():
    set_task_id("task-123")
    set_turn_id("turn-abc")
    payload = sanitized_record("launch", gemini_api_key="secret-token-value", password="hidden", api_key="x")
    assert payload["task_id"] == "task-123"
    assert payload["turn_id"] == "turn-abc"
    assert payload["gemini_api_key"] == "<redacted>"
    assert payload["password"] == "<redacted>"
    assert "secret-token-value" not in str(payload)


def test_safe_subprocess_requires_argument_list_and_supports_timeout(monkeypatch):
    fake = Mock()
    fake.run = Mock(side_effect=SafeSubprocessError("timeout"))
    monkeypatch.setattr("core.safe_subprocess.subprocess.run", fake.run)
    try:
        safe_run(["python", "-c", "print(1)"])
    except SafeSubprocessError:
        pass
    else:
        raise AssertionError("safe_run accepted the mocked subprocess path without error")


def test_ocr_image_decodes_raw_tesseract_bytes_without_unicode_crash(monkeypatch):
    monkeypatch.setattr("screen_reader_app._find_tesseract", lambda: "tesseract.exe")

    class FakeProc:
        returncode = 0
        stdout = b"visible text \x9d okay"
        stderr = b""

    def fake_run(cmd, capture_output=True, text=False, check=False):
        return FakeProc()

    monkeypatch.setattr("screen_reader_app.subprocess.run", fake_run)

    text = screen_reader_app._ocr_image(Path("dummy.png"))
    assert "visible text" in text
    assert "okay" in text


def test_safe_subprocess_background_lifecycle_and_boundaries_registry(monkeypatch):
    fake_thread = Mock()
    fake_thread.is_alive.return_value = False
    fake_thread.join = Mock()
    monkeypatch.setattr("core.safe_subprocess.threading.Thread", Mock(return_value=fake_thread))

    task = SafeBackgroundTask("probe")
    assert task.is_cancelled() is False
    task.cancel()
    assert task.is_cancelled() is True
    assert "audio" in SERVICE_BOUNDARIES
    assert "llm" in SERVICE_BOUNDARIES
    assert "file_document" in SERVICE_BOUNDARIES
    assert "search" in SERVICE_BOUNDARIES
    assert sorted(registered_services()) == sorted(SERVICE_BOUNDARIES)


def test_jarvis_system_monitor_check_handles_shutdown_executor_errors(monkeypatch):
    import main

    fake_ui = SimpleNamespace(
        on_text_command=None,
        on_remote_clicked=None,
        on_interrupt=None,
    )
    jarvis = main.JarvisLive(fake_ui)

    async def fake_to_thread(fn, *args, **kwargs):
        raise RuntimeError("cannot schedule new futures after shutdown")

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    assert asyncio.run(jarvis._safe_system_monitor_check()) is None
