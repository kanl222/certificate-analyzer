"""Сервис регулярного мониторинга сроков действия сертификатов и целостности хранилища."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.models.certificate import Certificate

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MonitoringResult:
    """Результат выполнения одного цикла мониторинга сертификатов.

    Attributes:
        records: Список проверенных сертификатов из базы данных.
        errors: Словарь ошибок (путь или отпечаток -> описание проблемы).
        counts: Словарь со статистикой распределения статусов сертификатов.
        report_path: Путь к сформированному Excel-отчёту (если отчёт был сохранён).
    """

    records: list[Certificate] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    report_path: Path | None = None


class MonitoringService:
    """Сервис мониторинга сертификатов, генерации отчетов и отправки оповещений."""

    def __init__(
        self,
        certificate_service: Any,
        report_service: Any,
        notification_manager: Any,
        settings: Any,
    ) -> None:
        """Инициализирует сервис мониторинга.

        Args:
            certificate_service: Сервис для получения записей сертификатов и статистики.
            report_service: Сервис для экспорта отчетов.
            notification_manager: Менеджер отправки push-уведомлений.
            settings: Конфигурация приложения с путями экспорта.
        """
        self._certificates = certificate_service
        self._reports = report_service
        self._notifications = notification_manager
        self._settings = settings

    def run_cycle(self) -> MonitoringResult:
        """Выполняет один цикл проверки сертификатов.

        Проверяет наличие файлов в хранилище, пересчитывает актуальные статусы,
        сохраняет сводный отчет `monitoring.xlsx` и отправляет системные уведомления.

        Returns:
            MonitoringResult: Объект со статистикой, проверенными записями и ошибками.
        """
        records = self._certificates.list(CertificateQuery(limit=None))
        errors: dict[str, str] = {}

        for cert in records:
            path_str = cert.source_path
            if not path_str or not Path(path_str).is_file():
                key = path_str or cert.fingerprint_sha256
                errors[key] = "Файл сертификата отсутствует"
                logger.warning("%s: Файл сертификата отсутствует", key)

        report_path: Path | None = None
        counts: dict[str, int] = {}

        if records:
            export_folder = (
                Path(self._settings.export_folder)
                if self._settings and self._settings.export_folder
                else Path(".")
            )
            export_folder.mkdir(parents=True, exist_ok=True)
            report_path = export_folder / "monitoring.xlsx"

            try:
                self._reports.export("xlsx", records, [], report_path)
            except Exception as exc:
                logger.error("Ошибка при сохранении отчёта мониторинга: %s", exc)

            counts = self._certificates.statistics()
            if self._notifications is not None:
                try:
                    self._notifications.check_and_notify_expired(
                        counts.get("EXPIRED", 0),
                        counts.get("EXPIRING_SOON", 0),
                        counts.get("total", 0),
                    )
                except Exception as exc:
                    logger.error("Ошибка отправки уведомления мониторинга: %s", exc)

        return MonitoringResult(
            records=records,
            errors=errors,
            counts=counts,
            report_path=report_path,
        )
