"""Перечисление статусов машиночитаемой доверенности (МЧД)."""

from enum import Enum


class MchdStatus(str, Enum):
    """Статусы действия машиночитаемой доверенности."""

    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
