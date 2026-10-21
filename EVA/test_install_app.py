import pytest
from unittest.mock import patch, MagicMock
from actions.install_app import (
    _clean_app_name,
    _parse_winget_table,
    _find_best_match,
    install_app,
)
from actions.open_app import _normalize, open_app
from main import TOOL_DECLARATIONS


def test_clean_app_name():
    assert _clean_app_name("download VLC from Microsoft Store") == "VLC"
    assert _clean_app_name("install WhatsApp from store") == "WhatsApp"
    assert _clean_app_name("get Spotify app") == "Spotify"
    assert _clean_app_name("microsoft store for telegram") == "telegram"
    assert _clean_app_name("download PowerToys from windows store") == "PowerToys"
    assert _clean_app_name("install discord") == "discord"
    assert _clean_app_name("  VLC  ") == "VLC"
    assert _clean_app_name("") == ""


def test_parse_winget_table():
    sample_output = """
Name     Id           Version Match Source
-------------------------------------------
WhatsApp 9NKSQGP7F2NH Unknown       msstore
WhatsApp Beta 9NBDXK71NK08 Unknown  msstore
"""
    parsed = _parse_winget_table(sample_output)
    assert len(parsed) >= 1
    assert parsed[0]["name"] == "WhatsApp"
    assert parsed[0]["id"] == "9NKSQGP7F2NH"


def test_find_best_match():
    items = [
        {"name": "WhatsApp Beta", "id": "9NBDXK71NK08"},
        {"name": "WhatsApp", "id": "9NKSQGP7F2NH"},
    ]
    best = _find_best_match("WhatsApp", items)
    assert best is not None
    assert best["name"] == "WhatsApp"
    assert best["id"] == "9NKSQGP7F2NH"


def test_install_app_empty():
    res = install_app(parameters={})
    assert "Please specify" in res


def test_install_app_already_installed():
    with patch("actions.install_app._check_already_installed_winget", return_value=(True, "WhatsApp")):
        res = install_app(parameters={"app_name": "WhatsApp", "launch_after": False})
        assert "already installed" in res.lower()
        assert "WhatsApp" in res


def test_install_app_winget_success():
    with patch("actions.install_app._check_already_installed_winget", return_value=(False, "")), \
         patch("actions.install_app._search_msstore_winget", return_value=[{"name": "Spotify", "id": "9NCBCSZSJRSB"}]), \
         patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Successfully installed Spotify"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = install_app(parameters={"app_name": "Spotify", "launch_after": False})
        assert "Successfully installed" in res
        assert "Spotify" in res


def test_install_app_fallback_to_store_ui():
    with patch("actions.install_app._check_already_installed_winget", return_value=(False, "")), \
         patch("actions.install_app._search_msstore_winget", return_value=[{"name": "Spotify", "id": "9NCBCSZSJRSB"}]), \
         patch("actions.install_app._open_store_ui", return_value=True) as mock_open_ui, \
         patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: Requires Microsoft account"
        mock_run.return_value = mock_proc

        res = install_app(parameters={"app_name": "Spotify", "launch_after": False})
        assert "Microsoft Store" in res
        assert mock_open_ui.called


def test_open_app_store_normalization():
    assert _normalize("microsoft store") == "ms-windows-store:"
    assert _normalize("store") == "ms-windows-store:"
    assert _normalize("microsoft store whatsapp") == "ms-windows-store://search/?query=whatsapp"
    assert _normalize("store vlc") == "ms-windows-store://search/?query=vlc"


def test_open_app_redirection_to_install():
    with patch("actions.install_app.install_app", return_value="Redirected to install WhatsApp") as mock_install:
        res = open_app(parameters={"app_name": "install WhatsApp from Microsoft Store"})
        assert "Redirected to install WhatsApp" in res
        assert mock_install.called


def test_tool_declarations_has_install_app():
    names = [t["name"] for t in TOOL_DECLARATIONS]
    assert "install_app" in names
    tool = next(t for t in TOOL_DECLARATIONS if t["name"] == "install_app")
    assert "app_name" in tool["parameters"]["properties"]
    assert "app_name" in tool["parameters"]["required"]


def test_popular_apps_catalog():
    from actions.install_app import _POPULAR_APPS
    assert "vlc" in _POPULAR_APPS
    assert _POPULAR_APPS["vlc"]["id"] == "VideoLAN.VLC"
    assert "whatsapp" in _POPULAR_APPS
    assert "chrome" in _POPULAR_APPS
    assert "spotify" in _POPULAR_APPS


def test_fast_check_installed_local():
    from actions.install_app import _fast_check_installed_local
    # Non-existent app should return False quickly
    is_inst, name = _fast_check_installed_local("definitely_not_a_real_app_xyz_123")
    assert is_inst is False
    assert name == ""


def test_silent_flags_in_winget_command():
    from actions.install_app import install_app
    with patch("actions.install_app._check_already_installed_winget", return_value=(False, "")), \
         patch("actions.install_app._stream_winget_install") as mock_stream:
        mock_stream.return_value = (0, "Successfully installed VLC media player")
        res = install_app(parameters={"app_name": "VLC", "launch_after": False})
        assert "Successfully installed" in res
        assert mock_stream.called
        cmd = mock_stream.call_args[0][0]
        assert "--silent" in cmd
        assert "--accept-package-agreements" in cmd
        assert "--accept-source-agreements" in cmd
        assert "--disable-interactivity" in cmd
        assert "--force" in cmd

