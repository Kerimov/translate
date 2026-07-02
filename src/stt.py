import os
import sys

import numpy as np
from faster_whisper import WhisperModel


def _cuda_usable() -> bool:
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() == 0:
            return False
    except Exception:
        return False

    if sys.platform == "win32":
        import ctypes

        for name in ("cublas64_12.dll", "cublas64_11.dll", "cublas64_10.dll"):
            try:
                ctypes.WinDLL(name)
                return True
            except OSError:
                continue
        return False

    return True


def _resolve_whisper_backend() -> tuple[str, str]:
    device = os.getenv("WHISPER_DEVICE", "auto").strip().lower()
    if device == "auto":
        if _cuda_usable():
            return "cuda", "float16"
        return "cpu", "int8"
    if device == "cuda":
        return "cuda", os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    return "cpu", os.getenv("WHISPER_COMPUTE_TYPE", "int8")


class SpeechToText:
    def __init__(self, model_name: str, label: str = "stt") -> None:
        self.model_name = model_name
        self.label = label
        self._vad_filter = os.getenv("WHISPER_VAD", "false").lower() == "true"
        self._device, self._compute_type = _resolve_whisper_backend()
        self.model = self._load_model(self._device, self._compute_type)

    def _load_model(self, device: str, compute_type: str) -> WhisperModel:
        print(
            f"[{self.label}] Loading Whisper '{self.model_name}' on {device} "
            f"({compute_type}, first run may download)..."
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
        segments, _info = self.model.transcribe(
            audio,
            language=language,
            beam_size=1,
            best_of=1,
            vad_filter=self._vad_filter,
            condition_on_previous_text=False,
            without_timestamps=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
