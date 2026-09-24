import tkinter as tk
from tkinter import ttk

import matplotlib

from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_COLOR,
    BUTTON_HOVER,
    CARD_BG_COLOR,
    CARD_BORDER_COLOR,
    CARD_TITLE_COLOR,
    CARD_VALUE_COLOR,
    EXPIRED_COLOR,
    HEADER_COLOR,
    MCHD_COLOR,
    NORMAL_COLOR,
    SIDEBAR_COLOR,
    SIDEBAR_TEXT_COLOR,
    TEXT_COLOR,
    UI_FONT,
    WARNING_COLOR,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.infrastructure.mchd.xml_parser import MCHDParser
from certificate_analyzer.presentation.gui.controllers.certificate_controller import (
    CertificateController,
)
from certificate_analyzer.presentation.gui.controllers.mchd_controller import (
    MchdController,
)
from certificate_analyzer.presentation.gui.controllers.settings_controller import (
    SettingsController,
)
from certificate_analyzer.presentation.gui.presenters.certificate_presenter import (
    CertificatePresenter,
)
from certificate_analyzer.presentation.gui.views.certificate_view import CertificateView
from certificate_analyzer.presentation.gui.views.history_view import NotificationHistory
from certificate_analyzer.presentation.gui.views.normative_view import NormativeWindow
from certificate_analyzer.presentation.gui.widgets.toast import ToastNotification


