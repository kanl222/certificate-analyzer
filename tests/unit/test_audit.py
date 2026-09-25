"""Тесты для репозитория и сервиса аудита действий в системе."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from certificate_analyzer.application.services.audit_service import AuditService
from certificate_analyzer.domain.models.audit_event import AuditEvent
from certificate_analyzer.infrastructure.database.models.base import Base
from certificate_analyzer.infrastructure.repositories.audit_repository import (
    AuditRepository,
)


@pytest.fixture
def db_session_factory():
    """Создает временную базу данных SQLite в памяти для тестов аудита.

    Yields:
        sessionmaker: Фабрика сессий SQLAlchemy.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()


def test_audit_repository_record_and_list(db_session_factory):
    """Проверяет сохранение и выборку событий аудита в репозитории.

    Args:
        db_session_factory: Фикстура фабрики сессий БД.

    Returns:
        None
    """
    repo = AuditRepository(db_session_factory)
    event1 = AuditEvent(
        id=None,
        event_type="CERTIFICATE_IMPORTED",
        entity_type="CERTIFICATE",
        entity_id="sha256_111",
        description="Импортирован сертификат",
        created_at=datetime(2026, 9, 25, 10, 0, 0),
        details={"path": "C:/certs/test1.cer"},
    )
    event2 = AuditEvent(
        id=None,
        event_type="FILE_DELETED",
        entity_type="FILE",
        entity_id="sha256_111",
        description="Файл перемещён в корзину",
        created_at=datetime(2026, 9, 25, 11, 0, 0),
        details={"path": "C:/certs/test1.cer"},
    )

    saved1 = repo.save(event1)
    saved2 = repo.save(event2)

    assert saved1.id is not None
    assert saved2.id is not None

    events = repo.list_events(limit=10)
    assert len(events) == 2
    # Сортировка по убыванию времени создания
    assert events[0].event_type == "FILE_DELETED"
    assert events[1].event_type == "CERTIFICATE_IMPORTED"

    # Фильтр по entity_id
    filtered = repo.list_events(entity_id="sha256_111")
    assert len(filtered) == 2

    # Фильтр по event_type
    by_action = repo.list_events(event_type="FILE_DELETED")
    assert len(by_action) == 1
    assert by_action[0].event_type == "FILE_DELETED"


def test_audit_service_logging(db_session_factory):
    """Проверяет методы логирования AuditService.

    Args:
        db_session_factory: Фикстура фабрики сессий БД.

    Returns:
        None
    """
    repo = AuditRepository(db_session_factory)
    service = AuditService(repo)

    service.log_event(
        event_type="CERTIFICATE_IMPORTED",
        entity_type="CERTIFICATE",
        entity_id="sha256_abc",
        description="Импортирован сертификат",
        details={"path": "C:/certs/alice.cer"},
    )
    service.log_event(
        event_type="FILE_DELETED",
        entity_type="CERTIFICATE",
        entity_id="sha256_abc",
        description="Файл перемещён в корзину",
        details={"path": "C:/certs/alice.cer", "to_trash": True},
    )
    service.log_event(
        event_type="RECORD_DELETED",
        entity_type="CERTIFICATE",
        entity_id="sha256_abc",
        description="Удалена запись из реестра",
    )

    events = service.list_events(limit=5)
    assert len(events) == 3

    event_types = [e.event_type for e in events]
    assert "RECORD_DELETED" in event_types
    assert "FILE_DELETED" in event_types
    assert "CERTIFICATE_IMPORTED" in event_types
