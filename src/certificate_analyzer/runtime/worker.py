"""Фоновый воркер периодического мониторинга сертификатов."""

import logging
import threading
from typing import Any

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.services.monitoring_service import (
    MonitoringService,
)
from certificate_analyzer.application.services.notification_service import (
    PushNotificationManager,
)
from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.runtime.scheduler import Scheduler

logger = logging.getLogger(__name__)


class MonitoringWorker:
    """Оркестратор фонового мониторинга записей сертификатов без сканирования папок."""

    def __init__(self, settings=None, notifier=None, *, application=None) -> None:
        """Инициализирует воркер мониторинга.

        Args:
            settings: Конфигурация приложения (опционально).
            notifier: Менеджер отправки уведомлений (опционально).
            application: Готовый ApplicationContainer (опционально).
        """
        self.app = application or create_application(settings=settings)
        self._owns_application = application is None
        self.settings = self.app.settings
        self.notifier = notifier or self.app.notifications or PushNotificationManager()
        self.stop_event = threading.Event()
        self.errors: dict[str, str] = {}

        if notifier is not None:
            self._service = MonitoringService(
                certificate_service=self.app.certificates,
                report_service=self.app.reports,
                notification_manager=self.notifier,
                settings=self.settings,
            )
        elif self.app.monitoring is not None:
            self._service = self.app.monitoring
        else:
            self._service = MonitoringService(
                certificate_service=self.app.certificates,
                report_service=self.app.reports,
                notification_manager=self.notifier,
                settings=self.settings,
            )

        self._scheduler: Scheduler | None = None

    def run_once(self) -> list[dict[str, Any]]:
        """Выполняет однократную проверку сертификатов и сохранение отчета.

        Returns:
            list[dict[str, Any]]: Список сериализованных словарей проверенных сертификатов.
        """
        result = self._service.run_cycle()
        self.errors = result.errors
        return [certificate_to_dict(cert) for cert in result.records]

    def stop(self) -> None:
        """Сигнализирует о необходимости остановки фонового процесса."""
        self.stop_event.set()
        if self._scheduler is not None:
            self._scheduler.stop()

    def close(self) -> None:
        """Завершает работу воркера и освобождает ресурсы контейнера приложения."""
        self.stop()
        if self._owns_application:
            self.app.close()

    def run_forever(self) -> None:
        """Запускает непрерывный цикл периодической проверки в соответствии с интервалом."""
        try:
            while not self.stop_event.is_set():
                try:
                    self.run_once()
                except Exception:
                    logger.exception("Ошибка фоновой проверки")
                if self.stop_event.wait(self.settings.check_interval):
                    break
        finally:
            self.close()
