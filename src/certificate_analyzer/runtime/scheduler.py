"""Планировщик периодического выполнения фоновых задач (Scheduler)."""

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class Scheduler:
    """Управляет периодическим запуском задач в фоновом потоке.

    Позволяет запускать любую функцию с заданным интервалом в секундах,
    гарантирует корректное завершение потока при остановке приложения.
    """

    __slots__ = (
        "_interval",
        "_task",
        "_name",
        "_stop_event",
        "_thread",
        "_lock",
    )

    def __init__(
        self,
        interval_seconds: float,
        task: Callable[[], Any],
        name: str = "SchedulerThread",
    ) -> None:
        """Инициализирует планировщик фоновых задач.

        Args:
            interval_seconds: Интервал между итерациями в секундах.
            task: Функция обратного вызова без обязательных аргументов.
            name: Имя создаваемого фонового потока.

        Raises:
            ValueError: Если интервал меньше или равен нулю.
        """
        if interval_seconds <= 0:
            raise ValueError("Интервал планировщика должен быть положительным числом")
        self._interval = float(interval_seconds)
        self._task = task
        self._name = name
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()


    @property
    def is_running(self) -> bool:
        """Возвращает признак активности фонового потока планировщика."""
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def interval(self) -> float:
        """Возвращает текущий интервал запуска задач в секундах."""
        return self._interval

    @interval.setter
    def interval(self, value: float) -> None:
        """Задаёт новый интервал запуска задач.

        Новое значение применяется к следующей итерации цикла: если
        планировщик сейчас находится в ожидании, изменение вступит в
        силу только после текущего ожидания. Это осознанный компромисс
        в пользу простоты и отсутствия дополнительной синхронизации.

        Args:
            value: Новый интервал в секундах.

        Raises:
            ValueError: Если значение меньше или равно нулю.
        """
        if value <= 0:
            raise ValueError("Интервал планировщика должен быть положительным числом")
        self._interval = float(value)

    def start(self) -> None:
        """Запускает фоновый поток планировщика.

        Если поток уже запущен, повторный вызов игнорируется.
        """
        with self._lock:
            if self.is_running:
                logger.warning("Планировщик %s уже запущен", self._name)
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name=self._name,
                daemon=True,
            )
            self._thread.start()
            logger.info("Планировщик %s запущен с интервалом %.1f с", self._name, self._interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Останавливает фоновый поток планировщика.

        Безопасен для вызова как снаружи, так и изнутри самой задачи
        (`task`): в последнем случае поток не пытается присоединиться
        сам к себе (что вызвало бы RuntimeError), а лишь выставляет
        сигнал остановки — цикл завершится сразу после текущей итерации.

        Args:
            timeout: Максимальное время ожидания завершения потока в секундах.
        """
        current_thread = threading.current_thread()
        thread_to_join: threading.Thread | None = None

        with self._lock:
            if not self.is_running:
                return
            logger.info("Остановка планировщика %s...", self._name)
            self._stop_event.set()
            if self._thread is not current_thread:
                thread_to_join = self._thread
            self._thread = None

        # join выполняется вне лока, чтобы не блокировать параллельные
        # обращения к is_running/interval на время ожидания.
        if thread_to_join is not None:
            thread_to_join.join(timeout=timeout)
            if thread_to_join.is_alive():
                logger.warning("Поток планировщика %s не завершился за отведенный таймаут", self._name)

        logger.info("Планировщик %s остановлен", self._name)

    def _run_loop(self) -> None:
        """Внутренний цикл выполнения задачи планировщика."""
        stop_event = self._stop_event
        task = self._task
        while not stop_event.is_set():
            try:
                task()
            except Exception:
                logger.exception("Ошибка при выполнении запланированной задачи %s", self._name)

            if stop_event.wait(self._interval):
                break

    def __enter__(self) -> "Scheduler":
        """Вход в контекстный менеджер планировщика с автостартом."""
        self.start()
        return self

    def __exit__(self, *_) -> None:
        """Выход из контекстного менеджера с гарантированной остановкой."""
        self.stop()
