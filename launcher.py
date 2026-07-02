"""Windows launcher: first-run setup + one-click start before CS2."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"


def _read_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env(values: dict[str, str]) -> None:
    lines = [
        f"DEEPSEEK_API_KEY={values['DEEPSEEK_API_KEY']}",
        "",
        "TEAM_LOOPBACK=true",
        f"TEAM_AUDIO_DEVICE={values.get('TEAM_AUDIO_DEVICE', '')}",
        f"MIC_INPUT_DEVICE={values.get('MIC_INPUT_DEVICE', '')}",
        f"VIRTUAL_MIC_DEVICE={values.get('VIRTUAL_MIC_DEVICE', '')}",
        "",
        "WHISPER_MODEL_IN=small.en",
        "WHISPER_MODEL_OUT=small",
        "TTS_VOICE=en-US-GuyNeural",
        f"ENABLE_OUTGOING={values.get('ENABLE_OUTGOING', 'true')}",
        "SHOW_ORIGINAL=true",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def _needs_setup() -> bool:
    env = _read_env()
    key = env.get("DEEPSEEK_API_KEY", "").strip()
    return not key or key == "your_api_key_here"


def _launch_translator() -> None:
    from src.main import main as run_main

    run_main()


class SetupWindow:
    def __init__(self) -> None:
        from src.devices import autodetect_windows, format_device, list_input_devices, list_output_devices

        self.detect = autodetect_windows()
        self.inputs = list_input_devices()
        self.outputs = list_output_devices()
        self.format_device = format_device

        self.root = tk.Tk()
        self.root.title("CS2 Translate — настройка")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")

        width, height = 620, 520
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(self.root, bg="#1a1a1a", padx=24, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="CS2 Translate",
            fg="#ffffff",
            bg="#1a1a1a",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            text="Один раз настройте — потом просто запускайте перед игрой.",
            fg="#aaaaaa",
            bg="#1a1a1a",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 16))

        tk.Label(frame, text="DeepSeek API Key", fg="#cccccc", bg="#1a1a1a").pack(anchor="w")
        self.api_key = tk.Entry(frame, width=72, show="*", font=("Segoe UI", 10))
        self.api_key.pack(fill="x", pady=(4, 12))

        env = _read_env()
        if env.get("DEEPSEEK_API_KEY"):
            self.api_key.insert(0, env["DEEPSEEK_API_KEY"])

        self.mic_var = self._combo(frame, "Ваш микрофон", self.inputs, self.detect.get("mic"))
        self.team_var = self._combo(frame, "Звук игры (наушники)", self.outputs, self.detect.get("team"))
        self.cable_var = self._combo(
            frame,
            "VB-Cable Input (голос в Steam)",
            self.outputs,
            self.detect.get("virtual_mic"),
        )

        self.outgoing_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame,
            text="Переводить мой голос на английский (RU → EN)",
            variable=self.outgoing_var,
            fg="#cccccc",
            bg="#1a1a1a",
            selectcolor="#333333",
            activebackground="#1a1a1a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(8, 8))

        note = (
            "Нужно один раз:\n"
            "1. Установить VB-Audio Virtual Cable (vb-audio.com/Cable)\n"
            "2. Steam → Settings → Voice → CABLE Output (VB-Audio)\n"
            "3. CS2 в оконном / borderless режиме"
        )
        tk.Label(
            frame,
            text=note,
            fg="#888888",
            bg="#1a1a1a",
            justify="left",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 12))

        btn_row = tk.Frame(frame, bg="#1a1a1a")
        btn_row.pack(fill="x")
        tk.Button(
            btn_row,
            text="Сохранить и запустить",
            command=self._save_and_launch,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            padx=16,
            pady=8,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")

        if not self.detect.get("virtual_mic"):
            tk.Label(
                frame,
                text="⚠ VB-Cable не найден — установите перед игрой",
                fg="#fbbf24",
                bg="#1a1a1a",
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w", pady=(12, 0))

    def _combo(
        self,
        parent: tk.Frame,
        label: str,
        options: list[tuple[int, str]],
        selected: tuple[int, str] | None,
    ) -> tk.StringVar:
        tk.Label(parent, text=label, fg="#cccccc", bg="#1a1a1a").pack(anchor="w", pady=(8, 0))
        values = [f"[{idx}] {name}" for idx, name in options]
        var = tk.StringVar()
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=68)
        combo.pack(fill="x", pady=(4, 0))

        if selected:
            var.set(f"[{selected[0]}] {selected[1]}")
        elif values:
            var.set(values[0])
        return var

    @staticmethod
    def _parse_combo(value: str) -> str:
        if not value.startswith("["):
            return ""
        end = value.find("]")
        return value[1:end]

    def _save_and_launch(self) -> None:
        api_key = self.api_key.get().strip()
        if not api_key:
            messagebox.showerror("Ошибка", "Введите DeepSeek API Key")
            return

        values = {
            "DEEPSEEK_API_KEY": api_key,
            "TEAM_AUDIO_DEVICE": self._parse_combo(self.team_var.get()),
            "MIC_INPUT_DEVICE": self._parse_combo(self.mic_var.get()),
            "VIRTUAL_MIC_DEVICE": self._parse_combo(self.cable_var.get()),
            "ENABLE_OUTGOING": "true" if self.outgoing_var.get() else "false",
        }
        _write_env(values)
        self.root.destroy()
        _launch_translator()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        SetupWindow().run()
        return

    if _needs_setup():
        SetupWindow().run()
    else:
        _launch_translator()


if __name__ == "__main__":
    main()
