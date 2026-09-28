"""Главное меню приложения и обработчики горячих клавиш."""

import tkinter as tk
from typing import Any


class AppMenuBar:
    """Компонент главного меню графического интерфейса приложения."""

    def __init__(
        self,
        root: tk.Tk | tk.Toplevel,
        handler: Any,
        status_labels: dict[str, Any],
        status_var: tk.StringVar,
    ) -> None:
        """Инициализирует главное меню приложения и привязывает горячие клавиши.

        Args:
            root: Корневое окно Tkinter.
            handler: Объект-обработчик действий меню (обычно экземпляр главного окна).
            status_labels: Словарь названий статусов сертификатов и их значений.
            status_var: Tkinter-переменная для радиокнопок фильтра по статусу.
        """
        self.root = root
        self.handler = handler
        self.status_labels = status_labels
        self.status_var = status_var

        self.menubar = tk.Menu(self.root, tearoff=0)
        self._build_file_menu()
        self._build_edit_menu()
        self._build_view_menu()
        self._build_tools_menu()
        self._build_help_menu()

        self.root.config(menu=self.menubar)
        self._bind_hotkeys()

    def _build_file_menu(self) -> None:
        """Создает выпадающее меню «Файл» с подменю «Импорт» и «Экспорт».

        Returns:
            None
        """
        file_menu = tk.Menu(self.menubar, tearoff=0)

        import_menu = tk.Menu(file_menu, tearoff=0)
        import_menu.add_command(
            label="Импорт файлов сертификатов...",
            command=self.handler.import_files,
            accelerator="Ctrl+O",
        )
        import_menu.add_command(
            label="Импорт папки с сертификатами...",
            command=self.handler.import_folder,
        )
        import_menu.add_separator()
        import_menu.add_command(
            label="Импорт телефонного справочника...",
            command=self.handler.import_phonebook,
        )
        file_menu.add_cascade(label="Импорт", menu=import_menu)

        export_menu = tk.Menu(file_menu, tearoff=0)
        export_menu.add_command(
            label="Экспорт отчёта (Excel / PDF)...",
            command=self.handler.export_report,
            accelerator="Ctrl+E",
        )
        file_menu.add_cascade(label="Экспорт", menu=export_menu)

        file_menu.add_separator()
        file_menu.add_command(
            label="Настройки...",
            command=self.handler.show_settings,
            accelerator="Ctrl+,",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Выход",
            command=self.handler.close,
            accelerator="Alt+F4",
        )
        self.menubar.add_cascade(label="Файл", menu=file_menu)

    def _build_edit_menu(self) -> None:
        """Создает выпадающее меню «Правка».

        Returns:
            None
        """
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(
            label="Обновить записи",
            command=self.handler.refresh,
            accelerator="F5",
        )
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Открыть сертификат",
            command=self.handler.open_certificate,
        )
        edit_menu.add_command(
            label="Показать в проводнике",
            command=self.handler.reveal_certificate_file,
        )
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Удалить из учета",
            command=self.handler.delete_selected,
            accelerator="Delete",
        )
        edit_menu.add_command(
            label="Удалить физический файл (в корзину)...",
            command=self.handler.delete_physical_file,
            accelerator="Shift+Delete",
        )
        self.menubar.add_cascade(label="Правка", menu=edit_menu)

    def _build_view_menu(self) -> None:
        """Создает выпадающее меню «Вид» с фильтром по статусу и переключением вкладок.

        Returns:
            None
        """
        view_menu = tk.Menu(self.menubar, tearoff=0)

        status_menu = tk.Menu(view_menu, tearoff=0)
        for label in self.status_labels:
            status_menu.add_radiobutton(
                label=label,
                variable=self.status_var,
                value=label,
                command=lambda: self.handler.refresh(reset=True),
            )


        view_menu.add_command(
            label="Вкладка «Сертификаты»",
            command=self.handler.show_certificates_tab,
            accelerator="Ctrl+1",
        )
        view_menu.add_command(
            label="Вкладка «Заявки»",
            command=self.handler.show_requests_tab,
            accelerator="Ctrl+2",
        )
        view_menu.add_command(
            label="Вкладка «Сотрудники»",
            command=self.handler.show_employees_tab,
            accelerator="Ctrl+3",
        )
        view_menu.add_command(
            label="Вкладка «МЧД»",
            command=self.handler.show_mchd_tab,
            accelerator="Ctrl+4",
        )
        self.menubar.add_cascade(label="Вид", menu=view_menu)

    def _build_tools_menu(self) -> None:
        """Создает выпадающее меню «Инструменты».

        Returns:
            None
        """
        tools_menu = tk.Menu(self.menubar, tearoff=0)

        employees_menu = tk.Menu(tools_menu, tearoff=0)
        employees_menu.add_command(
            label="Справочник сотрудников",
            command=self.handler.show_employees_tab,
        )
        employees_menu.add_command(
            label="Добавить сотрудника...",
            command=self.handler.create_employee,
        )
        tools_menu.add_cascade(label="Сотрудники", menu=employees_menu)

        requests_menu = tk.Menu(tools_menu, tearoff=0)
        requests_menu.add_command(
            label="Список заявок",
            command=self.handler.show_requests_tab,
        )
        requests_menu.add_command(
            label="Создать новую заявку...",
            command=self.handler.create_certificate_request,
            accelerator="Ctrl+N",
        )
        tools_menu.add_cascade(label="Заявки на сертификаты", menu=requests_menu)

        mchd_menu = tk.Menu(tools_menu, tearoff=0)
        mchd_menu.add_command(
            label="Вкладка доверенностей (МЧД)",
            command=self.handler.show_mchd_tab,
            accelerator="Ctrl+4",
        )
        mchd_menu.add_command(
            label="Сканировать папку XML МЧД...",
            command=self.handler.open_mchd,
        )
        tools_menu.add_cascade(
            label="Машиночитаемые доверенности (МЧД)", menu=mchd_menu
        )

        tools_menu.add_separator()
        tools_menu.add_command(
            label="Журнал аудита...",
            command=self.handler.show_audit_window,
        )
        tools_menu.add_command(
            label="История уведомлений...",
            command=self.handler.show_notification_history,
        )
        tools_menu.add_command(
            label="Нормативные документы...",
            command=self.handler.show_normative_docs,
        )
        self.menubar.add_cascade(label="Инструменты", menu=tools_menu)

    def _build_help_menu(self) -> None:
        """Создает выпадающее меню «Справка».

        Returns:
            None
        """
        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(
            label="Нормативная база (законы и приказы)...",
            command=self.handler.show_normative_docs,
        )
        help_menu.add_separator()
        help_menu.add_command(
            label="О программе...",
            command=self.handler.show_about,
        )
        self.menubar.add_cascade(label="Справка", menu=help_menu)

    def _bind_hotkeys(self) -> None:
        """Регистрирует клавиатурные комбинации для быстрого доступа к функциям.

        Returns:
            None
        """
        self.root.bind("<Control-o>", lambda _: self.handler.import_files())
        self.root.bind("<Control-O>", lambda _: self.handler.import_files())
        self.root.bind("<Control-e>", lambda _: self.handler.export_report())
        self.root.bind("<Control-E>", lambda _: self.handler.export_report())
        self.root.bind("<F5>", lambda _: self.handler.refresh())
        self.root.bind("<Control-Key-1>", lambda _: self.handler.show_certificates_tab())
        self.root.bind("<Control-Key-2>", lambda _: self.handler.show_requests_tab())
        self.root.bind("<Control-Key-3>", lambda _: self.handler.show_employees_tab())
        self.root.bind("<Control-Key-4>", lambda _: self.handler.show_mchd_tab())
        self.root.bind(
            "<Control-n>", lambda _: self.handler.create_certificate_request()
        )
        self.root.bind(
            "<Control-N>", lambda _: self.handler.create_certificate_request()
        )
        self.root.bind("<Shift-Delete>", lambda _: self.handler.delete_physical_file())
