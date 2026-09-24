"""Модуль для загрузки телефонного справочника из TXT файлов."""

import re
from typing import List

from certificate_analyzer.domain.models.employee import Employee


class TxtPhonebookLoader:
    """Загрузчик телефонного справочника из формата TXT."""

    def load(self, file_path: str) -> List[Employee]:
        """Загружает данные сотрудников из TXT файла.

        Args:
            file_path: Путь к файлу TXT со справочником.

        Returns:
            Список объектов Employee.

        Raises:
            Exception: При ошибке чтения файла.
        """
        employees: List[Employee] = []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if (
                not line
                or line.startswith("+")
                or line.startswith("|==")
                or line.startswith("|--")
            ):
                continue

            if line.startswith("|"):
                parts = line.split("|")
                if len(parts) >= 3:
                    department = self._clean_text(parts[1]) if len(parts) > 1 else ""
                    full_name = self._clean_text(parts[2]) if len(parts) > 2 else ""
                    office = self._clean_text(parts[3]) if len(parts) > 3 else ""

                    phones = []
                    for i in range(4, min(len(parts), 7)):
                        phone_part = self._clean_text(parts[i])
                        if (
                            phone_part
                            and phone_part not in ["-", "—", "####", "#", ""]
                            and not phone_part.startswith("#")
                        ):
                            if not any(
                                x in phone_part.lower() for x in ["@", "mail", "http"]
                            ):
                                for p in phone_part.split(","):
                                    p_clean = p.strip()
                                    if p_clean:
                                        phones.append(p_clean)

                    name = full_name
                    cabinet = self._normalize_cabinet(office)

                    if name or department or cabinet:
                        if (
                            name
                            and name != "—"
                            and any(x in name.lower() for x in ["@", "mail", "http"])
                        ):
                            name = "—"
                        if (
                            department
                            and department != "—"
                            and any(
                                x in department.lower() for x in ["@", "mail", "http"]
                            )
                        ):
                            department = "—"

                        name_val = name if name and name != "—" else "—"
                        dept_val = (
                            department if department and department != "—" else None
                        )
                        off_val = cabinet if cabinet and cabinet != "—" else None

                        emp = Employee(
                            full_name=name_val,
                            department=dept_val,
                            office=off_val,
                            phones=phones,
                        )
                        employees.append(emp)

        return employees

    def _clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов и пробелов.

        Args:
            text: Исходный текст.

        Returns:
            Очищенный текст.
        """
        if not text:
            return ""
        text = re.sub(r"[•▪▫◦▪▸►]", "", text)
        text = " ".join(text.split())
        return text.strip()

    def _normalize_cabinet(self, cabinet: str) -> str:
        """Нормализует номер кабинета.

        Args:
            cabinet: Исходный номер кабинета.

        Returns:
            Нормализованный номер кабинета.
        """
        if not cabinet or cabinet in ("—", "-"):
            return ""
        cabinet = re.sub(r"[^\d\w]", "", cabinet)
        return cabinet.strip()
