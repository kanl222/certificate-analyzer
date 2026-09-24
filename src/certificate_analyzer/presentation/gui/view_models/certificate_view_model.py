from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


def utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


@dataclass(slots=True)
class CertificateViewModel:
    file_name: str
    file_type: str
    valid_from: str
    valid_to: str
    subject_cn: str
    serial_number: str
    email: str
    office_number: str
    department: str
    phone: str
    status: str
    color: str
    tag: str
    details: dict[str, Any] | None = None

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_certificate_view_model(cert, source_path: str | None = None) -> CertificateViewModel:
    """Format domain Certificate or DTO into a presentation ViewModel with UI colors and labels."""
    valid_to = cert.valid_to
    now = datetime.now(UTC)
    days = max(0, (utc(valid_to) - now).days) if valid_to else 0

    status = getattr(cert, "status", CertificateStatus.ACTIVE)
    labels = {
        CertificateStatus.EXPIRED: ("Просрочен", "#e57373", "expired"),
        CertificateStatus.EXPIRING_SOON: (f"Истекает ({days} дн.)", "#ffd54f", "warning"),
        CertificateStatus.ACTIVE: ("Активен", "#81c784", "normal"),
        CertificateStatus.INVALID: ("Недействителен", "#e57373", "expired"),
        CertificateStatus.REVOKED: ("Отозван", "#e57373", "expired"),
    }
    status_label, color, tag = labels.get(status, ("Неизвестно", "#9e9e9e", "normal"))

    # Extract employee data if available
    employee = getattr(cert, "employee", None)
    office = getattr(employee, "office", None) or getattr(cert, "office", None) or "—"
    department = getattr(employee, "department", None) or getattr(cert, "department", None) or "—"
    
    phones = getattr(employee, "phones", None)
    if phones and isinstance(phones, list):
        phone_str = ", ".join(phones)
    else:
        phone_str = getattr(cert, "phone", "—")

    path = source_path or getattr(cert, "source_path", "—")

    return CertificateViewModel(
        file_name=path,
        file_type="Сертификат",
        valid_from=cert.valid_from.strftime("%d.%m.%Y") if hasattr(cert.valid_from, "strftime") else str(cert.valid_from),
        valid_to=cert.valid_to.strftime("%d.%m.%Y") if hasattr(cert.valid_to, "strftime") else str(cert.valid_to),
        subject_cn=getattr(cert, "subject", "—"),
        serial_number=getattr(cert, "serial_number", "—") or "—",
        email=getattr(cert, "email", "—") or "—",
        office_number=office,
        department=department,
        phone=phone_str,
        status=status_label,
        color=color,
        tag=tag,
    )
