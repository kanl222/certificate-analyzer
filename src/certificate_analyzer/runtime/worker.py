import logging
import threading
from pathlib import Path

from certificate_analyzer.application.services.certificate_service import (
    CertificateAnalyzerCore,
)
from certificate_analyzer.application.services.notification_service import (
    PushNotificationManager,
)
from certificate_analyzer.infrastructure.config.config_loader import load_settings


class MonitoringWorker:
    def __init__(self, settings=None, notifier=None):
        self.settings = settings or load_settings()
        self.core = CertificateAnalyzerCore(self.settings)
        self.notifier = notifier or PushNotificationManager()
        self.stop_event = threading.Event()
        self.errors = {}

    def run_once(self):
        rows, errors = [], {}
        for folder in dict.fromkeys(self.settings.folders.values()):
            try:
                self.core.scan_certificates(folder)
                rows.extend(self.core.parse_certificates())
                errors.update(self.core.errors)
            except OSError as exc:
                errors[folder] = str(exc)
        self.errors = errors
        for path, error in errors.items():
            logging.getLogger(__name__).warning("%s: %s", path, error)
        if rows:
            self.core.export_to_excel(
                rows, str(Path(self.settings.export_folder) / "monitoring.xlsx")
            )
            self.notifier.check_and_notify_expired(
                sum(r["status"] == "Просрочен" for r in rows),
                sum("Истекает" in r["status"] for r in rows),
                len(rows),
            )
        return rows

    def stop(self):
        self.stop_event.set()

    def run_forever(self):
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logging.getLogger(__name__).exception("Ошибка фоновой проверки")
            self.stop_event.wait(self.settings.check_interval)
