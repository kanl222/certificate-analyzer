"""Представление вкладки сотрудников организации в графическом интерфейсе."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.mchd.validator import is_valid_inn, is_valid_snils
from certificate_analyzer.presentation.gui.styles import UI_FONT

EMPLOYEE_COLUMNS = {
    "full_name": ("ФИО сотрудника", 220),
    "position": ("Должность", 160),
    "department": ("Подразделение", 160),
    "office": ("Кабинет", 80),
    "phones": ("Телефоны", 140),
    "email": ("Email", 140),
    "inn": ("ИНН", 110),
    "snils": ("СНИЛС", 110),
}


class EmployeeDialog(tk.Toplevel):
    """Модальное диалоговое окно добавления или редактирования сотрудника."""

    def __init__(
        self,
        parent: tk.Widget,
        employee: Employee | None = None,
        on_save: Callable[[Employee], None] | None = None,
    ) -> None:
        """Инициализирует диалоговое окно сотрудника.

        Args:
            parent: Родительский виджет.
            employee: Экземпляр редактируемого сотрудника (None для создания).
            on_save: Колбэк, вызываемый после успешного сохранения.
        """
        super().__init__(parent)
        self.employee = employee
        self.on_save = on_save
        self.title("Редактировать сотрудника" if employee else "Новый сотрудник")
        self.geometry("480x380")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._init_ui()

    def _init_ui(self) -> None:
        """Создает форму ввода реквизитов сотрудника."""
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        fields = [
            ("ФИО сотрудника *:", "full_name", self.employee.full_name if self.employee else ""),
            ("Должность:", "position", (self.employee.position if self.employee and self.employee.position else "")),
            ("Подразделение:", "department", (self.employee.department if self.employee and self.employee.department else "")),
            ("Кабинет:", "office", (self.employee.office if self.employee and self.employee.office else "")),
            ("Телефоны:", "phones", (", ".join(self.employee.phones) if self.employee and self.employee.phones else "")),
            ("Email:", "email", (self.employee.email if self.employee and self.employee.email else "")),
            ("ИНН:", "inn", (self.employee.inn if self.employee and self.employee.inn else "")),
            ("СНИЛС:", "snils", (self.employee.snils if self.employee and self.employee.snils else "")),
        ]

        self.entries: dict[str, tk.StringVar] = {}

        for row, (label, field_name, initial_val) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=initial_val)
            self.entries[field_name] = var
            ttk.Entry(frame, textvariable=var, width=34).grid(row=row, column=1, pady=3, padx=(8, 0))

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=len(fields), column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttk.Button(btn_box, text="Отмена", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_box, text="Сохранить", style="Accent.TButton", command=self._save).pack(side="right")

    def _save(self) -> None:
        """Валидирует данные формы и выполняет сохранение."""
        full_name = self.entries["full_name"].get().strip()
        if not full_name:
            messagebox.showerror("Ошибка", "ФИО сотрудника обязательно для заполнения", parent=self)
            return

        inn = self.entries["inn"].get().strip() or None
        if inn and not is_valid_inn(inn):
            messagebox.showerror("Ошибка", f"Некорректный формат ИНН: {inn} (ожидается 10 или 12 цифр)", parent=self)
            return

        snils = self.entries["snils"].get().strip() or None
        if snils and not is_valid_snils(snils):
            messagebox.showerror("Ошибка", f"Некорректный формат СНИЛС: {snils} (ожидается 11 цифр)", parent=self)
            return

        phones_raw = self.entries["phones"].get().strip()
        phones = [p.strip() for p in phones_raw.split(",") if p.strip()]

        emp_id = self.employee.id if self.employee else None
        saved_emp = Employee(
            id=emp_id,
            full_name=full_name,
            position=self.entries["position"].get().strip() or None,
            department=self.entries["department"].get().strip() or None,
            office=self.entries["office"].get().strip() or None,
            phones=phones,
            email=self.entries["email"].get().strip() or None,
            inn=inn,
            snils=snils,
        )

        if self.on_save:
            self.on_save(saved_emp)
        self.destroy()


class EmployeesView(ttk.Frame):
    """Виджет вкладки учета и управления справочником сотрудников."""

    def __init__(
        self,
        parent: tk.Widget,
        application: Any,
        on_message: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Инициализирует представление вкладки сотрудников.

        Args:
            parent: Родительский контейнер Tkinter.
            application: Контейнер сервисов приложения ApplicationContainer.
            on_message: Функция вывода сообщений в статусную строку главного окна.
            **kwargs: Дополнительные параметры ttk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.app = application
        self.on_message = on_message or (lambda _: None)
        self.employees: list[Employee] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        """Формирует графические элементы интерфейса вкладки сотрудников."""
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(
            toolbar,
            text="+ Добавить сотрудника",
            style="Accent.TButton",
            command=self.show_create_dialog,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Обновить",
            command=self.refresh,
            style="Toolbar.TButton",
        ).pack(side="left", padx=3)

        filters = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="Поиск:", style="Panel.TLabel").pack(
            side="left", padx=(0, 4)
        )
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var, width=28)
        self.search_entry.pack(side="left", padx=(0, 4))
        self.search_entry.bind("<Return>", lambda _: self.refresh())
        ttk.Button(
            filters, text="Найти", command=self.refresh, style="Toolbar.TButton"
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            filters,
            text="Сбросить",
            command=self._clear_search,
            style="Toolbar.TButton",
        ).pack(side="left")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        cols = list(EMPLOYEE_COLUMNS.keys())
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
        )

        for col_id, (col_title, col_width) in EMPLOYEE_COLUMNS.items():
            self.tree.heading(col_id, text=col_title, anchor="w")
            self.tree.column(col_id, width=col_width, minwidth=60, anchor="w")

        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda _: self.edit_selected())
        self.tree.bind("<Button-3>", self._show_context_menu)

        self._build_context_menu()

        bottom_bar = ttk.Frame(self, padding=(0, 6, 0, 0))
        bottom_bar.pack(fill="x")
        self.stats_label = ttk.Label(bottom_bar, text="Всего сотрудников: 0", font=(UI_FONT, 9))
        self.stats_label.pack(side="left")

    def _build_context_menu(self) -> None:
        """Создает контекстное меню правой кнопки мыши для строк таблицы."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Редактировать", command=self.edit_selected)
        self.context_menu.add_command(label="Создать заявку на сертификат", command=self.create_request_for_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Удалить сотрудника", command=self.delete_selected)

    def _show_context_menu(self, event: tk.Event) -> None:
        """Отображает контекстное меню для выбранной строки."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _clear_search(self) -> None:
        """Сбрасывает поисковую строку и перезагружает список."""
        self.search_var.set("")
        self.refresh()

    def get_selected_employee(self) -> Employee | None:
        """Возвращает объект выделенного в таблице сотрудника."""
        selected = self.tree.selection()
        if not selected:
            return None
        emp_id = int(selected[0])
        return next((e for e in self.employees if e.id == emp_id), None)

    def refresh(self) -> None:
        """Перезагружает список сотрудников из базы данных."""
        if not getattr(self.app, "employees", None):
            return

        search_query = self.search_var.get().strip() or None
        self.employees = self.app.employees.list_employees(search=search_query)

        self.tree.delete(*self.tree.get_children())
        for emp in self.employees:
            phones_str = ", ".join(emp.phones) if emp.phones else "—"
            self.tree.insert(
                "",
                "end",
                iid=str(emp.id),
                values=(
                    emp.full_name,
                    emp.position or "—",
                    emp.department or "—",
                    emp.office or "—",
                    phones_str,
                    emp.email or "—",
                    emp.inn or "—",
                    emp.snils or "—",
                ),
            )

        self.stats_label.config(text=f"Всего сотрудников: {len(self.employees)}")
        self.on_message(f"Сотрудников загружено: {len(self.employees)}")

    def show_create_dialog(self) -> None:
        """Открывает диалог добавления нового сотрудника."""
        def on_save(emp: Employee) -> None:
            self.app.employees.save_employee(emp)
            self.refresh()
            self.on_message(f"Сотрудник {emp.full_name} успешно добавлен")

        EmployeeDialog(self, employee=None, on_save=on_save)

    def edit_selected(self) -> None:
        """Открывает диалог редактирования для выделенного сотрудника."""
        emp = self.get_selected_employee()
        if not emp:
            messagebox.showinfo("Информация", "Выберите сотрудника для редактирования", parent=self)
            return

        def on_save(updated_emp: Employee) -> None:
            self.app.employees.save_employee(updated_emp)
            self.refresh()
            self.on_message(f"Данные сотрудника {updated_emp.full_name} обновлены")

        EmployeeDialog(self, employee=emp, on_save=on_save)

    def delete_selected(self) -> None:
        """Удаляет выбранного сотрудника после подтверждения пользователем."""
        emp = self.get_selected_employee()
        if not emp:
            messagebox.showinfo("Информация", "Выберите сотрудника для удаления", parent=self)
            return

        confirm = messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы действительно хотите удалить сотрудника:\n\n{emp.full_name}\n({emp.department or 'Без подразделения'})?",
            parent=self,
        )
        if not confirm:
            return

        if emp.id is not None:
            self.app.employees.delete_employee(emp.id)
            self.refresh()
            self.on_message(f"Сотрудник {emp.full_name} удален")

    def create_request_for_selected(self) -> None:
        """Создает заявку на сертификат для выбранного сотрудника."""
        emp = self.get_selected_employee()
        if not emp:
            messagebox.showinfo("Информация", "Выберите сотрудника для создания заявки", parent=self)
            return

        # Переключаемся на вкладку заявок или вызываем диалог заявок
        main_win = self.winfo_toplevel()
        if hasattr(main_win, "requests_view"):
            main_win.requests_view.show_create_dialog_for(emp.full_name, emp.department or "")
        elif hasattr(self.app, "certificate_requests"):
            # Создаем заявку напрямую
            req = self.app.certificate_requests.create_request(
                employee_name=emp.full_name,
                department=emp.department,
            )
            self.on_message(f"Заявка {req.request_number} для {emp.full_name} создана")
