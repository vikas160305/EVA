import json
import os
import re
import struct
from typing import Optional
import subprocess
import sys
import time
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.06
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_os() -> str:
    try:
        cfg = json.loads(
            (_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8")
        )
        return cfg.get("os_system", "windows").lower()
    except Exception:
        return "windows"


def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def _paste_text(text: str) -> None:
    _require_pyautogui()

    os_name = _get_os()
    paste_hotkey = ("command", "v") if os_name == "mac" else ("ctrl", "v")

    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey(*paste_hotkey)
        time.sleep(0.1)
    else:
        pyautogui.write(text, interval=0.03)


def _clear_and_paste(text: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
    pyautogui.hotkey(*select_all)
    time.sleep(0.1)
    pyautogui.press("delete")
    time.sleep(0.1)
    _paste_text(text)

def _open_app(app_name: str) -> bool:
    _require_pyautogui()
    os_name = _get_os()

    try:
        if os_name == "windows":
            pyautogui.press("win")
            time.sleep(0.5)
            _paste_text(app_name)
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(2.5)
            return True

        elif os_name == "mac":
            result = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["open", "-a", f"{app_name}.app"],
                    capture_output=True, text=True, timeout=10,
                )
            time.sleep(2.5)
            return result.returncode == 0

        else: 
            launched = False
            for launcher in [
                ["gtk-launch", app_name.lower()],
                [app_name.lower()],
            ]:
                try:
                    subprocess.Popen(
                        launcher,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            time.sleep(2.5)
            return launched

    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not open {app_name}: {e}")
        return False


def _open_browser_url(url: str) -> bool:
    import webbrowser
    try:
        webbrowser.open(url)
        time.sleep(4.0) 
        return True
    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not open browser: {e}")
        return False

def _search_in_app(query: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    search_hotkey = ("command", "f") if os_name == "mac" else ("ctrl", "f")

    pyautogui.hotkey(*search_hotkey)
    time.sleep(0.5)
    _clear_and_paste(query)
    time.sleep(1.0)

def _copy_file_to_clipboard(file_path: Path) -> bool:
    """Copy file to Windows/Mac clipboard using CF_HDROP format."""
    if not file_path.exists():
        return False

    os_name = _get_os()
    if os_name == "windows":
        try:
            import win32clipboard
            import win32con

            resolved_str = str(file_path.resolve())
            files_bytes = resolved_str.encode("utf-16le") + b"\x00\x00\x00\x00"
            dropfiles = struct.pack("IIIIi", 20, 0, 0, 0, 1) + files_bytes

            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_HDROP, dropfiles)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            print(f"[SendMessage] win32clipboard fallback: {e}")

        try:
            resolved_str = str(file_path.resolve()).replace('"', '`"')
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f'Set-Clipboard -Path "{resolved_str}"'],
                check=True,
                capture_output=True,
                timeout=6
            )
            return True
        except Exception as e:
            print(f"[SendMessage] PowerShell Set-Clipboard error: {e}")
            return False

    elif os_name == "mac":
        try:
            script = f'set the clipboard to (POSIX file "{file_path.resolve()}")'
            subprocess.run(["osascript", "-e", script], check=True, timeout=5)
            return True
        except Exception as e:
            print(f"[SendMessage] Mac clipboard error: {e}")
            return False

    return False


