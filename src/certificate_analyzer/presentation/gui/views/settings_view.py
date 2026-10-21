"""Представление окна настроек приложения."""

import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.infrastructure.config.config_loader import save_settings
from certificate_analyzer.presentation.gui.widgets.responsive_bar import fit_dialog
from certificate_analyzer.presentation.gui.widgets.scrollable_panel import ScrollablePanel


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
        fit_dialog(self, width=760, height=420)

    def _build_ui(self) -> None:
        """Создает элементы пользовательского интерфейса диалога настроек.

        Returns:
            None
        """
        frame = ttk.Frame(self, padding=16, style="App.TFrame")
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
            tab_shell = ttk.Frame(self.notebook, padding=16, style="Status.TFrame")
            scroll = ScrollablePanel(tab_shell, autohide=True)
            scroll.pack(fill="both", expand=True)
            tab = scroll.body
            tab.columnconfigure(0, weight=1)
            self.notebook.add(tab_shell, text=title)
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
                self._add_hint(tab, len(values) * 2,
                    "Например, 30: статус «Истекает» появится, когда до окончания действия останется 30 дней или меньше.\n0 — не выделять сертификаты заранее. Порог используется и для уведомлений.")
            if title == "Мониторинг":
                self._add_hint(tab, len(values) * 2,
                    "Порог дней общий с вкладкой «Сертификаты».\nУправление фоновым процессом и автозапуском доступно в меню «Служба».")
            scroll.bind_mousewheel()

        note = ttk.Label(frame,
                  text="После сохранения перезапустите приложение и фоновый процесс. Существующие файлы автоматически не перемещаются.",
                  wraplength=640, style="Muted.TLabel")
        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.pack(side="bottom", fill="x", before=self.notebook)
        ttk.Button(buttons, text="Сохранить", command=self.save, style="Accent.TButton").pack(side="right")
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="right", padx=8)
        note.pack(side="bottom", fill="x", pady=12, before=self.notebook)
        note.bind("<Configure>", lambda event: note.configure(wraplength=max(100, event.width)))

    def _add_hint(self, tab, row, text):
        hint = ttk.Label(tab, text=text, style="Settings.Hint.TLabel", wraplength=600)
        hint.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        tab.bind("<Configure>", lambda event: hint.configure(wraplength=max(100, event.width)), add="+")

    def _add_field(self, tab, row, label, variable, browse_kind):
        ttk.Label(tab, text=label, style="Status.TLabel").grid(row=row * 2, column=0, columnspan=2, sticky="w", pady=(4 if row == 0 else 16, 6))
        if browse_kind == "days":
            ttk.Spinbox(tab, from_=0, to=3650, increment=1, textvariable=variable, width=10, style="Settings.TSpinbox").grid(row=row * 2 + 1, column=0, sticky="w")
        else:
            ttk.Entry(tab, textvariable=variable, width=32, style="Settings.TEntry").grid(row=row * 2 + 1, column=0, sticky="ew")
        if browse_kind and browse_kind != "days":
            ttk.Button(tab, text="Обзор…", command=lambda: self._browse(variable, browse_kind)).grid(row=row * 2 + 1, column=1, padx=(10, 0))

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
