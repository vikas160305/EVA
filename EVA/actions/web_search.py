#web_search.py
import json
import sys
import threading
import time
import hashlib
import ipaddress
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


@dataclass
class SearchResult:
    title: str = ""
    url: str = ""
    snippet: str = ""
    provider: str = ""
    score: float = 0.0


class SearchOrchestrator:
    """Provider orchestrator that isolates each provider and preserves results.

    Phase 5 hardening note: provider errors remain isolated and converted to
    internal-safe labels. SearchResult objects stay recordable and deduplicated
    without leaking provider exception details into the UI output.
    """

    def __init__(self, providers: dict[str, Callable] | None = None):
        self.providers = providers or {}
        self.failures: dict[str, str] = {}
        self.last_results: list[SearchResult] = []
        self.cancelled = False

    def _invoke_provider(self, func: Callable, query: str, cancellation_event: threading.Event | None = None):
        try:
            if hasattr(func, "__code__") and "cancel_event" in func.__code__.co_varnames:
                return func(query, cancel_event=cancellation_event)
        except TypeError:
            pass
        try:
            return func(query)
        except TypeError:
            try:
                return func()
            except TypeError:
                return []

    def _safe_failure_label(self, exc: BaseException) -> str:
        msg = str(exc).lower()
        if "cancel" in msg or "interrupt" in msg:
            return "cancelled"
        if "timeout" in msg or "timed out" in msg or "read timeout" in msg:
            return "provider-timeout"
        return "provider-failed"

    def run(self, query: str, mode: str = "search", providers: list[str] | None = None,
            cancellation_event: threading.Event | None = None) -> list[SearchResult]:
        self.failures = {}
        self.last_results = []
        self.cancelled = False

        if cancellation_event and cancellation_event.is_set():
            self.cancelled = True
            return []

        provider_names = list(providers or list(self.providers.keys()))
        if not provider_names:
            return []

        successful: list[SearchResult] = []
        any_seen_success = False

        for name in provider_names:
            if cancellation_event and cancellation_event.is_set():
                self.cancelled = True
                return []

            func = self.providers.get(name)
            if func is None:
                self.failures[name] = "missing-provider"
                continue

            try:
                raw = self._invoke_provider(func, query, cancellation_event)
                if isinstance(raw, str):
                    raw = [{"title": raw, "snippet": raw, "url": "https://example.invalid", "provider": name}]
                results = rank_and_dedupe(raw, provider=name, mode=mode)
                if not results:
                    self.failures[name] = "invalid-provider-output"
                    continue
                successful.extend(results)
                any_seen_success = True
            except TimeoutError:
                self.failures[name] = "provider-timeout"
            except Exception as exc:
                self.failures[name] = self._safe_failure_label(exc)
                print(f"[WebSearch] ⚠️ provider={name} failed safely: {self.failures[name]}")

        if cancellation_event and cancellation_event.is_set():
            self.cancelled = True
            return []

        if any_seen_success:
            final = rank_and_dedupe(successful, provider="merged", mode=mode)
            self.last_results = final
            return final

        return []


class SearchResultCache:
    """Tiny in-process TTL cache for web search result objects."""

    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._data: dict[str, tuple[float, list[SearchResult]]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def key(query: str, mode: str = "search", providers: list[str] | tuple[str, ...] | None = None) -> str:
        providers = providers or []
        raw = f"{query}|{mode}|{','.join(sorted(str(p) for p in providers))}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def store(self, key: str, results: list[SearchResult]) -> None:
        with self._lock:
            self._data[key] = (time.time(), list(results))

    def get(self, key: str) -> list[SearchResult] | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, results = item
            if time.time() - expires_at > self.ttl_seconds:
                del self._data[key]
                return None
            return list(results)


class StaleGuard:
    """Reject provider results from older turns than the active turn token."""

    def __init__(self, current_turn_id: str = ""):
        self.current_turn_id = current_turn_id

    def accept(self, turn_id: str, payload: Any) -> bool:
        if turn_id != self.current_turn_id:
            return False
        return True


def _is_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"}:
            return False
        try:
            addresses = {ipaddress.ip_address(host)}
        except ValueError:
            try:
                addresses = {
                    ipaddress.ip_address(item[4][0])
                    for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
                }
            except Exception:
                return False
        return all(
            not addr.is_private and not addr.is_loopback and not addr.is_link_local and not addr.is_reserved
            for addr in addresses
        )
    except Exception:
        return False


def _normalise_url(url: str) -> str:
    try:
        return url.strip().strip('"\'') if url else ""
    except Exception:
        return ""


def rank_and_dedupe(raw: list[dict] | list[SearchResult], provider: str = "ddg", mode: str = "search") -> list[SearchResult]:
    """Rank, clean, and deduplicate search result dictionaries into SearchResult objects."""
    seen: set[str] = set()
    candidates: list[SearchResult] = []
    for item in raw:
        if isinstance(item, SearchResult):
            record = item
            url = item.url or ""
            title = item.title or ""
            snippet = item.snippet or ""
        else:
            record = item
            url = str(record.get("url", "") or "")
            title = str(record.get("title", "") or "")
            snippet = str(record.get("snippet", "") or record.get("body", "") or "")

        url = _normalise_url(url)
        if not _is_public_url(url):
            continue
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        score = 0.3 + min(0.5, len(title) / 80.0) + min(0.2, len(snippet) / 160.0)
        if mode == "news":
            score += 0.1
        if provider:
            score += 0.05
        candidates.append(SearchResult(title=title, url=url, snippet=snippet, provider=provider, score=score))

    candidates.sort(key=lambda r: r.score, reverse=True)
    return candidates

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
GEMINI_SEARCH_MODEL = "gemini-3.6-flash"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _gemini_search(query: str) -> str:
    from google import genai

    client   = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model=GEMINI_SEARCH_MODEL,
        contents=query,
        config={"tools": [{"google_search": {}}]},
    )

    text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            text += part.text

    text = text.strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title":   r.get("title",  ""),
                "snippet": r.get("body",   ""),
                "url":     r.get("href",   ""),
            })
    return results


