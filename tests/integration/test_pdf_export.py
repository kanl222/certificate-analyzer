from pathlib import Path
from certificate_analyzer.infrastructure.reports.pdf_exporter import (
    PdfReportExporter,
    pdf_font,
)


def test_pdf_cyrillic_and_markup(tmp_path):
    path = PdfReportExporter().export_rows(
        [{"subject_cn": "Иванов <Иван> & Ко", "phone": "00123"}],
        tmp_path / "report.pdf",
        "Отчёт <тест>",
    )
    assert pdf_font() == "AnalyzerSans"
    assert Path(path).read_bytes().startswith(b"%PDF-")
    assert Path(path).stat().st_size > 1000
