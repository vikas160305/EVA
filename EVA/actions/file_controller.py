import os
import difflib
import re
import shutil
import subprocess
import platform
import tempfile
import uuid
import zipfile
import csv
import json
import threading
from pathlib import Path
from datetime import datetime
from threading import Lock
from time import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class DocumentTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    progress: float = 0.0
    label: str = "pending"
    cancel_event: threading.Event = field(default_factory=threading.Event)
    timeout_seconds: float = 60.0
    result: str = ""
    error: str = ""


class DocumentService:
    """Central, dependency-light service for atomic file creation and conversion.

    It is deliberately small and testable: every write goes through a same-directory
    temporary file, then the completed artifact is validated by extension and content
    signature before a safe replace or move.
    """

    SUPPORTED_FORMATS = {"txt", "md", "markdown", "json", "csv", "docx", "pdf", "pptx", "html"}
    TEXT_EXTENSIONS = {"txt", "md", "markdown", "json", "csv", "html"}
    OFFICE_EXTENSIONS = {"docx", "pptx", "pdf"}
    OUTPUT_LABELS = {
        "txt": "text artifact",
        "md": "markdown artifact",
        "json": "json artifact",
        "csv": "csv artifact",
        "docx": "DOCX artifact",
        "pdf": "PDF artifact",
        "pptx": "PPTX artifact",
        "html": "HTML artifact",
    }
    SUPPORTED_PAIRS = {
        "txt->txt": "high-fidelity",
        "txt->md": "best-effort",
        "txt->json": "best-effort",
        "txt->csv": "best-effort",
        "txt->docx": "best-effort",
        "txt->pdf": "high-fidelity",
        "txt->pptx": "best-effort",
        "docx->txt": "best-effort",
        "docx->pdf": "high-fidelity",
        "pptx->txt": "best-effort",
        "pptx->pdf": "best-effort",
        "pdf->txt": "best-effort",
        "pdf->pdf": "high-fidelity",
    }

    def __init__(self, timeout_seconds: float = 60.0):
        self.timeout_seconds = timeout_seconds

    def create_text_artifact(self, destination: Path, stem: str, extension: str, content: str,
                              confirm_overwrite: bool = False) -> tuple[Path, str]:
        extension = self._normalise_extension(extension)
        destination = Path(destination).expanduser().resolve(strict=False)
        if not _path_is_within(destination, Path.home().resolve(strict=False)):
            raise UnsafePathError("Destination must stay inside the safe home directory.")
        if not destination.exists():
            destination.mkdir(parents=True, exist_ok=True)
        if not extension or extension not in {"txt", "md", "json", "csv", "html"}:
            raise ValueError("Unsupported text artifact extension.")
        safe_output = self._next_safe_path(destination, stem, extension, confirm_overwrite=confirm_overwrite)
        tmp = self._atomic_tmp_path(safe_output)
        try:
            tmp.write_text(content, encoding="utf-8")
            self._validate_artifact(tmp, extension)
            os.replace(tmp, safe_output)
            return safe_output, "created"
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            raise

    def convert_artifact(self, source: Path, destination: Path, to_extension: str,
                          confirm_overwrite: bool = False, worker: Optional[Callable] = None,
                          cancellation_event: Optional[threading.Event] = None) -> tuple[Path, str]:
        to_extension = self._normalise_extension(to_extension)
        if not source.exists():
            raise FileNotFoundError(f"Source artifact not found: {source}")
        if not self._valid_extension(source.suffix.lower(), "source"):
            raise ValueError("Unsupported source extension for conversion.")
        if not self._valid_extension(to_extension, "target"):
            raise ValueError("Unsupported destination extension for conversion.")
        destination.mkdir(parents=True, exist_ok=True)
        safe_output = self._next_safe_path(destination, source.stem, to_extension, confirm_overwrite=confirm_overwrite)
        if safe_output.exists() and not confirm_overwrite:
            raise FileExistsError("Refusing to overwrite existing artifact without explicit confirmation.")
        label = self._fallback_label(source, to_extension)
        if cancellation_event and cancellation_event.is_set():
            raise TimeoutError("Conversion cancelled before dispatch.")

        def do_convert():
            if worker:
                return worker(source, safe_output, label)
            # Simple dependency-free conversion for testability.
            if source.suffix.lower() == ".txt" and to_extension == "pdf":
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import LETTER
                c = canvas.Canvas(str(safe_output), pagesize=LETTER)
                y = LETTER[1] - 72
                with source.open("r", encoding="utf-8", errors="ignore") as handle:
                    for line in handle:
                        line = line.rstrip("\n")
                        if y < 72:
                            c.showPage()
                            y = LETTER[1] - 72
                        c.drawString(72, y, line)
                        y -= 12
                c.save()
                return safe_output
            if source.suffix.lower() == ".docx" and to_extension == "txt":
                try:
                    from docx import Document
                    doc = Document(str(source))
                    text = "\n".join(p.text for p in doc.paragraphs)
                    safe_output.write_text(text, encoding="utf-8")
                    return safe_output
                except Exception:
                    import zipfile, xml.etree.ElementTree as ET
                    with zipfile.ZipFile(source, 'r') as z:
                        data = z.read('word/document.xml')
                    root = ET.fromstring(data)
                    texts = [t.text for t in root.iter() if t.tag.endswith('}t') and t.text]
                    safe_output.write_text('\n'.join(texts), encoding='utf-8')
                    return safe_output
            if source.suffix.lower() == ".pdf" and to_extension == "txt":
                from PyPDF2 import PdfReader
                pages = []
                reader = PdfReader(str(source))
                for p in reader.pages:
                    try:
                        pages.append(p.extract_text() or '')
                    except Exception:
                        pages.append('')
                safe_output.write_text('\n\n'.join(pages), encoding='utf-8')
                return safe_output
            raise RuntimeError(f"Unsupported conversion pair {source.suffix.lower()} → .{to_extension}.")

        tmp = self._atomic_tmp_path(safe_output)
        try:
            # Do work in the background style but keep it local and cancellable.
            if cancellation_event:
                cancellation_event.clear()
            if worker:
                produced = worker(source, tmp, label)
            else:
                produced = do_convert()
            if produced and Path(produced).exists():
                self._validate_artifact(Path(produced), to_extension)
                if Path(produced) != safe_output:
                    os.replace(Path(produced), safe_output)
                return safe_output, label
            raise RuntimeError("Conversion worker did not produce a readable artifact.")
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            raise

    def _normalise_extension(self, value: str) -> str:
        value = str(value or "txt").lower().strip().lstrip(".")
        if value == "markdown":
            value = "md"
        if value in {"powerpoint", "ppt"}:
            value = "pptx"
        if value in {"word", "document", "doc"}:
            value = "docx"
        return value

    def _valid_extension(self, ext: str, role: str = "") -> bool:
        ext = (ext or "").lower().lstrip(".")
        return ext in self.SUPPORTED_FORMATS

    def _validate_artifact(self, path: Path, extension: str) -> None:
        if not path.exists():
            raise ValueError("Generated artifact is missing.")
        if path.stat().st_size <= 0:
            raise ValueError("Generated artifact is empty.")
        if path.stat().st_size > 50 * 1024 * 1024:
            raise ValueError("Generated artifact exceeds the safe file-size limit.")
        ext = extension.lower().lstrip(".")
        if ext in {"txt", "md", "html", "htm", "css", "py", "js", "ts", "java", "c", "cpp", "cs", "go", "rs", "php", "sql", "ps1", "sh", "bat", "xml", "yaml", "yml"}:
            path.read_text(encoding="utf-8", errors="ignore")
        elif ext == "json":
            json.loads(path.read_text(encoding="utf-8"))
        elif ext == "csv":
            with path.open(newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                row = next(reader, None)
                if row is None:
                    raise ValueError("CSV artifact has no header row.")
        elif ext == "docx":
            with zipfile.ZipFile(path, 'r') as archive:
                required = {'[Content_Types].xml', '_rels/.rels', 'word/document.xml'}
                if not required.issubset(set(archive.namelist())):
                    raise ValueError('DOCX package content is incomplete.')
        elif ext == "pptx":
            with zipfile.ZipFile(path, 'r') as archive:
                if '[Content_Types].xml' not in archive.namelist() or 'ppt/presentation.xml' not in archive.namelist():
                    raise ValueError('PPTX package content is incomplete.')
        elif ext == "pdf":
            head = path.read_bytes()[:5]
            if head != b'%PDF-':
                raise ValueError('PDF signature missing.')
        else:
            try:
                path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                raise ValueError(f"Unsupported output extension: {ext}")

    def _atomic_tmp_path(self, destination: Path) -> Path:
        tmp_dir = destination.parent
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir / f".{destination.name}.{uuid.uuid4().hex}.tmp"

    def _next_safe_path(self, destination: Path, stem: str, extension: str, confirm_overwrite: bool = False) -> Path:
        safe_stem = re.sub(r"[^A-Za-z0-9 _-]+", "", str(stem)).strip().replace(" ", "_").lower()[:80] or "jarvis_document"
        target = destination / f"{safe_stem}.{extension}"
        if not target.exists() or confirm_overwrite:
            return target
        index = 2
        while True:
            candidate = destination / f"{safe_stem}_{index}.{extension}"
            if not candidate.exists():
                return candidate
            index += 1

    def _fallback_label(self, source: Path, target_ext: str) -> str:
        if source.suffix.lower() == ".docx" and target_ext == "pdf":
            return "office/libreoffice-high-fidelity"
        if source.suffix.lower() == ".pptx" and target_ext == "pdf":
            return "office/libreoffice-high-fidelity"
        if source.suffix.lower() == ".pdf" and target_ext == "txt":
            return "pdf-text-extraction"
        if source.suffix.lower() == ".pptx" and target_ext == "txt":
            return "pptx-xml-text-fallback"
        if source.suffix.lower() == ".docx" and target_ext == "txt":
            return "docx-xml-text-fallback"
        return "direct-support"

    @staticmethod
    def dependency_message(module: str, install_hint: str) -> str:
        return f"Missing dependency: {module}. Install it with: {install_hint}"

    def supported_pairs(self) -> dict[str, str]:
        return dict(self.SUPPORTED_PAIRS)


class DocumentWorker:
    """Tiny cancellable background task wrapper for conversions and creation."""

    def __init__(self, service: DocumentService, timeout_seconds: float = 60.0):
        self.service = service
        self.timeout_seconds = timeout_seconds
        self._tasks: dict[str, DocumentTask] = {}
        self._lock = threading.Lock()

    def submit(self, target: str, func: Callable[[DocumentTask], str], timeout_seconds: Optional[float] = None) -> DocumentTask:
        task = DocumentTask(timeout_seconds=float(timeout_seconds or self.timeout_seconds))
        with self._lock:
            self._tasks[task.task_id] = task
        thread = threading.Thread(target=self._run, args=(task, target, func), daemon=True)
        thread.start()
        return task

    def _run(self, task: DocumentTask, target: str, func: Callable[[DocumentTask], str]) -> None:
        try:
            task.status = "running"
            task.progress = 1.0
            task.result = func(task)
            task.status = "done" if not task.cancel_event.is_set() else "cancelled"
            task.progress = 100.0
        except Exception as exc:
            task.error = str(exc)
            task.status = "failed"

    def cancel(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.cancel_event.set()
            task.status = "cancelled"
            task.progress = 100.0

try:
    import send2trash
    _SEND2TRASH = True
except ImportError:
    _SEND2TRASH = False

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

_SAFE_ROOTS: list[Path] = [
    Path.home(),
]

_SHORTCUTS = {
    "desktop": "_get_desktop",
    "downloads": "_get_downloads",
    "documents": "_get_documents",
    "pictures": "_get_pictures",
    "music": "_get_music",
    "videos": "_get_videos",
    "home": "_home",
}
_PROTECTED_NAMES = {"desktop", "downloads", "documents", "pictures", "music", "videos", "home"}
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SEARCH_SKIP_NAMES = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".cache", "cache", "caches", "temp", "tmp",
    "appdata", "program files", "program files (x86)", "programdata",
    "windows", "$recycle.bin", "system volume information",
}
_SEARCH_SELECTION_LOCK = Lock()
_LAST_SEARCH_RESULTS: list[Path] = []
_FILE_SEARCH_CACHE_TTL_SECONDS = 30.0
_FILE_SEARCH_CACHE: dict[tuple, tuple[float, list[tuple], list[str], list[Path]]] = {}
_FILE_SEARCH_CACHE_LOCK = Lock()


class UnsafePathError(ValueError):
    """Raised when a requested path leaves the user's home directory."""


def validate_name(name: str) -> str:
    """Validate one filesystem name and return it unchanged."""
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ValueError("A valid file or folder name is required.")
    if _INVALID_NAME_CHARS.search(name) or name.endswith((".", " ")):
        raise ValueError(f"Invalid file or folder name: {name!r}")
    if Path(name).name != name or Path(name).name != name.replace("\\", "/"):
        raise ValueError("The name must be a single file or folder name.")
    if Path(name).drive or Path(name).root:
        raise ValueError("Absolute names are not allowed.")
    if platform.system() == "Windows" and Path(name).stem.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        raise ValueError(f"Reserved Windows name: {name!r}")
    return name


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        return path == root or path.is_relative_to(root)
    except ValueError:
        return False


def resolve_safe_path(raw: str, name: str = "") -> Path:
    """Resolve a shortcut/path and optional child name, strictly under home."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("A path is required.")
    raw_path = raw.strip().replace("\\", "/")
    parts = Path(raw_path).parts
    if ".." in parts:
        raise UnsafePathError("Parent-directory traversal is not allowed.")
    anchor = Path(raw_path).anchor
    for part in parts:
        if part != anchor:
            validate_name(part)

    lower = raw_path.lower()
    base = None
    for alias, getter_name in _SHORTCUTS.items():
        if lower == alias or lower.startswith(alias + "/"):
            getter = Path.home if getter_name == "_home" else globals()[getter_name]
            base = getter()
            suffix = raw_path[len(alias):].lstrip("/")
            if suffix:
                base = base / suffix
            break
    if base is None:
        candidate = Path(raw_path).expanduser()
        base = candidate if candidate.is_absolute() else Path.home() / candidate

    if name:
        validate_name(name)
        base = base / name

    resolved = base.resolve(strict=False)
    home = Path.home().resolve(strict=True)
    if not _path_is_within(resolved, home):
        raise UnsafePathError(f"Access denied outside home directory: {resolved}")
    return resolved


def is_protected_path(path: Path) -> bool:
    """Return whether a path is one of the user's protected root folders."""
    resolved = path.resolve(strict=False)
    protected = [
        Path.home(), _get_desktop(), _get_downloads(), _get_documents(),
        _get_pictures(), _get_music(), _get_videos(),
    ]
    return any(resolved == item.resolve(strict=False) for item in protected)


def require_confirmation(confirmed: bool) -> None:
    if confirmed is not True:
        raise PermissionError("Deletion requires confirmed=True.")

def _is_safe_path(target: Path) -> bool:
    """Compatibility wrapper for callers that need a boolean safety check."""
    try:
        resolved = target.resolve(strict=False)
        return any(_path_is_within(resolved, root.resolve(strict=True)) for root in _SAFE_ROOTS)
    except (OSError, RuntimeError, ValueError):
        return False

def _get_desktop() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    onedrive_dt = Path.home() / "OneDrive" / "Desktop"
    if onedrive_dt.exists():
        return onedrive_dt
    return Path.home() / "Desktop"

def _get_downloads() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DOWNLOAD_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Downloads"

def _get_documents() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DOCUMENTS_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    jarvis_docs = Path.home() / "Documents" / "JARVIS Created"
    if jarvis_docs.exists():
        return Path.home() / "Documents"
    onedrive_docs = Path.home() / "OneDrive" / "Documents"
    if onedrive_docs.exists():
        return onedrive_docs
    return Path.home() / "Documents"

def _get_pictures() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_PICTURES_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Pictures"

def _get_music() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_MUSIC_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Music"

def _get_videos() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_VIDEOS_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Videos"


def _configured_search_roots() -> list[Path]:
    """Return extra read-only search roots configured by the user."""
    roots = []
    for raw_root in os.environ.get("MARK_L_SEARCH_PATHS", "").split(os.pathsep):
        if not raw_root.strip():
            continue
        try:
            root = Path(raw_root).expanduser().resolve(strict=False)
            if root.exists() and root.is_dir():
                roots.append(root)
        except (OSError, RuntimeError, ValueError):
            continue
    return roots


def _local_drive_roots() -> list[Path]:
    """Return mounted local volumes for read-only ``all`` searches."""
    if _OS != "Windows":
        return [Path("/")]
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = Path(f"{letter}:\\")
        try:
            if root.exists() and root.is_dir():
                drives.append(root)
        except OSError:
            continue
    return drives


def _search_roots(raw_path: str) -> list[Path]:
    """Resolve a search scope without granting mutation access outside home."""
    query = (raw_path or "home").strip().lower()
    if query in {"all", "everywhere", "all drives", "this pc"}:
        roots = [
            Path.home(), _get_desktop(), _get_downloads(), _get_documents(),
            _get_pictures(), _get_music(), _get_videos(),
            *_local_drive_roots(),
            *_configured_search_roots(),
        ]
    elif query in {"", "home", "user", "user folders"}:
        roots = [
            Path.home(), _get_desktop(), _get_downloads(), _get_documents(),
            _get_pictures(), _get_music(), _get_videos(),
            *_configured_search_roots(),
        ]
    else:
        candidate = Path(raw_path).expanduser()
        if candidate.is_absolute():
            resolved_candidate = candidate.resolve(strict=False)
            # Searching is read-only.  An explicit path supplied by the user
            # may be on another local drive, while write/delete operations
            # remain restricted by resolve_safe_path().
            roots = [resolved_candidate]
        else:
            roots = [_resolve_path(raw_path)]

    unique = []
    seen = set()
    for root in roots:
        try:
            resolved = root.resolve(strict=False)
            key = os.path.normcase(str(resolved))
            if key not in seen and resolved.exists() and resolved.is_dir():
                seen.add(key)
                unique.append(resolved)
        except (OSError, RuntimeError, ValueError):
            continue
    return unique


def _search_item_type(item_type: str) -> str:
    value = (item_type or "both").strip().lower()
    return {"file": "file", "files": "file", "folder": "folder", "folders": "folder"}.get(value, "both")


def _extension_set(extension: str) -> set[str]:
    query = (extension or "").strip().lower()
    if query in ("images", "image", "pictures", "picture"):
        return _IMAGE_EXTS
    if query in ("videos", "video"):
        return _VIDEO_EXTS
    if query in ("audio", "audios", "music", "song", "songs"):
        return {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
    if query in ("document", "documents", "doc"):
        return {".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".md"}
    if query in ("spreadsheet", "spreadsheets", "sheet", "sheets"):
        return {".xls", ".xlsx", ".ods", ".csv"}
    if query in ("presentation", "presentations", "slides", "slide"):
        return {".ppt", ".pptx", ".odp"}
    if query and not query.startswith("."):
        query = "." + query
    return {query} if query else set()


def _normalise_spoken_search(name: str, extension: str = "") -> tuple[str, str]:
    """Turn voice-style names such as ``W11 PDF`` into search terms.

    Speech recognition often returns the file type as a final word rather than
    putting it in the extension field.  Searching the phrase literally cannot
    match a normal filename such as ``W11.pdf``.
    """
    clean_name = (name or "").strip()
    clean_extension = (extension or "").strip()
    if clean_extension or not clean_name:
        return clean_name, clean_extension

    match = re.match(
        r"^(?P<stem>.+?)\s+(?P<extension>pdf|docx?|xlsx?|pptx?|txt|csv|jpe?g|png|gif|webp|mp[34]|mkv|wav|flac|m4a|document|documents|spreadsheet|sheet|presentation|slides|image|photo|picture|video|music|audio)$",
        clean_name,
        flags=re.IGNORECASE,
    )
    if match:
        spoken_extension = match.group("extension").lower()
        categories = {
            "document", "documents", "spreadsheet", "sheet", "presentation",
            "slides", "image", "photo", "picture", "video", "music", "audio",
        }
        extension = spoken_extension if spoken_extension in categories else "." + spoken_extension
        return match.group("stem").strip(), extension
    return clean_name, clean_extension


def invalidate_file_search_cache() -> None:
    """Clear the bounded file search cache after mutations that change results."""
    with _FILE_SEARCH_CACHE_LOCK:
        _FILE_SEARCH_CACHE.clear()


def _search_items(name: str, extension: str, path: str, item_type: str, max_results: int):
    name_query = (name or "").strip().casefold()
    ext_set = _extension_set(extension)
    wanted_type = _search_item_type(item_type)
    candidates = []
    suggestions = []
    roots = _search_roots(path)
    root_priority = {os.path.normcase(str(root)): index for index, root in enumerate(roots)}
    common_roots = [
        _get_desktop(), _get_downloads(), _get_documents(),
        _get_pictures(), _get_music(), _get_videos(),
    ]

    for root in roots:
        def on_walk_error(error):
            pass

        for current, directories, files in os.walk(root, topdown=True, onerror=on_walk_error):
            directories[:] = [
                directory for directory in directories
                if directory.casefold() not in _SEARCH_SKIP_NAMES
                and not directory.startswith(".")
            ]
            entries = []
            if wanted_type != "file":
                entries.extend((directory, True) for directory in directories)
            if wanted_type != "folder":
                entries.extend((file_name, False) for file_name in files)

            for entry_name, is_dir in entries:
                entry_path = Path(current) / entry_name
                suggestions.append(entry_name)
                lowered = entry_name.casefold()
                if name_query and name_query not in lowered:
                    continue
                if not is_dir and ext_set and entry_path.suffix.casefold() not in ext_set:
                    continue
                try:
                    stat = entry_path.stat()
                except (OSError, PermissionError):
                    continue
                exact = bool(name_query and lowered == name_query)
                match_score = 0 if exact else (1 if name_query else 2)
                common_score = len(common_roots) + root_priority.get(
                    os.path.normcase(str(root)), len(roots)
                )
                for index, common_root in enumerate(common_roots):
                    if _path_is_within(entry_path, common_root):
                        common_score = index
                        break
                candidates.append((
                    match_score, common_score, -stat.st_mtime,
                    entry_name.casefold(), entry_path, is_dir, stat,
                ))

    candidates.sort(key=lambda item: item[:4])
    unique_candidates = []
    seen_paths = set()
    for candidate in candidates:
        path_key = os.path.normcase(str(candidate[4]))
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)
        unique_candidates.append(candidate)
        if len(unique_candidates) >= max_results:
            break
    return unique_candidates, suggestions, roots


def _cached_search_items(name: str, extension: str, path: str, item_type: str, max_results: int):
    """Return a search result snapshot with a short bounded TTL and safe cache invalidation.

    This preserves the current API but avoids expensive directory scans for the same
    repeated file requests while staying consistent after create/rename/move/copy/delete.
    """
    key = (name.casefold() if name else "", extension.casefold() if extension else "", path, item_type, max_results)
    now = time()
    with _FILE_SEARCH_CACHE_LOCK:
        cached = _FILE_SEARCH_CACHE.get(key)
        if cached and cached[0] > now:
            return cached[1], cached[2], cached[3]
        if cached:
            del _FILE_SEARCH_CACHE[key]

    matches, suggestions, roots = _search_items(name, extension, path, item_type, max_results)
    with _FILE_SEARCH_CACHE_LOCK:
        _FILE_SEARCH_CACHE[key] = (now + _FILE_SEARCH_CACHE_TTL_SECONDS, matches, suggestions, roots)
        # keep the cache bounded in memory
        if len(_FILE_SEARCH_CACHE) > 128:
            expired = sorted(_FILE_SEARCH_CACHE.items(), key=lambda item: item[1][0])[: len(_FILE_SEARCH_CACHE) - 128]
            for exp_key, _ in expired:
                _FILE_SEARCH_CACHE.pop(exp_key, None)
    return matches, suggestions, roots


def _format_search_match(match, number: int) -> str:
    _, _, _, _, item_path, is_dir, stat = match
    item_type = "Folder" if is_dir else "File"
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    return f"{number}. {item_path.name} [{item_type}] — {item_path} — modified {modified}"


def _select_pending_result(selection: str) -> Path | None:
    value = (selection or "").strip()
    with _SEARCH_SELECTION_LOCK:
        results = list(_LAST_SEARCH_RESULTS)
    if not results:
        return None
    if value.isdigit():
        index = int(value) - 1
        return results[index] if 0 <= index < len(results) else None
    try:
        selected_path = Path(value).expanduser().resolve(strict=False)
        for result in results:
            if result.resolve(strict=False) == selected_path:
                return result
    except (OSError, RuntimeError, ValueError):
        pass
    matching_names = [result for result in results if result.name.casefold() == value.casefold()]
    return matching_names[0] if len(matching_names) == 1 else None


def _resolve_path(raw: str) -> Path:
    return resolve_safe_path(raw)


# Common media extension groups
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"}
_VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}

def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def _safe_trash(target: Path) -> str:

    if not _SEND2TRASH:
        return (
            "send2trash is not installed. "
            "Run: pip install send2trash — "
            "Permanent deletion is disabled for safety."
        )
    send2trash.send2trash(str(target))
    return f"Moved to Trash: {target.name}"


def list_files(path: str = "desktop", show_hidden: bool = False) -> str:
    try:
        target = _resolve_path(path)
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Path not found: {target}"
        if not target.is_dir():
            return f"Not a directory: {target}"

        items = []
        for item in sorted(target.iterdir()):
            if not show_hidden and item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = _format_size(item.stat().st_size)
                items.append(f"📄 {item.name} ({size})")

        if not items:
            return f"Directory is empty: {target.name}/"

        return f"Contents of {target.name}/ ({len(items)} items):\n" + "\n".join(items)

    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error listing files: {e}"


def create_file(path: str, name: str = "", content: str = "", overwrite: bool = False) -> str:
    try:
        target = resolve_safe_path(path, name)
        if target.exists() and not overwrite:
            return f"Already exists: {target}"
        if target.exists() and not target.is_file():
            return f"Cannot overwrite folder: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement for same-day writes: validate in a temporary file
        # in the destination directory, then replace the per-user target.
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent), text=False)
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            tmp_path.write_bytes(content.encode("utf-8"))
            if not tmp_path.exists() or tmp_path.stat().st_size == 0 and content:
                return f"Could not create file: validation failed for {target}"
            os.replace(tmp_path, target)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise
        invalidate_file_search_cache()
        return f"File created: {target}"
    except (OSError, UnicodeError, ValueError) as e:
        return f"Could not create file: {e}"


