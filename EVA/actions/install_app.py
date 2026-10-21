import os
import re
import sys
import time
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict

_SYSTEM = platform.system()

_CNW: dict = (
    {"creationflags": subprocess.CREATE_NO_WINDOW}
    if _SYSTEM == "Windows" else {}
)

# Curated direct package map for popular applications to guarantee instant 0.00s matching
_POPULAR_APPS: Dict[str, Dict[str, str]] = {
    "whatsapp": {"id": "WhatsApp.WhatsApp", "source": "winget", "name": "WhatsApp"},
    "vlc": {"id": "VideoLAN.VLC", "source": "winget", "name": "VLC media player"},
    "vlc media player": {"id": "VideoLAN.VLC", "source": "winget", "name": "VLC media player"},
    "spotify": {"id": "Spotify.Spotify", "source": "winget", "name": "Spotify"},
    "chrome": {"id": "Google.Chrome", "source": "winget", "name": "Google Chrome"},
    "google chrome": {"id": "Google.Chrome", "source": "winget", "name": "Google Chrome"},
    "discord": {"id": "Discord.Discord", "source": "winget", "name": "Discord"},
    "zoom": {"id": "Zoom.Zoom", "source": "winget", "name": "Zoom Workplace"},
    "telegram": {"id": "Telegram.TelegramDesktop", "source": "winget", "name": "Telegram Desktop"},
    "vscode": {"id": "Microsoft.VisualStudioCode", "source": "winget", "name": "Visual Studio Code"},
    "vs code": {"id": "Microsoft.VisualStudioCode", "source": "winget", "name": "Visual Studio Code"},
    "visual studio code": {"id": "Microsoft.VisualStudioCode", "source": "winget", "name": "Visual Studio Code"},
    "git": {"id": "Git.Git", "source": "winget", "name": "Git"},
    "steam": {"id": "Valve.Steam", "source": "winget", "name": "Steam"},
    "notion": {"id": "Notion.Notion", "source": "winget", "name": "Notion"},
    "slack": {"id": "SlackTechnologies.Slack", "source": "winget", "name": "Slack"},
    "7zip": {"id": "7zip.7zip", "source": "winget", "name": "7-Zip"},
    "7-zip": {"id": "7zip.7zip", "source": "winget", "name": "7-Zip"},
    "notepad++": {"id": "Notepad++.Notepad++", "source": "winget", "name": "Notepad++"},
    "notepad plus plus": {"id": "Notepad++.Notepad++", "source": "winget", "name": "Notepad++"},
    "brave": {"id": "Brave.Brave", "source": "winget", "name": "Brave Browser"},
    "firefox": {"id": "Mozilla.Firefox", "source": "winget", "name": "Mozilla Firefox"},
    "obs": {"id": "OBSProject.OBSStudio", "source": "winget", "name": "OBS Studio"},
    "obs studio": {"id": "OBSProject.OBSStudio", "source": "winget", "name": "OBS Studio"},
    "epic games": {"id": "EpicGames.EpicGamesLauncher", "source": "winget", "name": "Epic Games Launcher"},
    "python": {"id": "Python.Python.3.11", "source": "winget", "name": "Python 3.11"},
    "node": {"id": "OpenJS.NodeJS", "source": "winget", "name": "Node.js"},
    "nodejs": {"id": "OpenJS.NodeJS", "source": "winget", "name": "Node.js"},
    "anydesk": {"id": "AnyDeskSoftwareGmbH.AnyDesk", "source": "winget", "name": "AnyDesk"},
    "teamviewer": {"id": "TeamViewer.TeamViewer", "source": "winget", "name": "TeamViewer"},
    "canva": {"id": "Canva.Canva", "source": "winget", "name": "Canva"},
    "powertoys": {"id": "Microsoft.PowerToys", "source": "winget", "name": "Microsoft PowerToys"},
    "audacity": {"id": "Audacity.Audacity", "source": "winget", "name": "Audacity"},
    "gimp": {"id": "GIMP.GIMP", "source": "winget", "name": "GIMP"},
    "blender": {"id": "BlenderFoundation.Blender", "source": "winget", "name": "Blender"},
}


def _clean_app_name(raw: str) -> str:
    """Normalize user input to extract clean application name."""
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


def _fast_check_installed_local(app_name: str) -> Tuple[bool, str]:
    """Blazing-fast local check (under 0.03s) via Windows Registry and UWP Packages."""
    if _SYSTEM != "Windows":
        found = shutil.which(app_name) or shutil.which(app_name.lower())
        return (True, app_name) if found else (False, "")

    q = app_name.lower().strip()
    
    # 1. Path executable check
    if shutil.which(q) or shutil.which(f"{q}.exe"):
        return True, app_name

    # 2. Fast Windows Registry check
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sub in (
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ):
                try:
                    with winreg.OpenKey(root, sub) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                kname = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, kname) as sk:
                                    dname, _ = winreg.QueryValueEx(sk, "DisplayName")
                                    if dname and (q == dname.lower() or q in dname.lower() or dname.lower().startswith(q)):
                                        return True, dname
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # 3. Fast UWP Packages check (Local AppData)
    try:
        pkg_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages"
        if pkg_dir.exists():
            clean_q = re.sub(r"[^\w]", "", q)
            for p in pkg_dir.iterdir():
                if p.is_dir():
                    p_lower = p.name.lower()
                    if clean_q and clean_q in p_lower:
                        return True, app_name
    except Exception:
        pass

    return False, ""