class CertificateAnalyzerApp(
    SettingsController, CertificateController, MchdController, CertificateView
):
    def __init__(self, root):
        self.root = root
        self.root.title("Анализатор сертификатов и МЧД")
        self.root.geometry("1600x900")
        self.root.configure(bg=BG_COLOR)
        self.current_folder_key = "📁 Сотрудники"
        self.current_display_path = ""
        self.recent_folders = []
        self.setup_styles()
        app = create_application()
        self.core = app.certificates
        self.core.settings = app.settings
        self.core.loaded_files = []
        self.core.errors = {}
        self.core.certificates = []
        self.certificate_presenter = CertificatePresenter(view=self, model=self.core)
        self.default_folders = dict(self.core.settings.folders)
        self.cert_data_cache = []
        self.mchd_data_cache = []
        self.mchd_parser = MCHDParser()
        self.current_display_mode = "certificates"
        self.search_active = False
        self.current_search_query = ""
        self.date_filter_active = False
        self.date_from = None
        self.date_to = None
        self._notification_shown = False
        self.chart_type = "pie"
        self.open_windows = {}
        self.notification_history = NotificationHistory(root)
        self.setup_ui()
        self.load_default_folder()
        self.setup_folder_menu()
        self.setup_push_notifications()
        self.root.bind("<Configure>", self.on_window_resize)
        self.tree.bind("<Double-1>", self.on_item_double_click)
        if self.cal:
            self.cal.bind("<<CalendarMonthChanged>>", self.on_month_change)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.notification_manager.stop_monitoring()
        plt.close("all")
        self.root.destroy()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            ".", background=BG_COLOR, foreground=TEXT_COLOR, font=(UI_FONT, 9)
        )
        self.root.configure(bg=BG_COLOR)
        style.configure("TFrame", background=BG_COLOR)
        style.configure(
            "TLabelFrame",
            background=HEADER_COLOR,
            foreground=TEXT_COLOR,
            font=(UI_FONT, 10, "bold"),
            borderwidth=2,
            relief="groove",
        )
        style.configure(
            "TLabelFrame.Label", background=HEADER_COLOR, foreground=TEXT_COLOR
        )
        style.configure(
            "TButton",
            background=BUTTON_COLOR,
            foreground="white",
            font=(UI_FONT, 9, "bold"),
            borderwidth=0,
            padding=8,
        )
        style.map(
            "TButton",
            background=[("active", BUTTON_HOVER), ("pressed", BUTTON_HOVER)],
            foreground=[("active", "white")],
        )
        style.configure(
            "Accent.TButton",
            background=BUTTON_COLOR,
            foreground="white",
            font=(UI_FONT, 9, "bold"),
            borderwidth=0,
            padding=8,
        )
        style.map(
            "Accent.TButton",
            background=[("active", BUTTON_HOVER), ("pressed", BUTTON_HOVER)],
            foreground=[("active", "white")],
        )
        style.configure(
            "Danger.TButton",
            background="#D9534F",
            foreground="white",
            font=(UI_FONT, 9, "bold"),
            borderwidth=0,
            padding=8,
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#c9302c"), ("pressed", "#c9302c")],
            foreground=[("active", "white")],
        )
        style.configure(
            "Secondary.TButton",
            background="#e0e0e0",
            foreground="black",
            font=(UI_FONT, 9),
            borderwidth=0,
            padding=8,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#d5d5d5"), ("pressed", "#d5d5d5")],
            foreground=[("active", "black")],
        )
        style.configure(
            "Sidebar.TButton",
            background=SIDEBAR_COLOR,
            foreground=SIDEBAR_TEXT_COLOR,
            font=(UI_FONT, 10),
            borderwidth=0,
            padding=8,
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", "#34495e"), ("pressed", "#2c3e50")],
            foreground=[("active", "white")],
        )
        style.configure(
            "TEntry",
            fieldbackground="white",
            foreground=TEXT_COLOR,
            insertcolor=TEXT_COLOR,
            bordercolor="#e1e8ed",
            borderwidth=1,
            padding=5,
            font=(UI_FONT, 9),
        )
        style.configure(
            "Treeview",
            background="white",
            foreground=TEXT_COLOR,
            fieldbackground="white",
            rowheight=28,
            borderwidth=0,
            font=(UI_FONT, 9),
        )
        style.configure(
            "Treeview.Heading",
            background=ACCENT_COLOR,
            foreground="white",
            font=(UI_FONT, 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", BUTTON_COLOR)],
            foreground=[("selected", "white")],
        )
        style.configure(
            "Card.TFrame",
            background=CARD_BG_COLOR,
            borderwidth=1,
            relief="solid",
            bordercolor=CARD_BORDER_COLOR,
        )
        style.configure(
            "CardTitle.TLabel",
            font=(UI_FONT, 9),
            foreground=CARD_TITLE_COLOR,
            background=CARD_BG_COLOR,
        )
        style.configure(
            "CardValue.TLabel",
            font=(UI_FONT, 14),
            foreground=CARD_VALUE_COLOR,
            background=CARD_BG_COLOR,
        )
        style.configure("Sidebar.TFrame", background=SIDEBAR_COLOR)
        style.configure(
            "TCheckbutton",
            background=BG_COLOR,
            foreground=TEXT_COLOR,
            font=(UI_FONT, 9),
        )

    def close_window(self, key, window):
        self.open_windows[key] = None
        window.destroy()

    def show_window(self, window_key, window_class, *args, **kwargs):
        if (
            window_key in self.open_windows
            and self.open_windows[window_key] is not None
        ):
            try:
                if self.open_windows[window_key].winfo_exists():
                    self.open_windows[window_key].lift()
                    self.open_windows[window_key].focus_force()
                    return self.open_windows[window_key]
            except:
                pass
        window = window_class(*args, **kwargs)
        self.open_windows[window_key] = window
        if hasattr(window, "protocol"):

            def on_close():
                self.open_windows[window_key] = None
                if hasattr(window, "destroy"):
                    window.destroy()

            window.protocol("WM_DELETE_WINDOW", on_close)
        return window

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        sidebar_frame = ttk.Frame(main_frame, width=220, style="Sidebar.TFrame")
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar_frame.pack_propagate(False)

        logo_frame = ttk.Frame(sidebar_frame, style="Sidebar.TFrame")
        logo_frame.pack(fill=tk.X, pady=(10, 20))
        ttk.Label(logo_frame, text="🔐", font=(UI_FONT, 28), foreground="white", background=SIDEBAR_COLOR).pack(pady=(10, 0))
        ttk.Label(logo_frame, text="Анализатор", font=(UI_FONT, 14, "bold"), foreground="white", background=SIDEBAR_COLOR).pack()

        # Navigation
        from certificate_analyzer.presentation.gui.styles import SECONDARY_TEXT_COLOR
        ttk.Label(sidebar_frame, text="ОСНОВНОЕ", font=(UI_FONT, 8, "bold"), foreground=SECONDARY_TEXT_COLOR, background=SIDEBAR_COLOR).pack(anchor=tk.W, padx=15, pady=(10, 5))
        main_nav = [
            ("📊 Обзор", lambda: None),
            ("🪪 Сертификаты", lambda: self.switch_folder("📁 Сотрудники")),
            ("📑 МЧД", self.scan_mchd_folder),
            ("👥 Сотрудники", lambda: self.switch_folder("📁 Руководство")),
            ("📈 Отчёты", self.export_menu)
        ]
        for text, cmd in main_nav:
            btn = ttk.Button(sidebar_frame, text=text, command=cmd, style="Sidebar.TButton")
            btn.pack(fill=tk.X, padx=10, pady=2, ipady=4)

        ttk.Label(sidebar_frame, text="СИСТЕМА", font=(UI_FONT, 8, "bold"), foreground=SECONDARY_TEXT_COLOR, background=SIDEBAR_COLOR).pack(anchor=tk.W, padx=15, pady=(20, 5))
        sys_nav = [
            ("🔔 Уведомления", self.show_notification_settings),
            ("⚙️ Настройки", self.show_folder_settings)
        ]
        for text, cmd in sys_nav:
            btn = ttk.Button(sidebar_frame, text=text, command=cmd, style="Sidebar.TButton")
            btn.pack(fill=tk.X, padx=10, pady=2, ipady=4)
        
        ttk.Frame(sidebar_frame, style="Sidebar.TFrame").pack(fill=tk.BOTH, expand=True) # spacer
        
        bottom_nav = [
            ("📚 Нормативка", self.show_normative),
            ("ℹ️ О программе", self.show_about),
        ]
        for text, cmd in bottom_nav:
            btn = ttk.Button(sidebar_frame, text=text, command=cmd, style="Sidebar.TButton")
            btn.pack(fill=tk.X, padx=10, pady=2, ipady=4)
        
        # Content Area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Top Bar
        top_bar = ttk.Frame(content_frame)
        top_bar.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(top_bar, text="Сертификаты", font=(UI_FONT, 14, "bold")).pack(side=tk.LEFT)
        
        self.folder_path = tk.StringVar()
        ttk.Entry(top_bar, textvariable=self.folder_path, width=40).pack(side=tk.LEFT, padx=(20, 10))
        ttk.Button(top_bar, text="Выбрать", command=self.select_folder, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(top_bar, text="Обновить", command=self.refresh_all, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        
        # Stats Cards
        from certificate_analyzer.presentation.gui.widgets.stat_card import StatCard
        cards_frame = ttk.Frame(content_frame)
        cards_frame.pack(fill=tk.X, pady=(0, 15))
        self.card_total = StatCard(cards_frame, "Всего", "0")
        self.card_total.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.card_normal = StatCard(cards_frame, "Активны", "0", NORMAL_COLOR)
        self.card_normal.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.card_warning = StatCard(cards_frame, "Истекают", "0", WARNING_COLOR)
        self.card_warning.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.card_expired = StatCard(cards_frame, "Просрочены", "0", EXPIRED_COLOR)
        self.card_expired.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Filters
        filter_bar = ttk.Frame(content_frame)
        filter_bar.pack(fill=tk.X, pady=(0, 10))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        ttk.Entry(filter_bar, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(filter_bar, text="Статус ▼", style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_bar, text="Срок ▼", command=self.show_date_filter, style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_bar, text="Подразделение ▼", style="TButton").pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_bar, text="🗑 Удалить", command=self.delete_selected, style="Danger.TButton").pack(side=tk.RIGHT)

        # Table
        from certificate_analyzer.presentation.gui.widgets.certificate_table import (
            CertificateTable,
        )
        self.table = CertificateTable(content_frame)
        self.table.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.tree = self.table.tree
        self.columns = self.table.columns

        # Details Panel
        from certificate_analyzer.presentation.gui.widgets.certificate_details import (
            CertificateDetails,
        )
        self.details_panel = CertificateDetails(content_frame)
        self.details_panel.pack(fill=tk.X)
        self.table.set_on_select_callback(self._on_table_select)

        # Status Bar
        status_bar = ttk.Frame(content_frame)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_bar, variable=self.progress_var, maximum=100)
        
        self.status_label = ttk.Label(status_bar, text="Готово", font=(UI_FONT, 9), foreground=SECONDARY_TEXT_COLOR)
        self.status_label.pack(side=tk.LEFT)
        self.search_result_label = ttk.Label(status_bar, text="", font=(UI_FONT, 9), foreground=SECONDARY_TEXT_COLOR)
        self.search_result_label.pack(side=tk.RIGHT)

        self.sort_reverse = {col: False for col in self.columns}
        self.folder_history = []
        
        self.cal = None
        self.figure_status = None
        self.current_folder_label = tk.Label() # Dummy for compat

    def _on_table_select(self, values):
        if not values:
            self.details_panel.clear()
            return
        details = {
            "Subject": values[0],
            "Путь": values[1],
            "Email": values[6] if len(values) > 6 else "",
            "Телефон": values[5] if len(values) > 5 else "",
        }
        self.details_panel.update_details(details)

    def display_certificates(self, data_list):
        self.table.clear()
        if not data_list:
            self.table.insert_row(["Сертификаты не найдены"] * len(self.columns))
            return
        
        for item in data_list:
            status = item.get("status", "")
            tags = ()
            if "Просрочен" in status:
                tags = ("expired",)
            elif "Истекает" in status:
                tags = ("warning",)
            elif status:
                tags = ("normal",)

            row = (
                item.get("type", "—"),
                item.get("file_name", "—"),
                item.get("valid_from", "—"),
                item.get("valid_to", "—"),
                item.get("subject_cn", "—"),
                item.get("serial_number", "—"),
                item.get("email", "—"),
                item.get("office_number", "—"),
                item.get("department", "—"),
                item.get("phone", "—"),
                status,
            )
            # Use only the columns that match new UI
            new_row = (
                item.get("subject_cn", "—"),
                item.get("file_name", "—"),
                item.get("valid_to", "—"),
                item.get("days_left", "—"),
                item.get("department", "—"),
                item.get("phone", "—"),
                status,
            )
            self.table.insert_row(new_row, tags=tags)
            
    def update_stats_view(self, total, expired, warning, normal):
        self.card_total.set_value(str(total))
        self.card_expired.set_value(str(expired))
        self.card_warning.set_value(str(warning))
        self.card_normal.set_value(str(normal))
        
    def set_loaded_files(self, file_paths):
        pass # Not using listbox in new design
        
    def set_search_result_text(self, text):
        self.search_result_label.config(text=text)
        
    def clear_search_input(self):
        self.search_var.set("")
        
    def remove_tree_items(self, item_ids):
        for item_id in item_ids:
            self.table.tree.delete(item_id)
            
    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            frame = tk.Frame(tooltip, bg="#2c3e50", padx=8, pady=4)
            frame.pack()
            label = tk.Label(
                frame,
                text=text,
                font=(UI_FONT, 9),
                bg="#2c3e50",
                fg="white",
                wraplength=300,
            )
            label.pack()

            def hide_tooltip():
                tooltip.destroy()

            widget.tooltip = tooltip
            widget.after(3000, hide_tooltip)
            widget.bind("<Leave>", lambda e: hide_tooltip())

        widget.bind("<Enter>", show_tooltip)

    def show_notification(self, message, notification_type="info", duration=4000):
        try:
            self.notification_history.add_notification(message, notification_type)
            ToastNotification(self.root, message, duration, notification_type)
        except Exception as e:
            print(f"Ошибка показа уведомления: {e}")

    def show_notification_history(self):
        self.notification_history.show_history_window()

    def show_normative(self):
        self.show_window("normative", NormativeWindow, self.root)

    def show_about(self):
        if "about" in self.open_windows and self.open_windows["about"] is not None:
            try:
                if self.open_windows["about"].winfo_exists():
                    self.open_windows["about"].lift()
                    self.open_windows["about"].focus_force()
                    return
            except:
                pass

        about_window = tk.Toplevel(self.root)
        about_window.title("О программе")
        about_window.geometry("550x500")
        about_window.configure(bg=BG_COLOR)
        about_window.resizable(False, False)
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (550 // 2)
        y = (about_window.winfo_screenheight() // 2) - (500 // 2)
        about_window.geometry(f"550x500+{x}+{y}")
        self.open_windows["about"] = about_window

        main_frame = tk.Frame(about_window, bg=CARD_BG_COLOR, relief="flat", bd=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        header_bar = tk.Frame(main_frame, bg=MCHD_COLOR, height=80)
        header_bar.pack(fill=tk.X)
        header_bar.pack_propagate(False)

        tk.Label(
            header_bar, text="🔐", font=(UI_FONT, 32), bg=MCHD_COLOR, fg="white"
        ).place(x=20, y=20)
        tk.Label(
            header_bar,
            text="Анализатор сертификатов и МЧД",
            font=(UI_FONT, 16, "bold"),
            bg=MCHD_COLOR,
            fg="white",
        ).place(x=80, y=28)
        tk.Label(
            header_bar,
            text="Версия 3.1",
            font=(UI_FONT, 10),
            bg=MCHD_COLOR,
            fg="#e1bee7",
        ).place(x=80, y=55)

        body_frame = tk.Frame(main_frame, bg=CARD_BG_COLOR)
        body_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        canvas_frame = tk.Frame(body_frame, bg=CARD_BG_COLOR)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg=CARD_BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg=CARD_BG_COLOR)
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        desc_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        desc_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            desc_frame,
            text="📋 ОПИСАНИЕ",
            font=(UI_FONT, 11, "bold"),
            fg=MCHD_COLOR,
            bg=CARD_BG_COLOR,
        ).pack(anchor=tk.W, pady=(0, 8))
        description = """Программа для анализа сертификатов электронной подписи
 и машиночитаемых доверенностей (МЧД)."""
        tk.Label(
            desc_frame,
            text=description,
            font=(UI_FONT, 10),
            fg=TEXT_COLOR,
            bg=CARD_BG_COLOR,
            justify=tk.LEFT,
            wraplength=460,
        ).pack(anchor=tk.W, pady=(0, 10))

        functions_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        functions_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            functions_frame,
            text="⚡ ОСНОВНЫЕ ФУНКЦИИ",
            font=(UI_FONT, 11, "bold"),
            fg=MCHD_COLOR,
            bg=CARD_BG_COLOR,
        ).pack(anchor=tk.W, pady=(0, 8))
        functions = [
            "• Сканирование и анализ сертификатов (.cer, .crt, .der, .pem)",
            "• Анализ XML файлов МЧД",
            "• Объединение нескольких МЧД одного лица",
            "• Отслеживание сроков действия",
            "• Экспорт отчетов в Excel и PDF",
            "• Календарь окончания сертификатов",
            "• Push-уведомления о просроченных сертификатах",
            "• 8 типов диаграмм для визуализации",
            "• Загрузка справочника телефонов для поиска контактов",
        ]
        for func in functions:
            tk.Label(
                functions_frame,
                text=func,
                font=(UI_FONT, 10),
                fg=TEXT_COLOR,
                bg=CARD_BG_COLOR,
                anchor=tk.W,
            ).pack(anchor=tk.W, pady=2)

        dev_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        dev_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            dev_frame,
            text="👨‍💻 РАЗРАБОТКА",
            font=(UI_FONT, 11, "bold"),
            fg=MCHD_COLOR,
            bg=CARD_BG_COLOR,
        ).pack(anchor=tk.W, pady=(0, 8))
        dev_info = """Разработано для внутреннего использования.
 По вопросам и предложениям обращаться в ИБ-отдел."""
        tk.Label(
            dev_frame,
            text=dev_info,
            font=(UI_FONT, 10),
            fg=TEXT_COLOR,
            bg=CARD_BG_COLOR,
            justify=tk.LEFT,
            wraplength=460,
        ).pack(anchor=tk.W)

        copyright_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        copyright_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Label(
            copyright_frame,
            text="© 2026 | Все права защищены",
            font=(UI_FONT, 9, "italic"),
            fg=ACCENT_COLOR,
            bg=CARD_BG_COLOR,
        ).pack(anchor=tk.CENTER)

        btn_frame = tk.Frame(main_frame, bg=CARD_BG_COLOR, pady=15)
        btn_frame.pack(fill=tk.X)
        close_btn = tk.Button(
            btn_frame,
            text="❌ ЗАКРЫТЬ",
            command=lambda: self.close_window("about", about_window),
            font=(UI_FONT, 10, "bold"),
            bg=BUTTON_COLOR,
            fg="white",
            cursor="hand2",
            padx=25,
            pady=8,
            relief="flat",
            bd=0,
        )
        close_btn.pack()

        def on_enter(e):
            close_btn.config(bg=BUTTON_HOVER)

        def on_leave(e):
            close_btn.config(bg=BUTTON_COLOR)

        close_btn.bind("<Enter>", on_enter)
        close_btn.bind("<Leave>", on_leave)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def on_destroy():
            canvas.unbind_all("<MouseWheel>")
            self.open_windows["about"] = None
            about_window.destroy()

        about_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def create_card(self, parent, title, value, color=None):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10))
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor=tk.W)
        value_label = ttk.Label(card, text=value, style="CardValue.TLabel")
        value_label.pack(anchor=tk.W)
        if color:
            value_label.configure(foreground=color)
        return value_label

    def export_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Экспорт в Excel", command=self.export_to_excel_gui)
        menu.add_command(label="Экспорт в PDF", command=self.export_to_pdf_gui)
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def service_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Установить службу", command=self.install_service)
        menu.add_command(label="Удалить службу", command=self.remove_service)
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def show_help(self):
        if "help" in self.open_windows and self.open_windows["help"] is not None:
            try:
                if self.open_windows["help"].winfo_exists():
                    self.open_windows["help"].lift()
                    self.open_windows["help"].focus_force()
                    return
            except:
                pass

        help_text = """Анализатор сертификатов и МЧД - Справка

 ОСНОВНЫЕ ФУНКЦИИ:

 1. 📁 РАБОТА С ПАПКАМИ
    • Сотрудники - сканирование сертификатов сотрудников
    • Руководство - сканирование сертификатов руководства
    • МЧД - сканирование XML файлов МЧД

 2. 📊 АНАЛИЗ СЕРТИФИКАТОВ    • Автоматическое определение статуса
    • Извлечение кабинета и подразделения из OU
    • Автоматический поиск телефона из справочника

 3. 📊 АНАЛИЗ МЧД
    • Номер доверенности, даты, ФИО, коды полномочий
    • Подсветка людей с несколькими МЧД
    • Поиск по фамилии, сортировка

 4. 🔄 ОБЪЕДИНЕНИЕ МЧД
    • Выберите несколько МЧД одного человека
    • Нажмите "Объединить выбранные МЧД"

 5. 🔍 ПОИСК И ФИЛЬТРАЦИЯ
    • Поиск по всем полям
    • Фильтр по диапазону дат

 6. 📅 КАЛЕНДАРЬ
    • Светло-розовый - просроченные
    • Светло-желтый - истекающие
    • Светло-зеленый - активные

 7. 📊 ДИАГРАММЫ
    • 8 типов диаграмм на выбор

 8. 📤 ЭКСПОРТ
    • Excel и PDF с графиком

 9. 🔔 PUSH-УВЕДОМЛЕНИЯ
    • Уведомления в системный трей Windows

10. 📞 СПРАВОЧНИК ТЕЛЕФОНОВ
    • Загрузка справочника из файла .docx или .txt
    • Автоматический поиск телефона по кабинету, ФИО или подразделению
    • Отображение найденного телефона в общем списке
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Справка")
        help_window.geometry("750x650")
        help_window.configure(bg=BG_COLOR)
        self.open_windows["help"] = help_window

        frame = ttk.Frame(help_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        text_widget = tk.Text(
            frame,
            wrap=tk.WORD,
            font=(UI_FONT, 10),
            background="white",
            foreground=TEXT_COLOR,
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert("1.0", help_text)
        text_widget.config(state="disabled")
        ttk.Button(
            frame,
            text="Закрыть",
            command=lambda: self.close_window("help", help_window),
            style="Accent.TButton",
        ).pack(pady=(10, 0))

        def on_destroy():
            self.open_windows["help"] = None
            help_window.destroy()

        help_window.protocol("WM_DELETE_WINDOW", on_destroy)
