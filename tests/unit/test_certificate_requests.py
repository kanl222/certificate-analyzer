"""Модульные тесты для сервиса и репозитория заявок на получение сертификатов."""

from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from certificate_analyzer.application.services.certificate_request_service import (
    CertificateRequestService,
)
from certificate_analyzer.application.services.employee_service import EmployeeService
from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.database.models import Base
from certificate_analyzer.infrastructure.repositories.certificate_request_repository import (
    CertificateRequestRepository,
)
from certificate_analyzer.infrastructure.repositories.employee_repository import (
    EmployeeRepository,
)


@pytest.fixture
def sqlite_sessions(tmp_path: Path):
    """Создает тестовую БД SQLite в памяти/файле и сессии для тестов.

    Args:
        tmp_path: Временный каталог pytest.

    Yields:
        sessionmaker: Фабрика сессий SQLAlchemy.
    """
    db_path = tmp_path / "requests_test.sqlite"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"timeout": 30})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    yield sessions
    engine.dispose()


@pytest.fixture
def request_service(sqlite_sessions):
    """Инициализирует CertificateRequestService для тестов.

    Args:
        sqlite_sessions: Фикстура фабрики сессий БД.

    Returns:
        CertificateRequestService: Экземпляр сервиса заявок.
    """
    emp_repo = EmployeeRepository(sqlite_sessions)
    req_repo = CertificateRequestRepository(sqlite_sessions)
    return CertificateRequestService(req_repo, emp_repo)


def test_create_certificate_request(request_service: CertificateRequestService):
    """Проверяет создание новой заявки на получение сертификата.

    Args:
        request_service: Тестируемый сервис заявок.

    Returns:
        None
    """
    req = request_service.create_request(
        request_number="REQ-2026-001",
        department="Бухгалтерия",
        needs_signature=True,
        comment="Срочный выпуск подписи главного бухгалтера",
    )
    assert req.id is not None
    assert req.request_number == "REQ-2026-001"
    assert req.department == "Бухгалтерия"
    assert req.needs_signature is True
    assert req.status == CertificateRequestStatus.NOT_SUBMITTED
    assert req.submitted_at is None
    stored = request_service.get_request(req.id)
    assert stored.status == CertificateRequestStatus.NOT_SUBMITTED
    assert stored.submitted_at is None
    assert req.comment == "Срочный выпуск подписи главного бухгалтера"


def test_update_request_status(request_service: CertificateRequestService):
    """Проверяет обновление статуса жизненного цикла заявки.

    Args:
        request_service: Тестируемый сервис заявок.

    Returns:
        None
    """
    req = request_service.create_request(request_number="REQ-2026-002")
    assert req.id is not None

    ok = request_service.update_status(req.id, CertificateRequestStatus.IN_PROGRESS)
    assert ok is True

    updated = request_service.get_request(req.id)
    assert updated is not None
    assert updated.status == CertificateRequestStatus.IN_PROGRESS


def test_request_requires_electronic_signature_by_default(
    request_service: CertificateRequestService,
):
    """Новая заявка по умолчанию создается для выпуска сертификата ЭП."""
    request = request_service.create_request(request_number="REQ-SIGN-DEFAULT")

    assert request.needs_signature is True


def test_mark_request_processed(request_service: CertificateRequestService):
    """Проверяет перевод заявки в статус «Обработана» без удаления из базы данных.

    Args:
        request_service: Тестируемый сервис заявок.

    Returns:
        None
    """
    req = request_service.create_request(request_number="REQ-PROC-001")
    assert req.id is not None

    ok = request_service.update_status(req.id, CertificateRequestStatus.PROCESSED)
    assert ok is True

    processed = request_service.get_request(req.id)
    assert processed is not None
    assert processed.status == CertificateRequestStatus.PROCESSED
    assert processed.status.label == "Обработана"


def test_link_certificate(request_service: CertificateRequestService):
    """Проверяет связывание заявки с отпечатком выпущенного сертификата.

    Args:
        request_service: Тестируемый сервис заявок.

    Returns:
        None
    """
    req = request_service.create_request(request_number="REQ-2026-003")
    assert req.id is not None
    fingerprint = "A" * 64

    ok = request_service.link_certificate(req.id, fingerprint)
    assert ok is True

    linked = request_service.get_request(req.id)
    assert linked is not None
    assert linked.certificate_fingerprint == fingerprint
    assert linked.status == CertificateRequestStatus.ISSUED


