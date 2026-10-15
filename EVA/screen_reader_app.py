#!/usr/bin/env python3
"""Standalone screen reader app for Mark-L / EVA.

This utility captures the visible screen or background window, runs OCR if the system
has Tesseract installed, and prints readable text in the terminal.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import mss
    import mss.tools
except ImportError:
    mss = None

try:
    from PIL import Image
except ImportError:
    Image = None


def _get_background_window_rect() -> dict | None:
    """Locate bounding box of active window behind reader terminal/JARVIS."""
    if sys.platform != "win32":
        return None
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        title = (win32gui.GetWindowText(hwnd) or "").lower()
        if any(k in title for k in ["jarvis", "mark", "eva", "screen_reader", "python", "cmd", "powershell"]):
            curr = hwnd
            for _ in range(25):
                curr = win32gui.GetWindow(curr, 2)  # GW_HWNDNEXT
                if not curr:
                    break
                try:
                    if win32gui.IsWindowVisible(curr):
                        rect = win32gui.GetWindowRect(curr)
                        w, h = rect[2] - rect[0], rect[3] - rect[1]
                        t = (win32gui.GetWindowText(curr) or "").lower()
                        if w > 200 and h > 200 and "program manager" not in t and "desktop" not in t:
                            hwnd = curr
                            break
                except Exception:
                    continue

        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if w > 100 and h > 100:
            return {"left": max(0, rect[0]), "top": max(0, rect[1]), "width": w, "height": h}
    except Exception:
        pass
    return None


def _capture_screen(path: Path, monitor_index: int = 1, crop_bg: bool = True) -> Path:
    """Capture the background window or screen area and save it as a PNG for OCR."""
    if mss is None:
        raise RuntimeError("mss is not installed. Run: pip install mss pillow")

    mss_cls = getattr(mss, "MSS", mss.mss)
    with mss_cls() as sct:
        target_rect = _get_background_window_rect() if crop_bg else None
        if target_rect:
            screenshot = sct.grab(target_rect)
        else:
            monitors = sct.monitors
            if monitor_index >= len(monitors):
                monitor_index = 1 if len(monitors) > 1 else 0
            target = monitors[monitor_index]
            screenshot = sct.grab(target)

    if Image is None:
        raise RuntimeError("Pillow is not installed. Run: pip install pillow")

    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    img = img.convert("RGB")
    img.save(path, format="PNG")
    return path


def _find_tesseract() -> str | None:
    """Locate tesseract binary via PATH or standard Windows install directories."""
    tesseract = shutil.which("tesseract")
    if tesseract:
        return tesseract

    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
    ]
    for p in possible_paths:
        if Path(p).exists():
            return p
    return None


def _ocr_image(image_path: Path, language: str = "eng") -> str:
    """Return OCR text for an image path, safely decoding raw output."""
    tesseract = _find_tesseract()
    if not tesseract:
        return ""

    try:
        proc = subprocess.run(
            [tesseract, str(image_path), "stdout", "--psm", "6", "-l", language],
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            raw = proc.stdout
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="replace").strip()
            return str(raw).strip()
    except Exception:
        return ""

    return ""


def _speak_text(text: str) -> None:
    """Best-effort Windows text-to-speech using the OS SpeechSynthesizer."""
    if shutil.which("powershell") is None:
        return
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = 0; $s.Volume = 100; $s.Speak(\"" + text.replace('"', '\"') + "\"); "
        ]
        subprocess.run(cmd, check=False, capture_output=True, text=True)
    except Exception:
        return


def read_once(output_path: Path | None = None, speak: bool = False, language: str = "eng") -> str:
    image_path = Path("screen_reader_capture.png")
    _capture_screen(image_path)
    text = _ocr_image(image_path, language=language)

    if not text:
        text = "No readable text found on the screen."

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")

    print("\n[Screen Reader] Extracted text:\n")
    print(text)

    if speak:
        _speak_text(text)

    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standalone screen OCR reader for Mark-L / EVA.")
    parser.add_argument("--interval", type=float, default=0.0,
                        help="Seconds between screen reads. 0 means one-shot mode.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional output file for the extracted screen text.")
    parser.add_argument("--speak", action="store_true",
                        help="Speak the extracted text using Windows SpeechSynthesizer if available.")
    parser.add_argument("--language", default="eng",
                        help="Tesseract language code, e.g. eng, deu, spa.")
    parser.add_argument("--monitor", type=int, default=1,
                        help="Monitor index to inspect; default 1 for secondary/primary.")
    args = parser.parse_args(argv)

    print("[Screen Reader] Starting. Independent from the main UI window.")
    tess_path = _find_tesseract()
    if tess_path is None:
        print("[Screen Reader] Tesseract not found — OCR text extraction will be unavailable.")
    else:
        print(f"[Screen Reader] Tesseract detected at: {tess_path}")

    if args.interval <= 0:
        read_once(output_path=args.output, speak=args.speak, language=args.language)
        return 0

    try:
        while True:
            read_once(output_path=args.output, speak=args.speak, language=args.language)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[Screen Reader] Stopped.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[Screen Reader] Fatal error: {exc}", file=sys.stderr)
        raise SystemExit(1)
