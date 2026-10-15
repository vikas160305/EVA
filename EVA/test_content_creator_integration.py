"""Integration tests for document and content creation."""
import pytest
from pathlib import Path
from actions.content_creator import content_creator


def test_content_creator_empty_request():
    result = content_creator({})
    assert "Please say what you want to create" in result


def test_content_creator_unsupported_format():
    result = content_creator({"request": "Hello world", "format": "xyz_unsupported"})
    assert "Supported creation formats" in result


def test_content_creator_code_generation(tmp_path: Path):
    result = content_creator({
        "request": "Write a python function to add two numbers",
        "format": "code",
        "language": "python",
        "destination": str(tmp_path)
    })
    assert "Created" in result or "PY file" in result
    py_files = list(tmp_path.glob("*.py"))
    assert len(py_files) >= 1
    content = py_files[0].read_text(encoding="utf-8")
    assert "def " in content


def test_content_creator_txt_generation(tmp_path: Path):
    result = content_creator({
        "request": "A short summary of artificial intelligence",
        "format": "txt",
        "destination": str(tmp_path)
    })
    assert "Created TXT file" in result
    txt_files = list(tmp_path.glob("*.txt"))
    assert len(txt_files) >= 1
    assert txt_files[0].stat().st_size > 0
