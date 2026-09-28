"""Представление окна настроек приложения."""

import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox, ttk
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

        self.title("Настройки хранилища")
        self._build_ui()

    def _build_ui(self) -> None:
        """Создает элементы пользовательского интерфейса диалога настроек.

        Returns:
            None
        """
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        values = {
            "storage_folder": (
                "Папка сертификатов",
                str(self.app.certificates.storage.folder),
            ),
            "database_path": ("Файл SQLite", str(self.app.database.path)),
            "export_folder": ("Папка отчётов", self.app.settings.export_folder),
            "warning_days": (
                "Предупреждать за дней",
                str(self.app.settings.warning_days),
            ),
            "check_interval": (
                "Интервал мониторинга, секунд",
                str(self.app.settings.check_interval),
            ),
        }

        for index, (key, (label, value)) in enumerate(values.items()):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=5)
            self.fields[key] = tk.StringVar(value=value)
            ttk.Entry(frame, textvariable=self.fields[key], width=55).grid(
                row=index, column=1, padx=10
            )

        ttk.Label(
            frame,
            text="Настройки вступят в силу после перезапуска. Существующие файлы автоматически не перемещаются.",
            wraplength=600,
        ).grid(row=len(values), column=0, columnspan=2, pady=12)

        ttk.Button(frame, text="Сохранить", command=self.save).grid(
            row=len(values) + 1, column=1, sticky="e"
        )

    def save(self) -> None:
        """Сохраняет измененные настройки в файл конфигурации.

        Returns:
            None

        Raises:
            None (ошибки валидации отображаются пользователю через messagebox).
        """
        try:
            settings = replace(
                self.app.settings,
                **{
                    k: int(v.get())
                    if k in ("warning_days", "check_interval")
                    else v.get()
                    for k, v in self.fields.items()
                },
            )
            save_settings(settings, self.config_path)
            self.destroy()
            if self.on_saved:
                self.on_saved("Настройки сохранены. Перезапустите приложение.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Настройки", str(exc), parent=self)


# Алиас для обратной совместимости
SettingsView = SettingsDialog
