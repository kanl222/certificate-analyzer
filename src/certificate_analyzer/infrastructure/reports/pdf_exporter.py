"""Экспортер отчетов в формате PDF."""

import os
import io
from datetime import datetime
from typing import List, Optional, Any

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus

# Attempt to load fonts
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
    PDF_FONT = 'Arial'
except Exception:
    PDF_FONT = 'Helvetica'

class PdfReportExporter:
    """Класс для экспорта данных в PDF.
    
    Отвечает за генерацию .pdf отчетов по сертификатам и МЧД.
    """

    def __init__(self, export_folder: str = "") -> None:
        """Инициализирует экспортер.
        
        Args:
            export_folder: Путь к папке, куда будут сохраняться отчеты.
        """
        self.export_folder = export_folder
        if export_folder and not os.path.exists(export_folder):
            os.makedirs(export_folder, exist_ok=True)

    def export(self, certificates: List[Certificate], mchds: List[MchdDocument], save_path: Optional[str] = None, report_title: str = "Отчет по данным", figure: Any = None) -> str:
        """Экспортирует списки сертификатов и МЧД в PDF-файл.
        
        Args:
            certificates: Список объектов Certificate.
            mchds: Список объектов MchdDocument.
            save_path: Опциональный путь для сохранения файла.
            report_title: Заголовок отчета.
            figure: График (matplotlib figure), если есть.
            
        Returns:
            Путь к сохраненному файлу PDF.
            
        Raises:
            Exception: Если произошла ошибка при сохранении или генерации.
        """
        try:
            if not save_path:
                report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                save_path = os.path.join(self.export_folder, report_name)
                
            doc = SimpleDocTemplate(save_path, pagesize=landscape(letter),
                                    leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                                    topMargin=0.5 * inch, bottomMargin=0.5 * inch)
                                    
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('TitleStyle', parent=styles['Title'],
                                         fontName=f'{PDF_FONT}-Bold' if PDF_FONT == 'Arial' else 'Helvetica-Bold',
                                         fontSize=14, spaceAfter=10, alignment=1,
                                         textColor=colors.HexColor("#6c5ce7"))
            subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'],
                                            fontName=PDF_FONT, fontSize=10, alignment=1, spaceAfter=20)
            normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'],
                                          fontName=PDF_FONT, fontSize=7, leading=8)
            table_header_style = ParagraphStyle('TableHeader', parent=styles['Normal'],
                                                fontName=f'{PDF_FONT}-Bold' if PDF_FONT == 'Arial' else 'Helvetica-Bold',
                                                fontSize=7, textColor=colors.white)
                                                
            elements = []
            elements.append(Paragraph(report_title, title_style))
            elements.append(Paragraph(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", subtitle_style))
            elements.append(Spacer(1, 8))
            
            # Статистика
            total_certs = len(certificates)
            total_mchds = len(mchds)
            total = total_certs + total_mchds
            
            stats_text = f"<b>Статистика:</b><br/>Всего записей: {total} (Сертификаты: {total_certs}, МЧД: {total_mchds})"
            elements.append(Paragraph(stats_text, normal_style))
            elements.append(Spacer(1, 10))
            
            if figure:
                try:
                    imgdata = io.BytesIO()
                    figure.savefig(imgdata, format='png', dpi=100, bbox_inches='tight')
                    imgdata.seek(0)
                    img = Image(imgdata, width=5 * inch, height=2.5 * inch)
                    elements.append(img)
                    elements.append(Spacer(1, 10))
                except Exception as e:
                    print(f"Ошибка при добавлении графика в PDF: {e}")
                    
            if certificates or mchds:
                table_data = []
                headers = ["Тип", "Идентификатор", "Владелец", "Выдан", "Действ. с", "Действ. до", "Статус"]
                table_data.append([Paragraph(h, table_header_style) for h in headers])
                
                # Добавляем сертификаты
                status_map = {
                    "ACTIVE": "Активен",
                    "EXPIRING_SOON": "Истекает",
                    "EXPIRED": "Просрочен",
                    "REVOKED": "Отозван",
                    "INVALID": "Недействителен"
                }
                
                for cert in certificates:
                    status_str = status_map.get(cert.status.value, cert.status.value) if cert.status else "Неизвестно"
                    table_data.append([
                        Paragraph("Серт", normal_style),
                        Paragraph(str(cert.serial_number or cert.fingerprint_sha256[:10])[:15], normal_style),
                        Paragraph(str(cert.owner_name or cert.subject)[:30], normal_style),
                        Paragraph(str(cert.issuer)[:20], normal_style),
                        Paragraph(cert.valid_from.strftime('%d.%m.%Y') if cert.valid_from else '', normal_style),
                        Paragraph(cert.valid_to.strftime('%d.%m.%Y') if cert.valid_to else '', normal_style),
                        Paragraph(status_str[:15], normal_style)
                    ])
                    
                # Добавляем МЧД
                for mchd in mchds:
                    status_str = status_map.get(mchd.status.value, mchd.status.value) if mchd.status else "Неизвестно"
                    table_data.append([
                        Paragraph("МЧД", normal_style),
                        Paragraph(str(mchd.unified_number)[:15], normal_style),
                        Paragraph(str(mchd.representative_fio)[:30], normal_style),
                        Paragraph(str(mchd.principal_name)[:20], normal_style),
                        Paragraph(mchd.valid_from.strftime('%d.%m.%Y') if mchd.valid_from else '', normal_style),
                        Paragraph(mchd.valid_to.strftime('%d.%m.%Y') if mchd.valid_to else '', normal_style),
                        Paragraph(status_str[:15], normal_style)
                    ])
                    
                col_widths = [0.5, 1.2, 2.5, 1.5, 0.8, 0.8, 1.0]
                col_widths = [w * inch for w in col_widths]
                
                cert_table = Table(table_data, repeatRows=1, colWidths=col_widths)
                cert_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#6c5ce7")),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                
                # Применяем цвета к строкам
                idx = 1
                for cert in certificates:
                    status_str = cert.status.value if cert.status else ""
                    self._apply_row_color(cert_table, idx, status_str)
                    idx += 1
                for mchd in mchds:
                    status_str = mchd.status.value if mchd.status else ""
                    self._apply_row_color(cert_table, idx, status_str)
                    idx += 1
                    
                elements.append(cert_table)
                
            doc.build(elements)
            return save_path
            
        except Exception as e:
            raise Exception(f"Ошибка экспорта в PDF: {str(e)}")

    def _apply_row_color(self, table: Table, row_idx: int, status: str) -> None:
        """Применяет цвет фона к строке таблицы в зависимости от статуса.
        
        Args:
            table: Объект Table (reportlab).
            row_idx: Индекс строки.
            status: Строковый статус записи.
        """
        status_lower = status.lower()
        if "expired" in status_lower or "просрочен" in status_lower:
            bg_color = colors.HexColor("#e57373")
        elif "expiring" in status_lower or "истекает" in status_lower:
            bg_color = colors.HexColor("#ffd54f")
        elif "active" in status_lower or "активен" in status_lower:
            bg_color = colors.HexColor("#81c784")
        else:
            bg_color = colors.white
        table.setStyle(TableStyle([('BACKGROUND', (0, row_idx), (-1, row_idx), bg_color)]))
