import pytest
from defusedxml.common import DefusedXmlException

from certificate_analyzer.infrastructure.mchd.xml_parser import (
    MCHDParser,
    MchdXmlParser,
)


def test_namespaces_attribute_order_and_issuer(mchd_file):
    model = MchdXmlParser().parse(mchd_file())
    assert model.representative_fio == "Иванов Иван"
    assert model.representative_inn == "222"
    assert model.principal_name == "Организация & Ко"


def test_invalid_date_is_not_today(mchd_file):
    path = mchd_file(expiry="garbage")
    with pytest.raises(ValueError):
        MchdXmlParser().parse(path)
    assert MCHDParser.parse_file(path)["status"] == "Ошибка парсинга"


def test_xml_entities_rejected(tmp_path):
    path = tmp_path / "bad.xml"
    path.write_text('<!DOCTYPE x [<!ENTITY a "unsafe">]><x>&a;</x>')
    with pytest.raises(DefusedXmlException):
        MchdXmlParser().parse(path)
