"""Управление фоновыми операциями и асинхронными задачами графического интерфейса."""

from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Any, Callable


class TaskRunner:
    """Оркестратор выполнения длительных задач в фоновом потоке с визуализацией прогресса."""

    def __init__(
        self,
        root: tk.Widget,
        progress_bar: ttk.Progressbar | None = None,
        on_message: Callable[[str], None] | None = None,
        on_active_change: Callable[[bool], None] | None = None,
        on_close_ready: Callable[[], None] | None = None,
    ) -> None:
        """Инициализирует менеджер фоновых задач.

        Args:
            root: Корневой виджет Tkinter для вызова таймеров и очередей событий.
            progress_bar: Виджет прогресс-бара для отображения активности.
            on_message: Функция вывода текстовых сообщений о состоянии задачи.
            on_active_change: Колбэк изменения активности (True при старте, False при завершении).
            on_close_ready: Колбэк, вызываемый при готовности к закрытию окна после завершения задач.
        """
        self.root = root
        self.progress_bar = progress_bar
        self.on_message = on_message or (lambda _: None)
        self.on_active_change = on_active_change or (lambda _: None)
        self.on_close_ready = on_close_ready or (lambda: None)
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="gui-task-runner"
        )
        self.future: Future[Any] | None = None
        self.closing = False

    def submit(
        self,
        action: Callable[[], Any],
        finished: Callable[[Any], None] | None = None,
        post_refresh: Callable[[], None] | None = None,
    ) -> bool:
        """Запускает операцию в фоновом потоке.

        Args:
            action: Вызываемая функция операции без параметров.
            finished: Функция обратного вызова, принимающая результат выполнения action.
            post_refresh: Необязательная функция обновления интерфейса после завершения.

        Returns:
            bool: True, если задача успешно отправлена на выполнение, иначе False.
        """
        if self.future and not self.future.done():
            messagebox.showinfo(
                "Выполняется операция",
                "Дождитесь завершения текущей операции.",
                parent=self.root,
            )
            return False
        if self.closing:
            return False

        if self.progress_bar:
            self.progress_bar.start()
        self.on_message("Выполняется операция…")
        self.on_active_change(True)

        self.future = self.executor.submit(action)
        self.root.after(50, lambda: self._poll(finished, post_refresh))
        return True

    def _poll(
        self,
        finished: Callable[[Any], None] | None,
        post_refresh: Callable[[], None] | None,
    ) -> None:
        """Опрашивает статус завершения фонового потока.

        Args:
            finished: Колбэк с результатом задачи.
            post_refresh: Колбэк обновления интерфейса.

        Returns:
            None
        """
        if not self.future:
            return
        if not self.future.done():
            self.root.after(50, lambda: self._poll(finished, post_refresh))
            return

        if self.progress_bar:
            self.progress_bar.stop()
            self.progress_bar.configure(value=0)
        self.on_active_change(False)

        try:
            result = self.future.result()
            if not self.closing:
                if finished:
                    finished(result)
                if post_refresh:
                    post_refresh()
        except Exception as exc:
            if not self.closing:
                self.on_message("Операция не завершена")
                messagebox.showerror("Ошибка", str(exc), parent=self.root)
        finally:
            self.future = None
            if self.closing:
                self.on_close_ready()

    def shutdown(self, wait: bool = True) -> None:
        """Останавливает пул потоков.

        Args:
            wait: Ожидать ли завершения текущих задач.

        Returns:
            None
        """
        self.executor.shutdown(wait=wait)
