from io import BytesIO
from pathlib import Path

from PIL import Image

from actions import image_downloader as downloader


def _image_bytes(color="red"):
    stream = BytesIO()
    Image.new("RGB", (240, 240), color).save(stream, format="PNG")
    return stream.getvalue()


def test_download_creates_destination_and_validates_image(monkeypatch, tmp_path):
    payload = _image_bytes()
    monkeypatch.setattr(downloader, "_search_candidates", lambda *args: (["https://example.com/a.png"], "google"))
    monkeypatch.setattr(downloader, "_download_and_validate", lambda url: ("hash-a", payload, ".png"))
    destination = tmp_path / "missing" / "images"

    result = downloader.image_downloader({"query": "AI images", "count": 1, "destination": str(destination)})

    saved = destination / "ai_images.png"
    assert saved.exists()
    assert saved.read_bytes() == payload
    with Image.open(saved) as image:
        image.verify()
    assert "Downloaded 1/1" in result
    assert "Failed or skipped: 0" in result


def test_duplicate_name_gets_numbered_suffix(monkeypatch, tmp_path):
    payload = _image_bytes("blue")
    monkeypatch.setattr(downloader, "_search_candidates", lambda *args: (["https://example.com/a.png"], "bing"))
    monkeypatch.setattr(downloader, "_download_and_validate", lambda url: ("hash-b", payload, ".png"))
    args = {"query": "sunset", "count": 1, "destination": str(tmp_path)}

    downloader.image_downloader(args)
    result = downloader.image_downloader(args)

    assert (tmp_path / "sunset.png").exists()
    assert (tmp_path / "sunset_2.png").exists()
    assert "sunset_2.png" in result


def test_invalid_webpage_url_is_reported(monkeypatch, tmp_path):
    def reject(url):
        raise ValueError("Only public HTTP(S) URLs are allowed.")

    monkeypatch.setattr(downloader, "_webpage_images", reject)
    monkeypatch.setattr(downloader, "_google_images", reject)
    monkeypatch.setattr(downloader, "_bing_images", reject)
    monkeypatch.setattr(downloader, "_duckduckgo_images", reject)
    result = downloader.image_downloader({
        "query": "mountains", "source": "webpage", "url": "http://127.0.0.1/private",
        "destination": str(tmp_path),
    })

    assert "Image search failed" in result
    assert "public HTTP(S)" in result