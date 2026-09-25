"""Представление вкладки заявок на сертификаты в графическом интерфейсе."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

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
    "needs_signature": ("Подпись", 80),
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
    "Отклонена": CertificateRequestStatus.REJECTED,
    "Аннулирована": CertificateRequestStatus.CANCELLED,
}


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
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(
            toolbar,
            text="Создать заявку…",
            command=self.show_create_dialog,
            style="Accent.TButton",
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            toolbar, text="Сменить статус…", command=self.show_status_dialog
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar, text="Привязать сертификат…", command=self.show_link_dialog
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar, text="Обновить заявки", command=self.refresh
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar, text="Удалить заявку", command=self.delete_selected
        ).pack(side="right")

        # Панель фильтрации
        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 8))

        ttk.Label(filters, text="Поиск:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(filters, textvariable=self.search_var, width=25).pack(
            side="left", padx=5
        )

        ttk.Label(filters, text="Статус:").pack(side="left", padx=(10, 2))
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

        ttk.Button(filters, text="Сбросить", command=self.clear_filters).pack(
            side="left", padx=5
        )

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
                    "Да" if req.needs_signature else "Нет",
                    req.status.label,
                    sub_date,
                    iss_date,
                    cert_str,
                    req.comment,
                ),
                tags=(tag,) if tag else (),
            )

        self.stats_label.config(
            text=f"Всего заявок: {len(self.requests)}   В работе: {counts[CertificateRequestStatus.IN_PROGRESS]}   Выпущено: {counts[CertificateRequestStatus.ISSUED]}   Получено: {counts[CertificateRequestStatus.RECEIVED]}"
        )
        self.on_message(f"Заявок загружено: {len(self.requests)}")

    def show_create_dialog(self) -> None:
        """Отображает диалоговое окно создания новой заявки."""
        dialog = tk.Toplevel(self)
        dialog.title("Новая заявка на сертификат")
        dialog.geometry("450x320")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="ФИО сотрудника:").grid(row=0, column=0, sticky="w", pady=4)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=32).grid(row=0, column=1, pady=4)

        ttk.Label(frame, text="Подразделение:").grid(row=1, column=0, sticky="w", pady=4)
        dept_var = tk.StringVar()
        ttk.Entry(frame, textvariable=dept_var, width=32).grid(row=1, column=1, pady=4)

        ttk.Label(frame, text="Номер заявки:").grid(row=2, column=0, sticky="w", pady=4)
        number_var = tk.StringVar()
        ttk.Entry(frame, textvariable=number_var, width=32).grid(row=2, column=1, pady=4)
        ttk.Label(frame, text="(оставьте пустым для авто)", font=(UI_FONT, 8)).grid(row=3, column=1, sticky="w")

        needs_sig_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Требуется электронная подпись", variable=needs_sig_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=6
        )

        ttk.Label(frame, text="Примечание:").grid(row=5, column=0, sticky="w", pady=4)
        comment_var = tk.StringVar()
        ttk.Entry(frame, textvariable=comment_var, width=32).grid(row=5, column=1, pady=4)

        def save():
            name = name_var.get().strip()
            num = number_var.get().strip() or None
            dept = dept_var.get().strip()
            comm = comment_var.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Укажите ФИО сотрудника", parent=dialog)
                return
            try:
                self.app.certificate_requests.create_request(
                    request_number=num,
                    full_name=name,
                    department=dept,
                    needs_signature=needs_sig_var.get(),
                    comment=comm,
                )
                dialog.destroy()
                self.refresh()
                self.on_message(f"Создана заявка для: {name}")
            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc), parent=dialog)

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=6, column=0, columnspan=2, pady=16, sticky="e")
        ttk.Button(btn_box, text="Отмена", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_box, text="Создать", command=save, style="Accent.TButton").pack(side="right")

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

    def delete_selected(self) -> None:
        """Удаляет выбранную заявку после подтверждения."""
        selection = self.tree.selection()
        if not selection:
            return

        req_id = int(selection[0])
        if messagebox.askyesno("Подтверждение", "Удалить выбранную заявку?"):
            self.app.certificate_requests.delete_request(req_id)
            self.refresh()
            self.on_message("Заявка удалена")
