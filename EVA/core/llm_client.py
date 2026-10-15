"""
Local LLM client for MARK XL.

Supports two backends — selected via  "llm_provider"  in config/api_keys.json:

  "llm_provider": "ollama"   (default)
        Uses Ollama's native /api/chat endpoint.
        Download: https://ollama.com
        Default port: 11434

  "llm_provider": "openai"
        Uses any OpenAI-compatible server: LM Studio, Jan, LocalAI,
        llama.cpp server, vLLM, etc.
        LM Studio download: https://lmstudio.ai   (default port: 1234)
        Set  "llm_url": "http://localhost:1234"  in config.
        Note: tool-calling support depends on the model; use a model that
        supports function/tool calls (e.g. Qwen2.5, Llama-3.1, Mistral).
"""
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Generator

import requests


class LLMFailureState(RuntimeError):
    """Clear, testable failure wrapper for transient/terminal LLM request failures."""

    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class LLMRetryBudget:
    """Bounded retry with exponential backoff and jitter for transient LLM failures."""

    def __init__(self, max_attempts: int = 4, base_delay: float = 0.25, max_delay: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def should_retry(self, exc: BaseException) -> bool:
        text = str(exc).lower()
        return (
            isinstance(exc, requests.exceptions.Timeout)
            or isinstance(exc, requests.exceptions.ConnectionError)
            or "429" in text
            or "connection reset" in text
            or "temporar" in text
            or "timed out" in text
            or "timeout" in text
            or "500" in text
            or "502" in text
            or "503" in text
            or "504" in text
        )

    def delay_for_attempt(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** max(0, attempt - 1)), self.max_delay)
        return delay + random.uniform(0.0, 0.25)


def _request_timeout_tuple(timeout: int | float) -> tuple[float, float]:
    """Return connect/read/total timeout policy tuple, safe and explicit for Requests."""
    connect_timeout = min(5.0, max(1.0, timeout / 10.0))
    read_timeout = max(5.0, timeout)
    return (connect_timeout, read_timeout)

# Matches a sentence boundary: [.!?] followed by whitespace, or a blank line.
# Avoids splitting on decimals (3.5) because those have no space after the dot.
_SENT_END = re.compile(r'(?<=[.!?])\s+|(?<=\n)\s*\n')

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR    = get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

_DEFAULTS = {
    "llm_url":      "http://localhost:11434",
    "llm_model":    "llama3.2",
    "llm_provider": "ollama",   # "ollama" | "openai"
}


def get_llm_provider() -> str:
    """Returns 'ollama' or 'openai' (covers LM Studio, LocalAI, Jan, etc.)."""
    raw = _load_config().get("llm_provider", "ollama").strip().lower()
    return "openai" if raw in ("openai", "lmstudio", "localai", "jan", "llamacpp") else "ollama"


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


