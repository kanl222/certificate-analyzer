"""Парсер XML файлов машиночитаемой доверенности (МЧД)."""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, List

from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.domain.enums.mchd_status import MchdStatus


class MchdXmlParser:
    """Парсер для извлечения данных из XML-файлов МЧД.
    
    Использует встроенную библиотеку xml.etree.ElementTree для безопасного
    разбора структуры документа, без использования регулярных выражений.
    """

    def parse(self, xml_path: str) -> Optional[MchdDocument]:
        """Парсит XML-файл МЧД и возвращает объект MchdDocument.

        Args:
            xml_path: Путь к XML-файлу для парсинга.

        Returns:
            Объект MchdDocument, если парсинг успешен, иначе None.
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except (ET.ParseError, FileNotFoundError, OSError):
            return None

        def find_element(node: ET.Element, name: str) -> Optional[ET.Element]:
            """Ищет первый элемент с заданным именем, игнорируя пространства имен."""
            for elem in node.iter():
                if elem.tag.endswith(name):
                    return elem
            return None

        def find_all_elements(node: ET.Element, name: str) -> List[ET.Element]:
            """Ищет все элементы с заданным именем, игнорируя пространства имен."""
            return [elem for elem in node.iter() if elem.tag.endswith(name)]

        # 1. Извлечение номера МЧД
        unified_number = ""
        internal_number = None

        sv_dov = find_element(root, "СвДов")
        if sv_dov is not None:
            unified_number = sv_dov.get("НомДовер", "")
            internal_number = sv_dov.get("ВнНомДовер")
        
        if not unified_number:
            nom_dover_elem = find_element(root, "НомДовер")
            if nom_dover_elem is not None and nom_dover_elem.text:
                unified_number = nom_dover_elem.text.strip()
                
        if not unified_number:
            unified_number = "Не найден"

        # 2. Извлечение дат
        valid_from_str = ""
        valid_to_str = ""

        if sv_dov is not None:
            valid_from_str = sv_dov.get("ДатаВыдДовер", "")
            valid_to_str = sv_dov.get("СрокДейст", "")

        if not valid_from_str:
            elem = find_element(root, "ДатаВыдДовер")
            if elem is not None and elem.text:
                valid_from_str = elem.text.strip()

        if not valid_to_str:
            elem = find_element(root, "СрокДейст")
            if elem is not None and elem.text:
                valid_to_str = elem.text.strip()
                
        valid_from = self._parse_date(valid_from_str) if valid_from_str else datetime.now()
        valid_to = self._parse_date(valid_to_str) if valid_to_str else datetime.now()

        # 3. Доверитель (Principal)
        principal_inn = "Не найден"
        principal_name = "Не найдено"
        org_elem = find_element(root, "СвРосОрг")
        if org_elem is not None:
            principal_inn = org_elem.get("ИННЮЛ", principal_inn)
            principal_name = org_elem.get("НаимОрг", principal_name)

        # 4. Представитель (Representative)
        representative_inn = "Не найден"
        representative_snils = "Не найден"
        representative_fio = "Не найдено"

        # Поиск представителя в СвУпПред
        for sv_up_pred in find_all_elements(root, "СвУпПред"):
            if sv_up_pred.get("ТипПред") == "3":
                sved_fiz_l = find_element(sv_up_pred, "СведФизЛ")
                if sved_fiz_l is not None:
                    representative_inn = sved_fiz_l.get("ИННФЛ", representative_inn)
                    representative_snils = sved_fiz_l.get("СНИЛС", representative_snils)
                elif sv_up_pred.get("СНИЛС"):
                    representative_snils = sv_up_pred.get("СНИЛС", representative_snils)

                fio_elem = find_element(sv_up_pred, "ФИО")
                if fio_elem is not None:
                    representative_fio = self._format_fio(fio_elem)
                break

        # Запасной вариант поиска представителя
        if representative_fio == "Не найдено":
            person_elem = find_element(root, "ЛицоБезДов")
            if person_elem is not None:
                svfl = find_element(person_elem, "СвФЛ")
                if svfl is not None:
                    representative_inn = svfl.get("ИННФЛ", representative_inn)
                    representative_snils = svfl.get("СНИЛС", representative_snils)
                fio_elem = find_element(person_elem, "ФИО")
                if fio_elem is not None:
                    representative_fio = self._format_fio(fio_elem)

        # 5. Полномочия
        authority_codes = set()
        for elem in root.iter():
            code = elem.get("КодПолн")
            if code:
                authority_codes.add(code)

        # 6. Статус
        now = datetime.now()
        status = MchdStatus.ACTIVE
        if valid_to < now:
            status = MchdStatus.EXPIRED
        elif (valid_to - now) <= timedelta(days=60):
            status = MchdStatus.EXPIRING_SOON

        return MchdDocument(
            unified_number=unified_number,
            internal_number=internal_number,
            principal_inn=principal_inn,
            principal_name=principal_name,
            representative_inn=representative_inn,
            representative_fio=representative_fio,
            representative_snils=representative_snils,
            valid_from=valid_from,
            valid_to=valid_to,
            status=status,
            authority_codes=list(authority_codes)
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Парсит строку с датой в объект datetime.

        Args:
            date_str: Строка с датой.

        Returns:
            Объект datetime. Возвращает текущее время при ошибке парсинга.
        """
        date_str = date_str.strip()
        for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d.%m.%y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return datetime.now()

    def _format_fio(self, fio_elem: ET.Element) -> str:
        """Формирует строку ФИО из XML элемента.

        Args:
            fio_elem: XML элемент ФИО.

        Returns:
            Строка с полным именем.
        """
        last_name = fio_elem.get("Фамилия", "").strip()
        first_name = fio_elem.get("Имя", "").strip()
        middle_name = fio_elem.get("Отчество", "").strip()
        return " ".join(filter(None, [last_name, first_name, middle_name]))
