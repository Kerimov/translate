from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.platform_util import default_team_loopback

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
        # Backward compat: AUDIO_INPUT_DEVICE → TEAM_AUDIO_DEVICE
        team_device = _parse_device("TEAM_AUDIO_DEVICE") or _parse_device("AUDIO_INPUT_DEVICE")
        default_model_in = "base.en" if fast_mode else "small.en"
        default_model_out = "base" if fast_mode else "small"
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            team_audio_device=team_device,
            team_loopback=default_team_loopback(),
            mic_input_device=_parse_device("MIC_INPUT_DEVICE"),
            virtual_mic_device=_parse_device("VIRTUAL_MIC_DEVICE"),
            whisper_model_in=os.getenv("WHISPER_MODEL_IN", os.getenv("WHISPER_MODEL", default_model_in)),
            whisper_model_out=os.getenv("WHISPER_MODEL_OUT", default_model_out),
            show_original=os.getenv("SHOW_ORIGINAL", "true").lower() == "true",
            enable_outgoing=os.getenv("ENABLE_OUTGOING", "true").lower() == "true",
            tts_voice=os.getenv("TTS_VOICE", "en-US-GuyNeural"),
            segment_silence_frames=_parse_int(
                "SEGMENT_SILENCE_FRAMES", 8 if fast_mode else 12
            ),
            segment_min_speech_frames=_parse_int(
                "SEGMENT_MIN_SPEECH_FRAMES", 4 if fast_mode else 5
            ),
        )