class ApiKeyRotator:
    """Thread-safe API key pool manager with automatic round-robin and cooldown failover.

    Supports reading keys from:
      - config/api_keys.json: 'gemini_api_keys': [...] or 'gemini_api_key': 'key1, key2'
      - environment: GEMINI_API_KEYS, GEMINI_API_KEY, MARK_L_GEMINI_API_KEY
    """

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or CONFIG_PATH
        self._lock = threading.Lock()
        self._keys: list[str] = []
        self._index = 0
        self._cooldowns: dict[str, float] = {}
        self._reload_keys()

    def _reload_keys(self) -> list[str]:
        keys: list[str] = []
        env_multi = os.environ.get("GEMINI_API_KEYS")
        if env_multi:
            for k in re.split(r"[,;\s]+", env_multi):
                if k.strip() and k.strip() not in keys:
                    keys.append(k.strip())
        env_single = os.environ.get("GEMINI_API_KEY") or os.environ.get("MARK_L_GEMINI_API_KEY")
        if env_single and env_single.strip() not in keys:
            keys.append(env_single.strip())

        try:
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                multi = data.get("gemini_api_keys")
                if isinstance(multi, list):
                    for k in multi:
                        if isinstance(k, str) and k.strip() and k.strip() not in keys:
                            keys.append(k.strip())
                single = data.get("gemini_api_key")
                if isinstance(single, str):
                    for k in re.split(r"[,;\s]+", single):
                        if k.strip() and k.strip() not in keys:
                            keys.append(k.strip())
        except Exception:
            pass

        self._keys = keys
        return self._keys

    def get_keys(self) -> list[str]:
        with self._lock:
            if not self._keys:
                self._reload_keys()
            return list(self._keys)

    def get_current_key(self) -> str:
        with self._lock:
            if not self._keys:
                self._reload_keys()
            if not self._keys:
                raise RuntimeError("No Gemini API key configured in api_keys.json or environment.")
            now = time.monotonic()
            n = len(self._keys)
            for i in range(n):
                idx = (self._index + i) % n
                candidate = self._keys[idx]
                expire = self._cooldowns.get(candidate, 0.0)
                if now >= expire:
                    self._index = idx
                    return candidate
            soonest_key = min(self._keys, key=lambda k: self._cooldowns.get(k, 0.0))
            return soonest_key

    def rotate_key(self, failed_key: str | None = None, reason: str = "rate_limit", cooldown_seconds: float = 60.0) -> str:
        with self._lock:
            if not self._keys:
                self._reload_keys()
            if not self._keys:
                raise RuntimeError("No Gemini API key available to rotate.")
            if failed_key and failed_key in self._keys:
                self._cooldowns[failed_key] = time.monotonic() + cooldown_seconds
                print(f"[ApiKeyRotator] Key marked cooling down for {cooldown_seconds:.0f}s ({reason}).")
            if len(self._keys) > 1:
                self._index = (self._index + 1) % len(self._keys)
                next_key = self._keys[self._index]
                print(f"[ApiKeyRotator] Rotated to key index {self._index + 1}/{len(self._keys)}.")
                return next_key
            return self._keys[0]


_API_KEY_ROTATOR = ApiKeyRotator()


def get_gemini_api_key() -> str:
    """Return the active, healthy Gemini API key from the rotation pool."""
    return _API_KEY_ROTATOR.get_current_key()


def rotate_gemini_api_key(failed_key: str | None = None, reason: str = "rate_limit", cooldown_seconds: float = 60.0) -> str:
    """Rotate to the next API key and place the failing key in cooldown."""
    return _API_KEY_ROTATOR.rotate_key(failed_key=failed_key, reason=reason, cooldown_seconds=cooldown_seconds)


def get_all_gemini_api_keys() -> list[str]:
    """Return all configured Gemini API keys."""
    return _API_KEY_ROTATOR.get_keys()


def ensure_ollama_running(timeout: int = 15) -> bool:
    """
    For Ollama: ping /api/tags; auto-launch 'ollama serve' if not running.
    For OpenAI-compatible providers: just ping /v1/models (server must be started manually).
    Returns True if the LLM server is reachable.
    """
    url, _   = get_llm_settings()
    provider = get_llm_provider()

    if provider == "openai":
        # OpenAI-compatible servers (LM Studio, LocalAI, etc.) must be started
        # by the user — we just check if they're reachable.
        health = f"{url}/v1/models"
        try:
            ok = requests.get(health, timeout=5).status_code == 200
            if ok:
                print(f"[LLM] OpenAI-compatible server reachable at {url}")
            else:
                print(f"[LLM] Server at {url} returned non-200.  Is it running?")
            return ok
        except Exception as e:
            print(
                f"[LLM] Cannot reach OpenAI-compatible server at {url}.\n"
                "      Make sure LM Studio / LocalAI / Jan is running and the server is started."
            )
            return False

    # ── Ollama ──────────────────────────────────────────────────────────────
    health = f"{url}/api/tags"

    def _is_up() -> bool:
        try:
            return requests.get(health, timeout=3).status_code == 200
        except Exception:
            return False

    if _is_up():
        return True

    print("[LLM] Ollama not running — launching 'ollama serve'…")
    try:
        kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(["ollama", "serve"], **kwargs)
    except FileNotFoundError:
        print("[LLM] 'ollama' command not found. Install Ollama from https://ollama.com")
        return False
    except Exception as e:
        print(f"[LLM] Could not launch Ollama: {e}")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.0)
        if _is_up():
            print("[LLM] Ollama started successfully.")
            return True

    print("[LLM] Ollama did not respond within the timeout.")
    return False


