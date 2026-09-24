"""Namespace-aware parser for legacy МЧД XML formats.

Supports values stored both as XML attributes and as element text.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.domain.services.mchd_status import mchd_status

DATE_FORMATS = (
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%d.%m.%y",
)


def local_name(tag: str) -> str:
    """Return XML tag name without namespace."""
    return tag.rsplit("}", 1)[-1]


def find_element(node: Element | None, name: str) -> Element | None:
    """Find first descendant by local XML tag name."""
    if node is None:
        return None

    return next(
        (element for element in node.iter() if local_name(element.tag) == name),
        None,
    )


# Backward-compatible alias imported by merger.py
find = find_element  # noqa: F401


def get_value(node: Element | None, *names: str) -> str:
    """Read first matching value from attribute or element text.

    Legacy МЧД formats may store the same logical field either as:
    - an XML attribute;
    - a nested XML element.
    """
    if node is None:
        return ""

    names_set = set(names)

    for element in node.iter():
        # Attributes have priority to preserve legacy behaviour.
        for name in names:
            value = element.attrib.get(name)
            if value:
                value = value.strip()
                if value:
                    return value

        if local_name(element.tag) in names_set and element.text:
            value = element.text.strip()
            if value:
                return value

    return ""


def parse_date(value: str, *, field_name: str = "дата") -> datetime:
    """Parse a legacy МЧД date."""
    value = value.strip()

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            pass

    raise ValueError(
        f"Некорректная или отсутствующая {field_name} МЧД: {value!r}"
    )


def get_fio(node: Element | None) -> str:
    """Build person's full name from ФИО attributes."""
    fio_element = find_element(node, "ФИО")
    if fio_element is None:
        return ""

    return " ".join(
        value
        for key in ("Фамилия", "Имя", "Отчество")
        if (value := fio_element.get(key, "").strip())
    )


def find_representative(root: Element) -> Element | None:
    """Find a natural-person representative (ТипПред=3)."""
    return next(
        (
            element
            for element in root.iter()
            if local_name(element.tag) == "СвУпПред"
            and element.get("ТипПред") == "3"
        ),
        None,
    )


def collect_authority_codes(root: Element) -> list[str]:
    """Collect unique authority codes in sorted order."""
    return sorted(
        {
            code
            for element in root.iter()
            if (code := element.get("КодПолн", "").strip())
        }
    )


class MchdXmlParser:
    """Parser for legacy МЧД XML documents."""

    def parse(self, xml_path: str | Path) -> MchdDocument:
        root = ET.parse(xml_path).getroot()

        number = get_value(root, "НомДовер", "DocumentId")
        if not number:
            raise ValueError("Отсутствует номер МЧД")

        valid_from = parse_date(
            get_value(root, "ДатаВыдДовер", "IssueDate"),
            field_name="дата выдачи",
        )
        valid_to = parse_date(
            get_value(root, "СрокДейст", "ExpiryDate"),
            field_name="дата окончания",
        )

        if valid_to < valid_from:
            raise ValueError("Дата окончания МЧД раньше даты выдачи")

        representative = find_representative(root)
        organization = find_element(root, "СвРосОрг")

        return MchdDocument(
            unified_number=number,
            internal_number=get_value(root, "ВнНомДовер") or None,
            principal_inn=get_value(organization, "ИННЮЛ"),
            principal_name=get_value(organization, "НаимОрг"),
            representative_inn=get_value(representative, "ИННФЛ"),
            representative_fio=get_fio(representative),
            representative_snils=get_value(representative, "СНИЛС"),
            valid_from=valid_from,
            valid_to=valid_to,
            status=mchd_status(valid_to),
            authority_codes=collect_authority_codes(root),
        )


class MCHDParser:
    """Dictionary adapter for the migrated desktop interface."""

    @staticmethod
    def parse_file(file_path: str | Path) -> dict:
        from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict

        try:
            model = MchdXmlParser().parse(file_path)
            return mchd_to_dict(model)

        except (
            ValueError,
            OSError,
            ET.ParseError,
            DefusedXmlException,
        ) as exc:
            return {
                "file_name": str(file_path),
                "file_type": "МЧД",
                "status": "Ошибка парсинга",
                "color": "#e57373",
                "error": str(exc),
                "authority_codes": [],
                "authority_names": [],
            }