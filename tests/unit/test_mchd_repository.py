"""Тесты репозитория машиночитаемых доверенностей и нормализованных полномочий."""

from datetime import UTC, datetime
import sqlite3
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.infrastructure.database.migrations import SCHEMA_VERSION, migrate
from certificate_analyzer.infrastructure.database.models import Base
from certificate_analyzer.infrastructure.database.models.mchds import (
    MchdAuthorityModel,
)
from certificate_analyzer.infrastructure.repositories.mchd_repository import (
    MchdRepository,
)


@pytest.fixture
def session_factory(tmp_path):
    """Создает тестовую базу данных SQLite со всеми моделями и возвращает фабрику сессий."""
    db_file = tmp_path / "test_mchd.sqlite"
    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def sample_mchd():
    """Возвращает тестовую доменную модель МЧД."""
    return MchdDocument(
        unified_number="1111-2222-3333-4444",
        internal_number="INT-001",
        principal_inn="7701234567",
        principal_name="ООО Главная Компания",
        representative_inn="770298765432",
        representative_fio="Сидоров Алексей Петрович",
        representative_snils="12345678901",
        valid_from=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
        valid_to=datetime(2027, 1, 1, 0, 0, tzinfo=UTC),
        status=MchdStatus.ACTIVE,
        authority_codes=["CODE_SIGN", "CODE_SUBMIT"],
        authority_names=["Подписание финансовых отчетов", "Подача деклараций в ФНС"],
        source_path="/path/to/mchd_sample.xml",
    )


def test_mchd_repository_save_and_get(session_factory, sample_mchd):
    """Проверяет сохранение МЧД с нормализацией полномочий и чтение по номеру."""
    repo = MchdRepository(session_factory)
    saved = repo.save(sample_mchd)

    assert saved.unified_number == sample_mchd.unified_number
    assert saved.authority_codes == ["CODE_SIGN", "CODE_SUBMIT"]
    assert saved.authority_names == [
        "Подписание финансовых отчетов",
        "Подача деклараций в ФНС",
    ]

    loaded = repo.get_by_number("1111-2222-3333-4444")
    assert loaded is not None
    assert loaded.unified_number == sample_mchd.unified_number
    assert loaded.principal_name == "ООО Главная Компания"
    assert loaded.representative_fio == "Сидоров Алексей Петрович"
    assert loaded.authority_codes == ["CODE_SIGN", "CODE_SUBMIT"]
    assert loaded.authority_names == [
        "Подписание финансовых отчетов",
        "Подача деклараций в ФНС",
    ]

    # Проверяем физическое присутствие записей в таблице mchd_authorities
    with session_factory() as session:
        auth_rows = session.scalars(
            select(MchdAuthorityModel).where(
                MchdAuthorityModel.mchd_number == sample_mchd.unified_number
            )
        ).all()
        assert len(auth_rows) == 2
        assert {a.code for a in auth_rows} == {"CODE_SIGN", "CODE_SUBMIT"}


def test_mchd_repository_update_authorities(session_factory, sample_mchd):
    """Проверяет обновление полномочий и корректное каскадное удаление старых."""
    repo = MchdRepository(session_factory)
    repo.save(sample_mchd)

    # Обновляем список полномочий
    sample_mchd.authority_codes = ["CODE_NEW"]
    sample_mchd.authority_names = ["Новое полномочие"]
    updated = repo.save(sample_mchd)

    assert updated.authority_codes == ["CODE_NEW"]
    assert updated.authority_names == ["Новое полномочие"]

    loaded = repo.get_by_number(sample_mchd.unified_number)
    assert loaded is not None
    assert loaded.authority_codes == ["CODE_NEW"]
    assert loaded.authority_names == ["Новое полномочие"]

    with session_factory() as session:
        auth_rows = session.scalars(
            select(MchdAuthorityModel).where(
                MchdAuthorityModel.mchd_number == sample_mchd.unified_number
            )
        ).all()
        assert len(auth_rows) == 1
        assert auth_rows[0].code == "CODE_NEW"
        assert auth_rows[0].name == "Новое полномочие"


