import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from actions import file_controller as fc


@pytest.fixture
def safe_root():
    root = Path.home() / f".mark_l_file_controller_test_{uuid4().hex}"
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resolve_blocks_traversal_and_outside_absolute_path():
    with pytest.raises(fc.UnsafePathError):
        fc.resolve_safe_path("home/../outside")
    with pytest.raises(fc.UnsafePathError):
        fc.resolve_safe_path(str(Path.home().parent))


def test_create_file_preserves_exact_content_and_blocks_overwrite(safe_root):
    content = "line 1\nline 2\r\n终"
    nested = safe_root / "nested"
    first = fc.create_file(str(nested), "result.txt", content)

    assert first.startswith("File created:")
    target = nested / "result.txt"
    assert target.read_bytes() == content.encode("utf-8")
    assert "Already exists" in fc.create_file(str(nested), "result.txt", "changed")
    assert target.read_bytes() == content.encode("utf-8")
    assert "File created:" in fc.create_file(str(safe_root / "nested"), "result.txt", "changed", overwrite=True)
    assert target.read_bytes() == b"changed"


def test_create_folder_rejects_invalid_name(safe_root):
    result = fc.create_folder(str(safe_root), "bad/name")
    assert "Invalid file or folder name" in result


def test_delete_requires_confirmation(safe_root):
    target = safe_root / "remove.txt"
    target.write_text("x", encoding="utf-8")

    result = fc.delete_file(str(safe_root), target.name)

    assert "confirmed=True" in result
    assert target.exists()


def test_delete_protects_home_and_shortcut_roots():
    assert "Protected directory" in fc.delete_file("home", confirmed=True)
    assert "Protected directory" in fc.delete_file("desktop", confirmed=True)


def test_create_file_invalidates_search_cache_for_newly_created_file(safe_root):
    # warm the cache with a file search that should otherwise miss the future file
    first = fc.find_files(name="freshly_created", path=str(safe_root), max_results=5)
    assert "No matching freshly_created found." in first

    create_result = fc.create_file(str(safe_root), "freshly_created.txt", "hello world", overwrite=False)
    assert "File created:" in create_result

    # A stale result cache would keep this request from finding the new file.
    found = fc.find_files(name="freshly_created", path=str(safe_root), max_results=5)
    assert "freshly_created.txt" in found


def test_open_safe_file_uses_default_application(monkeypatch, safe_root):
    target = safe_root / "open.txt"
    target.write_text("open", encoding="utf-8")
    calls = []

    if fc._OS == "Windows":
        monkeypatch.setattr(fc.os, "startfile", lambda path: calls.append(path))
    else:
        monkeypatch.setattr(fc.subprocess, "Popen", lambda args, **kwargs: calls.append(args))

    result = fc.open_path(str(safe_root), target.name)

    assert result == f"Opened: {target}"
    assert calls
