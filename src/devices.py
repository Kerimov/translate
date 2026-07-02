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


def autodetect_windows() -> dict[str, DeviceOption | None]:
    mic = default_input_device()
    team = default_output_device()
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
