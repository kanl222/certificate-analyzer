"""Экспортер отчетов в формате Excel."""

import os
from datetime import datetime
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.mchd import MchdDocument


class ExcelReportExporter:
    """Класс для экспорта данных в Excel.
    
    Отвечает за генерацию .xlsx отчетов по сертификатам и МЧД.
    """

    def __init__(self, export_folder: str = "") -> None:
        """Инициализирует экспортер.
        
        Args:
            export_folder: Путь к папке, куда будут сохраняться отчеты. Если не указан, сохраняется по указанному пути.
        """
        self.export_folder = export_folder
        if export_folder and not os.path.exists(export_folder):
            os.makedirs(export_folder, exist_ok=True)

    def export(self, certificates: List[Certificate], mchds: List[MchdDocument], save_path: Optional[str] = None, report_title: str = "Отчет по данным") -> str:
        """Экспортирует списки сертификатов и МЧД в Excel-файл.
        
        Args:
            certificates: Список объектов Certificate.
            mchds: Список объектов MchdDocument.
            save_path: Путь для сохранения файла (output_path).
            report_title: Заголовок отчета.
            
        Returns:
            Путь к сохраненному файлу Excel.
            
        Raises:
            Exception: Если произошла ошибка при сохранении или генерации.
        """
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Данные"
            
            # Заголовок
            ws.merge_cells('A1:G1')
            title_cell = ws.cell(row=1, column=1)
            title_cell.value = report_title
            title_cell.font = Font(size=14, bold=True, color="6c5ce7")
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Дата создания
            ws.merge_cells('A2:G2')
            date_cell = ws.cell(row=2, column=1)
            date_cell.value = f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            date_cell.font = Font(size=10, italic=True)
            date_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            ws.merge_cells('A3:G3')
            
            headers = ["Тип", "Идентификатор", "Владелец/Представитель", "Выдан", "Действ. с", "Действ. до", "Статус"]
            ws.append(headers)
            
            header_fill = PatternFill(start_color="6c5ce7", end_color="6c5ce7", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            alignment = Alignment(horizontal='left', vertical='center')
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))
                                 
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=4, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = alignment
                cell.border = thin_border
                
            # Добавление сертификатов
            status_map = {
                "ACTIVE": "Активен",
                "EXPIRING_SOON": "Истекает",
                "EXPIRED": "Просрочен",
                "REVOKED": "Отозван",
                "INVALID": "Недействителен"
            }
            
            for cert in certificates:
                status_str = status_map.get(cert.status.value, cert.status.value) if cert.status else "Неизвестно"
                ws.append([
                    "Сертификат",
                    cert.serial_number or cert.fingerprint_sha256[:10],
                    cert.owner_name or cert.subject,
                    cert.issuer,
                    cert.valid_from.strftime('%d.%m.%Y') if cert.valid_from else '',
                    cert.valid_to.strftime('%d.%m.%Y') if cert.valid_to else '',
                    status_str
                ])
                self._format_row(ws, ws.max_row, len(headers), alignment, thin_border, status_str)

            # Добавление МЧД
            for mchd in mchds:
                status_str = status_map.get(mchd.status.value, mchd.status.value) if mchd.status else "Неизвестно"
                ws.append([
                    "МЧД",
                    mchd.unified_number,
                    mchd.representative_fio,
                    mchd.principal_name,
                    mchd.valid_from.strftime('%d.%m.%Y') if mchd.valid_from else '',
                    mchd.valid_to.strftime('%d.%m.%Y') if mchd.valid_to else '',
                    status_str
                ])
                self._format_row(ws, ws.max_row, len(headers), alignment, thin_border, status_str)
                
            # Автоподбор ширины столбцов
            for col in ws.columns:
                max_length = 0
                column_letter = get_column_letter(col[0].column)
                for cell in col:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
                
            if not save_path:
                report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                save_path = os.path.join(self.export_folder, report_name)
                
            wb.save(save_path)
            return save_path
            
        except Exception as e:
            raise Exception(f"Ошибка экспорта в Excel: {str(e)}")

    def _format_row(self, ws, row_idx: int, col_count: int, alignment, border, status: str) -> None:
        """Форматирует строку в зависимости от статуса.
        
        Args:
            ws: Объект Worksheet (openpyxl).
            row_idx: Индекс строки.
            col_count: Количество столбцов.
            alignment: Выравнивание.
            border: Рамка.
            status: Строковый статус записи.
        """
        for col in range(1, col_count + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.alignment = alignment
            cell.border = border
            status_lower = status.lower()
            if "expired" in status_lower or "просрочен" in status_lower:
                cell.fill = PatternFill(start_color="f5c6cb", end_color="f5c6cb", fill_type="solid")
                cell.font = Font(color="721c24")
            elif "expiring" in status_lower or "истекает" in status_lower:
                cell.fill = PatternFill(start_color="ffeeba", end_color="ffeeba", fill_type="solid")
                cell.font = Font(color="856404")
            elif "active" in status_lower or "активен" in status_lower:
                cell.fill = PatternFill(start_color="c3e6cb", end_color="c3e6cb", fill_type="solid")
                cell.font = Font(color="155724")
