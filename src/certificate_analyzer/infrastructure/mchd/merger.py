"""Create an unsigned draft with combined authorities, preserving source XML."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as XML

from defusedxml import ElementTree as ET

from certificate_analyzer.infrastructure.mchd.xml_parser import (
    MchdXmlParser,
    find,
    local_name,
)


class MCHDMerger:
    @staticmethod
    def get_merged_authorities(mchd_list):
        if not mchd_list:
            return None
        codes = sorted(
            {code for doc in mchd_list for code in doc.get("authority_codes", [])}
        )
        return {
            "person_name": mchd_list[0].get("full_name", ""),
            "total_files": len(mchd_list),
            "unique_codes_count": len(codes),
            "codes": codes,
            "file_names": [Path(doc["file_name"]).name for doc in mchd_list],
        }

    @staticmethod
    def merge_mchd_files(mchd_list, output_path=None):
        if len(mchd_list) < 2:
            raise ValueError("Для объединения нужны минимум две МЧД")
        paths = [Path(doc["file_name"]) for doc in mchd_list]
        models = [MchdXmlParser().parse(path) for path in paths]
        first = models[0]
        identity = (
            first.principal_inn,
            first.representative_inn,
            first.representative_snils,
            first.representative_fio,
        )
        if not first.principal_inn or not (
            first.representative_inn or first.representative_snils
        ):
            raise ValueError("Недостаточно идентификаторов доверителя и представителя")
        if any(
            (
                m.principal_inn,
                m.representative_inn,
                m.representative_snils,
                m.representative_fio,
            )
            != identity
            for m in models[1:]
        ):
            raise ValueError(
                "МЧД должны относиться к одному доверителю и представителю"
            )
        if any(
            (m.valid_from, m.valid_to) != (first.valid_from, first.valid_to)
            for m in models[1:]
        ):
            raise ValueError("Сроки действия объединяемых МЧД должны совпадать")
        root = deepcopy(ET.parse(paths[0]).getroot())
        number = str(uuid4())
        info = find(root, "СвДов")
        if info is None:
            raise ValueError("Объединение поддерживает XML со структурой СвДов")
        if "НомДовер" in info.attrib:
            info.set("НомДовер", number)
        else:
            number_element = find(info, "НомДовер")
            if number_element is None:
                raise ValueError("Номер доверенности отсутствует в СвДов")
            number_element.text = number
        for elem in root.iter():
            if "ИдФайл" in elem.attrib:
                elem.set("ИдФайл", f"ON_EMCHD_{datetime.now():%Y%m%d}_{number}")
        # Existing signatures cannot authenticate a newly generated draft.
        for parent in root.iter():
            for child in list(parent):
                if child.tag == "{http://www.w3.org/2000/09/xmldsig#}Signature":
                    parent.remove(child)
        system = find(root, "СведСист")
        if system is not None and system.text and "guid=" in system.text:
            system.text = f"https://m4d.nalog.gov.ru/emchd/check-status?guid={number}"
        authorities = find(root, "СвПолн")
        namespace = info.tag.rsplit("}", 1)[0] + "}" if "}" in info.tag else ""
        if authorities is None:
            authorities = XML.SubElement(
                info, namespace + "СвПолн", {"ТипПолн": "1", "ПрСовмПолн": "1"}
            )
        namespace = (
            authorities.tag.rsplit("}", 1)[0] + "}" if "}" in authorities.tag else ""
        )
        for child in list(authorities):
            if local_name(child.tag) == "МашПолн":
                authorities.remove(child)
        codes = {
            code: ""
            for model in models
            for code in model.authority_codes
        }
        for code in sorted(codes):
            attrs = {"КодПолн": code}
            if codes[code]:
                attrs["НаимПолн"] = codes[code]
            XML.SubElement(authorities, namespace + "МашПолн", attrs)
        target = (
            Path(output_path)
            if output_path
            else paths[0].with_name(f"Объединенная_МЧД_{number}.xml")
        )
        if target.resolve() in {path.resolve() for path in paths}:
            raise ValueError("Нельзя перезаписывать исходную МЧД")
        XML.indent(root)
        XML.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
        return str(target)
