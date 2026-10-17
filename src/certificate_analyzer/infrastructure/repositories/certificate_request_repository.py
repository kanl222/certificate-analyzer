"""Репозиторий для управления заявками на получение сертификатов в SQLite."""

from certificate_analyzer.domain.services.clock import utc_now
from certificate_analyzer.domain.services.certificate_status import utc
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.database.models.certificate_requests import (
    CertificateRequestModel,
)
from certificate_analyzer.infrastructure.database.models.employees import EmployeeModel
from certificate_analyzer.infrastructure.database.search import casefold_contains


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
            submitted_at=utc(model.submitted_at) if model.submitted_at else None,
            issued_at=utc(model.issued_at) if model.issued_at else None,
            certificate_fingerprint=model.certificate_fingerprint,
            comment=model.comment or "",
            created_at=utc(model.created_at),
            updated_at=utc(model.updated_at),
        )

    def save(self, request: CertificateRequest) -> CertificateRequest:
        """Сохраняет новую или обновляет существующую заявку.

        Args:
            request: Доменная сущность заявки.

        Returns:
            CertificateRequest: Сохраненная заявка с присвоенным ID.
        """
        now = utc_now()
        with self.sessions.begin() as session:
            if request.id:
                model = session.get(CertificateRequestModel, request.id)
            else:
                model = session.scalars(
                    select(CertificateRequestModel).where(
                        CertificateRequestModel.request_number == request.request_number
                    )
                ).first()
                if model is not None:
                    raise ValueError(f"Заявка с номером {request.request_number} уже существует")

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
        limit: int | None = None,
        offset: int = 0,
    ) -> list[CertificateRequest]:
        """Возвращает список заявок с опциональной фильтрацией.

        Args:
            status: Фильтр по статусу (опционально).
            employee_id: Фильтр по сотруднику (опционально).
            search: Поисковая строка по номеру или комментарию (опционально).

        Returns:
            list[CertificateRequest]: Список доменных сущностей заявок.
        """
        if offset < 0 or (limit is not None and limit < 0):
            raise ValueError("Лимит и смещение не могут быть отрицательными")
        with self.sessions() as session:
            stmt = select(CertificateRequestModel).options(
                selectinload(CertificateRequestModel.employee)
            ).outerjoin(EmployeeModel).order_by(
                CertificateRequestModel.created_at.desc(), CertificateRequestModel.id.desc()
            )

            if status:
                status_val = status.value if isinstance(status, CertificateRequestStatus) else str(status)
                stmt = stmt.where(CertificateRequestModel.status == status_val)
            if employee_id is not None:
                stmt = stmt.where(CertificateRequestModel.employee_id == employee_id)
            if search and search.strip():
                stmt = stmt.where(self._search_condition(session, search))
            if limit is not None:
                stmt = stmt.limit(limit)
            stmt = stmt.offset(offset)
            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]

    @staticmethod
    def _search_condition(session, search):
        return casefold_contains(session, (
            CertificateRequestModel.request_number,
            CertificateRequestModel.department,
            CertificateRequestModel.comment,
            EmployeeModel.full_name,
        ), search)

    def count_by_status(self, status=None, search=None) -> dict[CertificateRequestStatus, int]:
        with self.sessions() as session:
            stmt = (
                select(CertificateRequestModel.status, func.count())
                .select_from(CertificateRequestModel)
                .outerjoin(EmployeeModel)
                .group_by(CertificateRequestModel.status)
            )
            if status is not None:
                value = status.value if isinstance(status, CertificateRequestStatus) else str(status)
                stmt = stmt.where(CertificateRequestModel.status == value)
            if search and search.strip():
                stmt = stmt.where(self._search_condition(session, search))
            counts: dict[CertificateRequestStatus, int] = {}
            for value, count in session.execute(stmt):
                status_enum = CertificateRequestStatus._value2member_map_.get(
                    value, CertificateRequestStatus.NOT_SUBMITTED
                )
                counts[status_enum] = counts.get(status_enum, 0) + count
            return counts

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
        now = utc_now()
        with self.sessions.begin() as session:
            model = session.get(CertificateRequestModel, request_id)
            if not model:
                return False
            model.status = status_val
            model.updated_at = now
            if status_val == CertificateRequestStatus.SUBMITTED.value and model.submitted_at is None:
                model.submitted_at = now
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
            model.updated_at = utc_now()
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
