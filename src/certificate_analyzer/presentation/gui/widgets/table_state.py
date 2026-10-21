"""Общие визуальные состояния табличных представлений."""

from dataclasses import dataclass
from tkinter import ttk

from certificate_analyzer.presentation.gui.styles import (
    SECONDARY_TEXT_COLOR,
    UI_FONT,
)


def sort_heading_text(title: str, active: bool, descending: bool) -> str:
    """Добавляет к активному заголовку направление сортировки."""
    if not active:
        return title
    return f"{title} {'↓' if descending else '↑'}"


@dataclass
class TableState:
    """Выделение, фокус строки и прокрутка до перезагрузки данных."""

    selected: tuple[str, ...]
    focused: str
    horizontal: float
    vertical: float

    @classmethod
    def capture(cls, tree):
        """Запоминает состояние таблицы перед заменой строк."""
        return cls(tuple(tree.selection()), tree.focus(), tree.xview()[0], tree.yview()[0])

    def restore(self, tree):
        """Восстанавливает только существующие строки, не выбирая другую запись."""
        selected = tuple(row for row in self.selected if tree.exists(row))
        tree.selection_set(selected)
        tree.focus(self.focused if self.focused and tree.exists(self.focused) else "")
        tree.xview_moveto(self.horizontal)
        tree.yview_moveto(self.vertical)


class EmptyStateLabel(ttk.Label):
    """Сообщение, которое накладывается поверх пустой таблицы."""

    def __init__(self, parent, text: str) -> None:
        super().__init__(
            parent,
            text=text,
            justify="center",
            anchor="center",
            foreground=SECONDARY_TEXT_COLOR,
            font=(UI_FONT, 11),
            padding=18,
            style="Empty.TLabel",
        )
        parent.bind("<Configure>", self._resize, add="+")

    def _resize(self, event):
        """Переносит сообщение внутри узкой таблицы."""
        self.configure(wraplength=max(80, event.width - 60))

    def show(self, text: str | None = None) -> None:
        """Показывает сообщение в центре таблицы."""
        if text is not None:
            self.configure(text=text)
        self.place(relx=0.5, rely=0.45, anchor="center")
        self.lift()

    def hide(self) -> None:
        """Скрывает сообщение, когда в таблице появились строки."""
        self.place_forget()
