"""Тесты интеграции MchdService с MchdRepository."""

from datetime import UTC, datetime
from certificate_analyzer.application.services.mchd_service import MchdService
from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.infrastructure.database.models import Base
from certificate_analyzer.infrastructure.repositories.mchd_repository import (
    MchdRepository,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest


@pytest.fixture
def repo(tmp_path):
    """Возвращает репозиторий с базой данных в памяти/файле."""
    db_file = tmp_path / "service_test.sqlite"
    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield MchdRepository(factory)
    engine.dispose()


def test_mchd_service_crud_with_repository(repo):
    """Проверяет CRUD операции сервиса при наличии репозитория."""
    service = MchdService(repository=repo)

    doc = MchdDocument(
        unified_number="SERVICE-DOC-1",
        internal_number="INT-1",
        principal_inn="7701234567",
        principal_name="ООО Сервис",
        representative_inn="770987654321",
        representative_fio="Ковалев Константин",
        representative_snils="11122233344",
        valid_from=datetime(2025, 1, 1, tzinfo=UTC),
        valid_to=datetime(2026, 1, 1, tzinfo=UTC),
        status=MchdStatus.ACTIVE,
        authority_codes=["SRV_CODE"],
        authority_names=["Полномочие сервиса"],
    )

    saved = service.save(doc)
    assert saved.unified_number == "SERVICE-DOC-1"

    found = service.get_by_number("SERVICE-DOC-1")
    assert found is not None
    assert found.representative_fio == "Ковалев Константин"
    assert found.authority_codes == ["SRV_CODE"]

    auth_docs = service.find_by_authority("SRV_CODE")
    assert len(auth_docs) == 1
    assert auth_docs[0].unified_number == "SERVICE-DOC-1"

    listed = service.list_all(search="Сервис")
    assert len(listed) == 1

    deleted = service.delete("SERVICE-DOC-1")
    assert deleted is True
    assert service.get_by_number("SERVICE-DOC-1") is None


def test_mchd_service_scan_and_save(mchd_file, repo, tmp_path):
    """Проверяет сканирование каталога и сохранение распарсенных МЧД в базу данных."""
    folder = tmp_path / "xmls"
    folder.mkdir()
    f1 = mchd_file("doc1.xml", codes=("A", "B"))
    f1.replace(folder / "doc1.xml")

    service = MchdService(repository=repo)
    docs = service.scan(folder, save_to_db=True)

    assert len(docs) == 1
    assert docs[0].unified_number == "11111111-1111-1111-1111-111111111111"
    assert docs[0].authority_codes == ["A", "B"]

    # Проверяем, что документ сохранился в репозиторий
    in_db = repo.get_by_number("11111111-1111-1111-1111-111111111111")
    assert in_db is not None
    assert in_db.authority_codes == ["A", "B"]