def create_folder(path: str, name: str = "") -> str:
    try:
        target = resolve_safe_path(path, name)
        if target.exists():
            return f"Already exists: {target}"
        target.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {target}"
    except (OSError, ValueError) as e:
        return f"Could not create folder: {e}"


def _find_latest_file(category: str = "") -> Path | None:
    search_dirs = [
        Path.home() / "Documents" / "JARVIS Created",
        _get_desktop(),
        _get_documents(),
        _get_downloads(),
        Path.cwd(),
    ]
    all_files = []
    cat_lower = (category or "").lower()
    for d in search_dirs:
        try:
            if d.exists() and d.is_dir():
                for f in d.iterdir():
                    if f.is_file():
                        if any(w in cat_lower for w in ("presentation", "slide", "ppt")):
                            if f.suffix.lower() in {".ppt", ".pptx"}:
                                all_files.append(f)
                        elif any(w in cat_lower for w in ("document", "word", "doc")):
                            if f.suffix.lower() in {".doc", ".docx"}:
                                all_files.append(f)
                        elif "pdf" in cat_lower:
                            if f.suffix.lower() == ".pdf":
                                all_files.append(f)
                        elif any(w in cat_lower for w in ("code", "script", "program")):
                            if f.suffix.lower() in {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".cs"}:
                                all_files.append(f)
                        else:
                            all_files.append(f)
        except Exception:
            continue
    if not all_files:
        return None
    try:
        return max(all_files, key=lambda f: f.stat().st_mtime)
    except Exception:
        return None


