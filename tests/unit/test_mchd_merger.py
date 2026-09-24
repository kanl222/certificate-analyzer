import pytest
from defusedxml import ElementTree as ET

from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger
from certificate_analyzer.infrastructure.mchd.xml_parser import MchdXmlParser, find


def test_merge_preserves_namespace_ids_and_sources(mchd_file, tmp_path):
    a = mchd_file("a.xml")
    b = mchd_file("b.xml", codes=("B", "C"))
    original = a.read_bytes()
    output = tmp_path / "merged.xml"
    MCHDMerger.merge_mchd_files([{"file_name": str(a)}, {"file_name": str(b)}], output)
    model = MchdXmlParser().parse(output)
    assert model.authority_codes == ["A", "B", "C"]
    assert model.internal_number == "internal"
    assert model.unified_number != "11111111-1111-1111-1111-111111111111"
    root = ET.parse(output).getroot()
    assert root.tag == "{urn:test}Доверенность"
    assert (
        find(root, "ДругойИдентификатор").text == "11111111-1111-1111-1111-111111111111"
    )
    assert a.read_bytes() == original


def test_reject_different_principals_and_source_overwrite(mchd_file):
    a = mchd_file("a.xml")
    b = mchd_file("b.xml", inn="other")
    with pytest.raises(ValueError):
        MCHDMerger.merge_mchd_files([{"file_name": str(a)}, {"file_name": str(b)}])
    b = mchd_file("b.xml")
    with pytest.raises(ValueError):
        MCHDMerger.merge_mchd_files([{"file_name": str(a)}, {"file_name": str(b)}], a)
