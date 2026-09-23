"""Прикладной сервис генерации отчетов."""

from typing import Protocol, List
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.mchd import MchdDocument


class ReportExporter(Protocol):
    """Абстрактный экспортер отчетов, используемый Application-слоем."""

    def export(
        self,
        certificates: List[Certificate],
        mchd_list: List[MchdDocument],
        output_path: str,
    ) -> str:
        """Формирует отчет и сохраняет его по указанному пути.
        
        Args:
            certificates: Сертификаты.
            mchd_list: Доверенности.
            output_path: Путь файла.
            
        Returns:
            Итоговый путь к файлу.
        """
        ...
