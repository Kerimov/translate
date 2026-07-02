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

    if orig_sr > target_sr and orig_sr % target_sr == 0:
        factor = orig_sr // target_sr
        trimmed = len(audio) - (len(audio) % factor)
        if trimmed <= 0:
            return audio.astype(np.float32, copy=False)
        return audio[:trimmed].reshape(-1, factor).mean(axis=1).astype(np.float32)

    from math import gcd

    from scipy.signal import resample_poly

    divisor = gcd(orig_sr, target_sr)
    return resample_poly(audio, target_sr // divisor, orig_sr // divisor).astype(np.float32)


def normalize_audio(audio: np.ndarray, target_peak: float = 0.92) -> np.ndarray:
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-6:
        return audio.astype(np.float32, copy=False)
    return (audio * (target_peak / peak)).astype(np.float32)


def default_team_loopback() -> bool:
    raw = __import__("os").getenv("TEAM_LOOPBACK", "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    return is_windows()