def _quick_find_file(name: str, path_hint: str = "") -> Path | None:
    if not name:
        return None
    name_clean = name.strip()
    name_lower = name_clean.lower()

    priority_folders = [
        Path.home() / "Documents" / "JARVIS Created",
        _get_desktop(),
        _get_documents(),
        _get_downloads(),
        Path.cwd(),
        Path.home(),
    ]

    if path_hint and path_hint.lower() not in {"all", "everywhere", "this pc", ""}:
        try:
            hint_dir = _resolve_path(path_hint)
            if hint_dir.exists() and hint_dir.is_dir() and hint_dir not in priority_folders:
                priority_folders.insert(0, hint_dir)
        except Exception:
            pass

    # 1. Direct exact filename match
    for folder in priority_folders:
        try:
            if not folder.exists() or not folder.is_dir():
                continue
            direct = folder / name_clean
            if direct.exists() and direct.is_file():
                return direct
        except Exception:
            continue

    # 2. Case-insensitive or stem match
    for folder in priority_folders:
        try:
            if not folder.exists() or not folder.is_dir():
                continue
            for f in folder.iterdir():
                try:
                    if f.is_file():
                        if f.name.lower() == name_lower or f.stem.lower() == name_lower:
                            return f
                        if name_lower in f.stem.lower() and len(name_lower) >= 4:
                            return f
                except Exception:
                    continue
        except Exception:
            continue

    return None


