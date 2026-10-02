"""Репозиторий для управления заявками на получение сертификатов в SQLite."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.database.models.certificate_requests import (
    CertificateRequestModel,
)


class CertificateRequestRepository:
    """Репозиторий заявок на сертификаты на основе коротких сессий SQLAlchemy."""

    def __init__(self, session_factory):
        """Инициализирует репозиторий фабрикой сессий.

        Args:
            session_factory: Фабрика сессий SQLAlchemy.
        """
        self.sessions = session_factory

    @staticmethod
    def _to_domain(model: CertificateRequestModel) -> CertificateRequest:
        """Преобразует модель SQLAlchemy в доменную сущность CertificateRequest.

        Args:
            model: Экземпляр CertificateRequestModel.

        Returns:
            CertificateRequest: Доменная модель заявки.
        """
        employee = None
        if model.employee:
            employee = Employee(
                id=model.employee.id,
                full_name=model.employee.full_name,
                department=model.employee.department,
                office=model.employee.office,
                phones=[p.strip() for p in (model.employee.phones or "").split(",") if p.strip()],
                email=model.employee.email,
                position=model.employee.position,
                inn=model.employee.inn,
                snils=model.employee.snils,
                birth_date=model.employee.birth_date,
                is_management=bool(model.employee.is_management),
            )

        status_val = model.status
        try:
            status = CertificateRequestStatus(status_val)
        except ValueError:
            status = CertificateRequestStatus.NOT_SUBMITTED

        return CertificateRequest(
            id=model.id,
            request_number=model.request_number,
            employee_id=model.employee_id,
            employee=employee,
            department=model.department,
            needs_signature=model.needs_signature,
            status=status,
            submitted_at=model.submitted_at,
            issued_at=model.issued_at,
            certificate_fingerprint=model.certificate_fingerprint,
            comment=model.comment or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, request: CertificateRequest) -> CertificateRequest:
        """Сохраняет новую или обновляет существующую заявку.

        Args:
            request: Доменная сущность заявки.

        Returns:
            CertificateRequest: Сохраненная заявка с присвоенным ID.
        """
        now = datetime.utcnow()
        with self.sessions.begin() as session:
            if request.id:
                model = session.get(CertificateRequestModel, request.id)
            else:
                model = session.scalars(
                    select(CertificateRequestModel).where(
                        CertificateRequestModel.request_number == request.request_number
                    )
                ).first()

            status_str = request.status.value if isinstance(request.status, CertificateRequestStatus) else str(request.status)

            if not model:
                model = CertificateRequestModel(
                    request_number=request.request_number,
                    employee_id=request.employee_id,
                    department=request.department,
                    needs_signature=request.needs_signature,
                    status=status_str,
                    submitted_at=request.submitted_at,
                    issued_at=request.issued_at,
                    certificate_fingerprint=request.certificate_fingerprint,
                    comment=request.comment,
                    created_at=request.created_at or now,
                    updated_at=now,
                )
                session.add(model)
                session.flush()
            else:
                model.employee_id = request.employee_id
                model.department = request.department
                model.needs_signature = request.needs_signature
                model.status = status_str
                model.submitted_at = request.submitted_at
                model.issued_at = request.issued_at
                model.certificate_fingerprint = request.certificate_fingerprint
                model.comment = request.comment
                model.updated_at = now

            session.flush()
            # Дозагрузка связей
            session.refresh(model, ["employee", "certificate"])
            return self._to_domain(model)

    def get_by_id(self, request_id: int) -> CertificateRequest | None:
        """Получает заявку по первичному ключу.

        Args:
            request_id: Идентификатор заявки.

        Returns:
            CertificateRequest | None: Найденная заявка или None.
        """
        with self.sessions() as session:
            model = session.scalars(
                select(CertificateRequestModel)
                .options(selectinload(CertificateRequestModel.employee))
                .where(CertificateRequestModel.id == request_id)
            ).first()
            return self._to_domain(model) if model else None

    def get_by_number(self, request_number: str) -> CertificateRequest | None:
        """Получает заявку по уникальному номеру.

        Args:
            request_number: Номер заявки.

        Returns:
            CertificateRequest | None: Заявка или None.
        """
        with self.sessions() as session:
            model = session.scalars(
                select(CertificateRequestModel)
                .options(selectinload(CertificateRequestModel.employee))
                .where(CertificateRequestModel.request_number == request_number)
            ).first()
            return self._to_domain(model) if model else None

    def list(
        self,
        status: CertificateRequestStatus | str | None = None,
        employee_id: int | None = None,
        search: str | None = None,
    ) -> list[CertificateRequest]:
        """Возвращает список заявок с опциональной фильтрацией.

        Args:
            status: Фильтр по статусу (опционально).
            employee_id: Фильтр по сотруднику (опционально).
            search: Поисковая строка по номеру или комментарию (опционально).

        Returns:
            list[CertificateRequest]: Список доменных сущностей заявок.
        """
        with self.sessions() as session:
            stmt = select(CertificateRequestModel).options(
                selectinload(CertificateRequestModel.employee)
            ).order_by(CertificateRequestModel.created_at.desc())

            if status:
                status_val = status.value if isinstance(status, CertificateRequestStatus) else str(status)
                stmt = stmt.where(CertificateRequestModel.status == status_val)
            if employee_id is not None:
                stmt = stmt.where(CertificateRequestModel.employee_id == employee_id)

            models = session.scalars(stmt).all()
            domain_requests = [self._to_domain(m) for m in models]
            if search:
                search_lower = search.strip().casefold()
                domain_requests = [
                    r for r in domain_requests
                    if (r.request_number and search_lower in r.request_number.casefold())
                    or (r.department and search_lower in r.department.casefold())
                    or (r.comment and search_lower in r.comment.casefold())
                    or (r.employee and r.employee.full_name and search_lower in r.employee.full_name.casefold())
                ]
            return domain_requests

    def update_status(
        self,
        request_id: int,
        status: CertificateRequestStatus | str,
        issued_at: datetime | None = None,
    ) -> bool:
        """Обновляет статус заявки.

        Args:
            request_id: Идентификатор заявки.
            status: Новый статус.
            issued_at: Дата выпуска сертификата (если применимо).

        Returns:
            bool: True в случае успешного обновления.
        """
        status_val = status.value if isinstance(status, CertificateRequestStatus) else str(status)
        now = datetime.utcnow()
        with self.sessions.begin() as session:
            model = session.get(CertificateRequestModel, request_id)
            if not model:
                return False
            model.status = status_val
            model.updated_at = now
            if issued_at is not None:
                model.issued_at = issued_at
            elif status_val == CertificateRequestStatus.ISSUED.value and not model.issued_at:
                model.issued_at = now
            return True

    def link_certificate(self, request_id: int, fingerprint: str) -> bool:
        """Связывает заявку с выпущенным сертификатом по SHA-256 fingerprint.

        Args:
            request_id: Идентификатор заявки.
            fingerprint: Отпечаток сертификата SHA-256.

        Returns:
            bool: True в случае успешной привязки.
        """
        with self.sessions.begin() as session:
            model = session.get(CertificateRequestModel, request_id)
            if not model:
                return False
            model.certificate_fingerprint = fingerprint
            model.updated_at = datetime.utcnow()
            return True

    def delete(self, request_id: int) -> bool:
        """Удаляет заявку по идентификатору.

        Args:
            request_id: Идентификатор удаляемой заявки.

        Returns:
            bool: True, если запись удалена.
        """
        with self.sessions.begin() as session:
            model = session.get(CertificateRequestModel, request_id)
            if not model:
                return False
            session.delete(model)
            return True
