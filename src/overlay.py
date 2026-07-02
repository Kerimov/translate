from __future__ import annotations

import queue
from collections import deque

import tkinter as tk
from dataclasses import dataclass


@dataclass
class SubtitleUpdate:
    kind: str  # "incoming" | "outgoing" | "error"
    original: str
    translated: str
    show_original: bool


class SubtitleOverlay:
    def __init__(self, show_original: bool, enable_outgoing: bool) -> None:
        self.show_original = show_original
        self.enable_outgoing = enable_outgoing
        self._queue: queue.Queue[SubtitleUpdate | None] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("CS2 Translate")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.configure(bg="#111111")
        self.root.overrideredirect(True)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(900, screen_w - 80)
        height = 200 if enable_outgoing else 140
        x = (screen_w - width) // 2
        y = screen_h - height - 120
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.incoming_header = tk.Label(
            self.root,
            text="Команда:",
            fg="#888888",
            bg="#111111",
            font=("Helvetica", 11),
            anchor="w",
        )
        self.incoming_header.pack(fill="x", padx=20, pady=(10, 0))

        self.original_label = tk.Label(
            self.root,
            text="",
            fg="#aaaaaa",
            bg="#111111",
            font=("Helvetica", 13),
            wraplength=width - 40,
            justify="center",
        )
        self.original_label.pack(pady=(2, 2), padx=20)

        self.incoming_label = tk.Label(
            self.root,
            text="Слушаю команду...",
            fg="#ffffff",
            bg="#111111",
            font=("Helvetica", 18, "bold"),
            wraplength=width - 40,
            justify="center",
        )
        self.incoming_label.pack(pady=(0, 2), padx=20)

        self.history_label = tk.Label(
            self.root,
            text="",
            fg="#666666",
            bg="#111111",
            font=("Helvetica", 12),
            wraplength=width - 40,
            justify="center",
        )
        self.history_label.pack(pady=(0, 6), padx=20)
        self._history: deque[str] = deque(maxlen=2)

        if enable_outgoing:
            self.outgoing_header = tk.Label(
                self.root,
                text="Вы → команда:",
                fg="#888888",
                bg="#111111",
                font=("Helvetica", 11),
                anchor="w",
            )
            self.outgoing_header.pack(fill="x", padx=20, pady=(4, 0))

            self.outgoing_label = tk.Label(
                self.root,
                text="Говорите в микрофон...",
                fg="#66ccff",
                bg="#111111",
                font=("Helvetica", 16, "bold"),
                wraplength=width - 40,
                justify="center",
            )
            self.outgoing_label.pack(pady=(2, 10), padx=20)
        else:
            self.outgoing_label = None

        self.root.bind("<Escape>", lambda _e: self.stop())
        self.root.after(50, self._poll)

    def show_incoming(self, original: str, translated: str) -> None:
        self._queue.put(
            SubtitleUpdate("incoming", original, translated, self.show_original)
        )

    def show_incoming_progress(self, message: str) -> None:
        self._queue.put(SubtitleUpdate("incoming_progress", "", message, False))

    def show_outgoing(self, original: str, translated: str) -> None:
        self._queue.put(
            SubtitleUpdate("outgoing", original, translated, True)
        )

    def show_error(self, message: str) -> None:
        self._queue.put(SubtitleUpdate("error", "", message, False))

    def stop(self) -> None:
        self._queue.put(None)

    def _poll(self) -> None:
        try:
            while True:
                update = self._queue.get_nowait()
                if update is None:
                    self.root.quit()
                    return
                if update.kind == "incoming":
                    if update.show_original and update.original:
                        self.original_label.config(text=update.original)
                    else:
                        self.original_label.config(text="")
                    translated = update.translated or "..."
                    if translated not in ("…", "...", "Распознаю..."):
                        if (
                            self.incoming_label.cget("text")
                            not in ("Слушаю команду...", "Распознаю...", "…", "...")
                        ):
                            self._history.append(self.incoming_label.cget("text"))
                        self.history_label.config(
                            text="\n".join(self._history) if self._history else ""
                        )
                    self.incoming_label.config(text=translated)
                elif update.kind == "incoming_progress":
                    self.original_label.config(text="")
                    self.incoming_label.config(text=update.translated)
                elif update.kind == "outgoing" and self.outgoing_label is not None:
                    if update.original:
                        self.outgoing_label.config(
                            text=f"{update.original}  →  {update.translated}"
                        )
                    else:
                        self.outgoing_label.config(text=update.translated)
                elif update.kind == "error":
                    self.incoming_label.config(text=f"Ошибка: {update.translated}")
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def run(self) -> None:
        self.root.mainloop()
