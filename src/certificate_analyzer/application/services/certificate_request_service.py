"""Сервис приложения для управления заявками на получение сертификатов."""

from datetime import datetime
import uuid

from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.infrastructure.repositories.certificate_request_repository import (
    CertificateRequestRepository,
)
from certificate_analyzer.infrastructure.repositories.employee_repository import (
    EmployeeRepository,
)


class CertificateRequestService:
    """Сервис жизненного цикла заявок на выпуск и учет сертификатов."""

    def __init__(
        self,
        repository: CertificateRequestRepository,
        employee_repository: EmployeeRepository | None = None,
    ):
        """Инициализирует сервис заявок.

        Args:
            repository: Репозиторий заявок на сертификаты.
            employee_repository: Репозиторий сотрудников (опционально).
        """
        self.repository = repository
        self.employees = employee_repository

    def create_request(
        self,
        request_number: str | None = None,
        employee_id: int | None = None,
        full_name: str | None = None,
        department: str = "",
        needs_signature: bool = True,
        comment: str = "",
        status: CertificateRequestStatus = CertificateRequestStatus.SUBMITTED,
    ) -> CertificateRequest:
        """Создает новую заявку на выпуск сертификата.

        Args:
            request_number: Уникальный номер заявки (генерируется, если не передан).
            employee_id: Идентификатор сотрудника.
            full_name: ФИО сотрудника (для поиска/сопоставления, если не передан employee_id).
            department: Подразделение.
            needs_signature: Признак необходимости электронной подписи.
            comment: Примечание или комментарий.
            status: Начальный статус заявки.

        Returns:
            CertificateRequest: Созданная доменная заявка.
        """
        if not request_number:
            request_number = f"REQ-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        if not employee_id and full_name and self.employees:
            emp = self.employees.find_by_name(full_name)
            if emp:
                employee_id = emp.id
                department = department or (emp.department or "")

        req = CertificateRequest(
            request_number=request_number,
            employee_id=employee_id,
            department=department,
            needs_signature=needs_signature,
            status=status,
            submitted_at=datetime.utcnow() if status != CertificateRequestStatus.NOT_SUBMITTED else None,
            comment=comment,
        )
        return self.repository.save(req)

    def update_status(
        self,
        request_id: int,
        status: CertificateRequestStatus | str,
        issued_at: datetime | None = None,
    ) -> bool:
        """Обновляет статус заявки.

        Args:
            request_id: Идентификатор заявки.
            status: Новый статус (строка или перечисление).
            issued_at: Дата выпуска (опционально).

        Returns:
            bool: True в случае успеха.
        """
        if isinstance(status, str):
            status = CertificateRequestStatus(status)
        return self.repository.update_status(request_id, status, issued_at=issued_at)

    def link_certificate(self, request_id: int, fingerprint: str) -> bool:
        """Связывает заявку с выпущенным сертификатом и переводит в статус ISSUED.

        Args:
            request_id: Идентификатор заявки.
            fingerprint: Отпечаток сертификата SHA-256.

        Returns:
            bool: True в случае успешной привязки.
        """
        success = self.repository.link_certificate(request_id, fingerprint)
        if success:
            self.repository.update_status(request_id, CertificateRequestStatus.ISSUED)
        return success

    def get_request(self, request_id: int) -> CertificateRequest | None:
        """Возвращает заявку по первичному ключу.

        Args:
            request_id: Первичный ключ заявки.

        Returns:
            CertificateRequest | None: Найденная заявка.
        """
        return self.repository.get_by_id(request_id)

    def list_requests(
        self,
        status: CertificateRequestStatus | str | None = None,
        employee_id: int | None = None,
        search: str | None = None,
    ) -> list[CertificateRequest]:
        """Возвращает список заявок с фильтрацией.

        Args:
            status: Фильтр по статусу (опционально).
            employee_id: Фильтр по сотруднику (опционально).
            search: Поисковый запрос (опционально).

        Returns:
            list[CertificateRequest]: Список заявок.
        """
        return self.repository.list(status=status, employee_id=employee_id, search=search)

    def delete_request(self, request_id: int) -> bool:
        """Удаляет заявку.

        Args:
            request_id: Идентификатор удаляемой заявки.

        Returns:
            bool: True, если заявка удалена.
        """
        return self.repository.delete(request_id)
