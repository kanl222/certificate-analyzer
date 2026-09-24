"""Доменная модель цифрового сертификата."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from certificate_analyzer.domain.models.employee import Employee

from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


@dataclass(slots=True)
class Certificate:
    """Сущность цифрового сертификата X.509.

    Для идентификации используется SHA-256 fingerprint.
    Приложение НЕ хранит и не извлекает закрытые ключи.
    """

    fingerprint_sha256: str
    subject: str
    issuer: str
    valid_from: datetime
    valid_to: datetime
    status: CertificateStatus = CertificateStatus.EXPIRED
    serial_number: Optional[str] = None
    has_private_key_link: bool = False
    owner_name: Optional[str] = None
    employee: Optional["Employee"] = None
