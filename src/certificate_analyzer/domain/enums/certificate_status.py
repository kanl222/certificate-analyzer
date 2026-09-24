"""Перечисление статусов цифрового сертификата."""

from enum import Enum


class CertificateStatus(str, Enum):
    """Статусы жизненного цикла цифрового сертификата."""

    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    INVALID = "INVALID"
