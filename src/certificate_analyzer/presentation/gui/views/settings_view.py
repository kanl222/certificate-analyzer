"""Представление окна настроек приложения."""

import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.infrastructure.config.config_loader import save_settings


class SettingsDialog(tk.Toplevel):
    """Модальное диалоговое окно для настройки параметров хранилища и мониторинга."""

    def __init__(
        self,
        parent: tk.Widget,
        application: Any,
        config_path: str | Path | None = None,
        on_saved: Callable[[str], None] | None = None,
    ) -> None:
        """Инициализирует диалоговое окно настроек.

        Args:
            parent: Родительский виджет Tkinter.
            application: Контейнер сервисов приложения.
            config_path: Путь к файлу конфигурации.
            on_saved: Функция обратного вызова, вызываемая после успешного сохранения настроек.
        """
        super().__init__(parent)
        self.app = application
        self.config_path = config_path
        self.on_saved = on_saved
        self.fields: dict[str, tk.StringVar] = {}
        self.folder_fields: dict[str, tk.StringVar] = {}

        self.title("Настройки")
        self.minsize(680, 360)
        self.transient(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Создает элементы пользовательского интерфейса диалога настроек.

        Returns:
            None
        """
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True)
        groups = {
            "Хранилище": [
                ("storage_folder", "Папка сертификатов", str(self.app.certificates.storage.folder), "directory"),
                ("database_path", "Файл базы данных", str(self.app.database.path), "database"),
            ],
            "Импорт": [
                ("mchd_folder", "Папка МЧД", self.app.settings.mchd_folder, "directory"),
                ("phonebook_path", "Телефонный справочник", self.app.settings.phonebook_path or "", "phonebook"),
            ],
            "Сертификаты": [
                ("warning_days", "Считать истекающим за, дней", str(self.app.settings.warning_days), "days"),
            ],
            "Мониторинг": [
                ("warning_days", "Уведомлять за, дней", str(self.app.settings.warning_days), "days"),
                ("check_interval", "Интервал проверки, секунд", str(self.app.settings.check_interval), None),
            ],
            "Отчёты": [
                ("export_folder", "Папка отчётов", self.app.settings.export_folder, "directory"),
            ],
        }
        for title, values in groups.items():
            tab = ttk.Frame(self.notebook, padding=12)
            tab.columnconfigure(1, weight=1)
            self.notebook.add(tab, text=title)
            for row, (key, label, value, browse_kind) in enumerate(values):
                variable = self.fields.get(key)
                if variable is None:
                    variable = tk.StringVar(value=value)
                    self.fields[key] = variable
                self._add_field(tab, row, label, variable, browse_kind)
            if title == "Импорт":
                for row, (name, folder) in enumerate(self.app.settings.folders.items(), start=len(values)):
                    variable = tk.StringVar(value=folder)
                    self.folder_fields[name] = variable
                    self._add_field(tab, row, f"Сертификаты: {name}", variable, "directory")
            if title == "Сертификаты":
                ttk.Label(tab, text="Например, 30: статус «Истекает» появится, когда до окончания действия останется 30 дней или меньше.\n0 — не выделять сертификаты заранее. Порог используется и для уведомлений.",
                          wraplength=600).grid(row=len(values), column=0, columnspan=3, sticky="w", pady=12)
            if title == "Мониторинг":
                ttk.Label(tab, text="Порог дней общий с вкладкой «Сертификаты».\nУправление фоновым процессом и автозапуском доступно в меню «Служба».",
                          wraplength=600).grid(row=len(values), column=0, columnspan=3, sticky="w", pady=6)

        ttk.Label(frame,
                  text="После сохранения перезапустите приложение и фоновый процесс. Существующие файлы автоматически не перемещаются.",
                  wraplength=640).pack(fill="x", pady=12)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side="right")
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="right", padx=8)

    def _add_field(self, tab, row, label, variable, browse_kind):
        ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=6)
        if browse_kind == "days":
            ttk.Spinbox(tab, from_=0, to=3650, increment=1, textvariable=variable, width=12).grid(row=row, column=1, sticky="w", padx=10)
        else:
            ttk.Entry(tab, textvariable=variable, width=48).grid(row=row, column=1, sticky="ew", padx=10)
        if browse_kind and browse_kind != "days":
            ttk.Button(tab, text="Обзор…", command=lambda: self._browse(variable, browse_kind)).grid(row=row, column=2)

    def _browse(self, variable, kind):
        if kind == "directory":
            path = filedialog.askdirectory(parent=self, title="Выберите папку")
        elif kind == "database":
            path = filedialog.asksaveasfilename(parent=self, title="Файл базы данных",
                defaultextension=".db", filetypes=[("SQLite", "*.db *.sqlite"), ("Все файлы", "*.*")])
        else:
            path = filedialog.askopenfilename(parent=self, title="Телефонный справочник",
                filetypes=[("Справочник", "*.txt *.docx"), ("Все файлы", "*.*")])
        if path:
            variable.set(path)

    def save(self) -> None:
        """Сохраняет измененные настройки в файл конфигурации.

        Returns:
            None

        Raises:
            None (ошибки валидации отображаются пользователю через messagebox).
        """
        try:
            try:
                warning_days = int(self.fields["warning_days"].get())
            except ValueError:
                raise ValueError("Порог истечения должен быть целым числом дней") from None
            if warning_days < 0:
                raise ValueError("Порог истечения не может быть отрицательным")
            settings = replace(
                self.app.settings,
                **{
                    k: int(v.get())
                    if k in ("warning_days", "check_interval")
                    else (v.get().strip() or None) if k == "phonebook_path"
                    else v.get()
                    for k, v in self.fields.items()
                },
                folders={name: value.get() for name, value in self.folder_fields.items()},
            )
            save_settings(settings, self.config_path)
            self.destroy()
            if self.on_saved:
                self.on_saved("Настройки сохранены. Остановите фоновый процесс через меню «Служба» и перезапустите приложение.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Настройки", str(exc), parent=self)


# Алиас для обратной совместимости
SettingsView = SettingsDialog
