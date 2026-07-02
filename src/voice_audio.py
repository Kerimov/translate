"""Voice-focused processing for game loopback (reduce SFX, keep speech)."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt

SAMPLE_RATE = 16_000
_SPEECH_LOW = 300.0
_SPEECH_HIGH = 3_400.0


def _bandpass(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    if audio.size < 16:
        return audio.astype(np.float32, copy=False)
    nyquist = sample_rate / 2
    low = max(_SPEECH_LOW / nyquist, 0.01)
    high = min(_SPEECH_HIGH / nyquist, 0.99)
    if low >= high:
        return audio.astype(np.float32, copy=False)
    b, a = butter(4, [low, high], btype="band")
    return filtfilt(b, a, audio.astype(np.float64)).astype(np.float32)


def speech_energy(frame: np.ndarray, sample_rate: int) -> float:
    """Energy in speech band — less sensitive to explosions than raw RMS."""
    if frame.size < 8:
        return 0.0
    filtered = _bandpass(frame, sample_rate)
    return float(np.sqrt(np.mean(filtered.astype(np.float64) ** 2)))


def enhance_voice(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Band-pass speech frequencies and normalize."""
    if audio.size == 0:
        return audio
    voiced = _bandpass(audio, sample_rate)
    peak = float(np.max(np.abs(voiced)))
    if peak < 1e-5:
        return voiced
    return (voiced * (0.9 / peak)).astype(np.float32)


def is_mostly_speech(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bool:
    """Skip segments dominated by non-speech game noise."""
    if audio.size < sample_rate // 10:
        return False
    raw = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    voiced = float(np.sqrt(np.mean(_bandpass(audio, sample_rate).astype(np.float64) ** 2)))
    if raw < 0.002:
        return False
    return voiced / (raw + 1e-9) > 0.25
