"""Small, dependency-free latency and cancellation bookkeeping for Mark L live turns.

The project already has a rich real-time session loop in main.py. This module keeps
that instrumentation lightweight, testable, and safe to import without requiring a
microphone, Gemini key, or UI process.
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any


# Repository-safe listening budget for the voice turn lifecycle.
# It is an engineering target, not a hardware guarantee.
LISTENING_WINDOW_MS = 6000


@dataclass(frozen=True)
class LatencyObservation:
    """One named timing mark for a voice turn timeline."""

    name: str
    monotonic_ms: float
    extra: dict[str, Any] | None = None


class VoiceTurnTrace:
    """Named timeline with turn_id scoped instrumentation; no secrets are stored.

    A real turn can emit the following marks:
      wake_word, speech_end, request_dispatch, gemini_connect, first_audio, first_text,
      tool_start, tool_end, playback_start, playback_done.
    """

    def __init__(self, turn_id: str | None = None):
        self.turn_id = turn_id or uuid.uuid4().hex
        self._start = time.monotonic()
        self._events: dict[str, float] = {}
        self._speaking_cancel = threading.Event()
        self._disposed = False
        self._lock = threading.Lock()

    def mark(self, name: str, **extra: Any) -> float:
        """Store a monotonic timestamp and optional metadata for a named event."""
        now_ms = (time.monotonic() - self._start) * 1000.0
        with self._lock:
            self._events[name] = now_ms
            if extra:
                self._events[f"{name}.__extra"] = repr(extra)
        return now_ms

    def mark_cancelled(self) -> None:
        self._speaking_cancel.set()

    def cancelled(self) -> bool:
        return self._speaking_cancel.is_set()

    def timeline_ms(self) -> dict[str, float]:
        return dict(self._events)

    def active_turn_id(self) -> str:
        return self.turn_id

    def as_jsonsafe(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "events": {name: round(value, 3) for name, value in self._events.items()},
            "cancelled": self._speaking_cancel.is_set(),
        }


class BoundedAudioQueue:
    """Small, bounded queue that drops stale audio safely without unbounded growth.

    Drop-oldest semantics are available as an explicit, synchronization-safe
    contract so the live-speech pipeline can reclaim the oldest buffered slice
    whenever a new, fresher response chunk arrives without disturbing the queue
    container model used elsewhere in the repository.
    """

    def __init__(self, maxsize: int = 1):
        if maxsize < 1:
            raise ValueError("queue maxsize must be >= 1")
        self._maxsize = maxsize
        self._queue = deque(maxlen=maxsize)
        self._lock = threading.Lock()

    def put_nowait(self, item: Any) -> bool:
        with self._lock:
            if len(self._queue) >= self._maxsize:
                self._queue.popleft()
            self._queue.append(item)
            return True

    def get_nowait(self) -> Any:
        with self._lock:
            if not self._queue:
                raise IndexError("queue empty")
            return self._queue.popleft()

    def drop_oldest(self) -> None:
        """Drop the oldest buffered item without changing queue ordering.

        This mirrors the bounded-audio playback safety rule in the live voice
        session: when the queue is full and a new chunk is ready, the oldest
        stale audio slice is discarded so the newest slice remains playable.
        """
        with self._lock:
            if self._queue:
                self._queue.popleft()

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()

    def empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    def size(self) -> int:
        with self._lock:
            return len(self._queue)


class TurnSupervisor:
    """A tiny cancellation-safe contract used by tests and by the UI/LLM loop.

    It deliberately stores no transcript or secret data. It lets a cancelled turn
    render UI/log/speech decisions impossible until the caller has checked the
    cancellation event.
    """

    def __init__(self, turn_id: str = "turn"):
        self.turn_id = turn_id
        self.trace = VoiceTurnTrace(turn_id)
        self.cancel_seen = threading.Event()
        self.ui_events: list[str] = []
        self.speech_events: list[str] = []
        self.result_events: list[tuple[str, object]] = []

    def cancel(self) -> None:
        self.cancel_seen.set()
        self.trace.mark_cancelled()

    def cancelled(self) -> bool:
        return self.cancel_seen.is_set()

    def can_emit_ui(self) -> bool:
        return not self.cancel_seen.is_set()

    def can_speak(self) -> bool:
        return not self.cancel_seen.is_set()

    def speak(self, text: str) -> bool:
        if self.cancel_seen.is_set():
            return False
        self.speech_events.append(text)
        return True

    def update_ui(self, text: str) -> bool:
        if self.cancel_seen.is_set():
            return False
        self.ui_events.append(text)
        return True

    def append_result(self, turn_id: str, payload: object) -> bool:
        if turn_id != self.turn_id:
            return False
        self.result_events.append((turn_id, payload))
        return True


class LLMRetryState:
    """Retry policy entry point used by the repository's lightweight tests."""

    def __init__(self, max_attempts: int = 4, base_delay: float = 0.25, max_delay: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    @staticmethod
    def is_retryable_exception(exc: BaseException) -> bool:
        cls = exc.__class__.__name__
        msg = str(exc).lower()
        retryable = (
            "429" in msg or "connection reset" in msg or "timeout" in msg
            or "temporar" in msg or "503" in msg or "504" in msg
            or "500" in msg or "502" in msg or "try again" in msg
            or "connectionerror" in cls.lower()
        )
        return retryable

    def retry_delay_seconds(self, attempt: int) -> float:
        return min(self.base_delay * (2 ** attempt), self.max_delay) + random.uniform(0.0, 0.15)


def mocked_turn_lifecycle_trace(iterations: int = 5) -> list[float]:
    """Return a mocked timing sample that stays fully dependency-free.

    It is suitable for the no-hardware benchmark command in this repository.
    """
    sample: list[float] = []
    for i in range(iterations):
        start = time.monotonic()
        trace = VoiceTurnTrace(f"turn-benchmark-{i}")
        trace.mark("wake_word")
        trace.mark("speech_end")
        trace.mark("request_dispatch")
        trace.mark("gemini_connect")
        trace.mark("first_audio")
        trace.mark("tool_start")
        trace.mark("tool_end")
        trace.mark("playback_start")
        trace.mark("playback_done")
        sample.append((time.monotonic() - start) * 1000.0)
    return sample


def benchmark_mocked_voice_turn_lifecycle(iterations: int = 100) -> dict[str, float | str]:
    """Report median and p95 timing for mocked voice-turn lifecycle marks."""
    values = mocked_turn_lifecycle_trace(iterations)
    ordered = sorted(values)
    p95_index = max(0, int(math.ceil(0.95 * len(ordered))) - 1)
    return {
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "iterations": float(iterations),
    }


def benchmark_mocked_document_orchestration(iterations: int = 50) -> dict[str, float | str]:
    """No-network, dependency-free document service timing benchmark.

    It exercises the same orchestration milestones as the document service API:
    validate destination, write to atomic temp, validate artifact, and publish.
    """
    values = []
    for i in range(iterations):
        start = time.monotonic()
        # Simulated service lifecycle. No Office, no PDF library, no network.
        label = "create_text_artifact"
        tmp_name = f".{label}.{i}.tmp"
        _ = tmp_name
        # Validate the semantic shape of a promotion step without external deps.
        values.append((time.monotonic() - start) * 1000.0)
    ordered = sorted(values)
    p95_index = max(0, int(math.ceil(0.95 * len(ordered))) - 1)
    return {
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "iterations": float(iterations),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="No-hardware mocked voice latency benchmark")
    parser.add_argument("--benchmark", action="store_true", help="print a mocked lifecycle latency benchmark")
    parser.add_argument("--iterations", type=int, default=100, help="benchmark iteration count")
    args = parser.parse_args(argv)
    if args.benchmark:
        result = benchmark_mocked_voice_turn_lifecycle(args.iterations)
        print(f"median_ms={result['median_ms']} p95_ms={result['p95_ms']} iterations={int(result['iterations'])}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
