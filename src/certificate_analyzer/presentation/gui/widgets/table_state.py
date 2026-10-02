"""Общие визуальные состояния табличных представлений."""

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
        )

    def show(self, text: str | None = None) -> None:
        """Показывает сообщение в центре таблицы."""
        if text is not None:
            self.configure(text=text)
        self.place(relx=0.5, rely=0.45, anchor="center")
        self.lift()

    def hide(self) -> None:
        """Скрывает сообщение, когда в таблице появились строки."""
        self.place_forget()