def test_list_requests_filter(request_service: CertificateRequestService):
    """Проверяет фильтрацию и поиск заявок по статусу и строке.

    Args:
        request_service: Тестируемый сервис заявок.

    Returns:
        None
    """
    request_service.create_request(
        request_number="REQ-FIN-1", department="Финансы", status=CertificateRequestStatus.SUBMITTED
    )
    request_service.create_request(
        request_number="REQ-IT-1", department="IT отдел", status=CertificateRequestStatus.IN_PROGRESS
    )

    all_reqs = request_service.list_requests()
    assert len(all_reqs) >= 2

    submitted = request_service.list_requests(status=CertificateRequestStatus.SUBMITTED)
    assert any(r.request_number == "REQ-FIN-1" for r in submitted)
    assert not any(r.request_number == "REQ-IT-1" for r in submitted)

    search_it = request_service.list_requests(search="IT отдел")
    assert len(search_it) == 1
    assert search_it[0].request_number == "REQ-IT-1"


def test_delete_certificate_request(request_service: CertificateRequestService):
    """Проверяет удаление заявки из базы данных.

    Args:
        request_service: Тестируемый сервис заявок.

    Returns:
        None
    """
    req = request_service.create_request(request_number="REQ-DEL-1")
    assert req.id is not None

    deleted = request_service.delete_request(req.id)
    assert deleted is True

    assert request_service.get_request(req.id) is None


def test_employee_service_and_request_linking(sqlite_sessions):
    """Проверяет связь сотрудника с создаваемой заявкой.

    Args:
        sqlite_sessions: Фикстура фабрики сессий БД.

    Returns:
        None
    """
    emp_repo = EmployeeRepository(sqlite_sessions)
    req_repo = CertificateRequestRepository(sqlite_sessions)
    emp_service = EmployeeService(emp_repo)
    req_service = CertificateRequestService(req_repo, emp_repo)

    emp = emp_service.save_employee(
        Employee(
            full_name="Петров Петр Петрович",
            department="Департамент безопасности",
            office="404",
            email="petrov@corp.local",
            inn="770123456789",
            snils="123-456-789 00",
        )
    )
    assert emp.id is not None

    req = req_service.create_request(
        request_number="REQ-SEC-01",
        full_name="Петров Петр Петрович",
        needs_signature=True,
    )
    assert req.employee_id == emp.id
    assert req.department == "Департамент безопасности"
    assert req.employee is not None
    assert req.employee.full_name == "Петров Петр Петрович"


def test_duplicate_number_preserves_existing_request(request_service):
    original = request_service.create_request(request_number="DUP", comment="Original", status=CertificateRequestStatus.ISSUED)
    with pytest.raises(ValueError, match="уже существует"):
        request_service.create_request(request_number="DUP", comment="Replacement")
    stored = request_service.get_request(original.id)
    assert stored.comment == "Original"
    assert stored.status == CertificateRequestStatus.ISSUED
    assert len(request_service.list_requests()) == 1


def test_submission_date_is_set_once(request_service):
    request = request_service.create_request()
    assert request.submitted_at is None
    request_service.update_status(request.id, CertificateRequestStatus.SUBMITTED)
    submitted = request_service.get_request(request.id).submitted_at
    assert submitted is not None
    request_service.update_status(request.id, CertificateRequestStatus.NOT_SUBMITTED)
    request_service.update_status(request.id, CertificateRequestStatus.SUBMITTED)
    assert request_service.get_request(request.id).submitted_at == submitted


def test_unknown_employee_is_not_silently_lost(request_service):
    with pytest.raises(ValueError, match="создайте нового"):
        request_service.create_request(full_name="Неизвестный сотрудник")
    assert request_service.list_requests() == []


def test_ambiguous_employee_requires_selection(request_service):
    first = request_service.employees.save(Employee(full_name="Тёзка", department="ИТ"))
    request_service.employees.save(Employee(full_name="Тёзка", department="Кадры"))
    with pytest.raises(ValueError, match="Выберите сотрудника"):
        request_service.create_request(full_name="Тёзка")
    request = request_service.create_request(full_name="Тёзка", employee_id=first.id)
    assert request.employee_id == first.id


def test_request_search_and_pagination_keep_unicode_and_literal_wildcards(request_service):
    employee = request_service.employees.save(Employee(full_name="Ёлкин", department="ИТ"))
    request_service.create_request(request_number="R-1", employee_id=employee.id, comment="100% готово")
    request_service.create_request(request_number="R-2", employee_id=employee.id, comment="100% готово")
    request_service.create_request(request_number="R-3", comment="Другое")

    matches = request_service.list_requests(search="ёЛкИн", limit=1, offset=1)
    assert len(matches) == 1
    assert matches[0].request_number == "R-1"
    assert [r.request_number for r in request_service.list_requests(search="100%", limit=10)] == ["R-2", "R-1"]
    assert request_service.list_requests(search="100_", limit=10) == []
    assert request_service.count_by_status(search="ЁЛКИН") == {CertificateRequestStatus.NOT_SUBMITTED: 2}
    with pytest.raises(ValueError):
        request_service.list_requests(limit=-1)
