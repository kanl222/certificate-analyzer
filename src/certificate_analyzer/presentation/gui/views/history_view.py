import tkinter as tk
from datetime import timezone, datetime
from tkinter import messagebox, ttk

from certificate_analyzer.infrastructure.persistence.notification_history import (
    NotificationHistoryStore,
)
from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_COLOR,
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    NORMAL_COLOR,
    NORMAL_TEXT,
    UI_FONT,
    WARNING_COLOR,
    WARNING_TEXT,
)
from certificate_analyzer.presentation.gui.widgets.toast import ToastNotification



UTC = timezone.utc

class NotificationHistory:
    def __init__(self, parent):
        self.parent = parent
        self.notifications = []
        self.history_window = None
        self.load_history()

    def add_notification(self, message, notification_type="info"):
        notification = {
            "time": datetime.now(UTC).strftime("%d.%m.%Y %H:%M:%S"),
            "message": message,
            "type": notification_type,
        }
        self.notifications.insert(0, notification)
        if len(self.notifications) > 100:
            self.notifications = self.notifications[:100]
        self.save_history()

    def save_history(self):
        self.store.save(self.notifications)

    def load_history(self):
        self.store = NotificationHistoryStore()
        self.notifications = self.store.load()

    def show_history_window(self):
        if self.history_window and self.history_window.winfo_exists():
            self.history_window.lift()
            self.history_window.focus_force()
            return

        self.history_window = tk.Toplevel(self.parent)
        self.history_window.title("История уведомлений")
        self.history_window.geometry("700x500")
        self.history_window.configure(bg=BG_COLOR)
        self.history_window.minsize(600, 400)

        self.history_window.update_idletasks()
        x = (self.history_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.history_window.winfo_screenheight() // 2) - (500 // 2)
        self.history_window.geometry(f"700x500+{x}+{y}")

        main_frame = ttk.Frame(self.history_window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            title_frame, text="История уведомлений", font=(UI_FONT, 14, "bold")
        ).pack(side=tk.LEFT)

        ttk.Label(
            title_frame,
            text=f"Всего: {len(self.notifications)}",
            font=(UI_FONT, 10),
            foreground=ACCENT_COLOR,
        ).pack(side=tk.RIGHT)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            btn_frame,
            text="Очистить историю",
            command=self.clear_history,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Обновить",
            command=self.refresh_history_display,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Время", "Тип", "Сообщение")
        self.history_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )

        self.history_tree.heading("Время", text="Время")
        self.history_tree.heading("Тип", text="Тип")
        self.history_tree.heading("Сообщение", text="Сообщение")

        self.history_tree.column("Время", width=140, anchor=tk.W)
        self.history_tree.column("Тип", width=100, anchor=tk.CENTER)
        self.history_tree.column("Сообщение", width=420, anchor=tk.W)

        scroll_y = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.history_tree.yview
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.configure(yscrollcommand=scroll_y.set)
        self.history_tree.pack(fill=tk.BOTH, expand=True)

        self.history_tree.tag_configure(
            "error", background=EXPIRED_COLOR, foreground=EXPIRED_TEXT
        )
        self.history_tree.tag_configure(
            "warning", background=WARNING_COLOR, foreground=WARNING_TEXT
        )
        self.history_tree.tag_configure(
            "success", background=NORMAL_COLOR, foreground=NORMAL_TEXT
        )
        self.history_tree.tag_configure(
            "info", background=BUTTON_COLOR, foreground="white"
        )

        self.refresh_history_display()

        close_btn = ttk.Button(
            main_frame,
            text="Закрыть",
            command=self.history_window.destroy,
            style="Accent.TButton",
        )
        close_btn.pack(pady=(10, 0))

        self.history_window.protocol("WM_DELETE_WINDOW", self._on_history_window_close)

    def _on_history_window_close(self):
        if self.history_window:
            self.history_window.destroy()
            self.history_window = None

    def refresh_history_display(self):
        if not self.history_window or not self.history_window.winfo_exists():
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        types = {
            "error": "Ошибка",
            "warning": "Внимание",
            "success": "Успех",
            "info": "Информация",
        }

        for notif in self.notifications:
            notif_type = notif.get("type", "info")
            display_type = types.get(notif_type, "Информация")
            tag = notif_type

            self.history_tree.insert(
                "",
                tk.END,
                values=(notif.get("time", ""), display_type, notif.get("message", "")),
                tags=(tag,),
            )

    def clear_history(self):
        if messagebox.askyesno("Подтверждение", "Очистить всю историю уведомлений?"):
            self.notifications = []
            self.save_history()
            self.refresh_history_display()
            ToastNotification(
                self.parent, "История уведомлений очищена", 2000, "success"
            )
