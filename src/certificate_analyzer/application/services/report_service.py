class ReportService:
    def export(self, format, certificates, mchds, output_path):
        if format == "xlsx":
            from certificate_analyzer.infrastructure.reports.excel_exporter import (
                ExcelReportExporter,
            )

            exporter = ExcelReportExporter()
        elif format == "pdf":
            from certificate_analyzer.infrastructure.reports.pdf_exporter import (
                PdfReportExporter,
            )

            exporter = PdfReportExporter()
        else:
            raise ValueError(f"Неизвестный формат отчета: {format}")
        return exporter.export(certificates, mchds, str(output_path))
