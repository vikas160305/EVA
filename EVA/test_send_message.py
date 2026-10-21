import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from actions.send_message import (
    _resolve_media_file,
    _copy_file_to_clipboard,
    _send_whatsapp,
    _desktop_send_media,
    send_message,
)
from main import TOOL_DECLARATIONS


def test_resolve_media_file_direct():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        p = Path(tf.name)
    try:
        resolved = _resolve_media_file(str(p))
        assert resolved == p
    finally:
        p.unlink(missing_ok=True)


def test_resolve_media_file_nonexistent():
    assert _resolve_media_file("definitely_nonexistent_file_xyz_123.bin") is None


def test_copy_file_to_clipboard():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        p = Path(tf.name)
        p.write_text("test content", encoding="utf-8")
    try:
        ok = _copy_file_to_clipboard(p)
        assert ok is True
    finally:
        p.unlink(missing_ok=True)


def test_send_whatsapp_text_mocked():
    with patch("actions.send_message._desktop_send") as mock_ds:
        mock_ds.return_value = "Message sent to John via WhatsApp."
        res = _send_whatsapp("John", "Hello there")
        assert "Message sent to John via WhatsApp" in res
        mock_ds.assert_called_once_with("WhatsApp", "John", "Hello there")


def test_send_whatsapp_media_mocked():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        p = Path(tf.name)
    try:
        with patch("actions.send_message._desktop_send_media") as mock_dsm:
            mock_dsm.return_value = f"Successfully sent {p.name} to Mom via WhatsApp."
            res = _send_whatsapp("Mom", "Look at this", file_path=str(p))
            assert "Successfully sent" in res
            mock_dsm.assert_called_once_with("WhatsApp", "Mom", p, caption="Look at this")
    finally:
        p.unlink(missing_ok=True)


def test_send_whatsapp_media_not_found():
    res = _send_whatsapp("Mom", "Look at this", file_path="nonexistent_xyz_999.png")
    assert "Could not find file" in res


def test_send_message_missing_receiver():
    res = send_message({"message_text": "Hello"})
    assert "Please specify a recipient" in res


def test_send_message_missing_content():
    res = send_message({"receiver": "Alice"})
    assert "Please specify a message text or a file to send" in res


def test_send_message_with_file_integration():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        p = Path(tf.name)
    try:
        with patch("actions.send_message._desktop_send_media") as mock_dsm:
            mock_dsm.return_value = f"Successfully sent {p.name} to Alice via WhatsApp."
            res = send_message({
                "receiver": "Alice",
                "file_path": str(p),
                "message_text": "Here is the picture",
                "platform": "whatsapp"
            })
            assert "Successfully sent" in res
            mock_dsm.assert_called_once_with("WhatsApp", "Alice", p, caption="Here is the picture")
    finally:
        p.unlink(missing_ok=True)


def test_tool_declarations_send_message():
    names = [t["name"] for t in TOOL_DECLARATIONS]
    assert "send_message" in names
    sm_tool = next(t for t in TOOL_DECLARATIONS if t["name"] == "send_message")
    props = sm_tool["parameters"]["properties"]
    assert "receiver" in props
    assert "message_text" in props
    assert "file_path" in props
    assert "receiver" in sm_tool["parameters"]["required"]