def _resolve_media_file(target: str) -> Optional[Path]:
    """Find the requested file, image, or video path on disk."""
    if not target:
        return None

    raw = target.strip().strip('"\'')
    p = Path(raw).expanduser()
    if p.is_file():
        return p

    user_home = Path.home()
    userprofile = os.environ.get("USERPROFILE")
    onedrive = Path(userprofile) / "OneDrive" if userprofile else None

    search_dirs = [
        user_home / "Downloads" / "EVA Downloads",
        user_home / "Pictures" / "EVA Images",
        user_home / "Videos" / "EVA Videos",
        user_home / "Documents" / "EVA Documents",
        user_home / "Downloads" / "EVA Datasets",
        user_home / "Downloads" / "EVA Code",
        user_home / "Downloads",
        user_home / "Pictures",
        user_home / "Videos",
        user_home / "Documents",
        user_home / "Desktop",
    ]
    if onedrive and onedrive.exists():
        search_dirs.extend([
            onedrive / "Pictures" / "EVA Images",
            onedrive / "Documents" / "EVA Documents",
            onedrive / "Pictures",
            onedrive / "Documents",
            onedrive / "Desktop",
        ])

    for d in search_dirs:
        if not d.exists():
            continue
        candidate = d / raw
        if candidate.is_file():
            return candidate

    raw_lower = raw.lower()
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    video_exts = {".mp4", ".mkv", ".webm", ".avi", ".mov"}

    if any(k in raw_lower for k in ("recent image", "last image", "downloaded image", "the image", "image")):
        for d in [user_home / "Pictures" / "EVA Images", user_home / "Downloads", user_home / "Pictures"]:
            if d.exists():
                images = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in image_exts]
                if images:
                    images.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    return images[0]

    if any(k in raw_lower for k in ("recent video", "last video", "downloaded video", "the video", "video")):
        for d in [user_home / "Videos" / "EVA Videos", user_home / "Downloads", user_home / "Videos"]:
            if d.exists():
                videos = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in video_exts]
                if videos:
                    videos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    return videos[0]

    if any(k in raw_lower for k in ("recent file", "last file", "downloaded file", "the file", "recent document")):
        for d in [user_home / "Downloads" / "EVA Downloads", user_home / "Downloads", user_home / "Documents"]:
            if d.exists():
                files = [f for f in d.iterdir() if f.is_file()]
                if files:
                    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    return files[0]

    search_keywords = [w for w in re.split(r'[\s_\-\.]+', raw_lower) if len(w) >= 3 and w not in ("send", "file", "image", "video", "whatsapp", "the")]
    if search_keywords:
        for d in search_dirs:
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.is_file():
                    fname_lower = f.name.lower()
                    if all(k in fname_lower for k in search_keywords):
                        return f

    return None


def _open_whatsapp() -> bool:
    """Launch or focus WhatsApp Desktop application."""
    os_name = _get_os()
    if os_name == "windows":
        try:
            subprocess.Popen("start whatsapp:", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2.0)
            return True
        except Exception as e:
            print(f"[SendMessage] WhatsApp protocol error: {e}")
    return _open_app("WhatsApp")


def _desktop_send_media(app_name: str, receiver: str, file_path: Path, caption: str = "") -> str:
    """Send an attached file, image, or video to a recipient on desktop messaging app."""
    _require_pyautogui()

    if app_name.lower() == "whatsapp":
        if not _open_whatsapp():
            return "Could not open WhatsApp Desktop."
    else:
        if not _open_app(app_name):
            return f"Could not open {app_name}."

    time.sleep(1.0)
    _search_in_app(receiver)
    pyautogui.press("enter")
    time.sleep(1.2)

    if not _copy_file_to_clipboard(file_path):
        return f"Could not copy file '{file_path.name}' to clipboard."

    time.sleep(0.3)
    os_name = _get_os()
    paste_hotkey = ("command", "v") if os_name == "mac" else ("ctrl", "v")
    pyautogui.hotkey(*paste_hotkey)

    time.sleep(1.5)

    if caption:
        _paste_text(caption)
        time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.5)

    return f"Successfully sent {file_path.name} to {receiver} via {app_name}."


def _desktop_send(app_name: str, receiver: str, message: str) -> str:
    if not _open_app(app_name):
        return f"Could not open {app_name}."

    time.sleep(1.0)
    _search_in_app(receiver)
    pyautogui.press("enter")
    time.sleep(0.8)

    _paste_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)
    return f"Message sent to {receiver} via {app_name}."