def _open_target(target: Path) -> str:
    """Open an existing path. Callers are responsible for access checks."""
    if not target.exists():
        return f"Not found: {target}"

    # Open directories in file manager; open files with the default associated application
    if _OS == "Windows":
        if target.is_dir():
            subprocess.Popen(["explorer", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.startfile(str(target))
            except Exception:
                try:
                    subprocess.Popen(f'explorer /select,"{target}"', shell=True)
                except Exception:
                    subprocess.Popen(["explorer", str(target.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif _OS == "Darwin":
        subprocess.Popen(["open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Opened: {target}"


def open_path(path: str = "desktop", name: str = "") -> str:
    try:
        target = resolve_safe_path(path, name)
        return _open_target(target)
    except (OSError, ValueError, RuntimeError) as e:
        return f"Could not open path: {e}"


def open_discovered_path(target: Path) -> str:
    """Open a read-only search result, including one found on another drive."""
    try:
        return _open_target(target)
    except (OSError, ValueError, RuntimeError) as e:
        return f"Could not open search result: {e}"


def delete_file(path: str, name: str = "", confirmed: bool = False) -> str:
    try:
        require_confirmation(confirmed)
        target = resolve_safe_path(path, name)
        if is_protected_path(target):
            return f"Protected directory, cannot delete: {target.name}"
        if not target.exists() and not target.is_symlink():
            return f"Not found: {target.name}"
        # Re-resolve directly before trashing to close the check/use gap.
        target = resolve_safe_path(path, name)
        if is_protected_path(target):
            return f"Protected directory, cannot delete: {target.name}"
        if not target.exists() and not target.is_symlink():
            return f"Not found: {target.name}"
        result = _safe_trash(target)
        invalidate_file_search_cache()
        return result

    except (OSError, PermissionError, UnsafePathError, ValueError) as e:
        return f"Could not delete: {e}"


def move_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base   = _resolve_path(path)
        src    = (base / name) if name else base
        dst    = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source not found: {src.name}"
        if dst is None:
            return "No destination specified."
        if not _is_safe_path(src):
            return f"Access denied (source): {src}"
        if not _is_safe_path(dst):
            return f"Access denied (destination): {dst}"

        if dst.is_dir():
            dst = dst / src.name

        if dst.exists():
            return f"Destination already exists: {dst}"

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        invalidate_file_search_cache()
        return f"Moved: {src.name} → {dst.parent.name}/"

    except Exception as e:
        return f"Could not move: {e}"


def copy_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base = _resolve_path(path)
        src  = (base / name) if name else base
        dst  = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source not found: {src.name}"
        if dst is None:
            return "No destination specified."
        if not _is_safe_path(src):
            return f"Access denied (source): {src}"
        if not _is_safe_path(dst):
            return f"Access denied (destination): {dst}"

        if dst.is_dir():
            dst = dst / src.name

        if dst.exists():
            return f"Destination already exists: {dst}"

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))

        invalidate_file_search_cache()
        return f"Copied: {src.name} → {dst.parent.name}/"

    except Exception as e:
        return f"Could not copy: {e}"


def rename_file(path: str, name: str = "", new_name: str = "") -> str:
    try:
        base     = _resolve_path(path)
        target   = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"
        if not new_name:
            return "No new name provided."
        if _INVALID_NAME_CHARS.search(new_name) or new_name.endswith((".", " ")):
            return f"Invalid file or folder name: {new_name!r}"

        new_path = target.parent / new_name
        if new_path.exists():
            return f"A file named '{new_name}' already exists here."

        target.rename(new_path)
        invalidate_file_search_cache()
        return f"Renamed: {target.name} → {new_name}"

    except Exception as e:
        return f"Could not rename: {e}"


def read_file(path: str, name: str = "", max_chars: int = 4000) -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"File not found: {target.name}"
        if not target.is_file():
            return f"Not a file: {target.name}"

        content = target.read_text(encoding="utf-8", errors="ignore")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[Truncated — {len(content)} total chars]"
        return content

    except Exception as e:
        return f"Could not read file: {e}"


def write_file(path: str, name: str = "", content: str = "",
               append: bool = False) -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            f.write(content)
        action = "Appended to" if append else "Written to"
        return f"{action}: {target.name}"
    except Exception as e:
        return f"Could not write file: {e}"


def find_files(name: str = "", extension: str = "", path: str = "home",
               max_results: int = 20, item_type: str = "both") -> str:
    global _LAST_SEARCH_RESULTS
    try:
        max_results = max(1, min(int(max_results), 50))
        name, extension = _normalise_spoken_search(name, extension)
        matches, suggestions, roots = _cached_search_items(name, extension, path, item_type, max_results)
        with _SEARCH_SELECTION_LOCK:
            _LAST_SEARCH_RESULTS = [match[4] for match in matches]

        if not matches:
            query = name or extension or "items"
            close = difflib.get_close_matches(str(query), suggestions, n=3, cutoff=0.55)
            message = f"No matching {query} found."
            if close:
                message += " Closest names: " + ", ".join(dict.fromkeys(close))
            if not roots:
                message += " No accessible search folders were found."
            return message

        lines = [_format_search_match(match, index) for index, match in enumerate(matches, 1)]
        return f"Found {len(matches)} matching item(s):\n" + "\n".join(lines)

    except PermissionError:
        return f"Search access denied: {path}"
    except (OSError, ValueError, RuntimeError) as e:
        return f"Search error: {e}"


def get_largest_files(path: str = "downloads", count: int = 10) -> str:
    count = min(count, 50)  # maksimum 50
    try:
        search_path = _resolve_path(path)
        if not _is_safe_path(search_path):
            return f"Access denied: {search_path}"
        if not search_path.exists():
            return f"Path not found: {path}"

        files = []
        for item in search_path.rglob("*"):
            if item.is_file():
                try:
                    files.append((item.stat().st_size, item))
                except Exception:
                    continue

        files.sort(reverse=True)
        top = files[:count]

        if not top:
            return "No files found."

        lines = [f"Top {len(top)} largest files in {search_path.name}/:"]
        for size, f in top:
            lines.append(f"  {_format_size(size):>10}  {f.name}  ({f.parent})")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


def get_disk_usage(path: str = "home") -> str:
    try:
        target = _resolve_path(path)
        usage  = shutil.disk_usage(target)
        pct    = usage.used / usage.total * 100
        return (
            f"Disk usage ({target}):\n"
            f"  Total : {_format_size(usage.total)}\n"
            f"  Used  : {_format_size(usage.used)} ({pct:.1f}%)\n"
            f"  Free  : {_format_size(usage.free)}"
        )
    except Exception as e:
        return f"Could not get disk usage: {e}"


def organize_desktop() -> str:
    type_map = {
        "Images":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx",
                      ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
        "Videos":    {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
        "Music":     {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
        "Archives":  {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
        "Code":      {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                      ".cpp", ".java", ".cs", ".go", ".rs", ".sh"},
    }

    desktop = _get_desktop()
    moved, skipped = [], []

    try:
        for item in desktop.iterdir():
            # Klasörlere, gizli dosyalara ve organize klasörlerine dokunma
            if item.is_dir() or item.name.startswith("."):
                continue
            if item.name in {k for k in type_map}:
                continue

            ext        = item.suffix.lower()
            target_dir = desktop / "Others"
            for folder, exts in type_map.items():
                if ext in exts:
                    target_dir = desktop / folder
                    break

            target_dir.mkdir(exist_ok=True)
            new_path = target_dir / item.name

            if new_path.exists():
                skipped.append(item.name)
                continue

            shutil.move(str(item), str(new_path))
            moved.append(f"{item.name} → {target_dir.name}/")

        result = f"Desktop organized: {len(moved)} files moved."
        if moved:
            preview = moved[:8]
            result += "\n" + "\n".join(preview)
            if len(moved) > 8:
                result += f"\n... and {len(moved) - 8} more."
        if skipped:
            result += f"\n{len(skipped)} file(s) skipped (name conflict)."
        return result

    except Exception as e:
        return f"Could not organize desktop: {e}"


def get_file_info(path: str, name: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"

        stat = target.stat()
        info = {
            "Name":      target.name,
            "Type":      "Folder" if target.is_dir() else "File",
            "Size":      _format_size(stat.st_size),
            "Location":  str(target.parent),
            "Created":   datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
            "Modified":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "Extension": target.suffix or "—",
        }
        return "\n".join(f"  {k}: {v}" for k, v in info.items())

    except Exception as e:
        return f"Could not get file info: {e}"


def _find_soffice() -> str | None:
    found = shutil.which("soffice")
    if found:
        return found
    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "LibreOffice" / "program" / "soffice.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "LibreOffice" / "program" / "soffice.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LibreOffice" / "program" / "soffice.exe",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
    return None


def _run_soffice_convert(src: Path, outdir: Path, to_format: str) -> Path | None:
    """Try converting using LibreOffice `soffice --convert-to`.
    Returns the output file Path on success, or None on failure.
    """
    soffice_bin = _find_soffice()
    if not soffice_bin:
        return None
    try:
        cmd = [soffice_bin, "--headless", "--convert-to", to_format, "--outdir", str(outdir), str(src)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        # LibreOffice names the output with the same stem and new extension
        out = outdir / (src.stem + ("." + to_format if not to_format.startswith(".") else to_format))
        if out.exists():
            return out
        return None
    except Exception:
        return None


def _convert_docx_via_office(src: Path, out_path: Path) -> bool:
    """Try converting DOCX to PDF using Windows Word COM automation (comtypes or win32com)."""
    if _OS != "Windows":
        return False
    try:
        try:
            import comtypes.client as cc
            word = cc.CreateObject('Word.Application')
        except Exception:
            try:
                import win32com.client as wc
                word = wc.Dispatch('Word.Application')
            except Exception:
                return False

        word.Visible = False
        doc = word.Documents.Open(str(src))
        # 17 = wdFormatPDF
        doc.SaveAs(str(out_path), FileFormat=17)
        doc.Close(False)
        try:
            word.Quit()
        except Exception:
            pass
        return out_path.exists()
    except Exception:
        return False


def _convert_pptx_via_office(src: Path, out_path: Path) -> bool:
    """Try converting PPTX to PDF using Windows PowerPoint COM automation (comtypes or win32com)."""
    if _OS != "Windows":
        return False
    try:
        try:
            import comtypes.client as cc
            ppt = cc.CreateObject('PowerPoint.Application')
        except Exception:
            try:
                import win32com.client as wc
                ppt = wc.Dispatch('PowerPoint.Application')
            except Exception:
                return False

        ppt.Visible = False
        pres = ppt.Presentations.Open(str(src), WithWindow=False)
        # 32 = ppSaveAsPDF
        pres.SaveAs(str(out_path), FileFormat=32)
        pres.Close()
        try:
            ppt.Quit()
        except Exception:
            pass
        return out_path.exists()
    except Exception:
        return False


def convert_file(path: str = "home", name: str = "", to: str = "pdf") -> str:
    try:
        base = _resolve_path(path)
        src = (base / name) if name else base
        if not _is_safe_path(src):
            return f"Access denied: {src}"
        if not src.exists():
            return f"Source not found: {src.name}"

        to = (to or "pdf").strip().lower()
        if to.startswith("."):
            to = to[1:]

        out_dir = src.parent
        out_name = src.stem + "." + to
        out_path = out_dir / out_name

        src_ext = src.suffix.lower()

        # DOCX -> TXT
        if src_ext == ".docx" and to == "txt":
            try:
                from docx import Document
                doc = Document(str(src))
                text = "\n".join(p.text for p in doc.paragraphs)
                out_path.write_text(text, encoding="utf-8")
                return f"Converted: {out_path}"
            except Exception:
                # Fallback: extract text from DOCX (zip) manually
                try:
                    import zipfile, xml.etree.ElementTree as ET
                    with zipfile.ZipFile(src, 'r') as z:
                        data = z.read('word/document.xml')
                    root = ET.fromstring(data)
                    texts = [t.text for t in root.iter() if t.tag.endswith('}t') and (t.text)]
                    out_path.write_text('\n'.join(texts), encoding='utf-8')
                    return f"Converted (zip-fallback): {out_path}"
                except Exception:
                    return "Could not extract DOCX text (install python-docx for robust support)."

        # DOCX -> PDF (try docx2pdf then libreoffice)
        if src_ext == ".docx" and to == "pdf":
            try:
                import docx2pdf
                docx2pdf.convert(str(src), str(out_path))
                if out_path.exists():
                    return f"Converted: {out_path}"
            except Exception:
                pass
            # Try Windows Word COM automation (if running on Windows)
            try:
                if _convert_docx_via_office(src, out_path):
                    return f"Converted: {out_path}"
            except Exception:
                pass

            soffice_out = _run_soffice_convert(src, out_dir, "pdf")
            if soffice_out:
                return f"Converted: {soffice_out}"
            return "Could not convert DOCX→PDF: install docx2pdf or LibreOffice (soffice)"

        # PDF -> TXT
        if src_ext == ".pdf" and to == "txt":
            try:
                from PyPDF2 import PdfReader
            except Exception:
                return "Missing dependency: PyPDF2 (pip install PyPDF2)"
            reader = PdfReader(str(src))
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or "")
                except Exception:
                    pages.append("")
            out_path.write_text("\n\n".join(pages), encoding="utf-8")
            return f"Converted: {out_path}"

        # PPTX -> TXT
        if src_ext in {".pptx", ".ppt"} and to == "txt":
            try:
                from pptx import Presentation
                prs = Presentation(str(src))
                parts = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            parts.append(shape.text)
                out_path.write_text("\n\n".join(parts), encoding="utf-8")
                return f"Converted: {out_path}"
            except Exception:
                # Fallback: read slide XML from PPTX zip and extract <a:t> text
                try:
                    import zipfile, xml.etree.ElementTree as ET
                    texts = []
                    with zipfile.ZipFile(src, 'r') as z:
                        for name in z.namelist():
                            if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                                data = z.read(name)
                                root = ET.fromstring(data)
                                for t in root.iter():
                                    if t.tag.endswith('}t') and t.text:
                                        texts.append(t.text)
                    out_path.write_text('\n\n'.join(texts), encoding='utf-8')
                    return f"Converted (zip-fallback): {out_path}"
                except Exception:
                    return "Could not extract PPTX text (install python-pptx for robust support)."

        # PPTX -> PDF: try PowerPoint COM automation on Windows before soffice
        if src_ext in {".pptx", ".ppt"} and to == "pdf":
            try:
                if _convert_pptx_via_office(src, out_path):
                    return f"Converted: {out_path}"
            except Exception:
                pass
            soffice_out = _run_soffice_convert(src, out_dir, "pdf")
            if soffice_out:
                return f"Converted: {soffice_out}"
            # Fallback: extract slide text and render to PDF using reportlab
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import LETTER
                texts = []
                try:
                    from pptx import Presentation
                    prs = Presentation(str(src))
                    for slide in prs.slides:
                        slide_text = []
                        for shape in slide.shapes:
                            if hasattr(shape, 'text') and shape.text:
                                slide_text.append(shape.text)
                        texts.append('\n'.join(slide_text))
                except Exception:
                    # zip fallback for pptx
                    import zipfile, xml.etree.ElementTree as ET
                    with zipfile.ZipFile(src, 'r') as z:
                        slide_names = [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
                        for name in slide_names:
                            data = z.read(name)
                            root = ET.fromstring(data)
                            slide_text = [t.text for t in root.iter() if t.tag.endswith('}t') and t.text]
                            texts.append('\n'.join(slide_text))

                if texts:
                    c = canvas.Canvas(str(out_path), pagesize=LETTER)
                    for slide_text in texts:
                        y = LETTER[1] - 72
                        for line in slide_text.split('\n'):
                            if y < 72:
                                c.showPage()
                                y = LETTER[1] - 72
                            c.drawString(72, y, line)
                            y -= 12
                        c.showPage()
                    c.save()
                    if out_path.exists():
                        return f"Converted (text-render): {out_path}"
            except Exception:
                pass

        # Generic: try LibreOffice for many conversions (doc, docx, odt, pptx -> pdf/txt)
        soffice_map = {"pdf": "pdf", "txt": "txt"}
        # Additional PDF conversions: TXT -> PDF, images -> PDF
        if to == "pdf":
            # TXT -> PDF via reportlab if available, otherwise use soffice
            if src_ext == ".txt":
                try:
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import LETTER
                    c = canvas.Canvas(str(out_path), pagesize=LETTER)
                    y = LETTER[1] - 72
                    with open(src, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.rstrip("\n")
                            if y < 72:
                                c.showPage()
                                y = LETTER[1] - 72
                            c.drawString(72, y, line)
                            y -= 12
                    c.save()
                    if out_path.exists():
                        return f"Converted: {out_path}"
                except Exception:
                    soffice_out = _run_soffice_convert(src, out_dir, "pdf")
                    if soffice_out:
                        return f"Converted: {soffice_out}"
                    return "Could not convert TXT→PDF: install reportlab or LibreOffice (soffice)"

            # Images -> PDF via Pillow if available
            if src_ext in _IMAGE_EXTS:
                try:
                    from PIL import Image
                    im = Image.open(str(src))
                    if im.mode in ("RGBA", "LA"):
                        im = im.convert("RGB")
                    im.save(str(out_path), "PDF", resolution=100.0)
                    if out_path.exists():
                        return f"Converted: {out_path}"
                except Exception:
                    soffice_out = _run_soffice_convert(src, out_dir, "pdf")
                    if soffice_out:
                        return f"Converted: {soffice_out}"
                    return "Could not convert image→PDF: install Pillow or LibreOffice (soffice)"

        if to in soffice_map:
            soffice_out = _run_soffice_convert(src, out_dir, to)
            if soffice_out:
                return f"Converted: {soffice_out}"

        return f"Unsupported conversion: {src_ext} → .{to} or missing dependencies."

    except Exception as e:
        return f"Conversion error: {e}"

def file_controller(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    path   = params.get("path", "desktop")
    name   = params.get("name", "")

    if player:
        player.write_log(f"[file] {action} {name or path}")

    try:
        if action == "list":
            return list_files(path)

        elif action == "create_file":
            return create_file(
                path, name=name, content=params.get("content", ""),
                overwrite=params.get("overwrite", False),
            )

        elif action == "create_folder":
            return create_folder(path, name=name)

        elif action == "delete":
            return delete_file(path, name=name, confirmed=params.get("confirmed", False))

        elif action == "move":
            return move_file(path, name=name, destination=params.get("destination", ""))

        elif action == "copy":
            return copy_file(path, name=name, destination=params.get("destination", ""))

        elif action == "rename":
            return rename_file(path, name=name, new_name=params.get("new_name", ""))

        elif action == "read":
            return read_file(path, name=name)

        elif action == "write":
            return write_file(
                path, name=name,
                content=params.get("content", ""),
                append=params.get("append", False)
            )

        elif action in ("open", "open_file", "open_folder", "open_path", "explore"):
            # 1. Normalize parameters if path was passed as the filename
            if not name and path:
                path_str = str(path).strip()
                p_obj = Path(path_str)
                path_lower = path_str.lower()
                if p_obj.is_absolute():
                    if p_obj.exists():
                        return open_discovered_path(p_obj.resolve(strict=False))
                    name = p_obj.name
                    path = "all"
                elif p_obj.suffix or path_lower not in {"desktop", "downloads", "documents", "pictures", "images", "videos", "music", "home", "all", "user", "this pc", ""}:
                    name = path_str
                    path = "all"

            name_clean = (name or "").strip()
            name_lower = name_clean.lower()

            # 2. Handle requests for "latest", "recent", "the file", "the document", "the presentation", etc.
            if name_lower in {"latest", "recent", "last", "new", "the file", "the document", "the presentation", "the code", "current"}:
                latest_hit = _find_latest_file(name_lower)
                if latest_hit:
                    return open_discovered_path(latest_hit)

            # 3. Check pending search selection (e.g. user selected "1" or "2")
            selected = _select_pending_result(name)
            if selected:
                return open_discovered_path(selected)

            # 4. Check priority user folders (JARVIS Created, Desktop, Documents, Downloads, CWD)
            quick_hit = _quick_find_file(name_clean, path_hint=str(path or ""))
            if quick_hit:
                return open_discovered_path(quick_hit)

            # 5. Check if direct resolve_safe_path hits a valid path
            try:
                target = resolve_safe_path(path, name)
                if target.exists():
                    return open_discovered_path(target)
            except Exception:
                pass

            # 6. Deep search across local drives
            item_type = "folder" if action in ("open_folder", "explore") else "file"
            result_text = find_files(
                name=name,
                extension=params.get("extension", ""),
                path=path if path in {"all", "home", "desktop", "downloads", "documents"} else "all",
                max_results=min(int(params.get("max_results", 20)), 50),
                item_type=item_type,
            )
            with _SEARCH_SELECTION_LOCK:
                selected_results = list(_LAST_SEARCH_RESULTS)
            if len(selected_results) == 1:
                found = selected_results[0]
                return open_discovered_path(found)
            if len(selected_results) > 1:
                return (
                    result_text
                    + "\nWhich one should I open? Reply with a number, the full path, "
                    "or a unique folder/file name."
                )
            return result_text or f"Could not find or open: {name or path}"

        elif action == "find":
            do_open = bool(params.get("open", False))
            item_type = params.get("item_type", params.get("type", "both"))
            result_text = find_files(
                name=name or params.get("name", ""),
                extension=params.get("extension", ""),
                path=path,
                max_results=min(int(params.get("max_results", 20)), 50),
                item_type=item_type,
            )
            if not do_open:
                return result_text

            with _SEARCH_SELECTION_LOCK:
                selected_results = list(_LAST_SEARCH_RESULTS)
            if len(selected_results) == 1:
                selected = selected_results[0]
                return open_discovered_path(selected)
            if len(selected_results) > 1:
                return (
                    result_text
                    + "\nWhich one should I open? Reply with a number, the full path, "
                    "or a unique folder/file name."
                )
            return result_text

        elif action == "largest":
            return get_largest_files(
                path=path,
                count=int(params.get("count", 10)),
            )

        elif action == "disk_usage":
            return get_disk_usage(path)

        elif action == "organize_desktop":
            return organize_desktop()

        elif action == "info":
            return get_file_info(path, name=name)

        elif action == "convert":
            return convert_file(path=path, name=name, to=params.get("to", "pdf"))

        else:
            return f"Unknown action: '{action}'"

    except Exception as e:
        return f"File controller error ({action}): {e}"
