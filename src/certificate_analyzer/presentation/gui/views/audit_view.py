"""Окно просмотра журнала аудита событий безопасности и операций с файлами."""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from certificate_analyzer.presentation.gui.styles import (
    TEXT_COLOR,
    UI_FONT,
)

if TYPE_CHECKING:
    from certificate_analyzer.application.services.audit_service import AuditService

AUDIT_COLUMNS = {
    "created_at": ("Дата и время", 140),
    "event_type": ("Событие", 160),
    "entity_type": ("Сущность", 110),
    "entity_id": ("Идентификатор", 180),
    "description": ("Описание", 360),
}


class AuditWindow(tk.Toplevel):
    """Окно отображения журнала аудита системы."""

    def __init__(self, parent: tk.Widget, audit_service: "AuditService"):
        """Инициализирует окно аудита.

        Args:
            parent: Родительский виджет Tkinter.
            audit_service: Сервис журнала аудита.
        """
        super().__init__(parent)
        self.audit = audit_service
        self.title("Журнал аудита событий")
        self.geometry("980x520")
        self.minsize(700, 380)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        """Создает элементы управления и таблицу событий."""
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Button(toolbar, text="Обновить", command=self.refresh).pack(side="left", padx=(0, 6))

        ttk.Label(toolbar, text="Фильтр по типу:").pack(side="left", padx=(10, 4))
        self.filter_var = tk.StringVar(value="Все")
        event_types = ["Все", "CERTIFICATE_IMPORTED", "FILE_DELETED", "RECORD_DELETED", "FILE_OPENED", "FILE_REVEALED"]
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var, values=event_types, state="readonly", width=22)
        filter_combo.pack(side="left")
        filter_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        self.stats_label = ttk.Label(frame, font=(UI_FONT, 9, "bold"), foreground=TEXT_COLOR)
        self.stats_label.pack(anchor="w", pady=(0, 6))

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=list(AUDIT_COLUMNS),
            show="headings",
            selectmode="browse",
        )
        for key, (title, width) in AUDIT_COLUMNS.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=60)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """Обновляет таблицу событий из базы данных."""
        if not self.audit:
            return

        selected_type = self.filter_var.get()
        event_filter = None if selected_type == "Все" else selected_type

        events = self.audit.list_events(event_type=event_filter, limit=200)
        self.tree.delete(*self.tree.get_children())

        for ev in events:
            date_str = ev.created_at.strftime("%d.%m.%Y %H:%M:%S") if ev.created_at else "—"
            short_id = ev.entity_id[:20] + "…" if len(ev.entity_id) > 20 else ev.entity_id
            self.tree.insert(
                "",
                "end",
                values=(
                    date_str,
                    ev.event_type,
                    ev.entity_type,
                    short_id,
                    ev.description,
                ),
            )

        self.stats_label.config(text=f"Всего событий в журнале: {len(events)}")
