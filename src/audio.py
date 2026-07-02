from __future__ import annotations

import queue
import sys
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from src.config import CHANNELS, FRAME_MS, SAMPLE_RATE, FRAME_SAMPLES
from src.devices import is_virtual_cable_output
from src.platform_util import is_macos, is_windows, resample_audio


class SpeechSegmenter:
    """Buffers mic/system audio and emits segments when speech ends."""

    def __init__(
        self,
        on_segment: Callable[[np.ndarray], None],
        *,
        energy_threshold: float = 0.012,
        silence_frames: int = 12,
        min_speech_frames: int = 5,
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


def _wasapi_hostapi_index() -> int | None:
    for index, api in enumerate(sd.query_hostapis()):
        if "wasapi" in api["name"].lower():
            return index
    return None


def _is_loopback_device(index: int) -> bool:
    name = sd.query_devices(index)["name"].lower()
    if "[loopback]" in name:
        return True
    try:
        return bool(sd._lib.PaWasapi_IsLoopback(index))
    except Exception:
        return False


def _find_loopback_for_output(output_index: int) -> dict | None:
    output = sd.query_devices(output_index)
    output_name = output["name"]
    wasapi_index = _wasapi_hostapi_index()

    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] <= 0:
            continue
        if wasapi_index is not None and device["hostapi"] != wasapi_index:
            continue
        if not _is_loopback_device(index):
            continue
        if output_name in device["name"] or device["name"].startswith(output_name):
            return sd.query_devices(index)

    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0 and _is_loopback_device(index):
            return sd.query_devices(index)

    return None


def _resolve_loopback_device(device: int | None) -> tuple[int, int, int]:
    """Return (device_index, sample_rate, channels) for WASAPI loopback capture."""
    if device is None:
        output_info = sd.query_devices(kind="output")
    else:
        output_info = sd.query_devices(device)

    loopback = _find_loopback_for_output(int(output_info["index"]))
    if loopback is None:
        output_name = output_info["name"]
        if is_virtual_cable_output(output_name):
            raise RuntimeError(
                "TEAM_AUDIO_DEVICE указывает на VB-Cable Input — это устройство для "
                "голоса в Steam, а не для захвата звука игры. "
                "Запустите настройку: python launcher.py --setup "
                "и выберите наушники/колонки в поле «Звук игры»."
            )
        raise RuntimeError(
            "WASAPI loopback не найден для "
            f"'{output_name}'. Перезапустите CS2 Translate.bat "
            "(установит PortAudio с loopback) или укажите другое устройство вывода."
        )

    index = int(loopback["index"])
    sample_rate = int(loopback["default_samplerate"])
    channels = min(2, max(1, loopback["max_input_channels"]))
    return index, sample_rate, channels


class AudioCapture:
    def __init__(
        self,
        on_segment: Callable[[np.ndarray], None],
        *,
        device: int | None = None,
        label: str = "audio",
        loopback: bool = False,
        silence_frames: int = 12,
        min_speech_frames: int = 5,
    ) -> None:
        self.device = device
        self.label = label
        self.loopback = loopback
        self.capture_rate = SAMPLE_RATE
        self.capture_channels = CHANNELS

        def deliver(audio: np.ndarray) -> None:
            if self.capture_rate != SAMPLE_RATE:
                audio = resample_audio(audio, self.capture_rate, SAMPLE_RATE)
            on_segment(audio)

        self.segmenter = SpeechSegmenter(
            deliver,
            silence_frames=silence_frames,
            min_speech_frames=min_speech_frames,
        )
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._worker: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._worker.start()

        stream_kwargs: dict = {
            "dtype": "float32",
            "callback": self._callback,
        }

        if self.loopback:
            if not is_windows():
                raise RuntimeError("WASAPI loopback is only supported on Windows.")
            device_index, sample_rate, channels = _resolve_loopback_device(self.device)
            self.device = device_index
            self.capture_rate = sample_rate
            self.capture_channels = channels
            blocksize = max(1, sample_rate * FRAME_MS // 1000)
            stream_kwargs.update(
                {
                    "device": device_index,
                    "samplerate": sample_rate,
                    "channels": channels,
                    "blocksize": blocksize,
                }
            )
            print(
                f"[{self.label}] WASAPI loopback from output device {device_index} "
                f"({sample_rate} Hz, {channels} ch)"
            )
        else:
            stream_kwargs.update(
                {
                    "samplerate": SAMPLE_RATE,
                    "channels": CHANNELS,
                    "blocksize": FRAME_SAMPLES,
                    "device": self.device,
                }
            )
            print(f"[{self.label}] Capturing from input device {self.device!r}")

        self._stream = sd.InputStream(**stream_kwargs)
        self._stream.start()

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
            print(f"[{self.label}] {status}")
        if indata.ndim > 1 and indata.shape[1] > 1:
            frame = indata.mean(axis=1)
        else:
            frame = indata[:, 0]
        self._queue.put(frame.copy())

    def _process_loop(self) -> None:
        while self._running:
            try:
                frame = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            self.segmenter.push(frame)


def list_audio_devices() -> None:
    hostapis = sd.query_hostapis()
    print("Host APIs:")
    for api in hostapis:
        print(f"  [{api['index']}] {api['name']}")

    print("\nDevices:")
    for index, device in enumerate(sd.query_devices()):
        in_ch = device["max_input_channels"]
        out_ch = device["max_output_channels"]
        kind = []
        if in_ch > 0:
            kind.append("in")
        if out_ch > 0:
            kind.append("out")
        default = []
        if index == sd.default.device[0]:
            default.append("default-in")
        if index == sd.default.device[1]:
            default.append("default-out")
        flags = f" ({', '.join(default)})" if default else ""
        print(
            f"  [{index}] {device['name']} "
            f"[{'/'.join(kind) or '-'}, {int(device['default_samplerate'])} Hz]{flags}"
        )

    print()
    if is_windows():
        print("Windows tips:")
        print("  TEAM_LOOPBACK=true       — захват звука игры через WASAPI loopback (по умолчанию)")
        print("  TEAM_AUDIO_DEVICE=N      — индекс устройства вывода (наушники/динамики) для loopback")
        print("  MIC_INPUT_DEVICE=N       — ваш микрофон")
        print("  VIRTUAL_MIC_DEVICE=N     — CABLE Input (VB-Audio) для голоса в Steam")
        print("  Steam → Settings → Voice → CABLE Output (VB-Audio Virtual Cable)")
    elif is_macos():
        print("macOS tips:")
        print("  TEAM_AUDIO_DEVICE=N      — BlackHole input (голос команды)")
        print("  MIC_INPUT_DEVICE=N       — ваш микрофон")
        print("  VIRTUAL_MIC_DEVICE=N     — BlackHole output (Steam mic)")
    else:
        print("Set TEAM_AUDIO_DEVICE, MIC_INPUT_DEVICE, VIRTUAL_MIC_DEVICE in .env")
