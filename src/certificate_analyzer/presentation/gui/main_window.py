import tkinter as tk
from tkinter import ttk
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
    EXPIRED_TEXT,
    GRAPH_EXPIRED,
    GRAPH_NORMAL,
    GRAPH_WARNING,
    HEADER_COLOR,
    MCHD_COLOR,
    NORMAL_COLOR,
    NORMAL_TEXT,
    SIDEBAR_COLOR,
    SIDEBAR_TEXT_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
    WARNING_TEXT,
    UI_FONT,
    MONO_FONT,
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import Calendar
from certificate_analyzer.application.services.certificate_service import (
    CertificateAnalyzerCore,
)
from certificate_analyzer.infrastructure.mchd.xml_parser import MCHDParser
from certificate_analyzer.presentation.gui.widgets.toast import ToastNotification
from certificate_analyzer.presentation.gui.views.history_view import NotificationHistory
from certificate_analyzer.presentation.gui.views.normative_view import NormativeWindow


from certificate_analyzer.presentation.gui.controllers.settings_controller import (
    SettingsController,
)
from certificate_analyzer.presentation.gui.controllers.certificate_controller import (
    CertificateController,
)
from certificate_analyzer.presentation.gui.controllers.mchd_controller import (
    MchdController,
)
from certificate_analyzer.presentation.gui.presenters.certificate_presenter import (
    CertificatePresenter,
)
from certificate_analyzer.presentation.gui.views.certificate_view import CertificateView


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
        self.core = CertificateAnalyzerCore()
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

        sidebar_frame = ttk.Frame(main_frame, width=260, style="Sidebar.TFrame")
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar_frame.pack_propagate(False)

        logo_frame = ttk.Frame(sidebar_frame, style="Sidebar.TFrame")
        logo_frame.pack(fill=tk.X, pady=(10, 20))

        ttk.Label(
            logo_frame,
            text="🔐",
            font=(UI_FONT, 28),
            foreground="white",
            background=SIDEBAR_COLOR,
        ).pack(pady=(10, 0))
        ttk.Label(
            logo_frame,
            text="Анализатор",
            font=(UI_FONT, 14, "bold"),
            foreground="white",
            background=SIDEBAR_COLOR,
        ).pack()
        ttk.Label(
            logo_frame,
            text="Сертификатов и МЧД",
            font=(UI_FONT, 9),
            foreground=SIDEBAR_TEXT_COLOR,
            background=SIDEBAR_COLOR,
        ).pack()

        nav_buttons = [
            ("📁 Сотрудники", lambda: self.switch_folder("📁 Сотрудники")),
            ("📁 Руководство", lambda: self.switch_folder("📁 Руководство")),
            ("📁 МЧД", self.scan_mchd_folder),
            ("📤 Экспорт", self.export_menu),
            ("⚙️ Служба", self.service_menu),
            ("📞 Загрузить справочник", self.load_phonebook),
        ]

        for text, command in nav_buttons:
            btn = ttk.Button(
                sidebar_frame, text=text, command=command, style="Sidebar.TButton"
            )
            btn.pack(fill=tk.X, padx=10, pady=3, ipady=5)
            self.create_tooltip(btn, text)

        sep = ttk.Separator(sidebar_frame, orient="horizontal")
        sep.pack(fill=tk.X, padx=10, pady=15)

        bottom_buttons = [
            ("📋 История уведомлений", self.show_notification_history),
            ("🔔 Push-уведомления", self.show_notification_settings),
            ("📚 Нормативка", self.show_normative),
            ("ℹ️ О программе", self.show_about),
        ]

        for text, command in bottom_buttons:
            btn = ttk.Button(
                sidebar_frame, text=text, command=command, style="Sidebar.TButton"
            )
            btn.pack(fill=tk.X, padx=10, pady=3, ipady=5)
            self.create_tooltip(btn, text)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))

        back_btn = ttk.Button(
            nav_frame,
            text="◀ Назад",
            command=self.folder_back,
            style="Accent.TButton",
            width=10,
        )
        back_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.create_tooltip(back_btn, "Вернуться к предыдущей папке")

        self.folder_path = tk.StringVar()
        folder_entry = ttk.Entry(
            nav_frame, textvariable=self.folder_path, font=(UI_FONT, 10)
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        select_btn = ttk.Button(
            nav_frame,
            text="📂 Выбрать папку",
            command=self.select_folder,
            style="Accent.TButton",
        )
        select_btn.pack(side=tk.RIGHT)
        self.create_tooltip(select_btn, "Выбрать другую папку с сертификатами")

        settings_btn = ttk.Button(
            nav_frame,
            text="⚙️",
            command=self.show_folder_settings,
            style="Accent.TButton",
            width=3,
        )
        settings_btn.pack(side=tk.RIGHT, padx=(0, 5))
        self.create_tooltip(settings_btn, "Настройка путей к папкам")

        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill=tk.X, pady=(0, 15))

        self.card_total = self.create_card(cards_frame, "Всего записей", "0")
        self.card_normal = self.create_card(cards_frame, "Активные", "0", GRAPH_NORMAL)
        self.card_warning = self.create_card(
            cards_frame, "Истекают", "0", GRAPH_WARNING
        )
        self.card_expired = self.create_card(
            cards_frame, "Просрочены", "0", GRAPH_EXPIRED
        )

        content_inner_frame = ttk.Frame(main_frame)
        content_inner_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(content_inner_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        files_frame = ttk.LabelFrame(left_panel, text=" Найденные файлы ", padding=10)
        files_frame.pack(fill=tk.BOTH, pady=(0, 10))

        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        cert_list_frame = ttk.LabelFrame(list_frame, text="Сертификаты", padding=5)
        cert_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.listbox_files = tk.Listbox(
            cert_list_frame,
            height=6,
            selectmode=tk.EXTENDED,
            font=(MONO_FONT, 9),
            bg="white",
            fg=TEXT_COLOR,
            selectbackground=BUTTON_COLOR,
            selectforeground="white",
        )
        self.listbox_files.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll_files = ttk.Scrollbar(
            cert_list_frame, orient=tk.VERTICAL, command=self.listbox_files.yview
        )
        scroll_files.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_files.configure(yscrollcommand=scroll_files.set)

        mchd_list_frame = ttk.LabelFrame(list_frame, text="МЧД", padding=5)
        mchd_list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.listbox_mchd = tk.Listbox(
            mchd_list_frame,
            height=6,
            selectmode=tk.EXTENDED,
            font=(MONO_FONT, 9),
            bg="white",
            fg=TEXT_COLOR,
            selectbackground=BUTTON_COLOR,
            selectforeground="white",
        )
        self.listbox_mchd.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll_mchd = ttk.Scrollbar(
            mchd_list_frame, orient=tk.VERTICAL, command=self.listbox_mchd.yview
        )
        scroll_mchd.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_mchd.configure(yscrollcommand=scroll_mchd.set)

        results_frame = ttk.LabelFrame(
            left_panel, text=" Результаты анализа сертификатов ", padding=10
        )
        results_frame.pack(fill=tk.BOTH, expand=True)

        action_panel = ttk.Frame(results_frame)
        action_panel.pack(fill=tk.X, pady=(0, 10))

        search_frame = ttk.Frame(action_panel)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(search_frame, text="🔍 Поиск:", font=(UI_FONT, 10)).pack(
            side=tk.LEFT
        )
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))

        filter_btn = ttk.Button(
            search_frame,
            text="📅 Фильтр по дате",
            command=self.show_date_filter,
            style="Accent.TButton",
            width=14,
        )
        filter_btn.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(filter_btn, "Фильтр сертификатов по дате окончания")

        delete_btn = ttk.Button(
            action_panel,
            text="🗑 Удалить",
            command=self.delete_selected,
            style="Accent.TButton",
            width=10,
        )
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self.create_tooltip(delete_btn, "Удалить выбранные файлы с диска")

        refresh_btn = ttk.Button(
            action_panel,
            text="🔄 Обновить",
            command=self.refresh_all,
            style="Accent.TButton",
            width=10,
        )
        refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self.create_tooltip(refresh_btn, "Обновить список файлов и данные")

        self.search_result_label = ttk.Label(
            action_panel,
            text="",
            font=(UI_FONT, 9, "italic"),
            foreground=ACCENT_COLOR,
        )
        self.search_result_label.pack(side=tk.RIGHT, padx=(10, 0))

        self.current_folder_label = ttk.Label(
            action_panel,
            text=f"Текущая: {self.current_folder_key}",
            font=(UI_FONT, 9, "italic"),
            foreground=ACCENT_COLOR,
        )
        self.current_folder_label.pack(side=tk.RIGHT, padx=(10, 0))

        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.columns = (
            "Тип",
            "Файл",
            "С",
            "По",
            "ФИО",
            "Номер",
            "Email",
            "Кабинет",
            "Подразделение",
            "Телефон",
            "Статус",
        )

        self.tree = ttk.Treeview(
            tree_frame, columns=self.columns, show="headings", height=15
        )

        col_widths = [50, 150, 85, 85, 160, 110, 110, 85, 110, 120, 110]
        for col, width in zip(self.columns, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=width, anchor=tk.W, stretch=True, minwidth=50)

        scroll_y = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(
            tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure(
            "expired", background=EXPIRED_COLOR, foreground=EXPIRED_TEXT
        )
        self.tree.tag_configure(
            "warning", background=WARNING_COLOR, foreground=WARNING_TEXT
        )
        self.tree.tag_configure(
            "normal", background=NORMAL_COLOR, foreground=NORMAL_TEXT
        )
        self.tree.tag_configure("duplicate", background="#fff3cd", foreground="black")

        right_panel = ttk.Frame(content_inner_frame, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)

        calendar_frame = ttk.LabelFrame(
            right_panel, text=" 📅 Календарь окончаний ", padding=10
        )
        calendar_frame.pack(fill=tk.BOTH, pady=(0, 10))

        cal_controls_frame = ttk.Frame(calendar_frame)
        cal_controls_frame.pack(fill=tk.X, pady=(0, 5))

        today_btn = ttk.Button(
            cal_controls_frame,
            text="Сегодня",
            command=self.show_today,
            style="Accent.TButton",
            width=8,
        )
        today_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.create_tooltip(today_btn, "Показать сегодняшнюю дату в календаре")

        prev_btn = ttk.Button(
            cal_controls_frame,
            text="◀",
            command=self.prev_month,
            style="Accent.TButton",
            width=3,
        )
        prev_btn.pack(side=tk.LEFT, padx=(0, 5))

        next_btn = ttk.Button(
            cal_controls_frame,
            text="▶",
            command=self.next_month,
            style="Accent.TButton",
            width=3,
        )
        next_btn.pack(side=tk.LEFT)

        try:
            self.cal = Calendar(
                calendar_frame,
                selectmode="day",
                date_pattern="dd.mm.yyyy",
                firstweekday="monday",
                showweeknumbers=False,
                weekendbackground="#f5f5f5",
                weekendforeground="#666666",
                othermonthbackground="#f9f9f9",
                othermonthforeground="#cccccc",
                bordercolor=CARD_BORDER_COLOR,
                selectbackground=BUTTON_COLOR,
                selectforeground="white",
                background="white",
                foreground=TEXT_COLOR,
                font=(UI_FONT, 9),
                headersbackground="#f0f0f0",
                headersforeground=TEXT_COLOR,
                normalbackground="white",
                normalforeground=TEXT_COLOR,
                disabledforeground="#cccccc",
                locale="ru_RU",
            )
        except:
            self.cal = Calendar(
                calendar_frame,
                selectmode="day",
                date_pattern="dd.mm.yyyy",
                firstweekday="monday",
                showweeknumbers=False,
                weekendbackground="#f5f5f5",
                weekendforeground="#666666",
                othermonthbackground="#f9f9f9",
                othermonthforeground="#cccccc",
                bordercolor=CARD_BORDER_COLOR,
                selectbackground=BUTTON_COLOR,
                selectforeground="white",
                background="white",
                foreground=TEXT_COLOR,
                font=(UI_FONT, 9),
                headersbackground="#f0f0f0",
                headersforeground=TEXT_COLOR,
                normalbackground="white",
                normalforeground=TEXT_COLOR,
                disabledforeground="#cccccc",
            )

        self.cal.pack(fill=tk.BOTH, expand=True)
        self.cal.bind("<<CalendarSelected>>", self.on_date_select)

        dashboard_frame = ttk.LabelFrame(
            right_panel, text=" 📊 Статус документов ", padding=10
        )
        dashboard_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        chart_options_frame = ttk.Frame(dashboard_frame)
        chart_options_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(chart_options_frame, text="Тип:").pack(side=tk.LEFT, padx=(0, 5))

        self.chart_type_var = tk.StringVar(value="Круговая")
        chart_types = [
            "Круговая",
            "Столбчатая",
            "Линейная",
            "С областями",
            "Кольцевая",
            "Точечная",
            "Пузырьковая",
            "Гистограмма с накоплением",
        ]
        chart_combo = ttk.Combobox(
            chart_options_frame,
            textvariable=self.chart_type_var,
            values=chart_types,
            state="readonly",
            width=18,
        )
        chart_combo.pack(side=tk.LEFT, padx=5)
        chart_combo.bind("<<ComboboxSelected>>", self.on_chart_type_change)

        self.include_chart_var = tk.BooleanVar(value=True)
        chart_check = ttk.Checkbutton(
            chart_options_frame, text="Включать в PDF", variable=self.include_chart_var
        )
        chart_check.pack(side=tk.RIGHT)

        self.figure_status = plt.Figure(figsize=(5, 3), dpi=80, facecolor="white")
        self.ax_status = self.figure_status.add_subplot(111)
        self.ax_status.set_facecolor("white")
        self.canvas_status = FigureCanvasTkAgg(
            self.figure_status, master=dashboard_frame
        )
        self.canvas_status.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.sort_reverse = {col: False for col in self.columns}
        self.folder_history = []

        self.root.after(1000, self.update_calendar_colors)

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
