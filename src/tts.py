from __future__ import annotations

import asyncio
import io
import threading

import av
import edge_tts
import numpy as np
import sounddevice as sd


async def _synthesize_mp3(text: str, voice: str) -> bytes:
    mp3_bytes = bytearray()
    async for chunk in edge_tts.Communicate(text, voice).stream():
        if chunk["type"] == "audio":
            mp3_bytes.extend(chunk["data"])
    return bytes(mp3_bytes)


def _mp3_to_audio(mp3_bytes: bytes) -> tuple[np.ndarray, int]:
    container = av.open(io.BytesIO(mp3_bytes), format="mp3")
    stream = container.streams.audio[0]
    chunks: list[np.ndarray] = []

    for frame in container.decode(audio=0):
        arr = frame.to_ndarray()
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        chunks.append(arr.astype(np.float32))

    if not chunks:
        return np.array([], dtype=np.float32), stream.rate or 24000

    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio)))
    if peak > 1.0:
        audio = audio / peak
    return audio, stream.rate or 24000


class TextToSpeech:
    """Synthesizes English speech and plays it to the virtual mic output device."""

    def __init__(self, voice: str, output_device: int | None) -> None:
        self.voice = voice
        self.output_device = output_device
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        if not text.strip():
            return

        with self._lock:
            mp3 = asyncio.run(_synthesize_mp3(text, self.voice))
            audio, sample_rate = _mp3_to_audio(mp3)
            if audio.size == 0:
                return
            sd.play(audio, sample_rate, device=self.output_device)
            sd.wait()
