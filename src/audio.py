from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from src.config import CHANNELS, FRAME_SAMPLES, SAMPLE_RATE


class SpeechSegmenter:
    """Buffers mic/system audio and emits segments when speech ends."""

    def __init__(
        self,
        on_segment: Callable[[np.ndarray], None],
        *,
        energy_threshold: float = 0.012,
        silence_frames: int = 18,
        min_speech_frames: int = 8,
        max_frames: int = 500,
    ) -> None:
        self.on_segment = on_segment
        self.energy_threshold = energy_threshold
        self.silence_frames = silence_frames
        self.min_speech_frames = min_speech_frames
        self.max_frames = max_frames

        self._buffer: list[np.ndarray] = []
        self._speech_frames = 0
        self._silence_count = 0
        self._in_speech = False

    def push(self, frame: np.ndarray) -> None:
        energy = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
        is_speech = energy > self.energy_threshold

        if is_speech:
            self._in_speech = True
            self._silence_count = 0
            self._speech_frames += 1
            self._buffer.append(frame)
            if len(self._buffer) >= self.max_frames:
                self._flush()
            return

        if self._in_speech:
            self._buffer.append(frame)
            self._silence_count += 1
            if self._silence_count >= self.silence_frames:
                self._flush()

    def _flush(self) -> None:
        if self._speech_frames >= self.min_speech_frames and self._buffer:
            audio = np.concatenate(self._buffer)
            self.on_segment(audio)

        self._buffer.clear()
        self._speech_frames = 0
        self._silence_count = 0
        self._in_speech = False


class AudioCapture:
    def __init__(
        self,
        on_segment: Callable[[np.ndarray], None],
        *,
        device: int | None = None,
        label: str = "audio",
    ) -> None:
        self.device = device
        self.label = label
        self.segmenter = SpeechSegmenter(on_segment)
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._worker: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._worker.start()

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            device=self.device,
            callback=self._callback,
        )
        self._stream.start()
        print(f"[{self.label}] Capturing from device {self.device!r}")

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._worker is not None:
            self._worker.join(timeout=1)

    def _callback(self, indata, _frames, _time, status) -> None:
        if status:
            print(f"[audio] {status}")
        self._queue.put(indata[:, 0].copy())

    def _process_loop(self) -> None:
        while self._running:
            try:
                frame = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            self.segmenter.push(frame)


def list_audio_devices() -> None:
    devices = sd.query_devices()
    print(devices)
    print("\nTip: use TEAM_AUDIO_DEVICE for game voice (BlackHole input),")
    print("     MIC_INPUT_DEVICE for your mic, VIRTUAL_MIC_DEVICE for BlackHole output (Steam mic).")
