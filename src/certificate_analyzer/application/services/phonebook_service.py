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
        self._indexes: tuple[dict[str, set[str]], ...] = ({}, {}, {})

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
        indexes = ({}, {}, {})
        for employee in self._employees:
            phones = {p for p in employee.phones if self._is_valid_phone(p)}
            for index, value in zip(
                indexes, (employee.office, employee.full_name, employee.department)
            ):
                key = normalize(value)
                if key and phones:
                    index.setdefault(key, set()).update(phones)
        self._indexes = indexes

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

        for index, key in zip(
            self._indexes, (normalized_office, normalized_name, normalized_department)
        ):
            phones = index.get(key, set())
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
