"""Доменная модель сотрудника организации."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Employee:
    """Сущность сотрудника из телефонного справочника."""

    full_name: str
    department: str | None = None
    office: str | None = None
    phones: list[str] = field(default_factory=list)
