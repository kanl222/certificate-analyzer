from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


def utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass(slots=True)
class CertificateDTO:
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
    
    details: Dict[str, Any] = None

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def keys(self):
        return self.__annotations__.keys()


def certificate_to_dict(cert):
    days = max(0, (utc(cert.valid_to) - datetime.now(timezone.utc)).days)
    labels = {
        CertificateStatus.EXPIRED: ("Просрочен", "#e57373"),
        CertificateStatus.EXPIRING_SOON: (f"Истекает ({days} дн.)", "#ffd54f"),
        CertificateStatus.ACTIVE: ("Активен", "#81c784"),
        CertificateStatus.INVALID: ("Недействителен", "#e57373"),
        CertificateStatus.REVOKED: ("Отозван", "#e57373"),
    }
    status, color = labels[cert.status]
    from dataclasses import asdict
    dto = CertificateDTO(
        file_name=getattr(cert, "source_path", "—"),
        file_type="Сертификат",
        valid_from=cert.valid_from.strftime("%d.%m.%Y"),
        valid_to=cert.valid_to.strftime("%d.%m.%Y"),
        subject_cn=cert.subject,
        serial_number=cert.serial_number or "—",
        email="—",
        office_number=cert.employee.office if cert.employee and cert.employee.office else "—",
        department=cert.employee.department if cert.employee and cert.employee.department else "—",
        phone=", ".join(cert.employee.phones) if cert.employee and getattr(cert.employee, "phones", None) else "—",
        status=status,
        color=color,
    )
    return asdict(dto)
