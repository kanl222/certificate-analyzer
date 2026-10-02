from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import timezone, datetime
from typing import Any

from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


EMPTY = "—"


UTC = timezone.utc

def utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC)


def _display(value: Any, default: str = EMPTY) -> Any:
    """Replace None/empty string with UI placeholder."""
    return value if value not in (None, "") else default


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

    details: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        if key != "details" and hasattr(self, key):
            return getattr(self, key)

        return self.details.get(key, EMPTY)

    def get(self, key: str, default: Any = None) -> Any:
        if key != "details" and hasattr(self, key):
            return getattr(self, key)

        return self.details.get(key, default)

    def keys(self) -> list[str]:
        return [item.name for item in fields(self) if item.name != "details"] + list(
            self.details
        )

    def to_dict(self) -> dict[str, Any]:
        """Return flattened dictionary representation."""
        result = {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "details"
        }

        result.update(self.details)
        return result


STATUS_VIEW: dict[CertificateStatus, tuple[str, str]] = {
    CertificateStatus.EXPIRED: (
        "Просрочен",
        "#e57373",
    ),
    CertificateStatus.ACTIVE: (
        "В пределах срока",
        "#81c784",
    ),
    CertificateStatus.INVALID: (
        "Вне срока / неверные даты",
        "#e57373",
    ),
    CertificateStatus.REVOKED: (
        "Отозван",
        "#e57373",
    ),
}


def _status_view(
    status: CertificateStatus,
    valid_to: datetime,
) -> tuple[str, str]:
    """Convert certificate domain status to UI label and color."""

    if status is CertificateStatus.EXPIRING_SOON:
        days = max(
            0,
            (utc(valid_to) - datetime.now(UTC)).days,
        )
        return f"Истекает ({days} дн.)", "#ffd54f"

    return STATUS_VIEW.get(
        status,
        ("Неизвестен", "#bdbdbd"),
    )


def certificate_to_dto(cert) -> CertificateDTO:
    """Convert certificate domain model to DTO."""

    status, color = _status_view(
        cert.status,
        cert.valid_to,
    )

    employee = getattr(cert, "employee", None)

    phones = getattr(employee, "phones", None) if employee is not None else None

    return CertificateDTO(
        file_name=str(getattr(cert, "source_path", None) or EMPTY),
        file_type="Сертификат",
        valid_from=cert.valid_from.strftime("%d.%m.%Y"),
        valid_to=cert.valid_to.strftime("%d.%m.%Y"),
        subject_cn=_display(cert.subject),
        serial_number=_display(cert.serial_number),
        email=_display(getattr(cert, "email", None)),
        office_number=_display(getattr(employee, "office", None)),
        department=_display(getattr(employee, "department", None)),
        phone=", ".join(phones) if phones else EMPTY,
        status=status,
        color=color,
        details={
            "fingerprint_sha256": cert.fingerprint_sha256,
            "verification_status": "NOT_CHECKED",
            "Проверка подлинности": "Не проверена (подпись, доверие, отзыв)",
            "issuer": cert.issuer,
            "original_name": cert.original_name,
        },
    )


def certificate_to_dict(cert) -> dict[str, Any]:
    """Compatibility adapter for code expecting a dictionary."""
    return certificate_to_dto(cert).to_dict()
