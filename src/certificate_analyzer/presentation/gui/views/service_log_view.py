"""Bounded, read-only viewer of the shared process log."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from certificate_analyzer.infrastructure.config.paths import config_dir

MAX_LOG_BYTES = 256 * 1024


def read_log_tail(path: Path, max_bytes=MAX_LOG_BYTES):
    try:
        with path.open("rb") as stream:
            stream.seek(0, 2)
            start = max(0, stream.tell() - max_bytes)
            stream.seek(start)
            data = stream.read(max_bytes)
        if start:
            _, _, data = data.partition(b"\n")
        return data.decode("utf-8", errors="replace")
    except FileNotFoundError:
        return "Журнал пока не создан. Запустите фоновый процесс."


class ServiceLogWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Журнал службы")
        self.geometry("960x540")
        self.minsize(600, 300)
        self.path = config_dir() / "application.log"
        self._after_id = None
        self._last_text = None
        self.auto_refresh = tk.BooleanVar(value=True)
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=str(self.path), wraplength=900).pack(anchor="w", pady=(0, 8))
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Обновить", command=self.refresh).pack(side="left")
        ttk.Checkbutton(toolbar, text="Обновлять автоматически", variable=self.auto_refresh).pack(side="left", padx=12)
        ttk.Label(toolbar, text="Последние 256 КиБ журнала").pack(side="right")
        self.text = ScrolledText(frame, wrap="word", state="disabled")
        self.text.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        self._schedule()

    def refresh(self):
        try:
            content = read_log_tail(self.path)
        except OSError as exc:
            content = f"Не удалось прочитать журнал: {exc}"
        if content == self._last_text:
            return
        position = self.text.yview()
        at_bottom = position[1] >= 0.99
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")
        if at_bottom:
            self.text.see("end")
        else:
            self.text.yview_moveto(position[0])
        self._last_text = content

    def _schedule(self):
        if self.auto_refresh.get():
            self.refresh()
        self._after_id = self.after(2000, self._schedule)

    def close(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.destroy()
