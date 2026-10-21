"""Регрессионные тесты поведения по результатам аудита от октября 2026 года."""

from unittest.mock import Mock
from dataclasses import replace
from types import SimpleNamespace
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest
from sqlalchemy import select, update

from certificate_analyzer.application.services.mchd_service import MchdService
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.exceptions import MchdValidationError
from certificate_analyzer.infrastructure.database.models.certificates import CertificateModel
from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger
from certificate_analyzer.infrastructure.mchd.xml_parser import MchdXmlParser
from certificate_analyzer.infrastructure.repositories.employee_repository import EmployeeRepository
from certificate_analyzer.infrastructure.repositories.mchd_repository import MchdRepository


def test_import_certificate_keeps_employee_link(application, certificate_file):
    result = application.certificates.import_files([certificate_file()])
    assert not result.errors, result.errors
    certificate = application.certificates.list()[0]
    assert certificate.employee.id is not None
    with application.database.sessions() as session:
        assert session.scalar(select(CertificateModel.employee_id)) == certificate.employee.id


def test_reimport_repairs_missing_legacy_employee_link(application, certificate_file):
    source = certificate_file()
    application.certificates.import_files([source])
    with application.database.sessions.begin() as session:
        session.execute(update(CertificateModel).values(employee_id=None))
    result = application.certificates.import_files([source])
    assert not result.errors
    assert result.skipped == 0
    assert application.certificates.list()[0].employee.id is not None
    assert application.certificates.import_files([source]).skipped == 1


def test_full_namesakes_are_separate_records(application):
    repo = EmployeeRepository(application.database.sessions)
    first = repo.save(Employee(full_name="Иванов Иван", department="ИТ", inn="770000000001"))
    second = repo.save(Employee(full_name="Иванов Иван", department="Кадры", inn="770000000002"))
    assert first.id != second.id
    assert repo.get_by_id(first.id).inn == "770000000001"
    assert repo.find_by_name(first.full_name) is None


def test_delete_employee_preserves_certificates_and_requests(application, certificate_file):
    result = application.certificates.import_files([certificate_file()])
    assert not result.errors, result.errors
    repo = EmployeeRepository(application.database.sessions)
    certificate = application.certificates.list()[0]
    employee = repo.save(Employee(full_name="Linked employee"))
    certificate.employee.id = employee.id
    application.certificates.repository.save(certificate)
    request = application.certificate_requests.create_request(employee_id=employee.id)
    assert repo.delete(employee.id)
    assert application.certificates.list()[0].employee.id is None
    assert application.certificate_requests.get_request(request.id).employee_id is None


def test_merge_keeps_authority_names(mchd_file, tmp_path):
    first = mchd_file("one.xml", codes=("A", "B"))
    second = mchd_file("two.xml", codes=("B", "C"))
    target = tmp_path / "merged.xml"
    MCHDMerger.merge_mchd_files([{"file_name": str(first)}, {"file_name": str(second)}], target)
    merged = MchdXmlParser().parse(target)
    assert merged.authority_names == ["Полномочие A", "Полномочие B", "Полномочие C"]


def test_import_validation_is_used_and_errors_reset(mchd_file):
    validator = Mock()
    validator.validate_or_raise.side_effect = MchdValidationError("invalid identifier")
    repo = Mock()
    service = MchdService(repository=repo, validator=validator)
    source = mchd_file()
    assert service.import_files([source]) == []
    assert str(source) in service.errors
    repo.save.assert_not_called()
    service.import_files([])
    assert service.errors == {}


def test_import_rejects_invalid_identifiers(mchd_file):
    service = MchdService()
    source = mchd_file(inn="invalid")
    assert service.import_files([source]) == []
    assert str(source) in service.errors


def test_save_validates_document(mchd_file):
    validator = Mock()
    validator.validate_document_or_raise.side_effect = MchdValidationError("invalid identifier")
    repo = Mock()
    service = MchdService(repository=repo, validator=validator)
    with pytest.raises(MchdValidationError):
        service.save(MchdXmlParser().parse(mchd_file()))
    repo.save.assert_not_called()


def test_sql_search_paginates_after_unicode_filter(application, mchd_file):
    repo = MchdRepository(application.database.sessions)
    document = MchdXmlParser().parse(mchd_file())
    for index, name in enumerate(("Другой", "Иванов", "ИВАНОВ", "Иванов 100%")):
        repo.save(replace(document, unified_number=f"doc-{index}", representative_fio=name,
                          valid_to=document.valid_to + timedelta(days=index)))
    matches = repo.list_all(search="иВаНоВ", limit=1, offset=1)
    assert [doc.unified_number for doc in matches] == ["doc-2"]
    assert [doc.unified_number for doc in repo.list_all(search="100%", limit=2)] == ["doc-3"]
    assert repo.list_all(search="%_") == []
    assert len(repo.list_all(limit=0)) == 0
    with pytest.raises(ValueError):
        repo.list_all(offset=-1)


def test_mchd_import_runs_off_ui_thread_and_copies_errors():
    from certificate_analyzer.presentation.gui.views.mchd_view import MchdView
    ui_thread = threading.get_ident()
    threads = []
    callbacks = []
    service = SimpleNamespace(errors={"invalid.xml": "invalid"})
    with ThreadPoolExecutor(max_workers=1) as pool:
        def submit(work, finished):
            callbacks.append((pool.submit(work), finished))
        completed = []
        view = SimpleNamespace(app=SimpleNamespace(mchds=service), submit_task=submit,
                               _import_finished=completed.append)
        def action():
            threads.append(threading.get_ident())
            return ["document"]
        MchdView._run_import(view, action, "Imported")
        future, finished = callbacks[0]
        result = future.result(timeout=5)
        assert threads[0] != ui_thread
        assert completed == []
        service.errors.clear()
        finished(result)
        assert completed == [(["document"], {"invalid.xml": "invalid"}, "Imported")]


def test_connection_timeout_uses_configured_budget(tmp_path, monkeypatch):
    from certificate_analyzer.runtime import ipc
    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    stream = Mock()
    stream.__enter__ = Mock(return_value=stream)
    stream.__exit__ = Mock(return_value=False)
    connection.makefile.return_value = stream
    path = tmp_path / "db.sqlite"
    ipc.token_path(path).write_text("test-token", encoding="ascii")
    create_connection = Mock(return_value=connection)
    monkeypatch.setattr(ipc.socket, "create_connection", create_connection)
    monkeypatch.setattr(ipc, "receive", lambda stream: {"ok": True, "result": None})
    ipc.WriteClient(path, timeout=45).call()
    assert create_connection.call_args.kwargs["timeout"] == 45
    connection.settimeout.assert_called_once_with(45)


def test_timestamp_roundtrip_keeps_utc_timezone(application, certificate_file):
    from certificate_analyzer.domain.enums.certificate_request_status import CertificateRequestStatus

    application.certificates.import_files([certificate_file()])
    request = application.certificate_requests.create_request(status=CertificateRequestStatus.SUBMITTED)
    assert request.created_at.utcoffset() == timedelta(0)
    assert request.submitted_at.utcoffset() == timedelta(0)
    assert application.certificate_requests.get_request(request.id).created_at.utcoffset() == timedelta(0)
