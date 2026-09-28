"""Представление вкладки сертификатов в графическом интерфейсе."""

from dataclasses import replace
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.application.dto.certificate_dto import (
    certificate_to_dict,
)
from certificate_analyzer.application.dto.certificate_query import (
    CertificateQuery,
)
from certificate_analyzer.domain.enums.certificate_status import (
    CertificateStatus,
)
from certificate_analyzer.infrastructure.config.config_loader import (
    save_settings,
)
from certificate_analyzer.presentation.gui.widgets.certificate_details import (
    CertificateDetails,
)

STATUS_LABELS: dict[str, CertificateStatus | None] = {
    "Все статусы": None,
    "Активные": CertificateStatus.ACTIVE,
    "Истекающие": CertificateStatus.EXPIRING_SOON,
    "Просроченные": CertificateStatus.EXPIRED,
    "Недействительные": CertificateStatus.INVALID,
    "Отозванные": CertificateStatus.REVOKED,
}

COLUMNS: dict[str, tuple[str, int]] = {
    "subject": ("ФИО", 200),
    "original_name": ("Файл", 180),
    "valid_to": ("Действителен до", 120),
    "department": ("Подразделение", 180),
    "status": ("Статус", 140),
    "issuer": ("Издатель", 180),
}


class CertificatesView(ttk.Frame):
    """Виджет вкладки учета, просмотра и фильтрации сертификатов X.509."""

    def __init__(
        self,
        parent: tk.Widget,
        application: Any,
        submit_task: Callable[[Callable[[], Any], Callable[[Any], None]], None] | None = None,
        on_message: Callable[[str], None] | None = None,
        on_count_change: Callable[[int], None] | None = None,
        config_path: str | Path | None = None,
        status_var: tk.StringVar | None = None,
        **kwargs: Any,
    ) -> None:
        """Инициализирует представление сертификатов.

        Args:
            parent: Родительский контейнер Tkinter.
            application: Экземпляр контейнера сервисов приложения.
            submit_task: Функция отправки длительных операций в фоновый поток.
            on_message: Функция вывода сообщений в строку состояния.
            on_count_change: Функция обновления общего количества сертификатов.
            config_path: Путь к файлу конфигурации приложения.
            status_var: Внешняя переменная фильтра статуса (если передана, связывается с меню).
            **kwargs: Дополнительные аргументы ttk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.app = application
        self.submit_task = submit_task
        self.on_message = on_message or (lambda _: None)
        self.on_count_change = on_count_change or (lambda _: None)
        self.config_path = config_path

        self.search_after: str | None = None
        self.offset = 0
        self.sort = "subject"
        self.descending = False
        self.query = CertificateQuery()
        self._page: dict[str, Any] = {}

        self.search_var = tk.StringVar()
        self.status_var = status_var if status_var is not None else tk.StringVar(value="Все статусы")
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()

        self.import_buttons: list[ttk.Button] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Создает элементы пользовательского интерфейса вкладки сертификатов.

        Returns:
            None
        """
        # Панель инструментов
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        toolbar.pack(fill="x", pady=(0, 8))

        self.import_buttons.clear()
        for label, action, button_style in (
            ("Добавить сертификат", self.import_files, "Accent.TButton"),
            ("Импорт папки", self.import_folder, "Toolbar.TButton"),
        ):
            button = ttk.Button(
                toolbar, text=label, command=action, style=button_style
            )
            button.pack(side="left", padx=(0, 6))
            self.import_buttons.append(button)

        ttk.Button(
            toolbar,
            text="Обновить",
            command=self.refresh,
            style="Toolbar.TButton",
        ).pack(side="left", padx=3)

        ttk.Button(
            toolbar,
            text="Отчёт",
            command=self.export_report,
            style="Toolbar.TButton",
        ).pack(side="left", padx=3)

        # Метка сводной статистики
        self.stats_label = ttk.Label(self, style="Summary.TLabel")

        # Панель фильтров
        filters = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        filters.pack(fill="x", pady=(0, 8))

        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="Поиск:", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.search_var.trace_add("write", self._search_changed)
        ttk.Entry(filters, textvariable=self.search_var, width=24).grid(
            row=0, column=1, sticky="ew", padx=(6, 12)
        )

        status = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=list(STATUS_LABELS),
            state="readonly",
            width=18,
        )
        status.grid(row=0, column=2, padx=(0, 12))
        status.bind("<<ComboboxSelected>>", lambda _: self.refresh(reset=True))

        ttk.Label(filters, text="Срок с:", style="Panel.TLabel").grid(
            row=0, column=3, sticky="e", padx=(0, 4)
        )
        ttk.Entry(filters, textvariable=self.date_from_var, width=11).grid(
            row=0, column=4
        )

        ttk.Label(filters, text="по:", style="Panel.TLabel").grid(
            row=0, column=5, padx=(6, 4)
        )
        ttk.Entry(filters, textvariable=self.date_to_var, width=11).grid(
            row=0, column=6
        )

        ttk.Button(
            filters,
            text="Применить",
            command=lambda: self.refresh(reset=True),
            style="Toolbar.TButton",
        ).grid(row=0, column=7, padx=(12, 5))

        ttk.Button(
            filters,
            text="Сбросить",
            command=self.clear_filters,
            style="Toolbar.TButton",
        ).grid(row=0, column=8)

        ttk.Label(
            self,
            text="Даты фильтра: ГГГГ-ММ-ДД. Поиск: ФИО, файл, номер, email, кабинет, подразделение, телефон.",
            style="Muted.TLabel",
        ).pack(anchor="w")

        # Основная рабочая область: список слева, свойства справа.
        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.pack(fill="both", expand=True, pady=(6, 0))

        list_panel = ttk.Frame(content)
        properties_panel = ttk.Frame(
            content,
            style="Panel.TFrame",
            padding=(8, 8),
            width=360,
        )
        content.add(list_panel, weight=4)
        content.add(properties_panel, weight=1)
        self.content_pane = content
        self._last_layout_width = 0
        self._pane_layout_after: str | None = None
        self.bind("<Configure>", self._resize_content_pane, add="+")

        table = ttk.Frame(list_panel)
        table.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table, columns=list(COLUMNS), show="headings", selectmode="extended"
        )
        for key, (title, width) in COLUMNS.items():
            self.tree.heading(
                key, text=title, command=lambda key=key: self.sort_by(key)
            )
            self.tree.column(key, width=width, minwidth=90)

        scroll_y = ttk.Scrollbar(table, command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")
        scroll_x = ttk.Scrollbar(
            table,
            orient="horizontal",
            command=self.tree.xview,
        )
        scroll_x.pack(side="bottom", fill="x")
        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("expired", foreground="#a82020")
        self.tree.tag_configure("warning", foreground="#805500")
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        self.tree.bind("<Double-1>", self.open_certificate)

        # Контекстное меню таблицы
        self._tree_menu = tk.Menu(self.winfo_toplevel(), tearoff=0)
        self._tree_menu.add_command(
            label="Открыть файл", command=self.open_certificate
        )
        self._tree_menu.add_command(
            label="Показать в проводнике", command=self.reveal_certificate_file
        )
        self._tree_menu.add_separator()
        self._tree_menu.add_command(
            label="Удалить из учета", command=self.delete_selected
        )
        self._tree_menu.add_command(
            label="Удалить физический файл (в корзину)...",
            command=self.delete_physical_file,
        )

        def _on_tree_context(event: tk.Event) -> None:
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self.show_details()
                self._tree_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", _on_tree_context)

        # Панель пагинации
        paging = ttk.Frame(list_panel, style="Panel.TFrame", padding=(8, 6))
        paging.pack(fill="x", pady=(8, 0))

        self.previous_button = ttk.Button(
            paging,
            text="Предыдущие",
            command=lambda: self.change_page(-100),
            style="Toolbar.TButton",
        )
        self.previous_button.pack(side="left")

        self.next_button = ttk.Button(
            paging,
            text="Следующие",
            command=lambda: self.change_page(100),
            style="Toolbar.TButton",
        )
        self.next_button.pack(side="left", padx=5)

        self.page_label = ttk.Label(paging, style="Panel.TLabel")
        self.page_label.pack(side="left", padx=10)

        # Панель свойств и быстрых действий
        self.details = CertificateDetails(properties_panel)
        self.details.pack(fill="both", expand=True)

        actions = ttk.Frame(properties_panel, style="Panel.TFrame")
        actions.pack(fill="x", pady=(8, 0))
        open_button = ttk.Button(
            actions,
            text="Открыть файл",
            command=self.open_certificate,
            style="Toolbar.TButton",
            state="disabled",
        )
        open_button.pack(fill="x", pady=(0, 5))
        reveal_button = ttk.Button(
            actions,
            text="Показать в проводнике",
            command=self.reveal_certificate_file,
            style="Toolbar.TButton",
            state="disabled",
        )
        reveal_button.pack(fill="x")
        self.detail_action_buttons = (open_button, reveal_button)

    def _resize_content_pane(self, event: tk.Event) -> None:
        """Планирует раскладку после завершения расчёта геометрии Tk."""
        if event.widget is not self:
            return
        if self._last_layout_width and abs(event.width - self._last_layout_width) < 40:
            return
        self._last_layout_width = event.width
        if self._pane_layout_after is not None:
            try:
                self.after_cancel(self._pane_layout_after)
            except tk.TclError:
                pass
        self._pane_layout_after = self.after_idle(self._apply_content_pane_layout)

    def _apply_content_pane_layout(self) -> None:
        """Устанавливает ширину панелей по фактическому размеру Panedwindow."""
        self._pane_layout_after = None
        try:
            width = self.content_pane.winfo_width()
            if width <= 1:
                self._pane_layout_after = self.after(
                    20,
                    self._apply_content_pane_layout,
                )
                return

            details_width = min(390, max(300, int(width * 0.28)))
            min_list_width = min(480, max(1, width // 2))
            min_details_width = min(280, max(180, width // 3))
            max_position = max(1, width - min_details_width)
            position = min(
                max_position,
                max(min_list_width, width - details_width),
            )
            self.content_pane.sashpos(0, position)
        except tk.TclError:
            pass

    def _execute_async(
        self,
        action: Callable[[], Any],
        finished: Callable[[Any], None],
    ) -> None:
        """Передает задачу в TaskRunner или выполняет напрямую при его отсутствии.

        Args:
            action: Функция длительной операции.
            finished: Колбэк завершения операции.

        Returns:
            None
        """
        if self.submit_task:
            self.submit_task(action, finished)
        else:
            result = action()
            finished(result)
            self.refresh()

    def _search_changed(self, *_) -> None:
        """Обрабатывает ввод в поле поиска с задержкой debounce 250 мс.

        Returns:
            None
        """
        if self.search_after:
            self.after_cancel(self.search_after)
        self.search_after = self.after(250, self._apply_search)

    def _apply_search(self) -> None:
        """Применяет поисковую строку с перезагрузкой с первой страницы.

        Returns:
            None
        """
        self.search_after = None
        self.refresh(reset=True)

    def clear_filters(self) -> None:
        """Сбрасывает все поля фильтров и обновляет таблицу.

        Returns:
            None
        """
        self.search_var.set("")
        self.status_var.set("Все статусы")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.refresh(reset=True)

    def refresh(self, reset: bool = False) -> None:
        """Загружает данные из базы в таблицу в соответствии с текущими фильтрами.

        Args:
            reset: Если True, сбрасывает пагинацию на первую страницу.

        Returns:
            None
        """
        if reset:
            self.offset = 0
        try:
            date_from_val = self.date_from_var.get()
            date_to_val = self.date_to_var.get()

            query = CertificateQuery(
                search=self.search_var.get(),
                status=STATUS_LABELS[self.status_var.get()],
                date_from=date.fromisoformat(date_from_val) if date_from_val else None,
                date_to=date.fromisoformat(date_to_val) if date_to_val else None,
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

            summary = (
                f"Всего: {stats['total']}    "
                f"Активные: {stats['ACTIVE']}    "
                f"Истекающие: {stats['EXPIRING_SOON']}    "
                f"Просроченные: {stats['EXPIRED']}    "
                f"Недействительные: {stats['INVALID']}    "
                f"Отозванные: {stats['REVOKED']}"
            )
            self.stats_label.config(text=summary)
            self.on_message(summary)
            self.on_count_change(stats["total"])
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
            self._set_detail_actions_enabled(False)
        except Exception as exc:
            self.on_message(str(exc))

    def sort_by(self, key: str) -> None:
        """Сортирует таблицу сертификатов по выбранной колонке.

        Args:
            key: Имя атрибута или колонки для сортировки.

        Returns:
            None
        """
        self.descending = not self.descending if self.sort == key else False
        self.sort = key
        self.refresh(reset=True)

    def change_page(self, delta: int) -> None:
        """Переключает страницу пагинации на указанное смещение.

        Args:
            delta: Величина смещения (+100 или -100).

        Returns:
            None
        """
        self.offset = max(0, self.offset + delta)
        self.refresh()

    def show_details(self, _=None) -> None:
        """Отображает подробные метаданные выбранного сертификата в нижней панели.

        Args:
            _: Событие Tkinter.

        Returns:
            None
        """
        selection = self.tree.selection()
        cert = self._page.get(selection[0]) if selection else None
        if not cert:
            self.details.clear()
            self._set_detail_actions_enabled(False)
            return
        exists = bool(cert.source_path and Path(cert.source_path).is_file())
        self.details.update_details(
            {
                "Subject": cert.subject,
                "Issuer": cert.issuer,
                "Serial": cert.serial_number or "—",
                "SHA-256": cert.fingerprint_sha256,
                "Путь": (
                    cert.source_path
                    if exists
                    else f"Файл отсутствует: {cert.source_path or 'путь не сохранён'}"
                ),
                "Email": cert.email or "—",
            }
        )
        self._set_detail_actions_enabled(True)

    def _set_detail_actions_enabled(self, enabled: bool) -> None:
        """Включает действия панели свойств только при выбранной записи."""
        state = "normal" if enabled else "disabled"
        for button in getattr(self, "detail_action_buttons", ()):
            button.config(state=state)

    def open_certificate(self, _=None) -> None:
        """Открывает файл выбранного сертификата системной программой по умолчанию.

        Args:
            _: Событие Tkinter.

        Returns:
            None
        """
        selected = self.tree.selection()
        if not selected:
            return
        fingerprint = selected[0]
        try:
            self.app.certificates.open_file(fingerprint)
        except (OSError, FileNotFoundError) as exc:
            messagebox.showerror(
                "Открытие сертификата", str(exc), parent=self.winfo_toplevel()
            )

    def reveal_certificate_file(self, _=None) -> None:
        """Открывает проводник операционной системы с выделением файла сертификата.

        Args:
            _: Событие Tkinter.

        Returns:
            None
        """
        selected = self.tree.selection()
        if not selected:
            return
        fingerprint = selected[0]
        try:
            self.app.certificates.reveal_file(fingerprint)
        except (OSError, FileNotFoundError) as exc:
            messagebox.showerror(
                "Расположение файла", str(exc), parent=self.winfo_toplevel()
            )

    def delete_physical_file(self) -> None:
        """Удаляет файл сертификата в корзину с запросом подтверждения у пользователя.

        Returns:
            None
        """
        selected = self.tree.selection()
        if not selected:
            return
        fingerprint = selected[0]
        cert = self.app.certificates.get(fingerprint)
        if not cert:
            return
        path = cert.source_path or "путь не определён"
        if not messagebox.askyesno(
            "Подтверждение удаления файла",
            f"Вы действительно хотите удалить физический файл сертификата в корзину?\n\n"
            f"Файл: {path}\n"
            f"Владелец: {cert.subject}\n\n"
            f"Файл будет перемещён в корзину, а привязка к файлу будет удалена из базы данных.",
            parent=self.winfo_toplevel(),
            icon="warning",
        ):
            return

        def finished(deleted: bool) -> None:
            if deleted:
                self.on_message(f"Файл перемещён в корзину: {path}")
                self.refresh()
            else:
                messagebox.showwarning(
                    "Удаление файла",
                    f"Файл не найден на диске: {path}",
                    parent=self.winfo_toplevel(),
                )

        self._execute_async(
            lambda: self.app.certificates.delete_file(fingerprint, move_to_trash=True),
            finished,
        )

    def delete_selected(self) -> None:
        """Удаляет выбранные записи сертификатов из учета базы данных без удаления файлов.

        Returns:
            None
        """
        keys = list(self.tree.selection())
        if keys and messagebox.askyesno(
            "Удаление записей из учета",
            f"Удалить выбранных записей из учета: {len(keys)}?\n\n"
            "Внимание: Физические файлы сертификатов сохранятся на диске.",
            parent=self.winfo_toplevel(),
        ):
            self._execute_async(
                lambda: self.app.certificates.delete_records(keys),
                lambda count: (
                    self.on_message(f"Удалено записей из учета: {count}"),
                    self.refresh(),
                ),
            )

    def import_files(self) -> None:
        """Открывает диалог выбора отдельных файлов сертификатов для импорта.

        Returns:
            None
        """
        paths = filedialog.askopenfilenames(
            title="Импорт сертификатов",
            filetypes=[
                ("Сертификаты", "*.cer *.crt *.der *.pem"),
                ("Все файлы", "*.*"),
            ],
        )
        if paths:
            self._execute_async(
                lambda: self.app.certificates.import_files(paths),
                self._import_finished,
            )

    def import_folder(self) -> None:
        """Открывает диалог выбора каталога для рекурсивного импорта сертификатов.

        Returns:
            None
        """
        path = filedialog.askdirectory(title="Импорт сертификатов из папки")
        if path:
            self._execute_async(
                lambda: self.app.certificates.import_folder(path),
                self._import_finished,
            )

    def import_phonebook(self) -> None:
        """Открывает диалог выбора файла телефонного справочника для синхронизации контактов.

        Returns:
            None
        """
        path = filedialog.askopenfilename(
            title="Справочник", filetypes=[("Справочник", "*.txt *.docx")]
        )
        if path:

            def finished(count: int) -> None:
                self.app.settings.phonebook_path = path
                save_settings(self.app.settings, self.config_path)
                self.on_message(
                    f"Справочник: {count} записей; контакты обновлены"
                )

            self._execute_async(
                lambda: self.app.certificates.load_phonebook(path),
                finished,
            )

    def export_report(self) -> None:
        """Экспортирует сертификаты текущего фильтра в файл Excel или PDF.

        Returns:
            None
        """
        path = filedialog.asksaveasfilename(
            title="Отчёт по всем записям текущего фильтра",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("PDF", "*.pdf")],
        )
        if not path:
            return
        query = replace(self.query, limit=None, offset=0)
        self._execute_async(
            lambda: self.app.reports.export(
                Path(path).suffix.lstrip(".").lower(),
                self.app.certificates.list(query),
                [],
                path,
            ),
            lambda output: self.on_message(f"Отчёт сохранён: {output}"),
        )

    def _import_finished(self, result: Any) -> None:
        """Отображает результат выполнения операции импорта сертификатов.

        Args:
            result: Объект ImportResult со статистикой импорта.

        Returns:
            None
        """
        self.on_message(
            f"Добавлено: {result.imported}; обновлено: {result.updated}; без изменений: {result.skipped}; ошибок: {len(result.errors)}"
        )
        if result.errors:
            messagebox.showwarning(
                "Ошибки импорта",
                "\n".join(f"{p}: {e}" for p, e in result.errors.items()),
                parent=self.winfo_toplevel(),
            )
