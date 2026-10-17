"""Представление вкладки заявок на сертификаты в графическом интерфейсе."""

from certificate_analyzer.presentation.gui.widgets.table_sort import TreeviewSorter
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.presentation.gui.styles import (
    UI_FONT,
)
from certificate_analyzer.presentation.gui.widgets.table_state import EmptyStateLabel
from certificate_analyzer.presentation.gui.views.dialogs.employee_picker import EmployeePickerDialog, _add_entry_context_menu
from certificate_analyzer.presentation.gui.views.employees_view import EmployeeDialog

REQUEST_COLUMNS = {
    "request_number": ("Номер заявки", 130),
    "employee": ("Сотрудник", 180),
    "department": ("Подразделение", 140),
    "status": ("Статус", 120),
    "submitted_at": ("Дата подачи", 110),
    "issued_at": ("Дата выпуска", 110),
    "certificate": ("Сертификат", 140),
    "comment": ("Комментарий", 180),
}

REQUEST_STATUS_CHOICES = {
    "Все статусы": None,
    "Не подана": CertificateRequestStatus.NOT_SUBMITTED,
    "Подана": CertificateRequestStatus.SUBMITTED,
    "В работе": CertificateRequestStatus.IN_PROGRESS,
    "Выпущен": CertificateRequestStatus.ISSUED,
    "Получен": CertificateRequestStatus.RECEIVED,
    "Обработана": CertificateRequestStatus.PROCESSED,
    "Отклонена": CertificateRequestStatus.REJECTED,
    "Аннулирована": CertificateRequestStatus.CANCELLED,
}

REQUEST_PAGE_SIZE = 100


