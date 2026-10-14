"""Search public image sources and download validated image files."""

from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}
MAX_FILE_SIZE = 15 * 1024 * 1024
MIN_DIMENSION = 200
REQUEST_TIMEOUT = (8, 20)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def _is_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
            return False
        host = parsed.hostname.rstrip(".")
        if host.lower() in {"localhost", "localhost.localdomain"}:
            return False
        try:
            addresses = {ipaddress.ip_address(host)}
        except ValueError:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            }
        return all(not address.is_private and not address.is_loopback and not address.is_link_local
                   and not address.is_reserved for address in addresses)
    except (OSError, ValueError):
        return False


def _request(url: str, timeout: tuple[float, float] | None = None, cancel_event=None) -> requests.Response:
    if not _is_public_url(url):
        raise ValueError("Only public HTTP(S) URLs are allowed.")
    if cancel_event and cancel_event.is_set():
        raise TimeoutError("image provider cancelled")
    chosen_timeout = timeout or REQUEST_TIMEOUT
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=chosen_timeout)
        response.raise_for_status()
        return response
    except requests.Timeout:
        raise TimeoutError("image provider read timeout") from None
    except requests.RequestException as exc:
        raise TimeoutError(str(exc)) from exc


def _unique_urls(urls: list[str]) -> list[str]:
    result = []
    seen = set()
    for url in urls:
        url = html.unescape(url).strip().strip('"\'')
        if not _is_public_url(url) or url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def _google_images(query: str) -> list[str]:
    response = _request(f"https://www.google.com/search?tbm=isch&q={quote_plus(query)}")
    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    for image in soup.find_all("img"):
        for key in ("data-src", "data-iurl", "src"):
            value = image.get(key)
            if value and value.startswith(("http://", "https://")):
                urls.append(value)
    return _unique_urls(urls)


def _bing_images(query: str) -> list[str]:
    response = _request(f"https://www.bing.com/images/search?q={quote_plus(query)}")
    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    for node in soup.select("a.iusc"):
        try:
            metadata = json.loads(html.unescape(node.get("m", "{}")))
            urls.append(metadata.get("murl", ""))
        except (json.JSONDecodeError, TypeError):
            continue
    return _unique_urls(urls)


def _duckduckgo_images(query: str) -> list[str]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return _unique_urls([item.get("image", "") for item in ddgs.images(query, max_results=30)])


def _webpage_images(url: str) -> list[str]:
    if not url:
        raise ValueError("A webpage URL is required for source='webpage'.")
    response = _request(url)
    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    for image in soup.find_all("img"):
        for key in ("src", "data-src", "data-original", "data-lazy-src"):
            value = image.get(key)
            if value:
                urls.append(urljoin(response.url, value))
        srcset = image.get("srcset", "")
        urls.extend(urljoin(response.url, part.strip().split(" ")[0]) for part in srcset.split(",") if part.strip())
    return _unique_urls(urls)


def _search_candidates(query: str, source: str, url: str | None) -> tuple[list[str], str]:
    source = (source or "auto").lower().strip()
    providers = {"google": _google_images, "bing": _bing_images, "duckduckgo": _duckduckgo_images}
    if source == "webpage" or (source == "auto" and url):
        order = ["webpage", "google", "bing", "duckduckgo"]
    elif source in providers:
        order = [source] + [name for name in providers if name != source]
    else:
        order = ["google", "bing", "duckduckgo"]
    errors = []
    for provider in order:
        try:
            candidates = _webpage_images(url or "") if provider == "webpage" else providers[provider](query)
            if candidates:
                return candidates, provider
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
    raise RuntimeError("No image sources returned results. " + "; ".join(errors[-2:]))


def _download_and_validate(url: str) -> tuple[str, bytes, str]:
    response = _request(url)
    declared_size = int(response.headers.get("Content-Length", "0") or 0)
    if declared_size > MAX_FILE_SIZE:
        raise ValueError("file exceeds the 15 MB limit")
    data = bytearray()
    for chunk in response.iter_content(64 * 1024):
        data.extend(chunk)
        if len(data) > MAX_FILE_SIZE:
            raise ValueError("file exceeds the 15 MB limit")
    try:
        from PIL import Image
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            width, height = image.size
    except Exception as exc:
        raise ValueError(f"invalid image: {exc}") from exc
    if image_format not in ALLOWED_FORMATS:
        raise ValueError("unsupported image format")
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise ValueError("image is smaller than 200x200 pixels")
    return hashlib.sha256(data).hexdigest(), bytes(data), ALLOWED_FORMATS[image_format]


def _safe_stem(query: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", query).strip("_").lower()
    return (stem or "jarvis_image")[:80]


def _next_path(destination: Path, stem: str, extension: str) -> Path:
    candidate = destination / f"{stem}{extension}"
    index = 2
    while candidate.exists():
        candidate = destination / f"{stem}_{index}{extension}"
        index += 1
    return candidate


def image_downloader(parameters: dict, player=None) -> str:
    """Search and download public images; intended to run in an executor."""
    query = str(parameters.get("query", "")).strip()
    if not query:
        return "Please specify what images to search for."
    try:
        count = max(1, min(20, int(parameters.get("count", 5))))
    except (TypeError, ValueError):
        count = 5
    destination_value = str(parameters.get("destination") or "Pictures/JARVIS Downloads").strip()
    destination = Path(destination_value).expanduser()
    if not destination.is_absolute():
        destination = Path.home() / destination
    try:
        destination.mkdir(parents=True, exist_ok=True)
        candidates, used_source = _search_candidates(query, str(parameters.get("source", "auto")), parameters.get("url"))
    except Exception as exc:
        return f"Image search failed: {exc} I can use normal public image search when a browser page is unavailable."

    downloaded = []
    failed = 0
    hashes = set()
    with ThreadPoolExecutor(max_workers=min(count, 6)) as pool:
        futures = [pool.submit(_download_and_validate, item) for item in candidates[:max(count * 3, count)]]
        for future in as_completed(futures):
            try:
                digest, data, extension = future.result()
                if digest in hashes or len(downloaded) >= count:
                    continue
                hashes.add(digest)
                target = _next_path(destination, _safe_stem(query), extension)
                target.write_bytes(data)
                if target.stat().st_size > 0:
                    downloaded.append({"name": target.name, "path": str(target)})
            except Exception:
                failed += 1

    if parameters.get("open_folder"):
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(destination))
            else:
                import webbrowser
                webbrowser.open(destination.as_uri())
        except Exception:
            pass
    names = ", ".join(item["name"] for item in downloaded) or "none"
    warning = " Images may be copyrighted; follow each source's license."
    return (f"Downloaded {len(downloaded)}/{count} image(s) via {used_source} to {destination}. "
            f"Files: {names}. Failed or skipped: {failed}." + warning)