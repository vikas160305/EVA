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
    _download_web_file,
    _download_direct_file,
    _resolve_web_file_url,
    media_downloader,
)
from main import TOOL_DECLARATIONS


def test_detect_category():
    assert _detect_category("download song Believer by Imagine Dragons") == "song"
    assert _detect_category("download faded mp3") == "song"
    assert _detect_category("save iron man wallpaper 4k from google") == "image"
    assert _detect_category("download photos of cute cats") == "image"
    assert _detect_category("download python tutorial video") == "video"
    assert _detect_category("download python cheatsheet pdf") == "document"
    assert _detect_category("download titanic dataset csv") == "dataset"
    assert _detect_category("download 7zip windows installer") == "installer"
    assert _detect_category("download quicksort python code") == "code"
    assert _detect_category("download sample test file") == "file"

    # Parameter override
    assert _detect_category("some random query", category_param="song") == "song"
    assert _detect_category("some random query", category_param="image") == "image"
    assert _detect_category("some random query", category_param="video") == "video"
    assert _detect_category("some random query", category_param="document") == "document"
    assert _detect_category("some random query", category_param="dataset") == "dataset"
    assert _detect_category("some random query", category_param="installer") == "installer"
    assert _detect_category("some random query", category_param="code") == "code"
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

    doc_dir = _get_media_dir("document")
    assert isinstance(doc_dir, Path)
    assert doc_dir.exists()
    assert "EVA Documents" in str(doc_dir)

    data_dir = _get_media_dir("dataset")
    assert isinstance(data_dir, Path)
    assert data_dir.exists()
    assert "EVA Datasets" in str(data_dir)

    inst_dir = _get_media_dir("installer")
    assert isinstance(inst_dir, Path)
    assert inst_dir.exists()
    assert "EVA Installers" in str(inst_dir)

    code_dir = _get_media_dir("code")
    assert isinstance(code_dir, Path)
    assert code_dir.exists()
    assert "EVA Code" in str(code_dir)

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
        mock_response.url = "https://example.com/cheatsheet.pdf"
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.iter_content.return_value = [b"mock pdf bytes"]

        with patch("requests.get", return_value=mock_response):
            ok, msg, p = _download_direct_file("https://example.com/cheatsheet.pdf", dest)
            assert ok is True
            assert "cheatsheet.pdf" in msg
            assert p.exists()


def test_resolve_web_file_url_curated():
    url, name = _resolve_web_file_url("download titanic dataset", "dataset")
    assert url is not None
    assert "titanic.csv" in url
    assert name == "titanic.csv"

    url_pdf, name_pdf = _resolve_web_file_url("download python cheatsheet pdf", "document")
    assert url_pdf is not None
    assert "python-cheatsheet.pdf" in url_pdf


def test_download_web_file_dataset_mocked():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/csv",
            "Content-Disposition": 'attachment; filename="titanic.csv"'
        }
        mock_response.iter_content.return_value = [b"PassengerId,Survived\n1,0\n2,1"]

        with patch("requests.get", return_value=mock_response):
            ok, msg, p = _download_web_file("titanic dataset", dest, category="dataset")
            assert ok is True
            assert "titanic.csv" in msg
            assert p.exists()
            assert p.suffix == ".csv"


def test_media_downloader_integration_dataset():
    with patch("actions.media_downloader._download_web_file") as mock_dl, \
         patch("actions.media_downloader._reveal_in_explorer") as mock_reveal:
        fake_path = Path("fake_dataset.csv")
        mock_dl.return_value = (True, "Downloaded 'fake_dataset.csv' (60.3 KB) to EVA Datasets.", fake_path)

        res = media_downloader({
            "query": "download titanic dataset csv from google",
            "open_in_explorer": True
        })
        assert "Downloaded 'fake_dataset.csv'" in res
        assert "File Explorer" in res
        assert mock_reveal.called


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