def _send_whatsapp(receiver: str, message: str = "", file_path: Optional[str] = None) -> str:
    if file_path:
        target = _resolve_media_file(file_path)
        if not target:
            return f"Could not find file '{file_path}' to send on WhatsApp."
        return _desktop_send_media("WhatsApp", receiver, target, caption=message)
    return _desktop_send("WhatsApp", receiver, message)

def _send_telegram(receiver: str, message: str = "", file_path: Optional[str] = None) -> str:
    if file_path:
        target = _resolve_media_file(file_path)
        if target:
            return _desktop_send_media("Telegram", receiver, target, caption=message)
    return _desktop_send("Telegram", receiver, message)

def _send_signal(receiver: str, message: str) -> str:
    return _desktop_send("Signal", receiver, message)


def _send_discord(receiver: str, message: str = "", file_path: Optional[str] = None) -> str:
    if file_path:
        target = _resolve_media_file(file_path)
        if target:
            return _desktop_send_media("Discord", receiver, target, caption=message)
    return _desktop_send("Discord", receiver, message)


def _send_instagram(receiver: str, message: str) -> str:
    _require_pyautogui()

    if not _open_browser_url("https://www.instagram.com/direct/new/"):
        return "Could not open Instagram in browser."

    _paste_text(receiver)
    time.sleep(1.5)

    pyautogui.press("down")
    time.sleep(0.3)
    pyautogui.press("enter")   
    time.sleep(0.4)

    for _ in range(4):
        pyautogui.press("tab")
        time.sleep(0.15)
    pyautogui.press("enter")
    time.sleep(2.0)

    _paste_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)

    return f"Message sent to {receiver} via Instagram."


def _send_messenger(receiver: str, message: str) -> str:
    _require_pyautogui()

    if not _open_browser_url("https://www.messenger.com/"):
        return "Could not open Messenger in browser."


    _search_in_app(receiver)
    time.sleep(0.5)
    pyautogui.press("down")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(1.0)

    _paste_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)

    return f"Message sent to {receiver} via Messenger."

_PLATFORM_MAP = [
    ({"whatsapp", "wp", "wapp"},              _send_whatsapp),
    ({"telegram", "tg"},                      _send_telegram),
    ({"instagram", "ig", "insta"},            _send_instagram),
    ({"signal"},                               _send_signal),
    ({"discord"},                              _send_discord),
    ({"messenger", "facebook", "fb"},         _send_messenger),
]


def _resolve_platform(platform_str: str):
    key = platform_str.lower().strip()
    for keywords, handler in _PLATFORM_MAP:
        if any(k in key for k in keywords):
            return handler
    return lambda r, m: _desktop_send(platform_str.strip().title(), r, m)


def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params       = parameters or {}
    receiver     = str(params.get("receiver") or params.get("contact") or params.get("to") or "").strip()
    message_text = str(params.get("message_text") or params.get("message") or params.get("caption") or params.get("text") or "").strip()
    file_path    = str(params.get("file_path") or params.get("file") or params.get("image") or params.get("video") or params.get("media") or params.get("attachment") or "").strip()
    platform     = params.get("platform", "whatsapp").strip()

    if not receiver:
        return "Please specify a recipient."
    if not message_text and not file_path:
        return "Please specify a message text or a file to send."
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed — cannot control the desktop."

    preview = (message_text[:50] + ("…" if len(message_text) > 50 else "")) if message_text else f"file: {file_path}"
    print(f"[SendMessage] 📨 {platform} → {receiver}: {preview}")
    if player:
        player.write_log(f"[msg] {platform} → {receiver}")

    try:
        handler = _resolve_platform(platform)
        try:
            result  = handler(receiver, message_text, file_path=file_path)
        except TypeError:
            result  = handler(receiver, message_text)
    except Exception as e:
        result = f"Could not send message: {e}"

    print(f"[SendMessage] {'✅' if 'sent' in result.lower() else '❌'} {result}")
    if player:
        player.write_log(f"[msg] {result}")

    return result