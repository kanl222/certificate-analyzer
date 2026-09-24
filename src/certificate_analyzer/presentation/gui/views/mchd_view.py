from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.platform.base import open_path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
import pyperclip
from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_COLOR,
    BUTTON_HOVER,
    CARD_BG_COLOR,
    CARD_BORDER_COLOR,
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    MCHD_COLOR,
    MCHD_LIGHT_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
    WARNING_TEXT,
    UI_FONT,
)
from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger


class AuthoritiesViewWindow:
    def __init__(self, parent, merged_data):
        self.parent = parent
        self.merged_data = merged_data
        self.window = None
        self._create_window()

    def _create_window(self):
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

    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(
            title_frame, text="Объединенные полномочия", font=(UI_FONT, 14, "bold")
        ).pack(anchor=tk.W)
        ttk.Label(
            title_frame,
            text=f"ФИО: {self.merged_data.get('person_name', 'Неизвестно')}",
            font=(UI_FONT, 11),
            foreground=ACCENT_COLOR,
        ).pack(anchor=tk.W)
        info_frame = ttk.LabelFrame(main_frame, text=" Исходные файлы ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        files_text = "\n".join(
            [f"• {f}" for f in self.merged_data.get("file_names", [])]
        )
        ttk.Label(info_frame, text=files_text, font=(UI_FONT, 9)).pack(anchor=tk.W)
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        stats_text = f"Всего файлов: {self.merged_data.get('total_files', 0)} | Уникальных кодов: {self.merged_data.get('unique_codes_count', 0)}"
        ttk.Label(stats_frame, text=stats_text, font=(UI_FONT, 10, "bold")).pack()
        codes_frame = ttk.LabelFrame(main_frame, text=" Коды полномочий ", padding=10)
        codes_frame.pack(fill=tk.BOTH, expand=True)
        listbox_frame = ttk.Frame(codes_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.codes_listbox = tk.Listbox(
            listbox_frame, height=12, selectmode=tk.EXTENDED, font=("Courier New", 10)
        )
        self.codes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(
            listbox_frame, orient=tk.VERTICAL, command=self.codes_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.codes_listbox.configure(yscrollcommand=scrollbar.set)
        for code in self.merged_data.get("codes", []):
            self.codes_listbox.insert(tk.END, code)
        self.codes_listbox.bind("<Control-c>", self.copy_selected_codes_event)
        self.codes_listbox.bind("<Control-C>", self.copy_selected_codes_event)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(
            btn_frame,
            text="📋 Копировать все коды",
            command=self.copy_all_codes,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="📋 Копировать выбранные",
            command=self.copy_selected_codes,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="❌ Закрыть", command=self._on_close, style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)

    def copy_all_codes(self):
        codes = self.merged_data.get("codes", [])
        if codes:
            pyperclip.copy("\n".join(codes))
            messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")

    def copy_selected_codes(self):
        selected = self.codes_listbox.curselection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите коды для копирования")
            return
        codes = [self.codes_listbox.get(i) for i in selected]
        pyperclip.copy("\n".join(codes))
        messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")

    def copy_selected_codes_event(self, event):
        selected = self.codes_listbox.curselection()
        if selected:
            codes = [self.codes_listbox.get(i) for i in selected]
            pyperclip.copy("\n".join(codes))
            self.window.title(f"Скопировано {len(codes)} кодов")
            self.window.after(
                2000, lambda: self.window.title("Объединенные полномочия МЧД")
            )
            return "break"
        return None


class MCHDTableWindow:
    def __init__(self, parent, mchd_data):
        self.parent = parent
        self.mchd_data = mchd_data
        self.filtered_data = mchd_data.copy()
        self.window = None
        self.selected_items = []
        self.sort_reverse = {}
        self._create_window()

    def _create_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Анализ МЧД - Машиночитаемые доверенности")
        self.window.geometry("1400x800")
        self.window.configure(bg=BG_COLOR)
        self.setup_ui()
        self.check_for_duplicates()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            title_frame,
            text="Машиночитаемые доверенности (МЧД)",
            font=(UI_FONT, 16, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            title_frame,
            text=f"Всего: {len(self.mchd_data)}",
            font=(UI_FONT, 12),
            foreground=ACCENT_COLOR,
        ).pack(side=tk.RIGHT, padx=10)
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            search_frame, text="🔍 Поиск по фамилии:", font=(UI_FONT, 10)
        ).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))
        ttk.Button(
            search_frame,
            text="✖ Сбросить",
            command=self.clear_search,
            style="Accent.TButton",
            width=12,
        ).pack(side=tk.LEFT)
        self.search_result_label = ttk.Label(
            search_frame,
            text="",
            font=(UI_FONT, 9, "italic"),
            foreground=ACCENT_COLOR,
        )
        self.search_result_label.pack(side=tk.RIGHT, padx=(20, 0))
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        expired = sum(1 for m in self.mchd_data if m.get("status") == "Просрочен")
        warning = sum(
            1
            for m in self.mchd_data
            if m.get("status") and "Истекает" in m.get("status", "")
        )
        valid = sum(1 for m in self.mchd_data if m.get("status") == "Действует")
        stats_text = f"Действуют: {valid} | Истекают: {warning} | Просрочены: {expired}"
        ttk.Label(stats_frame, text=stats_text, font=(UI_FONT, 11, "bold")).pack()
        self.duplicate_frame = ttk.Frame(main_frame)
        self.duplicate_frame.pack(fill=tk.X, pady=(0, 10))
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.columns = (
            "Файл",
            "Номер доверенности",
            "Дата выдачи",
            "Срок действия",
            "ФИО",
            "Коды полномочий",
            "Статус",
        )
        self.tree = ttk.Treeview(
            table_frame,
            columns=self.columns,
            show="headings",
            height=12,
            selectmode=tk.EXTENDED,
        )
        col_widths = [150, 120, 90, 90, 200, 300, 100]
        for col, width in zip(self.columns, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=width, anchor=tk.W, minwidth=50)
            self.sort_reverse[col] = False
        scroll_y = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x = ttk.Scrollbar(
            table_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.tag_configure(
            "expired", background=EXPIRED_COLOR, foreground=EXPIRED_TEXT
        )
        self.tree.tag_configure(
            "warning", background=WARNING_COLOR, foreground=WARNING_TEXT
        )
        self.tree.tag_configure("normal", background=MCHD_LIGHT_COLOR)
        self.tree.tag_configure("duplicate_name", background="#fff3cd")
        self.populate_table()
        info_frame = ttk.LabelFrame(main_frame, text=" Информация ", padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        info_columns_frame = ttk.Frame(info_frame)
        info_columns_frame.pack(fill=tk.X, expand=True)
        left_info = ttk.Frame(info_columns_frame)
        left_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.selected_info_label = ttk.Label(
            left_info, text="Выбрано: 0 МЧД", font=(UI_FONT, 10, "bold")
        )
        self.selected_info_label.pack(anchor=tk.W)
        self.person_info_label = ttk.Label(
            left_info, text="", font=(UI_FONT, 9), foreground=ACCENT_COLOR
        )
        self.person_info_label.pack(anchor=tk.W)
        right_info = ttk.Frame(info_columns_frame)
        right_info.pack(side=tk.RIGHT, fill=tk.Y)
        self.view_auth_btn = ttk.Button(
            right_info,
            text="👁 Просмотр кодов",
            command=self.view_merged_authorities,
            style="Accent.TButton",
            state=tk.DISABLED,
        )
        self.view_auth_btn.pack(side=tk.RIGHT, padx=5)
        self.view_personal_btn = ttk.Button(
            right_info,
            text="👤 Персональные данные",
            command=self.view_personal_data,
            style="Accent.TButton",
            state=tk.DISABLED,
        )
        self.view_personal_btn.pack(side=tk.RIGHT, padx=5)
        self.merge_btn = ttk.Button(
            right_info,
            text="🔄 Объединить выбранные МЧД",
            command=self.merge_selected,
            style="Accent.TButton",
            state=tk.DISABLED,
        )
        self.merge_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            right_info,
            text="📋 Копировать коды",
            command=self.copy_selected_codes,
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)
        codes_frame = ttk.LabelFrame(
            main_frame, text=" Коды полномочий выбранных МЧД ", padding=10
        )
        codes_frame.pack(fill=tk.X, pady=(10, 0))
        listbox_frame = ttk.Frame(codes_frame)
        listbox_frame.pack(fill=tk.X, expand=True)
        self.codes_listbox = tk.Listbox(
            listbox_frame, height=6, selectmode=tk.SINGLE, font=("Courier New", 9)
        )
        self.codes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_codes = ttk.Scrollbar(
            listbox_frame, orient=tk.VERTICAL, command=self.codes_listbox.yview
        )
        scroll_codes.pack(side=tk.RIGHT, fill=tk.Y)
        self.codes_listbox.configure(yscrollcommand=scroll_codes.set)
        self.codes_listbox.bind("<Control-c>", self.copy_from_listbox)
        self.codes_listbox.bind("<Control-C>", self.copy_from_listbox)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(
            btn_frame,
            text="📊 Экспорт в Excel",
            command=self.export_to_excel,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="❌ Закрыть", command=self._on_close, style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)

    def copy_from_listbox(self, event):
        selected = self.codes_listbox.curselection()
        if selected:
            codes = [self.codes_listbox.get(i) for i in selected]
            pyperclip.copy("\n".join(codes))
            self.window.title(f"Скопировано {len(codes)} кодов - Анализ МЧД")
            self.window.after(
                2000,
                lambda: self.window.title("Анализ МЧД - Машиночитаемые доверенности"),
            )
            return "break"
        return None

    def view_personal_data(self):
        selected_mchd = self.get_selected_mchd_objects()
        if len(selected_mchd) != 1:
            messagebox.showwarning(
                "Внимание", "Выберите ровно одну МЧД для просмотра персональных данных"
            )
            return
        mchd = selected_mchd[0]
        has_issuer_data = (
            mchd.get("issuer_org_name", "Не найдено") != "Не найдено"
            or mchd.get("issuer_person_fullname", "Не найдено") != "Не найдено"
        )
        window_width = 900 if has_issuer_data else 750
        window_height = 750 if has_issuer_data else 600

        data_window = tk.Toplevel(self.window)
        data_window.title(
            f"Персональные данные МЧД - {os.path.basename(mchd.get('file_name', ''))}"
        )
        data_window.geometry(f"{window_width}x{window_height}")
        data_window.configure(bg=BG_COLOR)
        data_window.minsize(750, 600)

        main_frame = tk.Frame(data_window, bg=BG_COLOR, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame, bg=BG_COLOR)
        title_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            title_frame, text="📄", font=(UI_FONT, 32), bg=BG_COLOR, fg=MCHD_COLOR
        ).pack(side=tk.LEFT, padx=(0, 15))
        title_text_frame = tk.Frame(title_frame, bg=BG_COLOR)
        title_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            title_text_frame,
            text="Персональные данные",
            font=(UI_FONT, 18, "bold"),
            bg=BG_COLOR,
            fg=MCHD_COLOR,
        ).pack(anchor=tk.W)
        tk.Label(
            title_text_frame,
            text="Машиночитаемая доверенность",
            font=(UI_FONT, 10),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
        ).pack(anchor=tk.W)

        file_frame = tk.Frame(
            main_frame,
            bg=CARD_BG_COLOR,
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=CARD_BORDER_COLOR,
        )
        file_frame.pack(fill=tk.X, pady=(0, 15))
        file_inner = tk.Frame(file_frame, bg=CARD_BG_COLOR, padx=15, pady=10)
        file_inner.pack(fill=tk.X)

        tk.Label(
            file_inner,
            text="📁",
            font=(UI_FONT, 14),
            bg=CARD_BG_COLOR,
            fg=ACCENT_COLOR,
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            file_inner,
            text=os.path.basename(mchd.get("file_name", "")),
            font=(UI_FONT, 10, "italic"),
            bg=CARD_BG_COLOR,
            fg=ACCENT_COLOR,
        ).pack(side=tk.LEFT)

        canvas_frame = tk.Frame(main_frame, bg=BG_COLOR)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def create_info_card(parent, title, icon, data_list, color=MCHD_COLOR):
            card = tk.Frame(
                parent,
                bg=CARD_BG_COLOR,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=CARD_BORDER_COLOR,
            )
            card.pack(fill=tk.X, pady=(0, 15))
            header = tk.Frame(card, bg=color, height=40)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Label(
                header,
                text=f" {icon} {title}",
                font=(UI_FONT, 11, "bold"),
                fg="white",
                bg=color,
            ).pack(side=tk.LEFT, padx=15, pady=8)
            body = tk.Frame(card, bg=CARD_BG_COLOR, padx=15, pady=10)
            body.pack(fill=tk.X)
            for label, value in data_list:
                row = tk.Frame(body, bg=CARD_BG_COLOR)
                row.pack(fill=tk.X, pady=5)
                tk.Label(
                    row,
                    text=f"{label}:",
                    font=(UI_FONT, 9, "bold"),
                    fg=color,
                    bg=CARD_BG_COLOR,
                    width=24,
                    anchor="w",
                ).pack(side=tk.LEFT, padx=(0, 10))
                value_str = str(value) if value else "—"
                text_widget = tk.Text(
                    row,
                    height=1 if len(value_str) < 80 else 2,
                    wrap=tk.WORD,
                    font=(UI_FONT, 9),
                    bg=CARD_BG_COLOR,
                    fg=TEXT_COLOR,
                    borderwidth=0,
                    selectbackground=BUTTON_COLOR,
                    selectforeground="white",
                    highlightthickness=0,
                )
                text_widget.insert("1.0", value_str)
                text_widget.config(state="disabled")
                text_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            return card

        def create_codes_card(parent, title, icon, codes):
            card = tk.Frame(
                parent,
                bg=CARD_BG_COLOR,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=CARD_BORDER_COLOR,
            )
            card.pack(fill=tk.X, pady=(0, 15))
            header = tk.Frame(card, bg=MCHD_COLOR, height=40)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Label(
                header,
                text=f" {icon} {title}",
                font=(UI_FONT, 11, "bold"),
                fg="white",
                bg=MCHD_COLOR,
            ).pack(side=tk.LEFT, padx=15, pady=8)
            body = tk.Frame(card, bg=CARD_BG_COLOR, padx=15, pady=10)
            body.pack(fill=tk.X)
            if codes:
                codes_frame = tk.Frame(body, bg="#f8f9fa", relief="solid", bd=1)
                codes_frame.pack(fill=tk.X, pady=5)
                codes_text = "\n".join([f"  {code}" for code in codes])
                text_widget = tk.Text(
                    codes_frame,
                    height=min(len(codes) + 1, 10),
                    wrap=tk.WORD,
                    font=("Courier New", 9),
                    bg="#f8f9fa",
                    fg=TEXT_COLOR,
                    borderwidth=0,
                    selectbackground=BUTTON_COLOR,
                    selectforeground="white",
                    padx=10,
                    pady=8,
                )
                text_widget.insert("1.0", codes_text)
                text_widget.config(state="disabled")
                text_widget.pack(fill=tk.BOTH, expand=True)
                counter_frame = tk.Frame(body, bg=CARD_BG_COLOR)
                counter_frame.pack(fill=tk.X, pady=(8, 0))
                tk.Label(
                    counter_frame,
                    text=f"📊 Всего кодов: {len(codes)}",
                    font=(UI_FONT, 9, "italic"),
                    fg=ACCENT_COLOR,
                    bg=CARD_BG_COLOR,
                ).pack(side=tk.LEFT)

                def copy_codes():
                    pyperclip.copy("\n".join(codes))
                    messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")

                tk.Button(
                    counter_frame,
                    text="📋 Копировать коды",
                    command=copy_codes,
                    font=(UI_FONT, 8),
                    bg=BUTTON_COLOR,
                    fg="white",
                    cursor="hand2",
                    padx=10,
                    pady=2,
                    relief="flat",
                    bd=0,
                ).pack(side=tk.RIGHT)
            else:
                tk.Label(
                    body,
                    text="Нет данных о кодах полномочий",
                    font=(UI_FONT, 9, "italic"),
                    fg=ACCENT_COLOR,
                    bg=CARD_BG_COLOR,
                ).pack(pady=10)
            return card

        personal_data = [
            ("📋 Номер доверенности", mchd.get("doc_number", "Не найден")),
            ("📅 Дата выдачи", mchd.get("issue_date", "Не найдена")),
            ("⏰ Срок действия", mchd.get("expiry_date", "Не найден")),
            ("👤 ФИО представителя", mchd.get("full_name", "Не найдено")),
            ("🆔 ИНН представителя", mchd.get("inn", "Не найден")),
            ("🪪 СНИЛС представителя", mchd.get("snils", "Не найден")),
            ("🎂 Дата рождения представителя", mchd.get("birth_date", "Не найдена")),
            ("📊 Статус доверенности", mchd.get("status", "Не определен")),
        ]

        issuer_data = [
            ("📛 Наименование организации", mchd.get("issuer_org_name", "Не найдено")),
            ("🆔 ИНН организации", mchd.get("issuer_org_inn", "Не найден")),
            ("🔢 КПП организации", mchd.get("issuer_org_kpp", "Не найден")),
            ("📄 ОГРН организации", mchd.get("issuer_org_ogrn", "Не найден")),
            ("📍 Адрес организации", mchd.get("issuer_org_address", "Не найден")),
        ]

        authorized_data = [
            (
                "👤 ФИО уполномоченного лица",
                mchd.get("issuer_person_fullname", "Не найдено"),
            ),
            ("💼 Должность", mchd.get("issuer_person_position", "Не найдена")),
            ("🆔 ИНН уполномоченного лица", mchd.get("issuer_person_inn", "Не найден")),
            (
                "🪪 СНИЛС уполномоченного лица",
                mchd.get("issuer_person_snils", "Не найден"),
            ),
            (
                "🎂 Дата рождения уполномоченного лица",
                mchd.get("issuer_person_birthdate", "Не найдена"),
            ),
        ]

        auth_codes = mchd.get("authority_codes", [])
        create_info_card(
            scrollable_frame, "ИНФОРМАЦИЯ О ПРЕДСТАВИТЕЛЕ", "👤", personal_data
        )
        if has_issuer_data:
            create_info_card(
                scrollable_frame,
                "ОРГАНИЗАЦИЯ-ДОВЕРИТЕЛЬ",
                "🏢",
                issuer_data,
                ACCENT_COLOR,
            )
            create_info_card(
                scrollable_frame,
                "УПОЛНОМОЧЕННОЕ ЛИЦО",
                "👔",
                authorized_data,
                ACCENT_COLOR,
            )
        create_codes_card(scrollable_frame, "КОДЫ ПОЛНОМОЧИЙ", "🔑", auth_codes)

        info_bar = tk.Frame(main_frame, bg="#e9ecef", height=35)
        info_bar.pack(fill=tk.X, pady=(10, 0))
        info_bar.pack_propagate(False)
        tk.Label(
            info_bar,
            text="💡 Выделите любой текст мышкой и нажмите Ctrl+C для копирования",
            font=(UI_FONT, 8),
            fg=ACCENT_COLOR,
            bg="#e9ecef",
        ).pack(side=tk.LEFT, padx=15, pady=8)

        btn_frame = tk.Frame(main_frame, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        def copy_all_data():
            copy_text = "=" * 50 + "\n"
            copy_text += "          ПЕРСОНАЛЬНЫЕ ДАННЫЕ МЧД\n"
            copy_text += "=" * 50 + "\n\n"
            copy_text += "📌 ИНФОРМАЦИЯ О ПРЕДСТАВИТЕЛЕ\n"
            copy_text += "-" * 40 + "\n"
            copy_text += f"Номер доверенности: {mchd.get('doc_number', 'Не найден')}\n"
            copy_text += f"Дата выдачи: {mchd.get('issue_date', 'Не найдена')}\n"
            copy_text += f"Срок действия: {mchd.get('expiry_date', 'Не найден')}\n"
            copy_text += f"ФИО представителя: {mchd.get('full_name', 'Не найдено')}\n"
            copy_text += f"ИНН представителя: {mchd.get('inn', 'Не найден')}\n"
            copy_text += f"СНИЛС представителя: {mchd.get('snils', 'Не найден')}\n"
            copy_text += (
                f"Дата рождения представителя: {mchd.get('birth_date', 'Не найдена')}\n"
            )
            copy_text += f"Статус: {mchd.get('status', 'Не определен')}\n\n"
            if has_issuer_data:
                copy_text += "📌 ОРГАНИЗАЦИЯ-ДОВЕРИТЕЛЬ\n"
                copy_text += "-" * 40 + "\n"
                copy_text += (
                    f"Наименование: {mchd.get('issuer_org_name', 'Не найдено')}\n"
                )
                copy_text += f"ИНН: {mchd.get('issuer_org_inn', 'Не найден')}\n"
                copy_text += f"КПП: {mchd.get('issuer_org_kpp', 'Не найден')}\n"
                copy_text += f"ОГРН: {mchd.get('issuer_org_ogrn', 'Не найден')}\n"
                copy_text += f"Адрес: {mchd.get('issuer_org_address', 'Не найден')}\n\n"
                copy_text += "📌 УПОЛНОМОЧЕННОЕ ЛИЦО\n"
                copy_text += "-" * 40 + "\n"
                copy_text += (
                    f"ФИО: {mchd.get('issuer_person_fullname', 'Не найдено')}\n"
                )
                copy_text += (
                    f"Должность: {mchd.get('issuer_person_position', 'Не найдена')}\n"
                )
                copy_text += f"ИНН: {mchd.get('issuer_person_inn', 'Не найден')}\n"
                copy_text += f"СНИЛС: {mchd.get('issuer_person_snils', 'Не найден')}\n"
                copy_text += f"Дата рождения: {mchd.get('issuer_person_birthdate', 'Не найдена')}\n\n"
            copy_text += "📌 КОДЫ ПОЛНОМОЧИЙ\n"
            copy_text += "-" * 40 + "\n"
            if auth_codes:
                for code in auth_codes:
                    copy_text += f"  • {code}\n"
            else:
                copy_text += "Нет данных\n"
            copy_text += "\n" + "=" * 50 + "\n"
            copy_text += (
                f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            )
            pyperclip.copy(copy_text)
            messagebox.showinfo("Успех", "Все данные скопированы в буфер обмена")

        btn_copy = tk.Button(
            btn_frame,
            text="📋 КОПИРОВАТЬ ВСЕ ДАННЫЕ",
            command=copy_all_data,
            font=(UI_FONT, 10, "bold"),
            bg=BUTTON_COLOR,
            fg="white",
            cursor="hand2",
            padx=20,
            pady=8,
            relief="flat",
            bd=0,
        )
        btn_copy.pack(side=tk.LEFT, padx=5)

        btn_close = tk.Button(
            btn_frame,
            text="❌ ЗАКРЫТЬ",
            command=data_window.destroy,
            font=(UI_FONT, 10),
            bg=ACCENT_COLOR,
            fg="white",
            cursor="hand2",
            padx=20,
            pady=8,
            relief="flat",
            bd=0,
        )
        btn_close.pack(side=tk.RIGHT, padx=5)

        def on_enter_btn(btn, color):
            btn.config(bg=color)

        def on_leave_btn(btn, color):
            btn.config(bg=color)

        btn_copy.bind("<Enter>", lambda e: on_enter_btn(btn_copy, BUTTON_HOVER))
        btn_copy.bind("<Leave>", lambda e: on_leave_btn(btn_copy, BUTTON_COLOR))
        btn_close.bind("<Enter>", lambda e: on_enter_btn(btn_close, "#5a6268"))
        btn_close.bind("<Leave>", lambda e: on_leave_btn(btn_close, ACCENT_COLOR))

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def on_destroy():
            canvas.unbind_all("<MouseWheel>")
            data_window.destroy()

        data_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def on_search(self, *args):
        query = self.search_var.get().lower()
        if not query:
            self.filtered_data = self.mchd_data.copy()
            self.search_result_label.config(text="")
        else:
            self.filtered_data = []
            for mchd in self.mchd_data:
                full_name = mchd.get("full_name", "").lower()
                if query in full_name:
                    self.filtered_data.append(mchd)
            self.search_result_label.config(
                text=f"Найдено: {len(self.filtered_data)} из {len(self.mchd_data)}"
            )
        self.refresh_table()

    def clear_search(self):
        self.search_var.set("")
        self.filtered_data = self.mchd_data.copy()
        self.search_result_label.config(text="")
        self.refresh_table()

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.populate_table_with_data(self.filtered_data)

    def sort_column(self, col):
        data = [
            (self.tree.set(child, col), child) for child in self.tree.get_children("")
        ]
        if col in ("Дата выдачи", "Срок действия"):

            def parse_date(date_str):
                try:
                    if date_str and date_str not in ("Не найдена", "Не найден", ""):
                        return datetime.strptime(date_str, "%d.%m.%Y")
                except:
                    pass
                return datetime.min

            data.sort(key=lambda x: parse_date(x[0]), reverse=self.sort_reverse[col])
        elif col == "ФИО":
            data.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse[col])
        elif col == "Коды полномочий":
            data.sort(
                key=lambda x: len(x[0]) if x[0] != "Нет кодов" else 0,
                reverse=self.sort_reverse[col],
            )
        else:
            data.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse[col])
        for index, (val, child) in enumerate(data):
            self.tree.move(child, "", index)
        self.sort_reverse[col] = not self.sort_reverse[col]

    def check_for_duplicates(self):
        persons = {}
        for mchd in self.mchd_data:
            person = mchd.get("full_name", "Неизвестно")
            if person not in persons:
                persons[person] = []
            persons[person].append(mchd)
        duplicates = {
            p: m for p, m in persons.items() if len(m) > 1 and p != "Не найдено"
        }
        if duplicates:
            msg = "Найдены люди с несколькими МЧД:\n"
            for person, mchds in duplicates.items():
                msg += f"• {person} - {len(mchds)} МЧД\n"
            msg += "\nВы можете выделить их в таблице и нажать 'Объединить выбранные МЧД' или 'Просмотр кодов'"
            info_label = ttk.Label(
                self.duplicate_frame,
                text=msg,
                font=(UI_FONT, 9),
                foreground=MCHD_COLOR,
                wraplength=1300,
            )
            info_label.pack()

    def populate_table(self):
        self.populate_table_with_data(self.mchd_data)

    def populate_table_with_data(self, data):
        persons = {}
        for mchd in self.mchd_data:
            person = mchd.get("full_name", "Неизвестно")
            if person not in persons:
                persons[person] = []
            persons[person].append(mchd)
        duplicate_names = {
            p for p, m in persons.items() if len(m) > 1 and p != "Не найдено"
        }
        for mchd in data:
            tags = []
            if mchd.get("status") == "Просрочен":
                tags.append("expired")
            elif mchd.get("status") and "Истекает" in mchd.get("status", ""):
                tags.append("warning")
            else:
                tags.append("normal")
            person = mchd.get("full_name", "")
            if person in duplicate_names:
                tags.append("duplicate_name")
            auth_codes = ", ".join(mchd.get("authority_codes", []))
            if len(auth_codes) > 50:
                auth_codes = auth_codes[:50] + "..."
            if not mchd.get("authority_codes"):
                auth_codes = "Нет кодов"
            self.tree.insert(
                "",
                tk.END,
                values=(
                    os.path.basename(mchd.get("file_name", "")),
                    mchd.get("doc_number", ""),
                    mchd.get("issue_date", ""),
                    mchd.get("expiry_date", ""),
                    mchd.get("full_name", ""),
                    auth_codes,
                    mchd.get("status", ""),
                ),
                tags=tuple(tags),
            )

    def on_select(self, event):
        self.selected_items = self.tree.selection()
        count = len(self.selected_items)
        self.selected_info_label.config(text=f"Выбрано: {count} МЧД")
        selected_mchd = self.get_selected_mchd_objects()

        if count >= 1:
            persons = set(m.get("full_name", "") for m in selected_mchd)
            if count >= 2 and len(persons) == 1:
                self.merge_btn.config(state=tk.NORMAL)
                self.view_auth_btn.config(state=tk.NORMAL)
                self.view_personal_btn.config(state=tk.DISABLED)
                self.person_info_label.config(
                    text=f"ФИО: {list(persons)[0]} (можно объединить)"
                )
            elif count == 1:
                self.merge_btn.config(state=tk.DISABLED)
                self.view_auth_btn.config(state=tk.NORMAL)
                self.view_personal_btn.config(state=tk.NORMAL)
                self.person_info_label.config(
                    text=f"ФИО: {list(persons)[0] if persons else ''}"
                )
            else:
                self.merge_btn.config(state=tk.DISABLED)
                self.view_auth_btn.config(state=tk.NORMAL)
                self.view_personal_btn.config(state=tk.DISABLED)
                if len(persons) > 1:
                    self.person_info_label.config(
                        text="Выбраны разные люди! Объединение невозможно"
                    )
                else:
                    self.person_info_label.config(
                        text=f"ФИО: {list(persons)[0] if persons else ''}"
                    )
        else:
            self.merge_btn.config(state=tk.DISABLED)
            self.view_auth_btn.config(state=tk.DISABLED)
            self.view_personal_btn.config(state=tk.DISABLED)
            self.person_info_label.config(text="")
        self.update_codes_list()

    def get_selected_mchd_objects(self):
        selected_mchd = []
        for item in self.selected_items:
            values = self.tree.item(item)["values"]
            if not values:
                continue
            file_name = values[0]
            for mchd in self.filtered_data:
                if os.path.basename(mchd.get("file_name", "")) == file_name:
                    selected_mchd.append(mchd)
                    break
        return selected_mchd

    def view_merged_authorities(self):
        selected_mchd = self.get_selected_mchd_objects()
        if not selected_mchd:
            messagebox.showwarning("Внимание", "Выберите МЧД для просмотра")
            return
        merged_data = MCHDMerger.get_merged_authorities(selected_mchd)
        if merged_data:
            AuthoritiesViewWindow(self.window, merged_data)
        else:
            messagebox.showerror("Ошибка", "Не удалось получить данные о полномочиях")

    def update_codes_list(self):
        self.codes_listbox.delete(0, tk.END)
        if not self.selected_items:
            self.codes_listbox.insert(tk.END, "Выберите МЧД в таблице")
            return
        selected_mchd = self.get_selected_mchd_objects()
        all_codes = set()
        for mchd in selected_mchd:
            codes = mchd.get("authority_codes", [])
            all_codes.update(codes)
        if all_codes:
            for code in sorted(all_codes):
                self.codes_listbox.insert(tk.END, code)
            self.codes_listbox.insert(tk.END, "")
            self.codes_listbox.insert(
                tk.END, f"ВСЕГО УНИКАЛЬНЫХ КОДОВ: {len(all_codes)}"
            )
        else:
            self.codes_listbox.insert(tk.END, "Нет кодов полномочий")

    def merge_selected(self):
        if len(self.selected_items) < 2:
            messagebox.showwarning("Внимание", "Выберите минимум 2 МЧД для объединения")
            return
        selected_mchd = self.get_selected_mchd_objects()
        if len(selected_mchd) < 2:
            messagebox.showerror("Ошибка", "Не удалось найти выбранные файлы")
            return
        persons = set(m.get("full_name", "") for m in selected_mchd)
        if len(persons) > 1:
            messagebox.showerror("Ошибка", "Нельзя объединять МЧД разных людей!")
            return
        merged_data = MCHDMerger.get_merged_authorities(selected_mchd)
        response = messagebox.askyesnocancel(
            "Объединение МЧД",
            f"Выбрано {len(selected_mchd)} МЧД для {list(persons)[0]}\n"
            f"Уникальных кодов: {merged_data.get('unique_codes_count', 0)}\n\n"
            "Нажмите 'Да' чтобы создать неподписанный черновик XML,\n"
            "'Нет' чтобы только просмотреть коды,\n"
            "'Отмена' для отмены.",
        )
        if response is None:
            return
        if response:
            person_name = list(persons)[0].replace(" ", "_")
            default_name = f"Объединенная_МЧД_{person_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xml",
                filetypes=[("XML файлы", "*.xml"), ("Все файлы", "*.*")],
                initialdir=os.path.dirname(selected_mchd[0].get("file_name", "")),
                initialfile=default_name,
                title="Сохранить объединенную МЧД",
            )
            if not save_path:
                return
            try:
                result = MCHDMerger.merge_mchd_files(selected_mchd, save_path)
            except (ValueError, OSError) as exc:
                messagebox.showerror("Объединение МЧД", str(exc))
                return
            if result and os.path.exists(result):
                messagebox.showinfo(
                    "Успех",
                    f"Создан неподписанный черновик МЧД.\n\n"
                    f"ФИО: {list(persons)[0]}\n"
                    f"Всего уникальных кодов: {merged_data.get('unique_codes_count', 0)}\n"
                    f"Файл сохранен:\n{result}",
                )
                if messagebox.askyesno(
                    "Открыть папку", "Открыть папку с объединенным файлом?"
                ):
                    open_path(os.path.dirname(result))
            else:
                messagebox.showerror("Ошибка", "Не удалось объединить МЧД")
        else:
            if merged_data:
                AuthoritiesViewWindow(self.window, merged_data)

    def copy_selected_codes(self):
        codes = []
        for i in range(self.codes_listbox.size()):
            text = self.codes_listbox.get(i)
            if (
                text
                and not text.startswith("ВСЕГО")
                and text != "Нет кодов полномочий"
                and text != "Выберите МЧД в таблице"
                and text != ""
            ):
                codes.append(text)
        if codes:
            pyperclip.copy("\n".join(codes))
            messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")
        else:
            messagebox.showwarning("Внимание", "Нет кодов для копирования")

    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item)["values"]
        if not values:
            return
        file_name = values[0]
        for mchd in self.filtered_data:
            if os.path.basename(mchd.get("file_name", "")) == file_name:
                full_path = mchd.get("file_name")
                if full_path and os.path.exists(full_path):
                    try:
                        open_path(full_path)
                    except Exception as e:
                        messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
                break

    def export_to_excel(self):
        if not self.filtered_data:
            messagebox.showerror("Ошибка", "Нет данных для экспорта!")
            return
        try:
            default_name = (
                f"mchd_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
                initialdir=load_settings().export_folder,
                initialfile=default_name,
                title="Сохранить отчет МЧД",
            )
            if not save_path:
                return
            from certificate_analyzer.infrastructure.reports.excel_exporter import (
                ExcelReportExporter,
            )

            ExcelReportExporter().export_rows(
                self.filtered_data, save_path, "Отчет по МЧД"
            )
            messagebox.showinfo("Успех", f"Отчет сохранен:\n{save_path}")
        except Exception as e:
            messagebox.showerror(
                "Ошибка", f"Не удалось экспортировать в Excel:\n{str(e)}"
            )
