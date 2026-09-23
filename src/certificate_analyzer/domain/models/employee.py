"""Доменная модель сотрудника организации."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class Employee:
    """Сущность сотрудника из телефонного справочника."""

    full_name: str
    department: Optional[str] = None
    office: Optional[str] = None
    phones: List[str] = field(default_factory=list)
