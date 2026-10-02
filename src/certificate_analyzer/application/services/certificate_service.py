"""Сервис приложения для импорта, поиска, аудита и управления сертификатами."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.services.certificate_status import certificate_status


@dataclass
class ImportResult:
    """Результат пакетного импорта сертификатов.

    Attributes:
        certificates: Список успешно импортированных или обновленных сертификатов.
        errors: Словарь ошибок с путями к файлам и сообщениями об исключениях.
        imported: Количество вновь добавленных записей.
        updated: Количество обновленных записей.
        skipped: Количество пропущенных (неизменившихся) файлов.
    """

    certificates: list[Certificate] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    imported: int = 0
    updated: int = 0
    skipped: int = 0


class CertificateService:
    """Сервис бизнес-логики учета, импорта, управления файлами и аудита сертификатов."""

    def __init__(
        self,
        *,
        scanner,
        parser,
        repository,
        storage,
        phonebook_service,
        settings,
        platform_file_manager=None,
        audit_service=None,
        file_repository=None,
        employee_service=None,
    ):
        """Инициализирует сервис сертификатов.

        Args:
            scanner: Функция сканирования каталогов для поиска файлов сертификатов.
            parser: Парсер сертификатов X.509 (X509Parser).
            repository: Репозиторий метаданных сертификатов CertificateRepository.
            storage: Управляемое файловое хранилище сертификатов ManagedStorage.
            phonebook_service: Сервис телефонного справочника для обогащения контактов.
            settings: Настройки приложения.
            platform_file_manager: Платформо-зависимый файловый менеджер PlatformFileManager (опционально).
            audit_service: Сервис журнала аудита AuditService (опционально).
            file_repository: Репозиторий источников файлов CertificateFileRepository (опционально).
            employee_service: Сервис учета сотрудников EmployeeService (опционально).
        """
        self.scanner = scanner
        self.parser = parser
        self.repository = repository
        self.storage = storage
        self.phonebook = phonebook_service
        self.settings = settings
        self.platform = platform_file_manager
        self.audit = audit_service
        self.file_repository = file_repository
        self.employees = employee_service

    def import_folder(self, folder: str | Path, phonebook_path: str | Path | None = None) -> ImportResult:
        """Сканирует папку и импортирует все найденные файлы сертификатов.

        Args:
            folder: Путь к сканируемой папке.
            phonebook_path: Путь к файлу телефонного справочника (опционально).

        Returns:
            ImportResult: Результат пакетного импорта.
        """
        return self.import_files(self.scanner(folder), phonebook_path=phonebook_path)

    def import_files(self, paths: list[str | Path], phonebook_path: str | Path | None = None) -> ImportResult:
        """Импортирует список файлов сертификатов с проверкой на дубликаты.

        При совпадении отпечатка SHA-256 повторная доменная запись Certificate не создается,
        а добавляется связь с физическим файлом CertificateFile / CertificateSource.

        Args:
            paths: Список путей к файлам сертификатов.
            phonebook_path: Путь к файлу телефонного справочника (опционально).

        Returns:
            ImportResult: Результат импорта со счетчиками и списком ошибок.
        """
        result = ImportResult()
        if phonebook_path:
            self.phonebook.load(phonebook_path)
        elif self.settings.phonebook_path and not self.phonebook.employees:
            try:
                self.phonebook.load(self.settings.phonebook_path)
            except (OSError, ValueError) as exc:
                result.errors[str(self.settings.phonebook_path)] = str(exc)

        paths = list(dict.fromkeys(str(Path(p).expanduser().resolve()) for p in paths))
        collected = {}
        now = datetime.utcnow()

        # Обработка пакетами по 200 файлов для ограничения нагрузки на транзакцию БД
        for start in range(0, len(paths), 200):
            batch = paths[start : start + 200]
            known = self.repository.cached_sources(batch)
            certificates, sources, fingerprints = [], [], []

            for path in batch:
                try:
                    data = Path(path).read_bytes()
                    digest = sha256(data).hexdigest()
                    cached = known.get(path)

                    if cached and cached[0] == digest and not self.phonebook.employees:
                        stored = Path(cached[1])
                        if (
                            stored.parent == self.storage.folder
                            and stored.is_file()
                            and sha256(stored.read_bytes()).hexdigest().upper() == cached[2]
                        ):
                            result.skipped += 1
                            fingerprints.append(cached[2])
                            continue

                    cert, der = self.parser.parse_for_import(data)
                    cert.status = certificate_status(
                        cert.valid_from,
                        cert.valid_to,
                        warning_days=self.settings.warning_days,
                    )
                    cert.original_name = Path(path).name
                    cert.source_path = str(
                        self.storage.put(cert.fingerprint_sha256, der)
                    )
                    self._enrich(cert)

                    # Сопоставление с сотрудником через EmployeeService, если доступен
                    if self.employees and cert.employee and cert.employee.full_name:
                        emp = self.employees.get_or_create(
                            cert.employee.full_name, department=cert.employee.department
                        )
                        cert.employee.id = emp.id

                    certificates.append(cert)
                    sources.append(
                        {
                            "path": path,
                            "fingerprint": cert.fingerprint_sha256,
                            "content_sha256": digest,
                            "file_name": Path(path).name,
                            "size": len(data),
                            "first_seen_at": now,
                            "last_seen_at": now,
                        }
                    )
                    fingerprints.append(cert.fingerprint_sha256)

                    if self.audit:
                        self.audit.log_event(
                            event_type="CERTIFICATE_IMPORTED",
                            entity_type="CERTIFICATE",
                            entity_id=cert.fingerprint_sha256,
                            description=f"Импортирован файл «{Path(path).name}» для «{cert.subject}»",
                            details={"path": path, "fingerprint": cert.fingerprint_sha256},
                        )
                except (ValueError, OSError) as exc:
                    result.errors[path] = str(exc)

            inserted = self.repository.save_many(certificates, sources)
            result.imported += inserted
            result.updated += len(certificates) - inserted

            for cert in self.repository.find_many(list(dict.fromkeys(fingerprints))):
                collected[cert.fingerprint_sha256] = cert

        result.certificates = list(collected.values())
        return result

    def _enrich(self, cert: Certificate) -> None:
        """Обогащает данные о сотруднике номерами телефонов из справочника.

        Args:
            cert: Доменная сущность сертификата.

        Returns:
            None
        """
        if not cert.employee:
            return
        phone = self.phonebook.find_phone(
            office=cert.employee.office,
            full_name=cert.employee.full_name,
            department=cert.employee.department,
        )
        if phone:
            cert.employee.phones = [p.strip() for p in phone.split(",") if p.strip()]

    def load_phonebook(self, path: str | Path) -> int:
        """Загружает телефонный справочник и обновляет контакты существующих сертификатов.

        Args:
            path: Путь к файлу справочника (.txt или .docx).

        Returns:
            int: Количество сотрудников в справочнике.
        """
        self.phonebook.load(path)
        offset = 0
        while batch := self.repository.list(CertificateQuery(limit=200, offset=offset)):
            for cert in batch:
                self._enrich(cert)
            self.repository.save_many(batch)
            offset += len(batch)
        return len(self.phonebook.employees)

    def list(self, query: CertificateQuery | None = None) -> list[Certificate]:
        """Возвращает страницу сертификатов по заданному запросу.

        Args:
            query: Параметры поиска, фильтрации и пагинации CertificateQuery.

        Returns:
            list[Certificate]: Список доменных моделей сертификатов.
        """
        return self.repository.list(query)

    def statistics(self, query: CertificateQuery | None = None) -> dict[str, int]:
        """Возвращает агрегированную статистику по статусам сертификатов.

        Args:
            query: Параметры фильтрации.

        Returns:
            dict[str, int]: Количество сертификатов по статусам.
        """
        return self.repository.statistics(query)

    def get(self, fingerprint: str) -> Certificate:
        """Получает сертификат по его уникальному SHA-256 отпечатку.

        Args:
            fingerprint: Отпечаток сертификата.

        Returns:
            Certificate: Найденный сертификат.

        Raises:
            ValueError: Если сертификат с указанным отпечатком не найден.
        """
        cert = self.repository.find_by_fingerprint(fingerprint)
        if cert is None:
            raise ValueError("Запись сертификата не найдена")
        return cert

    def _resolve_file_path(self, cert: Certificate) -> str | None:
        """Находит существующий файл сертификата в хранилище или исходном расположении.

        Args:
            cert: Доменная модель сертификата.

        Returns:
            str | None: Путь к найденному файлу или None.
        """
        # 1. Проверяем source_path (управляемое хранилище или исходный путь)
        if cert.source_path and Path(cert.source_path).is_file():
            return cert.source_path

        # 2. Проверяем хранилище по отпечатку
        managed = self.storage.folder / f"{cert.fingerprint_sha256}.cer"
        if managed.is_file():
            return str(managed)

        # 3. Проверяем через репозиторий файлов
        if self.file_repository:
            files = self.file_repository.list_by_fingerprint(cert.fingerprint_sha256)
            for f in files:
                if Path(f.path).is_file():
                    return f.path

        return None

    def open_file(self, fingerprint: str) -> bool:
        """Открывает физический файл сертификата средством ОС по умолчанию.

        Args:
            fingerprint: Отпечаток сертификата.

        Returns:
            bool: True в случае успешного вызова.

        Raises:
            FileNotFoundError: Если файл сертификата отсутствует на диске.
        """
        cert = self.get(fingerprint)
        file_path = self._resolve_file_path(cert)
        if not file_path:
            raise FileNotFoundError(f"Файл сертификата {fingerprint} отсутствует на диске")

        if self.platform:
            self.platform.open_file(file_path)
        else:
            from certificate_analyzer.infrastructure.platform.base import open_path
            open_path(file_path)

        if self.audit:
            self.audit.log_event(
                event_type="FILE_OPENED",
                entity_type="CERTIFICATE",
                entity_id=fingerprint,
                description=f"Открыт файл сертификата: {file_path}",
                details={"path": str(file_path)},
            )
        return True

    def reveal_file(self, fingerprint: str) -> bool:
        """Показывает файл сертификата в файловом менеджере (выделяет его).

        Args:
            fingerprint: Отпечаток сертификата.

        Returns:
            bool: True в случае успешного вызова.

        Raises:
            FileNotFoundError: Если файл сертификата отсутствует на диске.
        """
        cert = self.get(fingerprint)
        file_path = self._resolve_file_path(cert)
        if not file_path:
            raise FileNotFoundError(f"Файл сертификата {fingerprint} отсутствует на диске")

        if self.platform:
            self.platform.reveal_file(file_path)
        else:
            from certificate_analyzer.infrastructure.platform.base import reveal_in_explorer
            reveal_in_explorer(file_path)

        if self.audit:
            self.audit.log_event(
                event_type="FILE_REVEALED",
                entity_type="CERTIFICATE",
                entity_id=fingerprint,
                description=f"Файл выделен в проводнике: {file_path}",
                details={"path": str(file_path)},
            )
        return True

    def delete_file(self, fingerprint: str, move_to_trash: bool = True) -> tuple[bool, str]:
        """Удаляет физический файл сертификата (в корзину или навсегда).

        Запись о сертификате в учете сохраняется, но файл удаляется с диска.

        Args:
            fingerprint: Отпечаток сертификата.
            move_to_trash: Переместить в корзину (True) или удалить безвозвратно (False).

        Returns:
            tuple[bool, str]: Кортеж (успех удаления, абсолютный путь к удаленному файлу).

        Raises:
            FileNotFoundError: Если файл сертификата не найден на диске.
        """
        cert = self.get(fingerprint)
        file_path = self._resolve_file_path(cert)
        if not file_path:
            raise FileNotFoundError(f"Файл сертификата {fingerprint} не найден на диске")

        path_str = str(file_path)
        if move_to_trash and self.platform:
            self.platform.move_to_trash(path_str)
        else:
            Path(path_str).unlink(missing_ok=True)

        if self.file_repository:
            self.file_repository.delete_by_path(path_str)

        if self.audit:
            self.audit.log_event(
                event_type="FILE_DELETED",
                entity_type="CERTIFICATE",
                entity_id=fingerprint,
                description=f"Файл «{path_str}» удален (в корзину: {move_to_trash})",
                details={"path": path_str, "move_to_trash": move_to_trash},
            )
        self.delete_records([fingerprint])
        return True, path_str

    def delete_records(self, fingerprints: list[str]) -> int:
        """Удаляет сертификаты из учета (метаданные), не удаляя физические файлы.

        Args:
            fingerprints: Список отпечатков удаляемых сертификатов.

        Returns:
            int: Количество удаленных записей.
        """
        count = self.repository.delete(fingerprints)
        if self.audit:
            for fp in fingerprints:
                self.audit.log_event(
                    event_type="RECORD_DELETED",
                    entity_type="CERTIFICATE",
                    entity_id=fp,
                    description=f"Запись сертификата {fp} удалена из учета",
                    details={"fingerprint": fp},
                )
        return count
