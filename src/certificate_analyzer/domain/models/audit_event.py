"""Доменная модель записи журнала аудита событий безопасности и операций."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class AuditEvent:
    """Сущность события аудита в системе.

    Фиксирует операции создания, изменения, удаления файлов и записей,
    а также изменения статусов заявок и сертификатов.

    Attributes:
        id: Уникальный идентификатор события в БД (может быть None до сохранения).
        event_type: Тип события (например: FILE_DELETED, RECORD_DELETED, CERTIFICATE_IMPORTED).
        entity_type: Тип затрагиваемой сущности (например: CERTIFICATE, FILE, REQUEST, EMPLOYEE).
        entity_id: Идентификатор сущности (отпечаток, номер заявки, путь к файлу).
        description: Подробное описание совершенного действия.
        created_at: Дата и время фиксации события.
        details: Дополнительные структурированные данные о событии.
    """

    event_type: str
    entity_type: str
    entity_id: str
    description: str
    created_at: datetime
    id: int | None = None
    details: dict | None = field(default_factory=dict)
