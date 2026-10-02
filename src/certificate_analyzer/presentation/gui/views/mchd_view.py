"""Представление вкладки машиночитаемых доверенностей (МЧД) и диалоговые окна."""

from datetime import timezone, datetime
UTC = timezone.utc
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
from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    CARD_BG_COLOR,
    CARD_BORDER_COLOR,
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    MCHD_COLOR,
    MCHD_LIGHT_COLOR,
    TEXT_COLOR,
    UI_FONT,
    WARNING_COLOR,
    WARNING_TEXT,
)
from certificate_analyzer.presentation.gui.widgets.table_state import (
    EmptyStateLabel,
    sort_heading_text,
)


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


class MchdPersonalDataWindow:
    """Окно карточки персональных данных и реквизитов МЧД."""

    def __init__(self, parent: tk.Widget, mchd: dict[str, Any]) -> None:
        """Инициализирует карточку доверенности.

        Args:
            parent: Родительский виджет.
            mchd: Словарь с атрибутами МЧД.
        """
        self.parent = parent
        self.mchd = mchd
        self.window: tk.Toplevel | None = None
        self._unbind_scroll = None
        self._create_window()

    def _create_window(self) -> None:
        """Создает Toplevel диалог просмотра реквизитов."""
        has_issuer = (
            self.mchd.get("issuer_org_name", "Не найдено") != "Не найдено"
            or self.mchd.get("issuer_person_fullname", "Не найдено")
            != "Не найдено"
        )
        width = 900 if has_issuer else 760
        height = 760 if has_issuer else 620

        self.window = tk.Toplevel(self.parent)
        file_name = os.path.basename(self.mchd.get("file_name", ""))
        self.window.title(f"Карточка МЧД — {file_name}")
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg=BG_COLOR)
        self.window.minsize(700, 550)

        self._setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Безопасно закрывает карточку и снимает биндинги мыши."""
        if self._unbind_scroll:
            self._unbind_scroll()
            self._unbind_scroll = None
        if self.window:
            self.window.destroy()
            self.window = None

    def _setup_ui(self) -> None:
        """Создает скроллируемые карточки с реквизитами МЧД."""
        if not self.window:
            return

        main_frame = tk.Frame(self.window, bg=BG_COLOR, padx=16, pady=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame, bg=BG_COLOR)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        title_text_frame = tk.Frame(title_frame, bg=BG_COLOR)
        title_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            title_text_frame,
            text="Карточка машиночитаемой доверенности",
            font=(UI_FONT, 16, "bold"),
            bg=BG_COLOR,
            fg=MCHD_COLOR,
        ).pack(anchor=tk.W)

        file_path = self.mchd.get("file_name", "—")
        tk.Label(
            title_text_frame,
            text=f"Файл: {os.path.basename(file_path)}",
            font=(UI_FONT, 9),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
        ).pack(anchor=tk.W)

        canvas_frame = tk.Frame(main_frame, bg=BG_COLOR)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind(
            "<Configure>",
            lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def add_info_card(
            title: str, items: list[tuple[str, Any]]
        ) -> None:
            card = tk.Frame(
                scrollable_frame,
                bg=CARD_BG_COLOR,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=CARD_BORDER_COLOR,
            )
            card.pack(fill=tk.X, pady=(0, 12))
            hdr = tk.Frame(card, bg=MCHD_COLOR, height=36)
            hdr.pack(fill=tk.X)
            hdr.pack_propagate(False)

            tk.Label(
                hdr,
                text=title,
                font=(UI_FONT, 10, "bold"),
                fg="white",
                bg=MCHD_COLOR,
            ).pack(side=tk.LEFT, padx=12, pady=6)

            body = tk.Frame(card, bg=CARD_BG_COLOR, padx=12, pady=8)
            body.pack(fill=tk.X)

            for label, value in items:
                row = tk.Frame(body, bg=CARD_BG_COLOR)
                row.pack(fill=tk.X, pady=3)
                tk.Label(
                    row,
                    text=f"{label}:",
                    font=(UI_FONT, 9, "bold"),
                    fg=MCHD_COLOR,
                    bg=CARD_BG_COLOR,
                    width=22,
                    anchor="w",
                ).pack(side=tk.LEFT, padx=(0, 8))

                val_str = str(value) if value else "—"
                lbl_val = tk.Label(
                    row,
                    text=val_str,
                    font=(UI_FONT, 9),
                    bg=CARD_BG_COLOR,
                    fg=TEXT_COLOR,
                    anchor="w",
                    justify="left",
                )
                lbl_val.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 1. Основные реквизиты
        add_info_card(
            "Реквизиты документа",
            [
                (
                    "Номер доверенности",
                    self.mchd.get("doc_number", "Не найдено"),
                ),
                ("Дата выдачи", self.mchd.get("issue_date", "Не найдена")),
                (
                    "Срок действия",
                    self.mchd.get("expiry_date", "Не найдена"),
                ),
                ("Статус срока", self.mchd.get("status", "Не определен")),
                ("Проверка подлинности", "Не проверена (подпись, доверие, отзыв)"),
            ],
        )

        # 2. Доверитель (организация)
        org_name = self.mchd.get(
            "issuer_org_name", self.mchd.get("principal_name", "Не найдено")
        )
        org_inn = self.mchd.get(
            "issuer_org_inn", self.mchd.get("principal_inn", "Не найден")
        )
        add_info_card(
            "Сведения о доверителе",
            [
                ("Наименование организации", org_name),
                ("ИНН организации", org_inn),
                ("КПП", self.mchd.get("issuer_org_kpp", "—")),
                ("ОГРН", self.mchd.get("issuer_org_ogrn", "—")),
            ],
        )

        # 3. Представитель (физическое лицо)
        rep_name = self.mchd.get(
            "full_name", self.mchd.get("representative_fio", "Не найдено")
        )
        rep_inn = self.mchd.get(
            "inn", self.mchd.get("representative_inn", "Не найден")
        )
        rep_snils = self.mchd.get(
            "snils", self.mchd.get("representative_snils", "Не найден")
        )
        add_info_card(
            "Сведения о представителе",
            [
                ("ФИО представителя", rep_name),
                ("ИНН представителя", rep_inn),
                ("СНИЛС представителя", rep_snils),
                (
                    "Дата рождения",
                    self.mchd.get("representative_birthdate", "—"),
                ),
            ],
        )

        # 4. Полномочия
        codes = self.mchd.get("authority_codes", [])
        names = self.mchd.get("authority_names", [])
        auth_items = []
        if codes:
            for i, c in enumerate(codes):
                c_name = names[i] if i < len(names) and names[i] else ""
                val = f"{c} ({c_name})" if c_name else c
                auth_items.append((f"Полномочие #{i + 1}", val))
        else:
            auth_items.append(("Полномочия", "Нет кодов"))
        add_info_card("Полномочия", auth_items)

        # Кнопки управления
        btn_bar = ttk.Frame(main_frame)
        btn_bar.pack(fill=tk.X, pady=(12, 0))

        ttk.Button(
            btn_bar, text="Закрыть", command=self._on_close, style="Accent.TButton"
        ).pack(side="right")

        # Безопасный скроллинг мыши
        def _on_mousewheel(event: tk.Event) -> None:
            try:
                if not canvas.winfo_exists():
                    return
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
                elif getattr(event, "delta", 0):
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except (tk.TclError, RuntimeError):
                pass

        def _bind(_event=None):
            try:
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
                canvas.bind_all("<Button-4>", _on_mousewheel)
                canvas.bind_all("<Button-5>", _on_mousewheel)
            except (tk.TclError, RuntimeError):
                pass

        def _unbind(_event=None):
            try:
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
            except (tk.TclError, RuntimeError):
                pass

        self._unbind_scroll = _unbind
        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)
        scrollable_frame.bind("<Enter>", _bind)
        scrollable_frame.bind("<Leave>", _unbind)
        self.window.bind("<MouseWheel>", _on_mousewheel)


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
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(
            toolbar,
            text="Сканировать папку…",
            command=self.scan_folder,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            toolbar,
            text="Импортировать XML…",
            command=self.import_files,
            style="Toolbar.TButton",
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            toolbar,
            text="Экспорт в Excel",
            command=self.export_to_excel,
            style="Toolbar.TButton",
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            toolbar,
            text="Обновить",
            command=self.refresh,
            style="Toolbar.TButton",
        ).pack(
            side=tk.LEFT, padx=3
        )

        # 2. Панель поиска и фильтрации
        filter_bar = ttk.Frame(self, style="Panel.TFrame", padding=(8, 6))
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        filter_bar.columnconfigure(1, weight=1)
        ttk.Label(filter_bar, text="Поиск:", style="Panel.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filters())
        search_entry = ttk.Entry(filter_bar, textvariable=self.search_var, width=28)
        search_entry.grid(row=0, column=1, sticky=tk.EW, padx=(6, 12))

        ttk.Label(filter_bar, text="Статус срока:", style="Panel.TLabel").grid(
            row=0, column=2, sticky=tk.E, padx=(0, 4)
        )
        self.status_var = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(
            filter_bar,
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
        status_combo.grid(row=0, column=3, padx=(0, 8))
        status_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        ttk.Button(
            filter_bar,
            text="Сбросить",
            command=self.clear_search,
            width=10,
            style="Toolbar.TButton",
        ).grid(row=0, column=4)

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
        self.person_info_label.pack(fill=tk.X, pady=(0, 8))

        self.mchd_detail_fields: dict[str, ttk.Label] = {}
        property_labels = (
            ("doc_number", "Номер"),
            ("status", "Статус срока"),
            ("full_name", "Представитель"),
            ("issuer_org_name", "Доверитель"),
            ("issue_date", "Дата выдачи"),
            ("expiry_date", "Действует до"),
            ("file_name", "Файл"),
        )
        properties = ttk.Frame(details_frame, style="Status.TFrame")
        properties.pack(fill=tk.X)
        properties.columnconfigure(1, weight=1)
        for row, (key, title) in enumerate(property_labels):
            ttk.Label(
                properties,
                text=f"{title}:",
                font=(UI_FONT, 9, "bold"),
                style="Panel.TLabel",
            ).grid(row=row, column=0, sticky=tk.NW, padx=(0, 8), pady=3)
            value = ttk.Label(
                properties,
                text="—",
                style="Panel.TLabel",
                wraplength=230,
                justify=tk.LEFT,
            )
            value.grid(row=row, column=1, sticky=tk.EW, pady=3)
            self.mchd_detail_fields[key] = value

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

        actions = ttk.Frame(details_frame, style="Status.TFrame")
        actions.pack(fill=tk.X, pady=(8, 0))
        self.detail_action_buttons: list[ttk.Button] = []
        for label, command in (
            ("Открыть карточку", self.view_personal_data),
            ("Открыть XML", self.open_xml_file),
            ("Показать в проводнике", self.reveal_file),
            ("Копировать коды", self.copy_selected_codes),
        ):
            button = ttk.Button(
                actions,
                text=label,
                command=command,
                style="Toolbar.TButton",
                state="disabled",
            )
            button.pack(fill=tk.X, pady=(0, 5))
            self.detail_action_buttons.append(button)
        details_frame.bind("<Configure>", self._resize_detail_values, add="+")

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
        wraplength = max(150, event.width - 145)
        self.person_info_label.config(wraplength=max(180, event.width - 24))
        for label in self.mchd_detail_fields.values():
            label.config(wraplength=wraplength)

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
        for idx, mchd in enumerate(self.filtered_data):
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
            iid = f"row_{idx}_{id(mchd)}"
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

        self.selected_items = ()
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
        if col in ("issue_date", "expiry_date"):

            def parse_d(val: str) -> datetime:
                try:
                    if val and val not in ("Не найдена", "Не найден", ""):
                        return datetime.strptime(val, "%d.%m.%Y")
                except Exception:
                    pass
                return datetime.min.replace(tzinfo=UTC)

            data.sort(
                key=lambda x: parse_d(x[0]), reverse=descending
            )
        else:
            data.sort(
                key=lambda x: str(x[0]).lower(), reverse=descending
            )

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
        if count >= 1:
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
                records = self.app.mchds.scan(path, save_to_db=True)
                if self.app.mchds.errors:
                    err_msg = "\n".join(
                        [
                            f"{Path(k).name}: {v}"
                            for k, v in list(self.app.mchds.errors.items())[:5]
                        ]
                    )
                    messagebox.showwarning(
                        "Ошибки при анализе МЧД",
                        f"Обнаружены ошибки в некоторых файлах:\n\n{err_msg}",
                        parent=self.winfo_toplevel(),
                    )
                self.refresh()
                self.on_message(
                    f"Отсканировано и сохранено МЧД: {len(records)}"
                )
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
                imported = self.app.mchds.import_files(paths, save_to_db=True)
                self.refresh()
                self.on_message(f"Импортировано файлов МЧД: {len(imported)}")
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
