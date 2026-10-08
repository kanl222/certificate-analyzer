"""Local, authenticated JSON command API. No pickle or arbitrary method dispatch."""

import dataclasses
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from certificate_analyzer.application.services.certificate_service import ImportResult
from certificate_analyzer.application.services.monitoring_service import MonitoringResult
from certificate_analyzer.domain.models.audit_event import AuditEvent
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.certificate_file import CertificateFile
from certificate_analyzer.domain.models.certificate_request import CertificateRequest
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.domain.enums.certificate_request_status import CertificateRequestStatus
from certificate_analyzer.domain.enums.mchd_status import MchdStatus

TYPES = {cls.__name__: cls for cls in (
    ImportResult, MonitoringResult, AuditEvent, Certificate, CertificateFile, CertificateRequest,
    Employee, MchdDocument, CertificateStatus, CertificateRequestStatus, MchdStatus,
)}
COMMANDS = {
    "archive": {"export", "export_choices", "inspect", "restore"},
    "certificates": {"import_files", "import_folder", "load_phonebook", "delete_records", "delete_file"},
    "employees": {"save_employee", "get_or_create", "delete_employee"},
    "certificate_requests": {"create_request", "update_status", "link_certificate", "delete_request"},
    "mchds": {"scan", "import_files", "save", "delete"},
    "audit": {"log_event"},
    "monitoring": {"run_cycle"},
}


def encode(value):
    if isinstance(value, Enum):
        return {"$type": type(value).__name__, "value": value.value}
    if dataclasses.is_dataclass(value):
        return {"$type": type(value).__name__, "fields": {
            f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)
        }}
    if isinstance(value, (datetime, date, Path)):
        kind = "datetime" if isinstance(value, datetime) else "date" if isinstance(value, date) else "path"
        return {"$type": kind, "value": str(value)}
    if isinstance(value, tuple):
        return {"$type": "tuple", "value": [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    return value


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    kind = value.get("$type")
    if not kind:
        return {k: decode(v) for k, v in value.items()}
    if kind in ("datetime", "date", "path", "tuple"):
        return {"datetime": datetime.fromisoformat, "date": date.fromisoformat,
                "path": Path, "tuple": lambda v: tuple(decode(v))}[kind](value["value"])
    cls = TYPES[kind]
    if issubclass(cls, Enum):
        return cls(value["value"])
    return cls(**decode(value["fields"]))


class CommandService:
    """Keep existing read methods local; route explicitly allowed writes to IPC."""

    def __init__(self, service, name, client):
        self._service, self._name, self._client = service, name, client

    def __getattr__(self, method):
        if method not in COMMANDS[self._name]:
            return getattr(self._service, method)

        def execute(*args, **kwargs):
            result, errors = self._client.call(self._name, method, args, kwargs)
            if hasattr(self._service, "errors"):
                self._service.errors = errors
            return result
        return execute


def configure_client(app):
    from certificate_analyzer.runtime.ipc import WriteClient
    client = WriteClient(app.database.path)
    for name in COMMANDS:
        setattr(app, name, CommandService(getattr(app, name), name, client))
    # Opening/revealing a file stays in the interactive session; its audit uses IPC.
    app.certificates._service.audit = app.audit
