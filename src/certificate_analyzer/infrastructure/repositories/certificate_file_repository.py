"""Репозиторий для управления записями файлов сертификатов в SQLite."""

from datetime import datetime
from sqlalchemy import delete, select

from certificate_analyzer.domain.models.certificate_file import CertificateFile
from certificate_analyzer.infrastructure.database.models.certificates import (
    CertificateSourceModel,
)


class CertificateFileRepository:
    """Репозиторий физических файлов сертификатов на базе SQLAlchemy."""

    def __init__(self, session_factory):
        """Инициализирует репозиторий файлов сертификатов.

        Args:
            session_factory: Фабрика сессий SQLAlchemy.
        """
        self.sessions = session_factory

    @staticmethod
    def _to_domain(model: CertificateSourceModel) -> CertificateFile:
        """Преобразует модель БД CertificateSourceModel в доменную сущность CertificateFile.

        Args:
            model: Модель базы данных.

        Returns:
            CertificateFile: Доменная сущность файла сертификата.
        """
        return CertificateFile(
            path=model.path,
            fingerprint=model.fingerprint,
            file_name=model.file_name or "",
            size=model.size or 0,
            first_seen_at=model.first_seen_at or datetime.utcnow(),
            last_seen_at=model.last_seen_at or datetime.utcnow(),
            content_sha256=model.content_sha256 or "",
        )

    def save(self, file_info: CertificateFile) -> CertificateFile:
        """Сохраняет или обновляет метаданные файла сертификата.

        Args:
            file_info: Доменная сущность файла.

        Returns:
            CertificateFile: Сохраненный файл.
        """
        now = datetime.utcnow()
        with self.sessions.begin() as session:
            model = session.get(CertificateSourceModel, file_info.path)
            if not model:
                model = CertificateSourceModel(
                    path=file_info.path,
                    fingerprint=file_info.fingerprint,
                    content_sha256=file_info.content_sha256,
                    file_name=file_info.file_name,
                    size=file_info.size,
                    first_seen_at=file_info.first_seen_at or now,
                    last_seen_at=now,
                )
                session.add(model)
            else:
                model.fingerprint = file_info.fingerprint
                model.content_sha256 = file_info.content_sha256
                model.file_name = file_info.file_name or model.file_name
                model.size = file_info.size or model.size
                model.last_seen_at = now
            session.flush()
            return self._to_domain(model)

    def get_by_path(self, path: str) -> CertificateFile | None:
        """Получает запись файла по его пути.

        Args:
            path: Абсолютный путь к файлу.

        Returns:
            CertificateFile | None: Найденная запись или None.
        """
        with self.sessions() as session:
            model = session.get(CertificateSourceModel, path)
            return self._to_domain(model) if model else None

    def list_by_fingerprint(self, fingerprint: str) -> list[CertificateFile]:
        """Возвращает все зарегистрированные файлы для заданного отпечатка сертификата.

        Args:
            fingerprint: SHA-256 отпечаток сертификата.

        Returns:
            list[CertificateFile]: Список записей файлов.
        """
        with self.sessions() as session:
            stmt = select(CertificateSourceModel).where(
                CertificateSourceModel.fingerprint == fingerprint
            )
            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]

    def delete_by_path(self, path: str) -> bool:
        """Удаляет запись файла по пути.

        Args:
            path: Абсолютный путь к файлу.

        Returns:
            bool: True, если запись была найдена и удалена, иначе False.
        """
        with self.sessions.begin() as session:
            result = session.execute(
                delete(CertificateSourceModel).where(CertificateSourceModel.path == path)
            )
            return bool(result.rowcount and result.rowcount > 0)

    def delete_by_fingerprint(self, fingerprint: str) -> int:
        """Удаляет все записи файлов для сертификата с указанным отпечатком.

        Args:
            fingerprint: SHA-256 отпечаток сертификата.

        Returns:
            int: Количество удаленных записей.
        """
        with self.sessions.begin() as session:
            result = session.execute(
                delete(CertificateSourceModel).where(
                    CertificateSourceModel.fingerprint == fingerprint
                )
            )
            return result.rowcount or 0
