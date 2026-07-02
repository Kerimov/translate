"""Download PortAudio with WASAPI loopback and install into sounddevice."""

from __future__ import annotations

import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_DLL = ROOT / "vendor" / "libportaudio64bit.dll"
LOOPBACK_DLL_URL = (
    "https://raw.githubusercontent.com/spatialaudio/portaudio-binaries/"
    "portaudio-master/libportaudio64bit.dll"
)


def _venv_dll() -> Path:
    import sounddevice as sd

    return (
        Path(sd.__file__).resolve().parent
        / "_sounddevice_data"
        / "portaudio-binaries"
        / "libportaudio64bit.dll"
    )


def download_vendor_dll() -> Path:
    VENDOR_DLL.parent.mkdir(parents=True, exist_ok=True)
    print("Скачиваю PortAudio с поддержкой WASAPI loopback...")
    with urllib.request.urlopen(LOOPBACK_DLL_URL, timeout=60) as response:
        data = response.read()
    if len(data) < 100_000:
        raise RuntimeError("Скачанный файл слишком маленький.")
    VENDOR_DLL.write_bytes(data)
    print(f"Сохранено: {VENDOR_DLL}")
    return VENDOR_DLL


def install_vendor_dll() -> bool:
    if not VENDOR_DLL.exists():
        return False
    target = _venv_dll()
    if target.exists():
        backup = target.with_suffix(".dll.bak")
        if not backup.exists():
            shutil.copy2(target, backup)
    shutil.copy2(VENDOR_DLL, target)
    print(f"Установлено в: {target}")
    return True


def main() -> int:
    if sys.platform != "win32":
        return 0

    try:
        if not VENDOR_DLL.exists():
            download_vendor_dll()
        install_vendor_dll()
    except Exception as exc:
        print(f"Ошибка: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
