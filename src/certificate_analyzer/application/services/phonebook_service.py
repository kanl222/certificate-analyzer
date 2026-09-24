import re
from pathlib import Path

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.phonebook.txt_loader import TxtPhonebookLoader


def normalize(text: str | None) -> str:
    """Нормализовать текст для сопоставления."""

    if not text:
        return ""

    cleaned = text.casefold().replace("ё", "е")

    cleaned = re.sub(
        r"[^\w\s]",
        "",
        cleaned,
    )

    return " ".join(cleaned.split())


class PhoneBook:
    """Справочник сотрудников."""

    def __init__(self) -> None:
        self._employees: list[Employee] = []

    @property
    def employees(self) -> tuple[Employee, ...]:
        return tuple(self._employees)

    def load(
        self,
        path: str | Path,
    ) -> None:
        path = Path(path)

        suffix = path.suffix.lower()

        if suffix == ".docx":
            from certificate_analyzer.infrastructure.phonebook.docx_loader import (
                DocxPhonebookLoader,
            )

            loader = DocxPhonebookLoader()

        elif suffix in {".txt", ".csv"}:
            loader = TxtPhonebookLoader()

        else:
            raise ValueError(f"Неподдерживаемый формат справочника: {suffix}")

        self._employees = loader.load(path)

    def find_phone(
        self,
        *,
        office: str | None = None,
        full_name: str | None = None,
        department: str | None = None,
    ) -> str | None:
        """Найти телефон сотрудника."""

        normalized_office = normalize(office)
        normalized_name = normalize(full_name)
        normalized_department = normalize(department)

        predicates = (
            lambda e: (normalized_office and normalize(e.office) == normalized_office),
            lambda e: (normalized_name and normalize(e.full_name) == normalized_name),
            lambda e: (
                normalized_department
                and normalize(e.department) == normalized_department
            ),
        )

        for predicate in predicates:
            phones = {
                phone
                for employee in self._employees
                if predicate(employee)
                for phone in employee.phones
                if self._is_valid_phone(phone)
            }

            if phones:
                return ", ".join(sorted(phones))

        return None

    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        if not re.search(r"\d", phone):
            return False

        value = phone.casefold()

        return not any(
            forbidden in value
            for forbidden in (
                "@",
                "http",
                "mail",
            )
        )
