"""Тесты валидации и парсинга набора демонстрационных тестовых МЧД."""

from pathlib import Path
import pytest

from certificate_analyzer.application.services.mchd_service import MchdService
from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger
from certificate_analyzer.infrastructure.mchd.xml_parser import (
    MCHDParser,
    MchdXmlParser,
)


@pytest.fixture
def test_mchd_dir() -> Path:
    """Возвращает путь к директории с тестовыми МЧД."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "test_mchd"
    return base_dir


def test_active_mchd_parsed(test_mchd_dir: Path):
    """Проверяет корректность разбора активной МЧД."""
    parser = MchdXmlParser()
    doc = parser.parse(test_mchd_dir / "mchd_active_01.xml")

    assert doc.unified_number == "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
    assert doc.internal_number == "МЧД-2026/001"
    assert doc.principal_name == 'ООО "Северные Технологии"'
    assert doc.principal_inn == "7701234567"
    assert doc.representative_fio == "Иванов Иван Иванович"
    assert doc.representative_inn == "770198765432"
    assert doc.representative_snils == "123-456-789 01"
    assert doc.status == MchdStatus.ACTIVE
    assert "BUN_001" in doc.authority_codes
    assert "BUN_002" in doc.authority_codes
    assert "STAT_001" in doc.authority_codes


def test_expiring_soon_mchd(test_mchd_dir: Path):
    """Проверяет определение статуса EXPIRING_SOON для истекающей доверенности."""
    parser = MchdXmlParser()
    doc = parser.parse(test_mchd_dir / "mchd_expiring_soon.xml")

    assert doc.status == MchdStatus.EXPIRING_SOON
    assert doc.representative_fio == "Смирнова Елена Сергеевна"
    assert "KDR_001" in doc.authority_codes


def test_expired_mchd(test_mchd_dir: Path):
    """Проверяет определение статуса EXPIRED для просроченной доверенности."""
    parser = MchdXmlParser()
    doc = parser.parse(test_mchd_dir / "mchd_expired.xml")

    assert doc.status == MchdStatus.EXPIRED
    assert doc.representative_fio == "Кузнецов Алексей Петрович"


def test_mincifry_format_003(test_mchd_dir: Path):
    """Проверяет разбор формата 003 Минцифры."""
    parser = MchdXmlParser()
    doc = parser.parse(test_mchd_dir / "mchd_mincifry_format_003.xml")

    assert doc.unified_number == "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"
    assert doc.representative_fio == "Васильев Дмитрий Николаевич"
    assert "FED_GOS_01" in doc.authority_codes


def test_merge_test_mchds(test_mchd_dir: Path, tmp_path: Path):
    """Проверяет успешное объединение двух тестовых МЧД одного представителя."""
    file_a = test_mchd_dir / "mchd_active_01.xml"
    file_b = test_mchd_dir / "mchd_active_02_mergeable.xml"
    out_file = tmp_path / "merged_output.xml"

    MCHDMerger.merge_mchd_files(
        [{"file_name": str(file_a)}, {"file_name": str(file_b)}],
        out_file,
    )

    merged_doc = MchdXmlParser().parse(out_file)
    assert set(merged_doc.authority_codes) == {
        "BUN_001",
        "BUN_002",
        "STAT_001",
        "FIN_001",
        "BANK_005",
    }
    assert merged_doc.principal_name == 'ООО "Северные Технологии"'
    assert merged_doc.representative_fio == "Иванов Иван Иванович"


def test_invalid_mchd_handling(test_mchd_dir: Path):
    """Проверяет корректный возврат статуса 'Ошибка парсинга' для невалидного файла."""
    data = MCHDParser.parse_file(test_mchd_dir / "mchd_invalid_error.xml")
    assert data["status"] == "Ошибка парсинга"
    assert "error" in data


def test_service_scan_directory(test_mchd_dir: Path):
    """Проверяет сканирование папки test_mchd через MchdService."""
    service = MchdService()
    docs = service.scan(test_mchd_dir, save_to_db=False)

    # Должно успешно распарситься 6 файлов, и 1 файл попасть в ошибки
    assert len(docs) == 6
    assert any("mchd_invalid_error.xml" in err for err in service.errors)
