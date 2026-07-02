"""Проверка: готов ли Whisper работать на GPU (CUDA + cuBLAS)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cuda_runtime import cublas_dll_name, setup_nvidia_cuda_paths

setup_nvidia_cuda_paths()


def _check_cublas_dll() -> tuple[bool, str]:
    name = cublas_dll_name()
    return (name is not None, name or "")


def main() -> int:
    print("=== Проверка CUDA для CS2 Translate ===\n")

    try:
        import ctranslate2

        count = ctranslate2.get_cuda_device_count()
        print(f"GPU (ctranslate2):     {count} устройств")
    except Exception as exc:
        print(f"GPU (ctranslate2):     ошибка — {exc}")
        count = 0

    if sys.platform == "win32":
        ok, dll = _check_cublas_dll()
        if ok:
            print(f"cuBLAS:                OK ({dll})")
        else:
            print("cuBLAS:                НЕ НАЙДЕН")
            print("                       Запустите CS2 Translate.bat (установит через pip)")
            print("                       или: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
    else:
        print("cuBLAS:                проверка только на Windows")

    from src.stt import _cuda_usable, _resolve_whisper_backend

    usable = _cuda_usable()
    device, compute = _resolve_whisper_backend()
    print(f"Программа выберет:     {device} ({compute})")
    print()

    if not usable or count == 0:
        print("Итог: GPU пока НЕ используется — Whisper на CPU.")
        print("Это нормально, программа работает, просто медленнее.")
        return 1

    print("Пробую распознать тест на GPU...")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("tiny.en", device="cuda", compute_type="float16")
        list(model.transcribe(np.zeros(16_000, dtype=np.float32), beam_size=1))
        print("Итог: GPU РАБОТАЕТ. Можно в .env поставить:")
        print("  WHISPER_DEVICE=cuda")
        print("  WHISPER_MODEL_IN=medium.en")
        return 0
    except Exception as exc:
        print(f"Итог: GPU найден, но тест не прошёл: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
