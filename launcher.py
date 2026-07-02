"""Windows launcher: first-run setup + one-click start before CS2."""

from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Callable
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
    existing = _read_env()
    merged = {**existing, **values}
    lines = [
        f"DEEPSEEK_API_KEY={merged['DEEPSEEK_API_KEY']}",
        "",
        f"TEAM_LOOPBACK={merged.get('TEAM_LOOPBACK', 'true')}",
        f"TEAM_AUDIO_DEVICE={merged.get('TEAM_AUDIO_DEVICE', '')}",
        f"MIC_INPUT_DEVICE={merged.get('MIC_INPUT_DEVICE', '')}",
        f"VIRTUAL_MIC_DEVICE={merged.get('VIRTUAL_MIC_DEVICE', '')}",
        "",
        f"WHISPER_MODEL_IN={merged.get('WHISPER_MODEL_IN', 'small.en')}",
        f"WHISPER_MODEL_OUT={merged.get('WHISPER_MODEL_OUT', 'small')}",
        f"TTS_VOICE={merged.get('TTS_VOICE', 'en-US-GuyNeural')}",
        f"ENABLE_OUTGOING={merged.get('ENABLE_OUTGOING', 'true')}",
        f"SHOW_ORIGINAL={merged.get('SHOW_ORIGINAL', 'true')}",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def _needs_setup() -> bool:
    env = _read_env()
    key = env.get("DEEPSEEK_API_KEY", "").strip()
    return not key or key == "your_api_key_here"


def _setup_entry_clipboard(entry: tk.Entry) -> Callable[[], str | None]:
    """Clipboard shortcuts that work on Russian Windows keyboard layouts."""

    def paste(_event=None):
        try:
            text = entry.clipboard_get()
        except tk.TclError:
            return "break"
        if entry.selection_present():
            entry.delete("sel.first", "sel.last")
        entry.insert(entry.index("insert"), text)
        return "break"

    def copy(_event=None):
        try:
            if entry.selection_present():
                entry.clipboard_clear()
                entry.clipboard_append(entry.selection_get())
        except tk.TclError:
            pass
        return "break"

    def cut(_event=None):
        copy()
        if entry.selection_present():
            entry.delete("sel.first", "sel.last")
        return "break"

    def on_ctrl_key(event: tk.Event) -> str | None:
        if event.keycode == 86:
            return paste()
        if event.keycode == 67:
            return copy()
        if event.keycode == 88:
            return cut()
        return None

    entry.bind("<Control-KeyPress>", on_ctrl_key)
    entry.bind("<Shift-Insert>", paste)
    entry.bind("<Control-Insert>", copy)

    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label="Вставить", command=paste)
    menu.add_command(label="Копировать", command=copy)
    menu.add_command(label="Вырезать", command=cut)
    entry.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))
    return paste


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
        key_row = tk.Frame(frame, bg="#1a1a1a")
        key_row.pack(fill="x", pady=(4, 0))
        self.api_key = tk.Entry(key_row, show="*", font=("Segoe UI", 10))
        self.api_key.pack(side="left", fill="x", expand=True, padx=(0, 8))
        paste_key = _setup_entry_clipboard(self.api_key)
        tk.Button(
            key_row,
            text="Вставить",
            command=paste_key,
            bg="#333333",
            fg="#ffffff",
            activebackground="#444444",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            padx=10,
            pady=2,
            relief="flat",
            cursor="hand2",
        ).pack(side="right")
        tk.Label(
            frame,
            text="Вставка: кнопка «Вставить», Ctrl+V или Shift+Ins",
            fg="#666666",
            bg="#1a1a1a",
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(2, 12))

        env = _read_env()
        if env.get("DEEPSEEK_API_KEY"):
            self.api_key.insert(0, env["DEEPSEEK_API_KEY"])

        outgoing_enabled = env.get("ENABLE_OUTGOING", "true").lower() in ("true", "1", "yes")
        self.outgoing_var = tk.BooleanVar(value=outgoing_enabled)

        self.team_var = self._combo(frame, "Звук игры (наушники)", self.outputs, self.detect.get("team"))

        tk.Checkbutton(
            frame,
            text="Переводить мой голос на английский (RU → EN в Steam)",
            variable=self.outgoing_var,
            command=self._toggle_outgoing_fields,
            fg="#cccccc",
            bg="#1a1a1a",
            selectcolor="#333333",
            activebackground="#1a1a1a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(8, 4))

        self.mode_hint = tk.Label(
            frame,
            text="",
            fg="#888888",
            bg="#1a1a1a",
            justify="left",
            font=("Segoe UI", 9),
        )
        self.mode_hint.pack(anchor="w", pady=(0, 8))

        self.outgoing_extra = tk.Frame(frame, bg="#1a1a1a")
        self.mic_frame = tk.Frame(self.outgoing_extra, bg="#1a1a1a")
        self.mic_frame.pack(fill="x")
        self.mic_var = self._combo(self.mic_frame, "Ваш микрофон", self.inputs, self.detect.get("mic"))
        self.cable_var = self._combo(
            self.mic_frame,
            "VB-Cable Input (голос в Steam)",
            self.outputs,
            self.detect.get("virtual_mic"),
        )

        note = (
            "Для режима с голосом в Steam:\n"
            "1. Установить VB-Audio Virtual Cable (vb-audio.com/Cable)\n"
            "2. Steam → Settings → Voice → CABLE Output (VB-Audio)\n"
            "3. CS2 в оконном / borderless режиме"
        )
        self.note_label = tk.Label(
            self.outgoing_extra,
            text=note,
            fg="#888888",
            bg="#1a1a1a",
            justify="left",
            font=("Segoe UI", 9),
        )
        self.note_label.pack(anchor="w", pady=(4, 0))
        self._toggle_outgoing_fields()

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
                text="⚠ VB-Cable не найден — нужен только для перевода вашего голоса",
                fg="#fbbf24",
                bg="#1a1a1a",
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w", pady=(12, 0))

    def _toggle_outgoing_fields(self) -> None:
        enabled = self.outgoing_var.get()
        if enabled:
            self.outgoing_extra.pack(fill="x", pady=(0, 12))
            self.mode_hint.config(
                text="Включён двусторонний режим: субтитры команды + ваш голос на английском."
            )
        else:
            self.outgoing_extra.pack_forget()
            self.mode_hint.config(
                text="Только субтитры: переводите голос команды, свой микрофон не трогаем."
            )

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
