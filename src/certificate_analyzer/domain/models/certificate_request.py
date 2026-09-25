"""Доменная модель заявки на получение цифрового сертификата."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from certificate_analyzer.domain.models.employee import Employee

from certificate_analyzer.domain.enums.certificate_request_status import (
    CertificateRequestStatus,
)


@dataclass(slots=True)
class CertificateRequest:
    """Сущность заявки на выпуск электронного сертификата подписи."""

    request_number: str
    id: int | None = None
    employee_id: int | None = None
    employee: Optional["Employee"] = None
    department: str = ""
    needs_signature: bool = True
    status: CertificateRequestStatus = CertificateRequestStatus.NOT_SUBMITTED
    submitted_at: datetime | None = None
    issued_at: datetime | None = None
    certificate_fingerprint: str | None = None
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
