"""Universal media and file downloader for EVA.

Downloads songs (MP3), images, videos (MP4), and documents/files from Google,
YouTube, Chrome, and the web, saving them directly into user-friendly File Explorer
directories and automatically revealing the downloaded file in File Explorer.
"""

from __future__ import annotations

import os
import re
import sys
import time
import shutil
import platform
import subprocess
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from typing import Optional, List, Dict, Tuple

import requests

_SYSTEM = platform.system()

_CNW: dict = (
    {"creationflags": subprocess.CREATE_NO_WINDOW}
    if _SYSTEM == "Windows" else {}
)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def _get_media_dir(category: str) -> Path:
    """Resolve active directory taking Windows OneDrive redirection into account."""
    cat = category.lower().strip()
    userprofile = os.environ.get("USERPROFILE")
    
    if cat in ("music", "song", "audio"):
        folder_name = "Music"
        sub_folder = "EVA Songs"
    elif cat in ("image", "images", "photo", "photos", "picture", "pictures", "wallpaper"):
        folder_name = "Pictures"
        sub_folder = "EVA Images"
    elif cat in ("video", "videos", "movie", "clip"):
        folder_name = "Videos"
        sub_folder = "EVA Videos"
    else:
        folder_name = "Downloads"
        sub_folder = "EVA Downloads"

    candidates = []
    if userprofile:
        candidates.append(Path(userprofile) / "OneDrive" / folder_name)
    candidates.append(Path.home() / folder_name)

    base = None
    for c in candidates:
        if c.exists():
            base = c
            break

    if not base:
        base = Path.home() / "Downloads"
        if not base.exists():
            base = Path.home()

    dest = base / sub_folder
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _reveal_in_explorer(target_path: Path) -> bool:
    """Open File Explorer and highlight/select the downloaded file."""
    try:
        if _SYSTEM == "Windows":
            if target_path.is_file():
                subprocess.Popen(
                    f'explorer.exe /select,"{target_path}"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **_CNW
                )
            else:
                if hasattr(os, "startfile"):
                    os.startfile(str(target_path))
                else:
                    subprocess.Popen(
                        f'explorer.exe "{target_path}"',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        **_CNW
                    )
            return True
        elif _SYSTEM == "Darwin":
            subprocess.Popen(["open", "-R", str(target_path)])
            return True
        elif _SYSTEM == "Linux":
            subprocess.Popen(["xdg-open", str(target_path.parent)])
            return True
    except Exception as e:
        print(f"[media_downloader] File Explorer reveal failed: {e}")
    return False


def _detect_category(query: str, category_param: str = "auto") -> str:
    """Infer media category from query and parameter."""
    if category_param and category_param.lower() != "auto":
        cp = category_param.lower().strip()
        if cp in ("song", "music", "audio", "mp3", "track"):
            return "song"
        if cp in ("image", "photo", "picture", "wallpaper", "images"):
            return "image"
        if cp in ("video", "clip", "movie", "mp4"):
            return "video"
        if cp in ("file", "document", "pdf", "doc", "zip"):
            return "file"

    q = query.lower()
    if any(w in q for w in ("song", "music", "audio", "mp3", "track", "soundtrack", "tune", "singing", "album")):
        return "song"
    if any(w in q for w in ("image", "images", "photo", "photos", "wallpaper", "picture", "pictures", "drawing", "logo")):
        return "image"
    if any(w in q for w in ("video", "videos", "clip", "movie", "mp4", "reel")):
        return "video"
    if any(w in q for w in ("pdf", "document", "cheatsheet", "doc", "docx", "zip", "rar", "csv", "xlsx")):
        return "file"
    return "image"


def _clean_query(raw: str) -> str:
    """Extract clean search terms from spoken query."""
    text = raw.strip()

    # Iteratively strip known prefixes and suffixes until stable
    for _ in range(4):
        prev = text
        # Strip leading command + category words (e.g. "download the image of", "download a picture of")
        text = re.sub(
            r"^(?:download|save|fetch|get|grab)\s+(?:an?\s+|the\s+)?(?:images?|songs?|videos?|files?|photos?|pictures?|music|audio|documents?|pdfs?)?\s*(?:of|for)?\s*(?:an?\s+|the\s+)?",
            "", text, flags=re.IGNORECASE
        )
        # Strip trailing destination phrases (e.g. "and save it in file explorer", "in file explorer", "and open in folder")
        text = re.sub(
            r"\s+(?:and\s+(?:save|open|show|view)\s+(?:it\s+)?(?:in\s+)?|(?:in|into|to)\s+)(?:file\s+explorer|folder|explorer)$",
            "", text, flags=re.IGNORECASE
        )
        # Strip trailing source phrases (e.g. "from chrome", "from google", "from web")
        text = re.sub(
            r"\s+(?:from|in|on|via)\s+(?:chrome|google|youtube|(?:the\s+)?web|(?:the\s+)?internet)$",
            "", text, flags=re.IGNORECASE
        )
        # Strip trailing media type words (e.g. "faded song" -> "faded")
        text = re.sub(
            r"\s+(?:songs?|music|audio|mp3|tracks?|images?|videos?|photos?|pictures?|wallpapers?)$",
            "", text, flags=re.IGNORECASE
        )
        # Strip leading articles
        text = re.sub(r"^(?:an?\s+|the\s+)", "", text, flags=re.IGNORECASE)
        text = text.strip("\"' ")
        if text == prev:
            break

    return text or raw.strip()


