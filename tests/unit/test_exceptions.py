"""Тесты для иерархии исключений Certificate Analyzer."""

import pytest

from certificate_analyzer.exceptions import (
    CertificateAnalyzerError,
    CertificateNotFoundError,
    CertificateParseError,
    CertificateValidationError,
    ConfigurationError,
    DatabaseMigrationError,
    DomainError,
    InfrastructureError,
    InvalidRequestStatusTransitionError,
    MchdMergeError,
    MchdParseError,
    MchdValidationError,
    NotificationError,
    PhonebookParseError,
    ReportExportError,
    StorageError,
    TrashOperationError,
)


def test_domain_exceptions_inheritance():
    """Проверяет наследование доменных исключений от DomainError и CertificateAnalyzerError."""
    assert issubclass(DomainError, CertificateAnalyzerError)
    assert issubclass(CertificateNotFoundError, (DomainError, FileNotFoundError))
    assert issubclass(CertificateParseError, (DomainError, ValueError))
    assert issubclass(CertificateValidationError, (DomainError, ValueError))
    assert issubclass(MchdParseError, (DomainError, ValueError))
    assert issubclass(MchdValidationError, (DomainError, ValueError))
    assert issubclass(MchdMergeError, (DomainError, ValueError))
    assert issubclass(PhonebookParseError, (DomainError, ValueError))
    assert issubclass(InvalidRequestStatusTransitionError, (DomainError, ValueError))


def test_infrastructure_exceptions_inheritance():
    """Проверяет наследование инфраструктурных исключений."""
    assert issubclass(InfrastructureError, CertificateAnalyzerError)
    assert issubclass(ConfigurationError, (InfrastructureError, ValueError))
    assert issubclass(StorageError, (InfrastructureError, OSError))
    assert issubclass(DatabaseMigrationError, (InfrastructureError, ValueError))
    assert issubclass(TrashOperationError, (InfrastructureError, OSError))
    assert issubclass(ReportExportError, (InfrastructureError, RuntimeError))
    assert issubclass(NotificationError, (InfrastructureError, RuntimeError))


def test_exception_catching_as_base():
    """Проверяет перехват специализированных исключений базовым типом CertificateAnalyzerError."""
    with pytest.raises(CertificateAnalyzerError):
        raise CertificateNotFoundError("Сертификат abc не найден")

    with pytest.raises(DomainError):
        raise MchdValidationError("Отсутствует обязательный реквизит")

    with pytest.raises(InfrastructureError):
        raise StorageError("Ошибка чтения диска")
