from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.platform_util import default_team_loopback

_SLOW_CPU_MODELS = frozenset(
    {"medium.en", "medium", "large-v3", "large-v3-turbo", "large"}
)


def _whisper_backend() -> str:
    device = os.getenv("WHISPER_DEVICE", "auto").strip().lower()
    if device == "cpu":
        return "cpu"
    if device == "cuda":
        return "cuda"
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            import ctypes
            import sys

            if sys.platform == "win32":
                for name in ("cublas64_12.dll", "cublas64_11.dll", "cublas64_10.dll"):
                    try:
                        ctypes.WinDLL(name)
                        return "cuda"
                    except OSError:
                        continue
                return "cpu"
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _resolve_whisper_model_in(explicit: str | None, *, fast_mode: bool, quality_mode: bool) -> str:
    if explicit:
        model = explicit
    elif fast_mode:
        model = "base.en"
    elif quality_mode and _whisper_backend() == "cuda":
        model = "medium.en"
    else:
        model = "small.en"

    if _whisper_backend() == "cpu" and model in _SLOW_CPU_MODELS:
        print(
            f"[config] {model} на CPU слишком медленно для live-чата, "
            "использую small.en (или установите CUDA 12 + WHISPER_DEVICE=cuda)"
        )
        return "small.en"
    return model

load_dotenv()

SAMPLE_RATE = 16_000
CHANNELS = 1
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

PROMPT_EN_TO_RU = (
    "You translate short CS2 / gaming voice callouts from English to Russian. "
    "Output ONLY the Russian translation, nothing else. "
    "Keep it short and natural for fast team comms. "
    "Examples: 'Rush B' -> 'Раш B', 'One HP' -> 'Один HP', 'Flash him' -> 'Флешь его'."
)

PROMPT_RU_TO_EN = (
    "You translate short CS2 / gaming voice callouts from Russian to English. "
    "Output ONLY the English translation, nothing else. "
    "Keep it short and natural for fast team comms. "
    "Examples: 'Раш B' -> 'Rush B', 'Один HP' -> 'One HP', 'Флешь его' -> 'Flash him'."
)


def _parse_device(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else None


def _parse_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    return default


def _parse_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


@dataclass
class Settings:
    deepseek_api_key: str
    team_audio_device: int | None
    team_loopback: bool
    mic_input_device: int | None
    virtual_mic_device: int | None
    whisper_model_in: str
    whisper_model_out: str
    show_original: bool
    enable_outgoing: bool
    tts_voice: str
    segment_silence_frames: int
    segment_min_speech_frames: int

    @classmethod
    def load(cls) -> "Settings":
        fast_mode = _parse_bool("FAST_MODE", False)
        quality_mode = _parse_bool("QUALITY_MODE", True)
        # Backward compat: AUDIO_INPUT_DEVICE → TEAM_AUDIO_DEVICE
        team_device = _parse_device("TEAM_AUDIO_DEVICE") or _parse_device("AUDIO_INPUT_DEVICE")
        explicit_in = os.getenv("WHISPER_MODEL_IN") or os.getenv("WHISPER_MODEL")
        model_in = _resolve_whisper_model_in(
            explicit_in, fast_mode=fast_mode, quality_mode=quality_mode
        )
        default_model_out = "base" if fast_mode else "small"
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            team_audio_device=team_device,
            team_loopback=default_team_loopback(),
            mic_input_device=_parse_device("MIC_INPUT_DEVICE"),
            virtual_mic_device=_parse_device("VIRTUAL_MIC_DEVICE"),
            whisper_model_in=model_in,
            whisper_model_out=os.getenv("WHISPER_MODEL_OUT", default_model_out),
            show_original=os.getenv("SHOW_ORIGINAL", "true").lower() == "true",
            enable_outgoing=os.getenv("ENABLE_OUTGOING", "true").lower() == "true",
            tts_voice=os.getenv("TTS_VOICE", "en-US-GuyNeural"),
            segment_silence_frames=_parse_int(
                "SEGMENT_SILENCE_FRAMES",
                8 if fast_mode else 12,
            ),
            segment_min_speech_frames=_parse_int(
                "SEGMENT_MIN_SPEECH_FRAMES",
                4 if fast_mode else 5,
            ),
        )
