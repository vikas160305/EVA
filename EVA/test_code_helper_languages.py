import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from actions.code_helper import (
    _get_desktop_dir,
    _infer_slug_from_description,
    _resolve_save_path,
    _wants_vscode,
    _run_file,
    _build,
    _write_action,
    code_helper,
)
from actions.content_creator import content_creator
from main import TOOL_DECLARATIONS


def test_get_desktop_dir():
    desktop = _get_desktop_dir()
    assert isinstance(desktop, Path)
    assert desktop.exists()
    assert "Desktop" in str(desktop)


def test_infer_slug_from_description():
    assert _infer_slug_from_description("create a file in java language of code factorial number and run it vls code") == "factorial"
    assert _infer_slug_from_description("write a python fibonacci script") == "fibonacci"
    assert _infer_slug_from_description("build a calculator in c++") == "calculator"
    assert _infer_slug_from_description("todo list application in javascript") in ("todo", "todolist")
    assert _infer_slug_from_description("", fallback="main") == "main"


def test_resolve_save_path_all_languages():
    desktop = _get_desktop_dir()

    # Java: Extracts public class name
    java_code = "public class FactorialNumber {\n    public static void main(String[] args) {}\n}"
    p_java = _resolve_save_path("", "java", code=java_code, description="factorial")
    assert p_java == desktop / "FactorialNumber.java"

    # Python
    p_py = _resolve_save_path("", "python", description="factorial number")
    assert p_py == desktop / "factorial.py"

    # JavaScript
    p_js = _resolve_save_path("", "javascript", description="factorial number")
    assert p_js == desktop / "factorial.js"

    # C
    p_c = _resolve_save_path("", "c", description="factorial number")
    assert p_c == desktop / "factorial.c"

    # C++
    p_cpp = _resolve_save_path("", "cpp", description="factorial number")
    assert p_cpp == desktop / "factorial.cpp"

    # TypeScript
    p_ts = _resolve_save_path("", "typescript", description="calculator")
    assert p_ts == desktop / "calculator.ts"

    # Go
    p_go = _resolve_save_path("", "go", description="prime check")
    assert p_go == desktop / "prime.go"

    # Rust
    p_rs = _resolve_save_path("", "rust", description="sorting algorithm")
    assert p_rs == desktop / "sorting.rs"

    # C#
    p_cs = _resolve_save_path("", "csharp", description="factorial")
    assert p_cs == desktop / "factorial.cs"

    # HTML
    p_html = _resolve_save_path("", "html", description="calculator")
    assert p_html == desktop / "calculator.html"


def test_wants_vscode():
    assert _wants_vscode("create a file in java language of code factorial number and run it vls code") is True
    assert _wants_vscode("run it in vs code") is True
    assert _wants_vscode("open in vscode") is True
    assert _wants_vscode("view in visual studio code") is True
    assert _wants_vscode("show in editor") is True
    assert _wants_vscode("just write python code", params={"open_in_editor": True}) is True
    assert _wants_vscode("just write python code", params={"open_in_editor": False}) is False


def test_run_file_python():
    with tempfile.TemporaryDirectory() as td:
        py_file = Path(td) / "factorial.py"
        py_file.write_text("print('Result is 120')", encoding="utf-8")
        out = _run_file(py_file)
        assert "Result is 120" in out


def test_run_file_missing_compiler_message():
    with tempfile.TemporaryDirectory() as td:
        with patch("shutil.which", return_value=None):
            # Java
            java_file = Path(td) / "Factorial.java"
            java_file.write_text("public class Factorial {}", encoding="utf-8")
            res_java = _run_file(java_file)
            assert "Java runtime (JDK) is not installed" in res_java

            # C
            c_file = Path(td) / "factorial.c"
            c_file.write_text("int main() { return 0; }", encoding="utf-8")
            res_c = _run_file(c_file)
            assert "C compiler" in res_c

            # Go
            go_file = Path(td) / "main.go"
            go_file.write_text("package main\nfunc main() {}", encoding="utf-8")
            res_go = _run_file(go_file)
            assert "Go compiler is not installed" in res_go


def test_code_helper_write_and_open_vscode():
    with patch("actions.code_helper._write") as mock_write, \
         patch("actions.code_helper._open_vscode") as mock_open:
        mock_file = _get_desktop_dir() / "Factorial.java"
        mock_write.return_value = ("public class Factorial {}", mock_file)
        mock_open.return_value = True

        res = code_helper({
            "action": "write",
            "language": "java",
            "description": "create a file in java language of code factorial number and run it vls code"
        })
        assert "Factorial.java" in res
        assert "Visual Studio Code" in res
        assert mock_open.called


def test_code_helper_build_missing_runtime_handles_cleanly():
    with patch("actions.code_helper._write") as mock_write, \
         patch("actions.code_helper._open_vscode") as mock_open, \
         patch("actions.code_helper._run_file") as mock_run:
        mock_file = _get_desktop_dir() / "Factorial.java"
        mock_write.return_value = ("public class Factorial {}", mock_file)
        mock_open.return_value = True
        mock_run.return_value = "Java runtime (JDK) is not installed in system PATH. Cannot execute Java in terminal. Please run it inside VS Code."

        res = code_helper({
            "action": "build",
            "language": "java",
            "description": "create a file in java language of code factorial number and run it in vs code"
        })
        assert "Created Factorial.java" in res
        assert "VS Code" in res
        assert "Java runtime (JDK) is not installed" in res


def test_tool_declarations_code_helper():
    ch_tool = next(t for t in TOOL_DECLARATIONS if t["name"] == "code_helper")
    assert "open_in_editor" in ch_tool["parameters"]["properties"]
    assert "Visual Studio Code" in ch_tool["description"]
