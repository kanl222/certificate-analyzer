"""Namespace-aware parser for the legacy МЧД formats (attributes and elements)."""

from datetime import datetime
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.domain.services.mchd_status import mchd_status


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def find(node, name):
    return (
        next((e for e in node.iter() if local_name(e.tag) == name), None)
        if node is not None
        else None
    )


def value(node, *names):
    if node is None:
        return ""
    for name in names:
        for elem in node.iter():
            if name in elem.attrib:
                return elem.attrib[name].strip()
            if local_name(elem.tag) == name and elem.text:
                return elem.text.strip()
    return ""


def parse_date(text):
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Некорректная или отсутствующая дата МЧД: {text!r}")


def fio(node):
    elem = find(node, "ФИО")
    return (
        " ".join(
            elem.get(k, "").strip()
            for k in ("Фамилия", "Имя", "Отчество")
            if elem.get(k, "").strip()
        )
        if elem is not None
        else ""
    )


class MchdXmlParser:
    def parse(self, xml_path):
        root = ET.parse(xml_path).getroot()
        number = value(root, "НомДовер", "DocumentId")
        if not number:
            raise ValueError("Отсутствует номер МЧД")
        start = parse_date(value(root, "ДатаВыдДовер", "IssueDate"))
        end = parse_date(value(root, "СрокДейст", "ExpiryDate"))
        if end < start:
            raise ValueError("Дата окончания МЧД раньше даты выдачи")
        representative = next(
            (
                e
                for e in root.iter()
                if local_name(e.tag) == "СвУпПред" and e.get("ТипПред") == "3"
            ),
            None,
        )
        org = find(root, "СвРосОрг")
        issuer = find(root, "ЛицоБезДов")
        codes = {}
        for elem in root.iter():
            code = elem.get("КодПолн", "").strip()
            if code:
                codes[code] = elem.get("НаимПолн", "")
        details = {
            "birth_date": value(representative, "ДатаРожд"),
            "issuer_org_kpp": value(org, "КПП"),
            "issuer_org_ogrn": value(org, "ОГРН"),
            "issuer_org_address": value(org, "АдрРФ"),
            "issuer_person_fullname": fio(issuer),
            "issuer_person_inn": value(issuer, "ИННФЛ"),
            "issuer_person_snils": value(issuer, "СНИЛС"),
            "issuer_person_position": value(issuer, "Должность"),
            "issuer_person_birthdate": value(issuer, "ДатаРожд"),
        }
        return MchdDocument(
            unified_number=number,
            internal_number=value(root, "ВнНомДовер") or None,
            principal_inn=value(org, "ИННЮЛ"),
            principal_name=value(org, "НаимОрг"),
            representative_inn=value(representative, "ИННФЛ"),
            representative_fio=fio(representative),
            representative_snils=value(representative, "СНИЛС"),
            valid_from=start,
            valid_to=end,
            status=mchd_status(end),
            authority_codes=sorted(codes),
        )


class MCHDParser:
    """Dictionary adapter for the migrated desktop interface."""

    @staticmethod
    def parse_file(file_path):
        from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict

        try:
            model = MchdXmlParser().parse(file_path)
            return mchd_to_dict(model)
        except (ValueError, OSError, ET.ParseError, DefusedXmlException) as exc:
            return {
                "file_name": str(file_path),
                "file_type": "МЧД",
                "status": "Ошибка парсинга",
                "color": "#e57373",
                "error": str(exc),
                "authority_codes": [],
                "authority_names": [],
            }
