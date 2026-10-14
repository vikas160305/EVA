import threading
import time

import pytest

from actions import web_search as ws
from actions import image_downloader as imgdl


def test_fast_valid_provider_plus_slow_timeout_provider_returns_fast_result():
    def provider_fast(query, cancel_event=None):
        time.sleep(0.02)
        return [ws.SearchResult(title="Fresh result", url="https://example.com", snippet="fresh", provider="fast", score=0.9)]

    def provider_timeout(query, cancel_event=None):
        if cancel_event:
            cancel_event.wait(0.05)
            if cancel_event.is_set():
                raise TimeoutError("cancelled")
        raise TimeoutError("provider read timeout")

    cancel = threading.Event()
    orch = ws.SearchOrchestrator(providers={"fast": provider_fast, "fallback": provider_timeout})
    results = orch.run("latest AI news", mode="news", providers=["fast", "fallback"], cancellation_event=cancel)
    assert len(results) == 1
    assert results[0].title == "Fresh result"
    assert orch.failures["fallback"] == "provider-timeout"


def test_fast_valid_provider_plus_exception_returns_fast_result():
    def provider_fast(query, cancel_event=None):
        time.sleep(0.02)
        return [ws.SearchResult(title="Fresh result", url="https://example.com", snippet="fresh", provider="fast", score=0.9)]

    def provider_exception(query, cancel_event=None):
        raise ValueError("provider blew up")

    cancel = threading.Event()
    orch = ws.SearchOrchestrator(providers={"fast": provider_fast, "fallback": provider_exception})
    results = orch.run("latest AI news", mode="news", providers=["fast", "fallback"], cancellation_event=cancel)
    assert len(results) == 1
    assert results[0].title == "Fresh result"
    assert orch.failures["fallback"] == "provider-failed"


def test_all_providers_fail_returns_clear_failure_state():
    def provider_timeout(query, cancel_event=None):
        raise TimeoutError("provider read timeout")

    def provider_exception(query, cancel_event=None):
        raise RuntimeError("provider exploded")

    cancel = threading.Event()
    orch = ws.SearchOrchestrator(providers={"fallback": provider_timeout, "other": provider_exception})
    results = orch.run("latest AI news", mode="news", providers=["fallback", "other"], cancellation_event=cancel)
    assert results == []
    assert orch.failures["fallback"] == "provider-timeout"
    assert orch.failures["other"] == "provider-failed"


def test_cancellation_stops_orchestration_and_returns_no_stale_result():
    cancel = threading.Event()

    def slow_provider(query, cancel_event=None):
        cancel_event.wait(1.0)
        if cancel_event.is_set():
            raise TimeoutError("cancelled")
        return []

    orch = ws.SearchOrchestrator(providers={"slow": slow_provider})
    cancel.set()
    results = orch.run("cancellation test", mode="search", providers=["slow"], cancellation_event=cancel)
    assert results == []
    assert orch.cancelled is True


def test_duplicate_valid_results_remain_deduplicated_despite_another_provider_failure():
    def provider_fast(query, cancel_event=None):
        return [
            ws.SearchResult(title="Fresh result", url="https://example.com", snippet="fresh", provider="fast", score=0.9),
            ws.SearchResult(title="Fresh result", url="https://example.com", snippet="fresh", provider="fast", score=0.9),
        ]

    def provider_exception(query, cancel_event=None):
        raise ValueError("provider blew up")

    cancel = threading.Event()
    orch = ws.SearchOrchestrator(providers={"fast": provider_fast, "fallback": provider_exception})
    results = orch.run("latest AI news", mode="news", providers=["fast", "fallback"], cancellation_event=cancel)
    assert len(results) == 1
    assert results[0].url == "https://example.com"
    assert orch.failures["fallback"] == "provider-failed"


def test_search_cache_hit_and_expiry(monkeypatch):
    cache = ws.SearchResultCache(ttl_seconds=0.1)
    key = cache.key(query="latest AI", mode="news", providers=["gemini", "ddg"])
    cache.store(key, [ws.SearchResult(title="Cached", url="https://cached.example", snippet="cached", provider="ddg", score=0.5)])
    assert cache.get(key)
    time.sleep(0.12)
    assert cache.get(key) is None


def test_rank_dedup_and_image_url_validation(monkeypatch):
    raw = [
        {"title": "News", "snippet": "same", "url": "https://example.com/one"},
        {"title": "News", "snippet": "same", "url": "https://example.com/one"},
        {"title": "News", "snippet": "spam", "url": "http://127.0.0.1/private"},
    ]
    ranked = ws.rank_and_dedupe(raw, provider="ddg", mode="search")
    assert len(ranked) == 1
    assert ranked[0].url == "https://example.com/one"
    assert ranked[0].provider == "ddg"


def test_image_provider_timeout_clear_failure_message(monkeypatch):
    def fail(url):
        raise TimeoutError("image provider read timeout")

    monkeypatch.setattr(imgdl, "_request", fail)
    with pytest.raises(TimeoutError):
        imgdl._google_images("test")


def test_stale_result_cannot_overwrite_newer_turn(monkeypatch):
    result_box = ws.StaleGuard("turn-new")
    assert result_box.accept("turn-new", {"ok": True}) is True
    assert result_box.accept("turn-old", {"ok": True}) is False
