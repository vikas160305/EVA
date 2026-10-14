"""Unit tests for MARK-L Architecture & Performance Upgrades."""

import pytest
from pathlib import Path
from core.intent_router import match_fast_intent
from memory.vector_memory import VectorMemoryStore
from actions.agent_planner import AgentTaskPlanner


def test_fast_intent_router_volume():
    res = match_fast_intent("set volume to 50%")
    assert res is not None
    assert "Volume set to 50%" in res


def test_fast_intent_router_stats():
    res = match_fast_intent("check system stats")
    assert res is not None
    assert "System status" in res


def test_fast_intent_router_unmatched():
    res = match_fast_intent("Tell me a joke about space")
    assert res is None


def test_vector_memory_store(tmp_path: Path):
    store_file = tmp_path / "test_vector_store.json"
    store = VectorMemoryStore(storage_path=store_file)
    
    store.add_document("projects", "mark_l", "Working on MARK-L voice assistant upgrades and RAG memory.")
    store.add_document("identity", "user_name", "User name is John Doe.")
    
    matches = store.search("voice assistant", top_k=1)
    assert len(matches) == 1
    assert matches[0][0]["key"] == "mark_l"


def test_agent_task_planner():
    planner = AgentTaskPlanner("search quantum computing and save report.txt")
    assert len(planner.steps) >= 2
    step = planner.execute_next_step()
    assert step is not None
    assert step.step_id == 1
    planner.mark_completed(1, "Search done")
    assert planner.steps[0].status == "completed"


def test_fast_intent_latency_benchmark(monkeypatch: pytest.MonkeyPatch):
    import time
    from actions import computer_settings
    # Mock OS hardware volume call to isolate intent router matching overhead
    monkeypatch.setattr(computer_settings, "computer_settings", lambda **kw: "Volume set to 80%")

    # Warmup call
    match_fast_intent("set volume to 75%")
    
    t0 = time.perf_counter()
    res = match_fast_intent("set volume to 80%")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert res is not None
    assert elapsed_ms < 30.0, f"Expected sub-30ms router execution, got {elapsed_ms:.2f}ms"


def test_vector_memory_recall_without_truncation(tmp_path: Path):
    store_file = tmp_path / "long_store.json"
    store = VectorMemoryStore(storage_path=store_file)
    long_content = "This is a detailed project notes paragraph. " * 150 + " unique_identifier_keyword " + "Additional long context text. " * 150
    store.add_document("notes", "deep_note", long_content)
    
    results = store.search("unique_identifier_keyword", top_k=1)
    assert len(results) == 1
    assert "unique_identifier_keyword" in results[0][0]["content"]
    assert len(results[0][0]["content"]) > 3000
