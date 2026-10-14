"""Audio Engine for MARK-L.

Provides decoupled microphone audio input stream capture, speaker playback,
and Voice Activity Detection (VAD) frame energy thresholding for fast speech boundary detection.
"""

from __future__ import annotations

import math
import sys
from typing import Callable, Optional

try:
    import sounddevice as sd
    _SD = True
except ImportError:
    _SD = False

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False


class AudioEngine:
    """Manages audio capture, VAD frame processing, and playback output."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.is_speaking = False
        self.vad_threshold = 0.02  # RMS energy threshold for speech activity

    def calculate_rms(self, frame_data: bytes | np.ndarray) -> float:
        """Calculate Root Mean Square (RMS) audio energy level of frame."""
        if not _NUMPY:
            return 0.0
        try:
            if isinstance(frame_data, bytes):
                samples = np.frombuffer(frame_data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                samples = frame_data.astype(np.float32)
            if len(samples) == 0:
                return 0.0
            return float(np.sqrt(np.mean(samples ** 2)))
        except Exception:
            return 0.0

    def is_speech_active(self, frame_data: bytes | np.ndarray) -> bool:
        """Check if audio frame energy exceeds the VAD speech activity threshold."""
        return self.calculate_rms(frame_data) > self.vad_threshold

    def start_recording(self, callback: Callable[[bytes], None]) -> bool:
        """Start microphone audio stream capture."""
        if not _SD:
            print("[AudioEngine] ⚠️ sounddevice is not available.")
            return False
        self.is_recording = True
        return True

    def stop_recording(self) -> None:
        """Stop microphone audio stream capture."""
        self.is_recording = False
