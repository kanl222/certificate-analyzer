"""Сервис управления и анализа машиночитаемых доверенностей (МЧД)."""

from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException

from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.infrastructure.certificates.scanner import scan_files
from certificate_analyzer.infrastructure.mchd.validator import MchdValidator
from certificate_analyzer.infrastructure.mchd.xml_parser import MchdXmlParser
from certificate_analyzer.infrastructure.repositories.mchd_repository import (
    MchdRepository,
)


class MchdService:
    """Сервис для сканирования, валидации, хранения и выборки МЧД."""

    def __init__(
        self,
        repository: MchdRepository | None = None,
        validator: MchdValidator | None = None,
    ) -> None:
        """Инициализирует сервис МЧД репозиторием и валидатором.

        Args:
            repository: Репозиторий для сохранения и чтения МЧД из базы данных.
            validator: Валидатор структуры и обязательных реквизитов МЧД.
        """
        self.repository = repository
        self.validator = validator or MchdValidator()
        self.errors: dict[str, str] = {}

    def scan(
        self,
        folder: str | Path,
        save_to_db: bool = False,
    ) -> list[MchdDocument]:
        """Сканирует директорию на наличие XML-файлов МЧД и парсит их.

        Args:
            folder: Путь к сканируемой папке.
            save_to_db: Флаг сохранения успешно распарсенных МЧД в базу данных.

        Returns:
            list[MchdDocument]: Список успешно распарсенных документов МЧД.
        """
        self.errors = {}
        documents: list[MchdDocument] = []
        parser = MchdXmlParser()

        for path in scan_files(folder, (".xml",)):
            try:
                doc = parser.parse(path)
                documents.append(doc)
                if save_to_db and self.repository:
                    self.repository.save(doc)
            except (ValueError, OSError, ParseError, DefusedXmlException) as exc:
                self.errors[str(path)] = str(exc)

        return documents

    def import_files(
        self,
        paths: list[str | Path],
        save_to_db: bool = True,
    ) -> list[MchdDocument]:
        """Импортирует список XML-файлов МЧД.

        Args:
            paths: Список путей к файлам доверенностей.
            save_to_db: Сохранять ли импортированные документы в базу данных.

        Returns:
            list[MchdDocument]: Список успешно импортированных документов.
        """
        documents: list[MchdDocument] = []
        parser = MchdXmlParser()

        for path in paths:
            try:
                doc = parser.parse(path)
                documents.append(doc)
                if save_to_db and self.repository:
                    self.repository.save(doc)
            except (ValueError, OSError, ParseError, DefusedXmlException) as exc:
                self.errors[str(path)] = str(exc)

        return documents

    def save(self, mchd: MchdDocument) -> MchdDocument:
        """Сохраняет доверенность в базе данных через репозиторий.

        Args:
            mchd: Доменная модель машиночитаемой доверенности.

        Returns:
            MchdDocument: Сохраненная доверенность.
        """
        if self.repository:
            return self.repository.save(mchd)
        return mchd

    def get_by_number(self, unified_number: str) -> MchdDocument | None:
        """Возвращает доверенность по единому регистрационному номеру.

        Args:
            unified_number: Уникальный номер доверенности.

        Returns:
            MchdDocument | None: Найденная доверенность или None.
        """
        if self.repository:
            return self.repository.get_by_number(unified_number)
        return None

    def list_all(
        self,
        search: str | None = None,
        authority_code: str | None = None,
        status: MchdStatus | None = None,
    ) -> list[MchdDocument]:
        """Возвращает список сохраненных МЧД с фильтрацией.

        Args:
            search: Строка поиска по ключевым атрибутам.
            authority_code: Код полномочия для фильтрации по классификатору.
            status: Статус действия доверенности.

        Returns:
            list[MchdDocument]: Список удовлетворяющих критериям доверенностей.
        """
        if self.repository:
            return self.repository.list_all(
                search=search,
                authority_code=authority_code,
                status=status,
            )
        return []

    def find_by_authority(self, code: str) -> list[MchdDocument]:
        """Находит доверенности по коду полномочия.

        Args:
            code: Код полномочия по классификатору.

        Returns:
            list[MchdDocument]: Список доверенностей с данным полномочием.
        """
        if self.repository:
            return self.repository.find_by_authority_code(code)
        return []

    def delete(self, unified_number: str) -> bool:
        """Удаляет доверенность из базы данных.

        Args:
            unified_number: Уникальный номер удаляемой доверенности.

        Returns:
            bool: True, если запись удалена, иначе False.
        """
        if self.repository:
            return self.repository.delete(unified_number)
        return False
