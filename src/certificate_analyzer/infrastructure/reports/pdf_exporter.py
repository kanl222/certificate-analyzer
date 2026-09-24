import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from certificate_analyzer.infrastructure.reports.rows import (
    HEADERS,
    model_rows,
    output_path,
    values,
)


def pdf_font():
    if "AnalyzerSans" in pdfmetrics.getRegisteredFontNames():
        return "AnalyzerSans"
    for path in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("/usr/share/fonts/noto/NotoSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ):
        if path.is_file():
            pdfmetrics.registerFont(TTFont("AnalyzerSans", str(path)))
            return "AnalyzerSans"
    raise RuntimeError("Для PDF с кириллицей установите шрифт DejaVu Sans или Arial")


class PdfReportExporter:
    def __init__(self, export_folder=""):
        self.export_folder = export_folder

    def export(
        self,
        certificates,
        mchds,
        save_path=None,
        report_title="Отчет по данным",
        figure=None,
    ):
        return self.export_rows(
            model_rows(certificates, mchds), save_path, report_title, figure
        )

    def export_rows(self, rows, save_path=None, report_title="Отчет", figure=None):
        target = output_path(self.export_folder, save_path, "pdf")
        font = pdf_font()
        style = ParagraphStyle(
            "Cell", fontName=font, fontSize=7, leading=9, splitLongWords=True
        )
        title = ParagraphStyle("ReportTitle", fontName=font, fontSize=14, leading=18)
        document = SimpleDocTemplate(
            target,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20,
        )
        story = [Paragraph(escape(report_title), title), Spacer(1, 12)]
        if figure is not None:
            buffer = io.BytesIO()
            figure.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
            buffer.seek(0)
            story.extend([Image(buffer, width=360, height=180), Spacer(1, 10)])
        paragraph = lambda text: Paragraph(escape(str(text or "")), style)
        data = [[paragraph(h) for h in HEADERS]] + [
            [paragraph(v) for v in values(row)] for row in rows
        ]
        fractions = [0.055, 0.09, 0.07, 0.07, 0.12, 0.1, 0.1, 0.065, 0.12, 0.13, 0.08]
        total = sum(fractions)
        table = Table(
            data,
            repeatRows=1,
            colWidths=[document.width * width / total for width in fractions],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ddd8ff")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        document.build(story)
        return target
