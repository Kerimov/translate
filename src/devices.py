from __future__ import annotations

import sounddevice as sd

DeviceOption = tuple[int, str]


def list_input_devices() -> list[DeviceOption]:
    result: list[DeviceOption] = []
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            result.append((index, device["name"]))
    return result


def list_output_devices() -> list[DeviceOption]:
    result: list[DeviceOption] = []
    for index, device in enumerate(sd.query_devices()):
        if device["max_output_channels"] > 0:
            result.append((index, device["name"]))
    return result


def find_device(patterns: list[str], *, kind: str) -> DeviceOption | None:
    devices = list_input_devices() if kind == "input" else list_output_devices()
    for pattern in patterns:
        needle = pattern.lower()
        for index, name in devices:
            if needle in name.lower():
                return index, name
    return None


def default_input_device() -> DeviceOption | None:
    index = sd.default.device[0]
    if index is None or int(index) < 0:
        devices = list_input_devices()
        return devices[0] if devices else None
    info = sd.query_devices(int(index))
    return int(index), info["name"]


def default_output_device() -> DeviceOption | None:
    index = sd.default.device[1]
    if index is None or int(index) < 0:
        devices = list_output_devices()
        return devices[0] if devices else None
    info = sd.query_devices(int(index))
    return int(index), info["name"]


def _is_virtual_cable_output(name: str) -> bool:
    lower = name.lower()
    return "cable input" in lower or "cable in 16ch" in lower


def is_virtual_cable_output(name: str) -> bool:
    return _is_virtual_cable_output(name)


def _wasapi_output_devices() -> list[DeviceOption]:
    wasapi_index = None
    for index, api in enumerate(sd.query_hostapis()):
        if "wasapi" in api["name"].lower():
            wasapi_index = index
            break
    if wasapi_index is None:
        return []

    result: list[DeviceOption] = []
    for index, device in enumerate(sd.query_devices()):
        if device["hostapi"] == wasapi_index and device["max_output_channels"] > 0:
            result.append((index, device["name"]))
    return result


def team_output_device() -> DeviceOption | None:
    """Output device for game audio loopback (WASAPI, not VB-Cable)."""
    for index, name in _wasapi_output_devices():
        if not _is_virtual_cable_output(name):
            return index, name

    default_out = default_output_device()
    if default_out is not None and not _is_virtual_cable_output(default_out[1]):
        return default_out

    for index, name in list_output_devices():
        if not _is_virtual_cable_output(name):
            return index, name
    return default_out


def autodetect_windows() -> dict[str, DeviceOption | None]:
    mic = default_input_device()
    team = team_output_device()
    cable = find_device(
        ["cable input", "vb-audio cable input"],
        kind="output",
    )
    return {
        "mic": mic,
        "team": team,
        "virtual_mic": cable,
    }


def format_device(option: DeviceOption | None) -> str:
    if option is None:
        return "не найдено"
    return f"[{option[0]}] {option[1]}"
