"""Add NVIDIA pip CUDA DLLs to PATH (Windows) before CTranslate2 loads."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_CONFIGURED = False


def setup_nvidia_cuda_paths() -> bool:
    global _CONFIGURED
    if _CONFIGURED or sys.platform != "win32":
        return _CONFIGURED

    site_packages: Path | None = None
    for entry in sys.path:
        candidate = Path(entry)
        if (candidate / "nvidia").is_dir():
            site_packages = candidate
            break
    if site_packages is None:
        return False

    nvidia_base = site_packages / "nvidia"

    paths: list[str] = []
    for sub in ("cublas/bin", "cudnn/bin", "cuda_nvrtc/bin", "cuda_runtime/bin"):
        folder = nvidia_base / sub.replace("/", os.sep)
        if folder.is_dir():
            paths.append(str(folder))

    if not paths:
        return False

    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(paths + ([current_path] if current_path else []))

    if hasattr(os, "add_dll_directory"):
        for path in paths:
            try:
                os.add_dll_directory(path)
            except OSError:
                pass

    _CONFIGURED = True
    return True


def cublas_dll_name() -> str | None:
    if sys.platform != "win32":
        return None
    import ctypes

    for name in ("cublas64_12.dll", "cublas64_11.dll"):
        try:
            ctypes.WinDLL(name)
            return name
        except OSError:
            continue
    return None
