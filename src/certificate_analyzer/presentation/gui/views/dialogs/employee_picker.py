"""Диалог выбора сотрудника и контекстные меню полей ввода."""

from certificate_analyzer.presentation.gui.widgets.table_sort import TreeviewSorter
import tkinter as tk
from tkinter import ttk
from typing import Any

def _add_entry_context_menu(widget: tk.Widget) -> None:
    """Добавляет контекстное меню (Копировать/Вставить/Вырезать) и поддержку горячих клавиш с русской раскладкой."""
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))

    def show_menu(e: tk.Event) -> None:
        menu.tk_popup(e.x_root, e.y_root)

    widget.bind("<Button-3>", show_menu)


class EmployeePickerDialog(tk.Toplevel):
    """Модальное диалоговое окно для интерактивного выбора сотрудника из справочника."""

    def __init__(self, parent: tk.Widget, employees: list[Any]) -> None:
        """Инициализирует диалог выбора сотрудника.

        Args:
            parent: Родительский виджет Tkinter.
            employees: Список объектов сотрудников Employee.
        """
        super().__init__(parent)
        self.title("Выбор сотрудника из справочника")
        self.geometry("680x420")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.employees = list(employees)
        self.selected_employee: Any | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Создает элементы интерфейса выбора сотрудника с поиском и таблицей."""
        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill="both", expand=True)

        # Панель поиска
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(search_frame, text="Поиск сотрудника:").pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=35)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        search_entry.focus_set()
        _add_entry_context_menu(search_entry)

        ttk.Button(search_frame, text="Очистить", command=lambda: self.search_var.set("")).pack(side="left")

        # Таблица сотрудников
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill="both", expand=True, pady=4)

        columns = ("full_name", "department", "position", "email")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("full_name", text="ФИО сотрудника")
        self.tree.heading("department", text="Подразделение")
        self.tree.heading("position", text="Должность")
        self.tree.heading("email", text="Email")

        self.sorter = TreeviewSorter(self.tree)

        self.tree.column("full_name", width=220)
        self.tree.column("department", width=140)
        self.tree.column("position", width=140)
        self.tree.column("email", width=130)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda _: self._select())
        self.tree.bind("<Return>", lambda _: self._select())

        # Нижняя панель с кнопками
        btn_box = ttk.Frame(main_frame)
        btn_box.pack(fill="x", pady=(10, 0))

        ttk.Button(btn_box, text="Отмена", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_box, text="Выбрать", command=self._select, style="Accent.TButton").pack(side="right")

        self._filter()

    def _filter(self) -> None:
        """Фильтрует список отображаемых сотрудников по введенной поисковой строке."""
        self.tree.delete(*self.tree.get_children())
        query = self.search_var.get().strip().casefold()

        for idx, emp in enumerate(self.employees):
            name = getattr(emp, "full_name", "") or ""
            dept = getattr(emp, "department", "") or ""
            pos = getattr(emp, "position", "") or ""
            email = getattr(emp, "email", "") or ""

            if not query or (
                query in name.casefold()
                or query in dept.casefold()
                or query in pos.casefold()
                or query in email.casefold()
            ):
                self.tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(name, dept, pos, email),
                )

        self.sorter.apply()

    def _select(self) -> None:
        """Фиксирует выбор сотрудника и закрывает диалоговое окно."""
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.employees):
            self.selected_employee = self.employees[idx]
        self.destroy()

    def show(self) -> Any | None:
        """Отображает диалог модально и возвращает выбранного сотрудника.

        Returns:
            Any | None: Выбранный объект Employee или None.
        """
        self.wait_window()
        return self.selected_employee

