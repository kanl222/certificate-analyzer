"""Представление вкладки заявок на сертификаты в графическом интерфейсе."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.presentation.gui.styles import (
    TEXT_COLOR,
    UI_FONT,
)

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
        self._build_ui()
        self.refresh()

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
            text="Отметить обработанной",
            command=self.mark_processed,
            style="Toolbar.TButton",
        ).pack(side="right")

        # Панель фильтрации
        filters = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        filters.pack(fill="x", pady=(0, 8))

        ttk.Label(filters, text="Поиск:", style="Panel.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(filters, textvariable=self.search_var, width=25).pack(
            side="left", padx=5
        )

        ttk.Label(filters, text="Статус:", style="Panel.TLabel").pack(
            side="left", padx=(10, 2)
        )
        self.status_var = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=list(REQUEST_STATUS_CHOICES),
            state="readonly",
            width=16,
        )
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        ttk.Button(
            filters,
            text="Сбросить",
            command=self.clear_filters,
            style="Toolbar.TButton",
        ).pack(side="left", padx=5)

        self.stats_label = ttk.Label(self, font=(UI_FONT, 10, "bold"), foreground=TEXT_COLOR)
        self.stats_label.pack(anchor="w", pady=(0, 6))

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

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill="both", expand=True)

        # Подсветка статусов
        self.tree.tag_configure("in_progress", foreground="#0d6efd")
        self.tree.tag_configure("issued", foreground="#198754")
        self.tree.tag_configure("processed", foreground="#6c757d")
        self.tree.tag_configure("rejected", foreground="#dc3545")
        self.tree.tag_configure("received", foreground="#0f5132")

    def clear_filters(self) -> None:
        """Сбрасывает установленные фильтры поиска и статуса."""
        self.search_var.set("")
        self.status_var.set("Все статусы")
        self.refresh()

    def refresh(self) -> None:
        """Перезагружает список заявок из базы данных."""
        if not getattr(self.app, "certificate_requests", None):
            return

        status_enum = REQUEST_STATUS_CHOICES.get(self.status_var.get())
        search_query = self.search_var.get().strip() or None

        self.requests = self.app.certificate_requests.list_requests(
            status=status_enum,
            search=search_query,
        )

        self.tree.delete(*self.tree.get_children())
        counts = {s: 0 for s in CertificateRequestStatus}

        for req in self.requests:
            if req.status in counts:
                counts[req.status] += 1

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

        self.stats_label.config(
            text=f"Всего заявок: {len(self.requests)}   В работе: {counts.get(CertificateRequestStatus.IN_PROGRESS, 0)}   Выпущено: {counts.get(CertificateRequestStatus.ISSUED, 0)}   Обработано: {counts.get(CertificateRequestStatus.PROCESSED, 0)}"
        )
        self.on_message(f"Заявок загружено: {len(self.requests)}")

    def show_create_dialog_for(
        self,
        full_name: str,
        department: str = "",
    ) -> None:
        """Отображает диалог создания заявки с предустановленным сотрудником.

        Args:
            full_name: Полное имя (ФИО) сотрудника.
            department: Подразделение сотрудника.
        """
        self.show_create_dialog(initial_employee=full_name, initial_department=department)

    def show_create_dialog(
        self,
        initial_employee: str = "",
        initial_department: str = "",
    ) -> None:
        """Отображает диалоговое окно создания новой заявки с выбором сотрудника из списка.

        Args:
            initial_employee: Начальное ФИО сотрудника (опционально).
            initial_department: Начальное подразделение (опционально).
        """
        dialog = tk.Toplevel(self)
        dialog.title("Новая заявка на сертификат")
        dialog.geometry("540x360")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

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

        emp_by_name = {
            e.full_name.strip(): e
            for e in employees
            if getattr(e, "full_name", None) and e.full_name.strip()
        }
        emp_names = list(emp_by_name.keys())

        name_var = tk.StringVar(value=initial_employee)
        dept_var = tk.StringVar(value=initial_department)

        # Если передан начальный сотрудник, пробуем автоматически подтянуть его подразделение
        if initial_employee and initial_employee in emp_by_name and not initial_department:
            dept_var.set(emp_by_name[initial_employee].department or "")

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

        def on_combo_selected(_event=None):
            sel_name = name_var.get().strip()
            if sel_name in emp_by_name:
                emp = emp_by_name[sel_name]
                if emp.department:
                    dept_var.set(emp.department)

        emp_combo.bind("<<ComboboxSelected>>", on_combo_selected)

        def open_picker():
            picker = EmployeePickerDialog(dialog, employees=employees)
            picked = picker.show()
            if picked:
                name_var.set(picked.full_name)
                if picked.department:
                    dept_var.set(picked.department)

        if emp_names:
            ttk.Button(
                emp_box,
                text="Выбрать…",
                command=open_picker,
                width=11,
            ).pack(side="left", padx=(6, 0))

        ttk.Label(frame, text="Подразделение:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=dept_var, width=42).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(frame, text="Номер заявки:").grid(row=2, column=0, sticky="w", pady=6)
        number_var = tk.StringVar()
        ttk.Entry(frame, textvariable=number_var, width=42).grid(row=2, column=1, sticky="w", pady=6)
        ttk.Label(frame, text="(оставьте пустым для автогенерации)", font=(UI_FONT, 8)).grid(row=3, column=1, sticky="w")

        ttk.Label(frame, text="Примечание:").grid(row=4, column=0, sticky="w", pady=6)
        comment_var = tk.StringVar()
        ttk.Entry(frame, textvariable=comment_var, width=42).grid(row=4, column=1, sticky="w", pady=6)

        def save():
            name = name_var.get().strip()
            num = number_var.get().strip() or None
            dept = dept_var.get().strip()
            comm = comment_var.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Выберите или укажите ФИО сотрудника", parent=dialog)
                return
            try:
                self.app.certificate_requests.create_request(
                    request_number=num,
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
        selected_status_var = tk.StringVar(value=statuses[0].label)

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
        dialog.geometry("450x180")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="SHA-256 отпечаток сертификата:").pack(anchor="w", pady=(0, 4))
        fp_var = tk.StringVar()
        ttk.Entry(frame, textvariable=fp_var, width=50).pack(fill="x", pady=4)

        def link():
            fp = fp_var.get().strip().upper()
            if not fp:
                messagebox.showwarning("Внимание", "Введите SHA-256 отпечаток", parent=dialog)
                return
            try:
                ok = self.app.certificate_requests.link_certificate(req_id, fp)
                if not ok:
                    messagebox.showerror("Ошибка", "Заявка не найдена", parent=dialog)
                    return
                dialog.destroy()
                self.refresh()
                self.on_message("Сертификат успешно привязан к заявке")
            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

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
        """Обрабатывает выбранную заявку (переводит в статус «Обработана» вместо удаления)."""
        self.mark_processed()
