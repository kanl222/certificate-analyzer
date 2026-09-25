"""Доменная модель сотрудника организации."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class Employee:
    """Сущность сотрудника организации.

    Является центральным источником персональных данных для сертификатов,
    заявок на их получение и машиночитаемых доверенностей (МЧД).
    """

    full_name: str
    department: str | None = None
    office: str | None = None
    phones: list[str] = field(default_factory=list)
    id: int | None = None
    position: str | None = None
    email: str | None = None
    inn: str | None = None
    snils: str | None = None
    birth_date: date | None = None
