import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from actions.media_downloader import (
    _detect_category,
    _clean_query,
    _get_media_dir,
    _reveal_in_explorer,
    _download_song,
    _download_video,
    _download_direct_file,
    media_downloader,
)
from main import TOOL_DECLARATIONS


def test_detect_category():
    assert _detect_category("download song Believer by Imagine Dragons") == "song"
    assert _detect_category("download faded mp3") == "song"
    assert _detect_category("save iron man wallpaper 4k from google") == "image"
    assert _detect_category("download photos of cute cats") == "image"
    assert _detect_category("download python tutorial video") == "video"
    assert _detect_category("download python cheatsheet pdf") == "file"
    # Parameter override
    assert _detect_category("some random query", category_param="song") == "song"
    assert _detect_category("some random query", category_param="image") == "image"
    assert _detect_category("some random query", category_param="video") == "video"
    assert _detect_category("some random query", category_param="file") == "file"


def test_clean_query():
    assert _clean_query("download song Believer by Imagine Dragons from google") == "Believer by Imagine Dragons"
    assert _clean_query("download faded song from chrome") == "faded"
    assert _clean_query("download iron man wallpaper 4k from google") == "iron man wallpaper 4k"
    assert _clean_query("download python cheatsheet pdf") == "python cheatsheet pdf"
    assert _clean_query("save pictures of cute cats from web and open in file explorer") == "cute cats"


def test_get_media_dir():
    music_dir = _get_media_dir("song")
    assert isinstance(music_dir, Path)
    assert music_dir.exists()
    assert "EVA Songs" in str(music_dir)

    img_dir = _get_media_dir("image")
    assert isinstance(img_dir, Path)
    assert img_dir.exists()
    assert "EVA Images" in str(img_dir)

    vid_dir = _get_media_dir("video")
    assert isinstance(vid_dir, Path)
    assert vid_dir.exists()
    assert "EVA Videos" in str(vid_dir)

    dl_dir = _get_media_dir("file")
    assert isinstance(dl_dir, Path)
    assert dl_dir.exists()
    assert "EVA Downloads" in str(dl_dir)


def test_reveal_in_explorer():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        p = Path(tf.name)
    try:
        with patch("subprocess.Popen") as mock_popen:
            res = _reveal_in_explorer(p)
            assert res is True
            assert mock_popen.called
    finally:
        try:
            p.unlink()
        except Exception:
            pass


def test_download_song_mocked():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td)
        # Create a mock mp3 in the destination folder
        mock_mp3 = dest / "Imagine Dragons - Believer.mp3"
        mock_mp3.write_bytes(b"mock mp3 data")

        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {"title": "Imagine Dragons - Believer"}

        with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
            ok, msg, p = _download_song("Believer Imagine Dragons", dest)
            assert ok is True
            assert "Believer" in msg
            assert p == mock_mp3


def test_download_video_mocked():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td)
        mock_mp4 = dest / "Python Tutorial.mp4"
        mock_mp4.write_bytes(b"mock mp4 data")

        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {"title": "Python Tutorial"}

        with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
            ok, msg, p = _download_video("Python Tutorial", dest)
            assert ok is True
            assert "Python Tutorial" in msg
            assert p == mock_mp4


def test_download_direct_file_mocked():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"mock pdf bytes"]

        with patch("requests.get", return_value=mock_response):
            ok, msg, p = _download_direct_file("https://example.com/cheatsheet.pdf", dest)
            assert ok is True
            assert "cheatsheet.pdf" in msg
            assert p.exists()


def test_media_downloader_integration_song():
    with patch("actions.media_downloader._download_song") as mock_dl_song, \
         patch("actions.media_downloader._reveal_in_explorer") as mock_reveal:
        fake_path = Path("fake_song.mp3")
        mock_dl_song.return_value = (True, "Downloaded 'Believer' as MP3.", fake_path)

        res = media_downloader({
            "query": "download song Believer by Imagine Dragons from google",
            "open_in_explorer": True
        })
        assert "Downloaded 'Believer'" in res
        assert "File Explorer" in res
        assert mock_reveal.called


def test_tool_declarations_media_downloader():
    names = [t["name"] for t in TOOL_DECLARATIONS]
    assert "media_downloader" in names
    md_tool = next(t for t in TOOL_DECLARATIONS if t["name"] == "media_downloader")
    assert "query" in md_tool["parameters"]["required"]
    assert "category" in md_tool["parameters"]["properties"]
    assert "source" in md_tool["parameters"]["properties"]
    assert "open_in_explorer" in md_tool["parameters"]["properties"]
