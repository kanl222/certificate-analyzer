"""Тесты валидатора и маппера машиночитаемых доверенностей (МЧД)."""

from datetime import UTC, datetime
from xml.etree.ElementTree import Element, SubElement
import pytest

from certificate_analyzer.application.dto.mchd_dto import MchdDTO
from certificate_analyzer.application.mappers.mchd_mapper import dto_to_mchd, mchd_to_dto
from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.exceptions import MchdValidationError
from certificate_analyzer.infrastructure.mchd.validator import (
    MchdValidator,
    is_valid_inn,
    is_valid_snils,
)


def test_inn_and_snils_validation():
    """Проверяет валидацию форматов ИНН и СНИЛС."""
    assert is_valid_inn("7701234567")
    assert is_valid_inn("770123456789")
    assert not is_valid_inn("123")
    assert not is_valid_inn("abc7701234567")

    assert is_valid_snils("12345678901")
    assert is_valid_snils("123-456-789 01")
    assert not is_valid_snils("12345")


def test_mchd_validator_valid_and_invalid():
    """Проверяет выявление ошибок структуры XML МЧД."""
    root = Element("Доверенность")
    errors = MchdValidator.validate_structure(root)
    assert len(errors) >= 3

    with pytest.raises(MchdValidationError):
        MchdValidator.validate_or_raise(root)

    # Заполняем валидный XML
    SubElement(root, "ИдДовер").text = "uuid-12345"
    SubElement(root, "ДатаВыд").text = "01.01.2026"
    SubElement(root, "ДатаКон").text = "31.12.2026"

    dov = SubElement(root, "Доверитель")
    SubElement(dov, "ИНН").text = "7701234567"

    rep = SubElement(root, "Представитель")
    SubElement(rep, "СНИЛС").text = "123-456-789 01"

    assert MchdValidator.validate_structure(root) == []


def test_mchd_mapper_roundtrip():
    """Проверяет преобразование между MchdDocument и MchdDTO."""
    doc = MchdDocument(
        unified_number="DOC-999",
        internal_number=None,
        principal_inn="7701234567",
        principal_name="ООО Ромашка",
        representative_inn="770199999999",
        representative_fio="Иванов Иван",
        representative_snils="12345678901",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_to=datetime(2026, 12, 31, tzinfo=UTC),
        status=MchdStatus.ACTIVE,
        authority_codes=["CODE1", "CODE2"],
        authority_names=["Подписание договоров", "Сдача отчетности"],
        source_path="incoming/doc999.xml",
    )

    dto = mchd_to_dto(doc)
    assert isinstance(dto, MchdDTO)
    assert dto.doc_number == "DOC-999"
    assert dto.full_name == "Иванов Иван"
    assert dto.authority_codes == ["CODE1", "CODE2"]

    restored = dto_to_mchd(dto)
    assert isinstance(restored, MchdDocument)
    assert restored.unified_number == "DOC-999"
    assert restored.representative_fio == "Иванов Иван"
    assert restored.authority_codes == ["CODE1", "CODE2"]