class RequestsView(ttk.Frame):
    """Виджет вкладки учета и управления заявками на выпуск сертификатов."""

    def __init__(
        self,
        parent: tk.Widget,
        application,
        on_message: Callable[[str], None] | None = None,
        **kwargs,
    ):
        """Инициализирует представление вкладки заявок.

        Args:
            parent: Родительский виджет Tkinter.
            application: Контейнер сервисов приложения ApplicationContainer.
            on_message: Функция обратного вызова для вывода сообщений в статусную строку.
            **kwargs: Дополнительные параметры ttk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.app = application
        self.on_message = on_message or (lambda _: None)
        self.requests: list[CertificateRequest] = []
        self.offset = 0
        self.search_after: str | None = None
        self._build_ui()
        self.bind("<Destroy>", self._on_destroy)
        self.refresh()

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self and self.search_after:
            self.after_cancel(self.search_after)
            self.search_after = None

    def _build_ui(self) -> None:
        """Создает элементы управления, панель фильтров и таблицу заявок."""
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Button(
            toolbar,
            text="Создать заявку…",
            command=self.show_create_dialog,
            style="Accent.TButton",
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            toolbar,
            text="Сменить статус…",
            command=self.show_status_dialog,
            style="Toolbar.TButton",
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar,
            text="Привязать сертификат…",
            command=self.show_link_dialog,
            style="Toolbar.TButton",
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar,
            text="Обновить",
            command=self.refresh,
            style="Toolbar.TButton",
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar,
            text="Удалить",
            command=self.delete_selected,
            style="Toolbar.TButton",
        ).pack(side="right", padx=(3, 0))

        ttk.Button(
            toolbar,
            text="Отметить обработанной",
            command=self.mark_processed,
            style="Toolbar.TButton",
        ).pack(side="right")

        # Панель фильтрации
        filters = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        filters.pack(fill="x", pady=(0, 8))

        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="Поиск:", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._search_changed)
        search_filter_entry = ttk.Entry(filters, textvariable=self.search_var, width=25)
        search_filter_entry.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        _add_entry_context_menu(search_filter_entry)

        ttk.Label(filters, text="Статус:", style="Panel.TLabel").grid(
            row=0, column=2, padx=(0, 4)
        )
        self.status_var = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=list(REQUEST_STATUS_CHOICES),
            state="readonly",
            width=16,
        )
        status_combo.grid(row=0, column=3, padx=(0, 8))
        status_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh(reset=True))

        ttk.Button(
            filters,
            text="Сбросить",
            command=self.clear_filters,
            style="Toolbar.TButton",
        ).grid(row=0, column=4)

        self.stats_label = ttk.Label(self, style="Summary.TLabel")

        # Таблица Treeview
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=list(REQUEST_COLUMNS),
            show="headings",
            selectmode="extended",
        )
        for key, (title, width) in REQUEST_COLUMNS.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=70)

        self.sorter = TreeviewSorter(self.tree, kinds={"submitted_at": "date", "issued_at": "date"})

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        scroll_x = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview,
        )
        scroll_x.pack(side="bottom", fill="x")
        self.tree.configure(
            yscrollcommand=scrollbar.set,
            xscrollcommand=scroll_x.set,
        )
        self.tree.pack(fill="both", expand=True)
        self.empty_label = EmptyStateLabel(
            table_frame,
            "Заявок пока нет\nСоздайте первую заявку на сертификат",
        )

        page_bar = ttk.Frame(self, padding=(8, 4))
        page_bar.pack(fill="x")
        self.page_label = ttk.Label(page_bar)
        self.page_label.pack(side="left")
        self.next_button = ttk.Button(page_bar, text="Следующая ›", command=lambda: self.change_page(1))
        self.next_button.pack(side="right", padx=(6, 0))
        self.previous_button = ttk.Button(page_bar, text="‹ Предыдущая", command=lambda: self.change_page(-1))
        self.previous_button.pack(side="right")

        # Подсветка статусов
        self.tree.tag_configure("in_progress", foreground="#0d6efd")
        self.tree.tag_configure("issued", foreground="#198754")
        self.tree.tag_configure("processed", foreground="#6c757d")
        self.tree.tag_configure("rejected", foreground="#dc3545")
        self.tree.tag_configure("received", foreground="#0f5132")
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Delete>", lambda _: self.delete_selected())

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Сменить статус…",
            command=self.show_status_dialog,
        )
        self.context_menu.add_command(
            label="Привязать сертификат…",
            command=self.show_link_dialog,
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Отметить обработанной",
            command=self.mark_processed,
        )
        self.context_menu.add_command(
            label="Удалить заявку",
            command=self.delete_selected,
        )

    def _show_context_menu(self, event: tk.Event) -> None:
        """Выбирает заявку под курсором и показывает доступные действия."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.context_menu.post(event.x_root, event.y_root)

    def on_double_click(self, event: tk.Event) -> None:
        """Открывает смену статуса только для строки под курсором."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.show_status_dialog()

    def clear_filters(self) -> None:
        """Сбрасывает установленные фильтры поиска и статуса."""
        self.search_var.set("")
        self.status_var.set("Все статусы")
        self.refresh(reset=True)

    def _search_changed(self, *_args) -> None:
        if self.search_after:
            self.after_cancel(self.search_after)
        self.search_after = self.after(250, lambda: self.refresh(reset=True))

    def change_page(self, direction: int) -> None:
        self.offset = max(0, self.offset + direction * REQUEST_PAGE_SIZE)
        self.refresh()

    def refresh(self, reset: bool = False) -> None:
        """Перезагружает список заявок из базы данных."""
        if not getattr(self.app, "certificate_requests", None):
            return
        if self.search_after:
            self.after_cancel(self.search_after)
            self.search_after = None
        if reset:
            self.offset = 0

        status_enum = REQUEST_STATUS_CHOICES.get(self.status_var.get())
        search_query = self.search_var.get().strip() or None

        counts = self.app.certificate_requests.count_by_status(status=status_enum, search=search_query)
        total = sum(counts.values())
        if self.offset >= total:
            self.offset = max(0, (total - 1) // REQUEST_PAGE_SIZE * REQUEST_PAGE_SIZE)
        self.requests = self.app.certificate_requests.list_requests(
            status=status_enum,
            search=search_query,
            limit=REQUEST_PAGE_SIZE,
            offset=self.offset,
        )

        self.tree.delete(*self.tree.get_children())

        for req in self.requests:
            emp_name = req.employee.full_name if req.employee else (req.comment if not req.department else "—")
            sub_date = req.submitted_at.strftime("%d.%m.%Y") if req.submitted_at else "—"
            iss_date = req.issued_at.strftime("%d.%m.%Y") if req.issued_at else "—"
            cert_str = req.certificate_fingerprint[:12] + "…" if req.certificate_fingerprint else "—"

            tag = ""
            if req.status == CertificateRequestStatus.IN_PROGRESS:
                tag = "in_progress"
            elif req.status == CertificateRequestStatus.ISSUED:
                tag = "issued"
            elif req.status == CertificateRequestStatus.RECEIVED:
                tag = "received"
            elif req.status == CertificateRequestStatus.PROCESSED:
                tag = "processed"
            elif req.status in (CertificateRequestStatus.REJECTED, CertificateRequestStatus.CANCELLED):
                tag = "rejected"

            self.tree.insert(
                "",
                "end",
                iid=str(req.id),
                values=(
                    req.request_number,
                    emp_name,
                    req.department or "—",
                    req.status.label,
                    sub_date,
                    iss_date,
                    cert_str,
                    req.comment,
                ),
                tags=(tag,) if tag else (),
            )

        self.sorter.apply()
        self.page_label.config(text=f"{self.offset + 1 if self.requests else 0}–{self.offset + len(self.requests)} из {total}")
        self.previous_button.config(state="normal" if self.offset else "disabled")
        self.next_button.config(state="normal" if self.offset + len(self.requests) < total else "disabled")

        if self.requests:
            self.empty_label.hide()
        elif search_query or status_enum is not None:
            self.empty_label.show(
                "По заданным условиям ничего не найдено\nИзмените или сбросьте фильтры"
            )
        else:
            self.empty_label.show(
                "Заявок пока нет\nСоздайте первую заявку на сертификат"
            )

        summary = (
            f"Всего заявок: {total}   "
            f"В работе: {counts.get(CertificateRequestStatus.IN_PROGRESS, 0)}   "
            f"Выпущено: {counts.get(CertificateRequestStatus.ISSUED, 0)}   "
            f"Обработано: {counts.get(CertificateRequestStatus.PROCESSED, 0)}"
        )
        self.stats_label.config(text=summary)
        self.on_message(summary)

    def show_create_dialog_for(
        self,
        full_name: str,
        department: str = "",
        employee_id: int | None = None,
    ) -> None:
        """Отображает диалог создания заявки с предустановленным сотрудником.

        Args:
            full_name: Полное имя (ФИО) сотрудника.
            department: Подразделение сотрудника.
        """
        self.show_create_dialog(initial_employee=full_name, initial_department=department, initial_employee_id=employee_id)

    def show_create_dialog(
        self,
        initial_employee: str = "",
        initial_department: str = "",
        initial_employee_id: int | None = None,
    ) -> None:
        """Отображает диалоговое окно создания новой заявки с выбором сотрудника из списка.

        Args:
            initial_employee: Начальное ФИО сотрудника (опционально).
            initial_department: Начальное подразделение (опционально).
        """
        dialog = tk.Toplevel(self)
        dialog.title("Новая заявка на сертификат")
        dialog.geometry("700x360")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        # Загрузка списка сотрудников из базы данных
        employees: list[Any] = []
        if hasattr(self.app, "employees") and self.app.employees:
            try:
                employees = self.app.employees.list_employees()
            except Exception:
                employees = []

        if not employees and hasattr(self.app, "certificates") and hasattr(self.app.certificates, "phonebook_service"):
            try:
                for c in self.app.certificates.phonebook_service.get_all_contacts():
                    name = c.get("name") if isinstance(c, dict) else getattr(c, "name", "")
                    dept = c.get("department") if isinstance(c, dict) else getattr(c, "department", "")
                    if name:
                        from certificate_analyzer.domain.models.employee import Employee
                        employees.append(Employee(full_name=name, department=dept))
            except Exception:
                pass

        emp_names = list(dict.fromkeys(e.full_name.strip() for e in employees if e.full_name.strip()))

        name_var = tk.StringVar(value=initial_employee)
        dept_var = tk.StringVar(value=initial_department)

        selected_employee = next((e for e in employees if e.id == initial_employee_id), None) if initial_employee_id is not None else None

        def clear_selection(*_args):
            nonlocal selected_employee
            selected_employee = None

        name_var.trace_add("write", clear_selection)

        def select_employee(employee):
            nonlocal selected_employee
            name_var.set(employee.full_name)
            dept_var.set(employee.department or "")
            selected_employee = employee

        def matching_employees():
            return [e for e in employees if e.full_name.strip() == name_var.get().strip()]

        if selected_employee is not None:
            select_employee(selected_employee)
        elif initial_employee:
            matches = matching_employees()
            if initial_department:
                matches = [e for e in matches if e.department == initial_department]
            if len(matches) == 1:
                select_employee(matches[0])

        ttk.Label(frame, text="Сотрудник:").grid(row=0, column=0, sticky="w", pady=6)
        emp_box = ttk.Frame(frame)
        emp_box.grid(row=0, column=1, sticky="ew", pady=6)

        emp_combo = ttk.Combobox(
            emp_box,
            textvariable=name_var,
            values=emp_names,
            width=28,
        )
        emp_combo.pack(side="left", fill="x", expand=True)
        _add_entry_context_menu(emp_combo)

        def on_combo_selected(_event=None):
            matches = matching_employees()
            if len(matches) == 1:
                select_employee(matches[0])
            else:
                clear_selection()
                dept_var.set("")

        emp_combo.bind("<<ComboboxSelected>>", on_combo_selected)

        def open_picker():
            picker = EmployeePickerDialog(dialog, employees=employees)
            picked = picker.show()
            dialog.grab_set()
            if picked:
                select_employee(picked)

        ttk.Button(
            emp_box,
            text="Выбрать…",
            command=open_picker,
            width=11,
        ).pack(side="left", padx=(6, 0))

        def create_employee():
            def on_save(employee):
                saved = self.app.employees.save_employee(employee)
                employees.append(saved)
                emp_combo.configure(values=list(dict.fromkeys(e.full_name.strip() for e in employees)))
                select_employee(saved)

            employee_dialog = EmployeeDialog(dialog, on_save=on_save)
            employee_dialog.entries["full_name"].set(name_var.get().strip())
            employee_dialog.entries["department"].set(dept_var.get().strip())
            dialog.wait_window(employee_dialog)
            if dialog.winfo_exists():
                dialog.grab_set()

        ttk.Button(
            emp_box,
            text="Создать сотрудника…",
            command=create_employee,
            state="normal" if getattr(self.app, "employees", None) else "disabled",
        ).pack(side="left", padx=(6, 0))

        ttk.Label(frame, text="Подразделение:").grid(row=1, column=0, sticky="w", pady=6)
        dept_entry = ttk.Entry(frame, textvariable=dept_var, width=42)
        dept_entry.grid(row=1, column=1, sticky="w", pady=6)
        _add_entry_context_menu(dept_entry)

        ttk.Label(frame, text="Номер заявки:").grid(row=2, column=0, sticky="w", pady=6)
        number_var = tk.StringVar()
        num_entry = ttk.Entry(frame, textvariable=number_var, width=42)
        num_entry.grid(row=2, column=1, sticky="w", pady=6)
        _add_entry_context_menu(num_entry)
        ttk.Label(frame, text="(оставьте пустым для автогенерации)", font=(UI_FONT, 8)).grid(row=3, column=1, sticky="w")

        ttk.Label(frame, text="Примечание:").grid(row=4, column=0, sticky="w", pady=6)
        comment_var = tk.StringVar()
        comment_entry = ttk.Entry(frame, textvariable=comment_var, width=42)
        comment_entry.grid(row=4, column=1, sticky="w", pady=6)
        _add_entry_context_menu(comment_entry)

        def save():
            name = name_var.get().strip()
            num = number_var.get().strip() or None
            dept = dept_var.get().strip()
            comm = comment_var.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Выберите или укажите ФИО сотрудника", parent=dialog)
                return
            try:
                employee = selected_employee
                if employee is None:
                    matches = matching_employees()
                    if len(matches) > 1:
                        raise ValueError("Найдено несколько сотрудников с таким ФИО. Нажмите «Выбрать…» и выберите нужного сотрудника")
                    employee = matches[0] if matches else None
                if employee is None or employee.id is None:
                    raise ValueError("Выберите сотрудника из справочника или нажмите «Создать сотрудника…»")
                self.app.certificate_requests.create_request(
                    request_number=num,
                    employee_id=employee.id,
                    full_name=name,
                    department=dept,
                    comment=comm,
                )
                dialog.destroy()
                self.refresh()
                self.on_message(f"Создана заявка для: {name}")
            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=5, column=0, columnspan=2, pady=16, sticky="e")
        ttk.Button(btn_box, text="Отмена", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_box, text="Создать заявку", command=save, style="Accent.TButton").pack(side="right")

    def show_status_dialog(self) -> None:
        """Отображает диалог смены статуса выбранной заявки."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Выбор", "Выберите заявку из списка")
            return

        req_id = int(selection[0])
        dialog = tk.Toplevel(self)
        dialog.title("Изменение статуса заявки")
        dialog.geometry("360x180")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Новый статус заявки:").pack(anchor="w", pady=(0, 6))

        statuses = [s for s in CertificateRequestStatus]
        status_map = {s.label: s for s in statuses}
        current_request = next(
            (request for request in self.requests if request.id == req_id),
            None,
        )
        current_status = (
            current_request.status
            if current_request is not None
            else CertificateRequestStatus.NOT_SUBMITTED
        )
        selected_status_var = tk.StringVar(value=current_status.label)

        combo = ttk.Combobox(
            frame,
            textvariable=selected_status_var,
            values=list(status_map.keys()),
            state="readonly",
            width=24,
        )
        combo.pack(fill="x", pady=6)

        def apply_status():
            new_st = status_map[selected_status_var.get()]
            try:
                self.app.certificate_requests.update_status(req_id, new_st)
                dialog.destroy()
                self.refresh()
                self.on_message(f"Статус заявки изменен на: {new_st.label}")
            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill="x", pady=12, side="bottom")
        ttk.Button(btn_box, text="Отмена", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_box, text="Применить", command=apply_status, style="Accent.TButton").pack(side="right")

    def show_link_dialog(self) -> None:
        """Отображает диалог привязки выпущенного сертификата к заявке."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Выбор", "Выберите заявку для привязки сертификата")
            return

        req_id = int(selection[0])
        dialog = tk.Toplevel(self)
        dialog.title("Привязка сертификата к заявке")
        dialog.geometry("760x440")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Выберите сертификат из хранилища:").pack(
            anchor="w",
            pady=(0, 6),
        )

        search_var = tk.StringVar()
        search_entry = ttk.Entry(frame, textvariable=search_var)
        search_entry.pack(fill="x", pady=(0, 8))
        _add_entry_context_menu(search_entry)

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True)
        columns = ("subject", "file", "valid_to", "status")
        picker = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        for column, title, width in (
            ("subject", "Владелец", 230),
            ("file", "Файл", 190),
            ("valid_to", "Действителен до", 110),
            ("status", "Статус", 120),
        ):
            picker.heading(column, text=title)
            picker.column(column, width=width, minwidth=80)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=picker.yview)
        picker.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        picker.pack(fill="both", expand=True)
        empty_label = EmptyStateLabel(
            table_frame,
            "В хранилище пока нет сертификатов\n"
            "Сначала добавьте сертификат на одноимённой вкладке",
        )
        picker_sorter = TreeviewSorter(picker, kinds={"valid_to": "date"})
        picker_offset = 0
        picker_after: str | None = None
        picker_page_size = 100
        page_bar = ttk.Frame(frame)
        page_bar.pack(fill="x", pady=(4, 0))
        page_label = ttk.Label(page_bar)
        page_label.pack(side="left")
        next_button = ttk.Button(page_bar, text="Следующая ›")
        next_button.pack(side="right", padx=(6, 0))
        previous_button = ttk.Button(page_bar, text="‹ Предыдущая")
        previous_button.pack(side="right")

        def populate_picker(reset: bool = False) -> None:
            nonlocal picker_offset, picker_after
            if picker_after:
                dialog.after_cancel(picker_after)
                picker_after = None
            if reset:
                picker_offset = 0
            query = CertificateQuery(
                search=search_var.get().strip(), limit=picker_page_size,
                offset=picker_offset, sort="subject",
            )
            total = self.app.certificates.statistics(query)["total"]
            if picker_offset >= total:
                picker_offset = max(0, (total - 1) // picker_page_size * picker_page_size)
                query = CertificateQuery(
                    search=query.search, limit=picker_page_size,
                    offset=picker_offset, sort="subject",
                )
            certificates = self.app.certificates.list(query)
            picker.delete(*picker.get_children())
            for certificate in certificates:
                row = certificate_to_dict(certificate)
                values = (
                    certificate.subject,
                    certificate.original_name,
                    row["valid_to"],
                    row["status"],
                )
                picker.insert(
                    "",
                    "end",
                    iid=certificate.fingerprint_sha256,
                    values=values,
                )
            picker_sorter.apply()
            page_label.config(text=f"{picker_offset + 1 if certificates else 0}–{picker_offset + len(certificates)} из {total}")
            previous_button.config(state="normal" if picker_offset else "disabled")
            next_button.config(state="normal" if picker_offset + len(certificates) < total else "disabled")
            if picker.get_children():
                empty_label.hide()
            elif query.search:
                empty_label.show("Сертификаты не найдены\nИзмените поисковый запрос")
            else:
                empty_label.show()

        def change_picker_page(direction: int) -> None:
            nonlocal picker_offset
            picker_offset = max(0, picker_offset + direction * picker_page_size)
            populate_picker()

        previous_button.config(command=lambda: change_picker_page(-1))
        next_button.config(command=lambda: change_picker_page(1))

        def schedule_picker_search(*_args) -> None:
            nonlocal picker_after
            if picker_after:
                dialog.after_cancel(picker_after)
            picker_after = dialog.after(250, lambda: populate_picker(reset=True))

        def cancel_picker_search(event: tk.Event) -> None:
            nonlocal picker_after
            if event.widget is dialog and picker_after:
                dialog.after_cancel(picker_after)
                picker_after = None

        dialog.bind("<Destroy>", cancel_picker_search)
        search_var.trace_add("write", schedule_picker_search)
        populate_picker()

        current_request = next(
            (request for request in self.requests if request.id == req_id),
            None,
        )
        if current_request and current_request.certificate_fingerprint:
            current = current_request.certificate_fingerprint
            if current in picker.get_children():
                picker.selection_set(current)
                picker.focus(current)
                picker.see(current)

        def link():
            picked = picker.selection()
            if not picked:
                messagebox.showwarning(
                    "Внимание",
                    "Выберите сертификат из списка",
                    parent=dialog,
                )
                return
            fingerprint = picked[0]
            try:
                ok = self.app.certificate_requests.link_certificate(
                    req_id,
                    fingerprint,
                )
                if not ok:
                    messagebox.showerror("Ошибка", "Заявка не найдена", parent=dialog)
                    return
                dialog.destroy()
                self.refresh()
                self.on_message("Сертификат успешно привязан к заявке")
            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

        def on_picker_double_click(event: tk.Event) -> None:
            item = picker.identify_row(event.y)
            if not item:
                return
            picker.selection_set(item)
            picker.focus(item)
            link()

        picker.bind("<Double-1>", on_picker_double_click)
        picker.bind("<Return>", lambda _: link())

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill="x", pady=12, side="bottom")
        ttk.Button(btn_box, text="Отмена", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_box, text="Привязать", command=link, style="Accent.TButton").pack(side="right")

    def mark_processed(self) -> None:
        """Переводит выбранную заявку в статус «Обработана» без удаления из базы данных."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Выбор", "Выберите заявку из списка")
            return

        req_id = int(selection[0])
        if messagebox.askyesno("Подтверждение", "Отметить выбранную заявку как обработанную?"):
            self.app.certificate_requests.update_status(
                req_id, CertificateRequestStatus.PROCESSED
            )
            self.refresh()
            self.on_message("Заявка отмечена как обработанная")

    def delete_selected(self) -> None:
        """Удаляет выбранные заявки из базы данных."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Выбор", "Выберите заявку из списка")
            return

        if messagebox.askyesno(
            "Подтверждение",
            f"Вы действительно хотите удалить {len(selection)} заявки(ок)?",
        ):
            count = 0
            for item in selection:
                req_id = int(item)
                try:
                    if self.app.certificate_requests.delete_request(req_id):
                        count += 1
                except Exception as exc:
                    self.on_message(f"Ошибка удаления: {exc}")
            self.refresh()
            self.on_message(f"Удалено заявок: {count}")
