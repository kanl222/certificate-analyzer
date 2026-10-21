"""Панель управления с переносом целых групп по доступной ширине."""

import tkinter as tk
from tkinter import ttk


class ResponsiveBar(ttk.Frame):
    """Сохраняет порядок элементов и переносит их без обрезания подписей."""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("style", "Panel.TFrame")
        kwargs.setdefault("padding", (8, 6))
        super().__init__(parent, **kwargs)
        self._items: list[tuple[tk.Widget, bool]] = []
        self._layout_after = None
        self.bind("<Configure>", self._schedule_layout, add="+")
        self.bind("<Destroy>", self._cancel_layout, add="+")

    def add(self, widget, *, stretch=False):
        """Добавляет кнопку или группу полей; stretch отдаёт ей свободное место."""
        self._items.append((widget, stretch))
        self._schedule_layout()
        return widget

    def _schedule_layout(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self._layout_after is None:
            self._layout_after = self.after_idle(self._layout)

    def _cancel_layout(self, event):
        if event.widget is self and self._layout_after is not None:
            self.after_cancel(self._layout_after)
            self._layout_after = None

    def _layout(self):
        self._layout_after = None
        if self.winfo_width() <= 1:
            return
        padding = [self.winfo_pixels(str(value)) for value in self.cget("padding")]
        left = padding[0] if padding else 0
        right = padding[2] if len(padding) > 2 else left
        available = max(1, self.winfo_width() - left - right - 2)
        top = padding[1] if len(padding) > 1 else left
        bottom = padding[3] if len(padding) > 3 else top
        rows = [[]]
        used = 0
        for widget, stretch in self._items:
            width = widget.winfo_reqwidth() + 8
            if rows[-1] and used + width > available:
                rows.append([])
                used = 0
            rows[-1].append((widget, stretch))
            used += width
        y = top + 1
        for row in rows:
            height = max((widget.winfo_reqheight() for widget, _ in row), default=0)
            extra = max(0, available - sum(widget.winfo_reqwidth() + 8 for widget, _ in row))
            stretch_count = sum(stretch for _, stretch in row)
            x = left + 1
            for widget, stretch in row:
                width = widget.winfo_reqwidth() + (extra // stretch_count if stretch else 0)
                widget.place(x=x, y=y + (height - widget.winfo_reqheight()) // 2,
                             width=min(width, available), height=widget.winfo_reqheight())
                x += width + 8
            y += height + 6
        self.configure(height=y - 6 + bottom + 1)


def fit_dialog(window, *, width, height):
    """Подбирает размер диалога по форме и оставляет возможность его увеличить."""
    window.update_idletasks()
    available_width = max(1, window.winfo_screenwidth() - 40)
    available_height = max(1, window.winfo_screenheight() - 100)
    desired_width = min(available_width, max(width, window.winfo_reqwidth()))
    desired_height = min(available_height, max(height, window.winfo_reqheight()))
    window.geometry(f"{desired_width}x{desired_height}")
    window.minsize(desired_width, desired_height)
    window.resizable(True, True)
    window.bind("<Escape>", lambda _: window.destroy())
