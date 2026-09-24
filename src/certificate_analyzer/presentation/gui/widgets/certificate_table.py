import tkinter as tk
from tkinter import ttk

from certificate_analyzer.presentation.gui.styles import (
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    NORMAL_COLOR,
    NORMAL_TEXT,
    WARNING_COLOR,
    WARNING_TEXT,
)


class CertificateTable(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.columns = (
            "ФИО",
            "Файл",
            "Действителен до",
            "Осталось дней",
            "Подразделение",
            "Телефон",
            "Статус",
        )
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=15)
        
        col_widths = [160, 150, 110, 110, 120, 120, 110]
        for col, width in zip(self.columns, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=width, anchor=tk.W, stretch=True, minwidth=50)

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure("expired", background=EXPIRED_COLOR, foreground=EXPIRED_TEXT)
        self.tree.tag_configure("warning", background=WARNING_COLOR, foreground=WARNING_TEXT)
        self.tree.tag_configure("normal", background=NORMAL_COLOR, foreground=NORMAL_TEXT)
        self.tree.tag_configure("duplicate", background="#fff3cd", foreground="black")

        self.sort_reverse = {col: False for col in self.columns}
        self._on_select_callback = None
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def set_on_select_callback(self, callback):
        self._on_select_callback = callback

    def _on_select(self, event):
        if self._on_select_callback:
            selection = self.tree.selection()
            if selection:
                item = self.tree.item(selection[0])
                self._on_select_callback(item["values"])

    def clear(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def insert_row(self, values, tags=()):
        self.tree.insert("", tk.END, values=values, tags=tags)

    def sort_column(self, col):
        pass # Implementation of sort