def _get_active_browser_url() -> Optional[str]:
    """Retrieve active browser tab URL via browser_control if active."""
    try:
        from actions.browser_control import browser_control
        res = browser_control(parameters={"action": "get_url"})
        if res and res.startswith("http"):
            return res.strip()
    except Exception:
        pass
    return None


def _download_song(
    query_or_url: str,
    dest_folder: Path,
    player=None
) -> Tuple[bool, str, Optional[Path]]:
    """Download audio/song and convert to high quality MP3 via yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        return False, "yt-dlp is not installed. Please run 'pip install yt-dlp'.", None

    is_direct_url = query_or_url.startswith("http://") or query_or_url.startswith("https://")
    target = query_or_url if is_direct_url else f"ytsearch1:{query_or_url}"

    log_msg = f"Searching and downloading song '{query_or_url}'..."
    print(f"[media_downloader] {log_msg}")
    if player:
        player.write_log(f"SYS: {log_msg}")

    out_template = str(dest_folder / "%(title).90B.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "noplaylist": True,
        "max_filesize": 50 * 1024 * 1024,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=True)
            entries = info.get("entries")
            entry = entries[0] if entries else info
            title = entry.get("title", "song")
            clean_title = title.encode("ascii", errors="replace").decode()

        # Find the newly created MP3
        mp3s = sorted(dest_folder.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True)
        if mp3s:
            newest = mp3s[0]
            size_mb = newest.stat().st_size / (1024 * 1024)
            msg = f"Downloaded '{clean_title}' ({size_mb:.1f} MB) as MP3 to {dest_folder.name}."
            return True, msg, newest

        return False, f"Downloaded '{clean_title}', but could not locate the MP3 file.", None
    except Exception as e:
        err_msg = f"Song download failed: {e}"
        print(f"[media_downloader] {err_msg}")
        return False, err_msg, None


def _download_video(
    query_or_url: str,
    dest_folder: Path,
    player=None
) -> Tuple[bool, str, Optional[Path]]:
    """Download video (MP4) via yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        return False, "yt-dlp is not installed.", None

    is_direct_url = query_or_url.startswith("http://") or query_or_url.startswith("https://")
    target = query_or_url if is_direct_url else f"ytsearch1:{query_or_url}"

    log_msg = f"Downloading video '{query_or_url}'..."
    print(f"[media_downloader] {log_msg}")
    if player:
        player.write_log(f"SYS: {log_msg}")

    out_template = str(dest_folder / "%(title).90B.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "noplaylist": True,
        "max_filesize": 150 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=True)
            entries = info.get("entries")
            entry = entries[0] if entries else info
            title = entry.get("title", "video")
            clean_title = title.encode("ascii", errors="replace").decode()

        # Find newly created video file
        videos = sorted(
            [f for f in dest_folder.glob("*.*") if f.suffix.lower() in (".mp4", ".mkv", ".webm")],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        if videos:
            newest = videos[0]
            size_mb = newest.stat().st_size / (1024 * 1024)
            msg = f"Downloaded video '{clean_title}' ({size_mb:.1f} MB) to {dest_folder.name}."
            return True, msg, newest

        return False, f"Video '{clean_title}' processed, but output file not found.", None
    except Exception as e:
        err_msg = f"Video download failed: {e}"
        print(f"[media_downloader] {err_msg}")
        return False, err_msg, None


def _download_images(
    query: str,
    dest_folder: Path,
    count: int = 3,
    url: Optional[str] = None,
    player=None
) -> Tuple[bool, str, Optional[Path]]:
    """Search and download images using multi-engine validation."""
    from actions.image_downloader import (
        _search_candidates,
        _download_and_validate,
        _safe_stem,
        _next_path,
    )
    from concurrent.futures import ThreadPoolExecutor, as_completed

    log_msg = f"Searching and downloading {count} image(s) for '{query}'..."
    print(f"[media_downloader] {log_msg}")
    if player:
        player.write_log(f"SYS: {log_msg}")

    try:
        candidates, used_source = _search_candidates(query, "auto", url)
    except Exception as e:
        return False, f"Image search failed: {e}", None

    downloaded = []
    hashes = set()
    first_path = None

    with ThreadPoolExecutor(max_workers=min(count, 5)) as pool:
        futures = [pool.submit(_download_and_validate, item) for item in candidates[:max(count * 3, count)]]
        for future in as_completed(futures):
            try:
                digest, data, extension = future.result()
                if digest in hashes or len(downloaded) >= count:
                    continue
                hashes.add(digest)
                target = _next_path(dest_folder, _safe_stem(query), extension)
                target.write_bytes(data)
                if target.stat().st_size > 0:
                    downloaded.append(target.name)
                    if not first_path:
                        first_path = target
            except Exception:
                pass

    if downloaded:
        msg = f"Downloaded {len(downloaded)} image(s) for '{query}' to {dest_folder.name} (Files: {', '.join(downloaded[:3])})."
        return True, msg, first_path

    return False, f"Could not find valid downloadable images for '{query}'.", None


def _download_direct_file(
    query_or_url: str,
    dest_folder: Path,
    player=None
) -> Tuple[bool, str, Optional[Path]]:
    """Download a document, PDF, or general file."""
    is_direct_url = query_or_url.startswith("http://") or query_or_url.startswith("https://")
    target_url = query_or_url

    if not is_direct_url:
        # Search web for file link
        try:
            from actions.web_search import _fetch_ddg_results
            ddg = _fetch_ddg_results(f"{query_or_url} filetype:pdf")
            if ddg and ddg[0].get("url"):
                target_url = ddg[0]["url"]
            else:
                return False, f"Could not find a direct download link for '{query_or_url}'.", None
        except Exception:
            return False, f"Could not resolve download URL for '{query_or_url}'.", None

    parsed = urlparse(target_url)
    filename = Path(parsed.path).name or "downloaded_file"
    if not Path(filename).suffix:
        filename += ".pdf" if "pdf" in query_or_url.lower() else ".bin"

    # Sanitize filename
    clean_filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    target_path = dest_folder / clean_filename

    log_msg = f"Downloading file '{clean_filename}' from web..."
    print(f"[media_downloader] {log_msg}")
    if player:
        player.write_log(f"SYS: {log_msg}")

    try:
        resp = requests.get(target_url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=25)
        resp.raise_for_status()
        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        size_kb = target_path.stat().st_size / 1024
        msg = f"Downloaded '{clean_filename}' ({size_kb:.1f} KB) to {dest_folder.name}."
        return True, msg, target_path
    except Exception as e:
        return False, f"File download failed: {e}", None


def media_downloader(
    parameters: Optional[dict] = None,
    player=None,
    speak=None
) -> str:
    """Download songs, images, videos, or files from Google, Chrome, or web.
    
    Parameters:
        query (str): Search term, song title, image topic, or URL.
        category (str): 'song' | 'image' | 'video' | 'file' | 'auto' (default: 'auto').
        count (int): Number of items (for images, default 3).
        source (str): 'auto' | 'google' | 'youtube' | 'chrome' (default: 'auto').
        url (str): Optional direct URL to download.
        open_in_explorer (bool): Open and highlight the file in File Explorer (default: True).
    """
    params = parameters or {}
    raw_query = str(params.get("query") or params.get("search") or params.get("title") or "").strip()
    category_param = str(params.get("category") or "auto").strip()
    source_pref = str(params.get("source") or "auto").lower().strip()
    url_param = params.get("url")
    open_in_explorer = params.get("open_in_explorer", True)

    try:
        count = max(1, min(10, int(params.get("count", 3))))
    except (TypeError, ValueError):
        count = 3

    # Check for active Chrome tab only if user asks for current page/tab or provided no query
    wants_current_tab = any(p in raw_query.lower() for p in ("this page", "this tab", "current tab", "current page", "from the tab", "this site", "from here"))
    if not url_param and (wants_current_tab or (not raw_query and source_pref == "chrome")):
        active_url = _get_active_browser_url()
        if active_url:
            url_param = active_url

    clean_target = _clean_query(raw_query) if raw_query else (url_param or "")
    if not clean_target and url_param:
        clean_target = url_param

    if not clean_target:
        return "Please specify what you would like to download (e.g. song name, image description, or file URL)."

    category = _detect_category(raw_query or clean_target, category_param)
    dest_folder = _get_media_dir(category)

    print(f"[media_downloader] Intent: category={category}, target='{clean_target}', folder={dest_folder}")

    success = False
    result_text = ""
    downloaded_file = None

    if category == "song":
        success, result_text, downloaded_file = _download_song(clean_target, dest_folder, player=player)
    elif category == "video":
        success, result_text, downloaded_file = _download_video(clean_target, dest_folder, player=player)
    elif category == "file":
        success, result_text, downloaded_file = _download_direct_file(clean_target, dest_folder, player=player)
    else:  # Image
        success, result_text, downloaded_file = _download_images(
            clean_target, dest_folder, count=count, url=url_param, player=player
        )

    if success and open_in_explorer and downloaded_file:
        _reveal_in_explorer(downloaded_file)
        result_text += "\n📂 Opened and highlighted in File Explorer."

    if player:
        player.write_log(f"SYS: {result_text}")

    if speak and success:
        speak(result_text)

    return result_text
