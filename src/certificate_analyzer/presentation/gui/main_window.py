"""Главное окно приложения Certificate Analyzer и координация подсистем."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.runtime.service_status import monitoring_process_status
from certificate_analyzer.presentation.gui.menu_bar import AppMenuBar
from certificate_analyzer.presentation.gui.styles import configure_gui_styles
from certificate_analyzer.presentation.gui.task_runner import TaskRunner
from certificate_analyzer.presentation.gui.views.audit_view import AuditWindow
from certificate_analyzer.presentation.gui.views.certificates_view import (
    COLUMNS,
    STATUS_LABELS,
    CertificatesView,
)
from certificate_analyzer.presentation.gui.views.employees_view import (
    EmployeesView,
)
from certificate_analyzer.presentation.gui.views.history_view import (
    NotificationHistory,
)
from certificate_analyzer.presentation.gui.views.mchd_view import MchdView
from certificate_analyzer.presentation.gui.views.normative_view import (
    NormativeWindow,
)
from certificate_analyzer.presentation.gui.views.requests_view import (
    RequestsView,
)
from certificate_analyzer.presentation.gui.views.settings_view import (
    SettingsDialog,
)

__all__ = [
    "COLUMNS",
    "STATUS_LABELS",
    "CertificateAnalyzerApp",
]


class CertificateAnalyzerApp:
    """Главный координатор приложения и контейнер вкладок графического интерфейса."""

    def __init__(
        self,
        root: tk.Tk | tk.Toplevel,
        application: Any = None,
        config_path: Any = None,
        destroy_root: bool = True,
    ) -> None:
        """Инициализирует главное окно приложения и его компоненты.

        Args:
            root: Корневое окно Tkinter.
            application: Экземпляр контейнера сервисов ApplicationContainer.
            config_path: Путь к файлу конфигурации settings.json.
            destroy_root: Уничтожать ли корневое окно при выходе из приложения.
        """
        self.root = root
        self.app = application or create_application(config_path)
        self._owns_app = application is None
        self._destroy_root = destroy_root
        self.config_path = config_path

        self.closing = False
        self.refresh_after: str | None = None
        self.monitor_status_after: str | None = None
        self._notification_history: NotificationHistory | None = None
        self.root.title("Менеджер сертификатов")
        self._configure_window_geometry()

        self._build_ui()
        self.refresh()
        self._schedule_refresh()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_window_geometry(self) -> None:
        """Выбирает удобный стартовый размер с учётом разрешения экрана."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        available_width = max(760, screen_width - 40)
        available_height = max(560, screen_height - 80)
        width = min(1440, max(1000, int(screen_width * 0.8)), available_width)
        height = min(900, max(680, int(screen_height * 0.82)), available_height)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(1000, width), min(650, height))

    def _build_ui(self) -> None:
        """Инициализирует графические элементы интерфейса, меню и вкладки.

        Returns:
            None
        """
        configure_gui_styles(self.root)
        frame = ttk.Frame(self.root, padding=12, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        # Контейнер вкладок
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.enable_traversal()

        # Вкладка 1: Сертификаты
        self.certs_tab = CertificatesView(
            self.notebook,
            application=self.app,
            submit_task=self._submit,
            on_message=self.set_message,
            config_path=self.config_path,
            padding=6,
        )
        self.certificates_view = self.certs_tab

        # Вкладка 2: Заявки
        self.requests_tab = ttk.Frame(self.notebook, padding=6)
        self.requests_view = RequestsView(
            self.requests_tab,
            application=self.app,
            on_message=self.set_message,
        )
        self.requests_view.pack(fill="both", expand=True)

        # Вкладка 3: Сотрудники
        self.employees_tab = ttk.Frame(self.notebook, padding=6)
        self.employees_view = EmployeesView(
            self.employees_tab,
            application=self.app,
            on_message=self.set_message,
            on_create_request=self._open_request_dialog_for_employee,
        )
        self.employees_view.pack(fill="both", expand=True)

        # Вкладка 4: МЧД
        self.mchd_tab = ttk.Frame(self.notebook, padding=6)
        self.mchd_view = MchdView(
            self.mchd_tab,
            application=self.app,
            on_message=self.set_message,
        )
        self.mchd_view.pack(fill="both", expand=True)

        self.notebook.add(self.certs_tab, text="Сертификаты")
        self.notebook.add(self.requests_tab, text="Заявки")
        self.notebook.add(self.employees_tab, text="Сотрудники")
        self.notebook.add(self.mchd_tab, text="МЧД")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Статусная строка и компактный индикатор фоновых операций
        status_bar = ttk.Frame(frame, style="Status.TFrame", padding=(8, 5))
        status_bar.pack(fill="x", pady=(4, 0))
        self.message = ttk.Label(status_bar, text="Загрузка…", style="Status.TLabel")
        self.message.pack(side="left")
        self.progress = ttk.Progressbar(
            status_bar,
            mode="indeterminate",
            length=120,
        )
        self.monitor_status = ttk.Label(
            status_bar,
            text="Мониторинг: проверка…",
            style="Status.TLabel",
        )
        self.monitor_status.pack(side="right")

        # Менеджер фоновых задач
        self.task_runner = TaskRunner(
            root=self.root,
            progress_bar=self.progress,
            on_message=self.set_message,
            on_active_change=self._on_task_activity_change,
            on_close_ready=self._finish_close,
        )

        # Главное меню приложения
        self.menu_bar = AppMenuBar(
            root=self.root,
            handler=self,
            status_labels=STATUS_LABELS,
            status_var=self.certs_tab.status_var,
        )
        self.menubar = self.menu_bar.menubar

        self._schedule_monitor_status()

    def _schedule_monitor_status(self) -> None:
        """Обновляет в нижней панели состояние системной службы мониторинга."""
        if self.closing:
            return
        self.monitor_status.config(text=monitoring_process_status(self.app.settings))
        self.monitor_status_after = self.root.after(
            30000, self._schedule_monitor_status
        )

    def _on_task_activity_change(self, is_active: bool) -> None:
        """Переключает доступность кнопок импорта при запуске/завершении фоновых задач.

        Args:
            is_active: Флаг активности фоновой задачи.

        Returns:
            None
        """
        state = "disabled" if is_active else "normal"
        for button in self.import_buttons:
            button.config(state=state)
        if is_active:
            self.progress.pack(
                side="left",
                padx=(12, 0),
                after=self.message,
            )
        else:
            self.progress.pack_forget()

    def set_message(self, text: str) -> None:
        """Устанавливает текст статусной строки приложения.

        Args:
            text: Текст сообщения для отображения.

        Returns:
            None
        """
        if hasattr(self, "message") and self.message.winfo_exists():
            self.message.config(text=text)

    # ---------------- Делегаты совместимости для вкладки сертификатов ----------------

    @property
    def tree(self) -> ttk.Treeview:
        """Возвращает дерево таблицы сертификатов."""
        return self.certs_tab.tree

    @property
    def search_var(self) -> tk.StringVar:
        """Возвращает переменную строки поиска сертификатов."""
        return self.certs_tab.search_var

    @property
    def status_var(self) -> tk.StringVar:
        """Возвращает переменную фильтра по статусу сертификатов."""
        return self.certs_tab.status_var

    @property
    def date_from_var(self) -> tk.StringVar:
        """Возвращает переменную фильтра даты начала срока действия."""
        return self.certs_tab.date_from_var

    @property
    def date_to_var(self) -> tk.StringVar:
        """Возвращает переменную фильтра даты окончания срока действия."""
        return self.certs_tab.date_to_var

    @property
    def details(self) -> Any:
        """Возвращает виджет подробной информации о выбранном сертификате."""
        return self.certs_tab.details

    @property
    def import_buttons(self) -> list[ttk.Button]:
        """Возвращает кнопки панели импорта сертификатов."""
        return self.certs_tab.import_buttons

    @property
    def stats_label(self) -> ttk.Label:
        """Возвращает виджет метки статистики сертификатов."""
        return self.certs_tab.stats_label

    @property
    def page_label(self) -> ttk.Label:
        """Возвращает виджет метки текущей страницы пагинации."""
        return self.certs_tab.page_label

    @property
    def previous_button(self) -> ttk.Button:
        """Возвращает кнопку перехода на предыдущую страницу."""
        return self.certs_tab.previous_button

    @property
    def next_button(self) -> ttk.Button:
        """Возвращает кнопку перехода на следующую страницу."""
        return self.certs_tab.next_button

    @property
    def offset(self) -> int:
        """Возвращает текущее смещение пагинации сертификатов."""
        return self.certs_tab.offset

    @offset.setter
    def offset(self, val: int) -> None:
        self.certs_tab.offset = val

    @property
    def sort(self) -> str:
        """Возвращает текущую колонку сортировки сертификатов."""
        return self.certs_tab.sort

    @sort.setter
    def sort(self, val: str) -> None:
        self.certs_tab.sort = val

    @property
    def descending(self) -> bool:
        """Возвращает направление сортировки сертификатов."""
        return self.certs_tab.descending

    @descending.setter
    def descending(self, val: bool) -> None:
        self.certs_tab.descending = val

    @property
    def query(self) -> Any:
        """Возвращает текущий запрос выборки сертификатов."""
        return self.certs_tab.query

    @query.setter
    def query(self, val: Any) -> None:
        self.certs_tab.query = val

    @property
    def _page(self) -> dict[str, Any]:
        """Возвращает словарь сертификатов текущей страницы по отпечаткам."""
        return self.certs_tab._page

    @_page.setter
    def _page(self, val: dict[str, Any]) -> None:
        self.certs_tab._page = val

    @property
    def future(self) -> Any:
        """Возвращает текущий Future выполняющейся фоновой задачи."""
        return self.task_runner.future

    @future.setter
    def future(self, val: Any) -> None:
        self.task_runner.future = val

    @property
    def executor(self) -> Any:
        """Возвращает ThreadPoolExecutor менеджера задач."""
        return self.task_runner.executor

    def _submit(
        self,
        action: Callable[[], Any],
        finished: Callable[[Any], None],
    ) -> bool:
        """Отправляет операцию на выполнение в фоновый поток TaskRunner.

        Args:
            action: Функция операции.
            finished: Колбэк получения результата.

        Returns:
            bool: True при успешном запуске задачи.
        """
        return self.task_runner.submit(
            action=action,
            finished=finished,
            post_refresh=self._refresh_active_tab,
        )

    def _import_finished(self, result: Any) -> None:
        """Отображает результат импорта сертификатов.

        Args:
            result: Результат операции импорта ImportResult.

        Returns:
            None
        """
        self.certs_tab._import_finished(result)

    def _apply_search(self) -> None:
        """Применяет поисковую строку к списку сертификатов.

        Returns:
            None
        """
        self.certs_tab._apply_search()

    def clear_filters(self) -> None:
        """Сбрасывает фильтры вкладки сертификатов.

        Returns:
            None
        """
        self.certs_tab.clear_filters()

    def refresh(self, reset: bool = False) -> None:
        """Обновляет данные активной таблицы сертификатов.

        Args:
            reset: Сбросить ли пагинацию на первую страницу.

        Returns:
            None
        """
        if self.closing:
            return
        self.certs_tab.refresh(reset=reset)

    def sort_by(self, key: str) -> None:
        """Сортирует сертификаты по указанной колонке.

        Args:
            key: Имя поля для сортировки.

        Returns:
            None
        """
        self.certs_tab.sort_by(key)

    def change_page(self, delta: int) -> None:
        """Перелистывает страницу списка сертификатов.

        Args:
            delta: Смещение (+100 или -100).

        Returns:
            None
        """
        self.certs_tab.change_page(delta)

    def show_details(self, _=None) -> None:
        """Отображает подробности выбранного сертификата.

        Args:
            _: Событие Tkinter.

        Returns:
            None
        """
        self.certs_tab.show_details(_)

    def open_certificate(self, _=None) -> None:
        """Открывает выбранный файл сертификата системным просмотрщиком.

        Args:
            _: Событие Tkinter.

        Returns:
            None
        """
        self.certs_tab.open_certificate(_)

    def reveal_certificate_file(self, _=None) -> None:
        """Показывает файл выбранного сертификата в проводнике.

        Args:
            _: Событие Tkinter.

        Returns:
            None
        """
        self.certs_tab.reveal_certificate_file(_)

    def delete_physical_file(self) -> None:
        """Удаляет файл выбранного сертификата в корзину.

        Returns:
            None
        """
        self.certs_tab.delete_physical_file()

    def delete_selected(self) -> None:
        """Удаляет выбранные сертификаты из учета БД.

        Returns:
            None
        """
        self.certs_tab.delete_selected()

    def import_files(self) -> None:
        """Запускает диалог импорта файлов сертификатов.

        Returns:
            None
        """
        self.certs_tab.import_files()

    def import_folder(self) -> None:
        """Запускает диалог импорта папки с сертификатами.

        Returns:
            None
        """
        self.certs_tab.import_folder()

    def import_phonebook(self) -> None:
        """Запускает диалог импорта телефонного справочника.

        Returns:
            None
        """
        self.certs_tab.import_phonebook()

    def export_report(self) -> None:
        """Запускает экспорт текущих записей сертификатов в отчёт.

        Returns:
            None
        """
        self.certs_tab.export_report()

    # ---------------- Навигация по вкладкам ----------------

    def _on_tab_changed(self, event: Any = None) -> None:
        """Обрабатывает событие переключения вкладок главного окна.

        Args:
            event: Событие Tkinter VirtualEvent.

        Returns:
            None
        """
        self._refresh_active_tab()

    def _refresh_active_tab(self) -> None:
        """Обновляет данные и нижнюю сводку только выбранной вкладки."""
        selected_tab = self.notebook.select()
        if not selected_tab:
            return
        tab_text = self.notebook.tab(selected_tab, "text")
        if tab_text == "Заявки" and hasattr(self, "requests_view"):
            self.requests_view.refresh()
        elif tab_text == "Сотрудники" and hasattr(self, "employees_view"):
            self.employees_view.refresh()
        elif tab_text == "МЧД" and hasattr(self, "mchd_view"):
            self.mchd_view.refresh()
        elif tab_text == "Сертификаты":
            self.refresh()

    def _open_request_dialog_for_employee(self, employee: Any) -> None:
        """Открывает форму заявки с данными выбранного сотрудника."""
        self.show_requests_tab()
        self.requests_view.show_create_dialog_for(
            employee.full_name,
            employee.department or "",
        )

    def show_requests_tab(self) -> None:
        """Активирует вкладку заявок на сертификаты.

        Returns:
            None
        """
        self.notebook.select(self.requests_tab)

    def show_employees_tab(self) -> None:
        """Активирует вкладку сотрудников.

        Returns:
            None
        """
        self.notebook.select(self.employees_tab)

    def show_mchd_tab(self) -> None:
        """Активирует вкладку машиночитаемых доверенностей (МЧД).

        Returns:
            None
        """
        self.notebook.select(self.mchd_tab)

    def show_certificates_tab(self) -> None:
        """Активирует вкладку сертификатов.

        Returns:
            None
        """
        self.notebook.select(self.certs_tab)

    def create_certificate_request(self) -> None:
        """Переключается на вкладку заявок и открывает диалог создания новой заявки.

        Returns:
            None
        """
        self.show_requests_tab()
        if hasattr(self, "requests_view"):
            self.requests_view.show_create_dialog()

    def create_employee(self) -> None:
        """Переключается на вкладку сотрудников и открывает диалог добавления сотрудника.

        Returns:
            None
        """
        self.show_employees_tab()
        if hasattr(self, "employees_view"):
            self.employees_view.show_create_dialog()

    def open_mchd(self) -> None:
        """Переключается на вкладку МЧД и запускает диалог сканирования папки XML.

        Returns:
            None
        """
        self.show_mchd_tab()
        if hasattr(self, "mchd_view"):
            self.mchd_view.scan_folder()

    # ---------------- Вспомогательные окна и диалоги ----------------

    def show_service_log(self) -> None:
        from certificate_analyzer.presentation.gui.views.service_log_view import ServiceLogWindow
        ServiceLogWindow(self.root)

    def manage_background_process(self, action: str) -> None:
        """Управляет пользовательским демоном, не блокируя интерфейс."""
        from certificate_analyzer.runtime.user_daemon import (
            ensure_writer, stop_writer, restart_writer, set_autostart,
        )
        operations = {
            "start": (lambda: ensure_writer(self.app.settings), "Фоновый процесс запущен"),
            "stop": (lambda: stop_writer(self.app.settings), "Фоновый процесс остановлен. Запись данных недоступна до запуска."),
            "restart": (lambda: restart_writer(self.app.settings), "Фоновый процесс перезапущен"),
            "status": (lambda: monitoring_process_status(self.app.settings), None),
            "enable_autostart": (lambda: set_autostart(True, self.config_path), "Автозапуск при входе включён"),
            "disable_autostart": (lambda: set_autostart(False, self.config_path), "Автозапуск при входе отключён"),
        }
        operation, message = operations[action]

        def finished(result):
            self.monitor_status.config(text=monitoring_process_status(self.app.settings))
            self.set_message(message or result)

        self.task_runner.submit(action=operation, finished=finished)

    def show_settings(self) -> None:
        """Открывает диалоговое окно настроек хранилища и параметров приложения.

        Returns:
            None
        """
        SettingsDialog(
            parent=self.root,
            application=self.app,
            config_path=self.config_path,
            on_saved=self.set_message,
        )

    def show_audit_window(self) -> None:
        """Отображает окно журнала аудита операций с сертификатами и файлами.

        Returns:
            None
        """
        if hasattr(self.app, "audit"):
            AuditWindow(self.root, self.app.audit)
        else:
            messagebox.showinfo(
                "Журнал аудита", "Сервис аудита недоступен.", parent=self.root
            )

    def show_notification_history(self) -> None:
        """Отображает окно истории уведомлений приложения.

        Returns:
            None
        """
        if (
            not hasattr(self, "_notification_history")
            or self._notification_history is None
        ):
            self._notification_history = NotificationHistory(self.root)
        self._notification_history.show_history_window()

    def show_normative_docs(self) -> None:
        """Отображает окно с нормативными документами по ЭП и МЧД.

        Returns:
            None
        """
        NormativeWindow(self.root)

    def show_about(self) -> None:
        """Отображает диалоговое окно с информацией о приложении.

        Returns:
            None
        """
        messagebox.showinfo(
            "О программе",
            "Хранилище сертификатов (Certificate Analyzer)\n\n"
            "Инструмент для учёта, мониторинга сроков действия и анализа "
            "сертификатов ключей электронной подписи и машиночитаемых доверенностей (МЧД).\n\n"
            "Поддерживает форматы X.509 (.cer, .crt, .der, .pem) и XML МЧД.",
            parent=self.root,
        )

    # ---------------- Жизненный цикл приложения ----------------

    def _schedule_refresh(self) -> None:
        """Планирует периодическое автообновление данных раз в 60 секунд.

        Returns:
            None
        """
        def tick() -> None:
            self._refresh_active_tab()
            if not self.closing:
                self._schedule_refresh()

        self.refresh_after = self.root.after(60000, tick)

    def close(self) -> None:
        """Инициирует безопасное закрытие приложения с ожиданием фоновых задач.

        Returns:
            None
        """
        self.closing = True
        self.task_runner.closing = True
        if hasattr(self.certs_tab, "search_after") and self.certs_tab.search_after:
            self.certs_tab.after_cancel(self.certs_tab.search_after)
            self.certs_tab.search_after = None
        if self.refresh_after:
            self.root.after_cancel(self.refresh_after)
            self.refresh_after = None
        if self.monitor_status_after:
            self.root.after_cancel(self.monitor_status_after)
            self.monitor_status_after = None
        if self.task_runner.future:
            self.set_message("Завершение текущей операции перед закрытием…")
            return
        self._finish_close()

    def _finish_close(self) -> None:
        """Завершает работу фонового пула потоков, сервисов и закрывает окно.

        Returns:
            None
        """
        self.task_runner.shutdown(wait=True)
        if self._owns_app:
            self.app.close()
        if self._destroy_root and hasattr(self.root, "destroy"):
            self.root.destroy()
