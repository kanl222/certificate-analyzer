"""Иерархия исключений приложения Certificate Analyzer."""


class CertificateAnalyzerError(Exception):
    """Базовое исключение для всех ошибок приложения Certificate Analyzer."""


# =====================================================================
# Доменные исключения (Domain Layer)
# =====================================================================


class DomainError(CertificateAnalyzerError):
    """Базовое исключение для ошибок доменного слоя."""


class CertificateNotFoundError(DomainError, FileNotFoundError):
    """Сертификат или файл сертификата не найден в системе.

    Args:
        message: Описание ошибки с указанием отпечатка или пути к файлу.
    """


class CertificateParseError(DomainError, ValueError):
    """Ошибка разбора структуры сертификата X.509.

    Args:
        message: Причина сбоя парсинга.
    """


class CertificateValidationError(DomainError, ValueError):
    """Ошибка валидации данных сертификата.

    Args:
        message: Описание нарушенного правила валидации.
    """


class MchdParseError(DomainError, ValueError):
    """Ошибка синтаксического разбора XML-файла МЧД.

    Args:
        message: Описание ошибки парсинга XML.
    """


class MchdValidationError(DomainError, ValueError):
    """Ошибка валидации обязательных полей или структуры МЧД.

    Args:
        message: Описание непройденной проверки валидатора.
    """


class MchdMergeError(DomainError, ValueError):
    """Ошибка объединения полномочий доверенностей МЧД.

    Args:
        message: Причина невозможности объединения.
    """


class PhonebookParseError(DomainError, ValueError):
    """Ошибка разбора файла телефонного справочника (DOCX/TXT).

    Args:
        message: Описание ошибки парсинга справочника.
    """


class InvalidRequestStatusTransitionError(DomainError, ValueError):
    """Недопустимый переход жизненного цикла заявки на сертификат.

    Args:
        message: Описание недопустимого изменения статуса заявки.
    """


# =====================================================================
# Инфраструктурные и системные исключения (Infrastructure Layer)
# =====================================================================


class InfrastructureError(CertificateAnalyzerError):
    """Базовое исключение для ошибок инфраструктурного слоя."""


class ConfigurationError(InfrastructureError, ValueError):
    """Ошибка загрузки или некорректные параметры конфигурации приложения.

    Args:
        message: Описание невалидного параметра конфигурации.
    """


class StorageError(InfrastructureError, OSError):
    """Ошибка операций с файловым хранилищем сертификатов.

    Args:
        message: Описание ошибки файлового ввода-вывода или конфликта хранилища.
    """


class DatabaseMigrationError(InfrastructureError, ValueError):
    """Ошибка применения миграций структуры базы данных.

    Args:
        message: Описание конфликта версии или сбоя схемы БД.
    """


class TrashOperationError(InfrastructureError, OSError):
    """Ошибка перемещения файла в корзину операционной системы.

    Args:
        message: Причина сбоя вызова системного API или утилиты корзины.
    """


class ReportExportError(InfrastructureError, RuntimeError):
    """Ошибка экспорта отчетов (Excel / PDF).

    Args:
        message: Описание ошибки при формировании отчета.
    """


class NotificationError(InfrastructureError, RuntimeError):
    """Ошибка отправки уведомлений пользователю.

    Args:
        message: Описание сбоя механизма уведомлений.
    """
