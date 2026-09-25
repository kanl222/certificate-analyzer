import logging
import threading
from pathlib import Path

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.application.services.notification_service import (
    PushNotificationManager,
)
from certificate_analyzer.bootstrap import create_application


class MonitoringWorker:
    """Monitor database records without importing or rescanning source folders."""

    def __init__(self, settings=None, notifier=None, *, application=None):
        self.app = application or create_application(settings=settings)
        self._owns_application = application is None
        self.settings = self.app.settings
        self.notifier = notifier or PushNotificationManager()
        self.stop_event = threading.Event()
        self.errors = {}

    def run_once(self):
        records = self.app.certificates.list(CertificateQuery(limit=None))
        self.errors = {
            c.source_path or c.fingerprint_sha256: "Файл сертификата отсутствует"
            for c in records
            if not c.source_path or not Path(c.source_path).is_file()
        }
        for path, error in self.errors.items():
            logging.getLogger(__name__).warning("%s: %s", path, error)
        if records:
            self.app.reports.export(
                "xlsx",
                records,
                [],
                Path(self.settings.export_folder) / "monitoring.xlsx",
            )
            counts = self.app.certificates.statistics()
            self.notifier.check_and_notify_expired(
                counts["EXPIRED"], counts["EXPIRING_SOON"], counts["total"]
            )
        return [certificate_to_dict(cert) for cert in records]

    def stop(self):
        self.stop_event.set()

    def close(self):
        self.stop()
        if self._owns_application:
            self.app.close()

    def run_forever(self):
        try:
            while not self.stop_event.is_set():
                try:
                    self.run_once()
                except Exception:
                    logging.getLogger(__name__).exception("Ошибка фоновой проверки")
                self.stop_event.wait(self.settings.check_interval)
        finally:
            self.close()
