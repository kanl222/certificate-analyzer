"""Представление вкладки машиночитаемых доверенностей (МЧД) и диалоговые окна."""

from datetime import timezone
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import pyperclip

from certificate_analyzer.presentation.gui.styles import (
    BG_COLOR,
    UI_FONT,
)


UTC = timezone.utc

class AuthoritiesViewWindow:
    """Окно детального просмотра объединенных полномочий нескольких МЧД."""

    def __init__(self, parent: tk.Widget, merged_data: dict[str, Any]) -> None:
        """Инициализирует окно просмотра полномочий.

        Args:
            parent: Родительский виджет.
            merged_data: Словарь с объединенными данными кодов полномочий.
        """
        self.parent = parent
        self.merged_data = merged_data
        self.window: tk.Toplevel | None = None
        self._create_window()

    def _create_window(self) -> None:
        """Создает и настраивает Toplevel окно."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Объединенные полномочия МЧД")
        self.window.geometry("600x500")
        self.window.configure(bg=BG_COLOR)
        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Закрывает окно."""
        if self.window:
            self.window.destroy()
            self.window = None

    def setup_ui(self) -> None:
        """Создает элементы управления и список кодов полномочий."""
        if not self.window:
            return

        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(
            title_frame,
            text="Объединенные полномочия",
            font=(UI_FONT, 14, "bold"),
        ).pack(anchor=tk.W)

        info_frame = ttk.LabelFrame(
            main_frame, text=" Исходные файлы ", padding=10
        )
        info_frame.pack(fill=tk.X, pady=(0, 10))
        files_text = "\n".join(
            [f"• {f}" for f in self.merged_data.get("file_names", [])]
        )
        ttk.Label(info_frame, text=files_text, font=(UI_FONT, 9)).pack(
            anchor=tk.W
        )

        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        stats_text = (
            f"Всего файлов: {self.merged_data.get('total_files', 0)} | "
            f"Уникальных кодов: {self.merged_data.get('unique_codes_count', 0)}"
        )
        ttk.Label(
            stats_frame, text=stats_text, font=(UI_FONT, 10, "bold")
        ).pack()

        codes_frame = ttk.LabelFrame(
            main_frame, text=" Коды полномочий ", padding=10
        )
        codes_frame.pack(fill=tk.BOTH, expand=True)

        listbox_frame = ttk.Frame(codes_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        self.codes_listbox = tk.Listbox(
            listbox_frame,
            height=12,
            selectmode=tk.EXTENDED,
            font=("Courier New", 10),
        )
        self.codes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            listbox_frame, orient=tk.VERTICAL, command=self.codes_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.codes_listbox.configure(yscrollcommand=scrollbar.set)

        for code in self.merged_data.get("codes", []):
            self.codes_listbox.insert(tk.END, code)

        self.codes_listbox.bind(
            "<Control-c>", lambda _: self.copy_selected_codes()
        )
        self.codes_listbox.bind(
            "<Control-C>", lambda _: self.copy_selected_codes()
        )

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(
            btn_frame,
            text="Копировать все коды",
            command=self.copy_all_codes,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Копировать выбранные",
            command=self.copy_selected_codes,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Закрыть",
            command=self._on_close,
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

    def copy_all_codes(self) -> None:
        """Копирует все полномочия в буфер обмена."""
        codes = self.merged_data.get("codes", [])
        if codes:
            pyperclip.copy("\n".join(codes))
            messagebox.showinfo(
                "Успех", f"Скопировано {len(codes)} кодов", parent=self.window
            )

    def copy_selected_codes(self) -> None:
        """Копирует выделенные в списке коды в буфер обмена."""
        selected = self.codes_listbox.curselection()
        if not selected:
            messagebox.showwarning(
                "Внимание",
                "Выберите коды для копирования",
                parent=self.window,
            )
            return
        codes = [self.codes_listbox.get(i) for i in selected]
        pyperclip.copy("\n".join(codes))
        messagebox.showinfo(
            "Успех", f"Скопировано {len(codes)} кодов", parent=self.window
        )

