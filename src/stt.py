import os
import sys

# CUDA DLLs from pip must be on PATH before ctranslate2 loads native libs.
from src.cuda_runtime import setup_nvidia_cuda_paths

setup_nvidia_cuda_paths()

import numpy as np
from faster_whisper import WhisperModel

from src.platform_util import normalize_audio

WHISPER_PROMPT_EN = (
    "CS2 voice comms: rush B, flash, smoke, Molly, A site, B site, eco, rotate, "
    "one HP, push, hold, planted, defuse, save, drop, heaven, mid, catwalk."
)

WHISPER_PROMPT_RU = (
    "CS2 голосовой чат: раш B, флеш, смок, молотов, A, B, эко, ротация, "
    "один HP, пуш, холд, плент, дефьюз, сейв, дроп."
)


def _cuda_usable() -> bool:
    setup_nvidia_cuda_paths()
    from src.cuda_runtime import cublas_dll_name

    if cublas_dll_name() is None:
        return False
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _resolve_whisper_backend() -> tuple[str, str]:
    device = os.getenv("WHISPER_DEVICE", "auto").strip().lower()
    if device == "auto":
        if _cuda_usable():
            return "cuda", "float16"
        return "cpu", "int8"
    if device == "cuda":
        return "cuda", os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    return "cpu", os.getenv("WHISPER_COMPUTE_TYPE", "int8")


def _parse_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


class SpeechToText:
    def __init__(
        self,
        model_name: str,
        label: str = "stt",
        *,
        for_loopback: bool = False,
    ) -> None:
        self.model_name = model_name
        self.label = label
        self._for_loopback = for_loopback
        fast_mode = os.getenv("FAST_MODE", "false").lower() in ("true", "1", "yes")
        quality_mode = os.getenv("QUALITY_MODE", "true").lower() in ("true", "1", "yes")
        self._device, self._compute_type = _resolve_whisper_backend()
        on_cpu = self._device == "cpu"

        if for_loopback:
            self._vad_filter = False
            self._no_speech_threshold = 0.35
            self._beam_size = _parse_int("WHISPER_BEAM_SIZE", 3)
        else:
            self._no_speech_threshold = 0.5
            if "WHISPER_VAD" in os.environ:
                self._vad_filter = os.getenv("WHISPER_VAD", "false").lower() == "true"
            else:
                self._vad_filter = False
            if fast_mode:
                self._beam_size = _parse_int("WHISPER_BEAM_SIZE", 1)
            elif on_cpu:
                self._beam_size = _parse_int("WHISPER_BEAM_SIZE", 3)
            else:
                self._beam_size = _parse_int("WHISPER_BEAM_SIZE", 5 if quality_mode else 3)

        self.model = self._load_model(self._device, self._compute_type)

    def _load_model(self, device: str, compute_type: str) -> WhisperModel:
        print(
            f"[{self.label}] Loading Whisper '{self.model_name}' on {device} "
            f"({compute_type}, beam={self._beam_size}, first run may download)..."
        )
        return WhisperModel(self.model_name, device=device, compute_type=compute_type)

    def _switch_to_cpu(self, reason: str) -> None:
        if self._device == "cpu":
            return
        print(f"[{self.label}] {reason} Переключаюсь на CPU.")
        self._device = "cpu"
        self._compute_type = "int8"
        self.model = self._load_model("cpu", "int8")

    def transcribe(self, audio: np.ndarray, *, language: str) -> str:
        if audio.size == 0:
            return ""

        audio = normalize_audio(audio)

        try:
            return self._transcribe_once(audio, language=language)
        except Exception as exc:
            message = str(exc).lower()
            if self._device != "cpu" and (
                "cublas" in message or "cuda" in message or "cudnn" in message
            ):
                self._switch_to_cpu(f"CUDA недоступна: {exc}")
                return self._transcribe_once(audio, language=language)
            raise

    def _transcribe_once(self, audio: np.ndarray, *, language: str) -> str:
        initial_prompt = WHISPER_PROMPT_EN if language == "en" else WHISPER_PROMPT_RU
        segments, _info = self.model.transcribe(
            audio,
            language=language,
            beam_size=self._beam_size,
            best_of=1,
            temperature=0.0,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=self._no_speech_threshold,
            vad_filter=self._vad_filter,
            condition_on_previous_text=False,
            without_timestamps=True,
            initial_prompt=initial_prompt,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
