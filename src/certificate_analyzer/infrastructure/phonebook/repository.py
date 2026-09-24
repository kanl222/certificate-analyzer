"""Репозиторий телефонного справочника сотрудников."""

from typing import Protocol, List
from certificate_analyzer.domain.models.employee import Employee


class PhoneBookRepository(Protocol):
    """Интерфейс репозитория сотрудников."""

    def get_all(self) -> List[Employee]: ...

    def find_by_name(self, name: str) -> Employee | None: ...
