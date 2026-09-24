from openpyxl import load_workbook

from certificate_analyzer.infrastructure.reports.excel_exporter import (
    ExcelReportExporter,
)


def test_export_preserves_text_metadata_and_formula_literals(tmp_path):
    path = ExcelReportExporter().export_rows(
        [{"subject_cn": "=1+2", "phone": "00123", "status": "Просрочен"}],
        tmp_path / "report.xlsx",
    )
    sheet = load_workbook(path).active
    assert sheet["E5"].value == "=1+2"
    assert sheet["E5"].data_type == "s"
    assert sheet["J5"].value == "00123"
    assert sheet["K5"].value == "Просрочен"
    assert sheet["A4"].value == "Тип"
