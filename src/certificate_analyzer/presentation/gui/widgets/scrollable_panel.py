"""Прокручиваемое содержимое карточек с длинными реквизитами."""

import tkinter as tk
from tkinter import ttk

from certificate_analyzer.presentation.gui.styles import CARD_BG_COLOR


class ScrollablePanel(ttk.Frame):
    """Оставляет действия снаружи, а реквизиты прокручивает внутри панели."""

    def __init__(self, parent, *, autohide=False):
        super().__init__(parent, style="Status.TFrame")
        self.canvas = tk.Canvas(self, background=CARD_BG_COLOR, highlightthickness=0,
                                width=1, height=1, takefocus=True)
        self._autohide = autohide
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self._sync_scrollbar)
        self.body = ttk.Frame(self.canvas, style="Status.TFrame")
        self._body_id = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self._resize)
        self.body.bind("<Configure>", self._update_region)
        for key, units in (("<Next>", 1), ("<Prior>", -1)):
            self.canvas.bind(key, lambda _, units=units: self.canvas.yview_scroll(units, "pages"))

    def _resize(self, event):
        self.canvas.itemconfigure(self._body_id, width=event.width)

    def _sync_scrollbar(self, first, last):
        self.scrollbar.set(first, last)
        if self._autohide:
            if float(first) <= 0 and float(last) >= 1:
                self.scrollbar.pack_forget()
            elif not self.scrollbar.winfo_manager():
                self.scrollbar.pack(side="right", fill="y", before=self.canvas)

    def _update_region(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def bind_mousewheel(self):
        """Ограничивает обработку колеса этой карточкой, не меняя другие окна."""
        def bind_children(widget):
            if isinstance(widget, (tk.Listbox, tk.Text, ttk.Treeview)):
                return
            widget.bind("<MouseWheel>", self._wheel, add="+")
            widget.bind("<Button-4>", lambda _: self._scroll(-1), add="+")
            widget.bind("<Button-5>", lambda _: self._scroll(1), add="+")
            for child in widget.winfo_children():
                bind_children(child)
        bind_children(self.canvas)

    def _wheel(self, event):
        if event.delta:
            return self._scroll(-max(1, abs(event.delta) // 120) if event.delta > 0 else max(1, abs(event.delta) // 120))

    def _scroll(self, units):
        if self.body.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(units, "units")
        return "break"
