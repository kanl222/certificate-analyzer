"""Валидация структуры и реквизитов машиночитаемых доверенностей (МЧД)."""

import re
from xml.etree.ElementTree import Element

from certificate_analyzer.exceptions import MchdValidationError
from certificate_analyzer.infrastructure.mchd.xml_parser import find_element, get_value


def is_valid_inn(inn: str) -> bool:
    """Проверяет корректность формата ИНН (10 цифр для ЮЛ, 12 цифр для ФЛ/ИП).

    Args:
        inn: Строка ИНН.

    Returns:
        bool: True, если ИНН состоит из 10 или 12 цифр.
    """
    clean_inn = inn.strip()
    return bool(re.fullmatch(r"\d{10}|\d{12}", clean_inn))


def is_valid_snils(snils: str) -> bool:
    """Проверяет корректность формата СНИЛС (11 цифр).

    Args:
        snils: Строка СНИЛС (может содержать дефисы и пробелы).

    Returns:
        bool: True, если очищенная строка СНИЛС содержит ровно 11 цифр.
    """
    digits = re.sub(r"\D", "", snils)
    return len(digits) == 11


class MchdValidator:
    """Валидатор структуры и обязательных реквизитов XML-файлов МЧД."""

    @staticmethod
    def validate_structure(root: Element) -> list[str]:
        """Проверяет наличие обязательных узлов и форматов полей в дереве XML.

        Args:
            root: Корневой XML-элемент документа МЧД.

        Returns:
            list[str]: Список обнаруженных ошибок валидации (пустой при успехе).
        """
        errors: list[str] = []

        # 1. Проверка номера/идентификатора доверенности
        doc_id = get_value(root, "ИдДовер", "НомерДовер", "Номер")
        if not doc_id:
            errors.append("Отсутствует обязательный идентификатор (номер) доверенности")

        # 2. Проверка дат действия
        date_from = get_value(root, "ДатаВыд", "ДатаНач", "ДатаВыдачи")
        date_to = get_value(root, "ДатаКон", "СрокДейст", "ДатаОконч")
        if not date_from:
            errors.append("Отсутствует дата выдачи (начала действия) доверенности")
        if not date_to:
            errors.append("Отсутствует дата окончания действия доверенности")

        # 3. Проверка доверителя
        principal = find_element(root, "Доверитель") or find_element(root, "СвДоверит")
        if principal is None:
            errors.append("В документе не найден блок сведений о доверителе")
        else:
            inn = get_value(principal, "ИНН", "ИННЮЛ", "ИННФЛ")
            if inn and not is_valid_inn(inn):
                errors.append(f"Некорректный формат ИНН доверителя: {inn}")

        # 4. Проверка представителя
        rep = find_element(root, "Представитель") or find_element(root, "СвУполном")
        if rep is None:
            errors.append("В документе не найден блок сведений о представителе")
        else:
            snils = get_value(rep, "СНИЛС")
            if snils and not is_valid_snils(snils):
                errors.append(f"Некорректный формат СНИЛС представителя: {snils}")

        return errors

    @classmethod
    def validate_or_raise(cls, root: Element) -> None:
        """Проверяет структуру МЧД и выбрасывает исключение при наличии ошибок.

        Args:
            root: Корневой XML-элемент документа МЧД.

        Raises:
            MchdValidationError: Если валидация выявила ошибки в документе.
        """
        errors = cls.validate_structure(root)
        if errors:
            raise MchdValidationError("; ".join(errors))