def _parse_winget_table(output: str) -> List[Dict[str, str]]:
    """Parse table output from `winget search` into list of dicts."""
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
            timeout=12,
            **_CNW
        )
        return _parse_winget_table(proc.stdout)
    except Exception as e:
        print(f"[install_app] winget msstore search failed: {e}")
        return []


def _search_all_winget(query: str) -> List[Dict[str, str]]:
    """Search all configured winget sources in a single fast query."""
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
            timeout=12,
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
    q = query.lower().strip()
    
    # 1. Exact name match
    for item in items:
        if item.get("name", "").lower().strip() == q:
            return item
            
    # 2. Exact ID or moniker match
    for item in items:
        item_id = item.get("id", "").lower()
        if item_id == q or item_id.endswith(f".{q}") or item_id.startswith(f"{q}."):
            return item
            
    # 3. Name starts with query
    for item in items:
        if item.get("name", "").lower().startswith(q):
            return item
            
    # 4. Query in name
    for item in items:
        if q in item.get("name", "").lower():
            return item
            
    # Fallback to first item
    return items[0]


def _check_already_installed_winget(app_name: str) -> Tuple[bool, str]:
    """Check if app is already installed using fast local check with winget list fallback."""
    # Fast 0.02s local check
    is_installed, name = _fast_check_installed_local(app_name)
    if is_installed:
        return True, name

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
            timeout=4,
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


def _stream_winget_install(cmd: List[str], target_name: str, player=None) -> Tuple[int, str]:
    """Execute winget install while streaming real-time download and installation progress."""
    full_output = []
    last_log_time = time.monotonic()
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="ignore",
            **_CNW
        )
        
        while True:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line and proc.poll() is not None:
                break
            line_str = line.strip()
            if not line_str:
                continue
            full_output.append(line_str)
            
            # Extract progress percentages e.g. "45%" or "[████░░░░] 50%"
            pct_match = re.search(r"(\d{1,3}%)", line_str)
            now = time.monotonic()
            
            if pct_match and (now - last_log_time >= 0.8):
                pct = pct_match.group(1)
                last_log_time = now
                if player:
                    if hasattr(player, "set_sub_status"):
                        player.set_sub_status(f"Installing {target_name}: {pct}")
                    player.write_log(f"SYS: Installing {target_name} ({pct})...")
            elif any(w in line_str.lower() for w in ("downloading", "installing", "verifying", "found", "starting")):
                if now - last_log_time >= 1.2:
                    last_log_time = now
                    clean_status = line_str[:60]
                    if player:
                        if hasattr(player, "set_sub_status"):
                            player.set_sub_status(clean_status)
                        player.write_log(f"SYS: {clean_status}")
                        
        proc.wait(timeout=120)
        return proc.returncode, "\n".join(full_output)
    except Exception as e:
        return -1, str(e)


