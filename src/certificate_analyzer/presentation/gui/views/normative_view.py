"""Окно просмотра нормативных документов по электронной подписи и МЧД."""

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.persistence.json_storage import (
    read_json,
    write_json,
)
from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_COLOR,
    SECONDARY_TEXT_COLOR,
    TEXT_COLOR,
    UI_FONT,
)

NORMATIVE_ITEMS = [
    {
        "title": "Федеральный закон № 63-ФЗ от 06.04.2011 «Об электронной подписи»",
        "category": "Федеральный закон",
        "description": "Основной закон об электронной подписи: виды подписей, юридическая сила, аккредитация УЦ",
        "url": "http://www.consultant.ru/document/cons_doc_LAW_112701/",
    },
    {
        "title": "Федеральный закон № 152-ФЗ от 27.07.2006 «О персональных данных»",
        "category": "Федеральный закон",
        "description": "Требования к обработке, хранению и защите персональных данных владельцев сертификатов",
        "url": "http://www.consultant.ru/document/cons_doc_LAW_61801/",
    },
    {
        "title": "Федеральный закон № 149-ФЗ от 27.07.2006 «Об информации, информ. технологиях и о защите информации»",
        "category": "Федеральный закон",
        "description": "Базовый закон об информации, юридической силе электронных сообщений и требованиях к защите",
        "url": "http://www.consultant.ru/document/cons_doc_LAW_61798/",
    },
    {
        "title": "Приказ Минцифры России № 857 от 18.10.2021 «Об утверждении единых требований к МЧД»",
        "category": "Приказ",
        "description": "Единые требования к формам машиночитаемых доверенностей (МЧД) в электронной форме",
        "url": "http://publication.pravo.gov.ru/Document/View/0001202112200010",
    },
    {
        "title": "Постановление Правительства РФ № 223 от 21.02.2022 «О порядке представления МЧД»",
        "category": "Постановление",
        "description": "Правила представления и проверки машиночитаемых доверенностей в информационных системах",
        "url": "http://publication.pravo.gov.ru/Document/View/0001202202240017",
    },
    {
        "title": "Приказ ФНС России от 30.04.2021 № ЕД-7-26/445@ «Формат МЧД для ФНС»",
        "category": "Приказ",
        "description": "Формат заявления о выдаче доверенности и формат машиночитаемой доверенности для налоговых органов",
        "url": "https://www.nalog.gov.ru/rn77/about_fts/docs/11631597/",
    },
    {
        "title": "ГОСТ Р 34.10-2012 «Процессы формирования и проверки ЭП»",
        "category": "ГОСТ",
        "description": "Национальный криптографический стандарт формирования и проверки электронной цифровой подписи",
        "url": "https://protect.gost.ru/document.aspx?control=7&id=190331",
    },
    {
        "title": "ГОСТ Р 34.11-2012 «Функция хэширования»",
        "category": "ГОСТ",
        "description": "Национальный криптографический стандарт вычисления хэш-функции («Стрибог»)",
        "url": "https://protect.gost.ru/document.aspx?control=7&id=190378",
    },
    {
        "title": "Приказ ФСБ России № 795 от 27.12.2011 «Требования к форме квалифицированного сертификата»",
        "category": "Приказ",
        "description": "Требования к структуре и полям квалифицированного сертификата ключа проверки электронной подписи",
        "url": "http://www.consultant.ru/document/cons_doc_LAW_125741/",
    },
    {
        "title": "Приказ ФСБ России № 796 от 27.12.2011 «Требования к средствам электронной подписи»",
        "category": "Приказ",
        "description": "Требования к средствам электронной подписи и средствам удостоверяющего центра",
        "url": "http://www.consultant.ru/document/cons_doc_LAW_126131/",
    },
]

COLUMNS = {
    "title": ("Наименование документа", 430),
    "category": ("Категория", 140),
    "description": ("Описание", 310),
}