def warmup_model(system_prompt: str | None = None) -> bool:
    """
    Pre-load the model AND prime Ollama's KV prefix cache.

    Why the system_prompt matters
    ─────────────────────────────
    Ollama caches the KV attention state of the prompt prefix across requests.
    If warmup includes the same system prompt that real requests will use, Ollama
    evaluates those tokens ONCE at startup.  Every subsequent request only needs
    to evaluate the small delta (user message ± time context) instead of the full
    300-500 token system prompt → drops first-token latency from ~17 s to <1 s.

    Pass the *static* part of the system prompt (the JARVIS protocol text, without
    timestamps or per-minute context) so the prefix stays valid across calls.
    """
    url, model = get_llm_settings()
    provider   = get_llm_provider()
    print(f"[LLM] Warming up '{model}' ({provider})…")

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": "hi"})

    if provider == "openai":
        # OpenAI-compatible: just fire a minimal request to ensure the model is loaded.
        # No keep_alive or KV-cache priming available — server manages this internally.
        payload = {
            "model":      model,
            "messages":   messages,
            "stream":     False,
            "max_tokens": 1,
        }
        try:
            resp = requests.post(f"{url}/v1/chat/completions", json=payload, timeout=180)
            resp.raise_for_status()
            print(f"[LLM] '{model}' ready (OpenAI-compatible server).")
            return True
        except Exception as e:
            print(f"[LLM] Warmup failed (non-fatal): {e}")
            return False

    # ── Ollama ──────────────────────────────────────────────────────────────
    payload = {
        "model":      model,
        "messages":   messages,
        "stream":     False,
        "keep_alive": -1,
        # num_gpu:99 → push ALL transformer layers to GPU (Ollama caps at available)
        # This is safe even without a GPU — Ollama silently ignores if n_gpu_layers=0
        "options":    {"num_predict": 1, "num_gpu": 99},
    }
    try:
        resp = requests.post(f"{url}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
        print(f"[LLM] '{model}' loaded and KV cache primed.")
        return True
    except Exception as e:
        print(f"[LLM] Warmup failed (non-fatal): {e}")
        return False


def check_model_available(log: Callable | None = None) -> bool:
    """
    Returns True if the configured model is already pulled in Ollama.
    Logs an actionable warning (to console + optional UI callback) if not.
    Always returns True for non-Ollama providers (cannot inspect their model list).
    """
    if get_llm_provider() != "ollama":
        return True

    url, model = get_llm_settings()
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        resp.raise_for_status()
        pulled = [m.get("name", "") for m in resp.json().get("models", [])]
        model_base = model.split(":")[0]
        found = any(
            m == model or m == model_base or m.startswith(model_base + ":")
            for m in pulled
        )
        if not found:
            available = ", ".join(pulled) if pulled else "none"
            warn = (
                f"WRN: Model '{model}' is not pulled in Ollama.\n"
                f"     Available: {available}\n"
                f"     Fix: ollama pull {model}"
            )
            print(warn)
            if log:
                log(f"WRN: '{model}' not found — run: ollama pull {model}")
        return found
    except Exception:
        return True   # Ollama might still be starting up; non-blocking


def get_llm_settings() -> tuple[str, str]:
    """Returns (base_url, model_name)."""
    cfg   = _load_config()
    url   = cfg.get("llm_url",   _DEFAULTS["llm_url"]).rstrip("/")
    model = cfg.get("llm_model", _DEFAULTS["llm_model"])
    return url, model


def _retryable_llm_status(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return (
        "429" in msg
        or "500" in msg
        or "502" in msg
        or "503" in msg
        or "504" in msg
        or "connection reset" in msg
        or "timeout" in msg
        or "timed out" in msg
        or "try again" in msg
        or "temporar" in msg
    )


def _post_with_retry(endpoint: str, payload: dict, timeout: int, *, max_attempts: int = 4, cancellation_event=None) -> requests.Response:
    """Use bounded retry only for transient request failures.

    Cancellation, invalid payloads, and user-supplied bad calls never retry.
    """
    last_exc: BaseException | None = None
    delay = 0.25
    for attempt in range(1, max_attempts + 1):
        if cancellation_event and cancellation_event.is_set():
            raise RuntimeError("LLM request cancelled")
        try:
            resp = requests.post(endpoint, json=payload, timeout=timeout)
            if resp.status_code in {429, 500, 502, 503, 504}:
                raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp
        except BaseException as exc:
            # Never retry explicit cancellation or an invalid request.
            if cancellation_event and cancellation_event.is_set():
                raise RuntimeError("LLM request cancelled")
            if isinstance(exc, requests.exceptions.Timeout):
                last_exc = exc
            elif isinstance(exc, requests.exceptions.ConnectionError):
                last_exc = exc
            elif isinstance(exc, requests.exceptions.HTTPError):
                status = getattr(exc.response, "status_code", None)
                if status in {429, 500, 502, 503, 504}:
                    last_exc = exc
                else:
                    raise RuntimeError(f"LLM HTTP failure: {status}")
            else:
                # A caller error is not transient.
                raise RuntimeError(f"LLM call failed: {exc}")
            if attempt >= max_attempts:
                raise RuntimeError(f"LLM call failed after transient retry budget: {exc}")
            # Prefer bounded exponential backoff with jitter.
            time.sleep(delay + random.uniform(0.0, 0.25))
            delay = min(delay * 2.0, 2.0)
    if last_exc:
        raise RuntimeError(f"LLM call failed after transient retry budget: {last_exc}")
    raise RuntimeError("LLM call failed after transient retry budget")


def call_llm(
    messages: list,
    tools:    list | None = None,
    timeout:  int = 120,
) -> dict:
    """
    Non-streaming chat request.  Routes to Ollama or OpenAI-compatible backend.

    Returns:
        {"content": str, "tool_calls": list}
    """
    url, model = get_llm_settings()
    provider   = get_llm_provider()

    if provider == "openai":
        endpoint = f"{url}/v1/chat/completions"
        payload: dict = {
            "model":      model,
            "messages":   messages,
            "stream":     False,
            "max_tokens": 150,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = "auto"
        try:
            resp = _post_with_retry(endpoint, payload, timeout, max_attempts=4)
            choice = resp.json().get("choices", [{}])[0]
            msg    = choice.get("message", {})
            # OpenAI tool_calls format → normalise to Ollama-style
            raw_tc  = msg.get("tool_calls") or []
            tc_list = [
                {
                    "id":       t.get("id", ""),
                    "function": {
                        "name":      t["function"]["name"],
                        "arguments": (
                            json.loads(t["function"]["arguments"])
                            if isinstance(t["function"].get("arguments"), str)
                            else t["function"].get("arguments", {})
                        ),
                    },
                }
                for t in raw_tc
            ]
            return {
                "content":    (msg.get("content") or "").strip(),
                "tool_calls": tc_list,
            }
        except LLMFailureState:
            raise
        except Exception as e:
            raise LLMFailureState(f"OpenAI-compatible LLM call failed: {e}")

    # ── Ollama ──────────────────────────────────────────────────────────────
    endpoint = f"{url}/api/chat"
    payload = {
        "model":      model,
        "messages":   messages,
        "stream":     False,
        "keep_alive": -1,
        "options":    {"num_predict": 150, "num_gpu": 99},
    }
    if tools:
        payload["tools"] = tools

    try:
        resp = _post_with_retry(endpoint, payload, timeout, max_attempts=4)
        data = resp.json()
        msg  = data.get("message", {})
        return {
            "content":    (msg.get("content") or "").strip(),
            "tool_calls": msg.get("tool_calls") or [],
        }
    except requests.exceptions.ConnectionError as e:
        print(f"[LLM] ConnectionError — trying to restart Ollama… ({e})")
        if ensure_ollama_running():
            try:
                resp = _post_with_retry(endpoint, payload, timeout, max_attempts=4)
                data = resp.json()
                msg  = data.get("message", {})
                return {
                    "content":    (msg.get("content") or "").strip(),
                    "tool_calls": msg.get("tool_calls") or [],
                }
            except Exception:
                pass
        raise LLMFailureState(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed and run: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise LLMFailureState("Ollama request timed out after 120 s.", retryable=True)
    except requests.exceptions.HTTPError as e:
        print(f"[LLM] HTTPError: {e.response.status_code} — {e.response.text[:200]}")
        raise LLMFailureState(f"Ollama HTTP error: {e.response.status_code}", retryable=False)
    except LLMFailureState:
        raise
    except Exception as e:
        print(f"[LLM] Unexpected error: {type(e).__name__}: {e}")
        raise LLMFailureState(f"LLM call failed: {e}", retryable=False)


def call_llm_text(
    prompt:  str,
    system:  str | None = None,
    model:   str | None = None,
    timeout: int = 120,
) -> str:
    """
    Simple text-only generation (no tools).
    Used by planner, executor, error_handler, code_helper, dev_agent.
    """
    url, default_model = get_llm_settings()
    endpoint = f"{url}/api/chat"
    m        = model or default_model

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": m, "messages": messages, "stream": False, "keep_alive": -1, "options": {"num_predict": 600}}

    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        resp.raise_for_status()
        return (resp.json().get("message", {}).get("content") or "").strip()
    except requests.exceptions.ConnectionError:
        if ensure_ollama_running():
            try:
                resp = requests.post(endpoint, json=payload, timeout=timeout)
                resp.raise_for_status()
                return (resp.json().get("message", {}).get("content") or "").strip()
            except Exception:
                pass
        raise RuntimeError(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed and run: ollama serve"
        )
    except Exception as e:
        raise RuntimeError(f"LLM text call failed: {e}")


def _stream_openai(
    messages: list,
    tools:    list | None,
    timeout:  int,
) -> Generator[dict, None, None]:
    """
    Streaming backend for OpenAI-compatible servers (LM Studio, LocalAI, Jan…).

    Parses Server-Sent Events (SSE) and accumulates streaming tool-call fragments
    so the output format is identical to the Ollama backend.
    """
    url, model = get_llm_settings()
    endpoint   = f"{url}/v1/chat/completions"

    payload: dict = {
        "model":      model,
        "messages":   messages,
        "stream":     True,
        "max_tokens": 150,
    }
    if tools:
        payload["tools"]       = tools
        payload["tool_choice"] = "auto"

    try:
        with requests.post(endpoint, json=payload, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            full_content = ""
            buf          = ""
            # tool_call fragments: index → {"id", "function": {"name", "arguments"}}
            tc_fragments: dict[int, dict] = {}

            for raw in resp.iter_lines():
                if not raw:
                    continue
                # SSE lines look like: b"data: {...}" or b"data: [DONE]"
                line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choice = chunk.get("choices", [{}])[0]
                delta  = choice.get("delta", {})
                text   = delta.get("content") or ""

                full_content += text
                buf          += text

                # Accumulate sentence boundaries for streaming TTS
                while True:
                    m = _SENT_END.search(buf)
                    if not m:
                        break
                    sentence = buf[: m.start() + 1].strip()
                    buf      = buf[m.end():]
                    if sentence:
                        yield {"type": "sentence", "text": sentence}

                # Accumulate streaming tool-call fragments
                for tc in (delta.get("tool_calls") or []):
                    idx = tc.get("index", 0)
                    if idx not in tc_fragments:
                        tc_fragments[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                    frag = tc_fragments[idx]
                    frag["id"] = frag["id"] or tc.get("id", "")
                    fn = tc.get("function", {})
                    frag["function"]["name"]      += fn.get("name") or ""
                    frag["function"]["arguments"] += fn.get("arguments") or ""

                finish = choice.get("finish_reason")
                if finish in ("stop", "tool_calls", "length"):
                    break

            # Flush any trailing content
            if buf.strip():
                yield {"type": "sentence", "text": buf.strip()}

            # Parse accumulated tool-call argument strings → dicts
            tool_calls: list = []
            for idx in sorted(tc_fragments):
                frag = tc_fragments[idx]
                args = frag["function"]["arguments"]
                try:
                    args = json.loads(args)
                except Exception:
                    pass   # leave as raw string; _execute_tool handles it
                tool_calls.append({
                    "id":       frag["id"],
                    "function": {"name": frag["function"]["name"], "arguments": args},
                })

            yield {
                "type":       "done",
                "content":    full_content.strip(),
                "tool_calls": tool_calls,
            }

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach OpenAI-compatible server at {url}.\n"
            "Make sure LM Studio / LocalAI / Jan is running and the server is started."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("OpenAI-compatible stream timed out.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"OpenAI-compatible HTTP error: {e.response.status_code}")
    except Exception as e:
        raise RuntimeError(f"OpenAI-compatible stream failed: {e}")


def call_llm_stream(
    messages: list,
    tools:    list | None = None,
    timeout:  int = 120,
) -> Generator[dict, None, None]:
    """
    Streaming chat request.  Routes to Ollama or OpenAI-compatible backend.

    Yields:
        {"type": "sentence", "text": str}   — each complete sentence as it arrives
        {"type": "done", "content": str, "tool_calls": list}  — when stream ends

    Sentences are split on [.!?] + whitespace so TTS can start immediately.
    Tool calls always appear in the final "done" event.
    """
    provider = get_llm_provider()
    if provider == "openai":
        yield from _stream_openai(messages, tools, timeout)
        return

    url, model = get_llm_settings()
    endpoint   = f"{url}/api/chat"

    payload: dict = {
        "model":      model,
        "messages":   messages,
        "stream":     True,
        "keep_alive": -1,
        # 150 tokens ≈ 100 words ≈ 3-4 sentences — enough for any voice reply.
        # num_gpu:99 pushes all layers to GPU; num_thread removed (Ollama auto-tunes).
        "options":    {"num_predict": 150, "num_gpu": 99},
    }
    if tools:
        payload["tools"] = tools

    def _do_stream() -> Generator[dict, None, None]:
        with requests.post(endpoint, json=payload, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            full_content = ""
            tool_calls:  list = []
            buf          = ""

            for raw in resp.iter_lines():
                if not raw:
                    continue
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg   = chunk.get("message", {})
                delta = msg.get("content") or ""

                full_content += delta
                buf          += delta

                # Yield complete sentences as they accumulate
                while True:
                    m = _SENT_END.search(buf)
                    if not m:
                        break
                    sentence = buf[: m.start() + 1].strip()
                    buf      = buf[m.end() :]
                    if sentence:
                        yield {"type": "sentence", "text": sentence}

                tc = msg.get("tool_calls")
                if tc:
                    tool_calls.extend(tc)

                if chunk.get("done"):
                    if buf.strip():
                        yield {"type": "sentence", "text": buf.strip()}

                    yield {
                        "type":       "done",
                        "content":    full_content.strip(),
                        "tool_calls": tool_calls,
                    }
                    return

    try:
        yield from _do_stream()
    except requests.exceptions.ConnectionError as e:
        print(f"[LLM] Stream ConnectionError — trying to restart Ollama… ({e})")
        if ensure_ollama_running():
            yield from _do_stream()
            return
        raise RuntimeError(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed and run: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama stream timed out.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e.response.status_code}")
    except Exception as e:
        print(f"[LLM] Stream error: {type(e).__name__}: {e}")
        raise RuntimeError(f"LLM stream failed: {e}")
