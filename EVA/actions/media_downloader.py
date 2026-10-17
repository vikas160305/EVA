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
import base64
import platform
import subprocess
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urljoin, unquote
from typing import Optional, List, Dict, Tuple

import requests
from bs4 import BeautifulSoup

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
    elif cat in ("document", "documents", "doc", "docs", "pdf", "book", "ebook", "cheatsheet"):
        folder_name = "Documents"
        sub_folder = "EVA Documents"
    elif cat in ("dataset", "datasets", "data", "sheet", "spreadsheet"):
        folder_name = "Downloads"
        sub_folder = "EVA Datasets"
    elif cat in ("installer", "installers", "app", "setup", "archive", "zip", "software"):
        folder_name = "Downloads"
        sub_folder = "EVA Installers"
    elif cat in ("code", "script", "scripts", "repo", "program"):
        folder_name = "Downloads"
        sub_folder = "EVA Code"
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
        if cp in ("document", "doc", "docs", "pdf", "book", "ebook", "cheatsheet"):
            return "document"
        if cp in ("dataset", "datasets", "data", "sheet", "spreadsheet", "csv", "excel"):
            return "dataset"
        if cp in ("installer", "installers", "setup", "archive", "zip", "exe", "msi"):
            return "installer"
        if cp in ("code", "script", "scripts", "repo"):
            return "code"
        if cp in ("file", "download", "direct"):
            return "file"

    q = query.lower()

    # URL or file extension detection
    parsed_path = urlparse(query).path.lower() if query.startswith(("http://", "https://")) else q
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg")):
        return "song"
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv")):
        return "video"
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico")):
        return "image"
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt", ".rtf", ".epub", ".odt")):
        return "document"
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".csv", ".xlsx", ".xls", ".tsv", ".parquet")):
        return "dataset"
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".zip", ".rar", ".7z", ".tar.gz", ".tar", ".gz", ".exe", ".msi", ".dmg", ".iso")):
        return "installer"
    if any(parsed_path.endswith(ext) or ext + "?" in parsed_path for ext in (".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".php", ".html", ".css", ".ipynb", ".sh", ".sql")):
        return "code"

    # Keyword detection
    if any(w in q for w in ("song", "music", "audio", "mp3", "track", "soundtrack", "tune", "singing", "album")):
        return "song"
    if any(w in q for w in ("video", "videos", "clip", "movie", "mp4", "reel", "youtube video", "tutorial video")):
        return "video"
    if any(w in q for w in ("dataset", "data set", "kaggle", "csv", "spreadsheet", "excel sheet", "xlsx", "records csv", "sales data", "training data", "test data")):
        return "dataset"
    if any(w in q for w in ("pdf", "cheatsheet", "cheat sheet", "document", "documentation", "whitepaper", "research paper", "handbook", "manual", "guide pdf", "ebook", "e-book", "book pdf", "lecture notes", "syllabus", "notes pdf", "sample resume", "resume template", "docx", "pptx")):
        return "document"
    if any(w in q for w in ("installer", "setup exe", "windows installer", "install file", "setup file", "zip file", "archive", "tar.gz", "msi installer", "executable", "7z")):
        return "installer"
    if any(w in q for w in ("source code", "github repo", "script", "python code", "java code", "c++ code", "javascript code", "starter code", "boilerplate", "implementation in python", "implementation in java")):
        return "code"
    if any(w in q for w in ("image", "images", "photo", "photos", "wallpaper", "picture", "pictures", "drawing", "illustration", "diagram", "screenshot", "logo", "icon", "vector art")):
        return "image"
    if any(w in q for w in ("file", "download")):
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


def _clean_filename(name: str) -> str:
    """Sanitize filename to prevent path traversal and illegal Windows chars."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name).strip(". ")
    if len(clean) > 90:
        p = Path(clean)
        ext = p.suffix
        stem = p.stem[:80]
        clean = stem + ext
    return clean or "downloaded_file"


def _default_ext_for_category(category: str) -> str:
    """Map category to default file extension."""
    cat = category.lower().strip()
    if cat == "document":
        return ".pdf"
    if cat == "dataset":
        return ".csv"
    if cat == "installer":
        return ".zip"
    if cat == "code":
        return ".py"
    if cat == "song":
        return ".mp3"
    if cat == "video":
        return ".mp4"
    if cat == "image":
        return ".jpg"
    return ".bin"


def _extract_filename_from_response(
    resp: requests.Response,
    fallback_name: str,
    default_ext: str = ""
) -> str:
    """Extract best filename from Content-Disposition, URL path, or Content-Type."""
    cd = str(resp.headers.get("Content-Disposition", "") or "") if hasattr(resp, "headers") else ""
    if cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?\"?([^;\"\']+)', cd)
        if m:
            extracted = unquote(m.group(1).strip())
            if extracted:
                return _clean_filename(extracted)

    resp_url = str(getattr(resp, "url", "") or "")
    if resp_url and isinstance(resp_url, str):
        parsed_path = unquote(urlparse(resp_url).path)
        path_name = Path(parsed_path).name
        if path_name and "." in path_name and len(Path(path_name).suffix) <= 6:
            return _clean_filename(path_name)

    # Infer extension from Content-Type
    ct = str(resp.headers.get("Content-Type", "") or "").split(";")[0].strip().lower() if hasattr(resp, "headers") else ""
    ct_map = {
        "application/pdf": ".pdf",
        "text/csv": ".csv",
        "application/json": ".json",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "application/x-7z-compressed": ".7z",
        "application/x-tar": ".tar",
        "application/gzip": ".tar.gz",
        "application/x-msdownload": ".exe",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "text/x-python": ".py",
        "text/javascript": ".js",
        "text/html": ".html",
        "text/plain": ".txt",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "audio/mpeg": ".mp3",
        "video/mp4": ".mp4",
    }
    ext = ct_map.get(ct, default_ext)
    stem = _clean_filename(fallback_name)
    if not Path(stem).suffix and ext:
        stem += ext
    return stem


def _resolve_github_file(query: str, extensions: List[str]) -> Optional[Tuple[str, str]]:
    """Search public GitHub repositories for direct raw file downloads."""
    try:
        clean_q = _clean_query(query)
        headers = {"User-Agent": USER_AGENT}
        url = f"https://api.github.com/search/repositories?q={quote_plus(clean_q)}&per_page=5"
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code != 200:
            return None

        items = resp.json().get("items", [])
        for item in items:
            repo_full_name = item.get("full_name")
            if not repo_full_name:
                continue
            contents_url = f"https://api.github.com/repos/{repo_full_name}/contents"
            c_resp = requests.get(contents_url, headers=headers, timeout=6)
            if c_resp.status_code != 200:
                continue

            entries = c_resp.json()
            if isinstance(entries, list):
                for f in entries:
                    if f.get("type") == "file":
                        name = f.get("name", "")
                        if any(name.lower().endswith(ext) for ext in extensions):
                            raw_url = f.get("download_url")
                            if raw_url:
                                return raw_url, name
    except Exception as e:
        print(f"[media_downloader] GitHub file resolution warning: {e}")
    return None


def _search_web_links(query: str, max_results: int = 8) -> List[dict]:
    """Search web using ddgs with multiple backends and Bing fallback."""
    results = []

    # 1. Try ddgs across api, html, and lite backends
    try:
        import ddgs
        client = ddgs.DDGS()
        for backend in ("api", "html", "lite"):
            try:
                raw_ddg = list(client.text(query, max_results=max_results, backend=backend))
                if raw_ddg:
                    for item in raw_ddg:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "snippet": item.get("body", ""),
                        })
                    break
            except Exception:
                continue
    except Exception:
        pass

    if results:
        return results

    # 2. Bing web search fallback
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(f"https://www.bing.com/search?q={quote_plus(query)}", headers=headers, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("li.b_algo h2 a"):
                href = a.get("href", "")
                if "bing.com/ck/a?" in href:
                    m = re.search(r'[?&]u=a1([a-zA-Z0-9_\-]+)', href)
                    if m:
                        b64 = m.group(1).replace("-", "+").replace("_", "/")
                        b64 += "=" * ((4 - len(b64) % 4) % 4)
                        try:
                            href = base64.b64decode(b64).decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                if href.startswith("http"):
                    results.append({"title": a.get_text(), "url": href, "snippet": ""})
    except Exception as e:
        print(f"[media_downloader] Bing search fallback warning: {e}")

    return results


CURATED_SOURCES = {
    "titanic": ("https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv", "titanic.csv"),
    "iris": ("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv", "iris.csv"),
    "python cheatsheet": ("https://static.realpython.com/python-cheatsheet.pdf", "python-cheatsheet.pdf"),
    "python cheat sheet": ("https://static.realpython.com/python-cheatsheet.pdf", "python-cheatsheet.pdf"),
    "quicksort": ("https://raw.githubusercontent.com/TheAlgorithms/Python/master/sorts/quick_sort.py", "quick_sort.py"),
}


def _resolve_web_file_url(query: str, category: str) -> Tuple[Optional[str], Optional[str]]:
    """Find direct download link for documents, datasets, installers, code, or files."""
    q_lower = query.lower()

    # Check curated instant sources
    for key, (cur_url, cur_name) in CURATED_SOURCES.items():
        if key in q_lower:
            return cur_url, cur_name

    # Handle direct URL passed in query
    if query.startswith(("http://", "https://")):
        url = query
        if "github.com" in url and "/blob/" in url:
            url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        p_name = Path(urlparse(url).path).name
        return url, p_name or "downloaded_file"

    # Define target file extensions by category
    ext_map = {
        "dataset": [".csv", ".xlsx", ".xls", ".json", ".tsv", ".parquet"],
        "document": [".pdf", ".docx", ".doc", ".pptx", ".txt", ".epub"],
        "installer": [".exe", ".msi", ".zip", ".rar", ".7z", ".tar.gz", ".dmg"],
        "code": [".py", ".java", ".cpp", ".c", ".js", ".ts", ".html", ".css", ".ipynb", ".sh", ".sql", ".go", ".rs"],
        "file": [".pdf", ".csv", ".zip", ".exe", ".docx", ".xlsx", ".py", ".txt"],
    }
    extensions = ext_map.get(category, ext_map["file"])

    # For dataset or code, check GitHub repositories first
    if category in ("dataset", "code"):
        gh_match = _resolve_github_file(query, extensions)
        if gh_match:
            return gh_match

    # Formulate targeted web search query
    clean = _clean_query(query)
    if category == "document" and not any(w in clean.lower() for w in ("pdf", "doc", "paper")):
        search_q = f"{clean} pdf download"
    elif category == "dataset" and not any(w in clean.lower() for w in ("csv", "xlsx", "data")):
        search_q = f"{clean} csv dataset download"
    elif category == "installer" and not any(w in clean.lower() for w in ("installer", "exe", "zip", "setup")):
        search_q = f"{clean} windows installer download"
    elif category == "code" and not any(w in clean.lower() for w in ("code", "github", "script")):
        search_q = f"{clean} github code"
    else:
        search_q = f"{clean} download"

    candidates = _search_web_links(search_q)

    # Check candidates for direct links or GitHub blob links
    for item in candidates:
        url = item.get("url", "")
        if not url:
            continue
        if "github.com" in url and "/blob/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            return raw_url, Path(urlparse(raw_url).path).name

        clean_path = urlparse(url).path.lower()
        if any(clean_path.endswith(ext) for ext in extensions):
            return url, Path(urlparse(url).path).name

    # If no direct file URL found, scrape candidate HTML pages for download links
    headers = {"User-Agent": USER_AGENT}
    for item in candidates[:3]:
        page_url = item.get("url", "")
        if not page_url or not page_url.startswith("http"):
            continue
        try:
            resp = requests.get(page_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a"):
                    h = a.get("href", "")
                    if not h:
                        continue
                    clean_h = urlparse(h).path.lower()
                    if any(clean_h.endswith(ext) for ext in extensions):
                        resolved = urljoin(page_url, h)
                        return resolved, Path(clean_h).name
        except Exception:
            continue

    return None, None


def _download_web_file(
    query_or_url: str,
    dest_folder: Path,
    category: str = "file",
    player=None
) -> Tuple[bool, str, Optional[Path]]:
    """Download documents, datasets, installers, code, or general files."""
    log_msg = f"Resolving download link for {category} '{query_or_url}'..."
    print(f"[media_downloader] {log_msg}")
    if player:
        player.write_log(f"SYS: {log_msg}")

    resolved_url, suggested_name = _resolve_web_file_url(query_or_url, category)
    if not resolved_url:
        return False, f"Could not find a downloadable {category} for '{query_or_url}'.", None

    log_msg = f"Downloading {category} from '{resolved_url}'..."
    print(f"[media_downloader] {log_msg}")
    if player:
        player.write_log(f"SYS: {log_msg}")

    try:
        resp = requests.get(
            resolved_url,
            headers={"User-Agent": USER_AGENT},
            stream=True,
            timeout=25
        )
        resp.raise_for_status()

        # Reject HTML responses if expecting binary/document/installer/dataset
        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" in content_type and category in ("document", "dataset", "installer") and not resolved_url.endswith((".html", ".htm")):
            return False, f"Download link returned an HTML webpage instead of a {category} file.", None

        filename = _extract_filename_from_response(
            resp,
            fallback_name=suggested_name or _clean_query(query_or_url),
            default_ext=_default_ext_for_category(category)
        )
        target_path = dest_folder / filename

        total_bytes = 0
        max_bytes = 150 * 1024 * 1024  # 150 MB limit

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        f.close()
                        target_path.unlink(missing_ok=True)
                        return False, "File exceeds maximum download size limit (150 MB).", None
                    f.write(chunk)

        if not target_path.exists() or target_path.stat().st_size == 0:
            return False, "Downloaded file was empty or could not be saved.", None

        size_kb = target_path.stat().st_size / 1024
        if size_kb >= 1024:
            size_str = f"{size_kb / 1024:.1f} MB"
        else:
            size_str = f"{size_kb:.1f} KB"

        msg = f"Downloaded '{filename}' ({size_str}) to {dest_folder.name}."
        return True, msg, target_path

    except Exception as e:
        err_msg = f"File download failed: {e}"
        print(f"[media_downloader] {err_msg}")
        return False, err_msg, None


def _download_direct_file(
    query_or_url: str,
    dest_folder: Path,
    player=None
) -> Tuple[bool, str, Optional[Path]]:
    """Legacy wrapper for _download_web_file."""
    return _download_web_file(query_or_url, dest_folder, category="file", player=player)


def media_downloader(
    parameters: Optional[dict] = None,
    player=None,
    speak=None
) -> str:
    """Download songs, images, videos, documents, datasets, installers, code, or files from Google, Chrome, or web.
    
    Parameters:
        query (str): Search term, song title, image topic, document query, or URL.
        category (str): 'song' | 'image' | 'video' | 'document' | 'dataset' | 'installer' | 'code' | 'file' | 'auto' (default: 'auto').
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
        return "Please specify what you would like to download (e.g. song name, image description, dataset topic, or file URL)."

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
    elif category == "image":
        success, result_text, downloaded_file = _download_images(
            clean_target, dest_folder, count=count, url=url_param, player=player
        )
    else:  # "document", "dataset", "installer", "code", "file"
        success, result_text, downloaded_file = _download_web_file(
            clean_target, dest_folder, category=category, player=player
        )

    if success and open_in_explorer and downloaded_file:
        _reveal_in_explorer(downloaded_file)
        result_text += "\n📂 Opened and highlighted in File Explorer."

    if player:
        player.write_log(f"SYS: {result_text}")

    if speak and success:
        speak(result_text)

    return result_text
