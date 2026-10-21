"""Представление вкладки машиночитаемых доверенностей (МЧД) и диалоговые окна."""

from datetime import timezone, datetime
from hashlib import sha256
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import pyperclip

from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict
from certificate_analyzer.infrastructure.config.config_loader import (
    load_settings,
)
from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger
from certificate_analyzer.infrastructure.platform.base import open_path
from certificate_analyzer.presentation.gui.views.dialogs.authorities_view import AuthoritiesViewWindow  # noqa: F401
from certificate_analyzer.presentation.gui.views.dialogs.mchd_personal_data import MchdPersonalDataWindow  # noqa: F401
from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    MCHD_LIGHT_COLOR,
    UI_FONT,
    WARNING_COLOR,
    WARNING_TEXT,
)
from certificate_analyzer.presentation.gui.widgets.table_state import (
    EmptyStateLabel,
    TableState,
    sort_heading_text,
)
from certificate_analyzer.presentation.gui.widgets.responsive_bar import ResponsiveBar
from certificate_analyzer.presentation.gui.widgets.scrollable_panel import ScrollablePanel


UTC = timezone.utc

class MchdView(ttk.Frame):
    """Представление вкладки учета и анализа машиночитаемых доверенностей (МЧД)."""

    COLUMNS = (
        "file_name",
        "doc_number",
        "issue_date",
        "expiry_date",
        "full_name",
        "principal_name",
        "authority_codes",
        "status",
    )

    COLUMN_HEADINGS = {
        "file_name": ("Файл", 150),
        "doc_number": ("Номер доверенности", 160),
        "issue_date": ("Дата выдачи", 95),
        "expiry_date": ("Срок действия", 95),
        "full_name": ("ФИО представителя", 190),
        "principal_name": ("Организация-доверитель", 190),
        "authority_codes": ("Полномочия", 220),
        "status": ("Статус срока", 110),
    }

    def __init__(
        self,
        parent: tk.Widget,
        application: Any = None,
        on_message: Callable[[str], None] | None = None,
        on_count_change: Callable[[int], None] | None = None,
        mchd_data: list[dict[str, Any]] | None = None,
        submit_task: Callable | None = None,
        **kwargs,
    ) -> None:
        """Инициализирует представление вкладки МЧД.

        Args:
            parent: Родительский виджет Tkinter.
            application: Контейнер сервисов приложения ApplicationContainer.
            on_message: Функция вывода сообщений в статусную строку.
            on_count_change: Функция обновления общего количества МЧД.
            mchd_data: Список заранее распарсенных данных МЧД (опционально).
            **kwargs: Дополнительные параметры ttk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.app = application
        self.submit_task = submit_task
        self._task_runner = None
        if submit_task is None:
            from certificate_analyzer.presentation.gui.task_runner import TaskRunner
            self._task_runner = TaskRunner(self, on_message=on_message)
            self.submit_task = self._task_runner.submit
            self.bind("<Destroy>", self._shutdown_tasks, add="+")
        self.on_message = on_message or (lambda _: None)
        self.on_count_change = on_count_change or (lambda _: None)
        self.mchd_data: list[dict[str, Any]] = (
            list(mchd_data) if mchd_data is not None else []
        )
        self.filtered_data: list[dict[str, Any]] = list(self.mchd_data)
        self.selected_items: tuple[str, ...] = ()
        self.sort_reverse: dict[str, bool] = {}
        self.sort_column_key: str | None = None
        self.sort_descending = False
        self._row_to_mchd: dict[str, dict[str, Any]] = {}

        self._build_ui()
        if self.app is not None and mchd_data is None:
            self.refresh()
        elif self.mchd_data:
            self.apply_filters()
            self.check_for_duplicates()

    def _build_ui(self) -> None:
        """Создает элементы управления, панель фильтров, таблицу и блок деталей."""
        # 1. Верхняя панель действий (Toolbar)
        toolbar = ResponsiveBar(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        toolbar.add(ttk.Button(
            toolbar,
            text="Сканировать папку…",
            command=self.scan_folder,
            style="Accent.TButton",
        ))

        toolbar.add(ttk.Button(
            toolbar,
            text="Импортировать XML…",
            command=self.import_files,
            style="Toolbar.TButton",
        ))
        toolbar.add(ttk.Button(
            toolbar,
            text="Экспорт в Excel",
            command=self.export_to_excel,
            style="Toolbar.TButton",
        ))

        toolbar.add(ttk.Button(
            toolbar,
            text="Обновить",
            command=self.refresh,
            style="Toolbar.TButton",
        ))

        # 2. Панель поиска и фильтрации
        filter_bar = ResponsiveBar(self)
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        search_group = ttk.Frame(filter_bar, style="Status.TFrame")
        ttk.Label(search_group, text="Поиск:", style="Panel.TLabel").pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filters())
        search_entry = ttk.Entry(search_group, textvariable=self.search_var, width=28)
        search_entry.pack(side="left", fill="x", expand=True)
        filter_bar.add(search_group, stretch=True)

        status_group = ttk.Frame(filter_bar, style="Status.TFrame")
        ttk.Label(status_group, text="Статус срока:", style="Panel.TLabel").pack(side="left", padx=(0, 6))
        self.status_var = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(
            status_group,
            textvariable=self.status_var,
            values=[
                "Все статусы",
                "Действует",
                "Истекает",
                "Просрочен",
                "Отозвана",
            ],
            state="readonly",
            width=14,
        )
        status_combo.pack(side="left")
        filter_bar.add(status_group)
        status_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        filter_bar.add(ttk.Button(
            filter_bar,
            text="Сбросить",
            command=self.clear_search,
            width=10,
            style="Toolbar.TButton",
        ))

        self.stats_label = ttk.Label(
            filter_bar,
            text="",
            font=(UI_FONT, 9, "bold"),
            foreground=ACCENT_COLOR,
            style="Panel.TLabel",
        )

        # 3. Баннер предупреждения о дубликатах доверенностей
        self.duplicate_frame = ttk.Frame(self)
        self.duplicate_frame.pack(fill=tk.X, pady=(0, 6))

        # 4. Рабочая область: список слева, свойства выбранной МЧД справа.
        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(content)
        details_frame = ttk.LabelFrame(
            content,
            text=" Свойства МЧД ",
            padding=10,
            style="Panel.TLabelframe",
            width=380,
        )
        content.add(table_frame, weight=4)
        content.add(details_frame, weight=1)
        self.content_pane = content
        self._last_layout_width = 0
        self._pane_layout_after: str | None = None
        self.bind("<Configure>", self._resize_content_pane, add="+")

        self.tree = ttk.Treeview(
            table_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode=tk.EXTENDED,
        )

        for col_id in self.COLUMNS:
            title, width = self.COLUMN_HEADINGS[col_id]
            self.tree.heading(
                col_id,
                text=title,
                command=lambda c=col_id: self.sort_column(c),
            )
            self.tree.column(col_id, width=width, minwidth=60, anchor=tk.W)
            self.sort_reverse[col_id] = False

        scroll_y = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x = ttk.Scrollbar(
            table_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(
            yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.empty_label = EmptyStateLabel(
            table_frame,
            "Доверенностей пока нет\nИмпортируйте XML или просканируйте папку",
        )
        self.empty_label.show()

        self.tree.tag_configure(
            "expired", background=EXPIRED_COLOR, foreground=EXPIRED_TEXT
        )
        self.tree.tag_configure(
            "warning", background=WARNING_COLOR, foreground=WARNING_TEXT
        )
        self.tree.tag_configure("normal", background=MCHD_LIGHT_COLOR)
        self.tree.tag_configure("duplicate_name", background="#fff3cd")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Контекстное меню таблицы
        self._tree_menu = tk.Menu(self, tearoff=0)
        self._tree_menu.add_command(
            label="Карточка МЧД...", command=self.view_personal_data
        )
        self._tree_menu.add_command(
            label="Просмотр кодов полномочий...",
            command=self.view_merged_authorities,
        )
        self._tree_menu.add_command(
            label="Открыть XML файл", command=self.open_xml_file
        )
        self._tree_menu.add_command(
            label="Показать в проводнике", command=self.reveal_file
        )
        self._tree_menu.add_separator()
        self._tree_menu.add_command(
            label="Объединить выбранные МЧД...", command=self.merge_selected
        )
        self._tree_menu.add_separator()
        self._tree_menu.add_command(
            label="Удалить из учета", command=self.delete_selected
        )

        def _on_context(event: tk.Event) -> None:
            item = self.tree.identify_row(event.y)
            if item:
                if item not in self.tree.selection():
                    self.tree.selection_set(item)
                self.on_select()
                self._tree_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", _on_context)

        # 5. Свойства, полномочия и действия выбранной МЧД
        actions_parent = details_frame
        self.details_scroll = ScrollablePanel(details_frame)
        self.details_scroll.pack(fill=tk.BOTH, expand=True)
        details_frame = self.details_scroll.body
        self.selected_info_label = ttk.Label(
            details_frame,
            text="Выбрано: 0 МЧД",
            font=(UI_FONT, 9, "bold"),
            style="Panel.TLabel",
        )
        self.selected_info_label.pack(fill=tk.X, pady=(0, 6))

        self.person_info_label = ttk.Label(
            details_frame,
            text="",
            font=(UI_FONT, 9),
            style="Panel.TLabel",
            wraplength=320,
            justify=tk.LEFT,
        )

        self.mchd_detail_fields: dict[str, ttk.Label] = {}
        property_labels = (
            ("doc_number", "Номер"),
            ("status", "Статус срока"),
            ("full_name", "Представитель"),
            ("issuer_org_name", "Доверитель"),
            ("issue_date", "Дата выдачи"),
            ("expiry_date", "Действует до"),
        )
        properties = ttk.Frame(details_frame, style="Status.TFrame")
        properties.pack(fill=tk.X)
        properties.columnconfigure(0, weight=1)
        self._detail_titles = dict(property_labels)
        self._detail_rows = {}
        self._selected_detail = None
        ttk.Style(self).configure("Selected.Card.TLabel", background="#DCEAFF", foreground="#183153")
        self._detail_copy_menu = tk.Menu(self, tearoff=0)
        self._detail_copy_menu.add_command(label="Копировать значение")
        self._detail_copy_menu.add_command(label="Копировать строку")
        self._detail_copy_menu.add_separator()
        self._detail_copy_menu.add_command(label="Копировать карточку", command=self._copy_detail_card)
        for row, (key, title) in enumerate(property_labels):
            title_widget = ttk.Label(
                properties,
                text=f"{title}:",
                font=(UI_FONT, 9, "bold"),
                style="Panel.TLabel",
            )
            title_widget.grid(row=row * 2, column=0, sticky="w", pady=(8, 2))
            value = ttk.Label(
                properties,
                text="—",
                style="Panel.TLabel",
                wraplength=230,
                justify=tk.LEFT,
            )
            value.grid(row=row * 2 + 1, column=0, sticky="ew")
            self.mchd_detail_fields[key] = value
            self._detail_rows[key] = (title_widget, value)
            for widget in (title_widget, value):
                widget.bind("<Button-1>", lambda event, key=key: self._select_detail(key))
                widget.bind("<Button-3>", lambda event, key=key: self._show_detail_copy_menu(event, key))
            value.bind("<Double-Button-1>", lambda event, key=key: self._copy_detail(key))

        ttk.Separator(details_frame).pack(fill=tk.X, pady=10)
        ttk.Label(
            details_frame,
            text="Полномочия",
            font=(UI_FONT, 9, "bold"),
            style="Panel.TLabel",
        ).pack(anchor=tk.W, pady=(0, 5))

        listbox_box = ttk.Frame(details_frame, style="Status.TFrame")
        listbox_box.pack(fill=tk.BOTH, expand=True)

        self.codes_listbox = tk.Listbox(
            listbox_box,
            height=8,
            selectmode=tk.SINGLE,
            font=("Courier New", 9),
        )
        self.codes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_c = ttk.Scrollbar(
            listbox_box, orient=tk.VERTICAL, command=self.codes_listbox.yview
        )
        scroll_c.pack(side=tk.RIGHT, fill=tk.Y)
        self.codes_listbox.configure(yscrollcommand=scroll_c.set)

        actions = ttk.Frame(actions_parent, style="Status.TFrame")
        actions.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0), before=self.details_scroll)
        self.detail_action_buttons: list[ttk.Button | ttk.Menubutton] = []
        for label, command in (
            ("Открыть карточку", self.view_personal_data),
            ("Открыть XML", self.open_xml_file),
        ):
            if self.detail_action_buttons:
                row = ttk.Frame(actions, style="Status.TFrame")
                row.pack(fill=tk.X)
            else:
                row = actions
            button = ttk.Button(
                row,
                text=label,
                command=command,
                style="Toolbar.TButton",
                state="disabled",
            )
            if row is actions:
                button.pack(fill=tk.X, pady=(0, 5))
            else:
                button.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.detail_action_buttons.append(button)
        more = ttk.Menubutton(row, text="Ещё…", state="disabled")
        more.pack(side=tk.RIGHT, padx=(6, 0))
        more_menu = tk.Menu(more, tearoff=0)
        more_menu.add_command(label="Показать в проводнике", command=self.reveal_file)
        more_menu.add_command(label="Копировать коды", command=self.copy_selected_codes)
        more.configure(menu=more_menu)
        self.detail_action_buttons.append(more)
        details_frame.bind("<Configure>", self._resize_detail_values, add="+")
        self.details_scroll.bind_mousewheel()

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

            details_width = min(410, max(320, int(width * 0.3)))
            min_list_width = min(520, max(1, width // 2))
            min_details_width = min(300, max(190, width // 3))
            max_position = max(1, width - min_details_width)
            position = min(
                max_position,
                max(min_list_width, width - details_width),
            )
            self.content_pane.sashpos(0, position)
        except tk.TclError:
            pass

    def _resize_detail_values(self, event: tk.Event) -> None:
        """Подстраивает перенос значений в карточке МЧД под её ширину."""
        wraplength = max(60, event.width - 8)
        self.person_info_label.config(wraplength=max(180, event.width - 24))
        for label in self.mchd_detail_fields.values():
            label.config(wraplength=wraplength)

    def _select_detail(self, key):
        if self._selected_detail is not None:
            for widget in self._detail_rows[self._selected_detail]:
                widget.configure(style="Panel.TLabel")
        self._selected_detail = key
        for widget in self._detail_rows[key]:
            widget.configure(style="Selected.Card.TLabel")

    def _copy_detail(self, key, include_label=False):
        text = str(self.mchd_detail_fields[key].cget("text"))
        self.clipboard_clear()
        self.clipboard_append(f"{self._detail_titles[key]}: {text}" if include_label else text)

    def _copy_detail_card(self):
        self.clipboard_clear()
        self.clipboard_append("\n".join(f"{self._detail_titles[key]}: {widget.cget('text')}" for key, widget in self.mchd_detail_fields.items()))

    def _show_detail_copy_menu(self, event, key):
        self._select_detail(key)
        self._detail_copy_menu.entryconfigure(0, command=lambda: self._copy_detail(key))
        self._detail_copy_menu.entryconfigure(1, command=lambda: self._copy_detail(key, True))
        try:
            self._detail_copy_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._detail_copy_menu.grab_release()

    def refresh(self) -> None:
        """Перечитывает данные МЧД из базы данных и обновляет таблицу."""
        if hasattr(self.app, "mchds") and self.app.mchds:
            try:
                docs = self.app.mchds.list_all()
                self.mchd_data = [mchd_to_dict(doc).to_dict() for doc in docs]
            except Exception as exc:
                self.on_message(f"Ошибка загрузки МЧД: {exc}")

        self.apply_filters()
        self.check_for_duplicates()
        self.on_count_change(len(self.mchd_data))

    def apply_filters(self, *args) -> None:
        """Применяет текстовый поиск и фильтрацию по статусу к списку МЧД."""
        query = self.search_var.get().strip().casefold()
        status_filter = self.status_var.get()

        self.filtered_data = []
        for mchd in self.mchd_data:
            st = mchd.get("status", "")
            if status_filter != "Все статусы":
                if status_filter == "Истекает" and "Истекает" not in st:
                    continue
                elif status_filter != "Истекает" and status_filter not in st:
                    continue

            if query:
                full_name = str(mchd.get("full_name", "")).casefold()
                doc_num = str(mchd.get("doc_number", "")).casefold()
                org = str(
                    mchd.get(
                        "issuer_org_name", mchd.get("principal_name", "")
                    )
                ).casefold()
                inn = str(mchd.get("inn", "")).casefold()
                if (
                    query not in full_name
                    and query not in doc_num
                    and query not in org
                    and query not in inn
                ):
                    continue

            self.filtered_data.append(mchd)

        self.refresh_table()
        self.update_stats()

    def clear_search(self) -> None:
        """Сбрасывает поисковую строку и фильтр статуса."""
        self.search_var.set("")
        self.status_var.set("Все статусы")
        self.apply_filters()

    def update_stats(self) -> None:
        """Обновляет сводную статистику по статусам доверенностей."""
        expired = sum(
            1 for m in self.mchd_data if m.get("status") == "Просрочен"
        )
        warning = sum(
            1
            for m in self.mchd_data
            if m.get("status") and "Истекает" in m.get("status", "")
        )
        valid = sum(
            1 for m in self.mchd_data if m.get("status") == "Действует"
        )
        summary = (
            f"Всего: {len(self.mchd_data)}    "
            f"Действуют: {valid}    "  
            f"Истекают: {warning}    " 
            f"Просрочены: {expired}    "
        )
        self.stats_label.config(text=summary)
        self.on_message(summary)

    @staticmethod
    def _get_status_tag(status_text: str) -> str:
        """Определяет тег стиля по текстовому статусу доверенности.

        Args:
            status_text: Текстовое описание статуса доверенности.

        Returns:
            str: Название тега для строки Treeview ('expired', 'warning' или 'normal').
        """
        if status_text in ("Просрочен", "Отозвана"):
            return "expired"
        if "Истекает" in status_text:
            return "warning"
        return "normal"

    def refresh_table(self) -> None:
        """Очищает и заново заполняет таблицу отфильтрованными данными."""
        table_state = TableState.capture(self.tree)
        if self.sort_column_key:
            column = self.sort_column_key
            self.filtered_data.sort(
                key=lambda record: MchdView._record_sort_value(record, column),
                reverse=self.sort_descending,
            )
        for item in self.tree.get_children():
            self.tree.delete(item)

        persons: dict[str, list[dict[str, Any]]] = {}
        for mchd in self.mchd_data:
            person = mchd.get("full_name", "Неизвестно")
            if person not in persons:
                persons[person] = []
            persons[person].append(mchd)

        duplicate_names = {
            p for p, m in persons.items() if len(m) > 1 and p != "Не найдено"
        }

        self._row_to_mchd.clear()
        occurrences = {}
        for mchd in self.filtered_data:
            status_text = mchd.get("status", "")
            tags = [self._get_status_tag(status_text)]

            person = mchd.get("full_name", "")
            if person in duplicate_names:
                tags.append("duplicate_name")

            auth_codes = ", ".join(mchd.get("authority_codes", []))
            if len(auth_codes) > 45:
                auth_codes = auth_codes[:45] + "…"
            if not mchd.get("authority_codes"):
                auth_codes = "Нет кодов"

            org = mchd.get("issuer_org_name", mchd.get("principal_name", ""))
            if org == "Не найдено":
                org = ""

            doc_number = mchd.get("doc_number", "")
            # Путь и реквизиты сохраняются при повторном чтении DTO из базы.
            identity = (mchd.get("file_name", ""), mchd.get("xml_path", ""), doc_number,
                        mchd.get("full_name", ""), mchd.get("inn", ""))
            occurrence = occurrences.get(identity, 0)
            occurrences[identity] = occurrence + 1
            iid = "mchd_" + sha256(repr((identity, occurrence)).encode("utf-8")).hexdigest()
            self._row_to_mchd[iid] = mchd

            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    os.path.basename(mchd.get("file_name", "")),
                    doc_number,
                    mchd.get("issue_date", ""),
                    mchd.get("expiry_date", ""),
                    person,
                    org,
                    auth_codes,
                    status_text,
                ),
                tags=tuple(tags),
            )

        if self.filtered_data:
            self.empty_label.hide()
        elif self.search_var.get().strip() or self.status_var.get() != "Все статусы":
            self.empty_label.show(
                "По заданным условиям ничего не найдено\nИзмените или сбросьте фильтры"
            )
        else:
            self.empty_label.show(
                "Доверенностей пока нет\nИмпортируйте XML или просканируйте папку"
            )

        table_state.restore(self.tree)
        self.on_select()

    def check_for_duplicates(self) -> None:
        """Проверяет наличие нескольких действующих МЧД у одного человека."""
        for widget in self.duplicate_frame.winfo_children():
            widget.destroy()

        persons: dict[str, list[dict[str, Any]]] = {}
        for mchd in self.mchd_data:
            p = mchd.get("full_name", "")
            if p and p != "Не найдено":
                if p not in persons:
                    persons[p] = []
                persons[p].append(mchd)

        duplicates = {p: m for p, m in persons.items() if len(m) > 1}
        if duplicates:
            banner = ttk.Frame(self.duplicate_frame, padding=6)
            banner.pack(fill=tk.X)

            msg = f"Внимание: обнаружены дубликаты МЧД ({len(duplicates)} чел. имеют несколько доверенностей)."
            ttk.Label(
                banner,
                text=msg,
                font=(UI_FONT, 9, "bold"),
                foreground="#b26a00",
            ).pack(side=tk.LEFT)

            def filter_dup():
                self.filtered_data = [
                    m
                    for m in self.mchd_data
                    if m.get("full_name") in duplicates
                ]
                self.refresh_table()

            ttk.Button(
                banner,
                text="Показать только дубликаты",
                command=filter_dup,
                width=24,
            ).pack(side=tk.RIGHT, padx=5)

    @staticmethod
    def _sort_value(value, column):
        if column in ("issue_date", "expiry_date"):
            try:
                return datetime.strptime(str(value), "%d.%m.%Y")
            except ValueError:
                return datetime.min
        return str(value or "").casefold()

    @staticmethod
    def _record_sort_value(record, column):
        value = record.get(column, "")
        if column == "file_name":
            value = os.path.basename(value)
        elif column == "authority_codes":
            value = ", ".join(value or [])
        return MchdView._sort_value(value, column)

    def sort_column(self, col: str) -> None:
        """Сортирует таблицу по значениям выбранного столбца.

        Args:
            col: Идентификатор столбца.
        """
        descending = self.sort_reverse[col]
        data = [
            (self.tree.set(child, col), child)
            for child in self.tree.get_children("")
        ]
        data.sort(key=lambda item: MchdView._sort_value(item[0], col), reverse=descending)

        for index, (_, child) in enumerate(data):
            self.tree.move(child, "", index)

        self.sort_column_key = col
        self.sort_descending = descending
        for column in self.COLUMNS:
            title, _width = self.COLUMN_HEADINGS[column]
            self.tree.heading(
                column,
                text=sort_heading_text(
                    title,
                    column == self.sort_column_key,
                    self.sort_descending,
                ),
            )
        self.sort_reverse[col] = not descending

    def on_select(self, _event=None) -> None:
        """Обновляет состояние панели деталей при изменении выделения строк."""
        self.selected_items = self.tree.selection()
        count = len(self.selected_items)
        self.selected_info_label.config(text=f"Выбрано: {count} МЧД")

        selected_mchd = self.get_selected_mchd_objects()
        if count > 1:
            self.person_info_label.pack(
                fill=tk.X, pady=(0, 8), after=self.selected_info_label
            )
            persons = {m.get("full_name", "") for m in selected_mchd}
            if len(persons) == 1:
                self.person_info_label.config(
                    text=f"Представитель: {next(iter(persons))}"
                )
            else:
                self.person_info_label.config(
                    text=f"Выбрано представителей: {len(persons)}"
                )
        else:
            self.person_info_label.config(text="")
            self.person_info_label.pack_forget()

        self._update_property_panel(selected_mchd)
        self.update_codes_list()

    def _update_property_panel(
        self,
        selected_mchd: list[dict[str, Any]],
    ) -> None:
        """Заполняет правую панель свойствами одной выбранной доверенности."""
        record = selected_mchd[0] if len(selected_mchd) == 1 else None
        for key, label in self.mchd_detail_fields.items():
            if record is None:
                label.config(text="—")
                continue
            value = record.get(key)
            if key == "issuer_org_name" and not value:
                value = record.get("principal_name")
            label.config(text=str(value or "—"))

        state = "normal" if selected_mchd else "disabled"
        for button in self.detail_action_buttons:
            button.config(state=state)

    def update_codes_list(self) -> None:
        """Обновляет содержимое списка кодов полномочий для выделенных строк."""
        self.codes_listbox.delete(0, tk.END)
        if not self.selected_items:
            self.codes_listbox.insert(0, "Выберите МЧД в таблице")
            return

        selected_mchd = self.get_selected_mchd_objects()
        all_codes: set[str] = set()
        for mchd in selected_mchd:
            all_codes.update(mchd.get("authority_codes", []))

        if all_codes:
            for code in sorted(all_codes):
                self.codes_listbox.insert(tk.END, f"• {code}")
            self.codes_listbox.insert(tk.END, "")
            self.codes_listbox.insert(
                tk.END, f"ВСЕГО УНИКАЛЬНЫХ КОДОВ: {len(all_codes)}"
            )
        else:
            self.codes_listbox.insert(0, "Нет кодов полномочий")

    def get_selected_mchd_objects(self) -> list[dict[str, Any]]:
        """Возвращает список словарей МЧД для выделенных строк в таблице.

        Returns:
            list[dict[str, Any]]: Список выбранных объектов доверенностей.
        """
        selected: list[dict[str, Any]] = []
        for iid in self.selected_items:
            if iid in self._row_to_mchd:
                selected.append(self._row_to_mchd[iid])
            else:
                for m in self.mchd_data:
                    if m.get("doc_number") == iid or str(id(m)) == iid:
                        selected.append(m)
                        break
        return selected

    def _shutdown_tasks(self, event) -> None:
        if event.widget is self and self._task_runner:
            self._task_runner.closing = True
            self._task_runner.shutdown(wait=False)

    def _import_finished(self, result) -> None:
        records, errors, label = result
        if errors:
            text = "\n".join(f"{Path(path).name}: {error}" for path, error in list(errors.items())[:5])
            messagebox.showwarning("Ошибки при анализе МЧД", text, parent=self.winfo_toplevel())
        self.refresh()
        self.on_message(f"{label}: {len(records)}")

    def _run_import(self, action, label) -> None:
        def work():
            records = action()
            return records, dict(self.app.mchds.errors), label
        self.submit_task(work, self._import_finished)

    def scan_folder(self) -> None:
        """Запрашивает каталог и сканирует все XML-файлы доверенностей с сохранением в БД."""
        path = filedialog.askdirectory(
            title="Выберите папку с файлами XML МЧД",
            parent=self.winfo_toplevel(),
        )
        if not path:
            return

        if hasattr(self.app, "mchds") and self.app.mchds:
            try:
                self._run_import(lambda: self.app.mchds.scan(path, save_to_db=True), "Отсканировано и сохранено МЧД")
            except Exception as exc:
                messagebox.showerror(
                    "Ошибка сканирования",
                    str(exc),
                    parent=self.winfo_toplevel(),
                )
        else:
            messagebox.showinfo(
                "Информация", "Сервис МЧД недоступен", parent=self.winfo_toplevel()
            )

    def import_files(self) -> None:
        """Импортирует выбранные пользователем XML-файлы МЧД в базу данных."""
        paths = filedialog.askopenfilenames(
            title="Выберите XML-файлы МЧД",
            filetypes=[("XML файлы", "*.xml"), ("Все файлы", "*.*")],
            parent=self.winfo_toplevel(),
        )
        if not paths:
            return

        if hasattr(self.app, "mchds") and self.app.mchds:
            try:
                self._run_import(lambda: self.app.mchds.import_files(paths, save_to_db=True), "Импортировано файлов МЧД")
            except Exception as exc:
                messagebox.showerror(
                    "Ошибка импорта", str(exc), parent=self.winfo_toplevel()
                )

    def delete_selected(self) -> None:
        """Удаляет выбранные МЧД из базы данных после подтверждения."""
        selected = self.get_selected_mchd_objects()
        if not selected:
            messagebox.showinfo(
                "Выбор",
                "Выберите МЧД для удаления из учета",
                parent=self.winfo_toplevel(),
            )
            return

        confirm = messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить выбранные доверенности ({len(selected)} шт.) из учета базы данных?",
            parent=self.winfo_toplevel(),
        )
        if not confirm:
            return

        deleted_count = 0
        if hasattr(self.app, "mchds") and self.app.mchds:
            for m in selected:
                num = m.get("doc_number")
                if num and self.app.mchds.delete(num):
                    deleted_count += 1
            self.refresh()
            self.on_message(f"Удалено из учета МЧД: {deleted_count}")

    def view_personal_data(self) -> None:
        """Открывает окно подробной карточки реквизитов выбранной МЧД."""
        selected = self.get_selected_mchd_objects()
        if len(selected) != 1:
            messagebox.showwarning(
                "Внимание",
                "Выберите ровно одну МЧД для просмотра карточки",
                parent=self.winfo_toplevel(),
            )
            return
        MchdPersonalDataWindow(self.winfo_toplevel(), selected[0])

    def view_merged_authorities(self) -> None:
        """Открывает окно просмотра объединенных полномочий для выбранных МЧД."""
        selected = self.get_selected_mchd_objects()
        if not selected:
            messagebox.showwarning(
                "Внимание",
                "Выберите МЧД для просмотра полномочий",
                parent=self.winfo_toplevel(),
            )
            return
        merged = MCHDMerger.get_merged_authorities(selected)
        if merged:
            AuthoritiesViewWindow(self.winfo_toplevel(), merged)

    def merge_selected(self) -> None:
        """Объединяет полномочия выбранных МЧД в единый XML файл."""
        selected = self.get_selected_mchd_objects()
        if len(selected) < 2:
            messagebox.showwarning(
                "Внимание",
                "Выберите минимум 2 МЧД для объединения полномочий",
                parent=self.winfo_toplevel(),
            )
            return

        persons = {m.get("full_name", "") for m in selected}
        if len(persons) > 1:
            messagebox.showerror(
                "Ошибка",
                "Нельзя объединять МЧД разных людей!",
                parent=self.winfo_toplevel(),
            )
            return

        merged = MCHDMerger.get_merged_authorities(selected)
        person_name = next(iter(persons))
        clean_name = person_name.replace(" ", "_")
        default_file = f"Объединенная_МЧД_{clean_name}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.xml"

        save_path = filedialog.asksaveasfilename(
            defaultextension=".xml",
            filetypes=[("XML файлы", "*.xml"), ("Все файлы", "*.*")],
            initialfile=default_file,
            title="Сохранить черновик объединенной МЧД",
            parent=self.winfo_toplevel(),
        )
        if not save_path:
            return

        try:
            result = MCHDMerger.merge_mchd_files(selected, save_path)
            if result and os.path.exists(result):
                messagebox.showinfo(
                    "Успех",
                    f"Создан неподписанный черновик МЧД:\n\n"
                    f"ФИО: {person_name}\n"
                    f"Уникальных кодов: {merged.get('unique_codes_count', 0)}\n\n"
                    f"Файл сохранен:\n{result}",
                    parent=self.winfo_toplevel(),
                )
        except Exception as exc:
            messagebox.showerror(
                "Ошибка объединения", str(exc), parent=self.winfo_toplevel()
            )

    def copy_selected_codes(self) -> None:
        """Копирует коды полномочий выбранных МЧД в буфер обмена."""
        selected = self.get_selected_mchd_objects()
        codes: set[str] = set()
        for m in selected:
            codes.update(m.get("authority_codes", []))

        if codes:
            pyperclip.copy("\n".join(sorted(codes)))
            messagebox.showinfo(
                "Успех",
                f"Скопировано {len(codes)} уникальных кодов полномочий",
                parent=self.winfo_toplevel(),
            )
        else:
            messagebox.showwarning(
                "Внимание",
                "Нет кодов для копирования",
                parent=self.winfo_toplevel(),
            )

    def export_to_excel(self) -> None:
        """Экспортирует список отображаемых МЧД в файл таблицы Excel."""
        if not self.filtered_data:
            messagebox.showwarning(
                "Внимание",
                "Нет данных для экспорта",
                parent=self.winfo_toplevel(),
            )
            return

        default_name = (
            f"mchd_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
            initialdir=load_settings().export_folder,
            initialfile=default_name,
            title="Сохранить отчет по МЧД",
            parent=self.winfo_toplevel(),
        )
        if not save_path:
            return

        try:
            from certificate_analyzer.infrastructure.reports.excel_exporter import (
                ExcelReportExporter,
            )


            ExcelReportExporter().export_rows(
                self.filtered_data, save_path, "Отчет по МЧД"
            )
            messagebox.showinfo(
                "Успех",
                f"Отчет успешно сохранен:\n{save_path}",
                parent=self.winfo_toplevel(),
            )
        except Exception as exc:
            messagebox.showerror(
                "Ошибка экспорта",
                f"Не удалось экспортировать в Excel:\n{exc}",
                parent=self.winfo_toplevel(),
            )

    def open_xml_file(self) -> None:
        """Открывает исходный XML-файл выбранной МЧД в системной программе."""
        selected = self.get_selected_mchd_objects()
        if not selected:
            return
        path = selected[0].get("file_name")
        if path and os.path.exists(path):
            try:
                open_path(path)
            except Exception as exc:
                messagebox.showerror(
                    "Ошибка",
                    f"Не удалось открыть файл:\n{exc}",
                    parent=self.winfo_toplevel(),
                )
        else:
            messagebox.showwarning(
                "Файл не найден",
                f"Файл не существует на диске:\n{path}",
                parent=self.winfo_toplevel(),
            )

    def reveal_file(self) -> None:
        """Открывает папку с исходным файлом МЧД в проводнике."""
        selected = self.get_selected_mchd_objects()
        if not selected:
            return
        path = selected[0].get("file_name")
        if path and os.path.exists(path):
            open_path(os.path.dirname(path))

    def on_double_click(self, event: tk.Event) -> None:
        """Открывает карточку только при двойном щелчке по строке таблицы."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.view_personal_data()


class MCHDTableWindow:
    """Окно для автономного отображения таблицы МЧД (для обратной совместимости)."""

    def __init__(
        self,
        parent: tk.Widget,
        mchd_data: list[dict[str, Any]] | None = None,
        application: Any = None,
    ) -> None:
        """Инициализирует отдельное окно со списком МЧД.

        Args:
            parent: Родительский виджет.
            mchd_data: Список словарей доверенностей.
            application: Контейнер приложения (опционально).
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Машиночитаемые доверенности (МЧД)")
        self.window.geometry("1300x750")
        self.window.configure(bg=BG_COLOR)

        self.view = MchdView(
            self.window, application=application, mchd_data=mchd_data
        )
        self.view.pack(fill=tk.BOTH, expand=True)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Закрывает окно."""
        if self.window:
            self.window.destroy()
            self.window = None
