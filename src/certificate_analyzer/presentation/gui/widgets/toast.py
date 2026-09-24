import tkinter as tk
from certificate_analyzer.presentation.gui.styles import (
    BUTTON_COLOR,
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    NORMAL_COLOR,
    NORMAL_TEXT,
    WARNING_COLOR,
    WARNING_TEXT,
    UI_FONT,
)


class ToastNotification:
    _active_toasts = []

    def __init__(self, parent, message, duration=4000, notification_type="info"):
        self.parent = parent
        self.message = message
        self.duration = duration
        self.notification_type = notification_type
        self.toast = None

        colors_config = {
            "info": {"bg": BUTTON_COLOR, "fg": "white"},
            "warning": {"bg": WARNING_COLOR, "fg": WARNING_TEXT},
            "error": {"bg": EXPIRED_COLOR, "fg": EXPIRED_TEXT},
            "success": {"bg": NORMAL_COLOR, "fg": NORMAL_TEXT},
        }

        self.bg_color = colors_config.get(notification_type, colors_config["info"])[
            "bg"
        ]
        self.fg_color = colors_config.get(notification_type, colors_config["info"])[
            "fg"
        ]
        self.parent.after(50, self._show)

    def _show(self):
        try:
            for toast in ToastNotification._active_toasts:
                if toast and toast.winfo_exists():
                    try:
                        if (
                            hasattr(toast, "message_text")
                            and toast.message_text == self.message
                        ):
                            return
                    except:
                        pass

            self.toast = tk.Toplevel(self.parent)
            self.toast.message_text = self.message
            self.toast.overrideredirect(True)
            self.toast.configure(bg=self.bg_color, bd=0, highlightthickness=0)
            self.toast.attributes("-topmost", True)

            icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}
            icon = icons.get(self.notification_type, "ℹ️")

            titles = {
                "info": "Информация",
                "warning": "Внимание",
                "error": "Ошибка",
                "success": "Успех",
            }
            title_text = titles.get(self.notification_type, "Информация")

            main_frame = tk.Frame(self.toast, bg=self.bg_color, bd=1, relief="solid")
            main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

            header_frame = tk.Frame(main_frame, bg=self.bg_color)
            header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

            tk.Label(
                header_frame,
                text=icon,
                font=(UI_FONT, 16),
                bg=self.bg_color,
                fg=self.fg_color,
            ).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(
                header_frame,
                text=title_text,
                font=(UI_FONT, 11, "bold"),
                bg=self.bg_color,
                fg=self.fg_color,
            ).pack(side=tk.LEFT)

            close_btn = tk.Label(
                header_frame,
                text="✕",
                font=(UI_FONT, 12, "bold"),
                bg=self.bg_color,
                fg=self.fg_color,
                cursor="hand2",
            )
            close_btn.pack(side=tk.RIGHT)
            close_btn.bind("<Button-1>", lambda e: self._close())

            body_frame = tk.Frame(main_frame, bg=self.bg_color)
            body_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

            tk.Label(
                body_frame,
                text=self.message,
                font=(UI_FONT, 10),
                bg=self.bg_color,
                fg=self.fg_color,
                wraplength=350,
                justify=tk.LEFT,
            ).pack(anchor=tk.W)

            self.toast.update_idletasks()

            screen_width = self.toast.winfo_screenwidth()
            screen_height = self.toast.winfo_screenheight()

            toast_width = 380
            toast_height = 120

            x = screen_width - toast_width - 20
            y = screen_height - toast_height - 50

            self.toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")

            ToastNotification._active_toasts.append(self.toast)
            ToastNotification._active_toasts = [
                t for t in ToastNotification._active_toasts if t and t.winfo_exists()
            ]

            self.toast.attributes("-alpha", 0)
            self._fade_in()
            self.toast.after(self.duration, self._fade_out)

        except Exception as e:
            print(f"Ошибка при создании уведомления: {e}")

    def _fade_in(self, alpha=0):
        if self.toast and self.toast.winfo_exists() and alpha <= 0.95:
            alpha += 0.05
            try:
                self.toast.attributes("-alpha", alpha)
                self.toast.after(20, lambda: self._fade_in(alpha))
            except:
                pass

    def _fade_out(self, alpha=0.95):
        if self.toast and self.toast.winfo_exists() and alpha >= 0.05:
            alpha -= 0.05
            try:
                self.toast.attributes("-alpha", alpha)
                self.toast.after(20, lambda: self._fade_out(alpha))
            except:
                pass
        else:
            self._close()

    def _close(self):
        try:
            if self.toast and self.toast.winfo_exists():
                if self.toast in ToastNotification._active_toasts:
                    ToastNotification._active_toasts.remove(self.toast)
                self.toast.destroy()
                self.toast = None
        except:
            pass
