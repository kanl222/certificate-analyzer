"""Локальный аутентифицированный JSON API команд. Без pickle и произвольного диспетчирования методов."""

from __future__ import annotations

from collections.abc import Callable
import dataclasses
from dataclasses import replace
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.application.services.certificate_service import CertificateService, ImportResult
from certificate_analyzer.application.services.monitoring_service import MonitoringResult
from certificate_analyzer.domain.enums.certificate_request_status import CertificateRequestStatus
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.audit_event import AuditEvent
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.certificate_file import CertificateFile
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.domain.models.mchd import MchdDocument

if TYPE_CHECKING:
    from certificate_analyzer.infrastructure.certificates.storage import CertificateStorage
    from certificate_analyzer.infrastructure.platform.base import PlatformFileManager
    from certificate_analyzer.runtime.ipc import WriteClient

TYPES: dict[str, type[Any]] = {cls.__name__: cls for cls in (
    ImportResult, MonitoringResult, AuditEvent, Certificate, CertificateFile, CertificateRequest,
    CertificateQuery,
    Employee, MchdDocument, CertificateStatus, CertificateRequestStatus, MchdStatus,
)}

COMMANDS: dict[str, set[str]] = {
    "archive": {"export", "export_choices", "inspect", "restore", "backup"},
    "certificates": {"import_files", "import_folder", "load_phonebook", "delete_records", "delete_file",
                     "list", "statistics", "get", "update_comment"},
    "certificate_files": {"get_by_path", "list_by_fingerprint"},
    "employees": {"save_employee", "get_or_create", "delete_employee",
                  "list_employees", "count_employees", "get_employee", "find_by_name"},
    "certificate_requests": {"create_request", "update_status", "link_certificate", "delete_request",
                             "get_request", "list_requests", "count_by_status"},
    "mchds": {"scan", "import_files", "save", "delete", "get_by_number", "list_all", "find_by_authority"},
    "audit": {"log_event", "list_events"},
    "monitoring": {"run_cycle"},
}

# Команды чтения не требуют формирования квитанций в журнале. Новые команды отслеживаются по умолчанию.
READ_COMMANDS: dict[str, set[str]] = {
    "archive": {"export_choices", "inspect"},
    "certificates": {"list", "statistics", "get"},
    "certificate_files": {"get_by_path", "list_by_fingerprint"},
    "employees": {"list_employees", "count_employees", "get_employee", "find_by_name"},
    "certificate_requests": {"get_request", "list_requests", "count_by_status"},
    "mchds": {"scan", "get_by_number", "list_all", "find_by_authority"},
    "audit": {"list_events"},
}


def encode(value: Any) -> Any:
    """Сериализует объекты домена и стандартные типы в JSON-совместимый формат."""
    if isinstance(value, Enum):
        return {"$type": type(value).__name__, "value": value.value}
    if dataclasses.is_dataclass(value):
        return {"$type": type(value).__name__, "fields": {
            f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)
        }}
    if isinstance(value, (datetime, date, Path)):
        kind: str = "datetime" if isinstance(value, datetime) else "date" if isinstance(value, date) else "path"
        return {"$type": kind, "value": str(value)}
    if isinstance(value, tuple):
        return {"$type": "tuple", "value": [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    return value


def decode(value: Any) -> Any:
    """Десериализует JSON-структуру в доменные объекты приложения."""
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    kind: str | None = value.get("$type")
    if not kind:
        return {k: decode(v) for k, v in value.items()}
    if kind in ("datetime", "date", "path", "tuple"):
        parsers: dict[str, Callable[[Any], Any]] = {
            "datetime": datetime.fromisoformat,
            "date": date.fromisoformat,
            "path": Path,
            "tuple": lambda v: tuple(decode(v)),
        }
        return parsers[kind](value["value"])
    cls: type[Any] = TYPES[kind]
    if issubclass(cls, Enum):
        return cls(value["value"])
    return cls(**decode(value["fields"]))


class RemoteService:
    """Предоставляет доступ только к разрешённым методам сервиса через IPC-демон."""

    def __init__(self, name: str, client: WriteClient) -> None:
        self._name: str = name
        self._client: WriteClient = client
        self.errors: dict[str, str] = {}

    def __getattr__(self, method: str) -> Callable[..., Any]:
        if method not in COMMANDS[self._name]:
            raise AttributeError(method)

        def execute(*args: Any, **kwargs: Any) -> Any:
            result: Any
            errors: dict[str, str]
            result, errors = self._client.call(self._name, method, args, kwargs)
            self.errors = errors
            return result
        return execute


class RemoteCertificateService(RemoteService):
    """Чтение метаданных через IPC; работа с файлами в интерактивном процессе."""

    _resolve_file_path = CertificateService._resolve_file_path
    open_file = CertificateService.open_file
    reveal_file = CertificateService.reveal_file

    def __init__(
        self,
        client: WriteClient,
        storage: CertificateStorage,
        platform: PlatformFileManager,
        audit: RemoteService,
        file_repository: RemoteService,
    ) -> None:
        super().__init__("certificates", client)
        self.storage: CertificateStorage = storage
        self.platform: PlatformFileManager = platform
        self.audit: RemoteService = audit
        self.file_repository: RemoteService = file_repository

    def list(self, query: CertificateQuery | None = None) -> list[Certificate]:
        """Постранично запрашивает список сертификатов через IPC."""
        if query is None or query.limit is not None:
            return super().__getattr__("list")(query)
        records: list[Certificate] = []
        offset: int = query.offset
        while True:
            batch: list[Certificate] = super().__getattr__("list")(replace(query, limit=100, offset=offset))
            records.extend(batch)
            if len(batch) < 100:
                return records
            offset += len(batch)
