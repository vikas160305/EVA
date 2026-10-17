import os
import re
import sys
import time
import shutil
import platform
import subprocess
from typing import Optional, Tuple, List, Dict

_SYSTEM = platform.system()

_CNW: dict = (
    {"creationflags": subprocess.CREATE_NO_WINDOW}
    if _SYSTEM == "Windows" else {}
)

def _clean_app_name(raw: str) -> str:
    """Normalize user input to extract clean application name.
    
    Examples:
        'download VLC from Microsoft Store' -> 'VLC'
        'install WhatsApp from store' -> 'WhatsApp'
        'get Spotify app' -> 'Spotify'
    """
    if not raw:
        return ""
    text = raw.strip()
    
    # Remove leading action verbs
    text = re.sub(r"^(?:download|install|get|fetch|setup|open)\s+", "", text, flags=re.IGNORECASE)
    
    # Remove store qualifiers
    text = re.sub(
        r"\s+(?:from|in|on|via)\s+(?:the\s+)?(?:microsoft\s+store|windows\s+store|ms\s+store|app\s+store|store)$",
        "", text, flags=re.IGNORECASE
    )
    text = re.sub(
        r"^(?:microsoft\s+store|windows\s+store|ms\s+store|store)\s+(?:for\s+)?",
        "", text, flags=re.IGNORECASE
    )
    
    # Remove trailing 'app' or 'application'
    text = re.sub(r"\s+(?:app|application|software|program)$", "", text, flags=re.IGNORECASE)
    
    # Strip quotes
    text = text.strip("\"' ")
    return text


def _is_winget_available() -> bool:
    """Check if winget CLI is accessible."""
    return shutil.which("winget") is not None or shutil.which("winget.exe") is not None


def _parse_winget_table(output: str) -> List[Dict[str, str]]:
    """Parse table output from `winget search` into list of dicts.
    
    Table format:
    Name     Id           Version  Match  Source
    --------------------------------------------
    WhatsApp 9NKSQGP7F2NH Unknown         msstore
    """
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if not lines:
        return []
        
    header_idx = -1
    for i, line in enumerate(lines):
        if "---" in line and i > 0:
            header_idx = i - 1
            break
            
    if header_idx == -1 or header_idx + 1 >= len(lines):
        return []

    header = lines[header_idx]
    separator = lines[header_idx + 1]

    # Find column start positions based on header text
    col_names = ["Name", "Id", "Version", "Match", "Source"]
    col_positions = []
    for col in col_names:
        pos = header.find(col)
        if pos != -1:
            col_positions.append((pos, col.lower()))
    col_positions.sort()

    results = []
    for line in lines[header_idx + 2:]:
        if not line.strip() or line.startswith("-"):
            continue
        entry = {}
        for idx, (start, col_name) in enumerate(col_positions):
            end = col_positions[idx + 1][0] if idx + 1 < len(col_positions) else len(line)
            entry[col_name] = line[start:end].strip() if start < len(line) else ""
        if entry.get("name") and entry.get("id"):
            results.append(entry)
            
    return results


def _search_msstore_winget(query: str) -> List[Dict[str, str]]:
    """Search Microsoft Store via winget."""
    if not _is_winget_available():
        return []
    try:
        cmd = ["winget", "search", query, "--source", "msstore", "--accept-source-agreements"]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=25,
            **_CNW
        )
        return _parse_winget_table(proc.stdout)
    except Exception as e:
        print(f"[install_app] winget msstore search failed: {e}")
        return []


def _search_all_winget(query: str) -> List[Dict[str, str]]:
    """Search all configured winget sources."""
    if not _is_winget_available():
        return []
    try:
        cmd = ["winget", "search", query, "--accept-source-agreements"]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=25,
            **_CNW
        )
        return _parse_winget_table(proc.stdout)
    except Exception as e:
        print(f"[install_app] winget search failed: {e}")
        return []


