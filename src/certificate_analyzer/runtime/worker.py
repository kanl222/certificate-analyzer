"""Фоновый рабочий процесс (Worker)."""


class MonitoringWorker:
    """Выполняет фоновые задачи мониторинга сертификатов и МЧД.
    Один и тот же worker используется на Windows (Service) и Linux (systemd).
    """

    def run_once(self) -> None:
        """Запускает один цикл проверки."""
        pass

    def run_forever(self) -> None:
        """Запускает бесконечный цикл проверок с заданным интервалом."""
        pass
