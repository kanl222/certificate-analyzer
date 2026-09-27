"""Тесты сервиса регулярного мониторинга MonitoringService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock


from certificate_analyzer.application.services.monitoring_service import (
    MonitoringResult,
    MonitoringService,
)
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.domain.models.certificate import Certificate


def test_monitoring_service_empty_records(tmp_path):
    """Проверяет поведение при отсутствии записей в базе данных."""
    cert_service = MagicMock()
    cert_service.list.return_value = []
    report_service = MagicMock()
    notifier = MagicMock()
    settings = MagicMock()
    settings.export_folder = str(tmp_path)

    service = MonitoringService(
        certificate_service=cert_service,
        report_service=report_service,
        notification_manager=notifier,
        settings=settings,
    )

    result = service.run_cycle()
    assert isinstance(result, MonitoringResult)
    assert result.records == []
    assert result.errors == {}
    assert result.report_path is None
    report_service.export.assert_not_called()
    notifier.check_and_notify_expired.assert_not_called()


def test_monitoring_service_with_missing_files(tmp_path):
    """Проверяет регистрацию ошибок для отсутствующих на диске файлов сертификатов."""
    missing_file = tmp_path / "absent.cer"
    real_file = tmp_path / "exists.cer"
    real_file.write_text("dummy")

    cert1 = Certificate(
        fingerprint_sha256="1111111111111111111111111111111111111111111111111111111111111111",
        subject="User 1",
        issuer="CA 1",
        valid_from=datetime.now(UTC),
        valid_to=datetime.now(UTC),
        serial_number="123",
        status=CertificateStatus.ACTIVE,
        source_path=str(real_file),
    )
    cert2 = Certificate(
        fingerprint_sha256="2222222222222222222222222222222222222222222222222222222222222222",
        subject="User 2",
        issuer="CA 2",
        valid_from=datetime.now(UTC),
        valid_to=datetime.now(UTC),
        serial_number="456",
        status=CertificateStatus.EXPIRED,
        source_path=str(missing_file),
    )

    cert_service = MagicMock()
    cert_service.list.return_value = [cert1, cert2]
    cert_service.statistics.return_value = {"EXPIRED": 1, "EXPIRING_SOON": 0, "total": 2}

    report_service = MagicMock()
    notifier = MagicMock()
    settings = MagicMock()
    settings.export_folder = str(tmp_path / "reports")

    service = MonitoringService(
        certificate_service=cert_service,
        report_service=report_service,
        notification_manager=notifier,
        settings=settings,
    )

    result = service.run_cycle()

    assert len(result.records) == 2
    assert str(missing_file) in result.errors
    assert str(real_file) not in result.errors
    report_service.export.assert_called_once()
    notifier.check_and_notify_expired.assert_called_once_with(1, 0, 2)
    assert result.report_path == tmp_path / "reports" / "monitoring.xlsx"
