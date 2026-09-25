"""Desktop view of the shared SQLAlchemy-backed application services."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from pathlib import Path

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.infrastructure.config.config_loader import save_settings
from certificate_analyzer.infrastructure.platform.base import open_path
from certificate_analyzer.presentation.gui.styles import (
    BG_COLOR,
    TEXT_COLOR,
    ACCENT_COLOR,
    UI_FONT,
)
from certificate_analyzer.presentation.gui.widgets.certificate_details import (
    CertificateDetails,
)

STATUS_LABELS = {
    "Все статусы": None,
    "Активные": CertificateStatus.ACTIVE,
    "Истекающие": CertificateStatus.EXPIRING_SOON,
    "Просроченные": CertificateStatus.EXPIRED,
    "Недействительные": CertificateStatus.INVALID,
    "Отозванные": CertificateStatus.REVOKED,
}
COLUMNS = {
    "subject": ("ФИО", 200),
    "original_name": ("Файл", 180),
    "valid_to": ("Действителен до", 120),
    "department": ("Подразделение", 180),
    "status": ("Статус", 140),
    "issuer": ("Издатель", 180),
}


class CertificateAnalyzerApp:
    """Widgets never own database sessions or the authoritative certificate collection."""

    def __init__(self, root, application=None, config_path=None):
        self.root = root
        self.app = application or create_application(config_path)
        self._owns_app = application is None
        self.config_path = config_path
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="certificate-import"
        )
        self.future = None
        self.closing = False
        self.search_after = None
        self.refresh_after = None
        self.offset = 0
        self.sort = "subject"
        self.descending = False
        self.query = CertificateQuery()
        self._page = {}
        self.root.title("Хранилище сертификатов")
        self.root.geometry("1200x760")
        self.root.minsize(860, 540)
        self._build_ui()
        self.refresh()
        self._schedule_refresh()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            ".", font=(UI_FONT, 10), background=BG_COLOR, foreground=TEXT_COLOR
        )
        style.configure(
            "Treeview", rowheight=30, background="white", fieldbackground="white"
        )
        style.configure("Treeview.Heading", font=(UI_FONT, 10, "bold"))
        style.configure(
            "Accent.TButton", background=ACCENT_COLOR, foreground="white", padding=7
        )
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)
        heading = ttk.Frame(frame)
        heading.pack(fill="x", pady=(0, 8))
        ttk.Label(
            heading, text="Хранилище сертификатов", font=(UI_FONT, 17, "bold")
        ).pack(side="left")
        ttk.Button(heading, text="Настройки", command=self.show_settings).pack(
            side="right"
        )
        ttk.Label(
            frame,
            text=f"Файлы: {self.app.certificates.storage.folder}",
            wraplength=1000,
        ).pack(anchor="w")
        ttk.Label(frame, text=f"База: {self.app.database.path}", wraplength=1000).pack(
            anchor="w", pady=(0, 10)
        )
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 10))
        self.import_buttons = []
        for label, action in (
            ("Импорт файлов", self.import_files),
            ("Импорт папки", self.import_folder),
        ):
            button = ttk.Button(
                toolbar, text=label, command=action, style="Accent.TButton"
            )
            button.pack(side="left", padx=(0, 6))
            self.import_buttons.append(button)
        ttk.Button(toolbar, text="Обновить записи", command=self.refresh).pack(
            side="left", padx=3
        )
        ttk.Button(toolbar, text="Отчёт", command=self.export_report).pack(
            side="left", padx=3
        )
        ttk.Button(toolbar, text="Справочник", command=self.import_phonebook).pack(
            side="left", padx=3
        )
        ttk.Button(toolbar, text="МЧД", command=self.open_mchd).pack(
            side="left", padx=3
        )
        ttk.Button(toolbar, text="Удалить записи", command=self.delete_selected).pack(
            side="right"
        )
        self.stats_label = ttk.Label(frame, font=(UI_FONT, 11, "bold"))
        self.stats_label.pack(anchor="w", pady=(0, 12))
        filters = ttk.Frame(frame)
        filters.pack(fill="x", pady=(0, 10))
        ttk.Label(filters, text="Поиск:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._search_changed)
        ttk.Entry(filters, textvariable=self.search_var, width=25).pack(
            side="left", padx=5
        )
        self.status_var = tk.StringVar(value="Все статусы")
        status = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=list(STATUS_LABELS),
            state="readonly",
            width=18,
        )
        status.pack(side="left", padx=5)
        status.bind("<<ComboboxSelected>>", lambda _: self.refresh(reset=True))
        ttk.Label(filters, text="Срок с:").pack(side="left", padx=(8, 2))
        self.date_from_var = tk.StringVar()
        ttk.Entry(filters, textvariable=self.date_from_var, width=11).pack(side="left")
        ttk.Label(filters, text="по:").pack(side="left", padx=2)
        self.date_to_var = tk.StringVar()
        ttk.Entry(filters, textvariable=self.date_to_var, width=11).pack(side="left")
        ttk.Button(
            filters, text="Применить", command=lambda: self.refresh(reset=True)
        ).pack(side="left", padx=5)
        ttk.Button(filters, text="Сбросить", command=self.clear_filters).pack(
            side="left"
        )
        ttk.Label(
            frame,
            text="Даты фильтра: ГГГГ-ММ-ДД. Поиск: ФИО, файл, номер, email, кабинет, подразделение, телефон.",
        ).pack(anchor="w")
        table = ttk.Frame(frame)
        table.pack(fill="both", expand=True, pady=(6, 0))
        self.tree = ttk.Treeview(
            table, columns=list(COLUMNS), show="headings", selectmode="extended"
        )
        for key, (title, width) in COLUMNS.items():
            self.tree.heading(
                key, text=title, command=lambda key=key: self.sort_by(key)
            )
            self.tree.column(key, width=width, minwidth=90)
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("expired", foreground="#a82020")
        self.tree.tag_configure("warning", foreground="#805500")
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        self.tree.bind("<Double-1>", self.open_certificate)
        paging = ttk.Frame(frame)
        paging.pack(fill="x", pady=7)
        self.previous_button = ttk.Button(
            paging, text="Предыдущие", command=lambda: self.change_page(-100)
        )
        self.previous_button.pack(side="left")
        self.next_button = ttk.Button(
            paging, text="Следующие", command=lambda: self.change_page(100)
        )
        self.next_button.pack(side="left", padx=5)
        self.page_label = ttk.Label(paging)
        self.page_label.pack(side="left", padx=10)
        self.details = CertificateDetails(frame)
        self.details.pack(fill="x", pady=5)
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x")
        self.message = ttk.Label(frame, text="Готово")
        self.message.pack(anchor="w")

    def _search_changed(self, *_):
        if self.search_after:
            self.root.after_cancel(self.search_after)
        self.search_after = self.root.after(250, self._apply_search)

    def _apply_search(self):
        self.search_after = None
        self.refresh(reset=True)

    def clear_filters(self):
        self.search_var.set("")
        self.status_var.set("Все статусы")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.refresh(reset=True)

    def refresh(self, reset=False):
        if self.closing:
            return
        if reset:
            self.offset = 0
        try:
            query = CertificateQuery(
                search=self.search_var.get(),
                status=STATUS_LABELS[self.status_var.get()],
                date_from=date.fromisoformat(self.date_from_var.get())
                if self.date_from_var.get()
                else None,
                date_to=date.fromisoformat(self.date_to_var.get())
                if self.date_to_var.get()
                else None,
                sort=self.sort,
                descending=self.descending,
                limit=100,
                offset=self.offset,
            )
            stats = self.app.certificates.statistics(query)
            if self.offset >= stats["total"]:
                self.offset = max(0, (stats["total"] - 1) // 100 * 100)
                query = replace(query, offset=self.offset)
            records = self.app.certificates.list(query)
            self.query = query
            self._page = {c.fingerprint_sha256: c for c in records}
            self.tree.delete(*self.tree.get_children())
            for cert in records:
                row = certificate_to_dict(cert)
                tag = (
                    "expired"
                    if cert.status == CertificateStatus.EXPIRED
                    else "warning"
                    if cert.status == CertificateStatus.EXPIRING_SOON
                    else ""
                )
                self.tree.insert(
                    "",
                    "end",
                    iid=cert.fingerprint_sha256,
                    values=(
                        cert.subject,
                        cert.original_name or Path(cert.source_path).name,
                        row["valid_to"],
                        row["department"],
                        row["status"],
                        cert.issuer,
                    ),
                    tags=(tag,),
                )
            self.stats_label.config(
                text=f"Всего: {stats['total']}    Активные: {stats['ACTIVE']}    Истекающие: {stats['EXPIRING_SOON']}    Просроченные: {stats['EXPIRED']}    Недействительные: {stats['INVALID']}    Отозванные: {stats['REVOKED']}"
            )
            self.page_label.config(
                text=f"{self.offset + 1 if records else 0}–{self.offset + len(records)} из {stats['total']}"
            )
            self.previous_button.config(state="normal" if self.offset else "disabled")
            self.next_button.config(
                state="normal"
                if self.offset + len(records) < stats["total"]
                else "disabled"
            )
            self.details.clear()
        except Exception as exc:
            self.message.config(text=str(exc))

    def sort_by(self, key):
        self.descending = not self.descending if self.sort == key else False
        self.sort = key
        self.refresh(reset=True)

    def change_page(self, delta):
        self.offset = max(0, self.offset + delta)
        self.refresh()

    def _schedule_refresh(self):
        def tick():
            self.refresh()
            if not self.closing:
                self._schedule_refresh()

        self.refresh_after = self.root.after(60000, tick)

    def _submit(self, action, finished):
        if self.future and not self.future.done():
            messagebox.showinfo(
                "Выполняется операция", "Дождитесь завершения текущей операции."
            )
            return
        if self.closing:
            return
        self.progress.start()
        self.message.config(text="Выполняется операция…")
        for button in self.import_buttons:
            button.config(state="disabled")
        self.future = self.executor.submit(action)
        self.root.after(50, lambda: self._poll(finished))

    def _poll(self, finished):
        if not self.future.done():
            self.root.after(50, lambda: self._poll(finished))
            return
        self.progress.stop()
        for button in self.import_buttons:
            button.config(state="normal")
        try:
            result = self.future.result()
            if not self.closing:
                finished(result)
                self.refresh()
        except Exception as exc:
            if not self.closing:
                self.message.config(text="Операция не завершена")
                messagebox.showerror("Ошибка", str(exc))
        finally:
            self.future = None
            if self.closing:
                self._finish_close()

    def _import_finished(self, result):
        self.message.config(
            text=f"Добавлено: {result.imported}; обновлено: {result.updated}; без изменений: {result.skipped}; ошибок: {len(result.errors)}"
        )
        if result.errors:
            messagebox.showwarning(
                "Ошибки импорта",
                "\n".join(f"{p}: {e}" for p, e in result.errors.items()),
            )

    def import_files(self):
        paths = filedialog.askopenfilenames(
            title="Импорт сертификатов",
            filetypes=[
                ("Сертификаты", "*.cer *.crt *.der *.pem"),
                ("Все файлы", "*.*"),
            ],
        )
        if paths:
            self._submit(
                lambda: self.app.certificates.import_files(paths), self._import_finished
            )

    def import_folder(self):
        path = filedialog.askdirectory(title="Импорт сертификатов из папки")
        if path:
            self._submit(
                lambda: self.app.certificates.import_folder(path), self._import_finished
            )

    def import_phonebook(self):
        path = filedialog.askopenfilename(
            title="Справочник", filetypes=[("Справочник", "*.txt *.docx")]
        )
        if path:

            def finished(count):
                self.app.settings.phonebook_path = path
                save_settings(self.app.settings, self.config_path)
                self.message.config(
                    text=f"Справочник: {count} записей; контакты обновлены"
                )

            self._submit(lambda: self.app.certificates.load_phonebook(path), finished)

    def show_details(self, _=None):
        selection = self.tree.selection()
        cert = self._page.get(selection[0]) if selection else None
        if not cert:
            self.details.clear()
            return
        exists = bool(cert.source_path and Path(cert.source_path).is_file())
        self.details.update_details(
            {
                "Subject": cert.subject,
                "Issuer": cert.issuer,
                "Serial": cert.serial_number or "—",
                "SHA-256": cert.fingerprint_sha256,
                "Путь": cert.source_path
                if exists
                else f"Файл отсутствует: {cert.source_path or 'путь не сохранён'}",
                "Email": cert.email or "—",
            }
        )

    def open_certificate(self, _=None):
        selected = self.tree.selection()
        if not selected:
            return
        cert = self.app.certificates.get(selected[0])
        if not cert.source_path or not Path(cert.source_path).is_file():
            messagebox.showwarning(
                "Файл отсутствует",
                "Импортируйте сертификат повторно для восстановления файла в хранилище.",
            )
            return
        try:
            open_path(cert.source_path)
        except OSError as exc:
            messagebox.showerror("Открытие сертификата", str(exc))

    def delete_selected(self):
        keys = list(self.tree.selection())
        if keys and messagebox.askyesno(
            "Удаление записей",
            f"Удалить записей: {len(keys)}? Файлы в хранилище сохранятся.",
        ):
            self._submit(
                lambda: self.app.certificates.delete_records(keys),
                lambda count: self.message.config(text=f"Удалено записей: {count}"),
            )

    def export_report(self):
        path = filedialog.asksaveasfilename(
            title="Отчёт по всем записям текущего фильтра",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("PDF", "*.pdf")],
        )
        if not path:
            return
        query = replace(self.query, limit=None, offset=0)
        self._submit(
            lambda: self.app.reports.export(
                Path(path).suffix.lstrip(".").lower(),
                self.app.certificates.list(query),
                [],
                path,
            ),
            lambda output: self.message.config(text=f"Отчёт сохранён: {output}"),
        )

    def open_mchd(self):
        path = filedialog.askdirectory(title="Папка XML МЧД")
        if not path:
            return

        def finished(records):
            from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict
            from certificate_analyzer.presentation.gui.views.mchd_view import (
                MCHDTableWindow,
            )

            if self.app.mchds.errors:
                messagebox.showwarning(
                    "Ошибки МЧД", "\n".join(self.app.mchds.errors.values())
                )
            MCHDTableWindow(self.root, [mchd_to_dict(m).to_dict() for m in records])
            self.message.config(text=f"МЧД: {len(records)}")

        self._submit(lambda: self.app.mchds.scan(path), finished)

    def show_settings(self):
        window = tk.Toplevel(self.root)
        window.title("Настройки хранилища")
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        fields = {}
        values = {
            "storage_folder": (
                "Папка сертификатов",
                str(self.app.certificates.storage.folder),
            ),
            "database_path": ("Файл SQLite", str(self.app.database.path)),
            "export_folder": ("Папка отчётов", self.app.settings.export_folder),
            "warning_days": (
                "Предупреждать за дней",
                str(self.app.settings.warning_days),
            ),
            "check_interval": (
                "Интервал мониторинга, секунд",
                str(self.app.settings.check_interval),
            ),
        }
        for index, (key, (label, value)) in enumerate(values.items()):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=5)
            fields[key] = tk.StringVar(value=value)
            ttk.Entry(frame, textvariable=fields[key], width=55).grid(
                row=index, column=1, padx=10
            )
        ttk.Label(
            frame,
            text="Настройки вступят в силу после перезапуска. Существующие файлы автоматически не перемещаются.",
            wraplength=600,
        ).grid(row=len(values), column=0, columnspan=2, pady=12)

        def save():
            try:
                settings = replace(
                    self.app.settings,
                    **{
                        k: int(v.get())
                        if k in ("warning_days", "check_interval")
                        else v.get()
                        for k, v in fields.items()
                    },
                )
                save_settings(settings, self.config_path)
                window.destroy()
                self.message.config(
                    text="Настройки сохранены. Перезапустите приложение."
                )
            except (ValueError, OSError) as exc:
                messagebox.showerror("Настройки", str(exc), parent=window)

        ttk.Button(frame, text="Сохранить", command=save).grid(
            row=len(values) + 1, column=1, sticky="e"
        )

    def close(self):
        self.closing = True
        if self.search_after:
            self.root.after_cancel(self.search_after)
            self.search_after = None
        if self.refresh_after:
            self.root.after_cancel(self.refresh_after)
            self.refresh_after = None
        if self.future:
            self.message.config(text="Завершение текущей операции перед закрытием…")
            return
        self._finish_close()

    def _finish_close(self):
        self.executor.shutdown(wait=True)
        if self._owns_app:
            self.app.close()
        self.root.destroy()
