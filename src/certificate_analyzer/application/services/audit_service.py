"""Сервис приложения для аудита операций и событий безопасности."""

from datetime import datetime

from certificate_analyzer.domain.models.audit_event import AuditEvent
from certificate_analyzer.infrastructure.repositories.audit_repository import (
    AuditRepository,
)


class AuditService:
    """Сервис регистрации и просмотра событий аудита системы."""

    def __init__(self, repository: AuditRepository):
        """Инициализирует сервис аудита.

        Args:
            repository: Репозиторий событий аудита.
        """
        self.repository = repository

    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        description: str,
        details: dict | None = None,
    ) -> AuditEvent:
        """Создает и регистрирует новое событие аудита в системе.

        Args:
            event_type: Тип события (например: FILE_DELETED, RECORD_DELETED, CERTIFICATE_IMPORTED).
            entity_type: Тип сущности (например: CERTIFICATE, FILE, REQUEST, EMPLOYEE).
            entity_id: Идентификатор сущности (отпечаток, номер заявки, путь к файлу).
            description: Текстовое описание операции.
            details: Словарь с дополнительными параметрами и метаданными события.

        Returns:
            AuditEvent: Зарегистрированное событие аудита.
        """
        event = AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            description=description,
            created_at=datetime.utcnow(),
            details=details or {},
        )
        return self.repository.save(event)

    def list_events(
        self,
        entity_type: str | None = None,
        event_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Возвращает список событий аудита с возможностью фильтрации.

        Args:
            entity_type: Фильтр по типу сущности (опционально).
            event_type: Фильтр по типу события (опционально).
            entity_id: Фильтр по идентификатору сущности (опционально).
            limit: Максимальное количество записей (по умолчанию 100).

        Returns:
            list[AuditEvent]: Список событий аудита.
        """
        return self.repository.list_events(
            entity_type=entity_type,
            event_type=event_type,
            entity_id=entity_id,
            limit=limit,
        )
