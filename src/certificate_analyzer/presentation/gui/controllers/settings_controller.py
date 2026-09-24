from certificate_analyzer.infrastructure.config.config_loader import (
    load_settings,
    save_settings as persist_settings,
)
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import json
from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    EXPIRED_COLOR,
    UI_FONT,
)
from certificate_analyzer.application.services.notification_service import (
    PushNotificationManager,
)
from certificate_analyzer.infrastructure.config.config_loader import save_config
from certificate_analyzer.infrastructure.config.paths import notification_config_path


class SettingsController:
    def show_folder_settings(self):
        if (
            "folder_settings" in self.open_windows
            and self.open_windows["folder_settings"] is not None
        ):
            try:
                if self.open_windows["folder_settings"].winfo_exists():
                    self.open_windows["folder_settings"].lift()
                    self.open_windows["folder_settings"].focus_force()
                    return
            except:
                pass

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройка путей к папкам")
        settings_window.geometry("600x450")
        settings_window.configure(bg=BG_COLOR)
        settings_window.resizable(False, False)
        self.open_windows["folder_settings"] = settings_window

        frame = ttk.Frame(settings_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            frame, text="Настройка путей к папкам", font=(UI_FONT, 14, "bold")
        ).pack(anchor="center", pady=(0, 20))

        emp_frame = ttk.Frame(frame)
        emp_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            emp_frame, text="📁 Сотрудники:", font=(UI_FONT, 10, "bold"), width=15
        ).pack(side=tk.LEFT)
        emp_path_var = tk.StringVar(value=self.default_folders.get("📁 Сотрудники", ""))
        ttk.Entry(emp_frame, textvariable=emp_path_var, width=40).pack(
            side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True
        )
        ttk.Button(
            emp_frame,
            text="Обзор",
            command=lambda: self.select_folder_path(emp_path_var),
            style="Accent.TButton",
            width=10,
        ).pack(side=tk.RIGHT)

        mgmt_frame = ttk.Frame(frame)
        mgmt_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            mgmt_frame, text="📁 Руководство:", font=(UI_FONT, 10, "bold"), width=15
        ).pack(side=tk.LEFT)
        mgmt_path_var = tk.StringVar(
            value=self.default_folders.get("📁 Руководство", "")
        )
        ttk.Entry(mgmt_frame, textvariable=mgmt_path_var, width=40).pack(
            side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True
        )
        ttk.Button(
            mgmt_frame,
            text="Обзор",
            command=lambda: self.select_folder_path(mgmt_path_var),
            style="Accent.TButton",
            width=10,
        ).pack(side=tk.RIGHT)

        mchd_frame = ttk.Frame(frame)
        mchd_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            mchd_frame, text="📁 МЧД (XML):", font=(UI_FONT, 10, "bold"), width=15
        ).pack(side=tk.LEFT)
        mchd_path_var = tk.StringVar(value=self.core.mchd_folder)
        ttk.Entry(mchd_frame, textvariable=mchd_path_var, width=40).pack(
            side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True
        )
        ttk.Button(
            mchd_frame,
            text="Обзор",
            command=lambda: self.select_folder_path(mchd_path_var, is_mchd=True),
            style="Accent.TButton",
            width=10,
        ).pack(side=tk.RIGHT)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)

        def save_settings():
            self.default_folders["📁 Сотрудники"] = emp_path_var.get()
            self.default_folders["📁 Руководство"] = mgmt_path_var.get()
            self.core.mchd_folder = mchd_path_var.get()
            settings = load_settings()
            settings.mchd_folder = self.core.mchd_folder
            persist_settings(settings)
            if save_config(self.default_folders):
                messagebox.showinfo("Успех", "Настройки сохранены!")
                self.close_window("folder_settings", settings_window)
                if self.current_folder_key in ["📁 Сотрудники", "📁 Руководство"]:
                    self.folder_path.set(self.default_folders[self.current_folder_key])
                    self.scan_folder()
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить настройки")

        ttk.Button(
            btn_frame, text="Сохранить", command=save_settings, style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            btn_frame,
            text="Отмена",
            command=lambda: self.close_window("folder_settings", settings_window),
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

        def on_destroy():
            self.open_windows["folder_settings"] = None
            settings_window.destroy()

        settings_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def select_folder_path(self, var, is_mchd=False):
        folder = filedialog.askdirectory(title="Выберите папку")
        if folder:
            var.set(folder)
            if is_mchd:
                self.core.mchd_folder = folder

    def setup_folder_menu(self):
        self.folder_menu = tk.Menu(self.root, tearoff=0)
        self.folder_menu.add_command(
            label="📁 Добавить папку в избранное", command=self.add_to_favorites
        )
        self.folder_menu.add_command(
            label="📋 Редактировать избранные папки", command=self.edit_favorites
        )
        self.folder_menu.add_separator()
        self.folder_menu.add_command(
            label="🗂️ Создать новую папку", command=self.create_new_folder
        )
        self.folder_menu.add_separator()
        self.folder_menu.add_command(
            label="⚙️ Настройки путей", command=self.show_folder_settings
        )

    def switch_folder(self, key):
        self.current_folder_key = key
        path = self.default_folders.get(key)
        if not path:
            self.show_folder_settings()
            return
        if not os.path.exists(path):
            response = messagebox.askyesno(
                "Создать папку", f"Папка '{path}' не существует. Создать?"
            )
            if response:
                os.makedirs(path)
            else:
                return
        self.folder_path.set(path)
        self.current_folder_label.config(text=f"Текущая: {key}")
        self.folder_history.append(path)
        self.scan_folder()

    def load_default_folder(self):
        if not self.default_folders:
            return
        self.current_folder_key = next(iter(self.default_folders))
        path = self.default_folders[self.current_folder_key]
        if not os.path.exists(path):
            os.makedirs(path)
        self.folder_path.set(path)
        self.folder_history.append(path)
        self.scan_folder()

    def folder_back(self):
        if len(self.folder_history) > 1:
            self.folder_history.pop()
            prev_folder = self.folder_history[-1]
            self.folder_path.set(prev_folder)
            folder_name = "Произвольная папка"
            for name, path in self.default_folders.items():
                if path == prev_folder:
                    folder_name = name
                    break
            self.current_folder_label.config(text=f"Текущая: {folder_name}")
            self.scan_folder()

    def add_to_favorites(self):
        current_path = self.folder_path.get()
        if not current_path:
            messagebox.showwarning("Внимание", "Сначала выберите папку")
            return
        name = simpledialog.askstring(
            "Добавить в избранное",
            "Введите имя для папки:",
            initialvalue=os.path.basename(current_path),
        )
        if name:
            self.default_folders[name] = current_path
            if save_config(self.default_folders):
                messagebox.showinfo("Успех", f"Папка '{name}' добавлена в избранное")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить настройки")

    def edit_favorites(self):
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Редактирование избранных папок")
        edit_window.geometry("500x400")
        edit_window.configure(bg=BG_COLOR)
        frame = ttk.Frame(edit_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Избранные папки:", font=(UI_FONT, 12, "bold")).pack(
            anchor="w"
        )
        listbox = tk.Listbox(frame, height=10, selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        for name, path in self.default_folders.items():
            listbox.insert(tk.END, f"{name}: {path}")

        def remove_selected():
            selection = listbox.curselection()
            if selection:
                item = listbox.get(selection[0])
                name = item.split(":")[0]
                if name in self.default_folders:
                    del self.default_folders[name]
                    listbox.delete(selection[0])
                    save_config(self.default_folders)

        def add_new():
            name = simpledialog.askstring("Добавить папку", "Имя:")
            if name:
                path = filedialog.askdirectory(title=f"Выберите папку для '{name}'")
                if path:
                    self.default_folders[name] = path
                    listbox.insert(tk.END, f"{name}: {path}")
                    save_config(self.default_folders)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(
            btn_frame, text="Добавить", command=add_new, style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Удалить", command=remove_selected, style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="Закрыть",
            command=edit_window.destroy,
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

    def create_new_folder(self):
        folder_name = simpledialog.askstring("Создать папку", "Введите имя папки:")
        if folder_name:
            new_folder_path = os.path.join(
                os.path.expanduser("~"), f"Cert_{folder_name}"
            )
            os.makedirs(new_folder_path, exist_ok=True)
            self.default_folders[f"📁 {folder_name}"] = new_folder_path
            save_config(self.default_folders)
            messagebox.showinfo(
                "Успех",
                f"Папка создаена: {new_folder_path}\nДобавлена в избранное как '📁 {folder_name}'",
            )

    def setup_push_notifications(self):
        self.notification_manager = PushNotificationManager()
        self.load_notification_settings()
        self.start_notification_monitoring()

    def load_notification_settings(self):
        config_file = str(notification_config_path())
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    interval_hours = settings.get("interval_hours", 1)
                    self.notification_manager.set_interval(interval_hours)
                    self.notification_enabled = settings.get("enabled", True)
                    api_url = settings.get("api_url", "https://api.example.com/v1/notifications")
                    api_key = settings.get("api_key")
                    stub_mode = settings.get("stub_mode", True)
                    self.notification_manager.configure_api(
                        api_url=api_url,
                        api_key=api_key,
                        stub_mode=stub_mode,
                    )
            except Exception:
                self.notification_enabled = True
        else:
            self.notification_enabled = True

    def save_notification_settings(self):
        config_file = str(notification_config_path())
        try:
            api_backend = self.notification_manager.api_backend
            data = {
                "interval_hours": self.notification_manager.notification_interval // 3600,
                "enabled": self.notification_enabled,
                "api_url": api_backend.api_url if api_backend else "https://api.example.com/v1/notifications",
                "api_key": api_backend.api_key if api_backend else None,
                "stub_mode": api_backend.stub_mode if api_backend else True,
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def start_notification_monitoring(self):
        if not self.notification_enabled:
            return

        def check_certificates():
            if not hasattr(self, "cert_data_cache") or not self.cert_data_cache:
                return
            expired = sum(
                1 for c in self.cert_data_cache if c.get("status") == "Просрочен"
            )
            warning = sum(
                1 for c in self.cert_data_cache if "Истекает" in c.get("status", "")
            )
            total = len(self.cert_data_cache)
            self.notification_manager.check_and_notify_expired(expired, warning, total)

        self.notification_manager.start_background_monitoring(check_certificates, 3600)

    def show_notification_settings(self):
        if (
            "notification_settings" in self.open_windows
            and self.open_windows["notification_settings"] is not None
        ):
            try:
                if self.open_windows["notification_settings"].winfo_exists():
                    self.open_windows["notification_settings"].lift()
                    self.open_windows["notification_settings"].focus_force()
                    return
            except:
                pass

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройка push-уведомлений")
        settings_window.geometry("450x380")
        settings_window.configure(bg=BG_COLOR)
        settings_window.resizable(False, False)
        self.open_windows["notification_settings"] = settings_window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (380 // 2)
        settings_window.geometry(f"450x380+{x}+{y}")

        main_frame = ttk.Frame(settings_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            main_frame,
            text="🔔 Настройка push-уведомлений",
            font=(UI_FONT, 14, "bold"),
        ).pack(pady=(0, 15))

        if sys.platform == "win32" and not getattr(
            self.notification_manager.backend, "_available", False
        ):
            ttk.Label(
                main_frame,
                text="⚠️ Для уведомлений установите: pip install win10toast",
                font=(UI_FONT, 9),
                foreground=EXPIRED_COLOR,
            ).pack(pady=(0, 15))

        enabled_frame = ttk.Frame(main_frame)
        enabled_frame.pack(fill=tk.X, pady=5)
        self.notification_enabled_var = tk.BooleanVar(value=self.notification_enabled)
        ttk.Checkbutton(
            enabled_frame,
            text="Включить push-уведомления",
            variable=self.notification_enabled_var,
            command=self.toggle_notifications,
        ).pack(side=tk.LEFT)

        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill=tk.X, pady=15)
        ttk.Label(
            interval_frame, text="Интервал уведомлений:", font=(UI_FONT, 10)
        ).pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(
            value=self.notification_manager.notification_interval // 3600
        )
        ttk.Spinbox(
            interval_frame,
            from_=1,
            to=24,
            width=5,
            textvariable=self.interval_var,
            command=self.update_notification_interval,
        ).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(interval_frame, text="часов").pack(side=tk.LEFT)

        info_frame = ttk.LabelFrame(main_frame, text=" ℹ️ Информация ", padding=10)
        info_frame.pack(fill=tk.X, pady=15)
        info_text = """Push-уведомления будут приходить:
 • При обнаружении просроченных сертификатов
 • При истекающих сертификатах (менее 60 дней)
 • С выбранным интервалом (не чаще)"""
        ttk.Label(
            info_frame,
            text=info_text,
            font=(UI_FONT, 9),
            foreground=ACCENT_COLOR,
            wraplength=380,
        ).pack()

        ttk.Button(
            main_frame,
            text="🔔 Отправить тестовое уведомление",
            command=self.send_test_notification,
            style="Accent.TButton",
        ).pack(pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(
            btn_frame,
            text="Сохранить",
            command=lambda: self.save_notification_settings_close(settings_window),
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            btn_frame,
            text="Отмена",
            command=lambda: self.close_window("notification_settings", settings_window),
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

        def on_destroy():
            self.open_windows["notification_settings"] = None
            settings_window.destroy()

        settings_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def toggle_notifications(self):
        self.notification_enabled = self.notification_enabled_var.get()
        if not self.notification_enabled:
            self.notification_manager.stop_monitoring()
        else:
            self.start_notification_monitoring()
        self.save_notification_settings()

    def update_notification_interval(self):
        hours = self.interval_var.get()
        self.notification_manager.set_interval(hours)
        self.save_notification_settings()
        if self.notification_enabled:
            self.notification_manager.stop_monitoring()
            self.start_notification_monitoring()

    def save_notification_settings_close(self, window):
        self.save_notification_settings()
        self.close_window("notification_settings", window)
        self.show_notification("Настройки уведомлений сохранены", "success", 2000)

    def send_test_notification(self):
        if self.notification_manager.send_notification(
            "🔔 Тестовое уведомление",
            "Если вы видите это сообщение, push-уведомления работают корректно!",
            duration=5,
        ):
            self.show_notification("Тестовое уведомление отправлено!", "success", 2000)
        else:
            self.show_notification(
                "Не удалось отправить уведомление. Проверьте настройки.", "error", 3000
            )

    def install_service(self):
        from certificate_analyzer.runtime.windows_service import install_service

        try:
            install_service()
            messagebox.showinfo(
                "Служба",
                "Служба установлена. Настройки берутся из пользовательской конфигурации.",
            )
        except Exception as exc:
            messagebox.showerror("Служба", str(exc))

    def remove_service(self):
        from certificate_analyzer.runtime.windows_service import remove_service

        try:
            remove_service()
            messagebox.showinfo("Служба", "Служба удалена")
        except Exception as exc:
            messagebox.showerror("Служба", str(exc))