def _find_best_match(query: str, items: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Select the best matching package from search results."""
    if not items:
        return None
    q = query.lower()
    # Exact name match
    for item in items:
        if item.get("name", "").lower() == q:
            return item
    # Name starts with query
    for item in items:
        if item.get("name", "").lower().startswith(q):
            return item
    # Query in name
    for item in items:
        if q in item.get("name", "").lower():
            return item
    # Fallback to first item
    return items[0]


def _check_already_installed_winget(app_name: str) -> Tuple[bool, str]:
    """Check if app is already installed via winget list."""
    if not _is_winget_available():
        return False, ""
    try:
        cmd = ["winget", "list", app_name, "--accept-source-agreements"]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=15,
            **_CNW
        )
        if proc.returncode == 0:
            entries = _parse_winget_table(proc.stdout)
            match = _find_best_match(app_name, entries)
            if match:
                return True, match.get("name", app_name)
    except Exception:
        pass
    return False, ""


def _open_store_ui(query_or_id: str, is_product_id: bool = False) -> bool:
    """Launch Microsoft Store directly using Windows URI protocol."""
    if _SYSTEM != "Windows":
        return False
    try:
        if is_product_id:
            uri = f"ms-windows-store://pdp/?productid={query_or_id}"
        else:
            # Query string
            safe_query = query_or_id.replace(" ", "%20")
            uri = f"ms-windows-store://search/?query={safe_query}"
        
        subprocess.Popen(
            f'start "" "{uri}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_CNW
        )
        return True
    except Exception as e:
        print(f"[install_app] Failed to open Microsoft Store URI: {e}")
        return False


def _launch_app_if_possible(app_name: str) -> None:
    """Attempt to launch the installed app."""
    try:
        from actions.open_app import open_app
        open_app(parameters={"app_name": app_name})
    except Exception as e:
        print(f"[install_app] Post-install launch failed: {e}")


def install_app(
    parameters: Optional[dict] = None,
    player=None,
    speak=None,
) -> str:
    """Download and install an application, prioritizing Microsoft Store.
    
    Parameters:
        app_name (str): The name or search term of the application.
        source (str): 'msstore' | 'winget' | 'auto' (default: 'msstore').
        launch_after (bool): Launch the application after successful installation.
    """
    params = parameters or {}
    raw_name = params.get("app_name", "").strip()
    source_pref = (params.get("source") or "msstore").lower().strip()
    launch_after = params.get("launch_after", True)
    
    if not raw_name:
        return "Please specify the application you would like to download or install."

    clean_name = _clean_app_name(raw_name)
    if not clean_name:
        clean_name = raw_name

    msg_init = f"Searching Microsoft Store for '{clean_name}'..."
    print(f"[install_app] {msg_init}")
    if player:
        player.write_log(f"SYS: {msg_init}")

    if _SYSTEM != "Windows":
        # Fallback for non-Windows systems
        if _SYSTEM == "Darwin":
            try:
                subprocess.Popen(["open", f"macappstore://showPage?title=search&query={clean_name}"])
                return f"Opened Mac App Store for '{clean_name}'."
            except Exception:
                return f"Application installation via App Store is only supported on Windows or macOS."
        elif _SYSTEM == "Linux":
            try:
                subprocess.Popen(["gnome-software", f"--search={clean_name}"])
                return f"Opened Software Center for '{clean_name}'."
            except Exception:
                return f"Please use your package manager (apt/snap/flatpak) to install {clean_name} on Linux."
        return f"App installation is not supported on {_SYSTEM}."

    # 1. Quick check if already installed
    installed, installed_name = _check_already_installed_winget(clean_name)
    if installed:
        res = f"{installed_name or clean_name} is already installed on your system."
        if launch_after:
            _launch_app_if_possible(installed_name or clean_name)
            res += f" Opened {installed_name or clean_name}."
        if player:
            player.write_log(f"SYS: {res}")
        return res

    # 2. Search Microsoft Store
    best_candidate = None
    source_used = "msstore"

    if source_pref in ("msstore", "auto"):
        msstore_results = _search_msstore_winget(clean_name)
        if msstore_results:
            best_candidate = _find_best_match(clean_name, msstore_results)
            source_used = "msstore"

    # Fallback to general winget if not found in msstore and source is auto/winget
    if not best_candidate and source_pref in ("winget", "auto"):
        winget_results = _search_all_winget(clean_name)
        if winget_results:
            best_candidate = _find_best_match(clean_name, winget_results)
            source_used = best_candidate.get("source", "winget")

    # 3. If no candidate found via CLI search, open Microsoft Store UI directly
    if not best_candidate:
        print(f"[install_app] No winget package found for '{clean_name}'. Opening Microsoft Store search...")
        _open_store_ui(clean_name, is_product_id=False)
        res = f"Opened Microsoft Store search for '{clean_name}'. You can click 'Get' or 'Install' on the store page."
        if player:
            player.write_log(f"SYS: {res}")
        return res

    target_id = best_candidate["id"]
    target_name = best_candidate.get("name", clean_name)
    print(f"[install_app] Found candidate: '{target_name}' (ID: {target_id}, Source: {source_used})")

    if player:
        player.write_log(f"SYS: Downloading '{target_name}' from Microsoft Store...")

    # 4. Attempt installation via winget
    install_cmd = [
        "winget", "install",
        "--id", target_id,
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--disable-interactivity",
    ]
    if source_used == "msstore":
        install_cmd.extend(["--source", "msstore"])

    try:
        proc = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
            **_CNW
        )
        combined_output = (proc.stdout or "") + (proc.stderr or "")

        if "already installed" in combined_output.lower():
            res = f"{target_name} is already installed."
            if launch_after:
                _launch_app_if_possible(target_name)
                res += f" Opened {target_name}."
            if player:
                player.write_log(f"SYS: {res}")
            return res

        if proc.returncode == 0 or "successfully installed" in combined_output.lower():
            res = f"Successfully installed {target_name} from Microsoft Store!"
            if launch_after:
                time.sleep(1.5)
                _launch_app_if_possible(target_name)
                res += f" Launching {target_name} now."
            if player:
                player.write_log(f"SYS: {res}")
            return res

        # If installation requires interactive authentication, elevated admin, or failed
        print(f"[install_app] winget install non-zero exit ({proc.returncode}): {combined_output[:200]}")
    except subprocess.TimeoutExpired:
        print(f"[install_app] winget install timed out for {target_name}.")
    except Exception as e:
        print(f"[install_app] winget install exception: {e}")

    # 5. Seamless fallback: Open the store page for the exact product ID so user can complete with 1 click
    is_msstore_id = bool(re.match(r"^[0-9A-Z]{12}$", target_id, re.IGNORECASE))
    if is_msstore_id:
        _open_store_ui(target_id, is_product_id=True)
        res = f"Opened the Microsoft Store page for {target_name}. Click 'Get' or 'Install' to complete the installation."
    else:
        _open_store_ui(target_name, is_product_id=False)
        res = f"Opened Microsoft Store for {target_name}. Click 'Install' to start downloading."

    if player:
        player.write_log(f"SYS: {res}")
    return res
