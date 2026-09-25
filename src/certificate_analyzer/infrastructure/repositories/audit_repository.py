"""Репозиторий журнала аудита событий на базе SQLAlchemy."""

import json
from datetime import datetime
from sqlalchemy import select

from certificate_analyzer.domain.models.audit_event import AuditEvent
from certificate_analyzer.infrastructure.database.models.audit import AuditEventModel


class AuditRepository:
    """Репозиторий для сохранения и чтения событий аудита."""

    def __init__(self, session_factory):
        """Инициализирует репозиторий аудита.

        Args:
            session_factory: Фабрика сессий SQLAlchemy.
        """
        self.sessions = session_factory

    @staticmethod
    def _to_domain(model: AuditEventModel) -> AuditEvent:
        """Преобразует модель AuditEventModel в доменную сущность AuditEvent.

        Args:
            model: Экземпляр модели БД.

        Returns:
            AuditEvent: Доменное событие аудита.
        """
        details = {}
        if model.details_json:
            try:
                details = json.loads(model.details_json)
            except (json.JSONDecodeError, TypeError):
                details = {}

        return AuditEvent(
            id=model.id,
            event_type=model.event_type,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            description=model.description,
            created_at=model.created_at,
            details=details,
        )

    def save(self, event: AuditEvent) -> AuditEvent:
        """Сохраняет новое событие аудита в базе данных.

        Args:
            event: Доменное событие аудита.

        Returns:
            AuditEvent: Сохраненное событие с присвоенным идентификатором id.
        """
        now = datetime.utcnow()
        details_str = json.dumps(event.details or {}, ensure_ascii=False)
        with self.sessions.begin() as session:
            model = AuditEventModel(
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                description=event.description,
                details_json=details_str,
                created_at=event.created_at or now,
            )
            session.add(model)
            session.flush()
            return self._to_domain(model)

    def list_events(
        self,
        entity_type: str | None = None,
        event_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Возвращает список событий аудита с сортировкой от новых к старым.

        Args:
            entity_type: Фильтр по типу сущности (опционально).
            event_type: Фильтр по типу события (опционально).
            entity_id: Фильтр по идентификатору сущности (опционально).
            limit: Максимальное количество записей (по умолчанию 100).

        Returns:
            list[AuditEvent]: Список событий аудита.
        """
        with self.sessions() as session:
            stmt = select(AuditEventModel).order_by(AuditEventModel.created_at.desc())
            if entity_type:
                stmt = stmt.where(AuditEventModel.entity_type == entity_type)
            if event_type:
                stmt = stmt.where(AuditEventModel.event_type == event_type)
            if entity_id:
                stmt = stmt.where(AuditEventModel.entity_id == entity_id)
            if limit:
                stmt = stmt.limit(limit)

            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]
