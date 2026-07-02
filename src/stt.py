import numpy as np
from faster_whisper import WhisperModel


class SpeechToText:
    def __init__(self, model_name: str, label: str = "stt") -> None:
        print(f"[{label}] Loading Whisper model '{model_name}' (first run may download)...")
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self.label = label

    def transcribe(self, audio: np.ndarray, *, language: str) -> str:
        if audio.size == 0:
            return ""

        segments, _info = self.model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
