import threading
import time
from unittest.mock import patch

import pytest
import requests

from core.latency import (
    VoiceTurnTrace,
    BoundedAudioQueue,
    TurnSupervisor,
    LISTENING_WINDOW_MS,
)
from core.llm_client import call_llm, _post_with_retry, LLMFailureState


def test_voice_turn_trace_marks_time_and_cancellation():
    trace = VoiceTurnTrace("turn-abc")
    t1 = trace.mark("wake_word")
    t2 = trace.mark("speech_end")
    assert t2 >= t1
    assert trace.turn_id == "turn-abc"
    assert trace.cancelled() is False
    trace.mark_cancelled()
    assert trace.cancelled() is True


def test_bounded_audio_queue_drops_stale_and_preserves_bounds():
    q = BoundedAudioQueue(maxsize=2)
    q.put_nowait("a")
    q.put_nowait("b")
    q.put_nowait("c")
    assert q.size() == 2
    assert q.get_nowait() == "b"
    assert q.get_nowait() == "c"


def test_bounded_audio_queue_can_be_cleared():
    q = BoundedAudioQueue(maxsize=3)
    q.put_nowait("x")
    q.clear()
    assert q.empty()


def test_bounded_audio_queue_can_drop_oldest_without_losing_newest():
    q = BoundedAudioQueue(maxsize=2)
    q.put_nowait("a")
    q.put_nowait("b")
    q.drop_oldest()
    q.put_nowait("c")
    assert q.size() == 2
    assert q.get_nowait() == "b"
    assert q.get_nowait() == "c"


def test_cancelled_turn_cannot_speak_or_update_the_ui():
    supervisor = TurnSupervisor("turn-cancel-1")
    assert supervisor.speak("hello") is True
    assert supervisor.update_ui("message") is True
    supervisor.cancel()
    assert supervisor.speak("blocked") is False
    assert supervisor.update_ui("blocked") is False
    assert supervisor.cancelled() is True


def test_retry_stops_immediately_on_cancellation():
    cancellation = threading.Event()
    cancellation.set()
    with patch("core.llm_client.requests.post") as fake_post:
        with pytest.raises(RuntimeError, match="cancelled"):
            _post_with_retry("http://example.invalid/v1/chat", {"x": 1}, timeout=10, max_attempts=5, cancellation_event=cancellation)
    fake_post.assert_not_called()


def test_mocked_slow_or_failing_llm_returns_clear_failure_state():
    with patch("core.llm_client.get_llm_provider", return_value="ollama"), \
         patch("core.llm_client.get_llm_settings", return_value=("http://localhost:11434", "test-model")), \
         patch("core.llm_client.requests.post", side_effect=requests.exceptions.Timeout("mock timeout")):
        with pytest.raises(LLMFailureState, match="LLM call failed"):
            call_llm(messages=[{"role": "user", "content": "hello"}], timeout=1)


def test_listening_window_budget_is_a_safe_5_to_7_second_window():
    assert 5000 <= LISTENING_WINDOW_MS <= 7000


def test_stale_results_cannot_overwrite_newer_turn():
    sup = TurnSupervisor("turn-new")
    assert sup.append_result("turn-new", {"value": 1}) is True
    assert sup.append_result("turn-old", {"value": 2}) is False
    assert len(sup.result_events) == 1
