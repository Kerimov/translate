from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np


class SegmentQueueWorker:
    """Process every speech segment; drop oldest only if queue is full."""

    def __init__(
        self,
        handler: Callable[[np.ndarray], None],
        *,
        max_queue: int = 6,
    ) -> None:
        self._handler = handler
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=max_queue)
        self._active = False
        self._lock = threading.Lock()
        self._dropped = 0

    def submit(self, audio: np.ndarray) -> None:
        try:
            self._queue.put_nowait(audio)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._dropped += 1
                self._queue.put_nowait(audio)
            except queue.Empty:
                pass
        with self._lock:
            if self._active:
                return
            self._active = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        while True:
            audio = self._queue.get()
            if audio is None:
                with self._lock:
                    self._active = False
                return
            try:
                self._handler(audio)
            except Exception as exc:
                print(f"[segment] {exc}")
            if self._queue.empty():
                with self._lock:
                    if self._queue.empty():
                        self._active = False
                        return

    @property
    def dropped_count(self) -> int:
        return self._dropped
