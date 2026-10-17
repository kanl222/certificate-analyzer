"""Real separate-process IPC, daemon-owned database and recovery."""

from dataclasses import asdict
from datetime import date
import json
import os
import subprocess
import sys
import time

import pytest

from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.domain.enums.certificate_request_status import CertificateRequestStatus
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.runtime.ipc import WriteClient, WriterServer, WriterUnavailable, WriteCommandError


@pytest.fixture
def writer(tmp_path):
    settings = Settings(database_path=str(tmp_path / "records.db"),
                        storage_folder=str(tmp_path / "certificates"),
                        export_folder=str(tmp_path / "reports"), check_interval=3600)
    environment = os.environ.copy()
    environment["CERTIFICATE_ANALYZER_DAEMON_SETTINGS"] = json.dumps(asdict(settings))
    process = subprocess.Popen([sys.executable, "-m", "certificate_analyzer", "worker"],
                               env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    client = WriteClient(settings.database_path, timeout=3)
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                info, _ = client.call()
                assert info["pid"] != os.getpid()
                break
            except WriterUnavailable:
                if process.poll() is not None or time.monotonic() > deadline:
                    _, errors = process.communicate(timeout=2)
                    pytest.fail(errors.decode(errors="replace"))
                time.sleep(0.05)
        yield settings, process, client
    finally:
        if process.poll() is None:
            try:
                client.call(method="stop")
                process.wait(timeout=10)
            except (WriterUnavailable, subprocess.TimeoutExpired):
                process.terminate()
                process.wait(timeout=5)
        process.communicate()


def test_gui_crud_reads_committed_data_and_cannot_write(writer):
    settings, _, _ = writer
    with create_application(settings=settings, read_only=True) as gui:
        created = gui.employees.save_employee(Employee(full_name="IPC сотрудник", birth_date=date(1980, 1, 2)))
        assert created.id is not None
        assert gui.employees.get_employee(created.id).birth_date == date(1980, 1, 2)
        created.department = "Отдел"
        gui.employees.save_employee(created)
        assert gui.employees.get_employee(created.id).department == "Отдел"
        assert gui.employees.count_employees(search="ipc СОТРУДНИК") == 1
        assert gui.employees.list_employees(search="ipc СОТРУДНИК", limit=1)[0].id == created.id
        request = gui.certificate_requests.create_request(full_name=created.full_name, employee_id=created.id)
        assert request.id is not None
        assert gui.certificate_requests.count_by_status(search="ipc СОТРУДНИК") == {CertificateRequestStatus.NOT_SUBMITTED: 1}
        assert gui.certificate_requests.list_requests(search="ipc СОТРУДНИК", limit=1)[0].id == request.id
        gui.certificate_requests.update_status(request.id, CertificateRequestStatus.PROCESSED)
        assert gui.certificate_requests.get_request(request.id).status == CertificateRequestStatus.PROCESSED
        assert not hasattr(gui.database, "engine")
        assert not hasattr(gui.database, "sessions")
        assert gui.certificate_requests.delete_request(request.id)
        assert gui.employees.delete_employee(created.id)
        assert gui.employees.get_employee(created.id) is None


def test_import_and_audit_through_ipc(writer, certificate_file):
    settings, _, _ = writer
    with create_application(settings=settings, read_only=True) as gui:
        result = gui.certificates.import_files([certificate_file()])
        assert result.imported == 1
        fingerprint = result.certificates[0].fingerprint_sha256
        assert gui.certificates.get(fingerprint).fingerprint_sha256 == fingerprint
        query = CertificateQuery(search=result.certificates[0].subject, limit=1)
        assert [item.fingerprint_sha256 for item in gui.certificates.list(query)] == [fingerprint]
        assert [item.fingerprint_sha256 for item in gui.certificates.list(CertificateQuery(limit=None))] == [fingerprint]
        assert gui.certificates.statistics(query)["total"] == 1
        assert gui.audit.list_events()
        assert gui.certificates.delete_records([fingerprint]) == 1
        assert gui.certificates.statistics()["total"] == 0


def test_archive_export_restore_in_real_daemon(writer, certificate_file, tmp_path):
    settings, _, _ = writer
    with create_application(settings=settings, read_only=True) as gui:
        assert gui.certificates.import_files([certificate_file()]).imported == 1
        archive = tmp_path / "through-ipc.cat"
        assert gui.archive.export(archive, "long-secret-password")["path"] == str(archive)
        preview = gui.archive.inspect(archive, "long-secret-password")
        gui.archive.restore(archive, "long-secret-password", "replace", {}, preview["digest"])
        assert gui.certificates.statistics()["total"] == 1
        assert not hasattr(gui.database, "engine")


def test_unavailable_does_not_fall_back_to_gui_write(writer):
    settings, process, client = writer
    with create_application(settings=settings, read_only=True) as gui:
        client.call(method="stop")
        process.wait(timeout=10)
        with pytest.raises(WriterUnavailable, match="Фоновый процесс недоступен"):
            gui.employees.save_employee(Employee(full_name="Не записывать"))
        with pytest.raises(WriterUnavailable, match="Фоновый процесс недоступен"):
            gui.employees.list_employees()


def test_cli_stop_waits_for_daemon_exit(writer):
    from certificate_analyzer.cli import main
    from certificate_analyzer.runtime.ipc import token_path

    settings, process, _ = writer
    assert main(["--database", settings.database_path, "worker", "--stop"]) == 0
    process.wait(timeout=10)
    assert not token_path(settings.database_path).exists()


def test_existing_gui_reconnects_after_daemon_restart(writer):
    from certificate_analyzer.runtime.user_daemon import restart_writer, stop_writer
    settings, process, client = writer
    with create_application(settings=settings, read_only=True) as gui:
        created = gui.employees.save_employee(Employee(full_name="Before restart"))
        restart_writer(settings)
        process.wait(timeout=10)
        try:
            created.department = "After restart"
            gui.employees.save_employee(created)
            assert gui.employees.get_employee(created.id).department == "After restart"
        finally:
            stop_writer(settings)


def test_second_writer_and_unknown_commands_rejected(writer):
    settings, _, client = writer
    with pytest.raises(OSError):
        WriterServer(settings.database_path)
    with pytest.raises(WriteCommandError, match="Неизвестная команда"):
        client.call("employees", "repository")
    with pytest.raises(WriteCommandError):
        client.call("employees", "save_employee", args=())
    assert client.call()[0]["pid"]


def test_mchd_import_and_error_details(writer, mchd_file):
    settings, _, _ = writer
    with create_application(settings=settings, read_only=True) as gui:
        path = mchd_file()
        documents = gui.mchds.import_files([path, path.parent / "missing.xml"])
        assert len(documents) == 1
        number = documents[0].unified_number
        assert gui.mchds.get_by_number(number).authority_codes == documents[0].authority_codes
        assert gui.mchds.list_all(limit=1)[0].unified_number == number
        assert "missing.xml" in next(iter(gui.mchds.errors))
        assert gui.mchds.delete(number)
        assert gui.mchds.get_by_number(number) is None


def test_audit_of_open_file_goes_to_writer(writer, certificate_file, monkeypatch):
    settings, _, _ = writer
    with create_application(settings=settings, read_only=True) as gui:
        result = gui.certificates.import_files([certificate_file()])
        monkeypatch.setattr(gui.platform, "open_file", lambda _: True)
        assert gui.certificates.open_file(result.certificates[0].fingerprint_sha256)
        assert gui.audit.list_events(event_type="FILE_OPENED")


def test_wrong_authentication_is_rejected(writer):
    import socket
    from certificate_analyzer.runtime.ipc import endpoint, receive, send
    settings, _, _ = writer
    with socket.create_connection(endpoint(settings.database_path), timeout=2) as connection:
        with connection.makefile("rwb") as stream:
            send(stream, {"version": 1, "token": "wrong", "service": "", "method": "stop"})
            assert receive(stream)["ok"] is False
    assert WriteClient(settings.database_path).call()[0]["pid"]


def test_daemon_events_are_logged_without_authentication_token(writer):
    from certificate_analyzer.infrastructure.config.paths import config_dir
    from certificate_analyzer.runtime.ipc import token_path
    settings, process, client = writer
    token = token_path(settings.database_path).read_text()
    with create_application(settings=settings, read_only=True) as gui:
        gui.employees.save_employee(Employee(full_name="Private name must not appear in logs"))
    client.call(method="stop")
    process.wait(timeout=10)
    content = (config_dir() / "application.log").read_text(encoding="utf-8")
    for event in ("Демон запущен", "employees.save_employee", "Начало проверки", "Демон остановлен"):
        assert event in content
    assert token not in content
    assert "Private name must not appear in logs" not in content


def test_parallel_clients_and_daemon_reads(writer):
    from concurrent.futures import ThreadPoolExecutor
    settings, _, _ = writer
    with create_application(settings=settings, read_only=True) as gui:
        assert gui.employees.count_employees() == 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            employees = list(pool.map(lambda i: gui.employees.save_employee(Employee(full_name=f"Employee {i}")), range(12)))
        assert len({employee.id for employee in employees}) == 12
        assert len(gui.employees.list_employees()) == 12