def _ddg_news(query: str, max_results: int = 8) -> list[dict]:
    """DDG news search — returns actual articles, not website homepages."""
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("url",    ""),
                    "source":  r.get("source", ""),
                })
    except Exception as e:
        print(f"[WebSearch] ⚠️ DDG news() failed ({e}) — falling back to text search")
        results = _ddg_search(query, max_results=max_results)
    return results


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   Source: {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_news(query: str, results: list[dict]) -> str:
    if not results:
        return f"No news found for: {query}"

    lines = [f"Latest news: {query}\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        if not title:
            continue
        src = f"  [{r['source']}]" if r.get("source") else ""
        lines.append(f"{i}. {title}{src}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:140]}")
        if r.get("url"):
            lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


# ── Briefing helper ────────────────────────────────────────────────────────────

def _gemini_headlines(n: int = 5) -> tuple[list[str], str]:
    """
    Fetches current headlines via Gemini grounded search.
    Optimised for speed: minimal prompt + strict token cap.
    Returns (headline_list, raw_text_for_display).
    """
    import re
    from google import genai

    client = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model=GEMINI_SEARCH_MODEL,
        contents=f"Current world news: {n} headlines. Numbered list, titles only.",
        config={"tools": [{"google_search": {}}]},
    )

    raw = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            raw += part.text

    headlines = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Only accept lines that begin with a number — skips preamble/closing sentences
        if not re.match(r'^[\d]+[.\)\-]', line):
            continue
        clean = re.sub(r'^[\d]+[.\)\-]\s*', '', line)
        clean = re.sub(r'^\*+\s*',          '', clean).strip()
        if clean and len(clean) > 10:
            headlines.append(clean)

    return headlines[:n], raw.strip()


# ── Modes ──────────────────────────────────────────────────────────────────────

def _search(query: str) -> str:
    """Default search — Gemini grounded, DDG fallback."""
    try:
        return _gemini_search(query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Gemini failed ({e}) — trying DDG...")
        results = _ddg_search(query)
        return _format_ddg(query, results)


def _news(query: str) -> str:
    """
    Runs Gemini grounded search AND DDG news in parallel.
    Returns whichever delivers a valid result first; cancels the other.
    """
    import threading

    gemini_query = f"latest news today: {query}" if query else "top world news today"
    ddg_query    = query if query else "world news today"

    result_box  = [None]   # first valid result lands here
    lock        = threading.Lock()
    done_evt    = threading.Event()
    failures    = [0]

    def _store(r: str) -> None:
        if r and len(r) > 60:
            with lock:
                if result_box[0] is None:
                    result_box[0] = r
            done_evt.set()
        else:
            with lock:
                failures[0] += 1
                if failures[0] >= 2:   # both failed — unblock caller
                    done_evt.set()

    def _try_gemini():
        try:
            _store(_gemini_search(gemini_query))
        except Exception as e:
            print(f"[WebSearch] ⚠️ Gemini news failed ({e})")
            _store("")

    def _try_ddg():
        try:
            results = _ddg_news(ddg_query, max_results=8)
            _store(_format_news(ddg_query, results))
        except Exception as e:
            print(f"[WebSearch] ⚠️ DDG news failed ({e})")
            _store("")

    threading.Thread(target=_try_gemini, daemon=True).start()
    threading.Thread(target=_try_ddg,    daemon=True).start()

    done_evt.wait(timeout=10.0)
    return result_box[0] or f"No news found for: {query}"


def _research(query: str) -> str:
    """
    Deep dive — asks Gemini for a comprehensive answer with context.
    Falls back to a wider DDG fetch.
    """
    research_query = (
        f"Comprehensive, detailed explanation of: {query}. "
        "Include background context, key facts, current state, and important nuances."
    )
    try:
        return _gemini_search(research_query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Research Gemini failed ({e}) — DDG fallback...")
        results = _ddg_search(query, max_results=10)
        return _format_ddg(query, results)


def _price(query: str) -> str:
    """Product price lookup — searches for current market prices."""
    price_query = f"current price of {query} — how much does it cost today"
    try:
        return _gemini_search(price_query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Price Gemini failed ({e}) — DDG fallback...")
        results = _ddg_search(f"{query} price buy", max_results=6)
        return _format_ddg(query, results)


def _compare(items: list[str], aspect: str) -> str:
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Gemini compare failed: {e} — falling back to DDG")

    all_results: dict[str, list] = {}
    for item in items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
            if r.get("url"):
                lines.append(f"    {r['url']}")
    return "\n".join(lines)


# ── Public entry point ─────────────────────────────────────────────────────────

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query."

    if items and mode not in ("compare",):
        mode = "compare"

    if player:
        player.write_log(f"[Search:{mode}] {query or ', '.join(items)}")

    print(f"[WebSearch] 🔍 mode={mode!r}  query={query!r}")

    try:
        if mode == "compare" and items:
            return _compare(items, aspect)
        if mode == "news":
            return _news(query)
        if mode == "research":
            return _research(query)
        if mode == "price":
            return _price(query)
        return _search(query)

    except Exception as e:
        print(f"[WebSearch] ❌ All backends failed: {e}")
        return f"Search failed: {e}"