class NormativeWindow:
    """Окно со списком нормативных документов и возможностью поиска."""

    _instance = None

    def __new__(cls, parent=None, *args, **kwargs):
        if cls._instance is not None:
            try:
                if cls._instance.window and cls._instance.window.winfo_exists():
                    cls._instance.window.lift()
                    cls._instance.window.focus_force()
                    return cls._instance
            except Exception:
                pass
        instance = super().__new__(cls)
        cls._instance = instance
        return instance

    def __init__(self, parent):
        if getattr(self, "_initialized", False):
            return

        self.parent = parent
        self.window = None
        self._sort_reverse: dict[str, bool] = {}
        self.custom_docs: list[dict] = self._load_custom_docs()
        self.documents = list(NORMATIVE_ITEMS) + list(self.custom_docs)
        self.filtered_docs = list(self.documents)

        self._create_window()
        self._initialized = True

    @property
    def _custom_docs_path(self) -> Path:
        return config_dir() / "custom_normative_docs.json"

    def _load_custom_docs(self) -> list[dict]:
        """Загружает добавленные пользователем нормативные документы из локального хранилища."""
        try:
            data = read_json(self._custom_docs_path, [])
            if isinstance(data, list):
                return [
                    doc
                    for doc in data
                    if isinstance(doc, dict) and "title" in doc and "url" in doc
                ]
        except Exception:
            pass
        return []

    def _save_custom_docs(self) -> None:
        """Сохраняет добавленные пользователем нормативные документы."""
        try:
            write_json(self._custom_docs_path, self.custom_docs)
        except Exception:
            pass

    def _create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Нормативные документы")
        self.window.geometry("940x590")
        self.window.minsize(680, 420)
        self.window.configure(bg=BG_COLOR)

        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None
        self._initialized = False
        NormativeWindow._instance = None

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок окна
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame,
            text="Нормативные документы по электронной подписи и МЧД",
            font=(UI_FONT, 13, "bold"),
            foreground=TEXT_COLOR,
        ).pack(side=tk.LEFT)

        self.stats_label = ttk.Label(
            header_frame,
            text="",
            font=(UI_FONT, 10),
            foreground=ACCENT_COLOR,
        )
        self.stats_label.pack(side=tk.RIGHT)

        # Панель поиска, фильтрации и добавления
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="Поиск:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_docs())
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=28)
        search_entry.pack(side=tk.LEFT, padx=(0, 12))
        search_entry.focus()

        ttk.Label(filter_frame, text="Категория:").pack(side=tk.LEFT, padx=(0, 5))
        self.category_var = tk.StringVar(value="Все категории")
        categories = ["Все категории"] + sorted(
            list({d["category"] for d in self.documents})
        )
        self.cat_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.category_var,
            values=categories,
            state="readonly",
            width=18,
        )
        self.cat_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.cat_combo.bind("<<ComboboxSelected>>", lambda _: self._filter_docs())

        ttk.Button(filter_frame, text="Сбросить", command=self.clear_filters).pack(
            side=tk.LEFT
        )

        # Таблица-список документов
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=list(COLUMNS.keys()),
            show="headings",
            selectmode="browse",
        )
        for col, (title, width) in COLUMNS.items():
            self.tree.heading(
                col,
                text=title,
                command=lambda c=col: self._sort_column(c),
            )
            self.tree.column(col, width=width, minwidth=100)

        scrollbar_y = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        scrollbar_x = ttk.Scrollbar(
            table_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=scrollbar_x.set)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Панель детальной информации по выбранному документу
        details_frame = ttk.LabelFrame(
            main_frame, text="Информация о документе", padding=8
        )
        details_frame.pack(fill=tk.X, pady=(10, 5))

        self.selected_title_var = tk.StringVar(value="Выберите документ из списка выше")
        self.selected_desc_var = tk.StringVar(value="")
        self.selected_url_var = tk.StringVar(value="")

        ttk.Label(
            details_frame,
            textvariable=self.selected_title_var,
            font=(UI_FONT, 9, "bold"),
            foreground=TEXT_COLOR,
            wraplength=900,
        ).pack(anchor=tk.W)

        ttk.Label(
            details_frame,
            textvariable=self.selected_desc_var,
            font=(UI_FONT, 9),
            foreground=SECONDARY_TEXT_COLOR,
            wraplength=900,
        ).pack(anchor=tk.W, pady=(2, 0))

        url_lbl = ttk.Label(
            details_frame,
            textvariable=self.selected_url_var,
            font=(UI_FONT, 9, "underline"),
            foreground=BUTTON_COLOR,
            cursor="hand2",
        )
        url_lbl.pack(anchor=tk.W, pady=(2, 0))
        url_lbl.bind("<Button-1>", lambda _: self.open_selected())

        # Нижняя панель с кнопками и подсказкой
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(8, 0))

  
        self.status_msg = ttk.Label(
            bottom_frame,
            text="",
            font=(UI_FONT, 9),
            foreground=ACCENT_COLOR,
        )
        self.status_msg.pack(side=tk.LEFT, padx=(15, 0))

        btn_box = ttk.Frame(bottom_frame)
        btn_box.pack(side=tk.RIGHT)

        self.add_btn = ttk.Button(
            btn_box,
            text="Добавить…",
            command=self.show_add_dialog,
        )
        self.add_btn.pack(side=tk.LEFT, padx=4)

        self.copy_btn = ttk.Button(
            btn_box,
            text="Копировать ссылку",
            command=self.copy_link,
        )
        self.copy_btn.pack(side=tk.LEFT, padx=4)

        self.open_btn = ttk.Button(
            btn_box,
            text="Открыть в браузере",
            command=self.open_selected,
            style="Accent.TButton",
        )
        self.open_btn.pack(side=tk.LEFT, padx=4)

        ttk.Button(
            btn_box,
            text="Закрыть",
            command=self._on_close,
        ).pack(side=tk.LEFT, padx=4)

        # Контекстное меню
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(
            label="Открыть в браузере", command=self.open_selected
        )
        self.context_menu.add_command(label="Копировать ссылку", command=self.copy_link)
        self.context_menu.add_command(
            label="Копировать наименование", command=self.copy_title
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Добавить документ…", command=self.show_add_dialog
        )
        self.context_menu.add_command(
            label="Удалить из списка", command=self.delete_selected
        )

        # Привязка событий
        self.tree.bind("<Double-1>", lambda _: self.open_selected())
        self.tree.bind("<Return>", lambda _: self.open_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._on_select())
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Delete>", lambda _: self.delete_selected())

        self.window.bind("<Escape>", lambda _: self._on_close())
        self.window.bind("<Control-f>", lambda _: search_entry.focus_set())
        self.window.bind("<Control-F>", lambda _: search_entry.focus_set())
        self.window.bind("<Control-n>", lambda _: self.show_add_dialog())
        self.window.bind("<Control-N>", lambda _: self.show_add_dialog())

        # Первичное заполнение
        self._filter_docs()

    def _filter_docs(self) -> None:
        """Фильтрует документы по поисковой строке и категории."""
        query = self.search_var.get().strip().lower()
        selected_category = self.category_var.get()

        self.filtered_docs = []
        for doc in self.documents:
            if (
                selected_category != "Все категории"
                and doc["category"] != selected_category
            ):
                continue

            if query:
                searchable_text = f"{doc['title']} {doc['description']} {doc['category']} {doc['url']}".lower()
                if query not in searchable_text:
                    continue

            self.filtered_docs.append(doc)

        self._populate_tree()
        self._update_stats()

    def _populate_tree(self, maintain_selection: bool = False) -> None:
        """Заполняет таблицу текущими отфильтрованными документами."""
        prev_url = None
        if maintain_selection and self.tree.selection():
            try:
                prev_idx = int(self.tree.selection()[0])
                if 0 <= prev_idx < len(self.filtered_docs):
                    prev_url = self.filtered_docs[prev_idx]["url"]
            except Exception:
                pass

        self.tree.delete(*self.tree.get_children())
        select_iid = None

        for idx, doc in enumerate(self.filtered_docs):
            iid = str(idx)
            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(doc["title"], doc["category"], doc["description"]),
            )
            if prev_url and doc["url"] == prev_url:
                select_iid = iid

        children = self.tree.get_children()
        if children:
            target = select_iid if select_iid else children[0]
            self.tree.selection_set(target)
            self.tree.focus(target)
            self._on_select()
        else:
            self._update_details(None)

    def _update_stats(self) -> None:
        """Обновляет счетчик найденных документов."""
        total = len(self.documents)
        found = len(self.filtered_docs)
        if found == total:
            self.stats_label.config(text=f"Всего документов: {total}")
        else:
            self.stats_label.config(text=f"Найдено: {found} из {total}")

    def _on_select(self, _event=None) -> None:
        """Обрабатывает выбор строки в списке."""
        selected = self.tree.selection()
        if not selected:
            self._update_details(None)
            return

        try:
            idx = int(selected[0])
            if 0 <= idx < len(self.filtered_docs):
                self._update_details(self.filtered_docs[idx])
            else:
                self._update_details(None)
        except (ValueError, IndexError):
            self._update_details(None)

    def _update_details(self, doc: dict | None) -> None:
        """Обновляет панель деталей по выбранному документу."""
        if doc:
            self.selected_title_var.set(doc["title"])
            self.selected_desc_var.set(
                f"Категория: {doc['category']} • {doc['description']}"
            )
            self.selected_url_var.set(doc["url"])
            self.open_btn.config(state="normal")
            self.copy_btn.config(state="normal")
        else:
            if not self.filtered_docs:
                self.selected_title_var.set("Ничего не найдено")
                self.selected_desc_var.set(
                    "Попробуйте изменить поисковый запрос или сбросить фильтры."
                )
            else:
                self.selected_title_var.set("Выберите документ из списка выше")
                self.selected_desc_var.set("")
            self.selected_url_var.set("")
            self.open_btn.config(state="disabled")
            self.copy_btn.config(state="disabled")

    def _sort_column(self, col: str) -> None:
        """Сортирует список документов по выбранной колонке."""
        reverse = self._sort_reverse.get(col, False)
        self.filtered_docs.sort(key=lambda d: d.get(col, "").lower(), reverse=reverse)
        self._sort_reverse[col] = not reverse
        self._populate_tree(maintain_selection=True)

    def _show_context_menu(self, event) -> None:
        """Отображает контекстное меню при правом клике на строку."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._on_select()
        self.context_menu.post(event.x_root, event.y_root)

    def open_selected(self, _event=None) -> None:
        """Открывает выбранный документ в веб-браузере по умолчанию."""
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            if 0 <= idx < len(self.filtered_docs):
                webbrowser.open(self.filtered_docs[idx]["url"])
        except (ValueError, IndexError):
            pass

    def copy_link(self) -> None:
        """Копирует ссылку выбранного документа в буфер обмена."""
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            if 0 <= idx < len(self.filtered_docs):
                url = self.filtered_docs[idx]["url"]
                self.window.clipboard_clear()
                self.window.clipboard_append(url)
                self.window.update()
                self.status_msg.config(text="✓ Ссылка скопирована в буфер обмена")
                self.window.after(2500, lambda: self.status_msg.config(text=""))
        except (ValueError, IndexError):
            pass

    def copy_title(self) -> None:
        """Копирует наименование выбранного документа в буфер обмена."""
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            if 0 <= idx < len(self.filtered_docs):
                title = self.filtered_docs[idx]["title"]
                self.window.clipboard_clear()
                self.window.clipboard_append(title)
                self.window.update()
                self.status_msg.config(text="✓ Название скопировано")
                self.window.after(2500, lambda: self.status_msg.config(text=""))
        except (ValueError, IndexError):
            pass

    def clear_filters(self) -> None:
        """Сбрасывает установленные поисковые фильтры."""
        self.search_var.set("")
        self.category_var.set("Все категории")
        self._filter_docs()

    def show_add_dialog(self) -> None:
        """Отображает диалоговое окно добавления нового нормативного документа."""
        dialog = tk.Toplevel(self.window)
        dialog.title("Добавить нормативный документ")
        dialog.geometry("540x280")
        dialog.minsize(460, 260)
        dialog.transient(self.window)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Наименование документа:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        title_var = tk.StringVar()
        title_entry = ttk.Entry(frame, textvariable=title_var, width=38)
        title_entry.grid(row=0, column=1, sticky="ew", pady=4)
        title_entry.focus_set()

        ttk.Label(frame, text="Категория:").grid(row=1, column=0, sticky="w", pady=4)
        category_var = tk.StringVar(value="Федеральный закон")
        existing_categories = sorted(
            list(
                {d["category"] for d in self.documents if d.get("category")}
                | {
                    "Федеральный закон",
                    "Приказ",
                    "Постановление",
                    "ГОСТ",
                    "Локальный акт",
                }
            )
        )
        cat_combo = ttk.Combobox(
            frame,
            textvariable=category_var,
            values=existing_categories,
            width=36,
        )
        cat_combo.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Описание:").grid(row=2, column=0, sticky="w", pady=4)
        desc_var = tk.StringVar()
        ttk.Entry(frame, textvariable=desc_var, width=38).grid(
            row=2, column=1, sticky="ew", pady=4
        )

        ttk.Label(frame, text="Ссылка (URL):").grid(row=3, column=0, sticky="w", pady=4)
        url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=url_var, width=38).grid(
            row=3, column=1, sticky="ew", pady=4
        )

        frame.columnconfigure(1, weight=1)

        def save():
            title = title_var.get().strip()
            category = category_var.get().strip() or "Другое"
            desc = desc_var.get().strip() or "—"
            url = url_var.get().strip()

            if not title:
                messagebox.showwarning(
                    "Внимание", "Укажите наименование документа.", parent=dialog
                )
                title_entry.focus_set()
                return

            if not url:
                messagebox.showwarning(
                    "Внимание", "Укажите ссылку (URL) на документ.", parent=dialog
                )
                return

            if not (
                url.startswith("http://")
                or url.startswith("https://")
                or url.startswith("file://")
            ):
                url = "https://" + url

            self.add_document(
                title=title,
                category=category,
                description=desc,
                url=url,
            )
            dialog.destroy()

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=4, column=0, columnspan=2, pady=(16, 0), sticky="e")

        ttk.Button(btn_box, text="Отмена", command=dialog.destroy).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(btn_box, text="Добавить", command=save, style="Accent.TButton").pack(
            side="right"
        )

        dialog.bind("<Return>", lambda _: save())
        dialog.bind("<Escape>", lambda _: dialog.destroy())

    def add_document(
        self, title: str, category: str, description: str, url: str
    ) -> None:
        """Добавляет новый нормативный документ в список и сохраняет пользовательские документы."""
        new_doc = {
            "title": title,
            "category": category,
            "description": description,
            "url": url,
            "custom": True,
        }
        self.documents.append(new_doc)
        self.custom_docs.append(new_doc)
        self._save_custom_docs()

        # Обновляем список категорий в фильтре
        categories = ["Все категории"] + sorted(
            list({d["category"] for d in self.documents})
        )
        self.cat_combo.config(values=categories)

        # Обновляем таблицу
        self._filter_docs()

        # Выбираем добавленный элемент
        for idx, doc in enumerate(self.filtered_docs):
            if doc["url"] == url and doc["title"] == title:
                iid = str(idx)
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                self._on_select()
                break

        self.status_msg.config(text="✓ Документ успешно добавлен")
        self.window.after(2500, lambda: self.status_msg.config(text=""))

    def delete_selected(self) -> None:
        """Удаляет выбранный документ из списка."""
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            if not (0 <= idx < len(self.filtered_docs)):
                return
            doc = self.filtered_docs[idx]
            if messagebox.askyesno(
                "Удаление документа",
                f"Удалить «{doc['title']}» из списка?",
                parent=self.window,
            ):
                self.documents = [d for d in self.documents if d != doc]
                self.custom_docs = [
                    d
                    for d in self.custom_docs
                    if not (
                        d.get("url") == doc.get("url")
                        and d.get("title") == doc.get("title")
                    )
                ]
                self._save_custom_docs()
                self._filter_docs()
                self.status_msg.config(text="✓ Документ удален")
                self.window.after(2500, lambda: self.status_msg.config(text=""))
        except (ValueError, IndexError):
            pass
