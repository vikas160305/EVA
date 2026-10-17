import os
import shutil
import platform
import subprocess
import sys
import json
import re
import time
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_desktop_dir() -> Path:
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        onedrive_desktop = Path(userprofile) / "OneDrive" / "Desktop"
        if onedrive_desktop.is_dir():
            return onedrive_desktop
    standard_desktop = Path.home() / "Desktop"
    if standard_desktop.is_dir():
        return standard_desktop
    return Path.home()


BASE_DIR           = get_base_dir()
API_CONFIG_PATH    = BASE_DIR / "config" / "api_keys.json"
DESKTOP            = _get_desktop_dir()
MAX_BUILD_ATTEMPTS = 3
GEMINI_MODEL       = "gemini-flash-latest"


def _open_vscode(target_path: Path) -> bool:
    """Open a file or directory in Visual Studio Code."""
    candidates = [
        "code",
        "code.cmd",
        rf"C:\Users\{Path.home().name}\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd",
        rf"C:\Users\{Path.home().name}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
    ]
    for cmd in candidates:
        exe = shutil.which(cmd) if not Path(cmd).is_absolute() else (cmd if Path(cmd).exists() else None)
        if exe:
            try:
                subprocess.Popen(
                    [exe, str(target_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True if platform.system() == "Windows" else False,
                )
                print(f"[Code] 💻 Opened in VS Code: {target_path}")
                return True
            except Exception as e:
                print(f"[Code] VS Code launch error with {exe}: {e}")
                continue
    return False


def _wants_vscode(description: str, params: dict = None) -> bool:
    if (params or {}).get("open_vscode") is True or (params or {}).get("open_in_editor") is True:
        return True
    text = f"{description} {(params or {}).get('action', '')}".lower()
    return any(term in text for term in ("vscode", "vs code", "vls code", "visual studio code", "in code", "in editor", "editor"))


def _infer_slug_from_description(description: str, fallback: str = "main") -> str:
    if not description:
        return fallback
    desc = description.lower()
    keywords = [
        "factorial", "fibonacci", "calculator", "palindrome", "prime",
        "sorting", "bubblesort", "mergesort", "quicksort", "binarysearch",
        "todolist", "todo", "snake", "tictactoe", "weather", "scraper",
        "server", "client", "bot", "game", "matrix", "linkedlist", "stack", "queue"
    ]
    for kw in keywords:
        if kw in desc:
            return kw
    words = re.findall(r"[a-zA-Z0-9]+", desc)
    stop_words = {
        "create", "file", "in", "language", "of", "code", "and", "run", "it",
        "vs", "vscode", "vls", "the", "a", "an", "program", "script", "to", "write", "make"
    }
    meaningful = [w for w in words if w.lower() not in stop_words]
    if meaningful:
        return "_".join(meaningful[:2]).lower()
    return fallback


def _resolve_save_path(output_path: str, language: str, code: str = "", description: str = "") -> Path:
    ext_map = {
        "python": ".py", "py": ".py",
        "javascript": ".js", "js": ".js", "node": ".js",
        "typescript": ".ts", "ts": ".ts",
        "html": ".html", "css": ".css",
        "java": ".java",
        "cpp": ".cpp", "c++": ".cpp", "cplusplus": ".cpp",
        "c": ".c",
        "csharp": ".cs", "cs": ".cs", "c#": ".cs",
        "bash": ".sh", "shell": ".sh", "sh": ".sh",
        "powershell": ".ps1", "ps1": ".ps1",
        "sql": ".sql", "json": ".json",
        "rust": ".rs", "rs": ".rs",
        "go": ".go", "golang": ".go",
        "ruby": ".rb", "rb": ".rb",
        "php": ".php",
    }
    lang_clean = (language or "python").lower().strip()
    ext = ext_map.get(lang_clean, ".py")
    desktop = _get_desktop_dir()

    if output_path:
        p = Path(output_path)
        if not p.is_absolute():
            p = desktop / p
        if not p.suffix:
            p = p.with_suffix(ext)
        return p

    # For Java: class name must match file name!
    if ext == ".java":
        if code:
            class_match = re.search(r"public\s+class\s+([A-Za-z0-9_]+)", code)
            if not class_match:
                class_match = re.search(r"class\s+([A-Za-z0-9_]+)", code)
            if class_match:
                return desktop / f"{class_match.group(1)}.java"
        slug = _infer_slug_from_description(description, fallback="Factorial" if "factorial" in description.lower() else "Main")
        return desktop / f"{slug.capitalize()}.java"

    # For other languages:
    slug = _infer_slug_from_description(description, fallback="main")
    return desktop / f"{slug}{ext}"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _get_gemini(model: str = GEMINI_MODEL):
    from google import genai
    _c = genai.Client(api_key=_get_api_key())

    class _W:
        def generate_content(self, contents):
            last_err = None
            for m in [model, "gemini-flash-latest", "gemini-3.8-flash", "gemini-flash-lite-latest"]:
                try:
                    return _c.models.generate_content(model=m, contents=contents)
                except Exception as e:
                    last_err = e
                    if "404" in str(e) or "503" in str(e) or "429" in str(e):
                        continue
                    raise
            if last_err:
                raise last_err
            raise RuntimeError("Gemini code generation failed.")

    return _W()


def _clean_code(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()




def _read_file(file_path: str) -> tuple[str, str]:
    if not file_path:
        return "", "No file path provided."
    p = Path(file_path)
    if not p.exists():
        return "", f"File not found: {file_path}"
    try:
        return p.read_text(encoding="utf-8"), ""
    except Exception as e:
        return "", f"Could not read file: {e}"


def _save_file(path: Path, content: str) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Saved to: {path}"
    except Exception as e:
        return f"Could not save: {e}"


def _preview(code: str, lines: int = 10) -> str:
    all_lines = code.splitlines()
    preview   = "\n".join(all_lines[:lines])
    suffix    = f"\n... ({len(all_lines) - lines} more lines)" if len(all_lines) > lines else ""
    return preview + suffix


def _has_error(output: str) -> bool:
    error_signals = ["error", "exception", "traceback", "syntaxerror",
                     "nameerror", "typeerror", "stderr", "failed", "crash"]
    return any(s in output.lower() for s in error_signals)


def _take_screenshot() -> Path | None:
    try:
        import pyautogui
        screenshot_path = Path.home() / "Desktop" / f"jarvis_debug_{int(time.time())}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(screenshot_path))
        print(f"[Code] 📸 Screenshot: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"[Code] ⚠️ Screenshot failed: {e}")
        return None


def _image_to_base64(path: Path) -> str:
    import base64
    return base64.b64encode(path.read_bytes()).decode("utf-8")


_VALID_INTENTS = {"write", "edit", "explain", "run", "build", "screen_debug", "optimize"}


def _detect_intent(description: str, file_path: str, code: str) -> str:
    """
    Dil bağımsız niyet tespiti — sabit anahtar kelime listesi YOK.
    Kullanıcı hangi dilde konuşursa konuşsun, açıklama Gemini'ye
    sınıflandırtılır. API'ye ulaşılamazsa dile bakmayan yapısal
    ipuçlarına (dosya diskte var mı, kod verilmiş mi) düşülür.
    """
    desc        = (description or "").strip()
    file_exists = bool(file_path) and Path(file_path).exists()

    if desc:
        try:
            ctx = []
            if file_path:
                ctx.append(f"a file path is provided (exists on disk: {file_exists})")
            if code:
                ctx.append("an inline code snippet is provided")
            prompt = (
                "Classify a coding assistant request into exactly ONE intent word.\n"
                "The request may be written in ANY language.\n\n"
                f"Request: {desc}\n"
                + (f"Context: {'; '.join(ctx)}\n" if ctx else "")
                + "\nIntents:\n"
                "  write        = create new code from scratch\n"
                "  edit         = modify an existing file\n"
                "  explain      = describe what given code/file does\n"
                "  run          = execute an existing file\n"
                "  build        = write code, run it, and iterate until it works\n"
                "  screen_debug = analyze an error currently visible on the user's screen\n"
                "  optimize     = refactor / clean up / speed up existing code\n\n"
                "Reply with ONLY the intent word, nothing else."
            )
            ans = _get_gemini().generate_content(prompt).text.strip().lower()
            ans = ans.strip("`'\". \n")
            if ans in _VALID_INTENTS:
                return ans
        except Exception as e:
            print(f"[Code] Intent classification failed ({e}) — structural fallback")

    # Yapısal geri dönüş — hiçbir dile bağlı değil
    if file_exists:
        return "edit" if desc else "explain"
    if code:
        return "explain"
    return "write"

def _write(description: str, language: str, output_path: str, player=None) -> tuple[str, Path]:
    lang  = language or "python"
    model = _get_gemini()

    prompt = f"""You are an expert {lang} developer.
Write clean, working, well-commented {lang} code for the description below.

Rules:
- Output ONLY the code. No explanation, no markdown, no backticks.
- Add helpful inline comments.
- Handle errors and edge cases properly.
- Use modern best practices.

Description: {description}

Code:"""

    response = model.generate_content(prompt)
    code     = _clean_code(response.text)
    path     = _resolve_save_path(output_path, lang, code=code, description=description)
    _save_file(path, code)
    return code, path


def _fix_code(code: str, error_output: str, description: str) -> str:
    model  = _get_gemini()
    prompt = f"""You are an expert debugger.
The code below failed with the following error. Fix it.
Return ONLY the corrected code — no explanation, no markdown, no backticks.

Original goal: {description}

Error:
{error_output[:2000]}

Broken code:
{code}

Fixed code:"""

    response = model.generate_content(prompt)
    return _clean_code(response.text)


def _exec_cmd(cmd: list, cwd: Path, timeout: int) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(cwd)
        )
        output = result.stdout.strip()
        error  = result.stderr.strip()
        parts  = []
        if output: parts.append(f"Output:\n{output}")
        if error:  parts.append(f"Stderr:\n{error}")
        return "\n\n".join(parts) if parts else "Executed with no output."
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    except FileNotFoundError:
        return f"Executable not found: {cmd[0]}."
    except Exception as e:
        return f"Execution error: {e}"


def _run_file(path: Path, args: list = None, timeout: int = 30) -> str:
    ext = path.suffix.lower()
    args = args or []

    # Python (.py)
    if ext == ".py":
        return _exec_cmd([sys.executable, str(path)] + args, path.parent, timeout)

    # JavaScript (.js)
    elif ext == ".js":
        node_bin = shutil.which("node") or shutil.which("nodejs")
        if not node_bin:
            return "Node.js is not installed in system PATH. Cannot execute JavaScript directly in terminal."
        return _exec_cmd([node_bin, str(path)] + args, path.parent, timeout)

    # TypeScript (.ts)
    elif ext == ".ts":
        runner = shutil.which("ts-node") or shutil.which("tsx")
        if runner:
            return _exec_cmd([runner, str(path)] + args, path.parent, timeout)
        if shutil.which("npx"):
            return _exec_cmd(["npx", "ts-node", str(path)] + args, path.parent, timeout)
        return "TypeScript runner (ts-node) is not installed in system PATH. Cannot execute TypeScript directly."

    # Java (.java)
    elif ext == ".java":
        java_bin = shutil.which("java")
        javac_bin = shutil.which("javac")
        if not java_bin and not javac_bin:
            return "Java runtime (JDK) is not installed in system PATH. Cannot execute Java in terminal. Please run it inside VS Code."
        # In Java 11+, java file.java runs single-file source code directly!
        if java_bin:
            try:
                res = subprocess.run(
                    [java_bin, str(path)] + args,
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    timeout=timeout, cwd=str(path.parent)
                )
                if res.returncode == 0 or res.stdout:
                    output = res.stdout.strip()
                    error  = res.stderr.strip()
                    parts  = []
                    if output: parts.append(f"Output:\n{output}")
                    if error:  parts.append(f"Stderr:\n{error}")
                    return "\n\n".join(parts) if parts else "Executed with no output."
            except Exception:
                pass
        # Classic javac compile and java run
        if javac_bin:
            c_res = subprocess.run(
                [javac_bin, str(path.name)],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, cwd=str(path.parent)
            )
            if c_res.returncode != 0:
                return f"Java Compilation Error:\n{c_res.stderr.strip() or c_res.stdout.strip()}"
            class_name = path.stem
            if java_bin:
                return _exec_cmd([java_bin, "-cp", ".", class_name] + args, path.parent, timeout)
        return "Failed to run Java file."

    # C (.c)
    elif ext == ".c":
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            return "C compiler (gcc/clang) is not installed in system PATH. Cannot execute C code directly in terminal."
        out_exe = path.with_suffix(".exe" if platform.system() == "Windows" else "")
        c_res = subprocess.run([compiler, str(path), "-o", str(out_exe)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=str(path.parent))
        if c_res.returncode != 0:
            return f"C Compilation Error:\n{c_res.stderr.strip() or c_res.stdout.strip()}"
        return _exec_cmd([str(out_exe)] + args, path.parent, timeout)

    # C++ (.cpp, .cc, .cxx)
    elif ext in (".cpp", ".cc", ".cxx"):
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            return "C++ compiler (g++/clang++) is not installed in system PATH. Cannot execute C++ code directly in terminal."
        out_exe = path.with_suffix(".exe" if platform.system() == "Windows" else "")
        c_res = subprocess.run([compiler, str(path), "-o", str(out_exe)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=str(path.parent))
        if c_res.returncode != 0:
            return f"C++ Compilation Error:\n{c_res.stderr.strip() or c_res.stdout.strip()}"
        return _exec_cmd([str(out_exe)] + args, path.parent, timeout)

    # Go (.go)
    elif ext == ".go":
        if not shutil.which("go"):
            return "Go compiler is not installed in system PATH. Cannot execute Go code directly in terminal."
        return _exec_cmd(["go", "run", str(path)] + args, path.parent, timeout)

    # Rust (.rs)
    elif ext == ".rs":
        rustc_bin = shutil.which("rustc")
        if not rustc_bin:
            return "Rust compiler (rustc) is not installed in system PATH. Cannot execute Rust code directly in terminal."
        out_exe = path.with_suffix(".exe" if platform.system() == "Windows" else "")
        c_res = subprocess.run([rustc_bin, str(path), "-o", str(out_exe)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=str(path.parent))
        if c_res.returncode != 0:
            return f"Rust Compilation Error:\n{c_res.stderr.strip() or c_res.stdout.strip()}"
        return _exec_cmd([str(out_exe)] + args, path.parent, timeout)

    # C# (.cs)
    elif ext == ".cs":
        if shutil.which("dotnet"):
            return _exec_cmd(["dotnet", "run", "--project", str(path.parent)] + args, path.parent, timeout)
        return "dotnet CLI is not installed in system PATH. Cannot execute C# directly in terminal."

    # Shell / Bash (.sh)
    elif ext == ".sh":
        bash_bin = shutil.which("bash") or shutil.which("sh")
        if not bash_bin:
            return "Bash is not installed in system PATH. Cannot execute shell script."
        return _exec_cmd([bash_bin, str(path)] + args, path.parent, timeout)

    # PowerShell (.ps1)
    elif ext == ".ps1":
        return _exec_cmd(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(path)] + args, path.parent, timeout)

    # Batch (.bat, .cmd)
    elif ext in (".bat", ".cmd"):
        return _exec_cmd(["cmd.exe", "/c", str(path)] + args, path.parent, timeout)

    # HTML (.html)
    elif ext == ".html":
        if platform.system() == "Windows":
            try:
                os.startfile(str(path))
            except Exception:
                pass
        return f"Opened {path.name} in your web browser."

    return f"No execution runner configured for {ext} files."


def _build(description, language, output_path, args, timeout, speak=None, player=None, open_editor=False) -> str:
    if not description:
        return "Please describe what you want me to build, sir."

    if player:
        player.write_log("[Code] Build started...")

    lang = language or "python"

    try:
        code, path = _write(description, lang, output_path, player)
        print(f"[Code] ✅ Written: {path}")
    except Exception as e:
        msg = f"Could not write initial code: {e}"
        if speak: speak(msg)
        return msg

    editor_msg = ""
    if open_editor:
        if _open_vscode(path):
            editor_msg = " Opened in VS Code."

    last_output = _run_file(path, args, timeout)

    # If runtime or compiler is missing, do not attempt broken fix cycles
    if "is not installed" in last_output.lower() or "not configured" in last_output.lower():
        msg = (
            f"Created {path.name} on your Desktop.{editor_msg} "
            f"{last_output}"
        )
        if speak: speak(msg)
        return f"{msg}\n\nCode Preview:\n{_preview(code)}"

    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        print(f"[Code] 🔄 Attempt {attempt}/{MAX_BUILD_ATTEMPTS}")
        if player:
            player.write_log(f"[Code] Attempt {attempt}...")

        if attempt > 1:
            last_output = _run_file(path, args, timeout)

        if not _has_error(last_output):
            msg = (
                f"Build complete, sir. "
                f"The code is working after {attempt} attempt{'s' if attempt > 1 else ''}. "
                f"Saved to {path}.{editor_msg}"
            )
            if speak: speak(msg)
            return f"{msg}\n\nOutput:\n{last_output}"

        print(f"[Code] ⚠️ Error on attempt {attempt}, fixing...")
        if player:
            player.write_log(f"[Code] Fixing (attempt {attempt})...")

        try:
            code = _fix_code(code, last_output, description)
            _save_file(path, code)
        except Exception as e:
            msg = f"Could not fix code on attempt {attempt}: {e}"
            if speak: speak(msg)
            return msg

    msg = (
        f"I was unable to build a working version after {MAX_BUILD_ATTEMPTS} attempts, sir. "
        f"The last error was: {last_output[:200]}"
    )
    if speak: speak(msg)
    return f"{msg}\n\nLast code saved to: {path}.{editor_msg}"


def _write_action(description, language, output_path, player, open_editor=False) -> str:
    if not description:
        return "Please describe what you want me to write, sir."
    if player:
        player.write_log("[Code] Writing code...")
    try:
        code, path = _write(description, language, output_path, player)
        print(f"[Code] ✅ Written: {path}")
        editor_msg = ""
        if open_editor:
            if _open_vscode(path):
                editor_msg = "\n💻 Opened in Visual Studio Code."
        return f"Code written. Saved to: {path}{editor_msg}\n\nPreview:\n{_preview(code)}"
    except Exception as e:
        return f"Could not generate code: {e}"


def _edit_action(file_path, instruction, player) -> str:
    if not file_path:
        return "Please provide a file path to edit, sir."
    if not instruction:
        return "Please describe what change to make, sir."

    content, err = _read_file(file_path)
    if err:
        return err

    if player:
        player.write_log("[Code] Editing file...")

    model  = _get_gemini()
    prompt = f"""You are an expert code editor.
Apply the following change to the code below.
Return ONLY the complete updated code — no explanation, no markdown, no backticks.

Change: {instruction}

Original code:
{content}

Updated code:"""

    try:
        response = model.generate_content(prompt)
        edited   = _clean_code(response.text)
    except Exception as e:
        return f"Could not edit code: {e}"

    status = _save_file(Path(file_path), edited)
    print(f"[Code] ✅ Edited: {file_path}")
    return f"File edited. {status}\n\nPreview:\n{_preview(edited)}"


def _explain_action(file_path, code, player) -> str:
    if file_path and not code:
        code, err = _read_file(file_path)
        if err:
            return err
    if not code:
        return "Please provide code or a file path to explain, sir."

    if player:
        player.write_log("[Code] Analyzing code...")

    model  = _get_gemini()
    prompt = f"""Explain what this code does in simple, clear language.
Focus on: what it does, how it works, and any important details.
Be concise — 3 to 6 sentences maximum.

Code:
{code[:4000]}

Explanation:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Could not explain code: {e}"


def _run_action(file_path, args, timeout, player, open_editor=False) -> str:
    if not file_path:
        return "Please provide a file path to run, sir."
    p = Path(file_path)
    if not p.exists():
        desktop_p = _get_desktop_dir() / file_path
        if desktop_p.exists():
            p = desktop_p
        else:
            for ext in [".py", ".java", ".js", ".c", ".cpp", ".ts", ".go", ".rs"]:
                candidate = _get_desktop_dir() / f"{file_path}{ext}"
                if candidate.exists():
                    p = candidate
                    break
    if not p.exists():
        return f"File not found: {file_path}"
    editor_msg = ""
    if open_editor:
        if _open_vscode(p):
            editor_msg = "\n💻 Opened in Visual Studio Code."
    if player:
        player.write_log(f"[Code] Running {p.name}...")
    res = _run_file(p, args, timeout)
    return f"{res}{editor_msg}"


def _optimize_action(file_path, code, language, output_path, player) -> str:

    if file_path and not code:
        code, err = _read_file(file_path)
        if err:
            return err
    if not code:
        return "Please provide code or a file path to optimize, sir."

    if player:
        player.write_log("[Code] Optimizing code...")

    lang  = language or "python"
    model = _get_gemini()

    prompt = f"""You are an expert {lang} developer and code reviewer.
Optimize the following code for:
1. Performance — eliminate unnecessary operations, use efficient data structures
2. Readability — clear variable names, proper formatting, logical structure
3. Best practices — modern {lang} patterns, error handling, type hints if applicable
4. Remove dead code, redundant comments, and unnecessary complexity

Return ONLY the optimized code — no explanation, no markdown, no backticks.

Original code:
{code[:6000]}

Optimized code:"""

    try:
        response  = model.generate_content(prompt)
        optimized = _clean_code(response.text)
    except Exception as e:
        return f"Could not optimize code: {e}"

    # Kaydet
    if file_path:
        save_path = Path(file_path)
    else:
        save_path = _resolve_save_path(output_path, lang)

    status = _save_file(save_path, optimized)
    print(f"[Code] ✅ Optimized: {save_path}")

    original_lines  = len(code.splitlines())
    optimized_lines = len(optimized.splitlines())
    diff = original_lines - optimized_lines

    return (
        f"Code optimized. {status}\n"
        f"Lines: {original_lines} → {optimized_lines} "
        f"({'−' if diff > 0 else '+'}{abs(diff)} lines)\n\n"
        f"Preview:\n{_preview(optimized)}"
    )


def _screen_debug_action(description, file_path, player, speak=None) -> str:

    if player:
        player.write_log("[Code] Taking screenshot for analysis...")

    print("[Code] 📸 Capturing screen for debug...")


    screenshot_path = _take_screenshot()
    if not screenshot_path:
        return "Could not take screenshot, sir. Please make sure PyAutoGUI is installed."


    file_content = ""
    if file_path:
        file_content, err = _read_file(file_path)
        if err:
            print(f"[Code] ⚠️ Could not read file: {err}")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=_get_api_key())

        image_bytes  = screenshot_path.read_bytes()
        image_base64 = _image_to_base64(screenshot_path)

        user_question = description or "What error or problem do you see on the screen? How can it be fixed?"

        context = ""
        if file_content:
            context = f"\n\nAdditionally, here is the related file content:\n```\n{file_content[:4000]}\n```"

        analysis_prompt = f"""You are an expert programmer and debugger analyzing a screenshot.

User's question: {user_question}{context}

Please:
1. Identify any errors, exceptions, or problems visible on the screen
2. Explain what is causing the problem in simple terms
3. Provide a concrete fix or solution
4. If there's code visible, show the corrected version

Be specific and actionable. If you see an error message, quote it exactly."""

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            analysis_prompt,
        ]

        response = None
        for m in [GEMINI_MODEL, "gemini-flash-latest", "gemini-3.8-flash", "gemini-flash-lite-latest"]:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=contents,
                )
                if response and response.text:
                    break
            except Exception:
                continue
        if not response:
            return "Could not analyze the screen at this moment."

        analysis = response.text.strip()
        print(f"[Code] ✅ Screen analysis complete")

        try:
            screenshot_path.unlink()
        except Exception:
            pass

        if file_path and file_content:

            code_match = re.search(r"```[a-zA-Z]*\n(.*?)```", analysis, re.DOTALL)
            if code_match:
                fixed_code = code_match.group(1).strip()
                save_path  = Path(file_path)
                _save_file(save_path, fixed_code)
                analysis += f"\n\n✅ Fixed code has been saved to: {file_path}"
                print(f"[Code] ✅ Fixed code saved: {file_path}")

        return analysis

    except Exception as e:

        try:
            screenshot_path.unlink()
        except Exception:
            pass
        return f"Screen analysis failed: {e}"


def code_helper(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None
) -> str:
    """
    Called from main.py.

    parameters:
        action      : write | edit | explain | run | build | screen_debug | optimize | auto
        description : What the code should do / what change to make / what problem to analyze
        language    : Programming language (default: python)
        output_path : Where to save — user specifies full path or filename
        file_path   : Path to existing file (edit / explain / run / build / optimize)
        code        : Raw code string (explain/optimize without a file)
        args        : CLI argument list for run/build
        timeout     : Execution timeout in seconds (default: 30)
    """
    p           = parameters or {}
    action      = p.get("action", "auto").lower().strip()
    description = p.get("description", "").strip()
    language    = p.get("language", "python").strip()
    output_path = p.get("output_path", "").strip()
    file_path   = p.get("file_path", "").strip()
    code        = p.get("code", "").strip()
    args        = p.get("args", [])
    timeout     = int(p.get("timeout", 30))
    open_editor = _wants_vscode(description, p)

    if action == "auto":
        action = _detect_intent(description, file_path, code)
        print(f"[Code] 🤖 Auto-detected: {action}")

    if action == "write":
        return _write_action(description, language, output_path, player, open_editor=open_editor)

    elif action == "edit":
        return _edit_action(
            file_path,
            description or p.get("instruction", ""),
            player
        )

    elif action == "explain":
        return _explain_action(file_path, code, player)

    elif action == "run":
        return _run_action(file_path, args, timeout, player, open_editor=open_editor)

    elif action == "build":
        return _build(description, language, output_path, args, timeout, speak, player, open_editor=open_editor)

    elif action == "optimize":
        return _optimize_action(file_path, code, language, output_path, player)

    elif action == "screen_debug":
        return _screen_debug_action(description, file_path, player, speak)

    else:
        return f"Unknown action: '{action}'. Use write, edit, explain, run, build, optimize, or screen_debug."