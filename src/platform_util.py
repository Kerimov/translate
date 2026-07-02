from __future__ import annotations

import sys

import numpy as np

SAMPLE_RATE = 16_000


def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    if orig_sr == target_sr or audio.size == 0:
        return audio.astype(np.float32, copy=False)

    target_len = max(1, int(len(audio) * target_sr / orig_sr))
    indices = np.linspace(0, len(audio) - 1, target_len)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)


def default_team_loopback() -> bool:
    raw = __import__("os").getenv("TEAM_LOOPBACK", "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    return is_windows()