def test_mchd_repository_filter_by_authority_code(session_factory, sample_mchd):
    """Проверяет фильтрацию и поиск по коду полномочия через связанную таблицу."""
    repo = MchdRepository(session_factory)
    repo.save(sample_mchd)

    other_mchd = MchdDocument(
        unified_number="9999-8888-7777-6666",
        internal_number="INT-002",
        principal_inn="7701234567",
        principal_name="ООО Главная Компания",
        representative_inn="770555555555",
        representative_fio="Петров Петр",
        representative_snils="98765432100",
        valid_from=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
        valid_to=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        status=MchdStatus.EXPIRED,
        authority_codes=["CODE_OTHER"],
        authority_names=["Другое полномочие"],
    )
    repo.save(other_mchd)

    # Поиск по коду полномочия
    found_sign = repo.find_by_authority_code("CODE_SIGN")
    assert len(found_sign) == 1
    assert found_sign[0].unified_number == sample_mchd.unified_number

    found_other = repo.find_by_authority_code("CODE_OTHER")
    assert len(found_other) == 1
    assert found_other[0].unified_number == other_mchd.unified_number

    found_none = repo.find_by_authority_code("NON_EXISTING")
    assert found_none == []


def test_mchd_repository_list_all_and_search(session_factory, sample_mchd):
    """Проверяет полнотекстовый регистронезависимый поиск с поддержкой кириллицы."""
    repo = MchdRepository(session_factory)
    repo.save(sample_mchd)

    assert repo.count() == 1

    # Поиск по ФИО в разном регистре
    found_fio = repo.list_all(search="СИДОРОВ")
    assert len(found_fio) == 1

    # Поиск по организации
    found_org = repo.list_all(search="главная компания")
    assert len(found_org) == 1

    # Поиск по номеру
    found_num = repo.list_all(search="2222-3333")
    assert len(found_num) == 1

    # Фильтрация по статусу
    active = repo.list_all(status=MchdStatus.ACTIVE)
    assert len(active) == 1
    expired = repo.list_all(status=MchdStatus.EXPIRED)
    assert len(expired) == 0


def test_mchd_repository_delete_and_cascade(session_factory, sample_mchd):
    """Проверяет каскадное удаление полномочий при удалении МЧД."""
    repo = MchdRepository(session_factory)
    repo.save(sample_mchd)

    # Удаление
    assert repo.delete(sample_mchd.unified_number) is True
    assert repo.delete("not-found") is False
    assert repo.get_by_number(sample_mchd.unified_number) is None
    assert repo.count() == 0

    # Проверяем, что в mchd_authorities не осталось записей-сирот
    with session_factory() as session:
        auth_count = session.query(MchdAuthorityModel).count()
        assert auth_count == 0


def test_mchd_schema_migration_from_v3(tmp_path):
    """Проверяет миграцию старой структуры до актуальной версии схемы."""
    db_file = tmp_path / "legacy.sqlite"
    # Создаем базу данных с версией 3 и старой таблицей mchds
    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA user_version=3")
        conn.execute(
            """CREATE TABLE mchds (
                unified_number VARCHAR(255) PRIMARY KEY,
                internal_number VARCHAR(255),
                principal_inn VARCHAR(20) NOT NULL,
                principal_name VARCHAR(255) NOT NULL,
                representative_inn VARCHAR(20) NOT NULL,
                representative_fio VARCHAR(255) NOT NULL,
                representative_snils VARCHAR(20) NOT NULL,
                valid_from TIMESTAMP NOT NULL,
                valid_to TIMESTAMP NOT NULL,
                status VARCHAR(50) NOT NULL,
                authority_codes VARCHAR(1024),
                source_path VARCHAR(1024)
            )"""
        )
        conn.execute(
            """INSERT INTO mchds VALUES (
                'MCHD-1', 'INT-1', '1234567890', 'Организация', '0987654321', 'Петров П.П.',
                '11122233344', '2025-01-01', '2026-01-01', 'ACTIVE', 'AUTH1, AUTH2', '/tmp/1.xml'
            )"""
        )
        conn.commit()

    # Запускаем миграцию
    engine = create_engine(f"sqlite:///{db_file}")
    migrate(engine, db_file)

    # Проверяем результат миграции
    with engine.connect() as conn:
        version = conn.exec_driver_sql("PRAGMA user_version").scalar()
        assert version == SCHEMA_VERSION

        # Проверяем создание таблицы mchd_authorities и перенос данных
        rows = conn.exec_driver_sql(
            "SELECT mchd_number, code FROM mchd_authorities ORDER BY code"
        ).all()
        assert len(rows) == 2
        assert rows[0] == ("MCHD-1", "AUTH1")
        assert rows[1] == ("MCHD-1", "AUTH2")

    engine.dispose()