def _open_store_ui(query_or_id: str, is_product_id: bool = False) -> bool:
    """Launch Microsoft Store directly using Windows URI protocol as fallback."""
    if _SYSTEM != "Windows":
        return False
    try:
        if is_product_id:
            uri = f"ms-windows-store://pdp/?productid={query_or_id}"
        else:
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
    """Attempt to launch the installed app immediately."""
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
    """Download and automatically install an application silently without manual permission.
    
    Parameters:
        app_name (str): The name of the application to install.
        source (str): 'winget' | 'msstore' | 'auto' (default: 'auto').
        launch_after (bool): Launch the application after successful installation.
    """
    params = parameters or {}
    raw_name = params.get("app_name", "").strip()
    source_pref = (params.get("source") or "auto").lower().strip()
    launch_after = params.get("launch_after", True)
    
    if not raw_name:
        return "Please specify the application you would like to download or install."

    clean_name = _clean_app_name(raw_name)
    if not clean_name:
        clean_name = raw_name

    # Immediate responsive notification
    msg_init = f"Auto-installing '{clean_name}'..."
    print(f"[install_app] {msg_init}")
    if player:
        if hasattr(player, "set_sub_status"):
            player.set_sub_status(f"Installing {clean_name}...")
        player.write_log(f"SYS: {msg_init}")
    if speak:
        speak(f"Installing {clean_name} automatically. Please wait a moment.")

    if _SYSTEM != "Windows":
        if _SYSTEM == "Darwin":
            try:
                subprocess.Popen(["open", f"macappstore://showPage?title=search&query={clean_name}"])
                return f"Opened Mac App Store for '{clean_name}'."
            except Exception:
                return "Application installation via App Store is only supported on Windows or macOS."
        elif _SYSTEM == "Linux":
            try:
                subprocess.Popen(["gnome-software", f"--search={clean_name}"])
                return f"Opened Software Center for '{clean_name}'."
            except Exception:
                return f"Please use your package manager to install {clean_name} on Linux."
        return f"App installation is not supported on {_SYSTEM}."

    # 1. Ultra-fast local check if already installed (0.02s)
    installed, installed_name = _check_already_installed_winget(clean_name)
    if installed:
        res = f"{installed_name or clean_name} is already installed on your system."
        if launch_after:
            _launch_app_if_possible(installed_name or clean_name)
            res += f" Opened {installed_name or clean_name}."
        if player:
            if hasattr(player, "set_sub_status"):
                player.set_sub_status("Ready")
            player.write_log(f"SYS: {res}")
        return res

    # 2. Check curated instant catalog for top popular applications
    best_candidate = None
    source_used = "winget"
    clean_lower = clean_name.lower().strip()
    
    if clean_lower in _POPULAR_APPS:
        entry = _POPULAR_APPS[clean_lower]
        best_candidate = {"name": entry["name"], "id": entry["id"], "source": entry["source"]}
        source_used = entry["source"]
        print(f"[install_app] Matched curated app catalog: {best_candidate['name']} ({best_candidate['id']})")
    else:
        # Check source preference
        if source_pref == "msstore":
            msstore_results = _search_msstore_winget(clean_name)
            if msstore_results:
                best_candidate = _find_best_match(clean_name, msstore_results)
                source_used = "msstore"

        # Unified single search across winget and msstore
        if not best_candidate:
            all_results = _search_all_winget(clean_name)
            if all_results:
                best_candidate = _find_best_match(clean_name, all_results)
                source_used = best_candidate.get("source", "winget")

    # 3. If package found, run 100% automated silent installation
    if best_candidate:
        target_id = best_candidate["id"]
        target_name = best_candidate.get("name", clean_name)
        print(f"[install_app] Installing '{target_name}' (ID: {target_id}, Source: {source_used})...")

        install_cmd = [
            "winget", "install",
            "--id", target_id,
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
            "--authentication-mode", "silentPreferred",
            "--force",
        ]
        if source_used in ("msstore", "winget"):
            install_cmd.extend(["--source", source_used])

        returncode, output = _stream_winget_install(install_cmd, target_name, player=player)
        combined_lower = output.lower()

        if "already installed" in combined_lower:
            res = f"{target_name} is already installed."
            if launch_after:
                _launch_app_if_possible(target_name)
                res += f" Opened {target_name}."
            if player:
                if hasattr(player, "set_sub_status"):
                    player.set_sub_status("Ready")
                player.write_log(f"SYS: {res}")
            return res

        if returncode == 0 or "successfully installed" in combined_lower:
            res = f"Successfully installed {target_name}!"
            if launch_after:
                time.sleep(1.2)
                _launch_app_if_possible(target_name)
                res += f" Launching {target_name} now."
            if player:
                if hasattr(player, "set_sub_status"):
                    player.set_sub_status("Installed")
                player.write_log(f"SYS: {res}")
            return res

        # If standard winget install failed, attempt silent installation with admin elevation automatically
        print(f"[install_app] Standard install exit {returncode}, attempting silent elevated install...")
        elevated_ps = (
            f"Start-Process winget -ArgumentList 'install --id \"{target_id}\" "
            f"--silent --accept-package-agreements --accept-source-agreements --disable-interactivity --force' "
            f"-Verb RunAs -Wait"
        )
        try:
            elev_res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", elevated_ps],
                timeout=90,
                **_CNW
            )
            if elev_res.returncode == 0:
                res = f"Successfully installed {target_name}!"
                if launch_after:
                    time.sleep(1.2)
                    _launch_app_if_possible(target_name)
                    res += f" Launching {target_name} now."
                if player:
                    player.write_log(f"SYS: {res}")
                return res
        except Exception as e:
            print(f"[install_app] Elevated install failed: {e}")

    # 4. Fallback: Open Microsoft Store for 1-click install if all automated methods failed
    target_val = best_candidate["id"] if best_candidate else clean_name
    is_msstore_id = bool(re.match(r"^[0-9A-Z]{12}$", target_val, re.IGNORECASE))
    if is_msstore_id:
        _open_store_ui(target_val, is_product_id=True)
        res = f"Opened Microsoft Store for {best_candidate.get('name', clean_name)}."
    else:
        _open_store_ui(clean_name, is_product_id=False)
        res = f"Opened Microsoft Store for {clean_name}."

    if player:
        if hasattr(player, "set_sub_status"):
            player.set_sub_status("Ready")
        player.write_log(f"SYS: {res}")
    return res
