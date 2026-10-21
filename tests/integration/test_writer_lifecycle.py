"""Проверки публикации порта и восстановления единственного writer после аварии."""

from dataclasses import asdict
import json
import os
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

import pytest

from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.runtime import ipc


@pytest.mark.parametrize("contents", ["", "0", "65536", "invalid", "-1", "\ufffd"])
def test_corrupt_port_record_uses_legacy_endpoint(tmp_path, contents):
    path = tmp_path / "records.db"
    ipc.port_path(path).write_text(contents, encoding="utf-8")
    assert ipc.endpoint(path) == ipc._default_endpoint(path)


def test_closing_old_server_twice_preserves_new_server_discovery(tmp_path):
    path = tmp_path / "records.db"
    old = ipc.WriterServer(path)
    old.attach(SimpleNamespace(database=SimpleNamespace(path=path)))
    old.server_close()
    with ipc.WriterServer(path) as current:
        current.attach(SimpleNamespace(database=SimpleNamespace(path=path)))
        old.server_close()
        assert ipc.port_path(path).exists()
        assert ipc.endpoint(path) == current.server_address
        assert ipc.token_path(path).exists()


def test_failed_private_publication_removes_temporary_file_and_releases_lock(tmp_path, monkeypatch):
    path = tmp_path / "records.db"

    def denied_access(_target):
        raise PermissionError("Не удалось выставить права")

    monkeypatch.setattr(ipc.WriterServer, "_restrict_access", staticmethod(denied_access))
    with ipc.WriterServer(path) as server:
        with pytest.raises(PermissionError):
            server.attach(SimpleNamespace(database=SimpleNamespace(path=path)))
    assert not list(tmp_path.glob("*.ipc-port*"))
    assert not list(tmp_path.glob("*.ipc-token*"))
    with ipc.WriterServer(path):
        pass


def test_fallback_writer_recovers_after_process_crash_without_data_loss(tmp_path):
    """Клиент другого процесса находит запасной порт; после аварии БД доступна снова."""
    from certificate_analyzer.bootstrap import create_application
    from certificate_analyzer.runtime.user_daemon import ensure_writer, stop_writer

    settings = Settings(database_path=str(tmp_path / "records.db"), folders={},
                        storage_folder=str(tmp_path / "storage"),
                        mchd_folder=str(tmp_path / "mchd"),
                        export_folder=str(tmp_path / "reports"), check_interval=3600)
    environment = os.environ.copy()
    environment["CERTIFICATE_ANALYZER_DAEMON_SETTINGS"] = json.dumps(asdict(settings))
    program = """
import errno, json, os
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.runtime.ipc import WriterServer
from certificate_analyzer.runtime.user_daemon import run_writer
bind = WriterServer.server_bind
def denied_default(server):
    if server.server_address[1] != 0:
        raise PermissionError(errno.EACCES, 'Reserved port')
    return bind(server)
WriterServer.server_bind = denied_default
run_writer(Settings(**json.loads(os.environ['CERTIFICATE_ANALYZER_DAEMON_SETTINGS'])))
"""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen([sys.executable, "-c", program], env=environment,
                                   stdout=output, stderr=output)
        client = ipc.WriteClient(settings.database_path, timeout=1)
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    info, _ = client.call()
                    break
                except ipc.WriterUnavailable:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        output.seek(0)
                        pytest.fail(output.read().decode("utf-8", errors="replace"))
                    time.sleep(0.05)
            assert ipc.endpoint(settings.database_path) != ipc._default_endpoint(settings.database_path)
            employee, _ = client.call("employees", "get_or_create", ("До перезапуска",))
            process.kill()
            process.wait(timeout=5)
            ensure_writer(settings)
            assert client.call()[0]["pid"] != info["pid"]
            with create_application(settings=settings, read_only=True) as reader:
                assert reader.employees.get_employee(employee.id).full_name == "До перезапуска"
        finally:
            try:
                stop_writer(settings)
            except ipc.WriterUnavailable:
                pass
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
