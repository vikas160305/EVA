"""Fast-path intent router for MARK-L.

Interprets high-frequency local OS commands (volume, brightness, application launching,
system telemetry) and executes them directly in <30ms without needing cloud LLM roundtrips.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional, Tuple


def _handle_volume(text: str) -> Optional[str]:
    from actions.computer_settings import computer_settings

    lower = text.lower()
    if "mute" in lower or "unmute" in lower:
        act = "mute" if "mute" in lower and "unmute" not in lower else "unmute"
        res = computer_settings(parameters={"action": act})
        return f"Volume updated: {res}"
    
    match = re.search(r"(?:set|change|put)?\s*volume\s*(?:to)?\s*(\d+)%?", lower)
    if match:
        val = match.group(1)
        res = computer_settings(parameters={"action": "volume_set", "value": int(val)})
        return f"Volume set to {val}%"
    
    if "volume up" in lower or "increase volume" in lower or "raise volume" in lower:
        res = computer_settings(parameters={"action": "volume_up"})
        return "Increased volume."
    
    if "volume down" in lower or "decrease volume" in lower or "lower volume" in lower:
        res = computer_settings(parameters={"action": "volume_down"})
        return "Decreased volume."
    
    return None


def _handle_app_launch(text: str) -> Optional[str]:
    lower = text.lower()
    patterns = [
        r"^open\s+([a-zA-Z0-9\s]+)$",
        r"^launch\s+([a-zA-Z0-9\s]+)$",
        r"^start\s+([a-zA-Z0-9\s]+)$",
    ]
    for pat in patterns:
        match = re.match(pat, lower.strip())
        if match:
            app_name = match.group(1).strip()
            # Filter out non-app phrases
            if app_name in ["camera", "screen", "browser", "menu", "settings", "volume", "webcam"]:
                continue
            from actions.open_app import open_app
            res = open_app(app_name)
            return f"Opening {app_name}..."
    return None


def _handle_system_stats(text: str) -> Optional[str]:
    lower = text.lower()
    if any(phrase in lower for phrase in ["system stats", "cpu usage", "ram usage", "battery level", "hardware status", "stats"]):
        from actions.system_monitor import get_system_status
        stats = get_system_status()
        if isinstance(stats, dict):
            cpu = stats.get("cpu_percent", stats.get("cpu", "N/A"))
            ram = stats.get("ram_percent", stats.get("ram", "N/A"))
            return f"System status: CPU usage is {cpu}%, RAM usage is {ram}%."
        return f"System status: {stats}"
    return None


def _handle_screenshot(text: str) -> Optional[str]:
    lower = text.lower()
    if any(phrase in lower for phrase in ["take screenshot", "capture screen", "screen capture"]):
        from actions.screen_processor import _capture_screen
        try:
            img_bytes, mime = _capture_screen()
            return "Screen capture completed successfully."
        except Exception as e:
            return f"Screenshot error: {e}"
    return None


_INTENT_HANDLERS: list[Callable[[str], Optional[str]]] = [
    _handle_volume,
    _handle_app_launch,
    _handle_system_stats,
    _handle_screenshot,
]


def match_fast_intent(text: str) -> Optional[str]:
    """Check if input matches a fast-path local intent.
    
    Returns execution response string if matched and executed locally (<30ms),
    or None if the query should be handled by Gemini Live LLM.
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()
    for handler in _INTENT_HANDLERS:
        try:
            result = handler(cleaned)
            if result:
                return result
        except Exception:
            continue

    return None
